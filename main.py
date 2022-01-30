import sys
import OpenGL.GL as gl
import OpenGL.GLUT as glut
import numpy as np
import ctypes

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
			error = gl.glGetProgramInfoLog(program).decode()
			print(error)
			raise RuntimeError("Linking error")

		gl.glDetachShader(program, vertex)
		gl.glDetachShader(program, fragment)

		self.program = program

		count = gl.glGetProgramiv(program, gl.GL_ACTIVE_UNIFORMS)
		self.uniforms = {name.decode(): i for i, (name, _, _) in enumerate(gl.glGetActiveUniform(program, i) for i in range(count))}
	
	def __getattribute__(self, name):
		if name.startswith("glUniform"):
			return lambda uniform, *args: self.set_uniform(name, uniform, *args)
		return object.__getattribute__(self, name)

	def set_uniform(self, method, uniform, *args):
		self.bind()
		object.__getattribute__(gl, method)(self.uniforms[uniform], *args)

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
		layout = layout or [(2, "a_position"), (4, "a_color")]

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

	def draw(self, x, y, w, h, r, g, b, a=1):
		if self.quad_index >= self.max_quad:
			self.flush()
		i = self.quad_index*4*self.stride
		for dx, dy in [(0, 0), (1, 0), (1, 1), (0, 1)]:
			self.quad_buffer[i+0] = x+dx*w
			self.quad_buffer[i+1] = y+dy*h
			self.quad_buffer[i+2] = r
			self.quad_buffer[i+3] = g
			self.quad_buffer[i+4] = b
			self.quad_buffer[i+5] = a
			i += self.stride
		self.quad_index += 1

	def flush(self):
		gl.glBindVertexArray(self.quadVA)
		self.shader.bind()
		gl.glBufferSubData(gl.GL_ARRAY_BUFFER, 0, self.quad_index*4*self.stride*SIZE_FLOAT, self.quad_buffer)
		gl.glDrawElements(gl.GL_TRIANGLES, self.quad_index*6, gl.GL_UNSIGNED_SHORT, None)
		self.begin_batch()

	def begin_batch(self):
		self.quad_index = 0


class App:
	def __init__(self, title, width, height):
		self.width = width
		self.height = height
		glut.glutInit()
		glut.glutInitDisplayMode(glut.GLUT_DOUBLE | glut.GLUT_RGBA)
		glut.glutCreateWindow(title)
		glut.glutReshapeWindow(width, height)
		glut.glutReshapeFunc(self.reshape)
		glut.glutDisplayFunc(self.display)
		glut.glutKeyboardFunc(self.keyboard)
		self.i = 0
		
	def init(self, batch):
		self.batch = batch

	def start(self):
		glut.glutMainLoop()

	def display(self):
		self.i += 1
		i = self.i
		gl.glClearColor((i%4)/4, (i%7)/7, (i%9)/9, 1)
		gl.glClear(gl.GL_COLOR_BUFFER_BIT)

		for i in range(50):
			self.batch.draw(i*100, i*100, 1*100, 1*100, 1, 0, 1)
		self.batch.flush()

		glut.glutSwapBuffers()

	def reshape(self, width, height):
		shader.glUniform4f("u_camera", width, height, 100, 100)
		gl.glViewport(0, 0, width, height)

	def keyboard(self, key, x, y):
		if key == b'\x1b':
			sys.exit()


app = App("Hello", 512, 512)
shader = Shader("""
attribute vec2 a_position;
attribute vec4 a_color;
varying vec4 v_color;

uniform vec4 u_camera;
uniform float u_zoom;

void main()
{
	gl_Position = vec4(((a_position-u_camera.zw)*u_zoom/u_camera.xy)*2., 0., 1.);
	v_color = a_color;
}
""", """
varying vec4 v_color;
void main()
{
	gl_FragColor = vec4(v_color);
}
""")
shader.glUniform1f("u_zoom", 1)
batch = Batch(1000, shader)
app.init(batch)
app.display()
app.start()
