#!/bin/sh -e
./cp210x-program -p -F testdata/cp2102-orig.hex > test.out
diff -us testdata/cp2102-orig.ini test.out
./cp210x-program -p -F testdata/cp2102-orig.hex -i test.out
diff -us testdata/cp2102-orig.ini test.out
./cp210x-program -pc -F testdata/cp2102-orig.hex -f test.out
diff -us testdata/cp2102-orig.hex test.out
./cp210x-program -pc \
  --set-product-string='Orange Pi Zero LTS 512' --set-serial-number='02c00142499c98f8' \
  --set-vendor-string='Xunlong' --set-bus-powered=yes \
  -F testdata/cp2102-orig.hex -i test.out.2 > test.out
diff -us testdata/cp2102-opi.ini test.out.2
diff -us testdata/cp2102-opi.hex test.out

rm -vf test.out.2 test.out
