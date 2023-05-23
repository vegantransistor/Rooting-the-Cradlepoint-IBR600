## mitmproxy_netcloud_logging.py

Script for parsing and logging NetCloud packets with mitmproxy (see [here](../README.md#mitm-netcloud-traffic-with-mitmproxy) for details).

## parse_netcloud_packets_from_yaml.py

Parses NetCloud packets from a YAML file exported by Wireshark (see [here](../README.md#decrypt-netcloud-traffic-in-wireshark) for details).

## test_netcloud_registration.py

Script for poking at the router registration process with NetCloud.

Quick instructions:

- Install the `netifaces` package: `$ pip install netifaces`
- The script requires the `api` folder and the `stream.crt` file
  - Note: The `stream.crt` file has been patched to work on a Mac. You may adapt it.
- In the script, change the variables which have `Required` in the comment
- Adjust the flags as needed to control the different registration stages. **Note**:
  - To register a device, one needs valid NetCloud credentials and the MAC Address of the router.
  - NetCloud provides an access token which the router later uses to connect to NetCloud.
  - It seems that a router which is already registered can be re-registered and a new token is generated (only the last token seems to be valid).
