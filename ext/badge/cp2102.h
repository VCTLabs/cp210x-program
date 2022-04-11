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

#ifndef _CP2102H_
#define _CP2102H_

#define CP210X_OK		0
#define CP210X_ERROR		-1
#define CP210X_TIMEOUT_MS	500

#define CP210X_VENDOR_ID	0x10C4
#define CP210X_DEVICE_ID	0xEA60

/* CP210x configuration request transfer type */

#define CP210X_REQUEST_CFG		0xFF

/* CP2102 configuration request */

#define CP210X_CFG_READ_LATCH		0x00C2 /* Read GPIO latch */
#define CP210X_CFG_VENDOR_ID		0x3701
#define CP210X_CFG_PRODUCT_ID		0x3702
#define CP210X_CFG_PRODUCT_STRING	0x3703
#define CP210X_CFG_SERIALNUM		0x3704
#define CP210X_CFG_ATTRIBUTES		0x3705
#define CP210X_CFG_MAX_POWER		0x3706
#define CP210X_CFG_PROD_VERSION		0x3707
#define CP210X_CFG_UNKNOWN		0x3708
#define CP210X_CFG_EEPROM		0x3709	/* EEPROM contents */
#define CP210X_CFG_LOCK_VALUE		0x370A	/* Data is locked */
#define CP210X_CFG_MODEL		0x370B	/* Part number */
#define CP210X_CFG_FLUSH		0x370D	/* Flush buffers */
#define CP210X_CFG_MODE			0x3711	/* SCI/ECI mode */
#define CP210X_CFG_WRITE_LATCH		0x00C2  /* Write GPIO latch */

/* EEPROM layout */

#define CP210X_EE_SIZE			0x0400

#define CP210X_EE_BAUDRATE_TABLE	0x0000
#define CP210X_EE_MODEL			0x01FF
#define CP210X_EE_STRING_DESC_0		0x0200
#define CP210X_EE_PRODUCT_STRING	0x0208
#define CP210X_EE_SERIALNUM		0x0307
#define CP210X_EE_VENDOR_ID		0x0390
#define CP210X_EE_PRODUCT_ID		0x0392
#define CP210X_EE_PROD_VERSION		0x0394
#define CP210X_EE_ATTRIBUTES		0x03A1
#define CP210X_EE_MAX_POWER		0x03A2
#define CP210X_EE_VENDOR_STRING		0x03C3
#define CP210X_EE_LOCK_VALUE		0x03FF

/* Data lock value */

#define CP210X_LOCK_VALUE_LOCKED	0xF0
#define CP210X_LOCK_VALUE_UNLOCKED	0xFF

/* Attributes */

#define CP210X_ATTR_BUSPOWER_ON		0xC0
#define CP210X_ATTR_BUSPOWER_OFF	0x80

/* Model number */

#define CP210X_MODEL_CP2101		0x01
#define CP210X_MODEL_CP2102		0x02
#define CP210X_MODEL_CP2103		0x03
#define CP210X_MODEL_UNKNOWN		0x20

/* GPIO latches */

#define CP210X_GPIOLATCH_MASK		0x00FF
#define CP210X_GPIOLATCH_STATE		0xFF00

#define CP210X_GPIO_MASK(x)		((x) & 0xFF)
#define CP210X_GPIO_STATE(x)		(((x) << 8) & 0xFF)

#define CP210X_GPIO1			0x01
#define CP210X_GPIO2			0x02
#define CP210X_GPIO3			0x04
#define CP210X_GPIO4			0x08
#define CP210X_GPIO5			0x10
#define CP210X_GPIO6			0x20
#define CP210X_GPIO7			0x40
#define CP210X_GPIO8			0x80

#define CP210X_PRODSTRING_SIZE		255
#define CP210X_SERNUM_SIZE		128

/* Things specific to CP2102N */

#define CP210X_PROD_CP2102N		0x20

#define CP210X_CFG_2102N_READ_CONFIG	0x000E
#define CP210X_CFG_2102N_WRITE_CONFIG	0x370F

typedef struct cp2102n_udesc {
	uint8_t		cp2102n_len[2];
	uint8_t		cp2102n_type;
} CP2102N_UDESC;

typedef struct cp2102n_config {
	uint8_t		cp2102n_preamble[55];
	uint8_t		cp2102n_langdesc[4];
	CP2102N_UDESC	cp2102n_manstr_desc;
	uint8_t		cp2102n_manstr[128];	/* manufacturer string */
	CP2102N_UDESC	cp2102n_prodstr_desc;
	uint8_t		cp2102n_prodstr[256];	/* product string */
	CP2102N_UDESC	cp2102n_serstr_desc;
	uint8_t		cp2102n_serstr[128];	/* serial number string */
	uint8_t		cp2102n_postamble[96];
	uint8_t		cp2102n_csum[2];
} CP2102N_CONFIG;

#define CP2102N_USB_MAXPOWER	31

#define CP2102N_MODE_RESET_P0	580
#define CP2102N_MODE_RESET_P1	581
#define CP2102N_MODE_RESET_P2	582

#define CP2102N_MODE_GPIO0	0x08
#define CP2102N_MODE_GPIO1	0x10
#define CP2102N_MODE_GPIO2	0x20
#define CP2102N_MODE_GPIO3	0x40

#define CP2102N_LATCH_RESET_P0	586
#define CP2102N_LATCH_RESET_P1	587
#define CP2102N_LATCH_RESET_P2	588

#define CP2102N_LATCH_GPIO0	0x08
#define CP2102N_LATCH_GPIO1	0x10
#define CP2102N_LATCH_GPIO2	0x20
#define CP2102N_LATCH_GPIO3	0x40

#define CP2102N_PORTSET		600

#define CP2102N_PORTSET_TXLED	0x04
#define CP2102N_PORTSET_RXLED	0x08

#endif /* _CP2102H_ */
