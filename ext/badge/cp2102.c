/*-
 *  SPDX-License-Identifier: Apache-2.0
 *
 * Copyright (c) 2019
 *      Bill Paul <wpaul@windriver.com>.  All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 3. All advertising materials mentioning features or use of this software
 *    must display the following acknowledgement:
 *      This product includes software developed by Bill Paul.
 * 4. Neither the name of the author nor the names of any co-contributors
 *    may be used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY Bill Paul AND CONTRIBUTORS ``AS IS'' AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED.  IN NO EVENT SHALL Bill Paul OR THE VOICES IN HIS HEAD
 * BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
 * THE POSSIBILITY OF SUCH DAMAGE.
 */

/*
 * This program is used to customize the configuration data of the Silicon
 * Image Labs CP2102N USB to RS232 chip on the Ides of DEF CON 27 badge.
 * It works by issuing vendor-specific control commands to the device over
 * USB. Note that this works with the CP2102N _ONLY_. It does not work
 * with the CP2102 or other chips in the CP210x family. Sadly, programming
 * interface varies wildly across the different parts.
 *
 * For the CP2102N, there are two main commands: read configuration block
 * (0x000E) and write configuration block (0x370F). These can be used to
 * obtain and manipulate a block of 678 bytes, which contains the vendor
 * string, product string, serial number string, USB vendor/device ID,
 * GPIO configuration, power configuration, and various other settings.
 * Some of these (like the USB vendor and device ID) should _never_ be
 * changed, as doing so might adversely affect the operation of the chip,
 * and restoring them might be tricky.
 *
 * The CP2102N configuration block is documented in the following
 * application note:
 *
 * https://www.silabs.com/documents/public/application-notes/AN978-cp210x-usb-to-uart-api-specification.pdf
 *
 * The programming interface can be gleaned by examining the source code
 * in the USBXpressHostSDK for Linux, which can be found here:
 *
 * https://www.silabs.com/documents/public/software/USBXpressHostSDK-Linux.tar
 *
 * A set of default configuration files for all CP210x devices can be
 * found here:
 *
 * https://www.silabs.com/content/usergenerated/asi/cloud/attachments/siliconlabs/en/community/groups/interface/forum/_jcr_content/content/primary/qna/cp2102n_command_line-s0yh/i_ve_attached_a_zip-Rn9F/cp21xxsmt_default_configurations.zip
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>

#include <libusb.h>

#include "cp2102.h"

CP2102N_CONFIG config;

static int cp210x_open (uint16_t, uint16_t, libusb_device_handle **);
static void cp210x_close (libusb_device_handle *);
static int cp210x_read (libusb_device_handle *,
    uint16_t, uint8_t *, uint16_t *);
static int cp210x_write (libusb_device_handle *,
    uint16_t, uint8_t *, uint16_t);

static void
cp210x_ascii_to_ucode (char * in, uint16_t * out)
{
	int i;

	for (i = 0; i < strlen(in); i++)
		out[i] = in[i];

	return;
}

static void
cp210x_ucode_to_ascii (uint16_t * in, char * out)
{
	int i = 0;

	while (in[i] != 0x0) {
		out[i] = in[i];
		i++;
	}

	return;
}

/*
 * The CP2102N configuration block must be checksummed. This function
 * generates a fletcher16 checksum for a given data block.
 */

static uint16_t
cp210x_csum (uint8_t * data, uint16_t len)
{
	uint16_t sum1 = 0xff, sum2 = 0xff;
	uint16_t tlen;

	while (len) {
		tlen = len >= 20 ? 20 : len;
		len -= tlen;
		do {
			sum2 += sum1 += *data++;
		} while (--tlen);
		sum1 = (sum1 & 0xff) + (sum1 >> 8);
		sum2 = (sum2 & 0xff) + (sum2 >> 8);
	}

	/* Second reduction step to reduce sums to 8 bits */

	sum1 = (sum1 & 0xff) + (sum1 >> 8);
	sum2 = (sum2 & 0xff) + (sum2 >> 8);

	return (sum2 << 8 | sum1);
}

/*
 * Scan for a CP2102 device.
 */

