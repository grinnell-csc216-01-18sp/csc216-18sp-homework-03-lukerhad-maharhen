##
# CSC 216 (Spring 2018)
# Reliable Transport Protocols (Homework 3)
#
# Main RTP driver (v1).  You should not need to modify this file for the
# homework.
#
# Note: this homework is written using language features that are incompatible
# between versions of python 2 and python 3, namely:
#
# - The module containing the Queue and PriorityQueue classes is called
#   Queue (Python 2) or PriorityQueue (Python 3)
# - The super() method used to access the superclass component of an object
#   takes no arguments (Python 3) or a class type and the object in question
#   (Python 2)
#
# This version of the Python code uses Python 2 conventions.  If you are using
# Python 3, you can either modify the code by hand or use the `2to3` program
# (included in most Python distributions) which produces diffs of Python 2
# source file that can be applied to produce Python 3-compatible source.
##

from __future__ import print_function

from sendrecv import NaiveSender, NaiveReceiver, \
	AltSender, AltReceiver, \
	GBNSender, GBNReceiver

import argparse
import Queue
import random

# Application defaults---modify these via command-line flags upon invocation
APP_DELAY = 2
NET_DELAY = 1
CORR_PROB = 0.25
DROP_PROB = 0.0
ATTEMPTS = 5
TIMEOUT = 10


# N.B. the queue.Queue class does not provide a peek method, so we crack its
#      abstraction to implement such functionality
def peek(q):
	return q.queue[0]


class Simulation:
	def __init__(self, sender, receiver, net_delay, corr_prob, drop_prob, timeout, attempts):
		self.sender = sender
		self.receiver = receiver
		self.net_delay = net_delay
		self.corr_prob = corr_prob
		self.drop_prob = drop_prob
		self.network_queue = Queue.PriorityQueue()

	def push_to_network(self, step, seg):
		# This shit doesn't work as intended
		if random.random() >= self.drop_prob:
			self.network_queue.put((step + self.net_delay, seg))

	def run(self, n):
		# Three-way handshake
		self.sender.initialize_connection()
		for step in range(1, n + 1):
			print('Step {}:'.format(step))

			# 1. Step the sender and receiver
			self.sender.step()
			self.receiver.step()

			# 2. Step the network layer
			if not self.network_queue.empty():
				(timeout, _) = peek(self.network_queue)
				if step >= timeout:
					(_, seg) = self.network_queue.get()
					if random.random() < self.corr_prob:
						seg.msg = '<CORRUPTED>'
					if seg.dst == "sender":
						self.sender.input_queue.put(seg)
					elif seg.dst == "receiver":
						self.receiver.input_queue.put(seg)
					else:
						raise RuntimeError('Unknown destination: {}'.format(seg.dst))
			if not self.sender.output_queue.empty():
				self.push_to_network(step, self.sender.output_queue.get())
			if not self.receiver.output_queue.empty():
				self.push_to_network(step, self.receiver.output_queue.get())

			if step == n - 15:
				print(self.sender.connection_established)
				print(self.receiver.connection_established)
				self.sender.close_connection()



def main():
	parser = argparse.ArgumentParser(
		description='Simulates transportation layer network traffic.')
	parser.add_argument('--app-delay',
						type=int, dest='app_delay', default=APP_DELAY,
						help='delay between application-level messages (default: {})'.format(APP_DELAY))
	parser.add_argument('--net-delay',
						type=int, dest='net_delay', default=NET_DELAY,
						help='network-level segment delay (default: {}'.format(NET_DELAY))
	parser.add_argument('--corr',
						type=float, dest='corr_prob', default=CORR_PROB,
						help='liklihood of segment corruption (default: {})'.format(CORR_PROB))
	parser.add_argument('--drop',
						type=float, dest='drop_prob', default=DROP_PROB,
						help='likelihood of dropped packets (default: {})'.format(DROP_PROB))
	parser.add_argument('--timeout',
						type=int, dest='timeout', default=TIMEOUT,
						help='timeout for sender (default: {})'.format(TIMEOUT))
	parser.add_argument('--attempts',
						type=int, dest='attempts', default=ATTEMPTS,
						help='number of attempts for sender to establish connection (default: {})'.format(ATTEMPTS))
	parser.add_argument('steps', type=int, help='number of steps to run the simulation')
	parser.add_argument('protocol', help='protocol to use [naive|alt|gbn]')
	args = parser.parse_args()
	if args.protocol == 'naive':
		sender, receiver = NaiveSender(args.app_delay, args.timeout, args.attempts), NaiveReceiver()
	elif args.protocol == 'alt':
		sender, receiver = AltSender(args.app_delay, args.timeout, args.attempts), AltReceiver()
	elif args.protocol == 'gbn':
		sender, receiver = GBNSender(args.app_delay, args.timeout, args.attempts), GBNReceiver()
	else:
		raise RuntimeError('Unknown protocol specified: {}'.format(args.protocol))
	sim = Simulation(sender, receiver, args.net_delay, args.corr_prob, args.drop_prob, args.timeout, args.attempts)
	sim.run(args.steps)


if __name__ == '__main__':
	main()
