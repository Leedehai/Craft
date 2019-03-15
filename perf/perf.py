#!/usr/bin/env python

import os, sys, time
import subprocess

class cd:
    def __init__(self, to_path):
        self.to_path = to_path
    def __enter__(self):
        self.original_path = os.getcwd()
        os.chdir(self.to_path)
    def __exit__(self, etype, value, traceback):
        os.chdir(self.original_path)

def run(filename):
    print("run: %-10s observed commands: %s" % (filename, int(filename.split('.')[0])))
    start_time = time.time()
    with open(os.devnull, 'w') as DEVNULL: # python2 doesn't define subprocess.DENULL
        p = subprocess.Popen(("make -f %s" % filename).split(), stdout=DEVNULL)
        p.wait()
    without_craft_time = time.time() - start_time

    try:
        pid = subprocess.check_output("lsof -t -i :8081", shell=True).decode()
    except subprocess.CalledProcessError: # no process is using port
        pid = ""
    if len(pid):
        subprocess.call("kill %s" % pid, shell=True)
    with open(os.devnull, 'w') as DEVNULL: # python2 doesn't define subprocess.DENULL
        start_time = time.time()
        p = subprocess.Popen(("../craft.py -- -f %s" % filename).split(), stdout=DEVNULL)
        p.wait()
    with_craft_time = time.time() - start_time
    time.sleep(1) # ensure recorder server terminates

    return without_craft_time, with_craft_time

def main():
    makefiles = sorted(
        [ filename for filename in os.listdir(".") if filename.endswith(".make") ],
        key=lambda filename : int(filename.split('.')[0])
    )

    num = min(int(sys.argv[1]), len(makefiles)) if (len(sys.argv) >= 2) else len(makefiles)

    # ensure observer is compiled
    if os.path.isfile("../observer"):
        os.remove("../observer")
    subprocess.call("../craft.py --prepare-observer", shell=True)

    times = []
    for filename in makefiles[:num]:
        without_craft_time, with_craft_time = run(filename)
        times.append((
            filename, without_craft_time, with_craft_time,
            (with_craft_time - without_craft_time) * 1.0 / without_craft_time)
        )
    print("filename   |  make      craft   overhead")
    print("-----------|-----------------------------")
    for item in times:
        print("%-10s |  %06.3f,  %06.3f,  %.2f %%" % (
            item[0], item[1], item[2], 100 * item[3]))

if __name__ == "__main__":
    sys.exit(main())