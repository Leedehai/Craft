#!/usr/bin/env python
# Copyright: see README and LICENSE under the project root directory.
# Author: Haihong Li
#
# File: recorder.py
# ---------------------------
# Recorder.

import asyncore
import socket
import re, json

HEADER_REGEX = re.compile(r"\[\[(\w+)\]\]([^(\[\[)]*)")
def parseData(string):
    data_dict = {}
    for match in HEADER_REGEX.finditer(string):
        header = match.group(1).strip()
        payload = match.group(2).strip()
        if header == "time":
            start_finish_elapsed = payload.split(';')
            payload = {
                "proc": start_finish_elapsed[0].split(','),
                "real": start_finish_elapsed[1].split(',')
            }
        data_dict[header] = payload
    print(json.dumps(data_dict, indent=2))   

class EchoHandler(asyncore.dispatcher):
    def handle_read(self):
        data = self.recv(9580)
        if not data:
            return
        parseData(data.decode('utf-8'))

class EchoServer(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            handler = EchoHandler(sock)

server = EchoServer('localhost', 8081)
asyncore.loop()