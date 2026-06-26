import time
from ipaddress import IPv4Address

from dht.server import Server

server = Server(address=IPv4Address("14.200.8.145"), port=12345)
print("Server intialised")

while True:
    time.sleep(60)