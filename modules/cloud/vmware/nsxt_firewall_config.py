#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2019, sky_joker
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
module: nsxt_firewall_config
short_description: Back up or restore firewall rules.
author:
  - sky-joker (@sky-joker)
version_added: ''
description:
  - This module can back up or restore firewall rules.
requirements:
  - python >= 2.7
options:
    hostname:
      description: 'Deployed NSX manager hostname.'
      required: true
      type: str
    username:
      description: 'The username to authenticate with the NSX manager.'
      required: true
      type: str
    password:
      description: 'The password to authenticate with the NSX manager.'
      required: true
      type: str
    port:
      description: 'Port to access NSX manager.'
      default: 443
      type: int
    validate_certs:
      description:
      - Allows connection when SSL certificates are not valid. Set to C(false) when certificates are not trusted.
      - If the value is not specified in the task, the value of environment variable C(VMWARE_VALIDATE_CERTS) will be used instead.
      - Environment variable supported added in Ansible 2.6.
      - If set to C(yes), please make sure Python >= 2.7.9 is installed on the given machine.
      type: bool
      default: 'yes'
    section_name:
      description:
      - Specifies the firewall section name.
      required: True
      type: str
    backup:
      description:
      - This argument will cause the create a backup file for the firewall section.
      - A backup directory is created in the current directory where you run Playbook, and a backup file is created in it.
      default: 'no'
      choices: [ 'yes', 'no' ]
      type: str
    backup_options:
      description:
      - This argument can specify where to save the backup file.
      - 'Valid attributes are:'
      - '  filename: Specify backup file name.'
      - '  dir_path: Specify a directory name to save backup file.'
    restore:
      description:
      - This argument can be restore firewall rules.
      - 'Valid attributes are:'
      - '  file_path: Specify the firewall rules file path to restore'
    exclude_rules:
      description:
      - This argument can exclude rules to backup or restore by firewall name.
      type: list
'''

EXAMPLES = '''
- name: firewall backup
  nsxt_firewall_config:
    hostname: "{{ nsxt_manager_hostname }}"
    username: "{{ nsxt_username }}"
    password: "{{ nsxt_password }}"
    validate_certs: no
    section_name: "{{ section_name }}"
    backup: yes
    exclude_rules:
      - Default LR Layer3 Rule

- name: firewall restore
  nsxt_firewall_config:
    hostname: "{{ nsxt_manager_hostname }}"
    username: "{{ nsxt_username }}"
    password: "{{ nsxt_password }}"
    validate_certs: no
    section_name: "{{ section_name }}"
    exclude_rules:
      - Default LR Layer3 Rule
    restore:
      file_path: "{{ restore_firewall_config_path }}"
'''

RETURN = '''
backup_path:
  description: The full path to the backup file
  returned: when backup is yes
  type: str
  sample: /backup/T0-FW-SEC01_config.2019-05-11@18:01:41
