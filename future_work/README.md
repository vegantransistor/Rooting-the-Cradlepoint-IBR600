# Future Work

This is a list of things we haven't tried yet and which might be interesting to take a look at:

## CPShell Escape

- Related work: [CVE-2022-3086](https://securitybytes.me/posts/cve-2021-37471/)
- Enable `su-cmds` in the CPShell command prompt:
  - Set `superuser` to `True` in `cpshell.pyc` and [rebuild/reflash the rootfs](../README.md#flashing-the-nand-images)
  - Enable technical support access in `service_manager.pyc` by modifying the `techsupport_access` method and [rebuild/reflash the rootfs](../README.md#flashing-the-nand-images)
- Try a shell escape with [ssh](https://gtfobins.github.io/gtfobins/ssh/), [telnet](https://gtfobins.github.io/gtfobins/telnet/), [tcpdump](https://gtfobins.github.io/gtfobins/tcpdump/), [find](https://gtfobins.github.io/gtfobins/find/), [diff](https://gtfobins.github.io/gtfobins/diff/) or [grep](https://gtfobins.github.io/gtfobins/grep/)
- Read password values with `get` command from config file(s)
- Edit files with the `edit` command --> Add backdoor to `/etc/rc` script
- In the router's rootfs grep for possible command injection flaws:
```
$ grep -iE "os.system|os.popen|commands.getstatusoutput|commands.getoutput|commands.getstatus|subprocess.call|subprocess.run|subprocess.Popen|pty.spawn|execfile|exec|eval"
```

## Miscellaneous

- Exploit known CVEs (see CVEs in CP's [Release Notes](https://customer.cradlepoint.com/s/article/Series-3-Firmware-Release-Notes-5-1-1-to-Most-Current-Firmware))
- Exploit known CVEs in open-source and Python libs
- Mess with the router's Rest API on the LAN interface, maybe there are hidden values that we can write (see [documentation](https://customer.cradlepoint.com/s/article/Is-it-possible-to-make-a-local-API-call-to-a-Cradlepoint-router))
  - `$ curl -u admin:admin --insecure http://192.168.0.1/api/config/firewall/ssh_admin/enabled`
- Mess with Cradlepoint's [Troubleshooting Tools](https://customer.cradlepoint.com/s/article/NCOS-Troubleshooting-Tools)
- Mess with `scp`. The [modem firmware can be upgraded](https://customer.cradlepoint.com/s/article/GPS-Not-Acquiring-Valid-GPS-Coordinates-After-2019-on-LPE-and-LP3-Modems) with `scp`. Maybe other stuff is possible as well.
- Try [command injection](https://gist.github.com/btoews/1528735) with `tcpdump` (the argument list is not filtered)
- Fuzz network protocols (`80`, `22`, `MQTT`, etc.)
- Try to [get a shell](https://github.com/mxrch/snmp-shell) with `SNMP` (CP uses `NET-SNMP` and we have a writable community strings available)
- NTP or DNS client-side attacks possible?
- Find bugs in the custom HTTP Server and REST API
- Dig into the Wifi stack
- Dig into the modem / baseband unit
  - Find bugs in the SMS message parser/receiver
- Find bugs in the custom SSH server
- Find bugs in the custom shell
- Try to bypass the license checks (see [Reddit thread](https://www.reddit.com/r/sysadmin/comments/wk6744/cradlepoint_licensing_terms_update/?rdt=47589))
- USB attacks, e.g.:
  - Flash malicious firmware via USB
  - USB stack fuzzing
