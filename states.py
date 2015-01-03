from enum import Enum
from McuCommand import *
from ReadHandle import ReadFSM
from WriteHandle import WriteFSM
from WriteHandle import PacketSize
import logging

import sys
import struct
import time

FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)

d = {'clientip': '192.168.0.1', 'user': 'fbloggs'}
logger = logging.getLogger('tcpserver')
logger.warning('Protocol problem: %s', 'connection reset', extra=d)


class St(Enum):
    Initial = 0
    InstallMode = 1
    PasswordMode = 2
    Read = 3
    Run = 4
    Written = 5
    Verified = 6

    WriteOriginal = 8
    Finish = 9


class Tr(Enum):
    SendInstall = 0
    SendPassword = 1
    TimeOut = 2
    Read = 3
    Write = 4
    QueueEmpty = 5
    VerifyFail = 6


class VerifyFSM(object):
    packet_size = 64

    def __init__(self):
        self.times = 0
        self.currentState = St.Initial
        self.readData = []
        self.com = None

    transitions = {
        (St.Initial, Tr.SendInstall): St.InstallMode,
        (St.Initial, Tr.TimeOut): St.Finish,
        (St.InstallMode, Tr.SendPassword): St.PasswordMode,
        (St.InstallMode, Tr.TimeOut): St.Finish,
        (St.PasswordMode, Tr.TimeOut): St.Finish,
        (St.PasswordMode, Tr.Read): St.Run,
        (St.Run, Tr.Read): St.Read,
        (St.Run, Tr.QueueEmpty): St.Finish,
        (St.Read, Tr.TimeOut): St.Finish,
        (St.Read, Tr.Write): St.Written,
        (St.Written, Tr.Read): St.Verified,
        (St.Written, Tr.TimeOut): St.Finish,
        (St.Written, Tr.VerifyFail): St.Finish,
        (St.Verified, Tr.TimeOut): St.Finish,
        (St.Verified, Tr.Write): St.Run,
        (St.Verified, Tr.TimeOut): St.Finish,

    }

    def do(self, transition):
        key = (self.currentState, transition)
        if key in self.transitions:
            self.currentState = self.transitions[key]
        else:
            print("transition {0} not found for state {1}"
                  .format(str(transition), str(self.currentState)))

    def enter_installation(self):
        command = [0x1B, 0x01]
        return self.com.send_command(command)

    def send_password(self):
        command = [0x14, 0x01, 0x35, 0x37, 0x39, 0x41, 0x43, 0x45]
        return self.com.send_command(command)

    def finish_state(self):
        print('FinishState')
        sys.exit(0)

    def initialize_state(self):
        print('initiate state')
        x = 0
        while x < 1:
            try:
                inp = input("StartOnSerialPort")
                x = int(inp) - 1
            except ValueError:
                print("please enter a port number")
        try:
            self.com = Comm(x)
        except Exception as error:
            print(error)
            self.do(Tr.TimeOut)
            return
        if self.enter_installation():
            self.do(Tr.SendInstall)
        else:
            self.do(Tr.TimeOut)

    def install_mode_state(self):
        print('install_mode')
        if self.com.receive_data():
            time.sleep(5)
            if self.send_password():
                self.do(Tr.SendPassword)
            else:
                self.do(Tr.TimeOut)
        else:
            print("install mode fail")
            self.do(Tr.TimeOut)

    def password_mode_state(self):
        print("password_mode")
        if self.com.receive_data():
            self.do(Tr.Read)
        else:
            print("password fail")
            self.do(Tr.TimeOut)

    def run_state(self):
        print("run")
        if self.times * PacketSize >= 2 ** 17:
            print("test succeed")
            self.do(Tr.QueueEmpty)
            return
        read = ReadFSM(self.com, self.times * PacketSize)
        read.run()
        if read.time_out:
            print("Timed out offset {0}".format(str(self.times * PacketSize)))
            self.do(Tr.TimeOut)
        else:
            self.readData = read.receivedData
            self.do(Tr.Read)

    def read_state(self):
        print("read")
        data = [0x83 for x in range(PacketSize)]
        write = WriteFSM(self.com, self.times * PacketSize, data)
        write.run()
        if write.time_out:
            print("Timed out offset {0}".format(str(self.times * PacketSize)))
            self.do(Tr.TimeOut)
        else:
            self.do(Tr.Write)

    def written_state(self):
        print("written")
        read = ReadFSM(self.com, self.times * PacketSize)
        data = [0x83 for x in range(PacketSize)]
        read.run()
        if read.time_out:
            self.do(Tr.TimeOut)
        else:
            # verify
            if data == read.receivedData[5:-1]:
                self.do(Tr.Read)
            else:
                print("Data offset: {0} received: {1}".format(
                    str(self.times * PacketSize),
                    str(to_hex(read.receivedData[5:-1]))))
                self.do(Tr.VerifyFail)

    def verified_state(self):
        print("verified")
        # write back original
        write = WriteFSM(self.com, self.times * PacketSize, self.readData)
        write.run()
        if write.time_out:
            print("Timed out offset {0}".format(str(self.times * PacketSize)))
            self.do(Tr.TimeOut)
        else:
            self.do(Tr.Write)
        self.times += 1

    states = {
        St.Initial: initialize_state,
        St.InstallMode: install_mode_state,
        St.PasswordMode: password_mode_state,
        St.Run: run_state,
        St.Read: read_state,
        St.Written: written_state,
        St.Verified: verified_state,
        St.Finish: finish_state,
    }

    def next(self):
        self.states[self.currentState](self)

    def run(self):
        while self.currentState != St.Finish:
            self.next()


sm = VerifyFSM()
sm.run()