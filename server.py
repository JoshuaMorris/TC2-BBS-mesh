#!/usr/bin/env python3

"""
TC²-BBS Server for Meshtastic by TheCommsChannel (TC²)
Date: 07/14/2024
Version: 0.1.6

Description:
The system allows for mail message handling, bulletin boards, and a channel
directory. It uses a configuration file for setup details and an SQLite3
database for data storage. Mail messages and bulletins are synced with
other BBS servers listed in the config.ini file.
"""

import logging
import time

from config_init import initialize_config, get_interface, init_cli_parser, merge_config
from db_operations import initialize_database
from js8call_integration import JS8CallClient
from message_processing import on_receive
from pubsub import pub

# General logging setup
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# JS8Call logging setup
js8call_logger = logging.getLogger('js8call')
js8call_logger.setLevel(logging.DEBUG)
js8call_handler = logging.StreamHandler()
js8call_handler.setLevel(logging.DEBUG)
js8call_formatter = logging.Formatter('%(asctime)s - JS8Call - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
js8call_handler.setFormatter(js8call_formatter)
js8call_logger.addHandler(js8call_handler)

def display_banner():
	banner = """
████████╗ ██████╗██████╗       ██████╗ ██████╗ ███████╗
╚══██╔══╝██╔════╝╚════██╗      ██╔══██╗██╔══██╗██╔════╝
   ██║   ██║      █████╔╝█████╗██████╔╝██████╔╝███████╗
   ██║   ██║     ██╔═══╝ ╚════╝██╔══██╗██╔══██╗╚════██║
   ██║   ╚██████╗███████╗      ██████╔╝██████╔╝███████║
   ╚═╝    ╚═════╝╚══════╝      ╚═════╝ ╚═════╝ ╚══════╝
Meshtastic Version
"""
	print(banner)

def initialize_js8call_client(interface):
	try:
		js8call_client = JS8CallClient(interface)
		js8call_client.logger = js8call_logger
		if js8call_client.db_conn:
			js8call_client.connect()
		return js8call_client
	except Exception as e:
		logger.error(f"Error initializing JS8Call client: {e}")
		return None


def initialize_meshtastic_interface(system_config):
	try:
		interface = get_interface(system_config)
		interface.bbs_nodes = system_config['bbs_nodes']
		interface.allowed_nodes = system_config['allowed_nodes']
		return interface
	except KeyError as e:
		logger.error(f"Configuration missing required key: {e}")
		sys.exit(1)
	except Exception as e:
		logger.error(f"Error initializing Meshtastic interface: {e}")
		sys.exit(1)


def main():
	display_banner()
	args = init_cli_parser()
	config_file = args.config if args.config else None
	system_config = initialize_config(config_file)
	merge_config(system_config, args)

	interface = initialize_meshtastic_interface(system_config)
	logging.info(f"TC²-BBS is running on {system_config['interface_type']} interface...")

	try:
		initialize_database()
	except Exception as e:
		logger.error(f"Database initialization failed: {e}")
		sys.exit(1)

	def receive_packet(packet, interface):
		try:
			on_receive(packet, interface)
		except Exception as e:
			logger.error(f"Error processing received packet: {e}")

	pub.subscribe(receive_packet, system_config['mqtt_topic'])

	js8call_client = initialize_js8call_client(interface)

	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		logger.info("Shutting down the server...")
		if interface:
			interface.close()
		if js8call_client and js8call_client.connected:
			js8call_client.close()


if __name__ == "__main__":
	main()
