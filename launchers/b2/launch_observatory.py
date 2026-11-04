# Copyright 2026 Aayush Kadam
# SPDX-License-Identifier: Apache-2.0
"""Serve the B2 static app locally; no scientific dataset is required."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import socket,sys,webbrowser
class Server(ThreadingHTTPServer):
    allow_reuse_address=False
    def server_bind(self):
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);parser.add_argument('--port',type=int,default=8870);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    root=args.directory.resolve()
    if not 0<=args.port<=65535:parser.error('Port must be between 0 and 65535.')
    if not (root/'index.html').is_file() or not (root/'assets').is_dir():print('Build missing: expected index.html and assets beside the launcher, or use --directory.',file=sys.stderr);return 1
    try:server=Server(('127.0.0.1',args.port),partial(SimpleHTTPRequestHandler,directory=str(root)))
    except OSError as error:print('Could not listen on the local port:',error,file=sys.stderr);return 1
    url=f'http://127.0.0.1:{server.server_port}/';print(f'Serving {root}\nOpen {url}\nCtrl+C stops the local server. No JPL API requests.',flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:server.server_close()
    return 0
if __name__=='__main__':raise SystemExit(main())
