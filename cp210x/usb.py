# Python interface for "usb.h" version 0.1.4.4.4
#
# Copyright (c) 2005 Robert Hoelzl <robert.hoelzl@gmx.de>
# Copyright (c) 2007 Johannes Hoelzl <johannes.hoelzl@gmx.de>
#
# This library is covered by the GNU LGPL, read LICENSE for details.

from ctypes import *
import sys

class LibUsbNotInstalled(OSError):
    pass

try:
    if sys.platform == 'darwin':
        PATH_MAX = 1024
        dll=cdll.LoadLibrary("libusb.dylib")
    elif sys.platform == 'linux2':
        PATH_MAX = 4096
        dll=cdll.LoadLibrary("libusb.so")
    else:
        raise NotImplementedError("Platform %s not supported by usb.py" % sys.platform)
except OSError:
    raise LibUsbNotInstalled() 
    

# helper functions
def func(f, *args, **retval):
    f.restype = retval.get('retval', None)
    f.argtypes = args
    if retval.has_key('rename'): globals()[retval['rename']] = f
    else: globals()[f.__name__[4:]] = f
    
# constants
CLASS_PER_INTERFACE = 0
USB_CLASS_AUDIO = 1
CLASS_COMM = 2
CLASS_HID = 3
CLASS_PRINTER = 7
CLASS_PTP = 6
CLASS_MASS_STORAGE = 8
CLASS_HUB = 9
CLASS_DATA = 10
CLASS_VENDOR_SPEC = 0xff

DT_DEVICE = 0x01
DT_CONFIG = 0x02
DT_STRING = 0x03
DT_INTERFACE = 0x04
DT_ENDPOINT = 0x05

DT_HID = 0x21
DT_REPORT = 0x22
DT_PHYSICAL = 0x23
DT_HUB = 0x29

DT_DEVICE_SIZE = 18
DT_CONFIG_SIZE = 9
DT_INTERFACE_SIZE = 9
DT_ENDPOINT_SIZE = 7
DT_ENDPOINT_AUDIO_SIZE = 9    # Audio extension
DT_HUB_NONVAR_SIZE = 7


class descriptor_header(Structure): _fields_ = [
    ("bLength", c_uint8),
    ("bDescriptorType", c_uint8) ]


class string_descriptor(Structure): _fields_ = [
    ("bLength", c_uint8),
    ("bDescriptorType", c_uint8),
    ("wData", c_uint*1) ]

class hid_descriptor(Structure): _fields_ = [
    ("bLength", c_uint8),
    ("bDescriptorType", c_uint8),
    ("bcdHID", c_uint16),
    ("bCountryCode", c_uint8),
    ("bNumDescriptors", c_uint8) ]

MAXENDPOINTS = 32
class endpoint_descriptor(Structure): _fields_ = [
    ("bLength", c_uint8),
    ("bDescriptorType", c_uint8),
    ("bEndpointAddress", c_uint8),
    ("bmAttributes", c_uint8),
    ("wMaxPacketSize", c_uint16),
    ("bInterval", c_uint8),
    ("bRefresh", c_uint8),
    ("bSynchAddress", c_uint8),

    ("extra", POINTER(c_uint8)),
    ("extralen", c_int) ]


ENDPOINT_ADDRESS_MASK = 0x0f    # in bEndpointAddress
ENDPOINT_DIR_MASK = 0x80

ENDPOINT_TYPE_MASK = 0x03    # in bmAttributes
ENDPOINT_TYPE_CONTROL = 0
ENDPOINT_TYPE_ISOCHRONOUS = 1
ENDPOINT_TYPE_BULK = 2
ENDPOINT_TYPE_INTERRUPT = 3

MAXINTERFACES = 32
class interface_descriptor(Structure): _fields_ = [
    ("bLength", c_uint8),
    ("bDescriptorType", c_uint8),
    ("bInterfaceNumber", c_uint8),
    ("bAlternateSetting", c_uint8),
    ("bNumEndpoints", c_uint8),
    ("bInterfaceClass", c_uint8),
    ("bInterfaceSubClass", c_uint8),
    ("bInterfaceProtocol", c_uint8),
    ("iInterface", c_uint8),

    ("endpoint", POINTER(endpoint_descriptor)),

    ("extra", POINTER(c_uint8)),
    ("extralen", c_int) ]

MAXALTSETTING = 128      # Hard limit
class interface(Structure): _fields_ = [
    ("altsetting", POINTER(interface_descriptor)),

    ("num_altsetting", c_int) ]

MAXCONFIG = 8
class config_descriptor(Structure): _fields_ = [
    ("bLength", c_uint8),
    ("bDescriptorType", c_uint8),
    ("wTotalLength", c_uint16),
    ("bNumInterfaces", c_uint8),
    ("bConfigurationValue", c_uint8),
    ("iConfiguration", c_uint16),
    ("bmAttributes", c_uint8),
    ("MaxPower", c_uint8),

    ("interface", POINTER(interface)),

    ("extra", POINTER(c_uint8)),  # Extra descriptors
    ("extralen", c_int) ]

