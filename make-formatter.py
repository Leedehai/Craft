#!/usr/bin/env python
# Copyright: see README and LICENSE under the project root directory.
# Author: Haihong Li
#
# File: make-formatter.py
# ---------------------------
# Make formatter engine: prettify the output of some make commands (less verbose) in
# real time. It works with multithreaded 'make' as well.
# Call:  make-formatter.py         # replacing 'make'
#        make-formatter.py -- -j8  # replacing 'make -j8'
# List and count targets to-be-built:
#        make-formatter.py -- --dry-run | grep " => "
#        make-formatter.py -- --dry-run | grep --count " => "

# switch: if False, all output lines are passed through as is.
enable = True # normally you should not touch this

import sys, signal
import subprocess
from os.path import normpath
from os.path import basename
from os import popen as os_popen
import time
import argparse

# key symbols
K_SHAREDLIB = ".so"
K_OBJ       = ".o"
K_CPP       = ".cc"
K_ASM       = ".s"
K_COMPILE   = " -c"
K_OUTPUT    = " -o"
K_FPIC      = " -fPIC"
K_PREPAR    = "Preparation: "
K_STARS     = "***"
K_MAKEDONE  = "make: DONE "

# prefixes
PREFIX_COMPILE   = "\x1b[38;5;220m[Compile]\x1b[0m" # yellow-ish
PREFIX_LINK      = "\x1b[38;5;45m[Link]\x1b[0m"     # red-ish
PREFIX_COMPLINK  = "\x1b[38;5;220m[Compile]\x1b[0m\x1b[38;5;45m[Link]\x1b[0m" # green-ish
PREFIX_SHAREDLIB = "\x1b[38;5;225m[Library]\x1b[0m" # purple-ish

# action categories
ACT_COMPILE   = "compile"
ACT_LINK      = "link"
ACT_COMPLINK  = "compile_link"
ACT_SHAREDLIB = "library"
ACT_OTHERS    = "others"
ACT_PASSTHROUGH = "passthrough"
ACT_MAKEDONE_MESSAGE = "make_done"
DO_NOT_STORE_ACTIONS = [ ACT_OTHERS, ACT_PASSTHROUGH, ACT_MAKEDONE_MESSAGE ]

"""
handlers for different types of lines.
Interface: param: str: the line, guaranteed not "" and not starting with space
           return: tuple ([0] str: the processed line, [1] bool: should be printed, [2] action category)
"""

def handle_compile_only(line):
    line_split = line.split()
    if line.count(K_OUTPUT.strip()) != 0:
        obj_file_index = line_split.index(K_OUTPUT.strip()) + 1
        processed_line = "%s => %s..." % (PREFIX_COMPILE, line_split[obj_file_index])
    else:
        source_files = [basename(item.replace(K_CPP, K_OBJ)) for item in line_split if item.endswith(K_CPP)]
        source_files += [basename(item.replace(K_ASM, K_OBJ)) for item in line_split if item.endswith(K_ASM)]
        processed_line = "%s => %s..." % (PREFIX_COMPILE, ' '.join(source_files))
    return processed_line, True, ACT_COMPILE

def handle_convert_obj_to_so(line):
    line_split = line.split()
    so_file_index = line_split.index(K_OUTPUT.strip()) + 1
    processed_line = "%s => %s..." % (PREFIX_SHAREDLIB, normpath(line_split[so_file_index]))
    return processed_line, True, ACT_SHAREDLIB

def handle_compile_and_link(line):
    line_split = line.split()
    exe_file_index = line_split.index(K_OUTPUT.strip()) + 1
    if exe_file_index >= len(line_split): # unlikely
        return "%s => a.out..." % (PREFIX_COMPLINK), True, ACT_COMPLINK
    processed_line = "%s => %s..." % (PREFIX_COMPLINK, normpath(line_split[exe_file_index]))
    return processed_line, True, ACT_COMPLINK

def handle_link_only(line):
    line_split = line.split()
    exe_file_index = line_split.index(K_OUTPUT.strip()) + 1
    if exe_file_index >= len(line_split): # unlikely
        return "%s => a.out..." % (PREFIX_LINK), True, ACT_LINK
    processed_line = "%s => %s..." % (PREFIX_LINK, normpath(line_split[exe_file_index]))
    return processed_line, True, ACT_LINK

def handle_preparation_msg(line):
    return "", False, ACT_OTHERS

def handle_separator(line):
    return "", False, ACT_OTHERS

def handler_makedone_message(line):
    return "", False, ACT_MAKEDONE_MESSAGE

def handle_passthrough(line):
    return line, True, ACT_PASSTHROUGH

"""
Check if the line is some tool's warning or error message. It should NOT rely on the
content of that tool's message pattern, as the pattern depends on the tool's authors.
Therefore, I need to use some heuristics.
@param str, guaranteed not "" but might starting with space
@return bool
"""
def is_error_msg(line):
    if line[0].isspace():
        return True # this line is a error (or warning) message from a tool
    elif line.startswith(K_STARS) or line.startswith(K_MAKEDONE) or line.count(K_PREPAR) != 0:
        return False

    first = line.split()[0]
    # "clang++", "g++", "clang", gcc"
    if first.endswith("g++") != 0 or line.endswith("clang") != 0 or line.endswith("gcc") != 0:
        return False
    # "ld", "gold", "ar"
    if first == "ld" or first == "ar":
        return False
    if first.count('-') == 1: # "clang++-6", "g++-7", "clang-6", "gcc-7"
        e1, e2 = first.split('-')[0], first.split('-')[1]
        if (e1.endswith("g++") or e1.endswith("clang") or e1.endswith("gcc")) and e2.isdigit():
            return False
    return True # this line is a error (or warning) message from a tool

