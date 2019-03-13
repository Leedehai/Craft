# This script will be automatically invoked by Craft
CFLAGS = -std=c11 -O3 -DNDEBUG -Wall -pedantic -Iutils

observer : utils/observer-utils.c utils/observer-serialize.c observer.c

clean:
	rm -f observer *.o *.pyc utils/*.o *.dep utils/*.dep
