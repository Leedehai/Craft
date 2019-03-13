# This script will be automatically invoked by Craft
CFLAGS = -std=c11 -O3 -DNDEBUG -Wall -pedantic

observer : observer-utils.c observer.c

clean:
	rm -f observer *.o *.pyc
