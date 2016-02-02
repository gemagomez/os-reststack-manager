#!/usr/bin/env python

from neutronclient.v2_0 import client
from keystoneclient.v2_0 import client as ks_client
import sys
import logging
from neutronclient.common.exceptions import NeutronClientException
from app import logging

logger = logging.getLogger('neutron_tenant')


def neutron_tenant_net(net_name, subnet_name, cidr, opts_tenant_name,
                       opts_shared, opts_dhcp, opts_dnsservers, opts_router,
                       dhcp_ip_start, dhcp_ip_end, os_username, os_password,
                       os_tenant_name, os_auth_url, os_region):

    keystone = ks_client.Client(username=os_username,
                                password=os_password,
                                tenant_name=os_tenant_name,
                                auth_url=os_auth_url,
                                region_name=os_region)
    neutron = client.Client(username=os_username,
                            password=os_password,
                            tenant_name=os_tenant_name,
                            auth_url=os_auth_url,
                            region_name=os_region)
    # Resolve tenant id
    tenant_id = None
    for tenant in [t._info for t in keystone.tenants.list()]:
        if (tenant['name'] == (opts_tenant_name or os_tenant_name)):
            tenant_id = tenant['id']
            break  # Tenant ID found - stop looking
    if not tenant_id:
        logger.error("Unable to locate tenant id for %s.", opts_tenant_name)
        sys.exit(1)

    # Create network
    networks = neutron.list_networks(name=net_name)
    if len(networks['networks']) == 0:
        logger.info('Creating network: %s', net_name)
        network_msg = {
            'network': {
                'name': net_name,
                'shared': opts_shared,
                'tenant_id': tenant_id
            }
        }
        network = neutron.create_network(network_msg)['network']
    else:
        logger.warning('Network %s already exists.', net_name)
        network = networks['networks'][0]

    # Create subnet
    subnets = neutron.list_subnets(name=subnet_name)
    if len(subnets['subnets']) == 0:
        logger.info('Creating subnet for %s', net_name)
        subnet_msg = {
            'subnet': {
                'name': subnet_name,
                'network_id': network['id'],
                'enable_dhcp': opts_dhcp,
                'cidr': cidr,
                'ip_version': 4,
                'tenant_id': tenant_id
            }
        }

        if (dhcp_ip_start and dhcp_ip_end):
            subnet_msg['allocation_pools'] = [{'start': dhcp_ip_start,
                                               'end': dhcp_ip_end}]

        subnet = neutron.create_subnet(subnet_msg)['subnet']
    else:
        logger.warning('Subnet %s already exists.', subnet_name)
        subnet = subnets['subnets'][0]

    # Update dns_nameservers
    if opts_dnsservers:
        msg = {
            'subnet': {
                'dns_nameservers': opts_dnsservers.split(',')
            }
        }
        logger.info('Updating dns_nameservers (%s) for subnet %s',
                    opts_dnsservers, subnet_name)
        neutron.update_subnet(subnet['id'], msg)

    # Plug subnet into router if provided
    if opts_router:
        routers = neutron.list_routers(name=opts_router)
        if len(routers['routers']) == 0:
            logger.error('Unable to locate provider router %s', opts_router)
            sys.exit(1)
        else:
            # Check to see if subnet already plugged into router
            ports = neutron.list_ports(device_owner='network:router_interface', network_id=network['id'])
            if len(ports['ports']) == 0:
                logger.info('Adding interface from %s to %s', opts_router, subnet_name)
                router = routers['routers'][0]
                try:
                    neutron.add_interface_router(router['id'], {'subnet_id': subnet['id']})
                except NeutronClientException:
                    logger.warning('Router already connected to subnet %s', subnet['id'])
            else:
                logger.warning('Router already connected to subnet')

    return network['id']


if __name__ == '__main__':
    pass
