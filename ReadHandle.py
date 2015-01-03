from enum import Enum
from McuCommand import *
import struct


class St(Enum):
    Read1 = 0
    Wait1 = 1
    Read2 = 2
    Wait2 = 3
    Fail = 4
    Finish = 5


class Tr(Enum):
    Read = 0
    Received = 1
    TimeOut = 2
    Stop = 3,


class ReadFSM(object):
    transitions = {
        (St.Read1, Tr.Read): St.Wait1,
        (St.Wait1, Tr.TimeOut): St.Read2,
        (St.Wait1, Tr.Received): St.Finish,
        (St.Read2, Tr.Read): St.Wait2,
        (St.Wait2, Tr.TimeOut): St.Fail,
        (St.Wait2, Tr.Received): St.Finish,
        (St.Fail, Tr.Stop): St.Finish,
    }

    def perform_read(self):
        print("read offset: {0}".format(self.offSet))
        command = [0x10, 0x06]
        address = [x for x in struct.pack('i', self.offSet)[::-1]]
        self.comm.send_command(command + address)

    def do(self, transition):
        key = (self.currentState, transition)
        if key in self.transitions:
            self.currentState = self.transitions[key]
        else:
            print("transition {0} not found for state {1}"
                  .format(str(transition), str(self.currentState)))

    def read1_state(self):
        print("read1")
        self.perform_read()
        self.do(Tr.Read)

    def wait1_state(self):
        print("WaitRead1")
        if self.comm.receive_data():
            self.time_out = False
            self.do(Tr.Received)
        else:
            self.do(Tr.TimeOut)

    def wait2_state(self):
        print("ReadWait2")
        if self.comm.receive_data():
            self.time_out = False
            self.do(Tr.Received)
        else:
            self.do(Tr.TimeOut)

    def read2_state(self):
        print("Read2")
        self.perform_read()
        self.do(Tr.Read)

    def fail_state(self):
        print("ReadFail")
        self.time_out = True
        print("failed 2x")
        self.do(Tr.Stop)

    states = {
        St.Read1: read1_state,
        St.Read2: read2_state,
        St.Wait1: wait1_state,
        St.Wait2: wait2_state,
        St.Fail: fail_state,
    }

    def __init__(self, comm, offset):
        self.time_out = True
        self.offSet = offset
        self.currentState = St.Read1
        self.comm = comm
        self.receivedData = []

    def next(self):
        self.states[self.currentState](self)

    def run(self):
        while self.currentState != St.Finish:
            self.next()
        if not self.time_out:
            self.receivedData = list(self.comm.received_bytes)
