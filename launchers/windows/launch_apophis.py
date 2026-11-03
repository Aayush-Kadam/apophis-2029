# Copyright 2026 Aayush Kadam
# SPDX-License-Identifier: Apache-2.0
"""Serve the static app beside this file, independent of the terminal directory."""
import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import socket
import webbrowser

APP_DIR = Path(__file__).resolve().parent

class LocalHTTPServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR can accept a second listener on an occupied port.
    allow_reuse_address = False
    allow_reuse_port = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

def verify_application(directory: Path) -> None:
    if not (directory/'index.html').is_file():
        raise ValueError('index.html is missing beside this launcher. Extract the entire ZIP first.')
    manifest = json.loads((directory/'snapshots/manifest.json').read_text(encoding='utf-8'))
    expected = manifest.get('files',{}).get('encounter.json')
    if not expected or hashlib.sha256((directory/'snapshots/encounter.json').read_bytes()).hexdigest()!=expected:
        raise ValueError('Frozen snapshot missing or hash mismatch. Extract the complete matching archive again.')

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    if not 0<=args.port<=65535:
        parser.error('Port must be between 0 and 65535.')
    try:
        verify_application(APP_DIR)
        handler=partial(SimpleHTTPRequestHandler,directory=str(APP_DIR))
        server=LocalHTTPServer(('127.0.0.1',args.port),handler)
    except (OSError,ValueError) as exc:
        print(f'APOPHIS could not start: {exc}',file=sys.stderr,flush=True)
        print('If the port is occupied, try START_APOPHIS.cmd --port 8766',file=sys.stderr,flush=True)
        return 1
    url=f'http://127.0.0.1:{server.server_port}/'
    print(f'Application directory: {APP_DIR}',flush=True)
    print(f'Open {url}',flush=True)
    print('Keep this window open. Press Ctrl+C to stop. No JPL API calls are made.',flush=True)
    if not args.no_browser:
        try: webbrowser.open(url)
        except webbrowser.Error: print('Open the printed URL manually.',flush=True)
    try: server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt: print('\nAPOPHIS local server stopped.',flush=True)
    finally: server.server_close()
    return 0

if __name__=='__main__': raise SystemExit(main())
