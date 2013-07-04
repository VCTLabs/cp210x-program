# -*- coding: utf-8 -*-
# Copyright (c) 2007 Johannes Hölzl <johannes.hoelzl@gmx.de>
#
# This library is covered by the GNU LGPL, read LICENSE for details.

import cp210x
from cp210x import from_binary, to_binary, VALUES

__all__ = ['EEPROM', 'HexFileError']

POS_BAUDRATE_TABLE  = 0x0000
POS_PART_NUMBER     = 0x01FF
POS_STRING_DESC_0   = 0x0200
POS_PRODUCT_STRING  = 0x0208
POS_SERIAL_NUMBER   = 0x0307
POS_VENDOR_ID       = 0x0390
POS_PRODUCT_ID      = 0x0392
POS_VERSION         = 0x0394
POS_CFG_ATTRIBUTES  = 0x03A1
POS_MAX_POWER       = 0x03A2
POS_VENDOR_STRING   = 0x03C3
POS_LOCK_VALUE      = 0x03FF

class HexFileError(StandardError):
    pass

def checksum(line):
    return sum(ord(c) for c in line) & 0xFF

def _int_value(position, size, read=lambda x:x, write=lambda x:x):
    def get(self):
        return read(from_binary(self.get(position, size)))
    def set(self, value):
        self.set(position, to_binary(write(value), size))
    return property(get, set)
    
def _str_value(position, max_desc_size):
    def get(self):
        desc_size = from_binary(self.get(position, 1))
        assert desc_size <= max_desc_size and desc_size >= 2, "desc_size: %d, max: %d" % (desc_size, max_desc_size)
        assert self.get(position + 1, 1) == '\x03', "Missing 0x03 at %04X" % (position + 1)
        return self.get(position + 2, desc_size - 2).decode('utf-16-le')
        
    def set(self, value):
        encoded = value.encode('utf-16-le')
        desc_size = len(encoded) + 2
        assert desc_size <= max_desc_size
        self.set(position, chr(desc_size) + '\x03' + encoded)
        
    return property(get, set)

class EEPROM(object):
    START_ADDRESS = 0x3600
    def __init__(self, content=None):
        if isinstance(content, str) or content is None:
            assert content is None or len(content) == cp210x.SIZE_EEPROM
            self.content = content
        elif isinstance(content, cp210x.Cp210xProgrammer):
            self.content = content.get_eeprom_content()
        else:
            self.parse_hex_file(content.read())

    def write_to_cp210x(self, cp210xDevice):
        cp210xDevice.set_eeprom_content(self.content)
            
    def parse_hex_file(self, hex_content):
        self.content = ''
        address = self.START_ADDRESS
        for tag in hex_content.split('\n'):
            if not tag.startswith(':'):
                raise HexFileError("Line doesn't start with ':'")
            
            try:
                content = tag[1:].decode('hex')
            except TypeError:
                raise HexFileError("Hex data expected")
            
            if len(content) < 5:
                raise HexFileError("Line to short")

            if checksum(content) != 0:
                raise HexFileError("Checksum error")
        
            size = from_binary(content[0])
            tag_address = from_binary(content[1:3], le=False)
            tag_type = from_binary(content[3:4])
            line = content[4:-1]
            
            if tag_type == 0x00:
                if tag_address != address:
                    raise HexFileError("Expected address %04X but found %04X"
                                       % (address, tag_address))
                self.content += line
                address += len(line)
            elif tag_type == 0x01:
                if size != 0 or len(line) != 0:
                    raise HexFileError("Defekt end tag")
                break
                
            else:
                raise HexFileError("Unknown tag type %02X" % tag_type)

    def build_hex_file(self):
        for tag_start in range(0, len(self.content), 0x10):
            line = self.content[tag_start:tag_start+0x10]
            address = self.START_ADDRESS + tag_start
            tag = (to_binary(len(line), 1) + 
                   to_binary(address, le=False) + 
                   '\x00' + 
                   line)
            cs = checksum(tag)
            if cs == 0:
                tag += '\x00'
            else:
                tag += chr(0x100 - cs)
            yield ":%s\n" % tag.encode('hex')
        yield ":00000001FF\n"

    def write_hex_file(self, f):
        if isinstance(f, str):
            f = file(f, 'wb')
            do_close = True
        else:
            do_close = False
        for line in self.build_hex_file():
            f.write(line)
        if do_close:
            f.close()

    def read_hex_file(self, f):
        if isinstance(f, str):
            f = file(f, 'rb')
            do_close = True
        else:
            do_close = False
        self.parse_hex_file(f.read())
        if do_close:
            f.close()

    def get(self, pos, length):
        return self.content[pos:pos+length]
    
    def set(self, pos, data):
        self.content = (self.content[:pos] + 
                        data + 
                        self.content[pos + len(data):])
   
    def _get_baudrate_table(self):
        dat = self.get(POS_BAUDRATE_TABLE, cp210x.SIZE_BAUDRATE_TABLE)
        return [cp210x.parse_baudrate_cfg(dat[pos:pos+cp210x.SIZE_BAUDRATE_CFG])
                for pos in range(0, cp210x.SIZE_BAUDRATE_TABLE, 
                                 cp210x.SIZE_BAUDRATE_CFG)]
    def _set_baudrate_table(self, baudrates):
        assert len(baudrates) == cp210x.SIZE_BAUDRATES
        self.set(POS_BAUDRATE_TABLE, 
                 ''.join(cp210x.build_baudrate_cfg(*cfg) for cfg in baudrates))
    baudrate_table = property(_get_baudrate_table, _set_baudrate_table)
    product_string = _str_value(POS_PRODUCT_STRING, cp210x.SIZE_PRODUCT_STRING)
    serial_number = _str_value(POS_SERIAL_NUMBER, cp210x.SIZE_SERIAL_NUMBER)
    part_number = _int_value(POS_PART_NUMBER, 1)
    vendor_id = _int_value(POS_VENDOR_ID, 2)
    product_id = _int_value(POS_PRODUCT_ID, 2)
    version = _int_value(POS_VERSION, 2, 
                         cp210x.from_bcd2, cp210x.to_bcd2)
    bus_powered = _int_value(POS_CFG_ATTRIBUTES, 1, 
                             lambda a: bool(a & 0x40), 
                             lambda a: 0xC0 if a else 0x80)
    max_power = _int_value(POS_MAX_POWER, 1, lambda p: p*2, cp210x.to_div2)
    vendor_string = _str_value(POS_VENDOR_STRING, cp210x.SIZE_VENDOR_STRING)
    locked = _int_value(POS_LOCK_VALUE, 1, 
                        lambda l: l == cp210x.LCK_LOCKED, 
                        lambda b: cp210x.LCK_LOCKED if b
                                  else cp210x.LCK_UNLOCKED)
        
    def get_values(self):
        return dict((name, getattr(self, name)) for name, type in VALUES)

    def set_values(self, values):
        for name, value in values.items():
            setattr(self, name, value)

            
