# -*- coding: utf-8 -*-
# Copyright (c) 2007 Johannes Hölzl <johannes.hoelzl@gmx.de>
#
# This library is covered by the GNU LGPL, read LICENSE for details.
"""Provides access to the EEPROM of Silabs CP210x devices

The following classes are available:

class Cp210xProgrammer:
    Provides direct access to the CP2101, can be used to write single data
    directly or via an EEPROM image.

class EEPROM:
    Can be used to read or write a hex file containing the EEPROM content
    of an CP2101. Provides also access to the single fields in the EEPROM.
"""

import ctypes
import usb

__all__ = ['Cp210xProgrammer', 'Cp210xError']

CP2101_UART         = 0x00
CP2101_CONFIG       = 0xFF

CP2101_UART_ENABLE  = 0x0001
CP2101_UART_DISABLE = 0x0000

REG_VENDOR_ID       = 0x3701
REG_PRODUCT_ID      = 0x3702
REG_PRODUCT_STRING  = 0x3703
REG_SERIAL_NUMBER   = 0x3704
REG_CFG_ATTRIBUTES  = 0x3705
REG_MAX_POWER       = 0x3706
REG_VERSION         = 0x3707
REG_UNKNOWN         = 0x3708
REG_EEPROM          = 0x3709
REG_LOCK_VALUE      = 0x370A
REG_PART_NUMBER     = 0x370B

SIZE_EEPROM         = 0x0400
SIZE_PRODUCT_STRING = 0x007D
SIZE_SERIAL_NUMBER  = 0x003F
SIZE_BAUDRATES      = 32
SIZE_BAUDRATE_CFG   = 10
SIZE_BAUDRATE_TABLE = SIZE_BAUDRATES * SIZE_BAUDRATE_CFG
SIZE_VENDOR_STRING  = 24

LCK_LOCKED          = 0x00
LCK_UNLOCKED        = 0xFF

VID_SILABS          = 0x10C4
PID_CP210x          = 0xEA60

VALUES = [
    ('product_string', 'string'),
    ('serial_number',  'string'),
    ('product_id',     'id'),
    ('vendor_id',      'id'),
    ('version',        'version'),
    ('bus_powered',    'boolean'),
    ('max_power',      'int'),
    ('locked',         'boolean'),
    ('part_number',    'int'),
    ('vendor_string',  'string'),
    ('baudrate_table', 'list'),
]

def iif(v, a, b):
    if v:
        return a
    else:
        return b

def to_div2(p):
    value = int(p / 2)
    if (value * 2) < p:
        value += 1
    return value
    
