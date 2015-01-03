import serial




def checksum(arr):
    counter = 0
    for item in arr:
        counter += item
    return counter % 256


def to_hex(intarray):
    return ''.join(["0x" + "%02X" % x + ", " for x in intarray])


class Comm(object):
    received_bytes = []

    def __init__(self, port=10, timeout=4):
        self.timeout = timeout
        self.unitId = 0
        try:
            self.ser = serial.Serial(port, 38400, timeout=timeout, writeTimeout=timeout)
        except serial.SerialException:
            raise Exception("could not initialize port")

    def send_command(self, command):
        # source
        command.insert(0, 0x81)
        # destination last packet received from
        command.insert(1, self.unitId)
        #amount
        command.insert(2, len(command) + 2)

        #print("writing:{0}".format(str(to_hex(command))))
        try:
            self.ser.write(command + [checksum(command)])
            return True
        except serial.SerialException:
            print("timeout after {0}s".format(str(self.timeout)))
            return False
        #except serial.SerialTimeoutException:
        #    print("timeout after {0}s".format(str(self.timeout)))
        #    return False

    def receive_data(self):
        res = self.ser.read(4)

        self.received_bytes = res

        if len(self.received_bytes) <= 3:
            print("did not receive any data while waiting")
            return False

        expected_amount = self.received_bytes[2]
        if expected_amount > 127 or expected_amount < 5:
            print("wrong amount of bytes:" + str(expected_amount))
            return False

        res = self.ser.read(expected_amount - 4)
        self.received_bytes += res

        if len(self.received_bytes) != expected_amount:
            print("incorrect amount expected: %s actual %s" %
                  (str(expected_amount), str(len(self.received_bytes))))
            return False

        if self.received_bytes[-1] != checksum(self.received_bytes[:-1]):
            print("incorrect checksum, got: {0} calculated: {1} ".format(
                str(self.received_bytes[-1]),
                str(checksum(self.received_bytes[:-1]))))
            return False

        self.unitId = self.received_bytes[0]
        #print("received set {0}", to_hex(self.received_bytes))
        return True
