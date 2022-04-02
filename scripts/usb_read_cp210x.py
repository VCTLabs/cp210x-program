# -*- coding: utf-8 -*-
import sys
import usb.core
import usb.util


dev = usb.core.find(idVendor = 0x10c4)  # Silicon Labs
if not dev:
    print("No devices found!!")
else:
    print(usb.core.show_devices(idVendor = 0x10c4))
    print('Manufacturer: {}'.format(usb.util.get_string(dev, dev.iManufacturer)))
    print('Product: {}\n'.format(usb.util.get_string(dev, dev.iProduct)))

for config in dev:
    cfg_num = config.bConfigurationValue
    ifaces = config.bNumInterfaces
    print('Configuration {} has {} interfaces.'.format(cfg_num, ifaces))
    for iface in config:
        if dev.is_kernel_driver_active(iface.bInterfaceNumber):
            dev.detach_kernel_driver(iface.bInterfaceNumber)
            print('Iface {} detached'.format(iface.bInterfaceNumber))


# select default => this fails without detaching each iface (/dev/tty*)
dev.set_configuration()


for cfg in dev:
    sys.stdout.write(str(cfg.bConfigurationValue) + '\n')
    for intf in cfg:
        sys.stdout.write('\t' + \
                         str(intf.bInterfaceNumber) + \
                         ',' + \
                         str(intf.bAlternateSetting) + \
                         '\n')
        for ep in intf:
            sys.stdout.write('\t\t' + \
                             str(ep.bEndpointAddress) + \
                             '\n')
    print('')
    print(cfg)


# let the kernel driver reclaim the tty device(s) when we are done
for cfg in dev:
    for iface in cfg:
        dev.attach_kernel_driver(iface.bInterfaceNumber)
