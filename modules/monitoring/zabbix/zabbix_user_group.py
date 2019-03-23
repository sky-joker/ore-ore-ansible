#/!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, sky_joker
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
module: zabbix_user_group
short_description: Module to add user groups to Zabbix.
description:
    - Create user groups if they do not exist.
    - Delete existing user groups if they exist.
requirements:
    - python >= 2.6
    - zabbix-api
options:
    server_url:
        description:
            - Specify the URL of zabbix server.
        required: True
    login_user:
        description:
            - Specify the user name to login to the zabbix server.
        required: True
    login_password:
        description:
            - Specify the user name to login to the zabbix server.
        required: True
    validate_certs:
        description:
            - Specify the password to login to the zabbix server.
        default: True
    user_group_name:
        description:
            - Specify the user group name.
        required: True
    host_groups:
        description:
            - Specify the host group to be associated with the user group.
            - 'Valid attributes are:'
            - '   host_group_name: Specify host group name.'
            - '   permission: Specify the permission to be associated with the host group'
            - '      choices: [deny, read, read-write]'
    users:
        description:
            - Specify the user(alias name) to be associated with the user group.
    state:
        description:
            - Create or delete user group.
        default: present
        choices: [ "present", "absent" ]
    timeout:
        description:
            - Specify the timeout time for Zabbix server connection.
        default: 10
'''

EXAMPLES = '''
---
- zabbix_user_group:
    server_url: http://127.0.0.1/zabbix
    login_user: admin
    login_password: zabbix
    validate_certs: no
    user_group_name: test group
    host_groups:
      - host_group_name: Linux servers
        permission: read
      - host_group_name: Hypervisors
        permission: deny
    users:
      - Admin
      - test
    state: present

- zabbix_user_group:
    server_url: http://127.0.0.1/zabbix
    login_user: admin
    login_password: zabbix
    validate_certs: no
    user_group_name: test group
    state: absent
'''

try:
    from zabbix_api import ZabbixAPI, ZabbixAPISubClass

    HAS_ZABBIX_API = True
except ImportError:
    HAS_ZABBIX_API = False

from ansible.module_utils.basic import AnsibleModule
from collections import defaultdict

def check_user_group(zbx, user_group):
    r = zbx.usergroup.get({
        'output': 'extend',
        'filter': {
            'name': user_group
        }
    })

    if(r):
        return r[0]
    else:
        return None

def get_host_group_id(zbx, host_group):
    r = zbx.hostgroup.get({
        'output': 'extend',
        'filter': {
            'name': host_group
        }
    })

    if(r):
        return r[0]
    else:
        return None

def get_user_id(zbx, user):
    r = zbx.user.get({
        'output': 'extend',
        'filter': {
            'alias': user
        }
    })

    if(r):
        return r[0]
    else:
        return None

def main():
    argument_spec = dict(
        server_url=dict(type='str', required=True, aliases=['url']),
        login_user=dict(type='str', required=True),
        login_password=dict(type='str', required=True, no_log=True),
        http_login_user=dict(type='str', required=False, default=None),
        http_login_password=dict(type='str', required=False, default=None, no_log=True),
        validate_certs=dict(type='bool', required=False, default=True),
        user_group_name=dict(type='str', required=True),
        host_groups=dict(type='list', required=False,
                         options=dict(
                             host_group_name=dict(type='str', required=True),
                             permission=dict(type='str', required=True,
                                             choice=['deny', 'read', 'read-write']),
                         )),
        users=dict(type='list'),
        state=dict(default='present', required=False, choice=['present', 'absent']),
        timeout=dict(type='int', default=10)
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_ZABBIX_API:
        module.fail_json(msg="Missing required zabbix-api module (check docs or install with: pip install zabbix-api)")

    server_url = module.params['server_url']
    login_user = module.params['login_user']
    login_password = module.params['login_password']
    http_login_user = module.params['http_login_user']
    http_login_password = module.params['http_login_password']
    validate_certs = module.params['validate_certs']
    user_group_name = module.params['user_group_name']
    users = module.params['users']
    host_groups = module.params['host_groups']
    state = module.params['state']
    timeout = module.params['timeout']

    try:
        zbx = ZabbixAPI(server_url, timeout=timeout, user=http_login_user, passwd=http_login_password,
                        validate_certs=validate_certs)
        zbx.login(login_user, login_password)
    except Exception as e:
        module.fail_json(msg="Failed to connect to Zabbix server: %s" % e)

    host_group_permission = {
        'deny': 0,
        'read': 2,
        'read-write':3
    }

    result = dict(changed=False)
    if state == "present":
        nested_dict = (lambda: defaultdict(nested_dict))

        r = check_user_group(zbx, user_group_name)
        if(r):
            result.update(r)
            module.exit_json(**result)

        exist_groups = []
        for host_group in host_groups:
            r = get_host_group_id(zbx, host_group['host_group_name'])
            if(r):
                exist_groups.append({'permission': host_group_permission[host_group['permission']],
                                     'id': r['groupid']})
            else:
                module.fail_json(msg="host group %s not found." % host_group['host_group_name'])

        user_ids = []
        if(users):
            for user in users:
                r = get_user_id(zbx, user)
                if(r):
                    user_ids.append(r['userid'])
                else:
                    module.fail_json(msg="user %s not found." % user)

        try:
            r = zbx.usergroup.create({
                'name': user_group_name,
                'rights': exist_groups,
                'userids': user_ids
            })
            result['changed'] = True
            result.update(r)
            module.exit_json(**result)
        except Exception as e:
            module.fail_json(msg="Error adding user group %s: %s" % (user_group_name, e))

    if state == "absent":
        r = check_user_group(zbx, user_group_name)
        if(r):
            r = zbx.usergroup.delete([r['usrgrpid']])
            result['changed'] = True
            result.update(r)
            module.exit_json(**result)
        else:
            module.exit_json(**result)

if __name__ == "__main__":
    main()