import serial

ser = None


def initialize_port(port):
    global ser
    ser = serial.Serial(port, 38400, timeout=3, writeTimeout=3)


def send_command(command):
    # source
    command.insert(0, 81)
    # destination master
    command.insert(1, 0x01)
    #amount
    command.insert(2, len(command) + 2)
    #checksum
    command.append(checksum(command))

    #print("writing:{0}".format(str(to_hex(command))))
    ser.write(command)


def checksum(arr):
    counter = 0
    for item in arr:
        counter += item
    return counter % 256


def to_hex(intarray):
    return ''.join(["0x" + "%02X" % x + ", " for x in intarray])


received_bytes = []


def receive_data():
    global received_bytes

    res = ser.read(4)

    received_bytes = res

    if len(received_bytes) <= 3:
        print("did not receive any data while waiting")
        return False

    expected_amount = received_bytes[2]
    if expected_amount > 127 or expected_amount < 5:
        print("wrong amount of bytes:" + str(expected_amount))
        return False

    res = ser.read(expected_amount - 4)
    received_bytes += res

    if len(received_bytes) != expected_amount:
        print("incorrect amount expected: s% actual s%" %
              (str(expected_amount), str(len(received_bytes))))
        return False

    if received_bytes[len(received_bytes) - 1] != checksum(received_bytes[:-1]):
        print("incorrect checksum, got: {0} calculated: {1} ".format(
            str(received_bytes[-1]),
            str(checksum(received_bytes[:-1]))))
        return False

    return True
