# Firmware Upgrade

Upgrading the router's firmware usually works via NetCloud, for newer firmware releases (`> 2018`) this is the only way. For older releases upgrading via `scp` or the web interface still works.

Older firmware images are still available on https://cradlepoint.com. They are signed with a RSA private key and encrypted with AES256-CBC. However, the signature verification can be easily bypassed and the AES key is hard-coded in the router's Python middleware.

## Implementation

The firmware upgrade is mainly implemented in the `/service_manager/services/utils/upgrade_write.pyc` file. This is what's going on:

1. `upgrade_write()` --> decrypts the upgrade file, writes a block, gets the `uimage` and `uboot` signatures from the firmware file *or* calls `upgrade_write_init()`
2. `upgrade_write_init()` --> header and CRC checks, writes a new SHA512 hash to flash memory
3. `_write()` --> writes data to memory flash
4. `upgrade_validate()` --> validates the file and checks the signature by calling `upgrade_validate_signature()`

If the version string in the firmware header matches a certain value, the signature verification check is ignored:

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
