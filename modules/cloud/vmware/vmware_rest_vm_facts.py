#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, sky_joker
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
module: vmware_rest_vm_facts
short_description: Return basic facts pertaining of vm from vSphere rest api
author:
  - sky-joker (@sky-jocker)
version_added: ''
description:
    - Return basic facts pertaining to a vSphere virtual machine guest.
requirements:
    - python >= 2.6
    - vSphere Automation SDK
options:
    hostname:
      description:
        - The hostname or IP address of the vSphere vCenter server.
    password:
      description:
        - The password of the vSphere vCenter server.
    username:
      description:
        - The username of the vSphere vCenter server.
    validate_certs:
      description:
        - Allows connection when SSL certificates are not valid. Set to false when certificates are not trusted.
        - If the value is not specified in the task, the value of environment variable VMWARE_VALIDATE_CERTS will be used instead.
      default: True
    protocol:
      description:
        - Specify the https or http.
      choices:
        - https
        - http
    name:
      description:
        - The virtual machine name.
        - If name is not specified, all the VM information is returned
extends_documentation_fragment: vmware_rest_client.documentation
'''

EXAMPLES = '''
---
- name: Get the devel facts.
  hosts: localhost
  gather_facts: no
  tasks:
    - vmware_rest_vm_facts:
        hostname: vcenter.local
        username: administrator@vsphere.local
        password: secret
        validate_certs: no
        protocol: https
        name: devel
      register: r

- name: Get all vm facts.
  hosts: localhost
  gather_facts: no
  tasks:
    - vmware_rest_vm_facts:
        hostname: vcenter.local
        username: administrator@vsphere.local
        password: secret
        validate_certs: no
        protocol: https
      register: r
'''

from ansible.module_utils.vmware_rest_client import VmwareRestClient
from ansible.module_utils.basic import AnsibleModule
try:
    from com.vmware import vcenter_client
except ImportError:
    pass


def main():
    result = dict(changed=False)
    argument_spec = VmwareRestClient.vmware_client_argument_spec()
    argument_spec.update(name=dict(type="str"))

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    try:
        obj = VmwareRestClient(module)
        vm_svc = vcenter_client.VM(obj.connect)
    except Exception as e:
        module.fail_json(msg=str(e))

    vm_name = module.params["name"]
    if(vm_name):
        names = set([vm_name])
        vm = vm_svc.list(vcenter_client.VM.FilterSpec(names=names))
        r = list(map(lambda x: x.to_dict(), vm))
        if(len(r) > 0):
            result["virtual_machines"] = vm_svc.get(r[0]["vm"]).to_dict()
            module.exit_json(**result)
        else:
            module.fail_json(msg="%s not found." % vm_name)
    else:
        vms = vm_svc.list()
        r = list(map(lambda x: x.to_dict(), vms))

        r_array = []
        for vm in r:
            r_array.append(vm_svc.get(vm["vm"]).to_dict())

        result["virtual_machines"] = r_array
        module.exit_json(**result)


if __name__ == "__main__":
    main()