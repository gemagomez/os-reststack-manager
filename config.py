#!/usr/bin/env python
import os
import errno

_basedir = os.path.abspath(os.path.dirname(__file__))

# Debug levels:
#  CRITICAL 50
#  ERROR   40
#  WARNING 30
#  INFO    20
#  DEBUG   10
#  NOTSET  0
DEBUG_LEVEL = 20
DEBUG_FORMAT = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
DEBUG_DATEFMT = '%m-%d %H:%M:%S'

# Make sure logs directory exists
# comment out if a different location to logs folder in local project is preferred
debug_path = os.path.join(_basedir, "logs")
try:
    os.makedirs(debug_path)
except OSError as exception:
    if exception.errno != errno.EEXIST:
        raise

DEBUG_FILENAME = os.path.join(debug_path, "tenant_manager.log")

# Database configuration
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(_basedir, 'app.db')
SQLALCHEMY_TRACK_MODIFICATIONS = True

DATABASE_CONNECT_OPTIONS = {}

# REST API binding IP and port
BIND_IP = '0.0.0.0'
PORT = 5050

# User specific configuration for cloud/app
PASSWORD_KEY = os.path.join(_basedir, 'password.key')
CREDENTIALS = os.path.join(_basedir, 'config/credentials.yml')
MACHINE = os.path.join(_basedir, "config/machine.yml")
CLOUD_CONFIG = os.path.join(_basedir, "config/cloud_config.yml")
