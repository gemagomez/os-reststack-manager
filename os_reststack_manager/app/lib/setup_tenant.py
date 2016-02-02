#!/usr/bin/env python
import jwt
import sys
import os
import argparse
import urllib2
import json
import re
import time
import sys
import yaml

from uuid import uuid4
from jinja2 import Environment
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from neutronclient.v2_0 import client as neutron_client
from keystoneclient.v3 import client as keystone_client
from keystoneclient.apiclient.exceptions import Conflict as keystoneConflictException
from novaclient.exceptions import NotFound as novaNotFoundException
from novaclient.exceptions import BadRequest as novaBadRequestException
from neutronclient.common.exceptions import NeutronClientException
from novaclient import client as nova_client
from glanceclient import client as glance_client

from neutron_tenant_net import neutron_tenant_net
from tenant_password import password_random, tenant_password
from os_reststack_manager.app import logging

logger = logging.getLogger('setup_tenant')


def extract_keys(key):
    if key.startswith("lp:"):
        lp_id = key.split(':')[1]
        lp_url = "http://launchpad.net/%s/+sshkeys" % lp_id
        response = urllib2.urlopen(lp_url)
        return response.read().split("\n")
    else:
        return [key]


def gen_multipart_cloudconfig(config_dict, other_files, tenant_name, tenant_pass, tenant_id):
    msg = MIMEMultipart()
    sm = MIMEText("#cloud-config\n%s" % json.dumps(config_dict), "cloud-config", sys.getdefaultencoding())
    sm.add_header('Content-Disposition', 'attachment', filename="cloud-config.txt")
    msg.attach(sm)
    for other_file in other_files:
        extra_config = prepare_extra_config(tenant_name, tenant_pass, tenant_id, other_file['template'])
        sm2 = MIMEText(extra_config, other_file['content_type'], sys.getdefaultencoding())
        sm2.add_header('Content-Disposition', 'attachment', filename=other_file['name'])
        logger.debug(os.path.curdir)
        msg.attach(sm2)
    return str(msg)


def parse_config(cfg_file):
    with open(cfg_file, 'r') as f:
        return yaml.load(f)


def prepare_extra_config(tenant_name, tenant_pass, tenant_id, template):
    def uuid4_filter(foo):
        return uuid4()

    stream = open(template, 'r')
    txt = stream.read()
    env = Environment()
    env.filters['random_password'] = password_random
    env.filters['uuid4'] = uuid4_filter
    tmpl = env.from_string(txt)

    return tmpl.render(tenant_name=tenant_name,
                       tenant_pass=tenant_pass,
                       tenant_id=tenant_id)


def gen_user_data(machinec, tenant_keys):
    user_data = {
        "users": [
            {
                "name": machinec['cloud_init']['user_name'],
                "lock-passwd": False,
                "shell": "/bin/bash",
                "ssh-authorized-keys": tenant_keys,
                "sudo": "ALL=(ALL) NOPASSWD:ALL"
                }
        ],
        "apt_proxy": machinec['cloud_init']['apt_proxy'],
        "apt_update": True,
        "apt_upgrade": True,
        "apt_sources": machinec['cloud_init']['apt_sources_default'] + machinec['cloud_init']['apt_sources_user'],
        "packages": machinec['cloud_init']['apt_packages_default'] + machinec['cloud_init']['apt_packages_user'],
        "phone_home": {
            "url": machinec['phone_home_url'],
            "post": ['instance_id']
        },
        "runcmd": machinec['cloud_init']['run_cmds'] + machinec['cloud_init']['user_run_cmds']

    }
    return user_data


