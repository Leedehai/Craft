#!/usr/bin/env python
# Copyright: see README and LICENSE under the project root directory.
# Author: Haihong Li
#
# File: craft.py
# ---------------------------
# Top-level manager.

import os, sys
import subprocess
import time, signal

def main():
    this_dir = os.path.dirname(__file__)
    if not os.path.isfile(os.path.join(this_dir, "observer")):
        subprocess.call("cd %s && make -f auto.make && cd .." % this_dir, shell=True)
    recorder_proc = subprocess.Popen("./recorder.py")
    time.sleep(5) # placeholder for subprocess calling 'make ...'
    recorder_proc.terminate()

if __name__ == "__main__":
    sys.exit(main())  