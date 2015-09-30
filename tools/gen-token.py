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
parser.add_argument("username", help="Provide username")
parser.add_argument("config", help="Provide credentials configuration file")

args = parser.parse_args()
username = args.username
config = parse_config(args.config)

try:
    encoded = jwt.encode({'user': username}, config['tenant_secret'], algorithm='HS256')
    print encoded
except KeyError, e:
    print "Error, please make sure your credentials file has a variable called tenant_secret."

