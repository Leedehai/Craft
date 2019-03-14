#!/usr/bin/env python
# Copyright: see README and LICENSE under the project root directory.
# Author: Haihong Li
#
# File: formatter.py
# ---------------------------
# Prettify the output of some make commands (less verbose).
# Taken from another project of mine: https://github.com/Leedehai/make-output-prettify

# switch: if False, all output lines are passed through as is.
enable = True # normally you should not touch this

import sys
from os.path import normpath
from os.path import basename
from os import isatty as os_isatty

# key symbols
K_SHAREDLIB = ".so"
K_OBJ       = ".o"
K_C         = ".c"
K_CPP       = ".cc"
K_ASM       = ".s"
K_COMPILE   = " -c"
K_OUTPUT    = " -o"
K_FPIC      = " -fPIC"

# prefixes
if os_isatty(1): # if stdout writes to terminal
    PREFIX_COMPILE   = "\x1b[38;5;220m[Compile]\x1b[0m" # yellow-ish
    PREFIX_LINK      = "\x1b[38;5;45m[Link]\x1b[0m"     # red-ish
    PREFIX_COMPLINK  = "\x1b[38;5;220m[Compile]\x1b[0m\x1b[38;5;45m[Link]\x1b[0m" # green-ish
    PREFIX_SHAREDLIB = "\x1b[38;5;225m[Library]\x1b[0m" # purple-ish
else:
    PREFIX_COMPILE   = "[Compile]"
    PREFIX_LINK      = "[Link]"
    PREFIX_COMPLINK  = "[Compile][Link]"
    PREFIX_SHAREDLIB = "[Library]"

# action categories - Python2 doesn't have 'enum'
ACT_COMPILE   = "COMPILE"
ACT_LINK      = "LINK"
ACT_COMPLINK  = "COMPLINK"
ACT_SHAREDLIB = "SHAREDLIB"
ACT_OTHERS    = "OTHERS"
ACT_PASSTHROUGH = "PASSTHROUGH"

"""
handlers for different types of lines.
Interface: param: str: the line
           return: tuple ([0] str: the processed line, [1] str: action category)
"""

def handle_compile_only(line):
    line_split = line.split()
    if line.count(K_OUTPUT.strip()) != 0:
        obj_file_index = line_split.index(K_OUTPUT.strip()) + 1
        processed_line = "%s => %s" % (PREFIX_COMPILE, line_split[obj_file_index])
    else:
        source_files = [basename(item.replace(K_CPP, K_OBJ)) for item in line_split if item.endswith(K_CPP)]
        source_files += [basename(item.replace(K_C, K_OBJ)) for item in line_split if item.endswith(K_C)]
        source_files += [basename(item.replace(K_ASM, K_OBJ)) for item in line_split if item.endswith(K_ASM)]
        processed_line = "%s => %s" % (PREFIX_COMPILE, ' '.join(source_files))
    return processed_line, ACT_COMPILE

def handle_convert_obj_to_so(line):
    line_split = line.split()
    so_file_index = line_split.index(K_OUTPUT.strip()) + 1
    processed_line = "%s => %s" % (PREFIX_SHAREDLIB, normpath(line_split[so_file_index]))
    return processed_line, ACT_SHAREDLIB

def handle_compile_and_link(line):
    line_split = line.split()
    exe_file_index = line_split.index(K_OUTPUT.strip()) + 1
    if exe_file_index >= len(line_split): # unlikely
        return "%s => a.out" % (PREFIX_COMPLINK), ACT_COMPLINK
    processed_line = "%s => %s" % (PREFIX_COMPLINK, normpath(line_split[exe_file_index]))
    return processed_line, ACT_COMPLINK

def handle_link_only(line):
    line_split = line.split()
    exe_file_index = line_split.index(K_OUTPUT.strip()) + 1
    if exe_file_index >= len(line_split): # unlikely
        return "%s => a.out" % (PREFIX_LINK), ACT_LINK
    processed_line = "%s => %s" % (PREFIX_LINK, normpath(line_split[exe_file_index]))
    return processed_line, ACT_LINK

def handle_others(line):
    return line, ACT_OTHERS

def handle_passthrough(line):
    return line, ACT_PASSTHROUGH

"""
Discern what the line is, and return a suitable function that handles it
NOTE the order of the condition checks are specifically arranged like this, modify with care
@param str
@return function
"""
def get_processing_handler(line):
    if line.count(K_COMPILE) != 0:
        return handle_compile_only
    # from here: no K_COMPILE found
    if line.count(K_FPIC) != 0:
        return handle_convert_obj_to_so
    # from here: no K_FPIC found
    if line.count(K_OUTPUT) != 0:
        if line.count(K_CPP) != 0 or line.count(K_C) != 0 or line.count(K_ASM) != 0:
            return handle_compile_and_link
        else:
            return handle_link_only
    # from here: no K_OUTPUT found
    return handle_others

"""
Generate processed line, and whether it should be printed
@param str
@return tuple ([0] str: the processed line, [1] str: action category)
"""
def process(line):
    if not enable:
        return (line, ACT_PASSTHROUGH)
    handler = get_processing_handler(line)
    return handler(line)

if __name__ == "__main__":
    line = ' '.join(sys.argv[1:])
    processed_line, category = process(line)
    print(processed_line)