class device_descriptor(Structure): _fields_ = [
    ("bLength", c_uint8),
    ("bDescriptorType", c_uint8),
    ("bcdUSB", c_uint16),
    ("bDeviceClass", c_uint8),
    ("bDeviceSubClass", c_uint8),
    ("bDeviceProtocol", c_uint8),
    ("bMaxPacketSize0", c_uint8),
    ("idVendor", c_uint16),
    ("idProduct", c_uint16),
    ("bcdDevice", c_uint16),
    ("iManufacturer", c_uint8),
    ("iProduct", c_uint8),
    ("iSerialNumber", c_uint8),
    ("bNumConfigurations", c_uint8) ]

class ctrl_setup(Structure): _fields_ = [
    ("bRequestType", c_uint8),
    ("bRequest", c_uint8),
    ("wValue", c_uint16),
    ("wIndex", c_uint16),
    ("wLength", c_uint16) ]


REQ_GET_STATUS = 0x00
REQ_CLEAR_FEATURE = 0x01
# 0x02 is reserved
REQ_SET_FEATURE = 0x03
# 0x04 is reserved
REQ_SET_ADDRESS = 0x05
REQ_GET_DESCRIPTOR = 0x06
REQ_SET_DESCRIPTOR = 0x07
REQ_GET_CONFIGURATION = 0x08
REQ_SET_CONFIGURATION = 0x09
REQ_GET_INTERFACE = 0x0A
REQ_SET_INTERFACE = 0x0B
REQ_SYNCH_FRAME = 0x0C

TYPE_STANDARD = (0x00 << 5)
TYPE_CLASS = (0x01 << 5)
TYPE_VENDOR = (0x02 << 5)
TYPE_RESERVED = (0x03 << 5)

RECIP_DEVICE = 0x00
RECIP_INTERFACE = 0x01
RECIP_ENDPOINT = 0x02
RECIP_OTHER = 0x03

ENDPOINT_IN = 0x80
ENDPOINT_OUT = 0x00

# Error codes
ERROR_BEGIN = 500000

#if 1
#define USB_LE16_TO_CPU(x) do { x = ((x & 0xff) << 8) | ((x & 0xff00) >> 8); } while(0)
#else
#define USB_LE16_TO_CPU(x)
#endif

device_p = POINTER("device")
bus_p = POINTER("bus")

class device(Structure): _fields_ = [
    ("next", device_p),
    ("prev", device_p),
    ("filename", c_char*(PATH_MAX + 1)),

    ("bus", bus_p),
    ("descriptor", device_descriptor),
    ("config", POINTER(config_descriptor)),

    ("dev", c_void_p),    # Darwin support

    ("devnum", c_char),

    ("num_children", c_uint8),
    ("children", POINTER(device_p)) ]
SetPointerType(device_p, device)

class bus(Structure): _fields_ = [
    ("next", bus_p),
    ("prev", bus_p),

    ("dirname", c_char*(PATH_MAX + 1)),

    ("devices", device_p),
    ("location", c_uint),

    ("root_dev", device_p) ]
SetPointerType(bus_p, bus)


dev_handle_p = c_void_p


func(dll.usb_open, device_p, retval=dev_handle_p, rename="_open")
func(dll.usb_close, dev_handle_p, retval=c_int)
func(dll.usb_get_string, dev_handle_p, c_int, c_int, c_char_p, c_int, retval=c_int)
func(dll.usb_get_string_simple, dev_handle_p, c_int, c_char_p, c_int, retval=c_int)
func(dll.usb_get_descriptor_by_endpoint, dev_handle_p, c_int, c_uint8, c_uint8, c_void_p, c_int, retval=c_int)
func(dll.usb_get_descriptor, dev_handle_p, c_uint8, c_uint8, c_void_p, c_int, retval=c_int)

func(dll.usb_bulk_write, dev_handle_p, c_int, c_char_p, c_int, c_int, retval=c_int)
func(dll.usb_bulk_read, dev_handle_p, c_int, c_char_p, c_int, c_int, retval=c_int)
func(dll.usb_interrupt_write, dev_handle_p, c_int, c_char_p, c_int, c_int, retval=c_int)
func(dll.usb_interrupt_read, dev_handle_p, c_int, c_char_p, c_int, c_int, retval=c_int)
func(dll.usb_control_msg, dev_handle_p, c_int, c_int, c_int, c_int, c_char_p, c_int, c_int, retval=c_int)
func(dll.usb_set_configuration, dev_handle_p, c_int, retval=c_int)
func(dll.usb_claim_interface, dev_handle_p, c_int, retval=c_int)
func(dll.usb_release_interface, dev_handle_p, c_int, retval=c_int)
func(dll.usb_set_altinterface, dev_handle_p, c_int, retval=c_int)
func(dll.usb_resetep, dev_handle_p, c_uint16, retval=c_int)
func(dll.usb_clear_halt, dev_handle_p, c_uint16, retval=c_int)
func(dll.usb_reset, dev_handle_p, retval=c_int)
     
func(dll.usb_strerror, retval=c_char_p)
     
func(dll.usb_init)
func(dll.usb_set_debug, c_int)
func(dll.usb_find_busses, retval=c_int)
func(dll.usb_find_devices, retval=c_int)
func(dll.usb_device, dev_handle_p, retval=device_p, rename="get_device")
func(dll.usb_get_busses, retval=bus_p)

func(dll.usb_detach_kernel_driver_np, dev_handle_p, c_int, retval=c_int)

# workaround for bug in ctypes 0.9.6 (cannot create functions with c_void_p as retval)
def open(dev):
    return cast(_open(dev), dev_handle_p)
