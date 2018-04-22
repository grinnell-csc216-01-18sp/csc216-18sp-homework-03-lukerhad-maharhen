##
# CSC 216 (Spring 2018)
# Reliable Transport Protocols (Homework 3)
#
# Sender-receiver base classes (v1).  You should not modify this file as part
# of your homework.
##

import Queue



class BaseSender(object):
	def __init__(self, app_interval, timeout, attempts):
		self.input_queue = Queue.Queue()
		self.output_queue = Queue.Queue()
		self.app_interval = app_interval
		self.timeout = timeout
		self.attempts = attempts
		self.app_timer = 0
		self.app_count = 0
		self.custom_enabled = False
		self.custom_interval = 0
		self.custom_timer = 0

	def send_to_network(self, seg):
		self.output_queue.put(seg)

	def step(self):
		self.app_timer += 1
		if self.app_timer >= self.app_interval and not self.check_sending():
			self.app_count += 1
			self.receive_from_app('message {}'.format(self.app_count))
			self.app_timer = 0
		if not self.input_queue.empty():
			self.receive_from_network(self.input_queue.get())
		if self.custom_enabled:
			self.custom_timer += 1
			if self.custom_timer >= self.custom_interval:
				self.on_interrupt()
				self.custom_timer = 0
				self.custom_enabled = False

	def start_timer(self, interval):
		self.custom_enabled = True
		self.custom_interval = interval
		self.custom_timer = 0

	def receive_from_app(self, msg):
		pass

	def receive_from_network(self, seg):
		pass

	def on_interrupt(self):
		pass

	def check_sending(self):
		return False

	def stop_timer(self):
		self.custom_enabled = False




class BaseReceiver(object):
	def __init__(self):
		self.input_queue = Queue.Queue()
		self.output_queue = Queue.Queue()
		self.received_count = 0
		pass

	def step(self):
		if not self.input_queue.empty():
			self.receive_from_client(self.input_queue.get())

	def send_to_network(self, seg):
		self.output_queue.put(seg)

	def send_to_app(self, msg):
		self.received_count += 1
		print('Message received ({}): {}'.format(self.received_count, msg))

	def receive_from_client(self, seg):
		pass
