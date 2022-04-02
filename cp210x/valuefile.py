# -*- coding: utf-8 -*-
# Copyright (c) 2007 Johannes Hölzl <johannes.hoelzl@gmx.de>
#
# This library is covered by the GNU LGPL, read LICENSE for details.

# For documentation of the baudrate table see:
#
# [AN205] Silicon Labs Application Note 205 Rev. 0.3
# http://www.silabs.com/public/documents/tpub_doc/anote/Microcontrollers/Interface/en/an205.pdf

import re
from configparser import ConfigParser

from .cp210x import SIZE_BAUDRATES, VALUES

__all__ = [
    'read_file',
    'write_file',
    'update_values',
    'PrescalerIsZero',
    'ValuesFileError',
]


class ValuesError(Exception):
    pass


class PrescalerIsZero(ValuesError):
    pass


class ValuesFileError(ValuesError):
    pass


version_pattern = re.compile(r'^\s*(\d\d?)\.(\d\d?)\s*$')


def read_version(s):
    match = version_pattern.match(s)
    if match is None:
        raise ValueError("Version does not match 'xx.yy'")
    return (int(match.group(1)), int(match.group(2)))


def write_version(v):
    return '%d.%02d' % v


def read_hex(s):
    return int(s.strip(), 16)


def write_hex(num):
    return '%04X' % num


def write_bool(b):
    if b:
        return 'yes'
    else:
        return 'no'


def read_bool(s):
    s = s.strip().lower()
    if s not in ['true', 'yes', 'false', 'no']:
        raise ValueError(
            "Boolean must be either 'true', 'yes', 'false' or 'no'."
        )
    return s in ['true', 'yes']


def read_baudrate_info(s):
    values = s.split(',')
    if len(values) != 3:
        raise ValueError('Baudrate info must be three comma-separated items')
    try:
        baudgen = read_hex(values[0])
    except ValueError:
        raise ValueError('The first baudrate info must be a hex-value')
    try:
        timer0 = read_hex(values[1])
    except ValueError:
        raise ValueError('The second baudrate info must be a hex-value')
    try:
        prescale = int(values[2])
    except ValueError:
        raise ValueError('The thirdbaudrate info must be a number')
    return (baudgen, timer0, prescale)


TYPES = {
    'boolean': (read_bool, write_bool),
    'int': (int, str),
    'id': (read_hex, write_hex),
    'string': (str, str),
    'version': (read_version, write_version),
}


def read_file(fp):
    cp = ConfigParser(inline_comment_prefixes=('#', ';'))
    if isinstance(fp, str):
        cp.read([fp])
    else:
        cp.readfp(fp)

    values = {}

    for name, type in VALUES:
        if name == 'baudrate_table':
            continue
        reader, _ = TYPES[type]
        if cp.has_option('usb device', name):
            try:
                values[name] = reader(cp.get('usb device', name))
            except ValueError as err:
                raise ValuesFileError("Key '%s': %s" % (name, str(err)))

    if cp.has_section('baudrate table'):
        baudrate_table = []
        for name, value in cp.items('baudrate table'):
            try:
                baudrate = int(name)
            except ValueError:
                raise ValuesFileError(
                    "Key names in 'baudrate table' must be"
                    ' baudrate numbers.'
                )
            try:
                baudrate_table.append(read_baudrate_info(value) + (baudrate,))
            except ValueError as err:
                raise ValuesFileError(
                    'Wrong baudrate info %i: %s' % (baudrate, str(err))
                )
        baudrate_table.sort(key=(lambda i: i[3]), reverse=True)

        values['baudrate_table'] = baudrate_table
    return values


def write_file(fp, values):
    fp.write('[usb device]\n')

    for name, type in VALUES:
        if name == 'baudrate_table':
            continue
        _, writer = TYPES[type]
        if name in values:
            fp.write('%s = %s\n' % (name, writer(values[name])))

    if 'baudrate_table' in values:
        fp.write('\n')
        fp.write('[baudrate table]\n')
        for (baudgen, timegen, prescaler, baudrate) in sorted(
            values['baudrate_table'], key=(lambda i: i[3]), reverse=True
        ):
            fp.write(
                '%7d = %04X, %04X, %d # %s\n'
                % (
                    baudrate,
                    baudgen,
                    timegen,
                    prescaler,
                    show_baudrate(baudgen, timegen, prescaler),
                )
            )


