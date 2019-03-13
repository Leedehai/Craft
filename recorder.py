#!/usr/bin/env python
# Copyright: see README and LICENSE under the project root directory.
# Author: Haihong Li
#
# File: recorder.py
# ---------------------------
# Recorder. It accepts and logs reports sent from observers, prints
# succinct summaries, and dumps logs on exit.
# NOTE the log is kept in memory and is not committed to disk until
#      exit. This is because (1) we want the Recorder be fast, i.e.
#      not blocked by disk IO, and (2) we're not interested in data
#      persistency in case of an unlikely event of powering-off. 

# NOTE 'asyncio' library is not in Python until Python 3, but we want
#       to support both Python 2.7 and 3. So, we stick to 'asyncore'.
import asyncore
import socket
import signal
import sys, re, json, time

record = {}

RECORDER_HOST = "localhost"
RECORDER_PORT = 8081  # used by observer to send data

MAX_PACKET_LEN = 9580
BACK_LOG_SIZE = 32

HEADER_PAYLOAD_REGEX = re.compile(r"\[\#(\w+)\#\]([^(\[\#)]*)")
def parse_data(data): # parse data (sync)
    print data
    data_dict = {}
    for match in HEADER_PAYLOAD_REGEX.finditer(data):
        header = match.group(1).strip()
        payload = match.group(2).strip()
        if header == "time":
            start_finish_elapsed = payload.split(';')
            payload = {
                "proc": start_finish_elapsed[0].split(','),
                "real": start_finish_elapsed[1].split(',')
            }
        data_dict[header] = payload
    return data_dict

def handle_data(data):
    global record
    record[time.time()] = parse_data(data)
    print(json.dumps(record, indent=2, sort_keys=True))

class Handler(asyncore.dispatcher):
    def handle_read(self):
        data = self.recv(MAX_PACKET_LEN)
        if not data:
            return
        handle_data(data)

class EventDrivenServer(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(BACK_LOG_SIZE)

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
    server = EventDrivenServer(RECORDER_HOST, RECORDER_PORT)
    asyncore.loop()

def sighandler(sig, frame):
    if sig == signal.SIGINT:
        print(" [SIGNAL] recorder: SIGINT sent to script")
    elif sig == signal.SIGABRT:
        print(" [SIGNAL] recorder: SIGABRT sent to script")
    sys.exit(1)

if __name__ == "__main__":
    # Set the signal handlers
    signal.signal(signal.SIGINT, onExit)
    signal.signal(signal.SIGABRT, sighandler)
    signal.signal(signal.SIGTERM, onExit)
    run()