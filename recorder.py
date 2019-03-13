#!/usr/bin/env python
# Copyright: see README and LICENSE under the project root directory.
# Author: Haihong Li
#
# File: recorder.py
# ---------------------------
# Recorder.

import asyncore
import socket
import signal
import sys, re, json, time

record = {}

HEADER_REGEX = re.compile(r"\[\[(\w+)\]\]([^(\[\[)]*)")
def parseData(string):
    global record
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
    record[time.time()] = data_dict
    #print(json.dumps(record, indent=2, sort_keys=True))

def getRecord():
    print(json.dumps(record, indent=2))

class Handler(asyncore.dispatcher):
    def handle_read(self):
        data = self.recv(9580)
        if not data:
            return
        parseData(data.decode('utf-8'))

class CraftServer(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(32)

    def handle_accept(self):
        pair = self.accept()
        if pair == None:
            return
        sock, addr = pair
        handler = Handler(sock)

def onExit(sig, frame):
    print(json.dumps(record, indent=2, sort_keys=True))
    sys.exit(1)

def run():
    server = CraftServer('localhost', 8081)
    asyncore.loop()

def sighandler(sig, frame):
    if sig == signal.SIGINT:
        print(" [SIGNAL] recorder: SIGINT sent to script")
    elif sig == signal.SIGABRT:
        print(" [SIGNAL] recorder: SIGABRT sent to script")
    sys.exit(1)

if __name__ == "__main__":
    # Set the signal handlers
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGABRT, sighandler)
    signal.signal(signal.SIGTERM, onExit)
    run()