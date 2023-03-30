# Rooting the Cradlepoint IBR600C and other stories

This is a description of the work I did with [stulle123](https://github.com/stulle123) end 2022 on the Cradlepoint IBR600C-150M-B-EU with FW Version 7.22.60.

## IBR600C Flashdump

It was a sunny day in September 2022 when someone put this device on my desk.

![crad](./pictures/crad.png)

The IBR600C is an LTE Modem & Router with Wifi, LAN and WAN Interfaces. It has an embedded webserver and cloud connectivity to the Cradlepoint Netcloud. 

I could not resist to open it and see if I could get some information about the boot process and eventually the firmware. The main processor is a Qualcomm IPQ4019 with SDRAM, NOR and NAND Flash. A UART interface is accessible:

![UART](./pictures/uart.png)

At boot time, the UART interface only gives very limited information about the first bootloader, after that it becomes silent. It is time to have a look in the Flash memory. NOR and NAND Flash is a typical combination - bootloaders in NOR, OS and Application in NAND. Both flashes are connected via the same SPI bus to the processor. NAND Flashes are not easy to dump because of the bad blocks and error management. Here is a picture of the device opened with logic analyser, serial interface and bus pirate connected:

![opened](./pictures/opened.png)

### NOR

The NOR Flash is easy to dummp with a [Bus Pirate](http://dangerousprototypes.com/docs/Bus_Pirate) and [Flashrom](https://www.flashrom.org/Flashrom). The content is not encrypted and secure boot is not in place. 

The u-boot environmental variables are a good starting point: in our case, a `SILENT` variable is set to `YES`. By changing it to `NO`, we get a u-boot console:

At this point, it may be possible to load some [openWRT](https://openwrt.org/) firmware. TFTP loader is implemented in u-boot.

### NAND 

NAND Flash dump is complicated to dump, I recorded the SPI interface during the boot phase with the [SALEAE](https://www.saleae.com/) logic analyser. There are two big activity blocks corresponding to the Linux Kernel and the Root Filesystem. Here is the rootfs:

![ROOTFS](./pictures/rootfs.png)

First the raw data are extracted with the Saleae SPI decoder feature and transformed in binary format with a python script. However, the raw data still contain some handshake information:

![handshake](./pictures/handshake.png)

A second script removes the handshake and we have now the root filesystem:

```
binwalk rootfs.cradl
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
0             0x0             Squashfs filesystem, little endian, version 4.0, compression:xz, size: 18464354 bytes, 2026 inodes, blocksize: 262144 bytes, created: 2022-06-02 18:01:34
```


## Discosure

