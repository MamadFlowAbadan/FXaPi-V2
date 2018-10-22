__author__ = 'Andrey Derevyagin, Edited by avramit'
__copyright__ = 'Copyright © 2015'

import websocket
import logging
import urllib.request
import urllib.parse
import urllib.error
import urllib.request
import urllib.error
import urllib.parse
import time
import json
import threading
import queue
import six


class SIOMessage:
	def __init__(self, engine_io=None, socket_io=None, message=None, parsed=False, socket_io_add=None):
		self.socket_io = socket_io
		self.socket_io_add = socket_io_add
		self.engine_io = engine_io
		self.message = message
		self.parsed = parsed
		self.tm = time.time()

	def __str__(self):
		rv = str(self.engine_io)
		if self.socket_io is not None:
			rv += str(self.socket_io)
		if self.socket_io_add is not None:
			rv += str(self.socket_io_add)
		if self.message is not None:
			if self.parsed:
				if isinstance(self.message, six.string_types) or isinstance(self.message, (int, float, complex)):
					rv += json.dumps((self.message, ))
				else:
					rv += json.dumps(self.message)
			else:
				rv += self.message
		return rv

	def parse(self):
		if self.parsed is False:
			try:
				self.message = json.loads(self.message)
			except ValueError as e:
				pass
			self.parsed = True


class SendMessageThread(threading.Thread):
	def __init__(self, send_messages_queue, socketio_cli, ping_interval=None):
		threading.Thread.__init__(self)
		self.setDaemon(True)
		self.send_messages_queue = send_messages_queue
		self.socketio_cli = socketio_cli
		self.ping_interval = ping_interval

	def run(self):
		ping_tm = time.time()
		ping_msg = SIOMessage(2)
		self._running = True
		while True:
			if not self._running:
				break
			if self.ping_interval:
				tm = time.time()
				if tm - ping_tm > self.ping_interval:
					logging.debug('ping message')
					self.socketio_cli.ws.send(str(ping_msg))
					ping_tm = tm
			try:
				msg = self.send_messages_queue.get(block=True, timeout=1)
			except queue.Empty as e:
				msg = None
			if msg:
				logging.debug(f'send message: {str(msg)}')
				self.socketio_cli.ws.send(str(msg))

	def stop(self):
		self._running = False


class ParseMessagesThread(threading.Thread):
	def __init__(self, raw_messages_queue, socketio_cli):
		threading.Thread.__init__(self)
		self.setDaemon(True)
		self.raw_messages_queue = raw_messages_queue
		self.socketio_cli = socketio_cli

	def run(self):
		while True:
			msg = self.raw_messages_queue.get(block=True)
			self.socketio_cli.message_worker(msg)
			# self.parsed_messages_queue.put(msg)


