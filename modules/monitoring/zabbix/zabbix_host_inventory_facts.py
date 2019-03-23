#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2019, sky-joker
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

RETURN = '''
hosts_inventory:
  description: List of Zabbix hosts. See https://www.zabbix.com/documentation/3.4/manual/api/reference/host/get for list of host values.
  returned: success
  type: dict
  sample: "[{'hostid': '10263', 'proxy_hostid': '0', ..., {'poc_2_phone_b': '', 'poc_2_cell': '', 'poc_2_screen': '', 'poc_2_notes': ''}}]"
'''

DOCUMENTATION = '''
module: zabbix_host_inventory_facts
short_description: Gather facts about Zabbix host inventory
author:
  - sky-joker (@sky-jocker)
version_added: ''
description:
  - This module gets Zabbix host inventory.
requirements:
  - python >= 2.7
  - zabbix-api
options:
    host_name:
        description:
            - Name of the host in Zabbix.
            - host_name is the unique identifier used and cannot be updated using this module.
        required: true
    host_ip:
        description:
            - Host interface IP of the host in Zabbix.
        required: false
    exact_match:
        description:
            - Find the exact match
        type: bool
        default: no
    remove_duplicate:
        description:
            - Remove duplicate host from host result
        type: bool
        default: yes
extends_documentation_fragment:
    - zabbix
'''

EXAMPLES = '''
- name: Get host inventory info
  local_action:
    module: zabbix_host_inventory_facts
    server_url: http://monitor.example.com
    login_user: username
    login_password: password
    host_name: ExampleHost
    timeout: 10
    exact_match: no
    remove_duplicate: yes
'''

from ansible.module_utils.basic import AnsibleModule

try:
    from zabbix_api import ZabbixAPI, ZabbixAPISubClass

    # Extend the ZabbixAPI
    # Since the zabbix-api python module too old (version 1.0, no higher version so far),
    # it does not support the 'hostinterface' api calls,
    # so we have to inherit the ZabbixAPI class to add 'hostinterface' support.
    class ZabbixAPIExtends(ZabbixAPI):
        hostinterface = None

        def __init__(self, server, timeout, user, passwd, validate_certs, **kwargs):
            ZabbixAPI.__init__(self, server, timeout=timeout, user=user, passwd=passwd, validate_certs=validate_certs)
            self.hostinterface = ZabbixAPISubClass(self, dict({"prefix": "hostinterface"}, **kwargs))

    HAS_ZABBIX_API = True
except ImportError:
    HAS_ZABBIX_API = False


class Host(object):
    def __init__(self, module, zbx):
        self._module = module
        self._zapi = zbx

    def get_hosts_inventory_by_host_name(self, host_name, exact_match):
        """Get hosts by host name"""
        search_key = 'search'
        if exact_match:
            search_key = 'filter'
        host_list = self._zapi.host.get({
            'output': 'extend',
            search_key: {
                'name': [host_name]
            },
            "withInventory": True,
            "selectInventory": "extend"
        })
        if len(host_list) < 1:
            self._module.fail_json(msg="Host not found: %s" % host_name)
        else:
            return host_list

    def get_hosts_inventory_by_all_host(self, host_name):
        """Get hosts inventory by all host"""
        host_list = self._zapi.host.get({
            'output': 'extend',
            "withInventory": True,
            "selectInventory": "extend"
        })
        if len(host_list) < 1:
            self._module.fail_json(msg="Host not found: %s" % host_name)
        else:
            return host_list

    def delete_duplicate_hosts(self, hosts):
        """ Delete duplicated hosts """
        unique_hosts = []
        listed_hostnames = []
        for zabbix_host in hosts:
            if zabbix_host['name'] in listed_hostnames:
                continue
            unique_hosts.append(zabbix_host)
            listed_hostnames.append(zabbix_host['name'])
        return unique_hosts


def main():
    module = AnsibleModule(
        argument_spec=dict(
            server_url=dict(type='str', required=True, aliases=['url']),
            login_user=dict(type='str', required=True),
            login_password=dict(type='str', required=True, no_log=True),
            host_name=dict(type='str', default='', required=False),
            host_ip=dict(type='list', default=[], required=False),
            http_login_user=dict(type='str', required=False, default=None),
            http_login_password=dict(type='str', required=False, default=None, no_log=True),
            validate_certs=dict(type='bool', required=False, default=True),
            timeout=dict(type='int', default=10),
            exact_match=dict(type='bool', required=False, default=False),
            remove_duplicate=dict(type='bool', required=False, default=True)
        ),
        supports_check_mode=True
    )

    if not HAS_ZABBIX_API:
        module.fail_json(msg="Missing required zabbix-api module (check docs or install with: pip install zabbix-api)")

    server_url = module.params['server_url']
    login_user = module.params['login_user']
    login_password = module.params['login_password']
    http_login_user = module.params['http_login_user']
    http_login_password = module.params['http_login_password']
    validate_certs = module.params['validate_certs']
    host_name = module.params['host_name']
    timeout = module.params['timeout']
    exact_match = module.params['exact_match']
    is_remove_duplicate = module.params['remove_duplicate']

    zbx = None
    # login to zabbix
    try:
        zbx = ZabbixAPIExtends(server_url, timeout=timeout, user=http_login_user, passwd=http_login_password,
                               validate_certs=validate_certs)
        zbx.login(login_user, login_password)
    except Exception as e:
        module.fail_json(msg="Failed to connect to Zabbix server: %s" % e)

    host = Host(module, zbx)

    if host_name:
        hosts_inventory = host.get_hosts_inventory_by_host_name(host_name, exact_match)
    else:
        hosts_inventory = host.get_hosts_inventory_by_all_host(host_name)

    if is_remove_duplicate:
        hosts_inventory = host.delete_duplicate_hosts(hosts_inventory)

    module.exit_json(ok=True, hosts_inventory=hosts_inventory)


if __name__ == "__main__":
    main()