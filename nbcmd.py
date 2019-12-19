import time
from py9b.link.base import LinkTimeoutException
from py9b.transport.base import BaseTransport as BT
from py9b.command.regio import ReadRegs, WriteRegs

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


class Command:
    def __init__(self, conn):
        self.new_sn = ''
        self.device = ''
        self.conn = conn
        self.old_sn = ''

    def setdev(self, d):
        self.device = d.lower()
        tprint(self.device+' selected as device')

    def setnewsn(self, p):
        self.new_sn = p
        tprint(self.new_sn+' input for newsn')

    def dump(self, device):
        dev = {
            'esc': BT.ESC,
            'ble': BT.BLE,
            'bms': BT.BMS,
            'extbms': BT.EXTBMS,
        }[device]
        with self.conn._tran as tran:
            for offset in range(256):
                try:
                    tprint('0x%02x: %04x' % (offset, tran.execute(ReadRegs(dev, offset, "<H"))[0]))
                except Exception as exc:
                    tprint('0x%02x: %s' % (offset, exc))

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

    def print_reg(self, tran, desc, reg, format, dev=BT.ESC):
        try:
            data = tran.execute(ReadRegs(dev, reg, format))
            tprint(desc % data)
        except Exception as exc:
            tprint(desc, repr(exc))

    def bms_info(self, tran, dev):
        tprint('BMS S/N:         %s' % tran.execute(ReadRegs(dev, 0x10, "14s"))[0].decode())
        print_reg(tran, 'BMS Version:     %04x', 0x17, "<H", dev=dev)
        print_reg(tran, 'BMS charge:      %d%%', 0x32, "<H", dev=dev)
        print_reg(tran, 'BMS full cycles: %d', 0x1b, "<H", dev=dev)
        print_reg(tran, 'BMS charges:     %d', 0x1c, "<H", dev=dev)
        print_reg(tran, 'BMS health:      %d%%', 0x3b, "<H", dev=dev)
        tprint('BMS current:     %.2fA' % (tran.execute(ReadRegs(dev, 0x33, "<h"))[0] / 100.0,))
        tprint('BMS voltage:     %.2fV' % (tran.execute(ReadRegs(dev, 0x34, "<h"))[0] / 100.0,))

    def info(self):
        tran = self.conn._tran
        tprint('ESC S/N:       %s' % tran.execute(ReadRegs(BT.ESC, 0x10, "14s"))[0].decode())
        tprint('ESC PIN:       %s' % tran.execute(ReadRegs(BT.ESC, 0x17, "6s"))[0].decode())
        tprint('')
        print_reg(tran, 'BLE Version:   %04x', 0x68, "<H")
        print_reg(tran, 'ESC Version:   %04x', 0x1A, "<H")
        tprint('')
        print_reg(tran, 'Error code:    %d', 0x1B, "<H")
        print_reg(tran, 'Warning code:  %d', 0x1C, "<H")
        tprint('')
        tprint('Total mileage: %s' % pp_distance(tran.execute(ReadRegs(BT.ESC, 0x29, "<L"))[0]))
        tprint('Total runtime: %s' % pp_time(tran.execute(ReadRegs(BT.ESC, 0x32, "<L"))[0]))
        tprint('Total riding:  %s' % pp_time(tran.execute(ReadRegs(BT.ESC, 0x34, "<L"))[0]))
        tprint('Chassis temp:  %d C' % (tran.execute(ReadRegs(BT.ESC, 0x3e, "<H"))[0] / 10.0,))
        tprint('')

        try:
            tprint(' *** Internal BMS ***')
            bms_info(tran, BT.BMS)
        except Exception as exc:
            tprint('No internal BMS found', repr(exc))

        tprint('')

        try:
            tprint(' *** External BMS ***')
            bms_info(tran, BT.EXTBMS)
        except Exception as exc:
            tprint('No external BMS found', repr(exc))

    def changesn(self, new_sn):

        tran = self.conn._tran
        self.old_sn = tran.execute(ReadRegs(BT.ESC, 0x10, "14s"))[0].decode()

        try:
            tran.execute(WriteRegs(BT.ESC, 0x10, "<H", new_sn.encode('utf-8')))
            tprint("OK")
        except LinkTimeoutException:
            tprint("Timeout !")

        # save config and restart
        tran.execute(WriteRegs(BT.ESC, 0x78, "<H", 0x01))
        time.sleep(3)

        self.old_sn = tran.execute(ReadRegs(BT.ESC, 0x10, "14s"))[0]
        tprint("Current S/N:", old_sn)

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
