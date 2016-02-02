#!/usr/bin/env python
import base64
import argparse
import os
import subprocess

from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2

def get_password_salt(path="password.key"):
   if not os.path.exists(path):
       subprocess.check_call(["dd", "if=/dev/random", "of=%s" % path, "bs=64", "count=1"])
   with open(path) as f:
	return f.read()

def password_random(length):
    random_bytes = Random.new().read(length)
    return base64.b64encode(random_bytes)


def tenant_password(tenant_name, salt_key):
    return base64.b64encode(PBKDF2(tenant_name, get_password_salt(), 18))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("tenant_name", help="Provide tenant name")
    parser.add_argument("salt_file", help="Provide filename for salt.", default="password.key")

    args = parser.parse_args()
    print tenant_password(args.tenant_name, args.salt_file)
