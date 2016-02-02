#!/usr/bin/env python
import base64
import argparse

from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2

# dd if=/dev/random of=password.key bs=64 count=1
with open('password.key', 'r') as f:
    password_salt = f.read()


def password_random(length):
    random_bytes = Random.new().read(length)
    return base64.b64encode(random_bytes)


def tenant_password(tenant_name, salt_key):
    # dd if=/dev/random of=password.key bs=64 count=1
    with open(salt_key, 'r') as f:
        password_salt = f.read()
    return base64.b64encode(PBKDF2(tenant_name, password_salt, 18))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("tenant_name", help="Provide tenant name")
    parser.add_argument("salt_file", help="Provide filename for salt.", default="password.key")

    args = parser.parse_args()
    print tenant_password(args.tenant_name, args.salt_file)
