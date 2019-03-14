#!/usr/bin/env python
# Copyright: see README and LICENSE under the project root directory.
# Author: Haihong Li
#
# File: run-test.py
# ---------------------------
# Testing: ./run-test.py

import os, sys, time
import subprocess
import json, difflib

LOG_FILENAME = "log.json"
EXAMPLE_LOG_FILENAME = "example-log.json"
OUT_FILENAME = "stdout.txt"
EXAMPLE_OUT_FILENAME = "example-out.txt"

def compare_log(actual, expected):
    min_start_real_time, max_finish_real_time = 2 ** 63 - 1, 0
    actual_values = json.load(open(actual, 'r')).values()
    expected_values = json.load(open(expected, 'r')).values()
    def get_consistent_fields(values):
        json_strings = {}
        for data_dict in values:
            processed_dict = {}
            processed_dict["cmd"] = data_dict["cmd"].strip()
            processed_dict["exit"] = data_dict["exit"].strip()
            processed_dict["out"] = data_dict["out"].strip()
            processed_dict["err"] = data_dict["err"].strip()
            json_strings[processed_dict["cmd"]] = json.dumps(processed_dict, sort_keys=True)
        return json.dumps(json_strings, sort_keys=True)
    def check_times(values):
        min_start_real_time, max_finish_real_time = 2 ** 63 - 1, 0
        for data_dict in values:
            proc_times = [ float(v) for v in data_dict["time"]["proc"] ]
            real_times = [ float(v) for v in data_dict["time"]["real"] ]
            if not (len(proc_times) == 3 and len(real_times) == 3):
                return False, None
            min_start_real_time = min(real_times[0], min_start_real_time)
            max_finish_real_time = max(real_times[1], max_finish_real_time)
            proc_time_diff = proc_times[1] - proc_times[0]
            real_time_diff = real_times[1] - real_times[0]
            if not (proc_times[1] < 10.0 and proc_times[0] < proc_times[1]
                    and 0.99 < proc_times[2] / proc_time_diff < 1.01):
                return False, None
            if not (real_times[1] > 15e8 and real_times[0] < real_times[1]
                    and 0.99 < real_times[2] / real_time_diff < 1.01):
                return False, None
        return True, max_finish_real_time - min_start_real_time
    has_error = False
    try:
        if get_consistent_fields(actual_values) != get_consistent_fields(expected_values):
            print("log: persistent fields mismatch")
            has_error = True
        valid_times, make_elapse = check_times(actual_values)
        if not valid_times:
            print("log: times not valid")
            has_error = True
    except KeyError:
        print("log: fields missing")
        return False, None
    return False if has_error else True, make_elapse

def compare_out(actual, expected):
    # sort the stdout, because of concurrency of Make ('-j2') interleaves the lines
    actual_strings = sorted([ l.strip() for l in open(actual, 'r') if len(l.strip()) ])
    expected_strings = sorted([ l.strip() for l in open(expected, 'r') if len(l.strip()) ])
    return actual_strings == expected_strings

def main():
    with open(os.devnull, 'w') as DEVNULL: # Python2 doesn't have subprocess.DEVNULL
        subprocess.call("make -C tests clean", shell=True, stdout=DEVNULL)
    with open(OUT_FILENAME, 'w') as out_f:
        start_time = time.time()
        subprocess.call("./craft.py -w %s -- -C tests -j2" % LOG_FILENAME, shell=True, stdout=out_f)
        craft_elapse = time.time() - start_time
    has_error = False
    log_same, make_elapse = compare_log(LOG_FILENAME, EXAMPLE_LOG_FILENAME)
    if False == log_same:
        has_error = True
        print("[Error] logging output is wrong")
    if False == compare_out(OUT_FILENAME, EXAMPLE_OUT_FILENAME):
        has_error = True
        print("[Error] stdout output is wrong")
    if not has_error:
        print("OK.")
        os.remove(LOG_FILENAME)
        os.remove(OUT_FILENAME)
    return 1 if has_error else 0

if __name__ == "__main__":
    sys.exit(main())
