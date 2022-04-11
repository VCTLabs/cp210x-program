# -*- coding: utf-8 -*-
# Copyright (c) 2007 Johannes Hölzl <johannes.hoelzl@gmx.de>
#
# This library is covered by the GNU LGPL, read LICENSE for details.
"""Provides access to the EEPROM of Silabs CP210x devices

The following class is available:

class Cp210xProgrammer:
    Provides direct access to the CP210x, can be used to write single data
    directly or via an EEPROM image.
"""

import usb
from usb.util import CTRL_IN, CTRL_OUT, CTRL_TYPE_VENDOR

__all__ = ['Cp210xProgrammer', 'Cp210xError']

CP210x_CONFIG = 0xFF

REG_VENDOR_ID = 0x3701
REG_PRODUCT_ID = 0x3702
REG_PRODUCT_STRING = 0x3703
REG_SERIAL_NUMBER = 0x3704
REG_CFG_ATTRIBUTES = 0x3705
REG_MAX_POWER = 0x3706
REG_VERSION = 0x3707
REG_UNKNOWN = 0x3708
REG_EEPROM = 0x3709
REG_LOCK_VALUE = 0x370A
REG_PART_NUMBER = 0x370B

SIZE_EEPROM = 0x0400
SIZE_PRODUCT_STRING = 255
SIZE_SERIAL_NUMBER = 128
SIZE_BAUDRATES = 32
SIZE_BAUDRATE_CFG = 10
SIZE_BAUDRATE_TABLE = SIZE_BAUDRATES * SIZE_BAUDRATE_CFG
SIZE_VENDOR_STRING = 50

# Buffer size limits
# (see AN721: CP210x/CP211x Device Customization Guide)
CP210x_MAX_PRODUCT_STRLEN = (SIZE_PRODUCT_STRING - 2) // 2
CP210x_MAX_SERIAL_STRLEN = (SIZE_SERIAL_NUMBER - 2) // 2

LCK_LOCKED = 0xF0
LCK_UNLOCKED = 0xFF

VID_SILABS = 0x10C4
PID_CP210x = 0xEA60

VALUES = [
    ('product_string', 'string'),
    ('serial_number', 'string'),
    ('vendor_id', 'id'),
    ('product_id', 'id'),
    ('version', 'version'),
    ('bus_powered', 'boolean'),
    ('max_power', 'int'),
    ('locked', 'boolean'),
    ('part_number', 'int'),
    ('vendor_string', 'string'),
    ('baudrate_table', 'list'),
]


def to_div2(p):
    value = int(p / 2)
    if (value * 2) < p:
        value += 1
    return value


