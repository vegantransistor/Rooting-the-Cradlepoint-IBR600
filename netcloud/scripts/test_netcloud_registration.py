""" Simple script to poke at the router <-> NetCloud registration process. """

import socket
import ssl
import json
import functools
import hashlib
import threading
import collections
import netifaces
import api.stream
from api.base import RootException, Timeout, NotRegistered, Disabled, Unauthorized

# Required: Add your NetCloud credentials (required for registering the router with NetCloud)
_CID = "your-netcloud-user"
_CPW = "your-netcloud-password"

# Optional: Alternatively, use an existing NetCloud access token which you get from your rooted Cradlepoint device
_CLIENT_ID = 0
_TOKEN_ID = "your-token-id"
_TOKEN_SECRET = "your-token-secret"

# Required: Your machine's network interface (requires the 'netifaces' package)
_MYIP_IF = netifaces.ifaddresses("<your-nic>")[2][0]

# Required: Add the MAC address of your Cradlepoint router
_MYMAC = "your-MAC"

# Optional: Adjust the following flags as needed to control the different registration stages
_AUTHORIZATION = False
_FULL_REGISTRATION = True
_INSECURE_ACTIVATION = False
_REGISTRATION_VIA_TOKEN = False
_REGISTRATION_VIA_LOGIN_CREDS = False
_BINDONLY = False
_COUNTRY_CODE_EU = True

