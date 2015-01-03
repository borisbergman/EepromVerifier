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

    def __init__(self, port):
        self.ser = serial.Serial(port, 38400, timeout=10, writeTimeout=10)

    def send_command(self, command):
        # source
        command.insert(0, 0x81)
        # destination master
        command.insert(1, 0x01)
        #amount
        command.insert(2, len(command) + 2)
        #checksum
        command.append(checksum(command))

        #print("writing:{0}".format(str(to_hex(command))))
        self.ser.write(command)

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
            print("incorrect amount expected: s%s actual s%s" %
                  (str(expected_amount), str(len(self.received_bytes))))
            return False

        if self.received_bytes[-1] != checksum(self.received_bytes[:-1]):
            print("incorrect checksum, got: {0} calculated: {1} ".format(
                str(self.received_bytes[-1]),
                str(checksum(self.received_bytes[:-1]))))
            return False

        return True
