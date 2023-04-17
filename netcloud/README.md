# NetCloud

- [Recon](#recon)
- [Get Access Token](#get-access-token)
- [Decrypt NetCloud Traffic in Wireshark](#decrypt-netcloud-traffic-in-wireshark)
- [MITM NetCloud Traffic with mitmproxy](#mitm-netcloud-traffic-with-mitmproxy)
- [Disconnect any Cradlepoint Router from NetCloud](#disconnect-any-cradlepoint-router-from-netcloud)
- [RCE](#rce)

## Recon

Cradlepoint documentation:

- [How to connect a router to NetCloud](https://customer.cradlepoint.com/s/article/NCM-Connecting-Devices)
- [NetCloud API to query routers remotely](https://customer.cradlepoint.com/s/article/NCM-APIv2-Overview)
  - [API query examples](https://developer.cradlepoint.com/)
- [Enable remote administration](https://customer.cradlepoint.com/s/article/NCOS-How-to-Configure-Remote-Administration-on-a-Cradlepoint-Router)

WPC Authentication / ECM:

- https://accounts.cradlepointecm.com/
  - Login with username and password
- The router uses a login `token_id` and `token_secret`
  - Token stored in NOR storage
  - `$ binwalk –extract nordump_pw0000.bin`
  - `$ grep -rl "wpc.auth" .`
- `ecm` command in the router's CLI
  - Privileged sub-commands: `tri`, `ale`, `dif`
- Connection
  - Server: `stream.cradlepointecm.com`
  - Port: `8001`
  - Certificate: `/service_manager/services/wpcclient/stream.crt`
- "Insecure Activation" (see `wpcclient.pyc`) probably only works if it's manually activated from the NetCloud side (see [use case](https://customer.cradlepoint.com/s/article/How-To-Have-Cradlepoint-register-a-router-to-NetCloud-Manager-when-it-is-physically-not-accessible)).
- "Insecure Activation" was also used to generate temporary credentials for brand-new devices (fixed by Cradlepoint after our report, fix verified by us).

## Get Access Token

Read NetCloud token from a [patched router CLI](../README.md#flashing-the-nand-images):

Connect to the router via SSH:

```bash
ssh admin@192.168.0.1
admin@192.168.0.1's password: 
[admin@IBR600C-a38: /]$ sh
/service_manager # cppython
```

... and paste the following into the interpreter:

```python
import filemanager
from board import board
file_io = board.get_partition("2nd Filemanager", rwdev=True)
fm2 = filemanager.FileManager2(file_io)
token = fm2.get("wpc.auth")
```

Example output: `(2439001, 0, '2b29ffccbda7e45df943dc1e82a096af04e24249', 'stream.cradlepointecm.com', 8001)`

You can use the `netcloud` command to register the router with the token:

```bash
[admin@IBR600C-a38: /]$ netcloud register --token_id=0 --token_secret=2b29ffccbda7e45df943dc1e82a096af04e24249
```

## Decrypt NetCloud Traffic in Wireshark

This step requires a rooted device (see [here](../README.md) for details).

1. In the dumped rootfs set the `SSLKEYLOGFILE` environment variable in `/etc/rc` and [reflash](../README.md#flashing-our-custom-kernel-and-rootfs) the device:

```bash
export SSLKEYLOGFILE=/tmp/ssl_key.txt
```

2. Connect to the router via SSH and start tcpdump:

```bash
ssh admin@192.168.0.1
admin@192.168.0.1's password: 
[admin@IBR600C-a38: /]$ sh
/service_manager # cd /var/tmp && tcpdump -i athc00 -w /tmp/netcloud_dump.pcap
```

3. Start a HTTP server to download the PCAP:

```bash
/var/tmp # iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
/var/tmp # cppython -m http.server 8080
```

4. Download PCAP:

```bash
$ wget 192.168.0.1:8080/netcloud_dump.pcap
```

5. Import pre-master secret into Wireshark: Grab the file from step 1) and add it to Wireshark (`Preferences` --> `TLS` --> `(Pre)-Master-Secret logfile name`)

6. Export TLS stream as YAML: `Follow` --> `TLS Stream` --> `Show Data as YAML`

7. Finally, parse the YAML file with this [script](./scripts/parse_netcloud_packets_from_yaml.py).

## MITM NetCloud Traffic with mitmproxy

This how-to sets up your MITM box as a transparent proxy to intercept Netcloud communications with mitmproxy (we used a Raspberry Pi for this purpose).

1. Enable IP forwarding, setup `dnsmasq` and configure `iptables` rules. For example:

```bash
#!/bin/bash
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
sudo iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT
sudo iptables -A FORWARD -i wlan0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 8001 -j REDIRECT --to-port 8080
sudo systemctl daemon-reload && sudo systemctl restart dhcpcd
sudo service dnsmasq restart
```

2. Setup the router's WAN interface to use your proxy as the default gateway (e.g., via the web interface)

3. Install mitmproxy (on Raspberry Pi):

``` bash
$ curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
$ sudo apt-get install build-essential libssl-dev libffi-dev python3-dev cargo
$ git clone https://github.com/mitmproxy/mitmproxy/tree/main/mitmproxy
$ cd mitmproxy
$ pip install -e .
```

4. On the router, copy your MITM CA certificate into the file `/service_manager/services/wpcclient/stream.crt` (trusted CA "store")

5. Copy your MITM CA certificate into mitmproxy's folder. It must have the name `mitmproxy-ca.pem` and the following structure:

```
-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
```

6. Fire up mitmproxy using [this](./scripts/mitmproxy_netcloud_logging.py) logging script:

```bash
$ mitmproxy --mode transparent --set confdir=$HOME/mitmproxy --rawtcp --tcp-hosts ".*" -s mitmproxy_netcloud_logging.py
```

## Disconnect any Cradlepoint Router from NetCloud

**TODO**

## RCE

**TODO**