def calc_baudrate(baudgen, timegen, prescaler):
    # This formulas are from AN205 page 5.
    if prescaler == 0:
        raise PrescalerIsZero('Prescaler is 0')
    baudrate = (24000000.0 / prescaler) / (0x10000 - baudgen)
    return (baudrate, (0x10000 - timegen) * 2)


def show_baudrate(baudgen, timegen, prescaler):
    try:
        baudrate, timeout = calc_baudrate(baudgen, timegen, prescaler)
    except PrescalerIsZero:
        return 'Wrong data, Prescaler is 0.'
    if timeout >= 1000:
        timeout = '%1.3f ms' % (float(timeout) / 1000)
    else:
        timeout = '%d us' % timeout
    if baudrate is None:
        return ', %s' % (timeout)
    else:
        return '%7.0f Baud, %s' % (baudrate, timeout)


def update_values(v, new, dev):
    old_baudrate_table = v.get('baudrate_table')
    new_baudrate_table = new.get('baudrate_table')

    v.update(new)

    # update baudrate table
    # it is needed, that the baudrate table has 32 entries when it is written
    # to the eeprom or device.
    if (old_baudrate_table is not None or new_baudrate_table is not None) and (
        new_baudrate_table is None or len(new_baudrate_table) < SIZE_BAUDRATES
    ):

        if old_baudrate_table is not None:
            if len(old_baudrate_table) < SIZE_BAUDRATES:
                baudrate_table = old_baudrate_table
            else:
                baudrate_table = list(
                    merge_baudrate_table(
                        dev.baudrate_table, old_baudrate_table
                    )
                )
        else:
            baudrate_table = dev.baudrate_table

        if new_baudrate_table:
            baudrate_table = list(
                merge_baudrate_table(baudrate_table, new_baudrate_table)
            )
        v['baudrate_table'] = baudrate_table


def merge_baudrate_table(old, new):
    for (old_info, (start, stop)) in zip(old, REQUEST_BAUDRATE_RANGES):
        for baudgen, timer, prescaler, baudrate in new:
            if (start is None or baudrate <= start) and baudrate >= stop:
                yield (baudgen, timer, prescaler, baudrate)
                break
        else:
            yield old_info


# fmt: off
REQUEST_BAUDRATE_RANGES = [
    # The table data is from AN205 Table 1 on page 1.
    # Start     End       Default Baudrate
    (None,    2457601), #  Undefined
    (2457600, 1474561), #  Undefined
    (1474560, 1053258), #  Undefined
    (1053257,  670255), #  921600
    ( 670254,  567139), #  576000
    ( 567138,  491521), #  500000
    ( 491520,  273067), #  460800
    ( 273066,  254235), #  256000
    ( 254234,  237833), #  250000
    ( 237832,  156869), #  230400
    ( 156868,  129348), #  153600
    ( 129347,  117029), #  128000
    ( 117028,   77609), #  115200
    (  77608,   64112), #   76800
    (  64111,   58054), #   64000
    (  58053,   56281), #   57600
    (  56280,   51559), #   56000
    (  51558,   38602), #   51200
    (  38601,   28913), #   38400
    (  28912,   19251), #   28800
    (  19250,   16063), #   19200
    (  16062,   14429), #   16000
    (  14428,    9613), #   14400
    (   9612,    7208), #    9600
    (   7207,    4804), #    7200
    (   4803,    4001), #    4800
    (   4000,    2401), #    4000
    (   2400,    1801), #    2400
    (   1800,    1201), #    1800
    (   1200,     601), #    1200
    (    600,     301), #     600
    (    300,      57), #     300
]
# fmt: on
