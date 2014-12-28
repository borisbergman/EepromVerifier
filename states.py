from enum import Enum
from McuCommand import *
import sys
import struct


class St(Enum):
    Initiate = 0
    AwaitInstall = 1
    AwaitPw = 2
    Run = 3
    Run2 = 4
    Wait = 5
    Wait2 = 6
    Finish = 7


class Tr(Enum):
    SendInstall = 0
    TimeOut = 1
    SendPw = 2
    PasswordOk = 3
    QueueEmpty = 4
    Send = 5
    Received = 6


class State(object):
    def execute(self):
        pass


class FinishState(State):
    def execute(self):
        print('FinishState')
        sys.exit(0)


class InitiateState(State):
    def execute(self):
        print('initiate state')
        enter_installation()
        sm.do(Tr.SendInstall)


class Wait2State(State):
    def execute(self):
        pass


class Run2State(State):
    def execute(self):
        print("run2State")
        send_eeprom()
        sm.do(Tr.Send)


class WaitInstallState(State):
    def execute(self):
        print('waitInstall')
        if receive_data():
            send_password()
            sm.do(Tr.SendPw)
        else:
            sm.do(Tr.TimeOut)


class AwaitPWState(State):
    def execute(self):
        print("awPassword")
        if receive_data():
            sm.do(Tr.PasswordOk)
        else:
            sm.do(Tr.TimeOut)


class RunState(State):
    def execute(self):
        print("RunState")
        reset_timer()
        if send_eeprom():
            sm.do(Tr.Send)
        else:
            print("done")
            sm.do(Tr.QueueEmpty)


class WaitState(State):
    def execute(self):
        print("WaitState")
        reset_timer()
        if receive_data():
            sm.do(Tr.Received)
        else:
            print("wrong data")
            sm.do(Tr.TimeOut)


class Send2State(State):
    def execute(self):
        print("Send2State")
        reset_timer()
        send_eeprom()


class Wait2State(State):
    def execute(self):
        print("Wait2State")
        reset_timer()
        if receive_data():
            sm.do(Tr.Received)
        else:
            print("wrong data 2")
            sm.do(Tr.TimeOut)
        print("Wait2")


class StateMachine(object):
    transitions = {
        (St.Initiate, Tr.SendInstall): St.AwaitInstall,
        (St.AwaitInstall, Tr.TimeOut): St.Finish,
        (St.AwaitInstall, Tr.SendPw): St.AwaitPw,
        (St.AwaitPw, Tr.TimeOut): St.Finish,
        (St.AwaitPw, Tr.PasswordOk): St.Run,
        (St.Run, Tr.Send): St.Wait,
        (St.Run, Tr.QueueEmpty): St.Finish,
        (St.Wait, Tr.Received): St.Run,
        (St.Wait, Tr.TimeOut): St.Run2,
        (St.Run2, Tr.Send): St.Wait2,
        (St.Run2, Tr.TimeOut): St.Finish,
        (St.Wait2, Tr.Received): St.Run,
        (St.Wait2, Tr.TimeOut): St.Finish,
    }

    states = {
        St.Initiate: InitiateState(),
        St.AwaitInstall: WaitInstallState(),
        St.AwaitPw: AwaitPWState(),
        St.Run: RunState(),
        St.Wait: WaitState(),
        St.Run2: Run2State(),
        St.Wait2: Wait2State(),
        St.Finish: FinishState(),
    }

    def __init__(self):
        self.currentState = St.Initiate

    def do(self, transition):
        key = (self.currentState, transition)
        if key in self.transitions:
            self.currentState = self.transitions[key]
        else:
            print("transition {0} not found for state {1}"
                  .format(str(transition), str(self.currentState)))
    def next(self):
        self.states[self.currentState].execute()


sm = StateMachine()


def enter_installation():
    x = input("StartOnSerialPort")
    initialize_port(int(x))
    command = [0x1B, 0x01]
    send_command(command)


def send_password():
    command = [0x14, 0x01, 0x35, 0x37, 0x39, 0x41, 0x43, 0x45]
    send_command(command)


times = 0
packet_size = 64


def send_eeprom():
    global times

    if times * packet_size >= 2 ** 17:
        return False
    print("write offset: {offset:}".format(str(times * packet_size)))
    command = [0x10, 0x0E]
    address = [x for x in struct.pack('i', times * packet_size)[::-1]]
    data = [0x83 for x in range(packet_size)]
    send_command(command + address + data)
    times += 1
    return True


def reset_timer():
    pass


def time_out():
    received_bytes.clear()
    sm.do(Tr.TimeOut)


while True:
    sm.next()