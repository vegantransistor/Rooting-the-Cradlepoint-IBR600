# How to build an OpenWRT Image for the Cradlepoint IBR600C Router

* Download an OpenWRT image for the `IPQ4018` with initramfs and uimage (e.g. [this one](https://downloads.openwrt.org/releases/22.03.3/targets/ipq40xx/generic/openwrt-22.03.3-ipq40xx-generic-8dev_jalapeno-initramfs-fit-uImage.itb)).

* Information about the image can be printed out with the `dumpimage` command:

```bash
$ dumpimage -l openwrt-22.03.3-ipq40xx-generic-8dev_jalapeno-initramfs-fit-uImage.itb 
FIT description: ARM OpenWrt FIT (Flattened Image Tree)
Created:         Tue Jan  3 01:24:21 2023
 Image 0 (kernel-1)
  Description:  ARM OpenWrt Linux-5.10.161
  Created:      Tue Jan  3 01:24:21 2023
  Type:         Kernel Image
  Compression:  gzip compressed
  Data Size:    9172760 Bytes = 8957.77 KiB = 8.75 MiB
  Architecture: ARM
  OS:           Linux
  Load Address: 0x80208000
  Entry Point:  0x80208000
  Hash algo:    crc32
  Hash value:   70ea10e1
  Hash algo:    sha1
  Hash value:   57a8b4005aa83fe8f2c90a06b392bae265c81de9
 Image 1 (fdt-1)
  Description:  ARM OpenWrt 8dev_jalapeno device tree blob
  Created:      Tue Jan  3 01:24:21 2023
  Type:         Flat Device Tree
  Compression:  uncompressed
  Data Size:    16599 Bytes = 16.21 KiB = 0.02 MiB
  Architecture: ARM
  Hash algo:    crc32
  Hash value:   9ea4cad2
  Hash algo:    sha1
  Hash value:   8dc5e93d9f11382a1af584f01ee3a81279abf7d2
 Default Configuration: 'config@1'
 Configuration 0 (config@1)
  Description:  OpenWrt 8dev_jalapeno
  Kernel:       kernel-1
  FDT:          fdt-1
```

* Extract the kernel with `dumpimage`:

```bash
$ dumpimage -T flat_dt openwrt-22.03.3-ipq40xx-generic-8dev_jalapeno-initramfs-fit-uImage.itb -p 0 -o kernel.gz
Extracted:
 Image 0 (kernel-1)
  Description:  ARM OpenWrt Linux-5.10.161
  Created:      Tue Jan  3 01:24:21 2023
  Type:         Kernel Image
  Compression:  gzip compressed
  Data Size:    9172760 Bytes = 8957.77 KiB = 8.75 MiB
  Architecture: ARM
  OS:           Linux
  Load Address: 0x80208000
  Entry Point:  0x80208000
  Hash algo:    crc32
  Hash value:   70ea10e1
  Hash algo:    sha1
  Hash value:   57a8b4005aa83fe8f2c90a06b392bae265c81de9
```

* Unzip the kernel image and compress it with `lzma` (we need this because of the size!):

```bash
$ gunzip -k kernel.gz
$ lzma kernel
```

* Build the image using `image.its` and the device tree `dt.dtb` (provided as `dtb` and `dts` for readability reasons):

```bash
$ mkimage -f image.its wnc-fit-uImage_v005.itb
```

* [Download this image via TFTP](../README.md/#booting-openwrt)
