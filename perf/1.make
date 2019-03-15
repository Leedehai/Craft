OBSERVER = #empty
DRIVER = $(OBSERVER) ./g++
all:
	@$(DRIVER) abc.cc -c abc.o