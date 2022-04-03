# -*- coding: utf-8 -*-
import os
import subprocess as sp
import sys
from pathlib import Path, PurePath

# test data
orig_hex_data = '''\
:10360000fff0fffa010060e31600fff0fffa01008f
:1036100060e31600ffecfff80100804f1200ffe6a8
:10362000fff6010000100e00ffd6fff0010000caf7
:103630000800ffd0ffee010020a10700ffccffec47
:10364000010000080700ffa2ffdc010000e8030002
:10365000ffa0ffdc010090d00300ff98ffd901001c
:1036600000840300ff64ffc5010000580200ff440e
:10367000ffb9010000f40100ff30ffb2010000c2f9
:103680000100fec8ff8b0100002c0100fe89ff73c2
:10369000010000fa0000fe5fff63010000e100008e
:1036a000fe53ff5f0100c0da0000fe2bff50010057
:1036b00000c80000fd8fff15010000960000fcbf50
:1036c000fec7010080700000fb1efe2b0100004bb6
:1036d0000000fa24fe0c0100803e0000f97dfe0c83
:1036e000010040380000f63cfe0c0100802500007f
:1036f000f2fbfe0c0100201c0000ec78fe0c010027
:10370000c0120000e890fe0c0100a00f0000d8f0ed
:10371000fe0c010060090000cbebfe0c0100080765
:103720000000b1e0fe0c0100b004000063c0fe0c1c
:10373000010058020000b1e0fe0c04002c01000062
:103740000000000000000000000000000000000079
:103750000000000000000000000000000000000069
:103760000000000000000000000000000000000059
:103770000000000000000000000000000000000049
:103780000000000000000000000000000000000039
:103790000000000000000000000000000000000029
:1037a0000000000000000000000000000000000019
:1037b0000000000000000000000000000000000009
:1037c00000000000000000000000000000000000f9
:1037d00000000000000000000000000000000000e9
:1037e00000000000000000000000000000000000d9
:1037f00000000000000000000000000000000002c7
:1038000004030904000000004a0343005000320092
:1038100031003000320020005500530042002000eb
:1038200074006f0020005500410052005400200039
:1038300042007200690064006700650020004300d8
:103840006f006e00740072006f006c006c00650009
:1038500072000000000000000000000000000000f6
:103860000000000000000000000000000000000058
:103870000000000000000000000000000000000048
:103880000000000000000000000000000000000038
:103890000000000000000000000000000000000028
:1038a0000000000000000000000000000000000018
:1038b0000000000000000000000000000000000008
:1038c00000000000000000000000000000000000f8
:1038d00000000000000000000000000000000000e8
:1038e00000000000000000000000000000000000d8
:1038f00000000000000000000000000000000000c8
:10390000000000000000000a0330003000300031e9
:1039100000000000000000000000000000000000a7
:103920000000000000000000000000000000000097
:103930000000000000000000000000000000000087
:103940000000000000000000000000000000000077
:103950000000000000000000000000000000000067
:103960000000000000000000000000000000000057
:103970000000000000000000000000000000000047
:1039800000000000000000021201100100000040d1
:10399000c41060ea000101020301090220000101d4
:1039a0000080320904000002ff00000207058102c6
:1039b0004000000705010240000000000000000078
:1039c0000000001a03530069006c00690063006f77
:1039d000006e0020004c00610062007300000000d7
:1039e00000000000000000000000000000000000d7
:1039f000000000000000000000000000000000ffc8
:00000001FF
'''

orig_hex_data_bytes = bytes(orig_hex_data.encode('utf-8'))
orig_hex_file = "cp2102-orig.hex"

out_file = 'test.out'
out_path = Path('testdata')


def test_text_file_io():
    orig_hex_data_txt = out_path.joinpath(orig_hex_file).read_text()

    assert orig_hex_data == orig_hex_data_txt


def test_bin_file_io():
    orig_hex_data_bin = out_path.joinpath(orig_hex_file).read_bytes()

    assert orig_hex_data_bin == orig_hex_data_bytes


def test_hex_file_output():
    outfile = out_path.joinpath(out_file)

    #for child in out_path.iterdir(): print(child)
    assert outfile.read_text() == orig_hex_data
    assert outfile.read_bytes() == orig_hex_data_bytes