"""
Discern what the line is, and return a suitable function that handles it
NOTE the order of the condition checks are specifically arranged like this, modify with care
@param str
@return function
"""
def get_processing_handler(line):
    if len(line) == 0 or is_error_msg(line):
        return handle_passthrough
    # from here: is not empty, is not error message
    if line.count(K_COMPILE) != 0:
        return handle_compile_only
    # from here: no K_COMPILE found
    if line.count(K_FPIC) != 0:
        return handle_convert_obj_to_so
    # from here: no K_FPIC found
    if line.count(K_OUTPUT) != 0:
        if line.count(K_CPP) != 0 or line.count(K_ASM) != 0:
            return handle_compile_and_link
        else:
            return handle_link_only
    # from here: no K_OUTPUT found
    if line.count(K_PREPAR):
        return handle_preparation_msg
    # from here: no K_PREPAR found
    if line.count(K_STARS) != 0:
        return handle_separator
    # from here: no K_STARS found
    if line.count(K_MAKEDONE) != 0:
        return handler_makedone_message
    # from here: no K_MAKEDONE found
    return handle_passthrough

"""
Generate processed line, and whether it should be printed
@param str
@return tuple (str, bool, str)
"""
def process(line):
    if not enable:
        return (line, True, ACT_PASSTHROUGH)
    handler = get_processing_handler(line)
    return handler(line) # return (str: processed line, bool: should print, str: action)

"""
Store raw_line and processed_line in memory.
@param raw_line: str
       processed_line: str
       action_cat: str
       begin_time: double
"""
record_dict = {}
record_counter = 0
def store_to_memory_log(raw_line, processed_line, action_cat, begin_time):
    global record_dict
    global record_counter
    if (action_cat in DO_NOT_STORE_ACTIONS):
        return
    assert(" => " in processed_line)
    record_counter += 1
    product_name = processed_line.split(" ")[-1][:-3] # "PRODUCT" from "ACTION => PRODUCT..."
    assert(product_name not in record_dict)
    record_dict[product_name] = {
        "command": raw_line,
        "order": record_counter,
        "action": action_cat,
        "on_disk": False, # 'False' is to be replace with 'True' if product is on disk
        "time": (begin_time, None), # 'None' is to be replaced with product mtime
        "size": None, # 'None' is to be replaced with product size (in bytes)
    }

TERMINAL_COLS = int(os_popen('stty size', 'r').read().split()[1])

def to_width(s, width):
    # make string exactly 'width' long, padding or truncating when necessary
    extra_space = width - len(s)
    return (s + ' ' * extra_space) if extra_space >= 0 else (s[:width - 3] + "...")

def print_line_eliding(s, eliding=True):
    if not eliding:
        print(s)
        return
    # print string on the same line as the previously-printed string, overwriting the latter
    extra_space = TERMINAL_COLS - len(s)
    sys.stdout.write("\r%s" % to_width(s, TERMINAL_COLS - 20))
    sys.stdout.flush()

SHOULD_RUN_DIRECTLY = [ "run", "runraw", "concurrent-run", "concurrent-runraw" ]
def check_cmd(cmd):
    # 1
    for item in SHOULD_RUN_DIRECTLY:
        if item in cmd:
            print("[Error] this command should be run directly with Make:")
            print("        make %s" % item)
            return False
    # 2
    multiprocessing = False
    for arg in cmd:
        if arg.startswith("-j"):
            multiprocessing = True
            strAfterJ = arg.split("-j")[-1]
            if len(strAfterJ) != 0 and strAfterJ.isdigit():
                print("[Info] Using %d processes" % int(strAfterJ))
            elif len(strAfterJ) == 0: # "make -j" let Make figure out number of jobs
                print("[Info] Using multiple processes")
            break
    if not multiprocessing:
        print("[Info] Using one process")
    return True

def work(args, cmd):
    if False == check_cmd(cmd):
        return 1

    if args.write_log:
        start_time = time.time()

    p = subprocess.Popen(' '.join(cmd), shell=True, stdout=subprocess.PIPE, bufsize=1)
    for raw_bytes in iter(p.stdout.readline, b''):
        t = time.time() # approximate: command begin time
        raw_line = raw_bytes.decode('utf-8').rstrip()
        processed_line, to_print, action_cat = process(raw_line)
        if args.write_log:
            store_to_memory_log(raw_line, processed_line, action_cat, t)
        if to_print:
            print_line_eliding(processed_line, args.elide)
    p.wait()

    if args.write_log:
        finish_time = time.time()

    if args.elide:
        sys.stdout.write("\n")
        sys.stdout.flush()

    if args.write_log:
        import json
        from os.path import getmtime as getmtime
        from os.path import isfile as isfile
        from os.path import getsize as getsize
        for product_name in record_dict:
            if isfile(product_name):
                record_dict[product_name]["time"] = (
                    record_dict[product_name]["time"][0], # job added, sec
                    getmtime(product_name) # job done, sec
                )
                record_dict[product_name]["size"] = getsize(product_name) # bytes
                record_dict[product_name]["on_disk"] = True
        with open(args.write_log, 'w') as f:
            json.dump({
                "time": (start_time, finish_time),
                "jobs": record_dict
            }, f, indent=2)

    return p.returncode # NOTE returncode is the return code of the shell program that
                        # is envoked to run the command, instead of the return code of
                        # the command itself.

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

    parser = argparse.ArgumentParser(description="Prettify output of Make",
                                     epilog="if '-- ..' exists, args after '--' are passed to Make")
    parser.add_argument("-e", "--elide", action='store_true',
                        help="output line will elide the previous line")
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
    make_cmd = ['make'] + make_args
    return work(args, make_cmd)

if __name__ == "__main__":
    sys.exit(main())
