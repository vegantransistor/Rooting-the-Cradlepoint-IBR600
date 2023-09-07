## mitmproxy_netcloud_logging.py

Script for parsing and logging NetCloud packets with mitmproxy (see [here](../README.md#mitm-netcloud-traffic-with-mitmproxy) for details).

## parse_netcloud_packets_from_yaml.py

Parses NetCloud packets from a YAML file exported by Wireshark (see [here](../README.md#decrypt-netcloud-traffic-in-wireshark) for details).

## test_netcloud_registration.py

Script for poking at the router registration process with NetCloud.

Quick instructions:

- Install the `netifaces` package: `$ pip install netifaces`
- The script requires the `api` folder and the `stream.pyc` file
  - Note: The `stream.pyc` file has been patched to work on a Mac. You may decompile it with [decompyle3](https://github.com/rocky/python-decompile3) and adapt it to your needs.
- In the script, change the variables which have `Required` in the comment
- Adjust the flags as needed to control the different registration stages. **Note**:
  - To register a device, one needs valid NetCloud credentials and the MAC Address of the router.
  - NetCloud provides an access token which the router later uses to connect to NetCloud.
  - It seems that a router which is already registered can be re-registered and a new token is generated (only the last token seems to be valid).

## mitmproxy_netcloud_rce.py

Mitmproxy script to replace the router's pickled license file with a reverse shell payload (see [here](../README.md#rce-through-deserializing-untrusted-data) for details).

To get a shell on the router, please first follow [these](../README.md#mitm-netcloud-traffic-with-mitmproxy) instructions. Adapt `_ATTACKER_IP` and `_ATTACKER_PORT` variables in the script.

Next, simply start mitmproxy:

```bash
$ mitmproxy --mode transparent --set confdir=$HOME/mitmproxy --rawtcp --tcp-hosts ".*" -s mitmproxy_netcloud_rce.py
```

To poke with the NetCloud servers, the reverse shell payload in the script won't work (just adapt it accordingly). Next, run mitmproxy the same as before.

Finally, run `test_netcloud_registration.py` (see instructions above) and wait for your Cradlepoint device to send its pickled license to the NetCloud server. This bug has been already patched by Cradlepoint, but we didn't re-verify :bomb:

For a simple test just use `openssl s_client`:

1) In the script change the IP address to `127.0.0.1` and the payload's Python interpreter to just `python`
2) Start mitmdump in one window: `$ mitmdump --rawtcp --tcp-hosts ".*" -s mitmproxy_netcloud_rce.py`
3) In another window start a netcat listener
4) Tunnel a license packet through `openssl s_client`: `$ cat license_packet_TO_netcloud.bin | openssl s_client -connect "google.com:443" -proxy localhost:8080`