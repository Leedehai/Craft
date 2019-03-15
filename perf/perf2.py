#!/usr/bin/env python

import os, sys, time, signal
import subprocess
import json

RESULT = "perf2-res.txt"
FILENAME = "bomb.make"

FILE_NOT_FOUND = -1
FILE_NOT_COMPLETE = -2

def run(makefile, tasks, n):
    print("run: %d tasks" % n)
    logname = "log-%d.json" % n

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
    task_list = ' '.join(tasks[:n])
    if os.path.isfile(logname):
        os.remove(logname)
    with open(os.devnull, 'w') as DEVNULL: # python2 doesn't define subprocess.DENULL
        p = subprocess.Popen(("../craft.py -w %s -- -f %s %s -j &> /dev/null" % (logname, makefile, task_list)).split(), stdout=DEVNULL)
        p.wait()

    dt, time_to_wait = 0.05, 1.0
    while not os.path.exists(logname):
        time.sleep(dt)
        time_to_wait -= dt
        if time_to_wait < 0:
            break
    if os.path.isfile(logname):
        time.sleep(0.1) # ensure file is complete
        with open(logname, 'r') as f:
            try:
                num_logged = len(json.load(f))
            except ValueError:
                num_logged = FILE_NOT_COMPLETE
        os.remove(logname)
    else:
        num_logged = FILE_NOT_FOUND

    time.sleep(0.2) # ensure recorder server terminates
    print("%d tasks, num_logged = %d" % (n, num_logged))
    return num_logged

counts = []

def sighandler(sig, frame):
    global counts
    if sig == signal.SIGINT:
        dump_counts(counts)
        sys.exit(0)
    elif sig == signal.SIGTERM:
        print(" [SIGNAL] SIGTERM sent to script")
    else:
        print(" [SIGNAL] Signal %d sent to script" % sig)
    sys.exit(1)

def main():
    signal.signal(signal.SIGINT, sighandler)
    with open(FILENAME, 'r') as f:
        lines = f.readlines()

    tasks = sorted([
        line.split(':')[0].strip() for line in lines
        if len(line) and line.startswith("t") and line[1].isdigit()
    ], key=lambda task : int(task[1:]))
    num_tasks = len(tasks)

    if (len(sys.argv) != 1) and (len(sys.argv) != 3):
        print("pass either 0 arg or 2 args, %d given" % len(sys.argv[1:]))
        sys.exit(1)

    start = max(int(sys.argv[1]), 0) if (len(sys.argv) == 3) else 0
    num = min(int(sys.argv[2]), num_tasks) if (len(sys.argv) == 3) else num_tasks
    assert(num > 0 and start + num <= num_tasks)

    # ensure observer is compiled
    if os.path.isfile("../observer"):
        os.remove("../observer")
    subprocess.call("../craft.py --prepare-observer", shell=True)

    global counts
    n = start
    dipped = False
    while n < start + num:
        try:
            num_logged = run(FILENAME, tasks, n)
        except OSError: # argument list may be too long
            print("OSError raised: argument too long")
            break
        counts.append((n, num_logged))
        if num_logged == n:
            n += (25 if (not dipped) else 5)
        else:
            dipped = True
            n += 5

    dump_counts(counts)

def dump_counts(counts):
    with open(RESULT, 'w') as result:
        result.write("N    |  logged   accept\n")
        result.write("-----|-------------------\n")
        for item in counts:
            if item[1] < 0:
                accept = 0
            elif item[0] == 0:
                accept = 1.0
            else:
                accept = float(item[1]) / float(item[0])
            result.write("%-4d |   %4d,   %3.2f %%\n" % (
                item[0], item[1], 100 * accept))

if __name__ == "__main__":
    sys.exit(main())