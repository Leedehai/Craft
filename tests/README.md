# tests

This directory contains a mock C++ project.

- g++: the fake compiler that simply creates a file as it is told to.
- \*.cc: fake source files.
- makefile: you can run it without Craft.

Try makefile without Craft:
```shell
make clean
make
```

Try makefile with Craft:
```shell
make clean
../craft.py -w log.json -- -j2 # run: make -j2
```

###### EOF
