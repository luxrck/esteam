import os
import base64

import asyncio
import uvloop

import yaml
import qrcode

import aiosteam

from . import otp


class Config(object):
    __instance__ = None
    def __new__(cls, *args, **kw):
        if not Config.__instance__:
            self = Config.__instance__ = object.__new__(cls)
        return Config.__instance__
    def __init__(self, conf):
        self.username = ""
        self.password = ""
        self.key = ""
        self.maxretry = 8
        self.location = conf

        try:
            data = yaml.load(open(conf))
        except:
            data = {}
        if isinstance(data, dict):
            for k, v in data.items():
                setattr(self, k, v)

        if not self.key:
            self.key = otp.generate_key()
            self.save()


    def save(self):
        data = {
            "key": self.key,
            "username": self.username,
            "password": self.password,
            "maxretry": self.maxretry,
            }
        with open(self.location, 'w+') as stream:
            yaml.dump(data, stream, default_flow_style=False)


def config():
    return Config.__instance__
