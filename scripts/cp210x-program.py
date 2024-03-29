#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2007 Johannes Hölzl <johannes.hoelzl@gmx.de>
#
# This library is covered by the GNU LGPL, read LICENSE for details.
"""\
Provides access to the EEPROM of a Silabs CP210x. The data can be directly
read from or written to the device.
"""

import optparse
import re
import string
import sys
import traceback

from cp210x import __license__, __version__, cp210x, valuefile
from cp210x.eeprom import EEPROM, HexFileError
from cp210x.valuefile import (
    ValuesFileError,
    read_baudrate_info,
    update_values,
)

TRANS_UNDERSCORE = str.maketrans('_', '-')

ERR_OK = 0
ERR_WRONG_INPUT = -1
ERR_INTERNAL = -2
ERR_DEVICE_LOCKED = -3
ERR_DEVICE_NOT_FOUND = -4
ERR_DEVICE_ERROR = -5
ERR_OTHER = -100

def error(message, retval=-1):
    sys.stderr.write(message + "\n")
    sys.exit(retval)

class Option(optparse.Option):
    TYPES = list(optparse.Option.TYPES)
    TYPE_CHECKER = dict(optparse.Option.TYPE_CHECKER)
    for type, (reader, _) in list(valuefile.TYPES.items()):
        if type in TYPES:
            continue
        TYPES.append(type)
        def checker(self, name, value, reader=reader):
            try:
                return reader(value)
            except ValueError as err:
                raise optparse.OptionValueError("option %s: %s" % (name,
                                                                   str(err)))
        TYPE_CHECKER[type] = checker

class OptionParser(optparse.OptionParser):
    def error(self, msg):
        error(msg, ERR_WRONG_INPUT)

    def __init__(self, *args, **kwargs):
        if 'option_class' not in kwargs:
            kwargs['option_class'] = Option
        optparse.OptionParser.__init__(self, *args, **kwargs)

def input_file(arg):
    if arg is None or arg == '-':
        return sys.stdin
    else:
        return open(arg, 'r')

def output_file(arg):
    if arg is None or arg == '-':
        return sys.stdout
    else:
        return open(arg, 'w', newline='\n')

def options_to_values(options):
    values = {}
    for name, type in cp210x.VALUES:
        if name == "baudrate_table":
            continue
        value = getattr(options, name)
        if value is not None:
            values[name] = value

    if options.baudrate_table:
        baudrate_table = []
        for s in options.baudrate_table:
            try:
                baudrate, info = s.split(':')
            except TypeError:
                error("option --set-baudrate: requires two parts separated by ':'",
                      ERR_WRONG_INPUT)
            try:
                baudrate_table.append(read_baudrate_info(info) +
                                      (int(baudrate), ))
            except ValueError as err:
                error("option --set-baudrate: %s" % str(err),
                      ERR_WRONG_INPUT)

        values['baudrate_table'] = baudrate_table
    return values

def find_device(patterns):
    usb_patterns = []
    for pattern in patterns:
        if ':' in pattern:
            try:
                vidString, pidString = pattern.split(':')
                vid = int(vidString, 16)
                pid = int(pidString, 16)

            except (TypeError, ValueError):
                error("Match must be either 'ddd/ddd' or 'hhhh:hhhh'.",
                      ERR_WRONG_INPUT)

            usb_patterns.append(dict(idVendor=vid, idProduct=pid))

        elif '/' in pattern:
            try:
                busString, addressString = pattern.split('/')
                bus = int(busString)
                address = int(addressString)

            except (TypeError, ValueError):
                error("Match must be either 'ddd/ddd' or 'hhhh:hhhh'.",
                      ERR_WRONG_INPUT)

            usb_patterns.append(dict(bus=bus, address=address))

        else:
            error("Match must be either 'ddd/ddd' or 'hhhh:hhhh'.",
                  ERR_WRONG_INPUT)

    for dev in cp210x.Cp210xProgrammer.list_devices(usb_patterns):
        return dev

    error("No devices found", ERR_DEVICE_NOT_FOUND)

