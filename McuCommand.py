import serial
import logging
import struct


def checksum(arr):
    counter = 0
    for item in arr:
        counter += item
    return counter % 256


def to_hex(intarray):
    return ''.join(["0x" + "%02X" % x + ", " for x in intarray])


class Comm(object):
    received_bytes = []

    def __init__(self, port=10, timeout=10):
        self.timeout = timeout
        self.unitId = 0
        try:
            self.ser = serial.Serial(port, 38400, timeout=timeout, writeTimeout=timeout)
        except serial.SerialException:
            raise Exception("could not initialize port")

    def send_command(self, command):
        self.flush_data()
        # source
        command.insert(0, 0x81)
        # destination last packet received from
        command.insert(1, self.unitId)
        # amount
        command.insert(2, len(command) + 2)

        y = command + [checksum(command)]
        try:
            self.ser.write(y)
            return True
        except serial.SerialException:
            logging.info("timeout after {0}s".format(str(self.timeout)))
            return False
        finally:
            logging.info("command {0}".format(str(to_hex(y))))

    def flush_data(self):
        self.ser.flushOutput()
        self.ser.flushInput()

    def receive_bytes(self, amount):
        rec = []
        while True:
            rec += self.ser.read(1)
            if b'':
                break
            if len(rec) >= amount:
                break
        self.received_bytes += rec
        #self.received_bytes += [struct.unpack('B', x)[0] for x in rec]

    def receive_data(self):
        self.received_bytes.clear()
        self.receive_bytes(4)
        if len(self.received_bytes) <= 3:
            logging.info("did not receive any data while waiting")
            return False

        expected_amount = self.received_bytes[2]
        if expected_amount > 127 or expected_amount < 5:
            logging.info("wrong amount of bytes:" + str(expected_amount))
            return False

        self.receive_bytes(expected_amount - 4)

        if len(self.received_bytes) != expected_amount:
            logging.info("incorrect amount expected: %s actual %s" %
                         (str(expected_amount), str(len(self.received_bytes))))
            return False

        if self.received_bytes[-1] != checksum(self.received_bytes[:-1]):
            logging.info("incorrect checksum, got: {0} calculated: {1} ".format(
                str(self.received_bytes[-1]),
                str(checksum(self.received_bytes[:-1]))))
            return False

        self.unitId = self.received_bytes[0]
        # logging.info("received set {0}", to_hex(self.received_bytes))
        return True