# Dummy router configuration
_POSTDATA = {
    "queue": "status_reply",
    "id": "on_connect",
    "value": {
        "success": True,
        "data": {
            "__errors__": {},
            "status": {
                "product_info": {
                    "manufacturing": {
                        "board_ID": "606507",
                        "serial_num": "WA203400365100",
                    },
                    "product_name": "IBR600C-150M-B-EU",
                },
                "ecm": {"last_sync_error": None, "sync": "ready"},
                "iot": {
                    "msft": {"status": "disconnected", "history": []},
                    "bluetooth": {"radio": None},
                },
                "wlan": {
                    "region": {"country_code": "EU", "global_wifi": False},
                    "radio": [
                        {
                            "channel": 1,
                            "channel_contention": 2,
                            "channel_list": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                            "channel_locked": True,
                            "reconnecting": False,
                            "region_code": 1,
                            "survey": [],
                            "clients": [],
                            "bss": [{"bssid": "003044539a39"}, {"bssid": None}],
                            "txpower": 100,
                        }
                    ],
                },
                "system": {"uptime": 170508.45228609597},
                "security": {
                    "ips": {"signature_version": None},
                    "default_password": {"admin": False, "wifi": True},
                },
                "fw_info": {
                    "major_version": 7,
                    "minor_version": 22,
                    "patch_version": 60,
                    "build_date": "Thu Jun  2 17:53:14 UTC 2022",
                    "build_version": "297988f4c5",
                    "build_type": "RELEASE",
                    "fw_update_available": False,
                    "upgrade_major_version": 0,
                    "upgrade_minor_version": 0,
                    "upgrade_patch_version": 0,
                    "sign_cert_types": "ROOTCA RELEASE",
                    "manufacturing_upgrade": False,
                },
            },
            "service": {
                "ecm": {
                    "runtime_defaults": [
                        {
                            "system": {
                                "system_id": "IBR600C-a38",
                                "users": {
                                    "0": {
                                        "_id_": "00000000-a0ab-3e74-bcbd-02af091f1c50",
                                        "username": "admin",
                                        "password": "$2$521ad9b6$93ZXtECvU0KUAxG3njqpafeNUZUel3zCssjc6CicXPo=",
                                        "group": "admin",
                                    }
                                },
                            },
                            "wlan": {
                                "radio": {
                                    "0": {
                                        "bss": {
                                            "0": {
                                                "ssid": "IBR600C-a38",
                                                "wpapsk": "WA203400365100",
                                                "radius0key": "secretkey",
                                            },
                                            "1": {
                                                "ssid": "Public-a38",
                                                "wpapsk": "WA203400365100",
                                                "radius0key": "secretkey",
                                            },
                                        }
                                    }
                                }
                            },
                        },
                        [],
                        {
                            "config": {
                                "nodes": {"dynamic": {"type": "struct", "nodes": {}}}
                            }
                        },
                    ],
                    "csdiff": [
                        {
                            "security": {
                                "zfw": {
                                    "filter_policies": {
                                        "0": {
                                            "rules": {
                                                "0": {
                                                    "priority": 10,
                                                    "name": "SSH",
                                                    "action": "allow",
                                                    "dst": {"port": [], "ip": []},
                                                    "src": {
                                                        "mac": [],
                                                        "port": [],
                                                        "ip": [],
                                                    },
                                                    "protocols": {
                                                        "0": {"identity": 6},
                                                        "1": {"identity": 17},
                                                    },
                                                    "ip_version": "ip4",
                                                }
                                            }
                                        },
                                        "2": {
                                            "name": "SSH",
                                            "default_action": "allow",
                                            "rules": {
                                                "0": {
                                                    "priority": 10,
                                                    "name": "SSH",
                                                    "action": "allow",
                                                    "dst": {"port": [], "ip": []},
                                                    "src": {
                                                        "mac": [],
                                                        "port": [],
                                                        "ip": [],
                                                    },
                                                    "protocols": {
                                                        "0": {"identity": 6},
                                                        "1": {"identity": 17},
                                                    },
                                                    "ip_version": "ip4",
                                                }
                                            },
                                            "_id_": "00000002-77db-3b20-980e-2de482869073",
                                        },
                                    }
                                }
                            },
                            "firewall": {"drop_invalid": False},
                            "wan": {
                                "rules2": {
                                    "0": {
                                        "ip_mode": "static",
                                        "static": {
                                            "dns": {
                                                "0": {"ip_address": "192.168.1.200"},
                                                "1": {"ip_address": "192.168.1.200"},
                                            },
                                            "ip_address": "192.168.1.1",
                                            "netmask": "255.255.255.0",
                                            "gateway": "192.168.1.200",
                                        },
                                    },
                                    "6": {
                                        "priority": 2.25,
                                        "trigger_name": "Modem-648bd63a",
                                        "trigger_string": "type|is|mdm%tech|is|lte/3g%uid|is|648bd63a",
                                        "_id_": "00000006-a81d-3590-93ca-8b1fcfeb8e14",
                                        "disabled": True,
                                    },
                                    "7": {
                                        "priority": 3.2502945955,
                                        "trigger_name": "WWAN-Company-Guest:2_4G-1",
                                        "trigger_string": "type|is|wwan%uid|is|Company-Guest:2_4G-1",
                                        "_id_": "00000007-a81d-3590-93ca-8b1fcfeb8e14",
                                    },
                                }
                            },
                            "system": {
                                "ui_activated": True,
                                "show_cloud_setup": False,
                                "logging": {"level": "debug"},
                                "users": {
                                    "0": {
                                        "password": "$2$6+F5uZzL$+WGT1RrPLwehh1Ls8N2yDXuh46p2n3BCN2wMcJ5EhDg="
                                    },
                                    "1": {
                                        "username": "cproot",
                                        "group": "admin",
                                        "password": "$2$5GJWH9gW$BRX+tgrnbNb8IulwlM5fvSKKi0ZvCVxgAyRm3NASAGo=",
                                        "_id_": "00000001-a0ab-3e74-bcbd-02af091f1c50",
                                    },
                                },
                                "admin": {"product_name": "IBR600C-150M-B-EU"},
                            },
                            "wwan": {
                                "radio": {
                                    "0": {
                                        "mode": "wwan",
                                        "profiles": {
                                            "0": {
                                                "active_scan": False,
                                                "roaming_enabled": False,
                                                "min_link_rssi": -70,
                                                "min_scan_rssi": -80,
                                                "bssid": None,
                                                "authmode": "wpa2psk",
                                                "enabled": True,
                                                "wpacipher": "aes",
                                                "ssid": "Company-Guest",
                                                "wpapsk": "rzQ753BQu7",
                                                "eapconf": {
                                                    "eaptype": "peap",
                                                    "phase1": "",
                                                    "phase2": "auth=MSCHAPV2",
                                                },
                                                "uid": "Company-Guest:2_4G-1",
                                            }
                                        },
                                    }
                                }
                            },
                        },
                        [],
                    ],
                }
            },
            "config": {"system": {"lldp": None}},
        },
    },
}

_TOKEN = {
    "client_id": _CLIENT_ID,
    "token_id": _TOKEN_ID,
    "token_secret": _TOKEN_SECRET,
}

# Client identifier (this is probably used to bind the token to a device)
try:
    _MYCLIENTID = _TOKEN["client_id"]
except:
    _MYCLIENTID = 0

# Credentials used for router registration
_CREDENTIALS2REG = {"username": _CID, "password": _CPW}
_CREDENTIALS = {"token_id": _TOKEN["token_id"], "token_secret": _TOKEN["token_secret"]}