def read_cp210x(options):
    usbdev = find_device(options.match)
    print("USB find_device returned:\n{}".format(usbdev))
    dev = cp210x.Cp210xProgrammer(usbdev)
    print("Cp210xProgrammer returned obj:\n{}".format(repr(dev)))

    if isinstance(dev, cp210x.Cp210xProgrammer):
        print("Cp210xProgrammer instance is valid!!")

    eeprom = EEPROM(dev)
    print("EEPROM returned obj:\n{}".format(repr(eeprom)))

    if options.hex_output:
        eeprom.write_hex_file(output_file(options.hex_output))
    if options.ini_output or not options.hex_output:
        valuefile.write_file(output_file(options.ini_output), eeprom.get_values())

def write_cp210x(options):
    usbdev = find_device(options.match)
    dev = cp210x.Cp210xProgrammer(usbdev)

    if options.hex_input or options.force_eeprom:

            if options.hex_input:
                eeprom = EEPROM(input_file(options.hex_input))
            else:
                eeprom = EEPROM(dev)

            values = eeprom.get_values()
            if options.ini_input:
                values = valuefile.read_file(input_file(options.ini_input))
            update_values(values, options_to_values(options), eeprom)

            eeprom.set_values(values)

            eeprom.write_to_cp210x(dev)

    else:
            if options.ini_input:
                values = valuefile.read_file(input_file(options.ini_input))
            else:
                values = {}
            update_values(values, options_to_values(options), dev)
            dev.set_values(values)

    if options.reset_device:
        dev.reset()

def change_hexfile(options):
    eeprom = EEPROM(input_file(options.hex_input))
    values =  {}
    if options.ini_input:
        update_values(values,
                      valuefile.read_file(input_file(options.ini_input)),
                      eeprom)
    update_values(values, options_to_values(options), eeprom)
    eeprom.set_values(values)
    if options.ini_output:
        valuefile.write_file(output_file(options.ini_output),
                             eeprom.get_values())
    eeprom.write_hex_file(output_file(options.hex_output))

def parse_hexfile(options):
    eeprom = EEPROM(input_file(options.hex_input))
    valuefile.write_file(output_file(options.ini_output), eeprom.get_values())

parser = OptionParser(version=__version__, description=__doc__)
parser.add_option("-r", "--read-cp210x", const=read_cp210x,
                  dest="action", action="store_const")
parser.add_option("-w", "--write-cp210x", const=write_cp210x,
                  dest="action", action="store_const")
parser.add_option("-c", "--change-hexfile", const=change_hexfile,
                  dest="action", action="store_const")
parser.add_option("-p", "--parse-hexfile", const=parse_hexfile,
                  dest="action", action="store_const")
parser.add_option("-F", "--hex-input", metavar="FILE")
parser.add_option("-f", "--hex-output", metavar="FILE")
parser.add_option("-I", "--ini-input", metavar="FILE")
parser.add_option("-i", "--ini-output", metavar="FILE")
for name, type in cp210x.VALUES:
    if name == 'baudrate_table':
        continue
    parser.add_option("--set-" + name.translate(TRANS_UNDERSCORE),
                      dest=name, metavar=name.upper(), type=type)
parser.add_option("--set-baudrate", action="append", dest="baudrate_table")
parser.add_option("-m", "--match", action="append", metavar="PATTERN")
parser.add_option("--reset-device", action="store_true")
parser.add_option("--force-eeprom", action="store_true")

parser.set_defaults(
    action=read_cp210x,
    hex_input=None,
    hex_output=None,
    ini_input=None,
    ini_output=None,
    match=[],
    baudrate_table=[],
    reset_device=False,
    force_eeprom=False,
)

def main():
    (options, _) = parser.parse_args()
    if not options.match:
        options.match = ['10C4:EA60', '10C4:EA61']
    options.action(options)

if __name__ == '__main__':
    try:
        main()

    except cp210x.DeviceLocked:
        error("Cannot write data to device. Device is locked.",
              ERR_DEVICE_LOCKED)

    except cp210x.Cp210xError as err:
        error(str(err), ERR_DEVICE_ERROR)

    except IOError as err:
        error(str(err), ERR_OTHER)

    except HexFileError as err:
        error(str(err), ERR_OTHER)

    except ValuesFileError as err:
        error(str(err), ERR_OTHER)

    except SystemExit as err:
        raise

    except:
        traceback.print_exc()
        sys.exit(ERR_INTERNAL)
