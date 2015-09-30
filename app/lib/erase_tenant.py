#!/usr/bin/env python
import argparse
import os

from neutronclient.v2_0 import client as neutron_client
from keystoneclient.v3 import client as keystone_client
from keystoneclient.apiclient.exceptions import Conflict as keystoneConflictException
from novaclient.exceptions import NotFound as novaNotFoundException
from novaclient.exceptions import BadRequest as novaBadRequestException
from neutronclient.common.exceptions import NeutronClientException
from keystoneclient.apiclient.exceptions import NotFound as keystoneNotFoundException

from novaclient import client as nova_client
from glanceclient import client as glance_client

from tenant_password import tenant_password
from setup_tenant import parse_config
from app import logging

logger = logging.getLogger('erase_tenant')

class TenantNotFound(Exception):
    pass

def tenant_delete(tenant_name, credentials):
    credsc = parse_config(credentials)

    keystone = keystone_client.Client(username=credsc['os_user'], password=credsc['os_password'], tenant_name=credsc['os_tenant_name'], auth_url=credsc['os_auth_url_v3'])
    try:
        tenant=keystone.projects.find(name=tenant_name)
        logger.info("Tenant found %s " % tenant.id)
    except keystoneNotFoundException,e:
        logger.error("Tenant Not Found, aborting")
        raise TenantNotFound()

    nova = nova_client.Client(version = 2, username=credsc['os_user'], api_key=credsc['os_password'], project_id=tenant.id, service_type='compute', auth_url=credsc['os_auth_url_v2'], tenant_id=credsc['os_tenant_id'])

    neutron = neutron_client.Client(username=credsc['os_user'], password=credsc['os_password'], project_id=tenant.id, auth_url=credsc['os_auth_url_v2'], tenant_id=credsc['os_tenant_id'])

    # Finding the tenant's floating ip
    floating_ips=neutron.list_floatingips()
    for (ip_id,ip) in [(floating_ip['id'],floating_ip['floating_ip_address']) for floating_ip in floating_ips['floatingips'] if floating_ip['tenant_id'] == tenant.id]:
        logger.info("Found a floating ip id: %s (ip is: %s)" % (ip_id, ip))
        neutron.update_floatingip(ip_id, {'floatingip': {'port_id': None}})
        neutron.delete_floatingip(ip_id)

    vms = nova.servers.list(search_opts={'all_tenants': 1})
    for vm in [vm for vm in vms if vm.tenant_id == tenant.id]:
        logger.info("Deleting VM: %s - %s" % (vm.name, vm.id))
        nova.servers.delete(vm.id)

        # Wait until VM is really gone.
        status = vm.status
        while True:
            try:
                nova.servers.get(vm.id)
            except novaNotFoundException,e:
                logger.debug("VM deleted")
                break

    subnets = [subnet for subnet in neutron.list_subnets()['subnets'] if subnet['tenant_id'] == tenant.id]

    routers=neutron.list_routers()
    for router in [router for router in routers['routers'] if router['tenant_id'] == tenant.id]:
        logger.info("Removing Router: %s" % router['id'])
        neutron.remove_gateway_router(router['id'])
        for subnet in subnets:
            try:
                neutron.remove_interface_router(router['id'], { 'subnet_id': subnet['id'] })
            except NeutronClientException,e:
                pass

        neutron.delete_router(router['id'])

    for subnet in subnets:
        logger.info("Removing subnet: %s" % subnet['id'])
        neutron.delete_subnet(subnet['id'])

    networks=neutron.list_networks()
    for network in [network for network in networks['networks'] if network['tenant_id'] == tenant.id]:
        logger.info("Removing Network: %s" % network['id'])
        neutron.delete_network(network['id'])

    logger.info("Removing Tenant %s" % tenant.id)
    keystone.projects.delete(tenant.id)
    try:
        user = keystone.users.find(name=tenant_name)
        logger.info("Deleting  user: %s" % user.id)
        keystone.users.delete(user.id)
    except keystoneNotFoundException,e:
        logger.debug("Didn't find user")
        pass

if __name__ == '__main__':
    pass
