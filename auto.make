# This script will be automatically invoked by Craft
CFLAGS = -std=c11 -O3 -DNDEBUG -Wall -pedantic

observer : observer.c

clean:
	rm -f observer *.pyc
