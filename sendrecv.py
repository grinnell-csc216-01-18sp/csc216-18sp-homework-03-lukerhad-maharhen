##
# CSC 216 (Spring 2018)
# Reliable Transport Protocols (Homework 3)
#
# Sender-receiver code for the RDP simulation program.  You should provide
# your implementation for the homework in this file.
#
# Your various Sender implementations should inherit from the BaseSender
# class which exposes the following important methods you should use in your
# implementations:
#
# - sender.send_to_network(seg): sends the given segment to network to be
#   delivered to the appropriate recipient.
# - sender.start_timer(interval): starts a timer that will fire once interval
#   steps have passed in the simulation.  When the timer expires, the sender's
#   on_interrupt() method is called (which should be overridden in subclasses
#   if timer functionality is desired)
#
# Your various Receiver implementations should also inherit from the
# BaseReceiver class which exposes the following important methods you should
# use in your implementations:
#
# - sender.send_to_network(seg): sends the given segment to network to be
#   delivered to the appropriate recipient.
# - sender.send_to_app(msg): sends the given message to receiver's application
#   layer (such a message has successfully traveled from sender to receiver)
#
# Subclasses of both BaseSender and BaseReceiver must implement various methods.
# See the NaiveSender and NaiveReceiver implementations below for more details.
##

from sendrecvbase import BaseSender, BaseReceiver
from copy import deepcopy
import Queue
import random


def peek(q):
	return q.queue[0]


def flip(i):
	if i == 0:
		return 1
	else:
		return 0


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


class NaiveSender(BaseSender):
	def __init__(self, app_interval, timeout, attempts):
		super(NaiveSender, self).__init__(app_interval, timeout, attempts)

	def receive_from_app(self, msg):
		seg = Segment(msg, 'receiver')
		self.send_to_network(seg)

	def receive_from_network(self, seg):
		pass  # Nothing to do!

	def on_interrupt(self):
		pass  # Nothing to do!


class NaiveReceiver(BaseReceiver):
	def __init__(self):
		super(NaiveReceiver, self).__init__()

	def receive_from_client(self, seg):
		self.send_to_app(seg.msg)


class AltSender(BaseSender):
	def __init__(self, app_interval, timeout, attempts):
		super(AltSender, self).__init__(app_interval, timeout, attempts)
		self.cur_sequence_number = 0
		self.cur_message = None

	def receive_from_app(self, msg):
		seg = Segment(msg, 'receiver', self.cur_sequence_number)
		self.cur_message = deepcopy(seg)
		print('Initial attempt to send packet with sequence ' + str(self.cur_message.seq))
		self.send_to_network(seg)
		self.start_timer(self.timeout)
		self.disallow_app_messages()

	def receive_from_network(self, seg):
		if seg.SYN == 1 or seg.FIN == 1 or self.closing_state == 'FIN_WAIT_2':
			self.connection_management(seg)
		else:
			# Correct sequence number, ACK received, and message not corrupted
			if (seg.seq == self.cur_sequence_number) and (seg.status == 'ACK') and (seg.msg != '<CORRUPTED>'):
				print('ACK on sequence ' + str(seg.seq))
				self.cur_sequence_number = flip(self.cur_sequence_number)
				if not self.closing:
                                        self.allow_app_messages()
				self.stop_timer()
			# Premature timeout
			elif seg.seq != self.cur_sequence_number and seg.status != 'NAK':
				print('premature timeout')
			elif seg.msg == '<CORRUPTED>':
				print('sender received corrupted packet')
				self.attempt_send_packet()
			# Resend required
			else:
				print('resending because NAK')
				self.attempt_send_packet()

	# Checks for next message and sends it, as well as starting the timeout timer
	def attempt_send_packet(self):
                if not self.closing:
                        temp_message = deepcopy(self.cur_message)
                        print('attempting to send packet with sequence ' + str(
                                self.cur_message.seq) + ' and message ' + self.cur_message.msg)
                        self.send_to_network(temp_message)
                        self.start_timer(self.timeout)

	def on_interrupt(self):
                if not self.closing:
                        # Resend current packet on timeout
                        print('Timeout occurred, resending')
                        self.attempt_send_packet()