def tenant_create(tenant_name, tenant_keys, image_name_or_id, credentials, cloud_conf, machine_conf):

    credsc = credentials
    cloudc = cloud_conf if type(cloud_conf) is dict else parse_config(cloud_conf)
    machinec = machine_conf if type(machine_conf) is dict else parse_config(machine_conf)

    keystone = keystone_client.Client(username=credsc['os_user'],
                                      password=credsc['os_password'],
                                      tenant_name=credsc['os_tenant_name'],
                                      auth_url=credsc['os_auth_url_v3'])

    try:
        tenant = keystone.projects.create(name=tenant_name,
                                          domain=credsc['os_domain'],
                                          enabled=True)

        logger.info("Creating tenant %s", tenant_name)
    except keystoneConflictException, e:
        tenant = keystone.projects.find(name=tenant_name)
        logger.warning("Tenant %s already exists", tenant_name)

    try:
        new_password = tenant_password(tenant_name, machinec['password_salt'])
        user = keystone.users.create(name=tenant_name,
                                     password=new_password,
                                     default_project=tenant.id)

        logger.info("Creating user %s", tenant_name)
    except keystoneConflictException, e:
        user = keystone.users.find(name=tenant_name)
        logger.warning("User %s already exists", tenant_name)

    role = keystone.roles.find(name=credsc['role_name'])

    keystone.roles.grant(role=role,
                         user=user,
                         project=tenant)

    nova = nova_client.Client(version=2,
                              username=credsc['os_user'],
                              api_key=credsc['os_password'],
                              project_id=tenant.id,
                              service_type='compute',
                              auth_url=credsc['os_auth_url_v2'],
                              tenant_id=credsc['os_tenant_id'])

    nova.quotas.update(tenant.id,
                       instances=machinec['quota']['quota_instances'],
                       cores=machinec['quota']['quota_cores'],
                       security_groups=machinec['quota']['quota_security_groups'],
                       security_group_rules=machinec['quota']['quota_security_group_rules'],
                       ram=machinec['quota']['quota_ram'])

    neutron = neutron_client.Client(username=credsc['os_user'],
                                    password=credsc['os_password'],
                                    project_id=tenant.id,
                                    auth_url=credsc['os_auth_url_v2'],
                                    tenant_id=credsc['os_tenant_id'])
    neutron.update_quota(tenant.id,
                         {'quota': {'port': machinec['quota']['quota_port'],
                                    'security_group': machinec['quota']['quota_security_groups'],
                                    'security_group_rule': machinec['quota']['quota_security_group_rules'],
                                    'floatingip': machinec['quota']['quota_floating_ip']
                                    }
                          }
                         )

    router = filter(lambda r: r['name'] == ("%s_router" % tenant_name), neutron.list_routers()['routers'])
    if len(router) == 0:
        logger.info("Creating router")
        neutron_as_tenant = neutron_client.Client(username=tenant_name,
                                                  password=tenant_password(tenant_name, machinec['password_salt']),
                                                  project_id=tenant.id,
                                                  auth_url=credsc['os_auth_url_v2'],
                                                  tenant_id=tenant.id)
        neutron_as_tenant.create_router({'router': {'name': machinec['net']['router'] % tenant_name}})
    else:
        logger.warning("Router already exists")

    router = filter(lambda r: r['name'] == (machinec['net']['router'] % tenant_name), neutron.list_routers()['routers'])[0]

    external_network = filter(lambda n: n['name'] == machinec['net']['ext_net'], neutron.list_networks()["networks"])[0]

    # Wiring tenant router to the outside world
    neutron.add_gateway_router(router['id'], {'network_id': external_network['id'], 'enable_snat': machinec['net']['enable_snat']})

    # Configure networking
    admin_net_id = neutron_tenant_net(machinec['net']['net_name'] % tenant_name,
                                      machinec['net']['subnet_name'] % tenant_name,
                                      machinec['net']['cidr'],
                                      tenant_name,
                                      machinec['net']['net_shared'],
                                      machinec['net']['disable_dhcp'],
                                      machinec['net']['dns_servers'],
                                      machinec['net']['router'] % tenant_name,
                                      machinec['net']['start_dhcp_ip'], machinec['net']['end_dhcp_ip'],
                                      credsc['os_user'],
                                      credsc['os_password'],
                                      credsc['os_tenant_name'],
                                      credsc['os_auth_url_v2'],
                                      credsc['os_region_name'])

    # Boot new nova instance
    vm_manager = nova.servers
    try:
        image = nova.images.get(image_name_or_id)
    except novaNotFoundException, e:
        image = sorted(filter(lambda i: re.search(image_name_or_id, i.name or ""), nova.images.list()), reverse=True, key=lambda i: i.created)[0]

    flavor = nova.flavors.find(name=machinec['flavor_name'])

    nova_tenant = nova_client.Client(version=2,
                                     username=tenant_name,
                                     api_key=tenant_password(tenant_name, machinec['password_salt']),
                                     project_id=tenant.id,
                                     service_type='compute',
                                     auth_url=credsc['os_auth_url_v2'],
                                     tenant_id=tenant.id)

    try:
        machine = nova_tenant.servers.find(name=machinec['net']['bastion_name'] % tenant_name)
        logger.warning("VM found, skipping creation")

        # Find ip return value
        ip = filter(lambda o: o["OS-EXT-IPS:type"] == 'floating', machine.addresses['%s_admin_net' % tenant_name])[0]['addr']
        logger.debug(">>> %s " % ip)

        return ip, machine.id

    except novaNotFoundException, e:
        logger.info("Creating new VM")
        # extra_config = prepare_extra_config(tenant_name,tenant_password(tenant_name,machinec['password_salt']), tenant.id, cloudc)
        user_data = gen_user_data(machinec, tenant_keys)

        machine = nova_tenant.servers.create(name=machinec['net']['bastion_name'] % tenant_name,
                                             image=image,
                                             flavor=flavor,
                                             userdata=gen_multipart_cloudconfig(user_data, cloudc['extra_files'],
                                             tenant_name, tenant_password(tenant_name, machinec['password_salt']), tenant.id),
                                             nics=[{'net-id': admin_net_id}])
        status = machine.status
        while status == 'BUILD':
            time.sleep(5)
            machine = nova.servers.get(machine.id)
            status = machine.status
            logger.debug("status: %s" % status)

        sg = filter(lambda g: g['tenant_id'] == tenant.id and g['name'] == credsc['os_domain'], neutron.list_security_groups()['security_groups'])[0]

        try:
            neutron.create_security_group_rule(
                    {'security_group_rule': {'security_group_id': sg['id'],
                                             'direction': 'ingress'}})
            logger.info("Security group rule created")
        except NeutronClientException, e:
            logger.warning("Security group rule already exists, skipping")

        floating_ips = nova_tenant.floating_ips.list()
        if len(floating_ips) > 0:
            floating_ip = floating_ips[0]
            logger.warning("Reusing floating ip %s", floating_ip.ip)
        else:
            # Create and add a new floating ip
            floating_ip = nova_tenant.floating_ips.create(pool=machinec['net']['ext_net'])
            logger.info("Created floating ip %s", floating_ip.ip)

        machine.add_floating_ip(floating_ip)

        return floating_ip.ip, machine.id

if __name__ == '__main__':
    pass
