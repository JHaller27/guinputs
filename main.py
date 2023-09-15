import inspect
import builtins
from typing import Callable
import PySimpleGUI as sg


ALLOWABLE_INT_CHARS = set('-_')
ALLOWABLE_FLOAT_CHARS = ALLOWABLE_INT_CHARS | set('.')


class App:
	def __init__(self) -> None:
		self.layout = []
		self.func = None
		self.arg_keys = []
		self.kwarg_keys = {}
		self.name = None

	def register(self, func_name: str = None):
		def _reg(func: Callable):
			self.func = func
			self.name = func_name or func.__name__

			signature = inspect.signature(func)

			for param_name, param in signature.parameters.items():
				default_value = None if param.default == inspect.Parameter.empty else param.default

				metadata = {'type': param.annotation}

				match param.annotation:
					case builtins.str:
						sg_key = f'-{param_name}-STR-'
						self.layout.append([sg.Text(param_name), sg.Input(default_value, key=sg_key, metadata=metadata)])

					case builtins.int:
						sg_key = f'-{param_name}-INT-'
						self.layout.append([sg.Text(param_name), sg.Input(default_value, key=sg_key, enable_events=True, metadata=metadata)])

					case builtins.float:
						sg_key = f'-{param_name}-FLOAT-'
						self.layout.append([sg.Text(param_name), sg.Input(default_value, key=sg_key, enable_events=True, metadata=metadata)])

					case builtins.bool:
						sg_key = f'-{param_name}-BOOL-'
						self.layout.append([sg.Text(param_name), sg.Checkbox(text='', default=default_value, key=sg_key, metadata=metadata)])

				if param.kind == param.POSITIONAL_ONLY:
					self.arg_keys.append(sg_key)
				else:
					self.kwarg_keys[sg_key] = param_name

			self.layout.append([sg.Submit()])

		return _reg

	def run(self) -> None:
		window = sg.Window(self.name, self.layout)
		while True:
			event, values = window.read()

			if event == sg.WIN_CLOSED:
				window.close()
				return

			elif event.endswith('-INT-') and len(values[event]) > 0:
				try:
					_ = int(values[event])
				except ValueError:
					if values[event][-1] not in ALLOWABLE_INT_CHARS:
						window[event].update(values[event][:-1])

			elif event.endswith('-FLOAT-') and len(values[event]) > 0:
				try:
					_ = float(values[event])
				except ValueError:
					if values[event][-1] not in ALLOWABLE_FLOAT_CHARS:
						window[event].update(values[event][:-1])

			else:
				break

		args = (window[key].metadata['type'](values[key]) for key in self.arg_keys)
		kwargs = {fn_key: window[sg_key].metadata['type'](values[sg_key]) for sg_key, fn_key in self.kwarg_keys.items()}
		self.func(*args, **kwargs)


if __name__ == '__main__':
	app = App()

	@app.register('GUInputs Test')
	def cli(name: str, comma: bool = True, times: int = 1, delay: float = 0., greeting: str = 'Hello'):
		import time
		for _ in range(times):
			time.sleep(delay)
			if not comma:
				print(f'{greeting} {name}')
			else:
				print(f'{greeting}, {name}')

	app.run()
