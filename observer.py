#!/usr/bin/env python
# Copyright: see README and LICENSE under the project root directory.
# Author: Haihong Li
#
# File: observer.py
# ---------------------------
# Observer. The script should be simple, to reduce runtime overhead.

import sys, signal
import subprocess

def sighandler(sig, frame):
    if sig == signal.SIGINT:
        print(" [SIGNAL] SIGINT sent to script")
    elif sig == signal.SIGTERM:
        print(" [SIGNAL] SIGTERM sent to script")
    else:
        print(" [SIGNAL] Signal %d sent to script" % sig)
    sys.exit(1)

def run(command):
    pass

def main():
    # Set the signal handlers
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    
    # Check the command
    command = sys.argv[1:]
    if len(commands) == 0:
        print("[Error] no command")
        return 1
    for arg in command:
        if ('*' in arg) or ('?' in arg) or ('>' in arg) or ('<' in arg)
            or ('|' in arg) or (';' in arg) or ('&' in arg):
            print("[Error] no shell character is allowed: * ? > < | ; &")
    return run(command)

if __name__ == "__main__":
    sys.exit(main())