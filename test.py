from main import *


class TestApp(App):
	def init(self, batch):
		self.batch = batch

	def reshape(self, width, height):
		self.batch.shader.glUniform4f("u_camera", width, height, 100, 100)


if __name__ == "__main__":
	app = TestApp("Hello", 512, 512)
	shader = circle_shader

	batch = Batch(1000, shader)
	#tex = Texture.from_file("img.png")
	tex = Texture.white_texture

	shader.glUniform1f("u_zoom", 1)
	shader.glUniform1i("u_tex", tex.bind(0))

	app.init(batch)
	app.start()
