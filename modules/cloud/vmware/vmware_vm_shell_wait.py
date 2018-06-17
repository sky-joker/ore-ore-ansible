#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, sky_joker
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
module: vmware_vm_shell_wait
short_description: Wait for processing of executed command
description:
    - Wait for processing of commands executed by vmware_vm_shell module.
    - This module supports only processes executed by vmware_vm_shell.
requirements:
    - python >= 2.6
    - PyVmomi
options:
    datacenter:
        description:
            - The datacenter hosting the virtual machine.
            - If set, it will help to speed up virtual machine search.
    cluster:
        description:
            - The cluster hosting the virtual machine.
            - If set, it will help to speed up virtual machine search.
    folder:
        description:
            - Destination folder, absolute or relative path to find an existing guest or create the new guest.
            - The folder should include the datacenter. ESX's datacenter is ha-datacenter
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
            - '   folder: vm/folder2'
            - '   folder: folder2'
        default: /vm
        version_added: "2.4"
    vm_id:
        description:
            - Name of the virtual machine to work with.
        required: True
    vm_username:
        description:
             - The user to login-in to the virtual machine.
        required: True
    vm_password:
        description:
            - The password used to login-in to the virtual machine.
        required: True
    vm_shell:
        description:
            - The absolute path to the program to start.
            - On Linux, shell is executed via bash.
        required: True
    vm_shell_args:
        description:
            - The argument to the program.
    check_interval:
        description:
            - Specify the process check interval in seconds.
        default: 1
    time_out:
        description:
            - Specify process check count.
            - If it exceeds the check count, the check processing is stopped.
'''

EXAMPLES = '''
---
- vmware_vm_shell_wait:
    hostname: vCenter or ESXi
    username: username
    password: secret
    validate_certs: no
    vm_id: devel # myVMName
    vm_username: root
    vm_password: secret
    vm_shell: /root/loop.sh
    vm_shell_args: 5

# Searching vm from a folder.
- vmware_vm_shell_wait:
    hostname: vCenter or ESXi
    username: username
    password: secret
    datacenter: datacenter
    folder: /datacenter_name/vm
    vm_id_type: inventory_path
    validate_certs: no
    vm_id: devel # myVMName
    vm_username: root
    vm_password: secret
    vm_shell: /root/loop.sh
    vm_shell_args: 5

# Confirm process execution three times.
- vmware_vm_shell_wait:
    hostname: vCenter or ESXi
    username: username
    password: secret
    validate_certs: no
    vm_id: devel # myVMName
    vm_username: root
    vm_password: secret
    vm_shell: /root/loop.sh
    vm_shell_args: 5
    time_out: 3
'''

try:
    from pyVmomi import vim, vmodl
    HAS_PYVMOMI = True
except ImportError:
    HAS_PYVMOMI = False

from ansible.module_utils.vmware import find_obj, connect_to_api, vmware_argument_spec, find_datacenter_by_name, find_cluster_by_name, find_vm_by_id
from ansible.module_utils.basic import AnsibleModule
import time
import re

class VMwareVMShellCheck():
    def __init__(self, module):
        self.module = module
        self.datacenter_name = module.params["datacenter"]
        self.cluster_name = module.params["cluster"]
        self.folder = module.params["folder"]
        self.vm_id = module.params["vm_id"]
        self.vm_id_type = module.params["vm_id_type"]
        self.vm_username = module.params["vm_username"]
        self.vm_password = module.params["vm_password"]
        self.vm_shell = module.params["vm_shell"]
        self.vm_shell_args = module.params["vm_shell_args"]
        self.check_interval = module.params["check_interval"]
        self.time_out = module.params["time_out"]
        self.content = connect_to_api(module)

    def execute(self):
        result = dict(changed=False)
        check_count = 0

        # search for vm
        datacenter = None
        if self.datacenter_name:
            datacenter = find_datacenter_by_name(self.content, self.datacenter_name)
            if not datacenter:
                self.module.fail_json(changed=False, msg="Unable to find %(datacenter)s datacenter" % self.module.params)

        cluster = None
        if self.cluster_name:
            cluster = find_cluster_by_name(self.content, self.cluster_name, self.datacenter)
            if not cluster:
                self.module.fail_json(changed=False, msg="Unable to find %(cluster)s cluster" % self.module.params)

        if self.module.params['vm_id_type'] == 'inventory_path':
            vm = find_vm_by_id(self.content, vm_id=self.module.params['vm_id'], vm_id_type="inventory_path", folder=self.folder)
        else:
            vm = find_vm_by_id(self.content, vm_id=self.module.params['vm_id'], vm_id_type=self.module.params['vm_id_type'],
                               datacenter=datacenter, cluster=cluster)
        if(vm):
            guest_auth = vim.vm.guest.NamePasswordAuthentication()
            guest_auth.username = self.vm_username
            guest_auth.password = self.vm_password
            while True:
                try:
                    r = self.content.guestOperationsManager.processManager.ListProcessesInGuest(
                        vm=vm,
                        auth=guest_auth
                    )
                except Exception as e:
                    self.module.fail_json(msg=str(e))

                pid_num = [x for x in r if (re.search(r'%s.*%s' % (self.vm_shell, self.vm_shell_args), x.cmdLine))]
                if (pid_num):
                    exitCode = pid_num.pop().exitCode
                    if (isinstance(exitCode, int)):
                        if (exitCode == 0):
                            self.module.exit_json(**result)
                        else:
                            self.module.fail_json(msg="Processing failed")

                if(self.time_out):
                    check_count += 1
                    if(check_count == self.time_out):
                        self.module.fail_json(msg="Processing was not completed within the time")

                time.sleep(self.check_interval)

        else:
            self.module.fail_json(msg="Unable to find virtual machine")

def main():
    argument_spec = vmware_argument_spec()
    argument_spec.update(datacenter=dict(type="str"),
                         cluster=dict(type="str"),
                         folder=dict(type="str", default="/vm"),
                         vm_id=dict(required=True, type="str"),
                         vm_id_type=dict(default='vm_name', type='str', choices=['inventory_path', 'uuid', 'dns_name', 'vm_name']),
                         vm_username=dict(required=True, type="str"),
                         vm_password=dict(required=True, type="str", no_log=True),
                         vm_shell=dict(required=True, type="str"),
                         vm_shell_args=dict(type="str"),
                         check_interval=dict(type=int, default=1),
                         time_out=dict(type=int))

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    if(not(HAS_PYVMOMI)):
        module.fail_json(msg="pyvmomi is required for this module")

    vmware_vm_shell_check = VMwareVMShellCheck(module)
    vmware_vm_shell_check.execute()

if __name__ == "__main__":
    main()