class AltReceiver(BaseReceiver):
	def __init__(self):
		super(AltReceiver, self).__init__()
		self.cur_sequence_number = 0

	def receive_from_client(self, seg):
		if seg.SYN == 1 or seg.FIN == 1 or self.closing_state == 'FIN_WAIT_2':
			self.connection_management(seg)
		else:
			if (seg.msg != '<CORRUPTED>') and (seg.seq == self.cur_sequence_number):
				print('received packet with sequence ' + str(seg.seq))
				self.send_to_app(seg.msg)
				seg = Segment('foo', 'sender', seg.seq, 'ACK')
				self.cur_sequence_number = flip(self.cur_sequence_number)
			# Detected duplicate packet so we resend ACK
			elif (seg.msg != '<CORRUPTED>') and (seg.seq != self.cur_sequence_number):
				print('received duplicate packet with sequence ' + str(seg.seq))
				seg = Segment('foo', 'sender', seg.seq, 'ACK')
			elif seg.msg == '<CORRUPTED>':
				print('receiver received corrupted packet')
				seg = Segment('foo', 'sender', 0, 'NAK')
			self.send_to_network(seg)
		

class GBNSender(BaseSender):
	def __init__(self, app_interval, timeout, attempts):
		super(GBNSender, self).__init__(app_interval, timeout, attempts)
		self.oldest_seq = self.initial_sequence
		self.next_seq_number = self.initial_sequence + 1
		self.max_packets_in_pipe = 3
		self.packets_sending = Queue.Queue()

	def receive_from_app(self, msg):
		if self.packets_sending.qsize() == 0:
			# Start the timer for this as the oldest packet
			self.start_timer(self.timeout)
		seg = Segment(msg, 'receiver', self.next_seq_number)
		self.next_seq_number += 1
		self.packets_sending.put(seg)
		print('Sender sending sequence number ' + str(seg.seq))
		self.send_to_network(deepcopy(seg))
		# If queue is full, disallow app messages
		if self.packets_sending.qsize() == self.max_packets_in_pipe:
			self.disallow_app_messages()

	def receive_from_network(self, seg):
		if seg.SYN == 1 or seg.FIN == 1 or self.closing_state == 'FIN_WAIT_2':
			self.connection_management(seg)
		else:
			if seg.seq == self.oldest_seq and seg.msg != '<CORRUPTED>':
				print('Sender received ACK for sequence number ' + str(seg.seq))
			elif (seg.msg != '<CORRUPTED>') and (seg.status == 'ACK'):
				print('Sender received ACK for sequence number ' + str(seg.seq))
				self.oldest_seq = seg.seq
				# Remove all packets from the window that have been ACK'd
				while not self.packets_sending.empty() and peek(self.packets_sending).seq <= seg.seq:
					self.packets_sending.get()
				if not self.packets_sending.empty() and not self.closing:
					self.start_timer(self.timeout)
				if not self.closing:
					self.allow_app_messages()

			else:
				print('Segment messages was {}'.format(seg.msg))

	def on_interrupt(self):
                if not self.closing:
                        print('Sender timeout; resending all packets')
                        for seg in list(self.packets_sending.queue):
                                self.send_to_network(deepcopy(seg))
                        self.stop_timer()
                        self.start_timer(self.timeout)

	def update_initial_sequence(self):
		self.oldest_seq = self.initial_sequence
		self.next_seq_number = self.initial_sequence + 1


class GBNReceiver(BaseReceiver):
	def __init__(self):
		super(GBNReceiver, self).__init__()
		self.last_sequence_received = self.initial_sequence

	def receive_from_client(self, seg):
		if seg.SYN == 1 or seg.FIN == 1 or self.closing_state == 'FIN_WAIT_2':
			self.connection_management(seg)
		else:
			if seg.seq == (self.last_sequence_received + 1) and seg.msg != '<CORRUPTED>':
				print('Receiver received sequence number ' + str(seg.seq) + '. Sending ACK...')
				self.last_sequence_received = seg.seq
				response = Segment('foo', 'sender', seg.seq, 'ACK')
				self.send_to_network(response)
				self.send_to_app(seg.msg)
			else:
				print('Bad segment with message {}, sequence {}. Internal sequence is {}'.format(seg.msg, seg.seq, self.last_sequence_received))
				print('Receiver resending ACK for sequence number ' + str(self.last_sequence_received))
				response = Segment('foo', 'sender', self.last_sequence_received, 'ACK')
				self.send_to_network(response)

	def update_initial_sequence(self):
		self.last_sequence_received = self.initial_sequence