def to_bcd(i):
    assert i >= 0 and i <= 99
    return (i // 10) << 4 | (i % 10)


def to_bcd2(i_j_tuple):
    (i, j) = i_j_tuple
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
        value = value << 8 | int(byte)
    return value


def to_binary(value, size=2, le=True):
    data = []
    for i in range(size):
        data.append(value & 0xFF)
        value >>= 8
    if le:
        return bytes(data)
    else:
        return bytes(data[::-1])


def parse_baudrate_cfg(data):
    return (
        from_binary(data[0:2], le=False),
        from_binary(data[2:4], le=False),
        from_binary(data[4:5]),
        from_binary(data[6:10]),
    )


def build_baudrate_cfg(baudgen, timer0reload, prescaler, baudrate):
    return (
        to_binary(baudgen, le=False)
        + to_binary(timer0reload, le=False)
        + to_binary(prescaler, 1)
        + bytes([0])
        + to_binary(baudrate, 4)
    )


class Cp210xError(IOError):
    pass


class DeviceLocked(Cp210xError):
    pass


class Cp210xMatch(object):
    def __init__(self, patterns):
        self.patterns = patterns

    def __call__(self, dev):
        for pattern in self.patterns:
            for name, value in list(pattern.items()):
                if getattr(dev, name) != value:
                    return False
            return True
        return False


class Cp210xProgrammer(object):
    """Program a Silabs CP2101, CP2102 or CP2103

    This module provides access to Silabs CP210x devices to set some USB
    descriptor fields and some USB descriptor strings.

    The following fields can be set:

     * Vendor ID
     * Product ID
     * Product String
     * Serial Number
     * Device Version
     * Bus Powered
     * max. Power consumption

    Either use PyUSB to find a device, and pass the usb.Device object
    to the constructor, or use Cp210xProgrammer.list_device() to list all
    devices matching certain pattern.
    """

    TIMEOUT = 300  # ms

    @classmethod
    def list_devices(
        self, patterns=[{'idVendor': VID_SILABS, 'idProduct': PID_CP210x}]
    ):
        """Yields a list of devices matching certain patterns.

        param patterns: This must be a list of dictionaries. Each device
            in the usb tree is matched against all patterns in the list.

            All fields of the descriptors are compared with the corresponding
            values in the dictionary. A device matches the pattern only if all
            values match.

        For example:

        >> list(Cp210xProgrammer.list_device([{ 'idVendor': VID_SILABS,
                                           'idProduct': PID_CP210x }]))
        [device(...)]

        """

        return usb.core.find(find_all=True, custom_match=Cp210xMatch(patterns))

    def __init__(self, usbdev):
        self.usbdev = usbdev
        self._locked = None
        self.has_kernel_driver = False
        self.has_kernel_driver = usbdev.is_kernel_driver_active(0)
        if self.has_kernel_driver:
            cfg = usbdev.get_active_configuration()
            self.intf = cfg[(0, 0)].bInterfaceNumber
            usbdev.detach_kernel_driver(self.intf)
        usbdev.set_configuration()

    def reset(self):
        """Force the USB stack to reset the device.

        Resets the device through an hard reset over the port to which the
        device is connected. After that happend the EEPROM content in the device
        is reread and the device's descriptors are the one written to it.
        """
        self.usbdev.reset()

    def __del__(self):
        if self.has_kernel_driver:
            self.usbdev.attach_kernel_driver(self.intf)

    def _set_config(self, value, index=0, data=None, request=CP210x_CONFIG):
        if self.get_locked():
            raise DeviceLocked()

        res = self.usbdev.ctrl_transfer(
            CTRL_OUT | CTRL_TYPE_VENDOR, request, value, index, data
        )
        if data is not None and res != len(data):
            raise Cp210xError(
                'Short write (%d of %d bytes)' % (res, len(data))
            )

    def _set_config_string(self, value, content, max_desc_size):
        assert isinstance(content, str)
        encoded = content.encode('utf-16-le')
        desc_size = len(encoded) + 2
        assert desc_size <= max_desc_size
        self._set_config(
            value, data=desc_size.to_bytes(1, 'big') + b'\x03' + encoded
        )

    def _get_config(self, value, length, index=0, request=CP210x_CONFIG):
        print(
            'usb ctrl msg: request, value, index, length:\n  {} {} {} {}'.format(
                request, value, index, length
            )
        )
        res = self.usbdev.ctrl_transfer(
            CTRL_IN | CTRL_TYPE_VENDOR, request, value, index, length
        )
        return res.tobytes()

    def _get_int8_config(self, value, index=0, request=CP210x_CONFIG):
        return ord(self._get_config(value, 1, index=index, request=request))

    def _get_int16_config(self, value, index=0, request=CP210x_CONFIG):
        data = self._get_config(value, 2, index=index, request=request)
        return ord(data[0]) << 8 | ord(data[1])

    def get_eeprom_content(self):
        """Get the entire EEPROM content as one big 1024-byte blob."""
        return self._get_config(REG_EEPROM, SIZE_EEPROM)

    def get_baudrate_content(self):
        """Get the baudrate table as binary data."""
        return self._get_config(REG_EEPROM, SIZE_BAUDRATE_TABLE)

    @property
    def baudrate_table(self):
        """Get the baudrate table.

        A list containing 4-tuples is returned.
        Each tuple contains the following data:

         * BaudGen: Value used to generate the baudrate.
         * Time0Reset: Value used to generate the usb timeout.
         * Prescaler: Used to down-scale the baudrate.
         * Baudrate: The baudrate which activates this entry.
        """
        data = self.get_baudrate_content()
        return [
            parse_baudrate_cfg(data[pos : pos + SIZE_BAUDRATE_CFG])
            for pos in range(0, SIZE_BAUDRATE_TABLE, SIZE_BAUDRATE_CFG)
        ]

    @baudrate_table.setter
    def baudrate_table(self, baudrates):
        """Write the baudrate table.

        See get_baudrate_table() for the structure of the table.
        """
        assert len(baudrates) == SIZE_BAUDRATES
        self.set_baudrate_content(
            data=''.join(build_baudrate_cfg(*cfg) for cfg in baudrates)
        )

    def get_part_number(self):
        """Get the part number of the device.

        Returns: 1 for a CP2101
                 2 for a CP2102
                 3 for a CP2103
        """
        return self._get_int8_config(REG_PART_NUMBER)

    def get_locked(self):
        """Read the lock value of the device.

        When True is returnes no data can be written to the device.
        """
        if self._locked is None:
            self._locked = self._get_int8_config(REG_LOCK_VALUE) == LCK_LOCKED
        return self._locked

    def set_eeprom_content(self, content):
        """Write a 1024-byte blob to the EEPROM"""
        assert len(content) == SIZE_EEPROM, (
            'EEPROM data must be %i bytes.' % SIZE_EEPROM
        )
        assert isinstance(content, bytes), 'EEPROM data must be bytes.'
        self._set_config(REG_EEPROM, data=content)

    def set_product_id(self, pid):
        """Set the Product ID"""
        assert pid > 0x0000 and pid < 0xFFFF
        self._set_config(REG_PRODUCT_ID, pid)

    def set_vendor_id(self, vid):
        """Set the Vendor ID"""
        assert vid > 0x0000 and vid < 0xFFFF
        self._set_config(REG_VENDOR_ID, vid)

    def set_product_string(self, product_string):
        """Set the product string.

        The string will be encoded with UTF-16 and must not exceed
        CP210x_MAX_PRODUCT_STRLEN.
        For Unicode Plane 0 (BMP; code points 0-FFFF), this specifies
        the maximum length of the string in characters.
        """
        self._set_config_string(
            REG_PRODUCT_STRING, product_string, SIZE_PRODUCT_STRING
        )

    def set_serial_number(self, serial_number):
        """Set the serial number string.

        The string will be encoded with UTF-16 and must not exceed
        CP210x_MAX_SERIAL_STRLEN.
        For Unicode Plane 0 (BMP; code points 0-FFFF), this specifies
        the maximum length of the string in characters.
        """
        self._set_config_string(
            REG_SERIAL_NUMBER, serial_number, SIZE_SERIAL_NUMBER
        )

    def set_max_power(self, max_power):
        """Set maximum power consumption."""
        assert max_power >= 0 and max_power <= 500
        self._set_config(REG_MAX_POWER, to_div2(max_power))

    def set_bus_powered(self, bus_powered):
        """Set the bus-powered flag in the device descriptor."""
        if bus_powered:
            self._set_config(REG_CFG_ATTRIBUTES, 0xC0)
        else:
            self._set_config(REG_CFG_ATTRIBUTES, 0x80)

    def set_version(self, version):
        """Set the device version ."""
        self._set_config(REG_VERSION, to_bcd2(version))

    def set_locked(self, locked):
        """Set the lock value of the device.

        When True is returned no data can be written to the device.
        """
        if locked:
            self._set_config(REG_LOCK_VALUE, LCK_LOCKED)
        else:
            self._set_config(REG_LOCK_VALUE, LCK_UNLOCKED)

    def set_values(self, values):
        for name, value in list(values.items()):
            if name not in ['part_number', 'vendor_string']:
                getattr(self, 'set_' + name)(value)
