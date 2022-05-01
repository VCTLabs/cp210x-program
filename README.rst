================
 cp210x-program
================

|ci| |wheels| |release| |badge|

|tag| |license| |python| |pylint|

|pre|

The goal of this library is to provide access to the EEPROM of an Silabs CP210x
under Linux.

.. warning:: THE LEGACY VERSION OF cp210x-program IS NOT FULLY TESTED, AND MAY RENDER
             YOUR CP210x USELESS OR DESTROY IT.  Be aware that the current
             (legacy) version was only tested on the original CP2102 part.
             Similarly, the cp2102N programmer in ``ext/badge`` is only
             "lightly" tested here.  Be warned...

Quick Start
===========

The CP210x is a series of USB-to-serial chip used in a lot of USB devices
(similar to FTDIs and PL2303). Certain CP210x devices have an EEPROM on
the chip which can be programmed via USB, while others only have the OTP
EPROM (which cannot be reprogrammed; see `Model notes`_). Silabs provides
various source code examples for Windows and Linux, and multiple drivers
for Windows.

The original ``cp210x-program`` uses results from monitoring the USB bus when
the windows library programs the CP210x device. The windows library was not
disassembled for the original protocol analysis.

Dependencies
------------

* Python >= 3
* PyUSB

For the external cp2102N tool:

* GNU or clang toolchain
* make
* libusb-1.0

Since libusb is available on most Linux, Mac OS X and FreeBSD cp210x-program
should run flawlessly on these platforms. Currently it is tested in Github CI
on Linux (Ubuntu), MacOS, and Windows (note the latter relies on the base GNU
libraries and tools installed on the Github CI runners).

If cp210x-program should run as non-root user, add the udev rule found in
doc/45-cp210x-programming.rules to /etc/udev/rules.d. When devices with already
programmed IDs are reprogrammed at this IDs to 45-cp210x-programming.rules.

Install deps on Ubuntu::

  $ sudo apt install python3-usb

Usage
-----

Read EEPROM content into hexfile::

  $ cp210x-program --read-cp210x -f eeprom-content.hex

Show EEPROM content from device 002 on bus 001::

  $ cp210x-program --read-cp210x -m 001/002

Write some data to device with vendor id 0x10C4 and product id 0xEA62::

  $ cp210x-program --write-cp210x -m 10C4:EA62 \
                 --set-product-string="Product String" \
                 --set-max-power=100 \
                 --set-bus-powered=no

Write default data to device::

  $ cp210x-program --write-cp210x -F testdata/cp2102-orig.hex

This is for example required when the baud rate table is corrupted and
the CP210x always uses 500kBit/sec as baudrate.

TODO
----

* (re)Test on CP2102 and CP2103 (legacy parts)
* read config blob from CP2102N (new part)

Dev tools
=========

Local tool dependencies to aid in development; install both tools for
maximum enjoyment.

Tox
---

As long as you have git and at least Python 3.6, then you can install
and use `tox`_.  After cloning the repository, you can run the repo
checks with the ``tox`` command.  It will build a virtual python
environment for each installed version of python with all the python
dependencies and run the specified commands, eg:

::

  $ git clone https://github.com/VCTLabs/cp210x-program
  $ cd cp210x-program/
  $ tox -e py

The above will run the default test commands using the (local) default
Python version.  To specify the Python version and host OS type, run
something like::

  $ tox -e py39-linux

To build and check the Python package, run::

  $ tox -e deploy,check

Full list of additional ``tox`` commands:

* ``tox -e deploy`` will build the python packages and run package checks
* ``tox -e check`` will install the wheel package from above and run the script
* ``tox -e lint`` will run ``pylint`` (somewhat less permissive than PEP8/flake8 checks)
* ``tox -e readhex`` will install the wheel package and try to read from a legacy device
* ``tox -e read`` will read the bulk USB descriptors from a device with SiLabs vendor ID
* ``tox -e badge`` will build the external cp2102N tool => ``/ext/badge/bin/``
* ``tox -e clean`` will clean the above ``bin`` directory

For the ``tox -e badge`` command, you may want to set the ``CC`` variable
either in your shell environment or on the command-line, eg::

  $ CC=gcc tox -e badge


Pre-commit
----------

This repo is now pre-commit_ enabled for python/rst source and file-type linting.
The checks run automatically on commit and will fail the commit (if not
clean) and perform simple file corrections.  If the mypy check fails
on commit, you must first fix any fatal errors for the commit to succeed.
That said, pre-commit does nothing if you don't install it first (both
the program itself and the hooks in your local repository copy).

You will need to install pre-commit before contributing any changes;
installing it using your system's package manager is recommended,
otherwise install with pip into your usual virtual environment using
something like::

  $ sudo emerge pre-commit  --or--
  $ pip install pre-commit

then install it into the repo you just cloned::

  $ git clone https://github.com/VCTLabs/cp210x-program
  $ cd cp210x-program/
  $ pre-commit install

It's usually a good idea to update the hooks to the latest version::

    $ pre-commit autoupdate

Most (but not all) of the pre-commit checks will make corrections for you,
however, some will only report errors, so these you will need to correct
manually.

