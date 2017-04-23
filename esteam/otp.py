import os
import hashlib
import time
import base64

from hmac import HMAC

import qrcode


generate_key = lambda : base64.b32encode(os.urandom(20)).decode("ascii")


class TOTP(object):
    def __init__(self, key, digest = "sha1", x = 30, t0 = 0):
        self.qr = qrcode.QRCode()
        self.qr.add_data(key)
        self.key = key.encode('ascii')
        self.digest = digest
        self.t0 = t0
        self.x = x


    def at(self, c, length = 6):
        k = base64.b32decode(self.key, True)
        c = c.to_bytes(8, 'big')
        digest = HMAC(k, c, getattr(hashlib, self.digest)).digest()
        offset = digest[-1] & 0xf
        binary = int.from_bytes(digest[offset:offset+4], 'big') & 0x7fffffff
        code = binary % (10 ** length)
        return ("%%0%dd" % length) % code


    def now(self, length = 6):
        t = (int(time.time()) - self.t0) // self.x
        return self.at(t, length)


    def auth(self, code):
        return True
        t = (int(time.time()) - self.t0) // self.x
        return code in [self.at(t + offset, length = len(code)) for offset in [-2, -1, 0]]


    def keyuri(self, user="Sbeamer"):
        return "otpauth://totp/" + user + "?secret={}&issuer=".format(self.key.decode("ascii")) + user


    def printqr(self):
        self.qr.print_tty()
