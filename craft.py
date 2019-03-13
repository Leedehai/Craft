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

class cd:
    def __init__(self, to_path):
        self.to_path = to_path
    def __enter__(self):
        self.original_path = os.getcwd()
        os.chdir(self.to_path)
    def __exit__(self, etype, value, traceback):
        os.chdir(self.original_path)

def main():
    this_dir = os.path.dirname(__file__)
    if not os.path.isfile(os.path.join(this_dir, "observer")):
        with cd(this_dir):
            subprocess.call("make -f utils/auto.make".split())
    recorder_proc = subprocess.Popen("./recorder.py")
    time.sleep(5) # placeholder for subprocess calling 'make ...'
    recorder_proc.terminate()

if __name__ == "__main__":
    sys.exit(main())