def to_bcd(i):
    assert i >= 0 and i <= 99
    return (i // 10) << 4 | (i % 10)

def to_bcd2( (i, j) ):
    return to_bcd(i) << 8 | to_bcd(j)

def from_bcd(num):
    return num & 0x0F + (num >> 4) * 10

def from_bcd2(data):
    return (from_bcd(data >> 8), from_bcd(data & 0xFF))

def from_binary(data, le=True):
    value = 0
    if le:
        data = data[::-1]
    for byte in data:
        value = value << 8 | ord(byte)
    return value

def to_binary(value, size=2, le=True):
    data = ''
    for i in range(size):
        data += chr(value & 0xFF)
        value >>= 8
    if le:
        return data
    else:
        return data[::-1]
    
def parse_baudrate_cfg(data):
    return (from_binary(data[0:2], le=False), 
            from_binary(data[2:4], le=False), 
            from_binary(data[4:5]),
            from_binary(data[6:10]))

def build_baudrate_cfg(baudgen, timer0reload, prescaler, baudrate):
    return (to_binary(baudgen, le=False) + to_binary(timer0reload, le=False) + 
            to_binary(prescaler, 1) + '\x00' + to_binary(baudrate, 4))

class Cp210xError(IOError):
    pass

class DeviceLocked(Cp210xError):
    pass

class Cp210xProgrammer(object):
    """Program an Silabs CP2101, CP2102 or CP2103
    
    This modul provides access to Silabs CP210x devices to set some USB
    descriptor fields and some USB descriptor strings. 

    The following fields can be set:

     * Vendor ID
     * Product ID
     * Product String
     * Serial Number
     * Device Version
     * Bus Powered
     * max. Power consumption
 
    Either use libusb to find a device, and provide the device description
    to the constructor, or use Cp210xProgrammer.list_device() to list all
    devices matching certain pattern.
    
    To progamm the device open() it, set the data, and close() it. To have the
    changed fields reread call reset() before closing it.
    """
    
    TIMEOUT = 300 #ms
    
    @classmethod
    def list_devices(self, patterns=[{ 'idVendor': VID_SILABS, 
                                       'idProduct': PID_CP210x }]):
        """Yields a list of devices matching certain patterns.
        
        param patterns: This must be a list of dictionaries or pairs of string.
            Each device in the usb tree is matched against all pattern in the
            list. 
            
            When an item is a dictionary all fields of the descriptors
            are compared against the corresponding values in the dictionary. If
            each value is equal, the device is yielded.
            
            When an item is a pair of strings. The first string must be the
            dirname of the bus and the second string the filename of the device.
        
        For example:

        >> list(Cp210xProgrammer.list_device([{ 'idVendor': VID_SILABS, 
                                           'idProduct': PID_CP210x }]))
        [device(...)]
        
        """
        
        usb.find_busses()
        usb.find_devices()
        
        bus = usb.get_busses()
        while bus:
            dev = bus.contents.devices
            while dev:
                for pattern in patterns:
                    if isinstance(pattern, dict):
                        for name, value in pattern.items():
                            if getattr(dev.contents.descriptor, name) != value:
                                break
                        else:
                            yield self(dev)
                            break
                    elif isinstance(pattern, tuple):
                        if (bus.dirname == pattern[0] and
                            dev.filename == pattern[1]):
                            yield self(dev)
                            break
                dev = dev.contents.next
            bus = bus.contents.next
    
    def __init__(self, dev_info):
        self.dev_info = dev_info
        self.handle = None
        self._locked = None
        
    def open(self):
        """Opens the device.
        
        Only after an successful call to open() data can be read from and
        written to the device. 

        Claims all resources associated with this device.
        """
        self.handle = usb.open(self.dev_info)
        if self.handle == 0:
            self.handle = None
            raise Cp210xError("Can't open device.")
        usb.set_configuration(self.handle, 1)
        usb.claim_interface(self.handle, 0)

    def reset(self):
        """Force the USB stack to reset the device.
        
        Resets the device through an hard reset over the port to which the
        device is connected. After that happend the EEPROM content in the device
        is reread and the device's descriptors are the one written to it.
        """
        assert self.handle is not None
        usb.reset(self.handle)
    
    def close(self):
        """Closes the device.
        
        Releases all resources associated with this device.
        """
        assert self.handle is not None
        usb.release_interface(self.handle, 0)
        usb.close(self.handle)
        self.handle = None
    
    def __del__(self):
        if self.handle is not None:
            self.close()

    def _set_config(self, value, index=0, data=None, request=CP2101_CONFIG):
        assert self.handle is not None
        if self.get_locked():
            raise DeviceLocked()
            
        if data is not None:
            data_length = len(data)
        else:
            data_length = 0
        res = usb.control_msg(self.handle, usb.ENDPOINT_OUT | usb.TYPE_VENDOR, 
                              request, value, index, data, data_length,
                              self.TIMEOUT)
        if res < 0:
            raise Cp210xError("Unable to send request %04X result=%d"
                              % (value, res))

    def _set_config_string(self, value, content, max_length):
        assert isinstance(content, basestring)
        encoded = content.encode('utf-16-le')
        assert len(encoded) <= max_length
        self._set_config(value, data=chr(len(encoded) + 2) + "\x03" + encoded)

    def _get_config(self, value, length, index=0, request=CP2101_CONFIG):
        assert self.handle is not None
        data = ctypes.create_string_buffer(length)
        res = usb.control_msg(self.handle, usb.ENDPOINT_IN | usb.TYPE_VENDOR, 
                              request, value, index, data, length,
                              self.TIMEOUT)
        if res < 0:
            raise Cp210xError("Unable to send request, %04X result=%d"
                              % (value, res))
        return data.raw[:res]
            
    def _get_int8_config(self, value, index=0, request=CP2101_CONFIG):
        return ord(self._get_config(value, 1, index=index, request=request))

    def _get_int16_config(self, value, index=0, request=CP2101_CONFIG):
        data = self._get_config(value, 2, index=index, request=request)
        return ord(data[0]) << 8 | ord(data[1])
    
    def get_eeprom_content(self):
        """Reads the entire EEPROM content as one big 1024-byte blob.
        """
        return self._get_config(REG_EEPROM, SIZE_EEPROM)
    
    def get_baudrate_content(self):
        """Return the baudrate table as binary data.
        """
        return self._get_config(REG_EEPROM, SIZE_BAUDRATE_TABLE)

    def get_baudrate_table(self):
        """Returns the baudrate table.
        
        A list containing 4-tuples are returnes.
        Each tuple containes the following data:
        
         * BaudGen: Value used to generate the real baudrate.
         * Time0Reset: Value used to generate the usb timeout.
         * Prescaler: Used to generate the real baudrate.
         * Baudrate: The baudrate which activates this entry.
        """
        data = self.get_baudrate_content()
        return [parse_baudrate_cfg(data[pos:pos+SIZE_BAUDRATE_CFG])
                for pos in range(0, SIZE_BAUDRATE_TABLE, SIZE_BAUDRATE_CFG)]
        
    def set_baudrate_table(self, baudrates):
        """Writes the baudrate table.
        
        See get_baudrate_table() for the structure of the table.
        """
        assert len(baudrates) == SIZE_BAUDRATES
        self.set_baudrate_content(data=''.join(build_baudrate_cfg(*cfg) 
                                               for cfg in baudrates))
    baudrate_table = property(get_baudrate_table, set_baudrate_table)
        
    def get_part_number(self):
        """ The part number of the device.
        
        Returns: 1 for an CP2101
                 2 for an CP2102
                 3 for an CP2103
        """
        return self._get_int8_config(REG_PART_NUMBER)
    
    def get_locked(self):
        """ The lock value of the device.
        
        When True is returnes no data can be written to the device.
        """
        if self._locked is None:
            self._locked = self._get_int8_config(REG_LOCK_VALUE) == LCK_LOCKED
        return self._locked
    
    def set_eeprom_content(self, content):
        """Writes an 1024-byte blob to the EEPROM
        """
        assert len(content) == SIZE_EEPROM, ("EEPROM data must be %i bytes."
                                             % SIZE_EEPROM)
        assert isinstance(content, str), "EEPROM data must be string."
        self._set_config(REG_EEPROM, data=content)
    
    def set_product_id(self, pid):
        """Sets the Product ID
        """
        assert pid > 0x0000 and pid < 0xFFFF
        self._set_config(REG_PRODUCT_ID, pid)
        
    def set_vendor_id(self, vid):
        """Sets the Vendor ID
        """
        assert vid > 0x0000 and vid < 0xFFFF
        self._set_config(REG_VENDOR_ID, vid)
    
    def set_product_string(self, product_string):
        """Sets the product string.
        
        Be aware that the string will be stored as UTF-16 encoded and should not
        exceed SIZE_PRODUCT_STRING 
        """
        self._set_config_string(REG_PRODUCT_STRING, product_string, 
                                SIZE_PRODUCT_STRING)
    
    def set_serial_number(self, serial_number):
        self._set_config_string(REG_SERIAL_NUMBER, serial_number, 
                                SIZE_SERIAL_NUMBER)
    
    def set_max_power(self, max_power):
        assert max_power >= 0 and max_power <= 500
        self._set_config(REG_MAX_POWER, to_div2(max_power))
    
    def set_bus_powered(self, bus_powered):
        if bus_powered:
            self._set_config(REG_CFG_ATTRIBUTES, 0xC0)
        else:
            self._set_config(REG_CFG_ATTRIBUTES, 0x80)

    def set_version(self, version):
        self._set_config(REG_VERSION, to_bcd2(version))

    def set_locked(self, locked):
        """ The lock value of the device.
        
        When True is returnes no data can be written to the device.
        """
        if locked:
            self._set_config(REG_LOCK_VALUE, LCK_LOCKED)
        else:
            self._set_config(REG_LOCK_VALUE, LCK_UNLOCKED)

    def set_values(self, values):
        for name, value in values.items():
            if name not in ['part_number', 'vendor_string']:
                getattr(self, "set_" + name) (value)
            