class SocketIO():
	def __init__(self, url=None, cookiejar=None, callbacks={}, on_connect=None, autoreconnect=True):
		self._url = url
		self.cj = cookiejar
		self.info = None
		self.callbacks = callbacks
		self.on_connect = on_connect
		self.autoreconnect = autoreconnect
		self.stopping = False
		self.connecting = False
		self.reconnect_interval = 10

		self.opener = urllib.request.build_opener(
			urllib.request.HTTPRedirectHandler(),
			urllib.request.HTTPHandler(debuglevel=0),
			urllib.request.HTTPSHandler(debuglevel=0),
			urllib.request.HTTPCookieProcessor(self.cj)
		)

		# Amit Avr
		self.opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36')]

		self.raw_messages_queue = queue.Queue()
		self.parse_messages_thread = ParseMessagesThread(self.raw_messages_queue, self)
		self.parse_messages_thread.start()
		self.socket_thread = None

		self.send_messages_queue = queue.Queue()
		self.send_message_thread = None

		self._emit_callbacks = {}
		self._emit_callback_id = 0

		# Amit Avr
		self.ws = None

		if self._url:
			self.connect()

	def connect(self):
		self.connecting = True
		if not self._url:
			# raise
			return
		sio_url = self._url + '/socket.io/'
		polling_c = 0
		prms = {
			'EIO': '3',
			'transport': 'polling',
		}
		self.info = None
		while True:
			prms['t'] = f'{int(time.time()*1000)}-{polling_c}'
			if self.info:
				prms['sid'] = self.info.get('sid')
			data = urllib.parse.urlencode(prms)
			url = f'{sio_url}?{data}'
			logging.debug(url)
			try:
				response = self.opener.open(url)
			except Exception as e:
				return
			polling_c += 1
			data = response.read()

			packets = self.parse_polling_packet(data)
			for p in packets:
				logging.debug(f'receive packet: {p} {p.parsed}')
			if self.info:
				break
			for p in packets:
				if p.engine_io == 0:
					self.info = p.message
			break
		self.start()

	def run(self):
		sio_url = self._url + '/socket.io/'
		if 'http' == sio_url[:len('http')]:
			sio_url = 'ws' + sio_url[len('http'):]
		prms = {
			'EIO': '3',
			'transport': 'websocket',
			# sid: AmitAvr #self.info.get('sid')
			'sid': ''
		}
		data = urllib.parse.urlencode(prms)
		url = f'{sio_url}?{data}'
		headers = []
		if self.cj:
			cookies = ';'.join([f'{c.name}={c.value}' for c in self.cj])
			headers.append(f'Cookie: {cookies}')
		logging.debug(url)
		self.ws = websocket.WebSocketApp(url, on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close, header=headers)
		# AmitAvr
		self.ws.connected = False

		self.send_message(SIOMessage(2, message='probe'))
		self.send_message(SIOMessage(5, message=''))

		self.connecting = False

		# self.ws.run_forever(ping_interval=self.info.get('pingInterval', 0)/1000.0, ping_timeout=self.info.get('pingTimeout', 0)/1000.0)
		self.ws.run_forever()
		self.ws = None
		logging.debug('run ends')

		if not self.stopping and self.autoreconnect:
			self.reconnect()

	def start(self):
		self.stopping = False
		self.socket_thread = threading.Thread(target=self.run)
		self.socket_thread.setDaemon(True)
		self.socket_thread.start()

	def stop(self):
		self.stopping = True
		if self.ws is not None:
			self.ws.close()
		if self.socket_thread is not None:
			self.socket_thread.join()
			self.socket_thread = None

	def reconnect(self):
		while True:
			if self.connecting:
				time.sleep(self.reconnect_interval)
			if self.send_message_thread:
				self.send_message_thread.stop()
				self.send_message_thread.join()
				self.send_message_thread = None
			logging.info('reconnecting...')
			self.connect()
			if not self.connecting:
				break

	def on_open(self):
		# self.ws = ws

		# AmitAvr
		self.ws.connected = True

		logging.info('open socket')
		ping_interval = self.info.get(
			'pingInterval', 30000) / 1000 if self.info else 30
		self.send_message_thread = SendMessageThread(
			self.send_messages_queue, self, ping_interval)
		self.send_message_thread.start()

	def on_message(self, message):
		p = self.socket_io_message(message)
		logging.debug(f'receive packet: {p}')

	def on_error(self, ws, error):
		logging.error(f'ERROR: {error}')

	def on_close(self):
		# AmitAvr
		self.ws.connected = False

		logging.info('close socket')
		if self.send_message_thread:
			self.send_message_thread.stop()
			self.send_message_thread.join()
			self.send_message_thread = None

	def parse_polling_packet(self, data):
		rv = []
		if len(data) == 0:
			return rv
		i = 0
		l = 0
		while i < len(data):
			if data[i] == '\x00':
				i += 1
				l = 0
				while data[i] != '\xFF':
					l = l * 10 + ord(data[i])
					i += 1
				i += 1

				rv.append(self.socket_io_message(data[i:i + l], parse_directly=True))
				i += l
			else:
				break
		return rv

	def socket_io_message(self, data, parse_directly=False):
		rv = SIOMessage()
		rv.engine_io = ord(data[0]) - 48
		if rv.engine_io in [0, 2, 3]:
			# rv.socket_io = 0
			i = 1
		else:
			rv.socket_io = ord(data[1]) - 48
			i = 2
			if rv.engine_io == 4 and rv.socket_io == 3:
				rv.socket_io_add = 0
				while i < len(data) and data[i] in '1234567890':
					rv.socket_io_add = rv.socket_io_add * 10 + ord(data[i]) - 48
					i += 1
		rv.message = data[i:]
		if parse_directly:
			rv.parse()
		else:
			self.raw_messages_queue.put(rv)
		return rv

	def message_worker(self, msg):
		msg.parse()
		if msg.engine_io == 4:
			if msg.socket_io in [2, 3]:
				if msg.socket_io_add is not None and msg.socket_io_add in self._emit_callbacks:
					self._emit_callbacks[msg.socket_io_add](self, msg.message, msg)
					self._emit_callbacks.pop(msg.socket_io_add, None)
				elif isinstance(msg.message, list) and isinstance(
					msg.message[0], six.string_types):
					cid = msg.message[0]
					if cid in self.callbacks:
						if isinstance(self.callbacks[cid], list):
							for c in self.callbacks[cid]:
								if len(msg.message) > 1:
									c(self, msg.message[1], msg)
								else:
									c(self, None, msg)
						else:
							if len(msg.message) > 1:
								self.callbacks[cid](self, msg.message[1], msg)
							else:
								self.callbacks[cid](self, None, msg)
			elif msg.socket_io == 0:
				if self.on_connect:
					self.on_connect(self)

	def send_message(self, msg):
		self.send_messages_queue.put(msg)
		# self.ws.send(str(msg))

	def on(self, callback_id, callback):
		if callback_id in self.callbacks:
			if isinstance(self.callbacks[callback_id], list):
				self.callbacks[callback_id].append(callback)
			else:
				self.callbacks[callback_id] = [self.callbacks[callback_id], callback]
		else:
			self.callbacks[callback_id] = [callback, ]

	def emit(self, data, callback=None):
		if callback:
			msg = SIOMessage(4, 2, data, parsed=True, socket_io_add=self._emit_callback_id)
			self._emit_callbacks[self._emit_callback_id] = callback
			self._emit_callback_id += 1
		else:
			msg = SIOMessage(4, 2, data, parsed=True)
		self.send_message(msg)