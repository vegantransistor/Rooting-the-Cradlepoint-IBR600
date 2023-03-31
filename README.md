# Rooting the Cradlepoint IBR600C and other stories

This is a description of the work I did with [stulle123](https://github.com/stulle123) Q4 2022 on the Cradlepoint IBR600C-150M-B-EU with FW Version 7.22.60.

## IBR600C Flashdump

It was a sunny day in September 2022 when someone put this device on my desk.

![crad](./pictures/crad.png)

The IBR600C is an LTE Modem & Router with Wifi, LAN and WAN Interfaces. It has an embedded webserver and cloud connectivity to the Cradlepoint Netcloud. 

I could not resist to open it and see if I could get some information about the boot process and eventually the firmware. The main processor is a Qualcomm IPQ4019 with SDRAM, NOR and NAND Flash. A UART interface is accessible:

**PIC: UART PINS**

At boot time, the UART interface only gives very limited information about the first bootloader, after that it becomes silent, so let's have a look inside the Flash memories. NOR and NAND Flash is a typical combination - bootloaders in NOR, OS and Application in NAND. Both flashes are connected via the same SPI bus to the processor. NAND Flashes are not easy to dump because of the bad blocks and error management. Here is a picture of the device opened with logic analyser, serial interface and bus pirate connected:

![opened](./pictures/opened.png)

### NOR

The NOR Flash is easy to dummp with a [Bus Pirate](http://dangerousprototypes.com/docs/Bus_Pirate) and [Flashrom](https://www.flashrom.org/Flashrom). The content is not encrypted and secure boot is not in place. 

The u-boot environmental variables are a good starting point: in our case, a `SILENT` variable is set to `YES`. By changing it to `NO`, we get a u-boot console:

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
**Caveat**: a CRC32 of the whole NOR Flash block (65536 bytes) protects the integrity of the u-boot bootenv. It is placed at the very beginning of the flash block. If you want to change some variables, don't forget to recalculate the CRC32 on the flash block, CRC32 excluded (65536-4 bytes).

At this point, it may be possible to load some [openWRT](https://openwrt.org/) firmware. TFTP loader is implemented in u-boot.

### NAND 

NAND Flash dump is complicated to dump, I recorded the SPI interface during the boot phase with the [SALEAE](https://www.saleae.com/) logic analyser. There are two big activity blocks corresponding to the Linux Kernel and the Root Filesystem. Here is the rootfs:

![ROOTFS](./pictures/rootfs.png)

First the raw data are extracted with the Saleae SPI decoder feature and transformed in binary format with a [python script](./scripts/make_bin.py). However, the raw data still contain some handshake informationas we see on the waveform:

![handshake](./pictures/handshake.png)

A [second script](./scripts/extract_nand.py) removes the handshake. Moreover we have to remove some `0xFFFFFFFF` at the end of the file -- and we have now the root filesystem:

```
binwalk rootfs.cradl
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
0             0x0             Squashfs filesystem, little endian, version 4.0, compression:xz, size: 18464354 bytes, 2026 inodes, blocksize: 262144 bytes, created: 2022-06-02 18:01:34
```

With `unsquashfs` we can extract all the files.

## Patch the Firmware to get a Root Shell
The device implements a shell accessible over SSH or internal webserver. However, this is not a linux shell but has only limited application-related commands. We will now patch this shell to get a linux root shell. The device SW is based on Linux and the application is almost completely written in Python.

Moreover, the application includes a feature that (re-)enables silent boot every time the application starts. We also need to patch this feature. In `/service_manager/services` we find a file called `silentboot.pyc`. Let's decompile this file with `decompyle3`:

We see that the u-boot `silent` variable is changed to `yes`. We can remove that:

Now we have to recompile the python source file in a `pyc` file and replace the original one. We can then re-build the squashfs image:

```
mksquashfs squashfs-root/ rootfsimage -b 262144 -comp xz -no-xattrs
```

***Here: How to patch root shell***

In the next chapter we will see how to flash the squashfs image in NAND Flash.
 
## Flash the patched Firmware 

To test our patched firmware we now need to flash it back in the NAND Flash. These are the steps:
1. Boot the device with silent mode **disabled** (with buspirate and flashrom, don't forget the CRC)
2. Interrupt u-boot via serial interface and get a u-boot console
3. Use TFTP Boot to boot a kernel from openWRT with prompt and root shell
4. Use the UBI commands to erase and flash the NAND Flash Kernel and ROOTFS

**Caveat**: even if only ROOTFS is changed, it is necessary to update the KERNEL too. 


### Preparation of KERNEL image

The raw kernel image dumped from flash contains:
* Linux Kernel in gzip format 
* ROOTFS parameters (crc and length) located at the end of the gzip kernel binary
* Device Tree
The image uses u-boot image format so we can use `mkimage` and `dumpimage`. 

First print info:

```

```

Then extract device tree and kernel:

```

```

We can now modify the kernel.gz binary with the ROOTFS information. The three last words of the kernel.gz file contain CRC, Length and 0x00000000 in little endian format. Note that these three words are not part of the compressed image, they are just added at the end.

First calculate the CRC of the ROOTFS image:
```
crc32 rootfsimage
```
Note the length of the rootfs image in bytes, convert in hex:
> E.g. 19034112 bytes, or 0x01227000 bytes

Open kernel.gz in a hex editor, change the CRC and length. For example:
* Original (CRC - Length - 0x0):
> 0xB4D11088 0x00733302 0x00000000
* Changed :
> 0x67452301 0x00702201 0x00000000

Now we can re-build the KERNEL image:
First we need to decompile the device tree with `dtc`, and then we can build the KERNEL image with `mkimage`:

```
dtc -I dtb -O dts dt.dtb -o dt.dts 
mkimage -f image.its kernelimage
```

Note: `image.its` is provided [here](./boot/image.its)


**Note about UBI**: Between the bare NAND FLash and the squashfs filesystem there is a layer inbetween called [UBI](http://www.linux-mtd.infradead.org/doc/ubi.html), which takes care of the Flash block management. 



## Software Update Mechanism

## Man in the Middle 

## Discosure

We disclosed our findings to Cradlepoint on 2023-01-05.
