OBSERVER = #empty
CXX = $(OBSERVER) ./g++ # a fake compiler

all: chrome content_shell browser_unittest

chrome: libchrome.so chrome.cc
	$(CXX) chrome.cc -L. -lchrome -o $@ -lpthread

libchrome.so: chrome1.cc chrome2.cc
	$(CXX) chrome1.cc -std=c++14 -DNDEBUG -Wall -pedantic -O2 -fPIC -c -o chrome1.o
	$(CXX) chrome2.cc -std=c++14 -DNDEBUG -Wall -pedantic -O2 -fPIC -c -o chrome2.o
	$(CXX) chrome1.o chrome2.o -fPIC -o $@

content_shell: libchrome.so content_shell.cc
	$(CXX) content_shell.cc -DNDEBUG -Wall -pedantic -O2 -std=c++14 -o content_shell.o
	$(CXX) content_shell.o -L. -lchrome -o $@ -lpthread

browser_unittest: libchrome.so browser_unittest.cc googletest/libgoogletest.so
	$(CXX) browser_unittest.cc -std=c++14 -DNDEBUG -Wall -pedantic -O2 -o browser_unittest.o -fsanitize=undefined,address
	$(CXX) browser_unittest.o -L. -lchrome -Lgoogletest -lgoogletest -o $@ -lpthread -fsanitize=undefined,address

clean:
	rm -rf *.so *.o chrome content_shell browser_unittest

.PHONY: clean