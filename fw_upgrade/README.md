# Firmware Upgrade

Upgrading the router's firmware usually works via NetCloud, for newer firmware releases (`> 2018`) this is the only way. For older releases upgrading via `scp` or the web interface still works.

Older firmware images are still available on https://cradlepoint.com. They are signed with a RSA private key and encrypted with AES256-CBC. However, the signature verification can be easily bypassed and the AES key is hard-coded in the router's Python middleware.

## Implementation

The firmware upgrade is mainly implemented in the `/service_manager/services/utils/upgrade_write.pyc` file. This is what's going on:

1. `upgrade_write()` --> decrypts the upgrade file, writes a block, gets the `uimage` and `uboot` signatures from the firmware file *or* calls `upgrade_write_init()`
2. `upgrade_write_init()` --> header and CRC checks, writes a new SHA512 hash to flash memory
3. `_write()` --> writes data to memory flash
4. `upgrade_validate()` --> validates the file and checks the signature by calling `upgrade_validate_signature()`

The firmware update blob contains a header with the firmware version. This header is **not signed** and therefore can be manipulated. If the version string in the firmware header matches a certain value, the signature verification check is ignored:

```python
if upgrade_int >= 458752:
    self.force_signature_validation = True
```

## Get the AES Decryption Key

Firmware update files which are available on the Cradlepoint website are encrypted with AES. However, at least for the `IBR600` a global hard-coded AES key is used.

In a nutshell, the key is generated with OpenSSL (in `/usr/lib/python3.8/cp/_aes.cpython-38m.so`) from a hard-coded passphrase (in `/service_managesr/service/utils/upgrade_write.pyc`). We'll leave it up to the reader to get the passphrase ;-)

The key is generated in the following way:

1. The shared lib `_aes.cpython-38m.so` uses [EVP_BytesToKey](https://www.openssl.org/docs/manmaster/man3/EVP_BytesToKey.html) to generate the AES key and IV from a passphrase.
2. The passphrase can be found in ther file `upgrade_write.pyc`.
3. Next, the passphrase is used to generate a "pre-key". This can be done with the openssl tool:
```bash
$ openssl enc -nosalt -p -in foo -out bar -e -aes256 -k "first-secret-passphrase" -md sha1
```
4. Next, that "pre-key" is used to decrypt a base64 string. The resulting "plaintext" makes a new passphrase: `new-secret-passphrase`.
5. Finally, the new passphrase is used to compute the AES key and IV:
```bash
$ openssl enc -nosalt -p -in test.txt -out test_encrypted -e -aes256 -k "new-secret-passphrase" -md sha1
```

The passphrase from step 4) above is very easy to obtain if you use Qemu to [emulate](../router_emulation/README.md) the router's rootfs:

