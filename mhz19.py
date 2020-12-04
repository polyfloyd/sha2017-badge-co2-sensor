from machine import UART
from time import sleep


class MHZ19ChecksumError(Exception):
    def __init__(self):
        super().__init__('mhz19: checksum error')

class MHZ19:
    def __init__(self, rx_pin: int, tx_pin: int):
        self.uart = UART(2, baudrate=9600, rx=rx_pin, tx=tx_pin, timeout=100)

    def close(self):
        try:
            self.uart.deinit()
        except:
            pass

    def _cmd(self, cmd: int, cmd_data: bytes, resp_len: int):
        req_bytes = bytearray([
            0xff, # Fixed start byte.
            1,    # Sensor num.
            cmd,
        ])
        req_bytes += cmd_data
        req_bytes += bytes([0] * (8 - len(req_bytes)))
        req_bytes += bytes([MHZ19._checksum(req_bytes[1:])])
        assert len(req_bytes) == 9

        bytes_written = self.uart.write(req_bytes)
        assert bytes_written is not None
        if resp_len == 0:
            return

        resp_bytes = self.uart.read(resp_len)
        if len(resp_bytes) != resp_len:
            raise Exception('mhz19: not enough bytes received: %d' % len(resp_bytes))
        if resp_bytes[-1] != MHZ19._checksum(resp_bytes[1:-1]):
            raise MHZ19ChecksumError()
        return resp_bytes[2:]

    def gas_concentration(self) -> int:
        resp = self._cmd(0x86, bytes(), 9)
        return resp[0]<<8 | resp[1]

    @staticmethod
    def _checksum(data: bytes) -> int:
        return ((0xff - sum(data) & 0xff) + 1) & 0xff

assert MHZ19._checksum(b'\x01\x86\x00\x00\x00\x00\x00') == 0x79
assert MHZ19._checksum(b'\x86\x01\x9a<\x00\x00\x00') == 0xa3