static int
cp210x_open (uint16_t vid, uint16_t did, libusb_device_handle ** d)
{
	struct libusb_device_descriptor desc;
	libusb_context * usbctx = NULL;
	libusb_device_handle * dev = NULL;
	libusb_device ** devlist;
	ssize_t devcnt, i;
	uint8_t strbuf[256];
	int sts = CP210X_ERROR;

	if (libusb_init (&usbctx) != LIBUSB_SUCCESS) {
		fprintf (stderr, "initializing libusb failed\n");
		return (sts);
	}

	/* Get device list */

	devcnt = libusb_get_device_list (usbctx, &devlist);

	if (devcnt < 0) {
		fprintf (stderr, "Getting USB device list failed\n");
		return (sts);
	}

	/* Walk the device in search of a CP210x */

	for (i = 0; i < devcnt; i++) {
		memset (&desc, 0, sizeof (desc));
		libusb_get_device_descriptor (devlist[i], &desc);
		if (desc.idVendor == vid && desc.idProduct == did)
			break;
	}

	if (i == devcnt) {
		fprintf (stderr, "No matching device found for 0x%x/0x%x\n",
		    vid, did);
		*d = NULL;
	} else {
		printf ("Found match for 0x%x/0x%x at bus %d device %d\n",
		    vid, did,  libusb_get_bus_number (devlist[i]),
		    libusb_get_device_address (devlist[i]));
		if (libusb_open (devlist[i], &dev) != LIBUSB_SUCCESS) {
			perror ("Opening device failed");
			*d = NULL;
		} else {
			libusb_get_string_descriptor_ascii (dev,
			    desc.iProduct, strbuf, sizeof (strbuf));
			printf ("Device ID string: [%s]\n", strbuf);
			*d = dev;
			sts = CP210X_OK;
		}
	}

	libusb_free_device_list (devlist, 1);

	return (sts);
}

/*
 * Close an open device handle.
 */

static void
cp210x_close (libusb_device_handle * d)
{
	libusb_close (d);
	return;
}

/*
 * Perform a vendor-specific read request on the control endpoint.
 */

static int
cp210x_read (libusb_device_handle * d, uint16_t req,
    uint8_t * buf, uint16_t * len)
{
	int r;
	uint16_t l;

	if (d == NULL || buf == NULL)
		return (CP210X_ERROR);

	l = *len;

	r = libusb_control_transfer (d, LIBUSB_ENDPOINT_IN |
	    LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_RECIPIENT_DEVICE,
	    CP210X_REQUEST_CFG, req, 0, buf, l, CP210X_TIMEOUT_MS);

	if (r < 0) {
		fprintf (stderr, "Reading 0%x failed: %d\n", req, r);
		return (CP210X_ERROR);
	}

	*len = r;

	return (CP210X_OK);
}

/*
 * Perform a vendor-specific write request on the control endpoint.
 */

static int
cp210x_write (libusb_device_handle * d, uint16_t req,
    uint8_t * buf, uint16_t len)
{
	int r;

	if (d == NULL || buf == NULL)
		return (CP210X_ERROR);

	r = libusb_control_transfer (d, LIBUSB_ENDPOINT_OUT |
	    LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_RECIPIENT_DEVICE,
	    CP210X_REQUEST_CFG, req, 0, buf, len, CP210X_TIMEOUT_MS);

	if (r < 0) {
		fprintf (stderr, "Reading writing: %d\n", r);
		return (CP210X_ERROR);
	}

	return (CP210X_OK);
}

static void
cp210x_usage (char * progname)
{
	fprintf (stderr, "%s: [-d file] [-l file] [-m mfgr string]\n"
	    "\t[-p product string] [-s serial # string]\n"
	    "\t[-g on|off] [-x usb power]\n",
	    progname);

	return;
}

