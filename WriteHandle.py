from enum import Enum
from McuCommand import *
import struct
import logging

PacketSize = 64


class St(Enum):
    Write1 = 0
    Wait1 = 1
    Write2 = 2
    Wait2 = 3
    Fail = 4
    Finish = 5


class Tr(Enum):
    Read = 0
    Received = 1
    TimeOut = 2
    Stop = 3,


class WriteFSM(object):
    def check_feedback(self):
        if [x for x in self.comm.received_bytes[3:5]] != [0x12, 0x01]:
            logging.info("unexpected feedback: {0}".format(str(to_hex(self.comm.received_bytes))))
            return False
        return True

    transitions = {
        (St.Write1, Tr.Read): St.Wait1,
        (St.Write1, Tr.TimeOut): St.Write2,
        (St.Wait1, Tr.TimeOut): St.Write2,
        (St.Wait1, Tr.Received): St.Finish,
        (St.Write2, Tr.Read): St.Wait2,
        (St.Write2, Tr.TimeOut): St.Finish,
        (St.Wait2, Tr.TimeOut): St.Fail,
        (St.Wait2, Tr.Received): St.Finish,
        (St.Fail, Tr.Stop): St.Finish,
    }

    def perform_write(self):
        logging.info("write offset: {0}".format(self.offSet))
        command = [0x10, 0x0E]
        address = [x for x in struct.pack('i', self.offSet)[::-1]]
        return self.comm.send_command(command + address + self.data)

    def do(self, transition):
        key = (self.currentState, transition)
        if key in self.transitions:
            self.currentState = self.transitions[key]
        else:
            logging.info("transition {0} not found for state {1}"
                  .format(str(transition), str(self.currentState)))

    def write1_state(self):
        logging.info("Write 1")
        if self.perform_write():
            self.do(Tr.Read)
        else:
            self.time_out = True
            self.do(Tr.TimeOut)

    def write2_state(self):
        logging.info("Write 2")
        if self.perform_write():
            self.do(Tr.Read)
        else:
            self.time_out = True
            self.do(Tr.TimeOut)

    def wait1_state(self):
        logging.info("Wait Write 1")
        if self.comm.receive_data() and self.check_feedback():
            self.time_out = False
            self.do(Tr.Received)
        else:            
            self.do(Tr.TimeOut)

    def wait2_state(self):
        logging.info("Wait Write 2")
        if self.comm.receive_data() and self.check_feedback():
            self.time_out = False
            self.do(Tr.Received)            
        else:
            self.do(Tr.TimeOut)

    def fail_state(self):
        logging.info("Write Fail")
        self.time_out = True
        self.do(Tr.Stop)

    states = {
        St.Write1: write1_state,
        St.Write2: write2_state,
        St.Wait1: wait1_state,
        St.Wait2: wait2_state,
        St.Fail: fail_state,
    }


    def __init__(self, comm, offset, data):
        self.time_out = True
        self.offSet = offset
        self.currentState = St.Write1
        self.comm = comm
        self.data = data

    def next(self):
        self.states[self.currentState](self)

    def run(self):
        while self.currentState != St.Finish:
            self.next()
