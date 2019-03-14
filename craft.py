#!/usr/bin/env python
# Copyright: see README and LICENSE under the project root directory.
# Author: Haihong Li
#
# File: craft.py
# ---------------------------
# Top-level manager.

import os, sys
import subprocess
import time, signal, socket
import argparse

RECORDER_HOST = "localhost"
RECORDER_PORT = 8081

class cd:
    def __init__(self, to_path):
        self.to_path = to_path
    def __enter__(self):
        self.original_path = os.getcwd()
        os.chdir(self.to_path)
    def __exit__(self, etype, value, traceback):
        os.chdir(self.original_path)

TIME_GRANULARITY, MAX_TIME = 0.05, 2.00
def wait_server_ready(): 
    t, connected = 0, False
    while t <= MAX_TIME: # spinning wait
        s = socket.socket()
        try:
            s.connect((RECORDER_HOST, RECORDER_PORT))
            connected = True
            break
        except socket.error as e:
            s.close()
            time.sleep(TIME_GRANULARITY)
            t += TIME_GRANULARITY
    s.close()
    if not connected:
        print("[Error] craft: unable to connect server %s:%d within %.2f sec" % (
            RECORDER_HOST, RECORDER_PORT, MAX_TIME))
        return False
    return True

def work(args, make_cmd):
    this_dir = os.path.dirname(__file__)
    # no need to check 'make_cmd' against injection hazard - this is user's Make command and
    # users can wrack their computer with that command all they want
    make_working_dir = get_make_working_dir(make_cmd)
    if not make_working_dir:
        return 1
    if False == sanitize_against_injection(args.write_log):
        print("[Error] illegal log filename: %s" % args.write_log)
        return 1
    make_cmd_with_observer = "%s %s" % (
        make_cmd, "OBSERVER=%s/observer" % os.path.relpath(this_dir, make_working_dir))

    with cd(this_dir): # ensure up-to-date observer
        with open(os.devnull, 'w') as DEVNULL: # Python2.7 doesn't have subprocess.DEVNULL
            subprocess.call("make -f utils/auto.make".split(), stdout=DEVNULL)

    recorder_proc = subprocess.Popen("%s/recorder.py" % this_dir)
    if False == wait_server_ready():
        return 1
    with open(os.devnull, 'w') as DEVNULL: # Python2.7 doesn't have subprocess.DEVNULL
        make_proc = subprocess.Popen(make_cmd_with_observer, shell=True, stdout=DEVNULL, stderr=DEVNULL)
        make_proc.wait()
    if args.write_log:
        print("craft: dump log to %s" % args.write_log)
        subprocess.call("%s/observer :close %s" % (this_dir, args.write_log), shell=True)
    else:
        subprocess.call("%s/observer :close", shell=True)
    return 0

def get_make_working_dir(make_cmd):
    if " -C " not in make_cmd:
        return "."
    make_cmd_split = make_cmd.split()
    make_working_dir_index = make_cmd_split.index("-C") + 1
    if make_working_dir_index >= len(make_cmd_split):
        print("[Error] option '-C' is present in Make arguments, but no directory is given")
        return None
    return make_cmd_split[make_working_dir_index]

def sanitize_against_injection(filename):
    # not an exhaustive defense
    if ('|' in filename) or ('&' in filename) or (';' in filename) or (' ' in filename):
        return False
    return True

def sighandler(sig, frame):
    if sig == signal.SIGINT:
        print(" [SIGNAL] SIGINT sent to script")
    elif sig == signal.SIGTERM:
        print(" [SIGNAL] SIGTERM sent to script")
    else:
        print(" [SIGNAL] Signal %d sent to script" % sig)
    sys.exit(1)

def main():
    # Set the signal handlers
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    parser = argparse.ArgumentParser(description="Craft",
                                     epilog="if '-- ..' exists, args after '--' are passed to Make")
    parser.add_argument("-w", "--write-log", metavar='FILENAME', type=str, default=None,
                        help="write log to file (JSON)")
    def preprocess(argv):
        if len(argv) == 0 or ("--" not in argv):
            return argv[1:], []
        delimiter_pos = argv.index("--")
        return argv[1:delimiter_pos], argv[delimiter_pos + 1:]
    # separate args for this script and args for Make
    this_args, make_args = preprocess(sys.argv)
    args = parser.parse_args(this_args)
    if ("-h" in make_args) or ("--help" in make_args):
        print("Use 'make -h' for Make's help")
        return 0 # do not do anything
    make_cmd = ' '.join(['make'] + make_args)
    print("execute: %s" % make_cmd)
    return work(args, make_cmd)

if __name__ == "__main__":
    sys.exit(main())