Automatic-fix checks include ffffff, isort, autoflake, the json/yaml/xml format checks,
and the miscellaneous file fixers. If any of these fail, you can review the changes
with ``git diff`` and just add them to your commit and continue.

If any of the mypy or rst source checks fail, you will get a report,
and you must fix any errors before you can continue adding/committing.

To see a "replay" of any ``rst`` check errors, run::

  $ pre-commit run rst-backticks -a
  $ pre-commit run rst-directive-colons -a
  $ pre-commit run rst-inline-touching-normal -a

To run all ``pre-commit`` checks manually, try::

  $ pre-commit run -a

.. _tox: https://github.com/tox-dev/tox
.. _pre-commit: https://pre-commit.com/index.html


Device Info
===========

Updated vendor links and basic model info; see the individual product
descriptions and data sheets for details.

Model notes
-----------

Taken from the respective device Data Sheets:

* CP2101 - EEPROM (512 byte)  *may work*
* CP2102 - EEPROM (1024 byte)  *should work*
* CP2103 - EEPROM (1024 byte)  *should work*
* CP2104 - EPROM only (1024 byte, not re-programmable)
* CP2105 - EPROM only (296 byte, not re-programmable)
* CP2109 - EPROM only (1024 byte, not re-programmable)
* CP2102N - EEPROM (960 byte) **will not work** with legacy ``cp210x-program``

The following table from AN721 shows the default SiLabs USB device IDs; note
third-party manufacturers often do not reprogram with their own vendor/product
IDs.

.. figure:: doc/images/cp210x_default_ids.png
    :alt: CP120x device IDs
    :width: 90%
    :figwidth: 90%
    :align: left


Links
-----

* Original cp210x-program / CP210x Programmer project page by Petr Tesarik (a.k.a. tesarik)
  and Johannes Hölzl (a.k.a. johoelzl): https://sourceforge.net/projects/cp210x-program/

* CP2102N Product page and Data Sheet on Silicon Labs:

  + https://www.silabs.com/interface/usb-bridges/usbxpress/device.cp2102n-gqfn20
  + https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf

* AN978 CP210x USB-to-UART API Specification:

  + note this mainly documents HW/package and feature compatibility, and only discusses
    the (newer) CP2102N model as far as configuration byte layout
  + https://www.silabs.com/documents/public/application-notes/an978-cp210x-usb-to-uart-api-specification.pdf

* AN721 Device Customization Guide:

  + https://www.silabs.com/documents/public/application-notes/AN721.pdf
  + https://www.silabs.com/documents/public/example-code/AN721SW.zip

* AN197 CP210x Serial Communications Guide:

  + https://www.silabs.com/documents/public/application-notes/an197.pdf
  + https://www.silabs.com/documents/public/example-code/AN197SW.zip

* AN223 Port Configuration and GPIO for CP210x

  + https://www.silabs.com/documents/public/application-notes/an223.pdf
  + https://www.silabs.com/documents/public/example-code/AN223SW.zip

License
=======

The python package 'cp210x' and the python script 'cp210x-program' are provided
under the terms of the GNU LGPL. See LICENSE.  Otherwise, anything under the
``ext`` directory tree has its own license/copyrights.

Current external sources:

* cp2102 source and header files borrowed from:
  https://github.com/lowerrandom/DaBomb_dc27_badge/tree/master/software/tools/src
* requires GNU/Clang toolchain and libusb

.. |ci| image:: https://github.com/VCTLabs/cp210x-program/actions/workflows/ci.yml/badge.svg
    :target: https://github.com/VCTLabs/cp210x-program/actions/workflows/ci.yml
    :alt: CI Status

.. |wheels| image:: https://github.com/VCTLabs/cp210x-program/actions/workflows/wheels.yml/badge.svg
    :target: https://github.com/VCTLabs/cp210x-program/actions/workflows/wheels.yml
    :alt: Wheel Status

.. |badge| image:: https://github.com/VCTLabs/cp210x-program/actions/workflows/pylint.yml/badge.svg
    :target: https://github.com/VCTLabs/cp210x-program/actions/workflows/pylint.yml
    :alt: Pylint Status

.. |release| image:: https://github.com/VCTLabs/cp210x-program/actions/workflows/release.yml/badge.svg
    :target: https://github.com/VCTLabs/cp210x-program/actions/workflows/release.yml
    :alt: Release Status

.. |pylint| image:: https://raw.githubusercontent.com/VCTLabs/cp210x-program/badges/master/pylint-score.svg
    :target: https://github.com/VCTLabs/cp210x-program/actions/workflows/pylint.yml
    :alt: Pylint score

.. |license| image:: https://img.shields.io/github/license/VCTLabs/cp210x-program
    :target: https://github.com/VCTLabs/cp210x-program/blob/master/LICENSE
    :alt: License

.. |tag| image:: https://img.shields.io/github/v/tag/VCTLabs/cp210x-program?color=green&include_prereleases&label=latest%20release
    :target: https://github.com/VCTLabs/cp210x-program/releases
    :alt: GitHub tag

.. |python| image:: https://img.shields.io/badge/python-3.6+-blue.svg
    :target: https://www.python.org/downloads/
    :alt: Python

.. |pre| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit
