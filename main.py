import sys
import OpenGL.GL as gl
import OpenGL.GLUT as glut
import numpy as np
import ctypes
from PIL import Image
from time import time


# INITIALISATION
glut.glutInit()
glut.glutInitDisplayMode(glut.GLUT_DOUBLE | glut.GLUT_RGBA)
WINDOW = glut.glutCreateWindow("")


class Texture:
	def __init__(self, id):
		self.id = id

	def from_file(filename, *args):
		img = Image.open(filename)
		img_data = np.array(img.getdata(), np.uint8)
		return Texture.from_data(img_data, img.size[0], img.size[1], *args)

	def from_data(img_data, width, height, attach=0, wrap_s=gl.GL_CLAMP, wrap_t=gl.GL_CLAMP, filter_mag=gl.GL_NEAREST, filter_min=gl.GL_NEAREST, from_format=gl.GL_RGB, to_format=gl.GL_RGB):
		print(img_data)
		id = gl.glGenTextures(1)
		gl.glActiveTexture(gl.GL_TEXTURE0+attach)
		gl.glBindTexture(gl.GL_TEXTURE_2D, id)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, wrap_s)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, wrap_t)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, filter_mag)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, filter_min)
		gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, from_format, width, height, 0, to_format, gl.GL_UNSIGNED_BYTE, img_data)
		return Texture(id)

	def bind(self, id=0):
		gl.glActiveTexture(gl.GL_TEXTURE0+id)
		gl.glBindTexture(gl.GL_TEXTURE_2D, self.id)
		return id
Texture.white_texture = Texture.from_data(np.array([[255,255,255]], np.uint8), 1, 1)


class Shader:
	def __init__(self, vertex_code, fragment_code):
		program  = gl.glCreateProgram()
		vertex   = gl.glCreateShader(gl.GL_VERTEX_SHADER)
		fragment = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)

		gl.glShaderSource(vertex, vertex_code)
		gl.glShaderSource(fragment, fragment_code)
		gl.glCompileShader(vertex)

		if not gl.glGetShaderiv(vertex, gl.GL_COMPILE_STATUS):
			error = gl.glGetShaderInfoLog(vertex).decode()
			print(error)
			raise RuntimeError("Vertex shader compilation error")

		gl.glCompileShader(fragment)
		if not gl.glGetShaderiv(fragment, gl.GL_COMPILE_STATUS):
			error = gl.glGetShaderInfoLog(fragment).decode()
			print(error)
			raise RuntimeError("Fragment shader compilation error")

		gl.glAttachShader(program, vertex)
		gl.glAttachShader(program, fragment)
		gl.glLinkProgram(program)

		if not gl.glGetProgramiv(program, gl.GL_LINK_STATUS):
			error = gl.glGetProgramInfoLog(program)
			print(error)
			raise RuntimeError("Linking error")

		gl.glDetachShader(program, vertex)
		gl.glDetachShader(program, fragment)

		self.program = program

		count = gl.glGetProgramiv(program, gl.GL_ACTIVE_UNIFORMS)
		self.uniforms = {name.decode(): i for i, (name, _, _) in enumerate(gl.glGetActiveUniform(program, i) for i in range(count))}
		print(" - "+"\n - ".join(self.uniforms.keys()))
	
	def __getattribute__(self, name):
		if name.startswith("glUniform"):
			return lambda uniform, *args: self.set_uniform(name, uniform, *args)
		return object.__getattribute__(self, name)

	def set_uniform(self, method, uniform, *args):
		self.bind()
		object.__getattribute__(gl, method)(self.uniforms[uniform], *args)

	def set_texture(self, uniform, texture):
		self.bind()
		gl.glUniform1i(self.uniforms[uniform], texture.id)

	def bind(self):
		gl.glUseProgram(self.program)

	def unbind(self):
		gl.glUseProgram(0)