# Timeout for the 'drain_events()' function
_CMD_TIMEOUT = 2

# Local IP address
_CLIENT_HOST = _MYIP_IF["addr"]

# Dummy router description which is sent during registration
_DESCR = {"mac": _MYMAC, "name": "", "product": "IBR600C-150M-B-EU"}

# NetCloud server
if _FULL_REGISTRATION or _AUTHORIZATION:
    if _COUNTRY_CODE_EU:
        _NETCLOUD_SERVER = "stream.eu4.cradlepointecm.com"
    else:
        _NETCLOUD_SERVER = "stream-shard.cradlepointecm.com"
else:
    _NETCLOUD_SERVER = "stream.cradlepointecm.com"

# NetCloud port
_NETCLOUD_SERVER_PORT = 8001

# Computes a SHA1 hash from a MAC address (code taken from the router's rootfs)
def hash_v2(value):
    min_loops = 10000
    max_loops = 40000
    loops = sum((ord(x) + 1 for x in value))
    i = 3
    while loops < min_loops or loops > max_loops:
        i += 1
        loops = (loops + i) ** 3 if loops < min_loops else loops % max_loops

    output = None
    for x in range(loops):
        output = hashlib.sha1((output if output else value).encode()).hexdigest()
    else:
        return output


if __name__ == "__main__":
    s = api.stream.StreamConnectionV1(
        host=_NETCLOUD_SERVER, port=(_NETCLOUD_SERVER_PORT), ecm_bind=(_CLIENT_HOST)
    )
    s.connect(ca_cert="stream.crt")

    secret = hash_v2(_MYMAC)
    print(secret)

    if _REGISTRATION_VIA_LOGIN_CREDS or _REGISTRATION_VIA_TOKEN:
        if _REGISTRATION_VIA_LOGIN_CREDS:
            cmd_id = (s.authorize)(**_CREDENTIALS2REG)
        else:
            cmd_id = (s.authorize)(**_CREDENTIALS)
        s.drain_events(maxevents=1, timeout=_CMD_TIMEOUT)
        act = s.get_response(cmd_id, timeout=0)
        s._authorized = True
        print(act)
        cmd_id = (s.register)(_DESCR)
        s.drain_events(maxevents=1, timeout=_CMD_TIMEOUT)
        act = s.get_response(cmd_id, timeout=0)
        s._authorized = True
        print(act)

    if _AUTHORIZATION:
        cmd_id = (s.authorize)(**_CREDENTIALS)
        s.drain_events(maxevents=1, timeout=_CMD_TIMEOUT)
        act = s.get_response(cmd_id, timeout=0)
        s._authorized = True
        print(act)

    if _INSECURE_ACTIVATION:
        secret = hash_v2(_MYMAC)
        cmd_id = s.execute_command("check_activation", dict(secrethash=secret))
        ccn = s.drain_events(maxevents=1, timeout=_CMD_TIMEOUT)
        print(ccn)
        act = s.get_response(cmd_id, timeout=0)
        print(act)

    if _FULL_REGISTRATION:
        print(_CREDENTIALS)
        cmd_id = (s.authorize)(**_CREDENTIALS)
        s.drain_events(maxevents=1, timeout=_CMD_TIMEOUT)
        act = s.get_response(cmd_id, timeout=0)
        s._authorized = True
        print(act)
        cmd_id = s.bind(client_id=_MYCLIENTID)
        s.drain_events(maxevents=1, timeout=_CMD_TIMEOUT)
        act = s.get_response(cmd_id, timeout=0)
        s._bound = True
        print(act)
        cmd_id = s.start_poll()
        s.drain_events(maxevents=1, timeout=_CMD_TIMEOUT)
        act = s.get_response(cmd_id, timeout=0)
        print(act)
        cmd_id = s.post(msg=_POSTDATA)
        s.drain_events(maxevents=1, timeout=_CMD_TIMEOUT)
        act = s.get_response(cmd_id, timeout=0)
        print(act)

    if _BINDONLY:
        cmd_id = (s.authorize)(**_CREDENTIALS2REG)
        s.drain_events(maxevents=1, timeout=_CMD_TIMEOUT)
        act = s.get_response(cmd_id, timeout=0)
        s._authorized = True
        print(act)
        cmd_id = s.bind(client_id=_MYCLIENTID)
        s.drain_events(maxevents=1, timeout=_CMD_TIMEOUT)
        act = s.get_response(cmd_id, timeout=0)
        s._bound = True
        print(act)

    s.close()
