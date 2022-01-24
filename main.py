import sys
import OpenGL.GL as gl
import OpenGL.GLUT as glut


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

	def bind(self):
		gl.glUseProgram(self.program)

	def unbind(self):
		gl.glUseProgram(0)


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

	def start(self):
		glut.glutMainLoop()

	def display(self):
		gl.glClear(gl.GL_COLOR_BUFFER_BIT)
		glut.glutSwapBuffers()

	def reshape(self, width, height):
		gl.glViewport(0, 0, width, height)

	def keyboard(self, key, x, y):
		if key == b'\x1b':
			sys.exit()


app = App("Hello", 512, 512)
shader = Shader("""
attribute vec2 position;
attribute vec4 color;
varying vec4 v_color;
void main()
{
	gl_Position = vec4(position, 0.0, 1.0);
	v_color = color;
}
""","""
varying vec4 v_color;
void main()
{
	gl_FragColor = vec4(v_color);
}
""")
app.start()