1. Fire up an emulated Cradlepoint router as described [here](../router_emulation/README.md)
2. Next, just run the following script with the `cppython` interpreter (you'll find the *real* hard-coded values in `upgrade_write.pyc`):
```python
from _aes import decryptobj, decrypt
from math import atan
import base64

_KEY = "first-secret-passphrase"
pre_passphrase = decryptobj(_KEY)
new_passphrase = pre_passphrase.decrypt(base64.b64decode(b'c29tZS1iYXNlNjQtc3RyaW5nCg=='))
aes = decryptobj(new_passphrase)
print(new_passphrase)
```

## Firmware Update File Analysis

1. Install the tools:
```bash
$ sudo apt-get install binwalk liblzo2-dev python-lzo
$ pip install python-lzo ubi_reader pycryptodomex
```
Alternatively, install `ubi_reader` from Github:
```bash
$ git clone https://github.com/jrspruitt/ubi_reader
$ cd ubi_reader && python setup.py install
```
2. Download any firmware update file for the `IBR600` from https://cradlepoint.com
3. Decrypt it with the following script (adjust `key`, `iv` and `in_file` variables)
```python
from Cryptodome.Cipher import AES
from math import atan
import base64


def decrypt(in_file, out_file):
    bs = AES.block_size
    key = b"\xDE\xAD"
    iv = b"\xBE\xEF"
    cipher = AES.new(key, AES.MODE_CBC, iv)
    next_chunk = ""
    finished = False

    while not finished:
        chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
        if len(next_chunk) == 0:
            padding_length = chunk[-1]
            chunk = chunk[:-padding_length]
            finished = True
        out_file.write(bytes(x for x in chunk))


with open("fw_encrypted.bin", "rb") as in_file, open(
    "fw_decrypted.bin", "wb"
) as out_file:
    decrypt(in_file, out_file)
```
4. Extract the firmware contents with `binwalk` and `ubi_reader`:
```bash
$ binwalk --extract decrypted-cp-fw.bin
$ cd ./_decrypted-cp-fw.bin.extracted
# Get the UBI images
$ ubireader_extract_images 48
# Extract the rootfs
$ unsquashfs -f -d <destination-folder> img-248169632_vol-ubi_rootfs.ubifs
```

General firmware info:
```bash
$ binwalk -B --term IBR6x0C_7.0.70_decrypted.bin

DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
0             0x0             uImage header, header size: 64 bytes, header CRC: 0xAB3EBAD8, created: 2019-05-30 22:06:11, image size: 17261896 bytes, Data Address: 0x80208000, Entry Point: 0x80208000, data CRC: 0x9B3DA5A2, OS: Linux, CPU: ARM, image
                              type: Multi-File Image, compression type: lzma, image name: "IBR600C 7.0.70"
72            0x48            LZMA compressed data, properties: 0x5D, dictionary size: 8388608 bytes, uncompressed size: 17958200 bytes
17256960      0x1075200       PEM certificate
17258298      0x107573A       PEM certificate
17260079      0x1075E2F       PEM certificate
```

## Build an update blob

To build an update blob, `rootfsimage` (see [here](https://github.com/vegantransistor/Rooting-the-Cradlepoint-IBR600/blob/main/README.md#building-the-squashfs-rootfs-image)) and `kernelimage` (see [here](https://github.com/vegantransistor/Rooting-the-Cradlepoint-IBR600/blob/main/README.md#preparing-the-kernel-image)) images are needed. This update blob can be downloaded via the web server or `scp` to update the device permanently.
 
1. First build the ubi image. Put the kernel binary `kernelimage` and the squashfs root filesystem `rootfsimage` in a directory and use `ubinize` with following `ubiini` file:

```
[kernel]
mode=ubi
image=kernelimage
vol_id=0
vol_type=dynamic
vol_name=kernel
vol_alignment=1
vol_size=3301376

[ubi_rootfs]
mode=ubi
image=rootfsimage
vol_id=1
vol_type=dynamic
vol_name=ubi_rootfs
vol_alignment=1
vol_size=19046400

[rootfs_data]
mode=ubi
vol_id=2
vol_type=dynamic
vol_name=rootfs_data
vol_flags=autoresize
vol_alignment=1
vol_size=1
```

Make the image:

```
ubinize -p 128KiB -m 2048 -o ubiimage ubiini
```

2. Package the ubi image:

```
mkimage -f fw.its ubiimage_packaged
```

Here is `fw.its`:

```
/dts-v1/;

/ {
        timestamp = <0x5bad4c90>;
        description = "Coconut";

        images {

                ubi-201725729ebf13a0afae256e25235343ee03bdef {
                        description = "Coconut";
                        data = /incbin/("ubiimage");
                        type = "firmware";
                        arch = "arm";
                        compression = "none";

                        hash@1 {
                                algo = "crc32";
                        };
                };
        };
};
```

3. Compress the packaged ubi image:

```
lzma -z -k ubiimage_packaged
```

4. Use following script to build the blob:
```python
from pathlib import Path
import zlib

ubi_file = Path("ubiimage_packaged.lzma")
blob_file = Path("fw_plain.bin")
headerimage = bytearray(b"\'\x05\x19V\x00\x00\x00\x00\\\xf0S\xd3\x01\x07eH\x80 \x80\x00\x80 \x80\x00\x00\x00\x00\x00\x05\x02\x04\x03IBR600C 6.0.00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")

try:
    with ubi_file.open(mode="rb") as ubi:
        ubiimage = ubi.read()
except OSError as error:
    print(f"Could not read imput files: {error}")

blobtmp1len = len(ubiimage)+8
blobtmp1 = bytearray(blobtmp1len)
blobtmp1[0:4] = blobtmp1len.to_bytes(4,'big')
blobtmp1[8:] = ubiimage

headerimage[12:16] = blobtmp1len.to_bytes(4,'big')
crc1 = zlib.crc32(blobtmp1)
headerimage[24:28] = crc1.to_bytes(4,'big')
crc2 = zlib.crc32(headerimage)
headerimage[4:8] = crc2.to_bytes(4,'big')

blobtmp2len = len(headerimage)+len(blobtmp1)
blobtmp2 = bytearray(blobtmp2len)
blobtmp2[0:len(headerimage)] = headerimage
blobtmp2[len(headerimage):] = blobtmp1

try:
    with blob_file.open(mode="wb") as blob:
        blob.write(blobtmp2)
        #blob.write(headerimageb)
except OSError as error:
    print(f"Could not write to rootfs: {error}")
```

5. Encrypt the blob with following script (replace IV and KEY with the correct ones):

```python
from Crypto.Cipher import AES
from math import atan
import base64
from Crypto.Util.Padding import pad, unpad

def encrypt(in_file, out_file):
   bs = AES.block_size
   key = b""
   iv = b""
   cipher = AES.new(key, AES.MODE_CBC, iv)
   finished = False

   while not finished:
       chunk = in_file.read(bs)
       if len(chunk) < (bs):
           chunk = cipher.encrypt(pad(chunk,bs));
           finished = True
       else:
           chunk = cipher.encrypt(chunk);
       out_file.write(bytes(x for x in chunk))

with open('fw_plain.bin', 'rb') as in_file, open('fw_encrypted.bin', 'wb') as out_file:
   encrypt(in_file, out_file)
```

6. Upgrade the router via the webserver or using `scp` (put the correct router IP address):

```bash
scp fw_encrypted.bin admin@10.10.15.15:/fw_upgrade
```




