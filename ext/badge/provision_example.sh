#!/usr/bin/env bash

# set custom product/vendor strings
PRODUCT_STR="VCT Labs CP2102N UART Bridge"
VENDOR_STR="VCT Labs"

echo
echo "cp2102N provision ready."

while [ /bin/true ];
do

    /bin/echo "Connect cable and hit ENTER or Q to quit."
    /bin/echo -n "==> "

    read X

    if [ "$X" == "q" -o "$X" == "Q" ]; then
        echo "[*] Bye!"
        exit
    fi

    echo "[*] Attempting serial provision for 2102N ..."

    NEWSERIAL=$(uuidgen | sed 's/-//g' | cut -c1-16)
    DATE=$(date)
    ./bin/cp2102 -p "${PRODUCT_STR}" -m "${VENDOR_STR}" -s ${NEWSERIAL}


    echo "[*] Provisioned serial ${NEWSERIAL}..."
    echo "[*] Serial number will not be returned by chip until full power cycle."
    echo
    echo $DATE $NEWSERIAL >> serials.txt
    echo
done
