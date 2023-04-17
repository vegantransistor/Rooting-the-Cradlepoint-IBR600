# Recon

## Device Info

- NCOS version `v7.22.60`
- Serial number: `WA203400365100`
- MAC addresses: `2a:30:44:53:9a:38` (LAN), `00:30:44:53:9a:38` (WAN)

### Init System
- Kernel `4.4` --> kernel exploits [available](https://www.exploit-db.com/) (danger zone, might brick the device)
- Uses SysVinit
- Init program: `/init`
- `/etc/inittab`:
  - `su:S:wait:/sbin/sulogin -p` (need to copy the `sulogin` binary to the device for this to work)
  - **TODO**: Try to boot into Single-User-Mode by adding `S` to the kernel command line
- Main boot script: `/etc/rc`

## Remote Attack Surfaces

- Search for `CradlepointHTTPService` and `SSH-2.0-CradlepointSSHService` on ZoomEye or Shodan.

### Remote Technical Support

- If enabled, the `cproot` user is activated (see details [here](https://customer.cradlepoint.com/s/article/Security-Update-Tech-Support-Mode-warning-bypass))
- Technical support can be enabled in `/service_manager/config_dtd.jsonmin`
- Main `handle_techsupport_access_enable_attempt()` method in `/service_manager/service_manager.pcy` which validates the license file by calling `validate_license()` in `/service_manager/service/utils/feature.pyc`
- Need to update the license file to enable technical support access
  - License can be seen using the `feature` command in the CPshell
  - `/service_manager/_factory.bin.extracted/100E7` includes or points to the license file (`SeenKeyFiles` dictionary key in `feature.pyc`)
  - License can be updated via the Web UI (see [here](https://customer.cradlepoint.com/s/article/Changing-Licenses-within-NetCloud-Manager))
  - The license file is signed with a RSA private key :-(
  - RSA Public Key (the RSA private key has 2048 bits):
```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAq7bUMXk3DRxObHM+do6K
nSCCYB3AcDAk0R56O+SopnOyeMbtUPzoxllDsX9+hiJDyrIrPVJsd1hs7jHjhxiX
yNXEZtItZ3VTbCrK/08dXCB8Ujpmf/NlEUn+EGislviOKB6rw9eBOrKf2OCQs1mc
pAnfANXbjpsZ+t+yn6bGIfvNgUdQbel/FXITMqPr2L+zqirI4r0Y7VicGqYzyahR
xT8rEd/I2/11FrbaVT/ps+y/GmGODi3d3LZX1pH+wgH2yHCWcNTs0CPTDg9QpPxM
fWREQHJzo+Vp8XGHKbEPgczYOPHWrgbeAjSR/C/FND7ZrCTD9rt7O1x4AWWcu/Pm
ZQIDAQAB
-----END PUBLIC KEY-----
```
  - `validate_license()` method in `/service_manager/service/utils/feature.pyc`:
    - Signature must be a valid RSA signature
    - MAC address must be on a `License Authorized MAC` list
    - USB serials must be on a `Authorized Serial` list
    - `AuthorizedFeatures` must include the string `f0c200da-ff54-11e9-96a9-acde48001122`

## LAN Ports

- TCP: `22`, `53` (dnsmasq), `80`, `443`, `20000`, `30000`, `35000`, `45000`, `46000`, `47000`
- UDP: `60066` (syslogd), `53` and `67` (dnsmasq)
  - `/usr/sbin/dnsmasq--keep-in-foreground--no-hosts--no-resolv--no-poll--expand-hosts--dhcp-authoritative--dhcp-script=/usr/bin/dnsmasq_client--localise-queries--leasefile-ro--dhcp-generate-names--domain-needed--addn-hosts=/tmp/hosts--servers-file=/tmp/dns-servers--dhcp-hostsfile=/tmp/dhcp-hosts--interface=primarylan1,guestlan2--domain=local.tld--local=/local.tld/--dhcp-range=set:l_primarylan1,10.10.15.85,10.10.15.170,255.255.255.0,720m--enable-ra--dhcp-range=set:l_primarylan1,::1,::5555,constructor:primarylan1,slaac,64,3600m,3600m--dhcp-range=set:l_guestlan2,192.168.10.85,192.168.10.170,255.255.255.0,720m--dhcp-range=set:l_guestlan2,::1,::5555,constructor:guestlan2,slaac,64,720m,3600m--log-facility=/dev/null`
  - `/sbin/syslogd-n-t-l7-T-f/var/tmp/syslog.conf-s200-F10-L-R10.225.29.222:5520-HIBR600C-a38 - DummyCompany-DummyTown?-u`

## Services

First, [dump the rootfs](../README.md#dumping-nand). In the `/service_manager` directory there are a lot of interesting *services* which are implemented in Python.

Simply search for interesting strings in the Python byte code files:

```bash
$ for i in $(find /service_manager -name "*.pyc"); do echo $i; strings $i | grep -i "Password"; done
```

Results:

- `service_manager/services/utils/__init__.pyc` (password generation)
- `service_manager/services/httpserver`
- `service_manager/cpshell.pyc` (custom shell)
- `service_manager/services/shell.pyc`
- `service_manager/services/sshserver.pyc` (custom SSHD with [libssh](https://www.libssh.org/) under the hood)
- `service_manager/services/usb_serial_services.pyc` (SSH via USB)
- `service_manager/services/passwd.pyc` (interesting `authenticate()` method)
- `service_manager/services/httpserver/fw_handler.pyc` (firmware upgrade)
- `service_manager/service_manager/services/utils/upgrade_write.pyc` (firmware upgrade helpers)
- `service_manager/services/usb_upgrade.pyc` (firmware upgrade via USB)
- `service_manager/validators/snmpd.pyc` (SNMP daemon)
- `service_manager/services/mqtt.pyc` (MQTT daemon)
- `service_manager/services/sms_protocol.pyc` (SMS daemon)
- `service_manager/services/wpcclient/shell.pyc` (NetCloud tool)

## Default Passwords

There are a couple of default passwords generated in different parts of the code. Some of them work in some cases, some don't.

### Su Password

There's a `getSuPassword()` function in `/service_manager/services/utils/__init__.pyc` which generates a password from the router's MAC address:

Example with a MAC address of `00:30:44:53:9a:38`:

- `str(math.pi)[2:6]` --> `1415`
- `'%02x%02x' % tuple(boardinfo.mac_addrs[0])[-2:]` --> `0308`

Which means the password is `14150308`.

### Default User Password

Another interesting method is located in `service_manager/board/qcomboard.pyc` where a default password is generated from the MAC or Serial Number of the device:

```python
def _default_passwd(self):
    mac_addr = []
    mfg_date = None
    new_passwd = False
    serial_num = None
    _ = mfg_date
    mac_addr = self.mac_addrs[0][-4:]
    if mac_addr and len(mac_addr) == 4:
        mac_passwd = '%02x%02x%02x%02x' % tuple(mac_addr)
    else:
        logger.warn('Invalid MAC address')
        return ''
    try:
        f = NORFlashIO(mtd.name2dev('0:CUSTDATA', rwdev=False))
    except OSError:
        f = MMCFlashIO(mtd.name2dev('0:CUSTDATA', rwdev=False))
    else:
        if f:
            data = f.read()
            data = data.split(b'\n')
            for d in data:
                if d == b'':
                    break
                else:
                    if d.startswith(b'MfgDate='):
                        mfg_date = d.decode().split('=')[1]
                    if d.startswith(b'SerialNumber='):
                        serial_num = d.decode().split('=')[1]
                if d.startswith(b'NewPassword='):
                    new_passwd = d.decode().split('=')[1]

        else:
            raise RuntimeError('Invalid board custdata partition')
        if not (serial_num and len(serial_num) == 14):
            logger.warn('Invalid Serial Number')
        if new_passwd:
            if serial_num:
                if len(serial_num) == 14:
                    return serial_num
        return mac_passwd
```

The password is either the 14-digit serial number of the device or the value `090a0308` (taking the MAC address `00:30:44:53:9a:38`as an example). This is also documented on the Cradlepoint [website](https://customer.cradlepoint.com/s/article/default-password-for-a-series-3-router).

### Miscellaneous

- `/service_manager/filemanager.pyc` reads the `shadow` file
- In `genericboard.pyc`: `default_passwd = '00000000'`
- There are default passwords in `/service_manager/config_dtd.jsonmin`
- The SSH host private key is stored in `/tmp/.ssh/rsa.raw.key`
- Certificates: `/tmp/certificates/cas/certs.pem`
- `/server_manager/services/certmgmt.pyc` uses the [Cryptography package's](https://github.com/pyca/cryptography) "Hazardous Materials" module and generates a couple of private keys (`_DSAPrivateKey`, `_RSAPrivateKey`, `_EllipticCurvePrivateKey`, `_Ed448PrivateKey`, `_Ed25519PrivateKey`)
  - **TODO**: check for possible crypto implementation flaws (see [warning](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/))
- `/service_manager/_factory.bin.extracted/100E7` is a "key database". It's signed with a simple key generated from the device's MAC address in `/service_manager/service/utils/feature.pyc`:
```python
def _generate_sig(db, mode=None):
   global cached_mac
   msg = _get_digest_str(db)
   if not cached_mac:
       cached_mac = bytes(board.mac_addrs[0])
   return hmac.new(cached_mac, (msg.encode()), digestmod=(hashlib.md5)).hexdigest()
```
- Encrypted passwords are stored in `/service_manager/config.bin` (factory default configuration):
  - Extract contents with `$ binwalk --extract config.bin`
  - There are several keys and passwords stored in the `100FF` binary file
  - The encrypted `admin` user password is also stored in the `200EA` binary file
- In `/service_manager/config_store.pyc` there's an AES encryption key used for encrypting values in `/service_manager/config.bin`:
```python
x2 = 'x^699oW59oWV'
x1 = '^GpkO6gx5GE'
x4 = 'A0iWoz^To='
x3 = 'moji0i6Iz5j'
eKey = (x1 + x2 + x3 + x4).translate({ 94: 78, 112: 74, 57: 104, 87: 50, 105: 77, 54: 68, 53: 90, 120: 49, 111: 89})
```
  - AES Encryption Key in base64: `NGJkODg1ZGE1NDhhY2ZhY2VmYjM0MDIzZjA0M2YzNTY=` (this was already [disclosed in 2018](https://packetstormsecurity.com/files/150203/Cradlepoint-Router-Password-Disclosure.html) and fixed)
- CP Zscaler Device Certificate (Zscaler seems to be a web traffic filter service which is used in `/service_manager/services/webfilter/zs.pyc`, see [here](https://customer.cradlepoint.com/s/article/NCOS-Configuring-Zscaler-Internet-Security) for more details):
```
-----BEGIN CERTIFICATE-----\nMIID3jCCAsagAwIBAgIRAIcsrj2eWzN3pVmUlu0RB8EwDQYJKoZIhvcNAQELBQAw\nZTELMAkGA1UEBhMCVVMxEzARBgNVBAgMCkNhbGlmb3JuaWExEDAOBgNVBAoMB1pz\nY2FsZXIxLzAtBgNVBAMMJkVUIHByb2QuenBhdGgubmV0IFRMViBSb290IENlcnRp\nZmljYXRlMB4XDTE5MDEyMTIzMDQ1OVoXDTI5MDExODIzMDQ1OVowdTELMAkGA1UE\nBhMCVVMxDjAMBgNVBAgMBUlkYWhvMQ4wDAYDVQQHDAVCb2lzZTEZMBcGA1UECgwQ\nQ3JhZGxlcG9pbnQsIEluYzErMCkGA1UEAwwiY3JhZGxlcG9pbnQuY29tLnRsdi5w\ncm9kLnpwYXRoLm5ldDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMzx\nRYcutx6omCe62UdWxtw6aNSDScWt6VB3MFx5hq2IjLZnkeRjF05I2SA5YHgHIm5J\nW5h5HbrWENMDoeDCBNL8pVjHoWT4yD2B1yQa01RWOSUIhMkQgJk33HJiZgWAxiD7\nhcT0Ul1PZFyYnGd4VfdxvykDp8q+OY4KWuJabXyEZKvrHEkgk6l2l1lwvKJZevLw\nP5R5/+ESV+QKoXSSty8DpxTNyUS2UP46cVA43qVQ1NjRuRW3hg04wCUXYyTCzOPB\nLtsnVZ6HT7ezkEJR5La9lUfb5iUvbhXq7TtLvPlL16+8iazfIJK59FogQe2AoCOm\n9B7nUwUL/uRYoLtbWtcCAwEAAaN5MHcwCQYDVR0TBAIwADALBgNVHQ8EBAMCBaAw\nHQYDVR0lBBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMCMB0GA1UdDgQWBBRRcWMc/XGQ\nySYvp0JgXYgU+qNglDAfBgNVHSMEGDAWgBRG9dz5qOGbaZgQwMVSzwdgZrsiNjAN\nBgkqhkiG9w0BAQsFAAOCAQEALpddx5Bt4//3JMMABFupHNZ0rycxMzHA8On8lYIY\nTbjnIfPEdXSlmWuduaPioIMikAo7ewg+1PbP0psIhZLqGszf5bjvWzXabW9raKcP\n//o9QXPTuDhpRkXRt9tquXCidnweKGAofQvV2YnvCLMFGR1AH3FujhOtcHLokCXD\nNArrFjXXDsaY+UbC+iyLvQsCIrLX210K7p/C+j7FsOm0qX68zVjV6JxEL1KMIXkg\nA+4lphl7DN0cmQu4YeYUomZRLJkJbXeisHkieKIFTaHUEYz+oGQDxY2Ri5fBeDTm\nZvwXFtC/6+oajr2K43L2cwDTHCDj1Nz+letkE+JlWAAzjw==\n-----END CERTIFICATE-----
```
```
-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDM8UWHLrceqJgn\nutlHVsbcOmjUg0nFrelQdzBceYatiIy2Z5HkYxdOSNkgOWB4ByJuSVuYeR261hDT\nA6HgwgTS/KVYx6Fk+Mg9gdckGtNUVjklCITJEICZN9xyYmYFgMYg+4XE9FJdT2Rc\nmJxneFX3cb8pA6fKvjmOClriWm18hGSr6xxJIJOpdpdZcLyiWXry8D+Uef/hElfk\nCqF0krcvA6cUzclEtlD+OnFQON6lUNTY0bkVt4YNOMAlF2MkwszjwS7bJ1Weh0+3\ns5BCUeS2vZVH2+YlL24V6u07S7z5S9evvIms3yCSufRaIEHtgKAjpvQe51MFC/7k\nWKC7W1rXAgMBAAECggEATrJ/bm+j5eP7uZXohZpu9nZ/dsuLcptbsohyS7Bm5RBA\naHLQ9RCQDIGwzsz5nF2w/QSyZZRstCgrgbwtVy9pxtM5cyQFd86IpgXL5ZNff000\n2GGzC7qIh02KG2ppnsdaTaQINB9V2Xr5IQ2BUcJF0KUfMNK0hggR9ddIGw96Z4uH\nYR5msUlaXw3nMRUxK9fPleuyGrPgyAIjTt9YXJqUXqH28YhZG87KDDZ9HBoHOjFI\na1jaCsg2mzIgNKhGat71ovufH4ssiVLBbYL5ce8n6ly+7p9/3Cj0GH5o+gupejB7\nuWzcZWR1Q/A8sU3AbuDYNkdcL/7NkxP9UWV3rWyagQKBgQDp5lxwktWvOHRDd+I8\njIVfBO7dWUu4wd3Of16an99jZMWl0L66LgoF/+CYb2ATQaonymLzhmHJWW2sY9GY\nJCzi/sD6pf74c20IB1wopTdptYA76oWuOOwhNs936yYttTpELNP546cQIfST607Y\nJmlzaGoB4vRwD2Mw8SVmwUg7IQKBgQDgTnsUnRWxotS7cm3Ie3Yz60lX6Yltos6d\nmxaFDRt7vC4zhdyJN6xqnqSfIimsHeyDi93SCPl6qzNFAIUi1wb8SXN/WZJxBRsG\ncKMuB0HPCMKyYUeBEPooYNyorejvyJ27sYh0QbvKczJ1rXnPiVnf5cib+nLMpHeg\ndwwnQB6O9wKBgBY6QgagrZXdM49F0UYXxITnHxwB5GRGaCG7kO34y23SocXENJvU\nzDcNvfY+f07VKqplXUnvN1O/H+EGC2D97xYTR5uKMtTBg1cD/AoQyVdOXEVVYCbS\nWf4+CzFGM3achlD8QZi5vaKW13tHHVMFM3g4L/rF6pzLmY2JHRjKvWaBAoGAb2tM\nhB7LaeOCXGIo2k9JldyoH/0ngMhAbdVdyFWMc1g0cu9pbtey03teNpXXsWFj3Kwb\nUXuXwTFNVFc/yuCY3bT2pCmwLmfk1rwYsoJ0VAz7+XOM+zWdrXT/5uIMNR+oClXT\nfDwytgum4wF64nZNqIQRtDkh0TlZGuJHrS+Sfl0CgYEAqK00waZUxq2/2HYiixzO\n749a3M/aqsUK04DOadQkljfBbpO0fASd9YcKB3+J75ZWpHYXSvZoDVZShJy2GP6h\ns9QUwOkSUh8AKRAoyJFAxye/MBIOYpufl/N/Q83DzobJSrUtJv/Mz8+KwR9Qc7qs\nQeC3fNIV+KTWak2/2gdTzbs=\n-----END PRIVATE KEY-----
```
