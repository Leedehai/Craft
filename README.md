Work in progress: observer and recorder are runnable

# Craft

More than Make.

**craft**<br>
&nbsp;&nbsp;&nbsp;&nbsp;*verb*&nbsp;&nbsp;&nbsp;&nbsp;to make or produce with care, skill, or ingenuity.

Craft is a build monitor on top of Make, a build utility.

This is based on [make-formatter.py](https://github.com/Leedehai/make-output-prettify), also authored by me.<br>
With minimal changes of code, it can be applied to other build systems, like Google's [Ninja](https://ninja-build.org), as well. 

### 1. Use case
Often times, a project has a (or more) complicated Makefile. Lots of information, the majority of them being the commands executed, is printed to stdout when Make is executing the Makefile. To suppress the verbose printout, one could take one of the approaches:
- redirect the output to `/dev/null`
- add `@` in front of a command in Makefile as to silence it.

But both completely silence the output, leaving the developer no knowledge of what command is being executed. To sum up, the pain point is that developers want to know which command is being executed by Make at any given moment, but they do not want Make to echo the exact commands. In a word, they want a **succinct** real-time printout.

Moreover, in some cases developers may be interested in the exact commands that were executed, mainly in order to debug the project. Therefore, they want a **logging** feature as well.

This is where Craft comes in.

### 2. Prerequisites
- macOS or Linux (sorry, no Windows).
- GNU Make, 3.81 or higher.
- C compiler supporting C11.
- Python 2.7, or Python 3.5 or higher.

### 3. Limitations
This project is taken from a larger C/C++ project of mine, and I don't intend to generalize it at the moment.

### 4. Overview
Craft has a simple architecture. It is basically a client-server pattern, but the communication between clients and the server is monodirectional. In light of this, Craft has three components:
- manager: the top-level API, which invokes `make` for you,
- observer: the program (client) that runs commands and capture commands' output,
- recorder: the program (server) that logs reports sent by observers.

Each (interested) command in Makefile will be invoked by the observer. Therefore, it is crucial that the observer only adds a minimum runtime overhead. Therefore, the observer is written in C, and should be compiled before invoking Craft. Luckily, if the manager finds the observer was not compiled, it will automatically compile it for you before launching the first observer.

### 5. How to use
1. Add `$(OBSERVER)` to the compiler name in the Makefile. In other words, instead of having
	```makefile
	CXX = clang++ # or g++
	```
	you should define the compiler for C++ `CXX` like this (and `CC`, `LD`, `AR`, and so forth):
	```makefile
	OBSERVER =                # empty string
	CXX = $(OBSERVER) clang++ # or g++
	```
	> To make your Makefile runnable without Craft, you should define `OBSERVER` to be empty in Makefile.

2. Instead of executing `make ARGS` in the console to invoke Make, run `craft [OPTIONS] [-- ARGS]` instead, where `OPTIONS` are arguments to Craft, and `ARGS` are arguments to Make. Example:
	```shell
	craft                    # no args given to Craft, and call Make like 'make'
	craft -w log.json        # ask Craft to write logs, and call Make like 'make'
	craft -w log.json -- -j8 # ask Craft to write logs, and call Make like 'make -j8'
	craft -- tests -j8       # no args to Craft, and call Make like 'make tests -j8'
	```

For help, `craft --help`.

###### EOF
