# Rooting the Cradlepoint IBR600 and other stories

This is a description of the work I did with [stulle123]() end 2022 on the Cradlepoint IBR600C-150M-B-EU with FW Version 7.22.60.

## IBR600C

It was a sunny day in September 2022 when someone put this device on my desk.

![crad](./pictures/crad.png)

I could not resist to open it and see if I could get some information about the boot process and eventually the firmware. The main processor is a Qualcomm IPQ4019 with SDRAM, NOR and NAND Flash. A UART interface is accessible:

![UART](./pictures/uart.png)

At boot time, the UART interface only gives very limited information about the first bootloader, after that it becomes silent. It is time to have a look in the Flash memory. NOR and NAND Flash is a typical combination - bootloaders in NOR, OS and Application in NAND. Both flashes are connected via the same SPI bus to the processor. NAND Flashes are not easy to dump because of the bad blocks and error management. But the NOR Flash is easy to dummp with a [Bus Pirate](http://dangerousprototypes.com/docs/Bus_Pirate) and [Flahrom](https://www.flashrom.org/Flashrom). The content is not encrypted and secure boot is not in place. 

The u-boot environmental variables are a good starting point: in our case, a `SILENT` variable is set to `YES`. By changing it to `NO`, we get a u-boot console:

At this point, it may be possible to load some [openWRT](https://openwrt.org/) firmware. TFTP loader is implemented in u-boot.

### 



## Discosure

