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
'''

DOCUMENTATION = '''
module: zabbix_event_close
short_description: Close the Zabbix event
author:
  - sky-joker (@sky-jocker)
version_added: ''
description:
  - This module closes the event that occurred in Zabbix.
requirements:
  - python >= 2.6
  - zabbix-api
options:
    event_id:
        description:
            - Specify event ID to be closed.
        type: str
        required: true
    message:
        description:
            - Specify the message to add when event closing.
        type: str
extends_documentation_fragment:
    - zabbix
'''

EXAMPLES = '''
- name: Close event
  local_action:
    module: zabbix_event_close
    server_url: http://monitor.example.com
    login_user: username
    login_password: password
    host_name: ExampleHost
    timeout: 10
    event_id: 186
    message: auto close
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

    def event_close(self, event_id, message):
        try:
            self._zapi.event.acknowledge({
                'eventids': event_id,
                'message': message,
                'action': 1
            })
        except Exception as e:
            self._module.fail_json(msg='%s' % e)


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
            event_id=dict(type='str', required=True),
            message=dict(type='str')
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
    timeout = module.params['timeout']
    event_id = module.params['event_id']
    message = module.params['message']

    zbx = None
    # login to zabbix
    try:
        zbx = ZabbixAPIExtends(server_url, timeout=timeout, user=http_login_user, passwd=http_login_password,
                               validate_certs=validate_certs)
        zbx.login(login_user, login_password)
    except Exception as e:
        module.fail_json(msg="Failed to connect to Zabbix server: %s" % e)

    host = Host(module, zbx)

    host.event_close(event_id, message)

    module.exit_json(changed=True)


if __name__ == "__main__":
    main()
