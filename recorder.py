#!/usr/bin/env python
# Copyright: see README and LICENSE under the project root directory.
# Author: Haihong Li
#
# File: recorder.py
# ---------------------------
# Recorder. It accepts and logs reports sent from observers, prints
# succinct summaries, and dumps logs when it is told to.
# NOTE the log is kept in memory and is not committed to disk until
#      dumping. This is because (1) we want Recorder be fast, i.e.
#      not blocked by disk IO, and (2) we're not interested in data
#      persistency in case of an (unlikely) unexpected power-off.
#
# How to use this file:
# Launch recorder.py
# Open another terminal, run a series of commands:
#   ./observer g++ file.cc -o file
#   ./observer date
#   ./observer sleep 1
#   ./observer :close log.json
# Then kill recorder.py. A log.json file is dumped and you can inspect
# it - it contains the commands you ran and their outputs and exit codes.

# NOTE 'asyncio' library is not in Python until Python 3, but we want
#       to support both Python 2.7 and 3. So, we stick to 'asyncore'.
import asyncore
import socket
import signal
import sys, re, json, time
from utils import formatter

record = {}

RECORDER_HOST = "localhost"
RECORDER_PORT = 8081  # used by observer to send data

COMMAND_CLEAR = ":clear"
COMMAND_CLOSE = ":close"

MAX_PACKET_LEN = 9580
BACK_LOG_SIZE = 32

def dump_log_sync(record_dict, dump_log_command):
    filename = dump_log_command[len(COMMAND_CLOSE):].strip()
    if not filename:
        return
    content_string = json.dumps(record_dict, indent=2, sort_keys=True)
    with open(filename, 'w') as f:
        f.write(content_string + '\n')

HEADER_PAYLOAD_REGEX = re.compile(r"\[\#(\w+)\#\]([^(\[\#)]*)")
def parse_data(data): # parse data (sync)
    data_dict = {}
    for match in HEADER_PAYLOAD_REGEX.finditer(data.decode()):
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
    data_dict = parse_data(data)
    if data_dict["cmd"].startswith(COMMAND_CLOSE):
        dump_log_sync(record, data_dict["cmd"])
        sys.exit(0)
    if data_dict["cmd"].strip() == COMMAND_CLEAR:
        record = {}
        return
    record[time.time()] = data_dict
    processed_line, category = formatter.process(data_dict["cmd"])
    print("%s" % processed_line)

class Handler(asyncore.dispatcher):
    def handle_read(self):
        data = self.recv(MAX_PACKET_LEN)
        if not data:
            return
        handle_data(data)

class EventDrivenServer(asyncore.dispatcher):
    def __init__(self, host, port):
        try:
            asyncore.dispatcher.__init__(self)
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            self.set_reuse_addr()
            s = self.bind((host, port))
            self.listen(BACK_LOG_SIZE)
        except Exception as e:
            print("[Error] recorder: error to establish server. Port %s:%d already in use?" % (host, port))
            sys.exit(1)
        print("craft: recorder server established at %s:%d" % (host, port))

    def handle_accept(self):
        pair = self.accept()
        if pair == None:
            return
        sock, addr = pair
        handler = Handler(sock)

def run():
    server = EventDrivenServer(RECORDER_HOST, RECORDER_PORT)
    asyncore.loop()

def sighandler(sig, frame):
    if sig == signal.SIGTERM:
        sys.exit(0)
    # abnormal exit
    if sig == signal.SIGINT:
        print(" [SIGNAL] recorder: SIGINT sent to script")
    elif sig == signal.SIGABRT:
        print(" [SIGNAL] recorder: SIGABRT sent to script")
    else:
        print(" [SIGNAL] recorder: signal %s sent to script" % sig)
    sys.exit(1)

if __name__ == "__main__":
    # Set the signal handlers
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGABRT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    run()