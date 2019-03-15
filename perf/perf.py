#!/usr/bin/env python

import os, sys, time
import subprocess

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
        # not elegant, because the process might terminate after getting the PID
        # but before invoking 'kill', and the OS might assign another process
        # to this PID, so we may end up killing the wrong process. But we take
        # the chance - it is only a perf test.
        subprocess.call("kill %s &> /dev/null" % pid, shell=True)
    with open(os.devnull, 'w') as DEVNULL: # python2 doesn't define subprocess.DENULL
        start_time = time.time()
        p = subprocess.Popen(("../craft.py -- -f %s" % filename).split(), stdout=DEVNULL)
        p.wait()
    with_craft_time = time.time() - start_time
    time.sleep(1) # ensure recorder server terminates

    return without_craft_time, with_craft_time

def main():
    makefiles = sorted([
            filename for filename in os.listdir(".")
            if filename.endswith(".make") and filename[0].isdigit()
        ],
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