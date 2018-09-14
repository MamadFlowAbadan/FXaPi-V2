from threading import Thread


class EventSystem():
	def __init__(self):
		self.events = {}

	def on(self, event):
		def _on(function):
			def _set(e):
				self.events.setdefault(e, []).append(function)

			if isinstance(event, list):
				for item in event:
					_set(item)
			elif isinstance(event, str):
				_set(event)

			return function
		return _on

	def emit(self, event, *args, **kwargs):
		if event in self.events:
			for function in self.events[event]:
				Thread(target=function, args=args, kwargs=kwargs).start()