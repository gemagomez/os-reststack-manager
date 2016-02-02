#!/usr/bin/env python

import os
import os_reststack_manager.config as CONF
import logging

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from lib.setup_tenant import parse_config


app = Flask(__name__)
app.config.from_object('os_reststack_manager.config')

# DB setup
db = SQLAlchemy(app)
db.create_all()

credentials = parse_config(CONF.CREDENTIALS)


class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String, unique=True)
    status = db.Column(db.String, unique=False)
    tenant_name = db.Column(db.String, unique=True)
    ip = db.Column(db.String)

    def __init__(self, tenant_name, machine_id, ip):
        self.tenant_name = tenant_name
        self.machine_id = machine_id
        self.ip = ip
        self.status = 'BUILDING'

    def __repr__(self):
        return '<tenant_name: %s, machine_id: %s, ip: %s, status: %s>' % (self.tenant_name, self.machine_id, self.ip, self.status)


def application(environ=None, start_response=None):

    from os_reststack_manager.app.tenant_manager import mod

    # Set up of logger
    logging.basicConfig(level=CONF.DEBUG_LEVEL,
                        format=CONF.DEBUG_FORMAT,
                        datefmt=CONF.DEBUG_DATEFMT,
                        filename=CONF.DEBUG_FILENAME,
                        filemode='w')

    # Checks for default config files
    if not os.path.isfile(CONF.PASSWORD_KEY):
        print("File %s does not exist" % CONF.PASSWORD_KEY)
        exit(1)

    if not os.path.isfile(CONF.CREDENTIALS):
        print("File %s does not exist" % CONF.CREDENTIALS)
        exit(1)

    if not os.path.isfile(CONF.MACHINE):
        print("File %s does not exist" % CONF.MACHINE)
        exit(1)

    if not os.path.isfile(CONF.CLOUD_CONFIG):
        print("File %s does not exist" % CONF.CLOUD_CONFIG)
        exit(1)

    app.register_blueprint(mod)

    if not environ or not start_response:
        return app
    else:
        return app(environ, start_response)
