#

CC=cc
BIN=./bin
SOURCE=./

PROG=cp2102
LIST=$(addprefix $(BIN)/, $(PROG))
CFLAGS= -I$(SOURCE)

detected_OS := $(shell sh -c 'uname 2>/dev/null || echo Unknown')

LIBS=-lusb

opt_libusb = $(shell if [ -d /opt/local/include/libusb-1.0 ]; then echo yes; else echo no; fi)
ifeq ($(opt_libusb),yes)  # in /opt
  CFLAGS +=  -I/opt/local/include/libusb-1.0
  LIBS=-L/opt/local/lib -lusb-1.0
else ifeq ($(detected_OS),Darwin)  # Mac OS X
  CFLAGS +=  -I/usr/local/include/libusb-1.0
  LIBS=-L/usr/local/lib -lusb-1.0
else ifeq ($(detected_OS),Linux)
  CFLAGS +=  -I/usr/include/libusb-1.0
  LIBS=-lusb-1.0
endif

all: dirs $(LIST)

dirs:
	-[ -d bin/ ] || mkdir -p bin/

$(BIN)/%:  $(SOURCE)%.c
	$(CC) $(INC) $< $(CFLAGS) -o $@ $(LIBS)

clean:
	rm -f $(LIST)

