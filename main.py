import inspect
import builtins
from typing import Callable
import PySimpleGUI as sg
import pathlib


ALLOWABLE_INT_CHARS = set('-_')
ALLOWABLE_FLOAT_CHARS = ALLOWABLE_INT_CHARS | set('.')


class App:
	def __init__(self) -> None:
		self.layout = []
		self.func = None
		self.arg_keys = []
		self.kwarg_keys = {}
		self.name = None
		self.convert_funcs = {}
		self.manual_values = {}
		self.window_map = {}

	def register(self, func_name: str = None):
		def _reg(func: Callable):
			self.func = func
			self.name = func_name or func.__name__

			signature = inspect.signature(func)

			for param_name, param in signature.parameters.items():
				default_value = None if param.default == inspect.Parameter.empty else param.default

				metadata = {'name': param_name}

				match param.annotation:
					case builtins.str:
						sg_key = f'-{param_name}-STR-'
						self.layout.append([sg.Text(param_name), sg.Input(default_value, key=sg_key, metadata=metadata)])

					case builtins.int:
						sg_key = f'-{param_name}-INT-'
						self.layout.append([sg.Text(param_name), sg.Input(default_value, key=sg_key, metadata=metadata, enable_events=True)])

					case builtins.float:
						sg_key = f'-{param_name}-FLOAT-'
						self.layout.append([sg.Text(param_name), sg.Input(default_value, key=sg_key, metadata=metadata, enable_events=True)])
						self.convert_funcs[sg_key] = float

					case builtins.bool:
						sg_key = f'-{param_name}-BOOL-'
						self.layout.append([sg.Text(param_name), sg.Checkbox(text='', default=default_value, key=sg_key, metadata=metadata)])

					case pathlib.Path:
						sg_key = f'-{param_name}-PATH-'
						self.layout.append([sg.Text(param_name), sg.Button('Browse', key=sg_key, metadata=metadata), sg.Text(key=f'{sg_key}-DISPLAY-')])

					case _ if param.annotation.__origin__ == builtins.list:
						sg_key = f'-{param_name}-LIST-'
						self.layout.append([sg.Text(param_name), sg.Button('Edit items', key=sg_key, metadata=metadata)])
						self.manual_values[sg_key] = default_value or []
						self.convert_funcs[f'{sg_key}_items'] = param.annotation.__args__[0]

					case _:
						raise TypeError(f"Parameter '{param_name}' is an unsupported type: '{param.annotation}'")

				self.convert_funcs[sg_key] = param.annotation

				if param.kind == param.POSITIONAL_ONLY:
					self.arg_keys.append(sg_key)
				else:
					self.kwarg_keys[sg_key] = param_name

			self.layout.append([sg.Submit()])

		return _reg

	def run(self) -> None:
		main_window = sg.Window(self.name, self.layout, finalize=True)
		self.window_map[main_window] = self._main_window_handle

		running = True
		while running:
			window, event, values = sg.read_all_windows()

			if window_handle := self.window_map.get(window):
				if not window_handle(window, event, values):
					window.close()
					self.window_map.pop(window)

			if len(self.window_map) == 0:
				# This feels like a weird pattern, like it should be handled by the _main_window_handle method
				# But the meaning here is "if you just closed the last window" which makes sense
				if event == sg.WIN_CLOSED:
					return
				break

		args = (self.convert_funcs[key](values[key]) if key in values else self.manual_values[key] for key in self.arg_keys)
		kwargs = {fn_key: self.convert_funcs[sg_key](values[sg_key]) if sg_key in values else self.manual_values[sg_key] for sg_key, fn_key in self.kwarg_keys.items()}
		self.func(*args, **kwargs)

	def _main_window_handle(self, window, event, values) -> bool:
		if event == sg.WIN_CLOSED:
			# Only close the main window when it's the last window
			return len(self.window_map) > 1

		elif event.endswith('-INT-'):
			if len(values[event]) > 0:
				try:
					_ = int(values[event])
				except ValueError:
					if values[event][-1] not in ALLOWABLE_INT_CHARS:
						window[event].update(values[event][:-1])

		elif event.endswith('-FLOAT-'):
			if len(values[event]) > 0:
				try:
					_ = float(values[event])
				except ValueError:
					if values[event][-1] not in ALLOWABLE_FLOAT_CHARS:
						window[event].update(values[event][:-1])

		elif event.endswith('-LIST-'):
			if event not in self.manual_values:
				self.manual_values[event] = []

			window, handle = self._list_handle(window[event].metadata['name'], event, self.convert_funcs[f'{event}_items'])
			self.window_map[window] = handle

		elif event.endswith('-PATH-'):
			self.manual_values[event] = sg.filedialog.askopenfilename()
			window[f'{event}-DISPLAY-'].update(value=self.manual_values[event])

		else:
			return False

		return True

	def _list_handle(self, title, list_key, element_type):
		init_col_layout = [
			[sg.Input(val, enable_events=True)] for val in self.manual_values[list_key]
		]
		init_col_layout.append([sg.Input(enable_events=True)])

		window = sg.Window(title, [
			[sg.Column(layout=init_col_layout, key='-ROWS-')],
			[sg.Submit(), sg.Cancel()],
		], finalize=True)

		def _handle(window, event, values):
			if event == sg.WINDOW_CLOSED or event == 'Cancel':
				return False

			elif event == 'Submit':
				self.manual_values[list_key] = [element_type(values[i]) for i in range(len(values)) if values[i] != '']
				return False

			else:
				if values[len(values) - 1] != '':
					window.extend_layout(window['-ROWS-'], [[sg.Input(enable_events=True)]])

			return True

		return window, _handle


if __name__ == '__main__':
	app = App()

	@app.register('GUInputs Test')
	def cli(save_to: pathlib.Path, names: list[str], comma: bool = True, times: int = 1, delays: list[float] = [0.], greeting: str = 'Hello'):
		import time
		from itertools import cycle

		print(f'Would save to {save_to}')
		for _ in range(times):
			for name, delay in zip(names, cycle(delays)):
				if not comma:
					print(f'{greeting} {name}')
				else:
					print(f'{greeting}, {name}')
				time.sleep(delay)

	app.run()
