from udp import UdpSender
import argparse
from ipaddress import ip_address

parser = argparse.ArgumentParser(
    description="Simple command line interface to turn on/off the Anne Frank installation"
)

parser.add_argument("on_off", type=str.upper, choices=['ON', 'OFF'], help="Whether to turn the targeted device(s) on or off")
parser.add_argument("--ip", required=True, type=ip_address, help="The IP address to send the message to (AFH is 192.168.252.255)")

if __name__ == "__main__":
    args = parser.parse_args()

    u = UdpSender()
    u.send(command=f"INSTALL_{args.on_off.upper()}", target_ip=args.ip)
