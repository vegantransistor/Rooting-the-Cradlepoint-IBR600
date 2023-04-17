# Router Emulation

As soon as you have the [router's rootfs](../README.md#dumping-nand) you can simply emulate it with Qemu. Steps:

1. [Get the rootfs](../README.md#dumping-nand)
2. Get `wlan.pyc`, `link.pyc`, and `__init__.pyc` from `/usr/lib/python3.8/cp/`, [decompile](https://github.com/rocky/python-decompile3) and patch them:
- `wlan.pyc`: Comment/remove the `if platform == 'host'` check at the end of the file
- `link.pyc`: Again, remove the `if platform != "host"` check 
- `__init__.pyc`: Change `platform = 'router'` to `platform = 'host'`
3. Get Qemu. It's the easiest to get it from [Docker Hub](
https://hub.docker.com/r/multiarch/qemu-user-static/):
```bash
$ docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```
4. Create a Docker container from the router's rootfs:
```bash
$ docker import - "my-router" < rootfs.tar
```
5. Run the container and mount your local directory that contains the files from step 2)
```bash
$ docker run -it --rm -v <directory-with-patched-files>:<mount-point-inside-container> --name my-router my-router bash
```
6. Change the `MOUNTED_FOLDER` variable in the [setup.sh](./setup.sh) script and run it:
```bash
# sh <path-to-setup.sh>
```
7. Finally, launch the `Service Manager` from within Docker:
```bash
# cppython service_manager/service_manager.pyc --daemon
```
8. Access the web interface via `localhost:10000` (user: `admin`, pw: `00000000`). 

SSH doesn't work, but you can also open the CLI via the web interface (`System` tab --> `System Control` --> `Device Options` --> `Device Console`).

**Optional**: to change the MAC address of the emulated device follow these steps:

1. Decompile `/service_manager/board/genericboard.pyc` into `genericboard.py` with [decompyle3](https://github.com/rocky/python-decompile3/tree/master/decompyle3)
2. Change the MAC:
```python
class GenericBoard(object):
   eth_q_affinity = None
   eth_q_irq_name = None
   _mac_addrs = [[0,0,0,0,0,0]]
   packet_accel = PacketAccel()
   eth_base_mod
```
3. Replace `/service_manager/board/genericboard.pyc` with your decompiled Python file
