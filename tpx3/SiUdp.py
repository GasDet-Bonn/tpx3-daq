#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#
# A transfer layer for SUdp Ethernet.
#

from __future__ import absolute_import
import logging
import socket
import struct
from array import array
from threading import RLock as Lock

from basil.TL.SiTransferLayer import SiTransferLayer

logger = logging.getLogger(__name__)


class SiUdp(SiTransferLayer):
    '''SiUdp transport layer.
    '''

    VERSION = 0x01  # TODO

    CMD_WR = 0x02
    CMD_RD = 0x01

    MAX_RD_SIZE = 1 * 1472 #32 * 1476 was making some problesm maybe 31? TODO: change packege on FPGA to 1472?
    MAX_WR_SIZE = 1024

    UDP_TIMEOUT = 1.0
    UDP_RETRANSMIT_CNT = 0  # TODO

    def __init__(self, conf):
        super(SiUdp, self).__init__(conf)
        self._sock_udp = None
        self._udp_lock = Lock()

    def init(self):
        super(SiUdp, self).init()
        self._sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock_udp.settimeout(self.UDP_TIMEOUT)

    def _write_single(self, addr, data):

        request = array('B', struct.pack('>BII', self.CMD_WR, len(data), addr))
        request += data

        self._sock_udp.sendto(request, (self._init['host'], self._init['port']))

        try:
            ack = self._sock_udp.recv(4)
        except socket.timeout:
            raise IOError('SiUdp:_write_single - Timeout')

        if len(ack) != 4:
            raise IOError('SiUdp:_write_single - Packet is wrong size %d %d' % (len(ack), ack))

        if struct.unpack('>I', ack)[0] != len(data):
            raise IOError('SiUdp:_write_single - Data error %d %d' % (len(data), struct.unpack('>I', ack)[0]))

    def write(self, addr, data):

        def chunks(array, max_len):
            index = 0
            while index < len(array):
                yield array[index: index + max_len]
                index += max_len

        buff = array('B', data)
        with self._udp_lock:
            new_addr = addr
            for req in chunks(buff, self.MAX_WR_SIZE):
                self._write_single(new_addr, req)
                new_addr += len(req)

    def _read_single(self, addr, size):
        request = array('B', struct.pack('>BII', self.CMD_RD, size, addr))
        self._sock_udp.sendto(request, (self._init['host'], self._init['port']))

        ack = ''
        try:
            while len(ack) != size:
                ack += self._sock_udp.recv(size)
        except socket.timeout:
            raise IOError('SiUdp:read_single - Timeout %d %d' % (len(ack), size))

        if len(ack) != size:
            raise IOError('SiUdp:read_single - Wrong packet size %d %d' % (len(ack), size))

        return array('B', ack)

    def read(self, addr, size):

        ret = array('B')

        if size > 0:
            with self._udp_lock:
                if size > self.MAX_RD_SIZE:
                    new_addr = addr
                    next_size = self.MAX_RD_SIZE
                    while next_size < size:
                        ret += self._read_single(new_addr, self.MAX_RD_SIZE)
                        new_addr = addr + next_size
                        next_size = next_size + self.MAX_RD_SIZE
                    ret += self._read_single(new_addr, size + self.MAX_RD_SIZE - next_size)
                else:
                    ret += self._read_single(addr, size)
        return ret

    def close(self):
        super(SiUdp, self).close()
        self._sock_udp.close()