SIZE_FLOAT = 4
class Batch:
	def __init__(self, n, shader, layout=None):
		self.max_quad = n
		self.quad_index = 0
		self.shader = shader
		layout = layout or [(2, "a_position"), (2, "a_texcoord"), (4, "a_color")]

		self.quadVA = 0
		gl.glCreateVertexArrays(1, self.quadVA)
		self.quadVB = gl.glGenBuffers(1)
		self.quadIB = gl.glGenBuffers(1)
		gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.quadVB)
		gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.quadIB)

		layout, names  = zip(*layout)
		stride = sum(layout)
		self.stride = stride

		self.quad_buffer = np.zeros(n*4*stride, dtype=np.float32)
		index_buffer = np.zeros(n*6, dtype=np.uint16)

		gl.glBindVertexArray(self.quadVA)

		offset = 0
		for size, name in zip(layout, names):
			loc = gl.glGetAttribLocation(shader.program, name)
			gl.glEnableVertexAttribArray(loc)
			gl.glVertexAttribPointer(loc, size, gl.GL_FLOAT, False, stride*SIZE_FLOAT, ctypes.c_void_p(offset*SIZE_FLOAT))
			offset += size
		for i in range(0, n, 4):
			for j, (dx, dy) in enumerate([(0, 1), (1, 1), (1, 0), (0, 0)]):
				self.quad_buffer[(i+j)*stride+2] = dx
				self.quad_buffer[(i+j)*stride+3] = dy
		gl.glBufferData(gl.GL_ARRAY_BUFFER, self.quad_buffer.nbytes, self.quad_buffer, gl.GL_DYNAMIC_DRAW)

		offset = 0
		for i in range(n):
			index_buffer[i*6+0] = offset+0
			index_buffer[i*6+1] = offset+1
			index_buffer[i*6+2] = offset+2

			index_buffer[i*6+3] = offset+0
			index_buffer[i*6+4] = offset+2
			index_buffer[i*6+5] = offset+3
			offset += 4
		gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, index_buffer, gl.GL_STATIC_DRAW)

	def draw(self, x, y, w, h, *args):
		if self.quad_index >= self.max_quad:
			self.flush()
		stride = self.stride
		i = self.quad_index*4*stride
		for dx, dy in [(0, 0), (1, 0), (1, 1), (0, 1)]:
			self.quad_buffer[i+0] = x+dx*w
			self.quad_buffer[i+1] = y+dy*h
			self.quad_buffer[i+4:i+stride] = args
			i += stride
		self.quad_index += 1
		glut.glutPostRedisplay()

	def flush(self):
		gl.glBindVertexArray(self.quadVA)
		self.shader.bind()
		gl.glBufferSubData(gl.GL_ARRAY_BUFFER, 0, self.quad_index*4*self.stride*SIZE_FLOAT, self.quad_buffer)
		gl.glDrawElements(gl.GL_TRIANGLES, self.quad_index*6, gl.GL_UNSIGNED_SHORT, None)
		self.begin_batch()

	def begin_batch(self):
		self.quad_index = 0


class App:
	instanciated = False
	def __init__(self, title, width, height, r=0, g=0, b=0, a=1):
		if App.instanciated:
			raise RuntimeError("Only one app can be instanciated")
		App.instanciated = True
		self.width = width
		self.height = height
		self.last_frame = time()
		glut.glutSetWindowTitle(title)
		glut.glutReshapeWindow(width, height)
		glut.glutReshapeFunc(self._reshape)
		glut.glutDisplayFunc(self._display)
		glut.glutKeyboardFunc(self._keyboard)
		glut.glutMouseFunc(self.mouse_click)
		glut.glutPassiveMotionFunc(self.mouse_move)
		gl.glClearColor(r, g, b, a)
		
	def start(self):
		glut.glutMainLoop()

	def _display(self):
		gl.glClear(gl.GL_COLOR_BUFFER_BIT)
		now = time()
		dt = now-self.last_frame
		glut.glutSetWindowTitle(f"{int(1/dt)} fps")
		self.update(dt)
		self.last_frame = now
		glut.glutSwapBuffers()

	def _reshape(self, width, height):
		self.reshape(width, height)
		gl.glViewport(0, 0, width, height)

	def _keyboard(self, key, x, y):
		if key == b'\x1b':
			glut.glutDestroyWindow(WINDOW)
		else:
			self.keyboard(key, x, y)

	def update(self, dt):
		for i in range(50):
			self.batch.draw(i*100, i*100, 1*100, 1*100, 1, 0, 1, 1)
		self.batch.flush()

	def mouse_click(self, *args):
		print(args)
	def mouse_move(self, *args):
		print(args)
	def keyboard(self, *args):
		print(args)


base_vertex_shader = """
attribute vec2 a_position;
attribute vec2 a_texcoord;
attribute vec4 a_color;

uniform vec4 u_camera;
uniform float u_zoom;

varying vec2 v_texcoord;
varying vec4 v_color;

void main()
{
	gl_Position = vec4(((a_position-u_camera.zw)*u_zoom/u_camera.xy)*2., 0., 1.);
	v_texcoord = a_texcoord;
	v_color = a_color;
}
"""
base_fragment_shader = """
uniform sampler2D u_tex;

varying vec2 v_texcoord;
varying vec4 v_color;

void main()
{
	gl_FragColor = vec4(v_color)*texture2D(u_tex, v_texcoord);
}
"""
circle_fragment_shader = """
uniform sampler2D u_tex;

varying vec2 v_texcoord;
varying vec4 v_color;

void main()
{
	if (distance(v_texcoord, vec2(0.5)) > 0.5) discard;
	gl_FragColor = vec4(v_color)*texture2D(u_tex, v_texcoord);
}
"""
base_shader = Shader(base_vertex_shader, base_fragment_shader)
circle_shader = Shader(base_vertex_shader, circle_fragment_shader)
