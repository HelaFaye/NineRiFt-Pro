import time
from py9b.link.base import LinkTimeoutException
from py9b.transport.base import BaseTransport as BT
from py9b.command.regio import ReadRegs, WriteRegs
from py9b.command.mfg import *

from kivy.utils import platform
try:
    from kivymd.toast import toast
except:
    print('no toast for you')

# toast or print
def tprint(msg):
    try:
        toast(msg)
    except:
        print(msg)

def cprint(msg, cout):
    cout+=msg+''
    print(cout)

class Command:
    def __init__(self, conn, cout):
        self.new_sn = ''
        self.device = ''
        self.snmeth = ''
        self.conn = conn
        self.cout = cout

    def setdev(self, d):
        self.device = d.lower()
        tprint(self.device+' selected as device')

    def setnewsn(self, p):
        self.new_sn = p
        tprint(self.new_sn+' input for NewSN')

    def setsnmethod(self, m):
        self.snmeth = m
        tprint(self.snmeth+' selected for ChangeSN method')

    def cprint_reg(self, tran, desc, reg, format, dev=BT.ESC):
        try:
            data = tran.execute(ReadRegs(dev, reg, format))
            cprint(desc % data, self.cout)
        except Exception as exc:
            cprint(desc, repr(exc), self.cout)

    def dump(self, device):
        if device:
            dev = {
                'esc': BT.ESC,
                'ble': BT.BLE,
                'bms': BT.BMS,
                'extbms': BT.EXTBMS,
            }[device]
        else:
            tprint('select device first')

        with self.conn._tran as tran:
            for offset in range(256):
                try:
                    cprint('0x%02x: %04x' % (offset, tran.execute(ReadRegs(dev, offset, "<H"))[0]), self.cout)
                except Exception as exc:
                    cprint('0x%02x: %s' % (offset, exc), self.cout)

    def sniff(self):
        tran = self.conn._tran
        while True:
            try:
                tprint(tran.recv())
            except LinkTimeoutException as exc:
                pass
            except Exception as exc:
                tprint(exc)

    def powerdown(self):
        tran = self.conn._tran
        tran.execute(WriteRegs(BT.ESC, 0x79, "<H", 0x0001))
        tprint('Done')

    def lock(self):
        tran = self.conn._tran
        tran.execute(WriteRegs(BT.ESC, 0x70, "<H", 0x0001))
        tprint('Done')

    def unlock(self):
        tran = self.conn._tran
        tran.execute(WriteRegs(BT.ESC, 0x71, "<H", 0x0001))
        tprint('Done')

    def reboot(self):
        tran = self.conn._tran
        tran.execute(WriteRegs(BT.ESC, 0x78, "<H", 0x0001))
        tprint('Done')

    def bms_info(self, tran, dev):
        cprint('BMS S/N:         %s' % tran.execute(ReadRegs(dev, 0x10, "14s"))[0].decode(), self.cout)
        tprint('BMS S/N:         %s' % tran.execute(ReadRegs(dev, 0x10, "14s"))[0].decode())
        cprint_reg(tran, 'BMS Version:     %04x', 0x17, "<H", dev=dev)
        cprint_reg(tran, 'BMS charge:      %d%%', 0x32, "<H", dev=dev)
        cprint_reg(tran, 'BMS full cycles: %d', 0x1b, "<H", dev=dev)
        cprint_reg(tran, 'BMS charges:     %d', 0x1c, "<H", dev=dev)
        cprint_reg(tran, 'BMS health:      %d%%', 0x3b, "<H", dev=dev)
        cprint('BMS current:     %.2fA' % (tran.execute(ReadRegs(dev, 0x33, "<h"))[0] / 100.0,), self.cout)
        cprint('BMS voltage:     %.2fV' % (tran.execute(ReadRegs(dev, 0x34, "<h"))[0] / 100.0,), self.cout)

    def info(self):
        tran = self.conn._tran
        cprint('ESC S/N:       %s' % tran.execute(ReadRegs(BT.ESC, 0x10, "14s"))[0].decode(), self.cout)
        tprint('ESC S/N:       %s' % tran.execute(ReadRegs(BT.ESC, 0x10, "14s"))[0].decode())
        cprint('ESC PIN:       %s' % tran.execute(ReadRegs(BT.ESC, 0x17, "6s"))[0].decode(), self.cout)
        cprint_reg(tran, 'BLE Version:   %04x', 0x68, "<H")
        cprint_reg(tran, 'ESC Version:   %04x', 0x1A, "<H")
        cprint_reg(tran, 'Error code:    %d', 0x1B, "<H")
        cprint_reg(tran, 'Warning code:  %d', 0x1C, "<H")
        cprint('Total mileage: %s' % pp_distance(tran.execute(ReadRegs(BT.ESC, 0x29, "<L"))[0]), self.cout)
        cprint('Total runtime: %s' % pp_time(tran.execute(ReadRegs(BT.ESC, 0x32, "<L"))[0]), self.cout)
        cprint('Total riding:  %s' % pp_time(tran.execute(ReadRegs(BT.ESC, 0x34, "<L"))[0]), self.cout)
        cprint('Chassis temp:  %d C' % (tran.execute(ReadRegs(BT.ESC, 0x3e, "<H"))[0] / 10.0,), self.cout)

        try:
            cprint(' *** Internal BMS ***', self.cout)
            bms_info(tran, BT.BMS)
        except Exception as exc:
            cprint('No internal BMS found', repr(exc), self.cout)

        try:
            cprint(' *** External BMS ***', self.cout)
            bms_info(tran, BT.EXTBMS)
        except Exception as exc:
            cprint('No external BMS found', repr(exc), self.cout)

    def changesn(self, new_sn):

        tran = self.conn._tran
        old_sn = tran.execute(ReadRegs(BT.ESC, 0x10, "14s"))[0].decode()

        if self.snmeth is 'dauth':
            if self.device is not '':
                dev = {
                    'esc': BT.ESC,
                    'ble': BT.BLE,
                    'bms': BT.BMS,
                    'extbms': BT.EXTBMS,
                }[self.device]
            else:
                tprint('pick a device first')
            uid3 = tran.execute(ReadRegs(dev, 0xDE, "<L"))[0]
            cprint("UID3: %08X" % (uid3), self.cout)

            auth = CalcSnAuth(old_sn, new_sn, uid3)
            # auth = 0
            cprint("Auth: %08X" % (auth), self.cout)
            try:
                # Write NewSN to device using DAuth Method
                tran.execute(WriteSNAuth(dev, new_sn.encode('utf-8'), auth))
                tprint("OK")
            except LinkTimeoutException:
                tprint("Timeout !")

        if self.snmeth is 'wregs':
            try:
                # Write NewSN to ESC using Regs Method
                tran.execute(WriteRegs(BT.ESC, 0x10, "<14sL", new_sn.encode('utf-8')))
                tprint("OK")
            except LinkTimeoutException:
                tprint("Timeout !")

        # save config and restart
        tran.execute(WriteRegs(BT.ESC, 0x78, "<H", 0x01))
        time.sleep(3)

        self.old_sn = tran.execute(ReadRegs(BT.ESC, 0x10, "14s"))[0]
        if self.old_sn is new_sn:
            tprint('SN Change Successful')
        elif self.snmeth is 'regs':
            tprint('Did you flash DRV777 first?')
        elif self.snmeth is 'dauth':
            tprint("Do you know what you're doing?")

    def pp_distance(dist):
        if dist < 1000:
            return '%dm' % dist
        return '%dkm %dm' % (dist / 1000.0, dist % 1000)

    def pp_time(seconds):
        periods = [
            ('year',        60*60*24*365),
            ('month',       60*60*24*30),
            ('day',         60*60*24),
            ('hour',        60*60),
            ('minute',      60),
            ('second',      1)
        ]

        strings = []
        for period_name, period_seconds in periods:
            if seconds > period_seconds:
                period_value, seconds = divmod(seconds, period_seconds)
                has_s = 's' if period_value > 1 else ''
                strings.append("%2s %s%s" % (period_value, period_name, has_s))

        return " ".join(strings)
