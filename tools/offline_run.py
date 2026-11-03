"""Reproduce the cached experiment with DNS and outbound connections prohibited."""
from pathlib import Path
import runpy
import socket
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def forbidden(*args, **kwargs):
    raise RuntimeError('Network forbidden during offline reproduction')

socket.create_connection = forbidden
socket.getaddrinfo = forbidden
socket.socket.connect = forbidden
runpy.run_module('science.run',run_name='__main__')
