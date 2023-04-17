import logging, json, struct, zlib

from mitmproxy.utils import strutils
from mitmproxy import tcp


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

    try:
        message_decoded = transcoder.decode(message.content[transcoder.header_size :])
        logging.info(
            f"tcp_message[from_client={message.from_client}), content={message_decoded}]"
        )
    except:
        logging.info(
            f"tcp_message[from_client={message.from_client}), content={strutils.bytes_to_escaped_str(message.content)}]"
        )