'''

import json
import time
import os
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible.module_utils.vmware_nsxt import vmware_argument_spec, request


def get_sectionid_by_section_display_name(module, manager_url, mgr_username, mgr_password, validate_certs,
                                          section_name):
    try:
        (rc, resp) = request(manager_url + '/firewall/sections', method='GET',
                             url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs,
                             ignore_errors=False)
    except Exception as err:
        module.fail_json(msg="%s" % to_native(err))

    section_id = ""
    revision = ""
    for section in resp['results']:
        if (section['display_name'] == section_name):
            section_id = section['id']
            revision = section['_revision']
        if (section_id and revision):
            break

    if(not(section_id) or not(revision)):
        module.fail_json(msg="Error")

    return section_id, revision


def get_section_firewall_rules_by_section_id(module, manager_url, mgr_username, mgr_password, validate_certs,
                                             section_id):
    try:
        (rc, resp) = request(manager_url + '/firewall/sections/{0}/rules'.format(section_id), method='GET',
                             url_username=mgr_username, url_password=mgr_password,
                             validate_certs=validate_certs, ignore_errors=False)
    except Exception as err:
        module.fail_json(msg="%s" % err)

    return rc, resp


def exclude_firewall_rule(firewall_rules, exclude_rules):
    for exclude_rule in exclude_rules:
        del_num = 0
        for firewall_rule in firewall_rules:
            if (firewall_rule['display_name'] == exclude_rule):
                firewall_rules.pop(del_num)
                break
            else:
                del_num += 1

    return firewall_rules


def main():
    argument_spec = vmware_argument_spec()
    argument_spec.update(section_name=dict(type='str', required=True),
                         backup=dict(type='str', choices=['yes', 'no'], default='no'),
                         backup_options=dict(type='dict',
                                             options=dict(
                                                 filename=dict(type='str', required=True),
                                                 dir_path=dict(type='str', required=True)
                                             )),
                         restore=dict(type='dict',
                                      options=dict(
                                          file_path=dict(type='str', requried=True)
                                      )),
                         exclude_rules=dict(type='list')
                         )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    mgr_hostname = module.params['hostname']
    mgr_username = module.params['username']
    mgr_password = module.params['password']
    validate_certs = module.params['validate_certs']
    section_name = module.params['section_name']
    backup = module.params['backup']
    backup_options = module.params['backup_options']
    restore = module.params['restore']
    exclude_rules = module.params['exclude_rules']

    manager_url = 'https://{0}/api/v1'.format(mgr_hostname)

    headers = dict(Accept="application/json")
    headers['Content-Type'] = 'application/json'

    if(backup == 'yes'):
        (section_id, revision) = get_sectionid_by_section_display_name(module, manager_url, mgr_username, mgr_password,
                                                                       validate_certs, section_name)

        (rc, resp) = get_section_firewall_rules_by_section_id(module, manager_url, mgr_username, mgr_password,
                                                              validate_certs, section_id)
        firewall_rules = resp['results']
        if(exclude_rules):
            firewall_rules = exclude_firewall_rule(firewall_rules, exclude_rules)

        for firewall_rule in firewall_rules:
            for key in ('section_id', 'resource_type', 'id', '_revision'):
                del firewall_rule[key]

        tstamp = time.strftime("%Y-%m-%d@%H:%M:%S", time.localtime(time.time()))
        filename = '%s_config.%s' % (section_name, tstamp)
        backup_path = os.getcwd() + '/backup'

        if(backup_options):
            if(backup_options['filename']):
                filename = backup_options['filename']

            if(backup_options['dir_path']):
                backup_path = backup_options['dir_path']

        dest = os.path.join(backup_path, filename)
        if(not(os.path.exists(backup_path))):
            os.makedirs(backup_path)

        with open(dest, 'w') as f:
            f.write(json.dumps({"rules": firewall_rules}, indent=2, ensure_ascii=False))

        module.exit_json(changed=True, backup_path=dest)

    elif(restore):
        if(os.path.isfile(restore['file_path'])):
            with open(restore['file_path'], 'r') as f:
                restore_data = json.loads(f.read())

            (section_id, revision) = get_sectionid_by_section_display_name(module, manager_url, mgr_username,
                                                                           mgr_password, validate_certs, section_name)
            (rc, resp) = get_section_firewall_rules_by_section_id(module, manager_url, mgr_username, mgr_password,
                                                                  validate_certs, section_id)

            firewall_rules = resp['results']
            if (exclude_rules):
                firewall_rules = exclude_firewall_rule(firewall_rules, exclude_rules)

            if(firewall_rules):
                # Delete all firewall rules.
                for firewall_rule in firewall_rules:
                    try:
                        (rc, resp) = request(manager_url + '/firewall/sections/{0}/rules/{1}'.format(section_id,
                                             firewall_rule['id']), method='DELETE', url_username=mgr_username,
                                             url_password=mgr_password, validate_certs=validate_certs,
                                             ignore_errors=False)
                    except Exception as err:
                        module.fail_json(msg="%s" % err)

                (rc, revision) = get_sectionid_by_section_display_name(module, manager_url, mgr_username, mgr_password,
                                                                       validate_certs, section_name)

            # Firewall rule restore.
            for restore_firewall_rule in restore_data['rules']:
                restore_firewall_rule['_revision'] = revision

            try:
                (rc, resp) = request(manager_url + '/firewall/sections/{0}/rules?action=create_multiple'.format(
                                     section_id), data=json.dumps(restore_data), headers=headers, method='POST',
                                     url_username=mgr_username, url_password=mgr_password,
                                     validate_certs=validate_certs, ignore_errors=False)
            except Exception as err:
                module.fail_json(msg="%s" % err)

            module.exit_json(changed=True)
        else:
            module.fail_json(msg="{0} not found.".format(restore['file_path']))
    else:
        module.exit_json(changed=False)


if __name__ == '__main__':
    main()
