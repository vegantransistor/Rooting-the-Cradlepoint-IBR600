# Rooting the Cradlepoint IBR600C

This is a description of the work I did with [stulle123](https://github.com/stulle123) Q4 2022 on the Cradlepoint IBR600C-150M-B-EU with FW Version 7.22.60.

## IBR600C Flashdump

It was a sunny day in September 2022 when someone put this device on my desk.

![crad](./pictures/crad.png)

The IBR600C is an LTE Modem & Router with Wifi, LAN and WAN Interfaces. It has an embedded webserver and cloud connectivity to the Cradlepoint Netcloud. 

I could not resist to open it and see if I could get some information about the boot process and eventually the firmware. The main processor is a Qualcomm IPQ4019 with SDRAM, NOR and NAND Flash. A UART interface is accessible:

***TODO:PIC with UART PINS***

At boot time, the UART interface only gives very limited information about the first bootloader, after that it becomes silent, so let's have a look inside the Flash memories. NOR and NAND Flash is a typical combination - bootloaders in NOR, OS and Application in NAND. Both flashes are connected via the same SPI bus to the processor. NAND Flashes are not easy to dump because of the bad blocks and error management. Here is a picture of the device opened with logic analyzer, serial interface and bus pirate connected:

![opened](./pictures/opened.png)

### NOR

The NOR Flash is easy to dump with a [Bus Pirate](http://dangerousprototypes.com/docs/Bus_Pirate) and [Flashrom](https://www.flashrom.org/Flashrom). The content is not encrypted and secure boot is not in place. 
Here are the steps to dump the NOR Flash:
1. Connect the Bus Pirate SPI interface to the NOR Flash located on the backside of the PCB:

***TODO:PIC of NOR with Pinout***

2. Put the main processor in `RESET` state. This is needed because we cannot have two SPI masters. 
3. Dump the flash with flashrom (change with your serial interface name):
```
flashrom -V -p buspirate_spi:dev=/dev/tty.usbserial-AG0JGQV3,serialspeed=230400 -n -r nor_dump.bin
```

The u-boot environmental variables are a good starting point: in our case, a `SILENT` variable is set to `YES`:
> silent=yes

We can change it to `no`.
**Caveat**: a CRC32 of the whole NOR Flash block (65536 bytes) protects the integrity of the u-boot bootenv. It is placed at the very beginning of the flash block. we need to recalculate the CRC32 on the flash block, CRC32 excluded (65536-4 bytes) and put it at the beginning of the block. The patched NOR Flash block containing the u-boot environmental variables is provided [here](./boot/nor_block_ubootenv_nosilent.bin).

Now reflash the NOR device:
```
flashrom -V -p buspirate_spi:dev=/dev/tty.usbserial-AG0JGQV3,serialspeed=230400 -n -w nor_dump_nosilent.bin
```
Boot the device, we now have a u-boot console (!):

```
U-Boot 2012.07 [Trail Mix GARNET v9.40,local] (Jan 04 2018 - 11:42:32)

smem ram ptable found: ver: 1 len: 3
RAM Configuration:
Bank #0: 80000000 256 MiB

DRAM:  256 MiB
NAND:  spi_nand: spi_nand_flash_probe SF NAND ID 0:ef:ab:21
SF: Detected W25M02GV with page size 2 KiB, total 256 MiB
SF: Detected W25Q64 with page size 4 KiB, total 8 MiB
ipq_spi: page_size: 0x100, sector_size: 0x1000, size: 0x800000
264 MiB
MMC:   


SW Version: v0.0.3
machid: 8010100
Net:   
configuring gpio 52 as func 2
configuring gpio 53 as func 2
configuring gpio 62 as func 0 (output) 0
MAC0 addr 00:30:44:53:9a:38
mdio init of IPQ MDIO0 in PSGMII mode
PHY ID1: 0x4d
PHY ID2: 0xd0b1
eth0
Ready.

Please choose the operation: 

   1: Load system code to SDRAM via TFTP. 
   2: Load system code then write to Flash via TFTP. 
   3: Boot system code via Flash (default).
   4: Enter boot command line interface.
   7: Validate Image 1 and Image 2. 
   8: Write SNV area information. 
   9: Load Boot Loader code then write to Flash via TFTP. 
 9 ... 0 
```

At this point, it will be possible to load some live image (SDRAM) in the device via TFTP.

### NAND 

NAND Flash dump is complicated to dump, I recorded the SPI interface during the boot phase with the [SALEAE](https://www.saleae.com/) logic analyzer. There are two big activity blocks corresponding to the Linux Kernel (first) and the Root Filesystem. Here is the rootfs:

![ROOTFS](./pictures/rootfs.png)

First the raw data are extracted with the Saleae SPI decoder feature and transformed in binary format with a [python script](./scripts/make_bin.py). However, the raw data still contain some handshake information, see the waveform:

![handshake](./pictures/handshake.png)

A [second script](./scripts/extract_nand.py) removes the handshake. Then remove all `0xFFFFFFFF` at the end of the file. We have now the root filesystem:

```
binwalk rootfs.cradl
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
0             0x0             Squashfs filesystem, little endian, version 4.0, compression:xz, size: 18464354 bytes, 2026 inodes, blocksize: 262144 bytes, created: 2022-06-02 18:01:34
```

With `unsquashfs` we can extract all the files.

With the same process we can extract the kernel image.

## Patch the Firmware to get a Root Shell
The device implements a shell accessible over SSH or internal webserver. However, this is not a linux shell, it has only limited application-related commands. We will now patch this shell to get a linux root shell. 

The device firmware is based on Linux and the application is almost completely written in Python.

### Patching the CPSHELL

In the `/service_manager/` directory we find a file called `cpshell.pyc`. This implements the reduced cradlepoint shell. If we `decompyle3` it we can find following interesting code:
```
            if self.superuser:
                self.cmds.update({'sh':(
                  self.sh, 'Internal Use Only'), 
                 'python':(
                  self.python, 'Internal Use Only')})
```
And:
```
        def sh(self):
            self.fork_exec(lambda: os.execl('/bin/sh', 'sh'))
```
The variable `superuser` is initilized to `false` :face_with_spiral_eyes: We just need to change the branch condition...

`decompyle3` is not able to decompile this file error-free, so that we can't just patch the `.py` file and recompile it. We have to patch the compiled python code `.pyc`.
First we can disassemble the file with `pydisasm` (https://github.com/rocky/python-xdis).
```
pydisasm --format xasm cpshell.pyc > cpshell.pyasm
```
Then we search for the variable `superuser` and branches associated to this variable. Here is the branch related to the code above:
```
237:
            LOAD_FAST            0 (self)
            LOAD_ATTR            13 (superuser)
            EXTENDED_ARG         1 (256)
            POP_JUMP_IF_FALSE    L500 (to 500)
```
We need to find the position of this `POP_JUMP_IF_FALSE` branch in the compiled python file and replce it with `POP_JUMP_IF_TRUE`. With following code we can print the opcodes related to the assembly code above:
```
import opcode
for op in ['LOAD_FAST', 'LOAD_ATTR', 'EXTENDED_ARG', 'POP_JUMP_IF_FALSE']:
print('%-16s%s' % (op, opcode.opmap[op].to_bytes(1,byteorder='little')))
```
A bytecode instruction is (mostly) composed of the 8 bit opcode (8 bit) and a 8 bit variable. In our case we can reconstruct following binary sequence:
```
0x7c 0x00 0x6a 0x0d 0x90 0x01 0x72
```
There is only one match in the `cpshell.pyc` file.

With `opcode` we can find that the opcode for `POP_JUMP_IF_FALSE` is `0x73`, so that we just need to change `0x7c 0x00 0x6a 0x0d 0x90 0x01 0x72` to `0x7c 0x00 0x6a 0x0d 0x90 0x01 0x73`. Our cpshell is now patched.

### Pachting the automatic silent mode reenabling function

The application includes a feature that (re-)enables silent boot every time the application starts. We also need to patch this feature. In `/service_manager/services` we find a file called `silentboot.pyc`. Let's decompile this file with `decompyle3`:

```
import services, cp
from services.utils.ubootenv import UbootEnv

class SilentBoot(services.Service):

    name = 'silentboot'
    __startup__ = 100
    __shutdown__ = 100

    def onStart(self):
        env = UbootEnv()
        if env.read('silent') != 'yes':
            env.write('silent', 'yes')
        if env.read('bootdelay') != '1':
            env.write('bootdelay', '1')

if cp.platform == 'router':
    services.register(SilentBoot)
```

We see that the u-boot `silent` variable is changed to `yes`. We can remove that:

```
import services, cp
from services.utils.ubootenv import UbootEnv

class SilentBoot(services.Service):
    name = 'silentboot'
    __startup__ = 100
    __shutdown__ = 100

    def onStart(self):
        env = UbootEnv()

if cp.platform == 'router':
    services.register(SilentBoot)
```

We have to recompile the python source file in a `pyc` file and replace the original one. 

### Recompile the squashfs rootfs image

After patching the application, we can re-build the squashfs image:

```
mksquashfs squashfs-root/ rootfsimage -b 262144 -comp xz -no-xattrs
```

In the next chapter we will see how to flash the squashfs image in NAND Flash.
 
## Flash the patched Firmware 

To test our patched firmware we now need to flash it back in the NAND Flash. These are the steps:
1. Boot the device with silent mode **disabled** (with buspirate and flashrom, don't forget the CRC)
2. Interrupt u-boot via serial interface and get a u-boot console
3. Use TFTP Boot to boot a live image containing kernel+rootfs from openWRT with prompt and root shell
4. Use the UBI commands to erase and flash the NAND Flash KERNEL and ROOTFS partitions

**Caveat**: even if only ROOTFS is changed, it is necessary to update the KERNEL too. 

### Preparation of KERNEL image

The raw kernel image dumped from flash contains:
* Linux Kernel in gzip format 
* ROOTFS parameters (crc and length) located at the end of the gzip kernel binary
* Device Tree

The image uses u-boot image format so we can use `mkimage` and `dumpimage`. 

First we can print some info:

```
mkimage -l kernelimage 
FIT description: CPRELEASE COCONUT IBR600C 7.22.60
Created:         Thu Nov 10 12:00:28 2022
 Image 0 (kernel@1)
  Description:  unavailable
  Created:      Thu Nov 10 12:00:28 2022
  Type:         Kernel Image
  Compression:  gzip compressed
  Data Size:    3153584 Bytes = 3079.67 KiB = 3.01 MiB
  Architecture: ARM
  OS:           Linux
  Load Address: 0x80208000
  Entry Point:  0x80208000
  Hash algo:    crc32
  Hash value:   fcca93bc
  Hash algo:    sha1
  Hash value:   5a4accc0eeeeafa42975e7d3943d784887f8ab78
 Image 1 (fdt@1)
  Description:  IBR600C device tree blob
  Created:      Thu Nov 10 12:00:28 2022
  Type:         Flat Device Tree
  Compression:  uncompressed
  Data Size:    20038 Bytes = 19.57 KiB = 0.02 MiB
  Architecture: ARM
  Hash algo:    crc32
  Hash value:   cb529e98
  Hash algo:    sha1
  Hash value:   3a2f1a92f537c1e614fde30c3bce9738cc76a225
 Default Configuration: 'config@5'
 Configuration 0 (config@5)
  Description:  Coconut
  Kernel:       kernel@1
  FDT:          fdt@1
```

Then extract device tree and kernel:

```
dumpimage -p 0 -o kernel.gz -T flat_dt kernelimage 
Extracted:
 Image 0 (kernel@1)
  Description:  unavailable
  Created:      Thu Nov 10 12:00:28 2022
  Type:         Kernel Image
  Compression:  gzip compressed
  Data Size:    3153584 Bytes = 3079.67 KiB = 3.01 MiB
  Architecture: ARM
  OS:           Linux
  Load Address: 0x80208000
  Entry Point:  0x80208000
  Hash algo:    crc32
  Hash value:   fcca93bc
  Hash algo:    sha1
  Hash value:   5a4accc0eeeeafa42975e7d3943d784887f8ab78


dumpimage -p 1 -o dt.dtb -T flat_dt kernelimage 
Extracted:
 Image 1 (fdt@1)
  Description:  IBR600C device tree blob
  Created:      Thu Nov 10 12:00:28 2022
  Type:         Flat Device Tree
  Compression:  uncompressed
  Data Size:    20038 Bytes = 19.57 KiB = 0.02 MiB
  Architecture: ARM
  Hash algo:    crc32
  Hash value:   cb529e98
  Hash algo:    sha1
  Hash value:   3a2f1a92f537c1e614fde30c3bce9738cc76a225
```

We can now modify the kernel.gz binary with the ROOTFS information. The three last words of the kernel.gz file contain CRC, Length and 0x00000000 in little endian format. Note that these three words are not part of the compressed image, they are just added at the end.

First calculate the CRC of the ROOTFS image:
```
crc32 rootfsimage
```
Note the length of the rootfs image in bytes, convert in hex:
> E.g. 19034112 bytes, or 0x01227000 bytes

Open kernel.gz in a hex editor, change the CRC and length. For example (last three bytes):
* Original (CRC - Length - 0x0):
> 0xB4D11088 0x00733302 0x00000000
* Changed :
> 0x67452301 0x00702201 0x00000000

Now we can re-build the KERNEL image:

```
mkimage -f image.its kernelimage
```
Note: `image.its` is provided [here](./boot/image.its)

### Flash the images

Connect your host pc to the Cradlepoint device with: 
1. a serial terminal 8n1,115200 
2. an ethernet cable connected to the LAN (***TODO:CHECK!!!***) port

Set up a TFTP server on the host computer with `IP = 192.168.0.200` and put the image `wnc-fit-uImage_v005.itb` (do not rename, provided [here](./boot/wnc-fit-uImage_v005.itb)) in the TFTP directory. This image contains the modified kernel and rootfs from openWRT. 

Boot the Cradlepoint with modified NOR FLash (silent mode disabled), so that Uboot messages are displayed. Then press 1 to load image via TFTP (9 seconds break). 
Note that the TFTP Server IP can be changed by modifying the u-boot variable `serverip` and using `saveenv`.
Cradlepoint will TFTP the file, unpack it and start the kernel. Now we have a root shell on the serial interface:
```
BusyBox v1.35.0 (2022-10-18 13:09:23 UTC) built-in shell (ash)
_______ ________ __
| |.-----.-----.-----.| | | |.----.| |_
| - || _ | -__| || | | || _|| _|
|_______|| __|_____|__|__||________||__| |____|
|__| W I R E L E S S F R E E D O M
-----------------------------------------------------
OpenWrt SNAPSHOT, r20976-7129d1e9c9
-----------------------------------------------------
=== WARNING! =====================================
There is no root password defined on this device!
Use the "passwd" command to set up a new password
in order to prevent unauthorized SSH logins.
--------------------------------------------------
root@OpenWrt:~#
```
Since we want to update the NAND Flash with big images, we will now switch so SSH. Change the IP Address of the host computer to 192.168.1.200 and SSH the Cradlepoint
with `ssh root@192.168.1.1`. 

How to flash the NAND Flash:

1. `scp` the new rootfsimage and kernelimage to the `/tmp/` directory of the Cradlepoint device (reminder: everything is in SDRAM with the openWRT image).
2. Attach the NAND Flash partition containing KERNEL and ROOTFS called `/dev/mtd1`:
```
ubiattach -b 1 -m 1
```
Now you shall see the three ubi volumes `/dev/ubi0_0` (kernel), `/dev/ubi0_1` (rootfs) and `/dev/ubi0_2` (empty, used as buffer).

3. Wipe out the first partition (partition 0), which contains the kernel image.
```
ubiupdatevol /dev/ubi0_0 -t
```
4. Flash the kernel image
```
ubiupdatevol /dev/ubi0_0 /tmp/kernelimage
```
5. Wipe out the second partition (partition 1), which contains the rootfs.
```
ubiupdatevol /dev/ubi0_1 -t
```
6. *Optional*: Resize the rootfs partition if the new rootfs is bigger than the partition size (i.e. the original one):
```
ubirsvol /dev/ubi0 -n 1 -s [nb of bytes of the new rootfs image]
```
7. *Optional*: Resize the third partition if the step before failed with following  error:
```
ubi_resize_volume: not enough PEBs: requested 4, available 0
```
Use ubinfo to display the size of the image and partitions. Note that the third partition does not contain any data so it can be resized.
```
ubirsvol /dev/ubi0 -n 2 -s [nb of bytes calculated to have enough place for ubi0_1]
```
8. Re-do step 7. if needed.
9. Flash the rootfs image
```
ubiupdatevol /dev/ubi0_1 /tmp/rootfsimage
```
10. Dettach the ubi partition
```
ubidettach ubi -m 1
```
11. Reboot. The device shall boot with the new rootfs without CRC error.
 
**Note about UBI**: Between the bare NAND FLash and the squashfs filesystem there is a layer in-between called [UBI](http://www.linux-mtd.infradead.org/doc/ubi.html), which takes care among other things of the Flash block management. 

If we `ssh` the device and type `sh` we get a root shell:

***TODO: ADD ROOTSHELL***

## Disclosure

We disclosed our findings to Cradlepoint on 2023-01-05.
