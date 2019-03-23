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

DOCUMENTATION = '''
module: vmware_guest_register_operation
short_description: VM inventory registration operation
author:
  - sky-joker (@sky-jocker)
version_added: ''
description:
  - This module can register or delete VMs in the inventory.
requirements:
  - python >= 2.7
  - PyVmomi
options:
  folder:
    description:
    - Description folder, absolute path of the target folder.
    - The folder should include the datacenter. ESX's datacenter is ha-datacenter.
    - This parameter is case sensitive.
    - This parameter is required, while deploying new virtual machine. version_added 2.5.
    - 'Examples:'
    - '   folder: /ha-datacenter/vm'
    - '   folder: ha-datacenter/vm'
    - '   folder: /datacenter1/vm'
    - '   folder: datacenter1/vm'
    - '   folder: /datacenter1/vm/folder1'
    - '   folder: datacenter1/vm/folder1'
    - '   folder: /folder1/datacenter1/vm'
    - '   folder: folder1/datacenter1/vm'
    - '   folder: /folder1/datacenter1/vm/folder2'
    default: /ha-datacenter/vm
  name:
    description:
    - Specify VM name to be registered in the inventory.
  esxi_hostname:
    description:
    - The ESXi hostname where the virtual machine will run.
    - This parameter is case sensitive.
  template:
    description:
    - Whether to register VM as a template.
    default: False
  path:
    description:
    - Specify the path of vmx file.
    - 'Examples:'
    - '    [datastore01] vm/vm.vmx'
    - '    [datastore01] vm/vm.vmtx'
  pool:
    description:
    - Specify resource pool name.
    default: Resources
  state:
    description:
    - Specify the state the virtual machine should be in.
    - if set to C(present), register VM in inventory.
    - if set to C(absent), unregister VM from inventory.
    default: present
extends_documentation_fragment: vmware.documentation
'''

EXAMPLES = '''
- name: Register VM to inventory
  vmware_guest_register_operation:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    validate_certs: no
    folder: "DC/vm"
    esxi_hostname: "{{ esxi_hostname }}"
    name: "{{ vm_name }}"
    template: no
    path: "[datastore1] vm/vm.vmx"
    state: present

- name: UnRegister VM from inventory
  vmware_guest_register_operation:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    validate_certs: no
    folder: "DC/vm"
    name: "{{ vm_name }}"
    state: absent
'''

try:
    from pyVmomi import vim, vmodl
    HAS_PYVMOMI = True
except ImportError:
    HAS_PYVMOMI = False

from ansible.module_utils.vmware import PyVmomi, vmware_argument_spec, find_resource_pool_by_name, find_vm_by_name
from ansible.module_utils.basic import AnsibleModule


class VMwareGuestRegisterOperation(PyVmomi):
    def __init__(self, module):
        super(VMwareGuestRegisterOperation, self).__init__(module)
        self.folder = module.params["folder"]
        self.name = module.params["name"]
        self.esxi_hostname = module.params["esxi_hostname"]
        self.path = module.params["path"]
        self.template = module.params["template"]
        self.pool = module.params["pool"]
        self.state = module.params["state"]

    def execute(self):
        result = dict(changed=False)

        folder_obj = self.content.searchIndex.FindByInventoryPath(inventoryPath="%s" % self.folder)
        if(not(folder_obj)):
            self.module.fail_json(msg="folder %s not found." % self.folder)

        if(self.state == "present"):
            if(find_vm_by_name(self.content, self.name)):
                self.module.exit_json(**result)

            host_obj = self.find_hostsystem_by_name(self.esxi_hostname)
            if(not(host_obj)):
                self.module.fail_json(msg="host %s not found." % self.host)

            resource_pool_obj = find_resource_pool_by_name(self.content, self.pool)
            if(not(resource_pool_obj)):
                self.module.fail_json(msg="resource pool %s not found." % self.pool)

            try:
                folder_obj.RegisterVM_Task(path=self.path, name=self.name, asTemplate=self.template,
                                           pool=resource_pool_obj, host=host_obj)
            except Exception as e:
                self.module.fail_json(msg="%s" % e)

            result.update(changed=True)
            self.module.exit_json(**result)

        else:
            vm_obj = find_vm_by_name(self.content, self.name, folder=folder_obj)
            if(vm_obj and vm_obj.runtime.powerState == "poweredOff"):
                try:
                    vm_obj.UnregisterVM()
                except Exception as e:
                    self.module.fail_json(msg="%s" % e)
                result.update(changed=True)
                self.module.exit_json(**result)

            elif(vm_obj and vm_obj.runtime.powerState != "poweredOff"):
                self.module.fail_json(msg="Virtual machine %s has not been powered off" % self.name)

            else:
                self.module.exit_json(**result)


def main():
    argument_spec = vmware_argument_spec()
    argument_spec.update(folder=dict(type="str", default="/ha-datacenter/vm"),
                         name=dict(type="str", required=True),
                         esxi_hostname=dict(type="str"),
                         path=dict(type="str", required=True),
                         template=dict(type="bool", default=False),
                         pool=dict(type="str", default="Resources"),
                         state=dict(type="str", default="present", cohices=["present", "absent"]))

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    vmware_guest_register_operation = VMwareGuestRegisterOperation(module)
    vmware_guest_register_operation.execute()


if __name__ == "__main__":
    main()
