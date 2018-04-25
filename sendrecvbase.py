##
# CSC 216 (Spring 2018)
# Reliable Transport Protocols (Homework 3)
#
# Sender-receiver base classes (v1).  You should not modify this file as part
# of your homework.
##

import Queue
import random


class Segment:
	def __init__(self, msg, dst, seq=None, status=None, SYN=0, FIN=0):
		# Sequence bit of the packet
		self.seq = seq
		# Status of the packet if it is a confirmation (i.e. 'ACK' or "NAK")
		self.status = status
		self.msg = msg
		self.dst = dst
		self.SYN = SYN
		self.FIN = FIN


class BaseSender(object):
	def __init__(self, app_interval, timeout, attempts):
		self.input_queue = Queue.Queue()
		self.output_queue = Queue.Queue()
		self.app_interval = app_interval
		self.timeout = timeout
		self.max_attempts = attempts
		self.app_timer = 0
		self.app_count = 0
		self.custom_enabled = False
		self.custom_interval = 0
		self.custom_timer = 0
		self.connection_established = False
		self.connection_timer_enabled = False
		self.connection_timer = 0
		self.connection_interval = 0
		self.connection_attempts_counter = 0
		self.closing_timer_enabled = False
		self.closing_timer = 0
		self.closing_timer_interval = 30
		self.closing_state = None
		self.initial_sequence = 0
		self.client_isn = 0

	def send_to_network(self, seg):
		self.output_queue.put(seg)

	def step(self):
		self.app_timer += 1
		if self.connection_established:
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
		if self.connection_timer_enabled:
			self.connection_timer += 1
			if self.connection_timer >= self.connection_interval:
				print('Connection timeout on attempt {}'.format(self.connection_attempts_counter))
				self.connection_interrupt()
				self.connection_timer = 0
				self.connection_timer_enabled = False
		if self.closing_timer_enabled:
			self.closing_timer += 1
			if self.closing_timer >= self.closing_interval:
				self.connection_established = False
				self.closing_timer = 0
				self.closing_timer_enabled = False

	def start_timer(self, interval):
		self.custom_enabled = True
		self.custom_interval = interval
		self.custom_timer = 0

	def start_connection_timer(self, interval):
		self.connection_timer_enabled = True
		self.connection_interval = interval
		self.connection_timer = 0

	def start_closing_timer(self):
		self.closing_timer_enabled = True
		self.closing_timer = 0

	def receive_from_app(self, msg):
		pass

	def receive_from_network(self, seg):
		pass

	def on_interrupt(self):
		pass

	def connection_interrupt(self):
		self.connection_attempts_counter += 1
		if self.connection_attempts_counter < self.max_attempts:
			self.initialize_connection()

	def check_sending(self):
		return False

	def stop_timer(self):
		self.custom_enabled = False

	def stop_connection_timer(self):
		self.connection_timer_enabled = False

	def stop_closing_timer(self):
		self.closing_timer_enabled = False

	def initialize_connection(self):
		self.start_connection_timer(self.timeout)
		self.initial_sequence = random.randint(0, 2**32-1)
		seg = Segment(None, 'receiver', self.initial_sequence, None, 1)
		self.send_to_network(seg)

	def close_connection(self):
		self.closing_state = 'FIN_WAIT_1'
		seg = Segment(None, 'receiver', None, None, None, 1)
		self.send_to_network(seg)

	def connection_management(self, seg):
		if seg.SYN == 1:
			self.connection_established = True
			client_isn = seg.status - 1
			# This is where we would keep track of the server_isn outside the context of the simulation
			self.initial_sequence = client_isn
			print('Connection established with client initial sequence number {}'.format(self.initial_sequence))
			self.stop_connection_timer()
			self.update_initial_sequence()
		elif seg.FIN == 1 or self.closing_state == 'FIN_WAIT_2':
			if self.closing_state == 'FIN_WAIT_1' and seg.status == 'ACK':
				self.closing_state = 'FIN_WAIT_2'
			elif self.closing_state == 'FIN_WAIT_2':
				seg = Segment(None, 'receiver', None, 'ACK', None, 1)
				self.send_to_network(seg)
				self.start_closing_timer()
			elif self.closing_state is None:
				seg = Segment(None, 'receiver', None, 'ACK', None, 1)
				self.send_to_network(seg)
				self.cleanup()
			else:
				self.stop_closing_timer()
				self.connection_established = False

	def cleanup(self):
		# What you would call between sending the ACK for the FIN from a client and sending a FIN to the client
		seg = Segment(None, 'receiver', None, None, None, 1)
		self.send_to_network(seg)

	def update_initial_sequence(self):
		pass


class BaseReceiver(object):
	def __init__(self):
		self.input_queue = Queue.Queue()
		self.output_queue = Queue.Queue()
		self.received_count = 0
		self.connection_established = False
		self.closing_state = None
		self.closing_timer_enabled = False
		self.closing_timer = 0
		self.closing_timer_interval = 30
		self.initial_sequence = 0

	def step(self):
		if not self.input_queue.empty():
			self.receive_from_client(self.input_queue.get())
		if self.closing_timer_enabled:
			self.closing_timer += 1
			if self.closing_timer >= self.closing_interval:
				self.connection_established = False
				self.closing_timer = 0
				self.closing_timer_enabled = False

	def send_to_network(self, seg):
		self.output_queue.put(seg)

	def send_to_app(self, msg):
		self.received_count += 1
		print('Message received ({}): {}'.format(self.received_count, msg))

	def receive_from_client(self, seg):
		pass

	def stop_closing_timer(self):
		self.closing_timer_enabled = False

	def close_connection(self):
		self.closing_state = 'FIN_WAIT_1'
		seg = Segment(None, 'sender', None, None, None, 1)
		self.send_to_network(seg)

	def connection_management(self, seg):
		if seg.SYN == 1:
			print('Connection request received')
			server_isn = random.randint(0, 2 ** 32 - 1)
			self.initial_sequence = seg.seq
			print('Connection established with sever initial sequence number {}'.format(self.initial_sequence))
			seg = Segment('', 'sender', server_isn, self.initial_sequence + 1, 1)
			self.send_to_network(seg)
			self.update_initial_sequence()
		elif seg.FIN == 1 or self.closing_state == 'FIN_WAIT_2':
			if self.closing_state == 'FIN_WAIT_1' and seg.status == 'ACK':
				self.closing_state = 'FIN_WAIT_2'
			elif self.closing_state == 'FIN_WAIT_2':
				seg = Segment(None, 'sender', None, 'ACK', None, 1)
				self.send_to_network(seg)
				self.start_closing_timer()
			elif self.closing_state is None:
				seg = Segment(None, 'receiver', None, 'ACK', None, 1)
				self.send_to_network(seg)
				self.cleanup()
			else:
				self.stop_closing_timer()
				self.connection_established = False

	def cleanup(self):
		# What you would call between sending the ACK for the FIN from a client and sending a FIN to the client
		seg = Segment(None, 'sender', None, None, None, 1)
		self.send_to_network(seg)

	def update_initial_sequence(self):
		pass
