#!/usr/bin/env python
from __future__ import print_function

from flask import Blueprint, Flask, jsonify, json, abort, request, g
from app import credentials, db, Tenant, logging

from keystoneclient.auth.identity import v2
from keystoneclient import session
from novaclient import client
from lib.setup_tenant import tenant_create, extract_keys, parse_config
from lib.erase_tenant import tenant_delete

import argparse
import os
import re
import jwt
import config as CONF

mod = Blueprint ( 'tenant-manager', __name__ )

logger = logging.getLogger('tenant_manager')

@mod.before_request
def authenticate():
    # logger.debug("endpoint request: %s" % request.endpoint)
    if re.search('tenant_provisioned', str(request.endpoint)):
        g.user = "phone_home"
        logger.info("Authentication bypassed: tenant_provisioned")
        return

    try:
        decoded = jwt.decode(request.headers['X-Auth-Token'], credentials['tenant_secret'], algorithms=['HS256'])
        g.user = decoded['user']
    except KeyError, e:
        logger.error("Error: key error")
        abort(401)
    except jwt.DecodeError, e:
        logger.error("Error: decode error")
        abort(401)


@mod.route('/', methods=['GET'])
def test_connection():
    logger.info("User " + g.user + " testing connection.")
    return 'Ok',200

@mod.route('/tenant', methods=['POST'])
def create_tenant():
    #TODO: get json with name and pub_key info
    #TODO create the tenant
    logger.info("User %s requested creation", g.user)
    data=request.get_json(force=True)
    logger.debug("Request data: %s" % data)

    mconf = data['machine_conf'] if 'machine_conf' in data else CONF.MACHINE
    cconf = data['cloud_conf'] if 'cloud_conf' in data else CONF.CLOUD_CONFIG

    ip, machine_id = tenant_create(tenant_name=data['tenant'],
                       tenant_keys=extract_keys(data['pub_key']),
                       image_name_or_id=data['image_id'],
                       credentials=credentials, cloud_conf=cconf,
                       machine_conf=mconf)
    tenant = Tenant(tenant_name = data['tenant'], machine_id = machine_id, ip = ip)
    db.session.add(tenant)
    db.session.commit()

    return jsonify(tenant=data['tenant'], machine_id = machine_id, ip = ip), 202

@mod.route('/tenant/<tenant>', methods=['GET'])
def get_tenant(tenant):
    logger.info("User %s is enquiring about %s" % (g.user, tenant))
    tenant = Tenant.query.filter_by(tenant_name=tenant).first_or_404()
    return jsonify(tenant_name=tenant.tenant_name, machine_id=tenant.machine_id, ip=tenant.ip, status=tenant.status),200

@mod.route('/tenant/<tenant>', methods=['DELETE'])
def delete_tenant(tenant):
    logger.info("User %s deleting tenant %s", (g.user, tenant))
    tenant_delete(tenant, CONF.CREDENTIALS)
    return "",200

@mod.route('/tenant/provisioned/<machine_id>', methods=['POST'])
def tenant_provisioned(machine_id):
    logger.info("Tenant provisioned! %s" % machine_id)
    tenant = Tenant.query.filter_by(machine_id=machine_id).first_or_404()
    tenant.status = 'READY'
    db.session.commit()

    return "", 200


if __name__ == '__main__':
    logger.error("Run from run.py")
    exit(1)
