#!/usr/bin/env python
import jwt
import sys
import os
import argparse
import yaml

def parse_config(cfg_file):
    with open(cfg_file, 'r') as f:
        return yaml.load(f)

parser = argparse.ArgumentParser()
parser.add_argument("token", help="Provide token")
parser.add_argument("config", help="Provide credentials configuration file")

args = parser.parse_args()
token = args.token
config = parse_config(args.config)

try:
    decoded = jwt.decode(token, config['tenant_secret'], algorithms=['HS256'])
    print "User: "+ decoded['user']
except jwt.DecodeError, e:
    print "Error decoding! Invalid token."