int
main (int argc, char * argv[])
{
	int i;
	uint16_t csum;
	uint16_t len;
	uint16_t total;
	unsigned long scan;
	char buf[256];
	uint8_t part;
	uint8_t * p;
	libusb_device_handle * dev = NULL;
	int c;
	char * dfile = NULL;
	char * lfile = NULL;
	char * mstr = NULL;
	char * pstr = NULL;
	char * sstr = NULL;
	char * gpio = NULL;
	char * pwr = NULL;

	FILE * fp;

	if (argc < 2) {
		cp210x_usage (argv[0]);
		exit (0);
	}

	while ((c = getopt (argc, argv, "d:l:m:p:s:x:g:")) != -1) {
		switch (c) {
			case 'd':
				dfile = optarg;
				break;
			case 'l':
				lfile = optarg;
				break;
			case 'm':
				mstr = optarg;
				break;
			case 'p':
				pstr = optarg;
				break;
			case 's':
				sstr = optarg;
				break;
			case 'g':
				gpio = optarg;
				break;
			case 'x':
				pwr = optarg;
				break;
			default:
				cp210x_usage (argv[0]);
				exit (0);
				break;
		}
	}

	if (cp210x_open (CP210X_VENDOR_ID,
	    CP210X_DEVICE_ID, &dev) == CP210X_ERROR) {
		fprintf (stderr, "CP210x not found\n");
		exit (-1);
	}

	/* Check that the device is actually a CP2102N */

	part = 0;
	len = 1;
	cp210x_read (dev, CP210X_CFG_MODEL, &part, &len);
	if (part != CP210X_PROD_CP2102N_QFN28 && part != CP210X_PROD_CP2102N_QFN24 && part != CP210X_PROD_CP2102N_QFN20) {
		cp210x_close (dev);
		fprintf (stderr, "device is not a CP2102N (0x%02X)\n", part);
		exit (-1);
	}


	/* Read the entire configuration block */

	len = sizeof(config);
	if (cp210x_read (dev, CP210X_CFG_2102N_READ_CONFIG,
	    (uint8_t *)&config, &len) != CP210X_OK) {
		fprintf (stderr, "reading config block failed\n");
		cp210x_close (dev);
		exit (-1);
	}

	memset (buf, 0, sizeof(buf));
	cp210x_ucode_to_ascii ((uint16_t *)config.cp2102n_manstr, buf);
	printf ("Vendor: %s\n", buf);

	memset (buf, 0, sizeof(buf));
	cp210x_ucode_to_ascii ((uint16_t *)config.cp2102n_prodstr, buf);
	printf ("Product: %s\n", buf);

	memset (buf, 0, sizeof(buf));
	cp210x_ucode_to_ascii ((uint16_t *)config.cp2102n_serstr, buf);
	printf ("Serial: %s\n", buf);

	if (dfile != NULL) {
		fp = fopen (dfile, "wb+");
		if (fp == NULL) {
			perror ("Opening dump file failed");
			exit (-1);
		}
		p = (uint8_t *)&config;
		for (i = 0; i < len; i++)
			fprintf (fp, "0x%02X ", p[i]);
		fprintf (fp, "\n");
		fclose (fp);
		goto out;
	}

	if (lfile != NULL) {
		fp = fopen (lfile, "r");
		if (fp == NULL) {
			perror ("Opening load file failed");
			exit (-1);
		}

		p = (uint8_t *)&config;
		total = 0;
		for (i = 0; i < len; i++) {
			memset (buf, 0, sizeof(buf));
			csum = fread (buf, 1, 5, fp);
			total++;
			if (csum < 4)
				break;
			scan = strtoul (buf, NULL, 16);
			p[i] = scan & 0xFF;
		}

		if (total != len) {
			fprintf (stderr,
			    "wrong number of config bytes (%d != %d)\n",
			    total, len);
			fclose (fp);
			cp210x_close (dev);
			exit (-1);
		}

		fclose (fp);

		/* Validate checksum */

		csum = cp210x_csum ((uint8_t *)&config,
		    sizeof(config) - 2);
		if (csum != (config.cp2102n_csum[0] << 8 |
		    config.cp2102n_csum[1])) {
			fprintf (stderr, "bad checksum (0x%x != 0x%x)\n",
			    csum, config.cp2102n_csum[0] << 8 |
			    config.cp2102n_csum[1]);
			cp210x_close (dev);
			exit (-1);
		}

		/* Looks ok, write the new data */

		goto save;
	}

	/* Reset GPIO pin behavior */

	if (gpio != NULL) {
		p = (uint8_t *)&config;
		if (strcmp (gpio, "on") == 0) {
			p[CP2102N_MODE_RESET_P1] |= CP2102N_MODE_GPIO0 |
			    CP2102N_MODE_GPIO1;
			p[CP2102N_PORTSET] |= CP2102N_PORTSET_TXLED |
			    CP2102N_PORTSET_RXLED;
		} else if (strcmp (gpio, "off") == 0) {
			p[CP2102N_MODE_RESET_P1] &= ~(CP2102N_MODE_GPIO0 |
			    CP2102N_MODE_GPIO1);
			p[CP2102N_PORTSET] &= ~(CP2102N_PORTSET_TXLED |
			    CP2102N_PORTSET_RXLED);
		} else {
			fprintf (stderr, "unexpected gpio command (%s)\n",
			    gpio);
			cp210x_close (dev);
			exit (-1);
		}
	}

	/* Reset USB max power value */

	if (pwr != NULL) {
		csum = strtol (pwr, NULL, 10);
		if (csum > 500) {
			fprintf (stderr, "power value must be 500mA or less\n");
			cp210x_close (dev);
			exit (-1);
		}
		p = (uint8_t *)&config;
		/* power is expressed as mA divided by 2 */
		p[CP2102N_USB_MAXPOWER] = csum >> 1;
	}

	/* Reset vendor */

	if (mstr != NULL) {
		memset (config.cp2102n_manstr, 0,
		    sizeof(config.cp2102n_manstr));
		memset (buf, 0, sizeof(buf));
		cp210x_ascii_to_ucode (mstr,
		    (uint16_t *)config.cp2102n_manstr);
		cp210x_ucode_to_ascii ((uint16_t *)config.cp2102n_manstr, buf);
		csum = (strlen (mstr) + 1) * 2;
		config.cp2102n_manstr_desc.cp2102n_len[0] = csum >> 8;
		config.cp2102n_manstr_desc.cp2102n_len[1] = csum & 0xFF;
		printf ("New vendor: %s\n", buf);
	}

	/* Reset product */

	if (pstr != NULL) {
		memset (config.cp2102n_prodstr, 0,
		    sizeof(config.cp2102n_prodstr));
		memset (buf, 0, sizeof(buf));
		cp210x_ascii_to_ucode (pstr,
		    (uint16_t *)config.cp2102n_prodstr);
		cp210x_ucode_to_ascii ((uint16_t *)config.cp2102n_prodstr, buf);
		csum = (strlen (pstr) + 1) * 2;
		config.cp2102n_prodstr_desc.cp2102n_len[0] = csum >> 8;
		config.cp2102n_prodstr_desc.cp2102n_len[1] = csum & 0xFF;
		printf ("New product: %s\n", buf);
	}

	/* Reset serial number */

	if (sstr != NULL) {
		memset (config.cp2102n_serstr, 0,
		    sizeof(config.cp2102n_serstr));
		memset (buf, 0, sizeof(buf));
		cp210x_ascii_to_ucode (sstr,
		    (uint16_t *)config.cp2102n_serstr);
		cp210x_ucode_to_ascii ((uint16_t *)config.cp2102n_serstr, buf);
		csum = (strlen (sstr) + 1) * 2;
		config.cp2102n_serstr_desc.cp2102n_len[0] = csum >> 8;
		config.cp2102n_serstr_desc.cp2102n_len[1] = csum & 0xFF;
		printf ("New serial: %s\n", buf);
	}

save:

	/* Update checksum */

	csum = cp210x_csum ((uint8_t *)&config, sizeof(config) - 2);
	config.cp2102n_csum[0] = csum >> 8;
	config.cp2102n_csum[1] = csum & 0xFF;

	len = sizeof(config);
	cp210x_write (dev, CP210X_CFG_2102N_WRITE_CONFIG,
	    (uint8_t *)&config, len);

out:

	cp210x_close (dev);

	exit (0);
}
