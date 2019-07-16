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
module: vmware_guest_powered_on_operation_question
short_description: Answer questions about VM power on
author:
  - sky-joker (@sky-joker)
version_added: ''
description:
  - This module answer questions asked when the virtual machine is powered on after virtual machine copied or moved.
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
    type: str
  name:
    description:
    - Specify a VM to powered on operation.
    type: str
  answer:
    description:
    - If C(answer) is set to C(cancel), cancel answer.
    - If C(answer) is set to C(moved), answer as a moved vm.
    - If C(answer) is set to C(copied), anser as a copied vm.
    choices: [ cancel, moved, copied ]
    default: copied
    type: str
  state:
    description:
    - Specify state of the virtual machine be in.
    - 'If C(state) is set to C(poweredon) and virtual machine exists with powerstate other than powered on,
       then the specified virtual machine is powered on.'
    choices: [ poweredon ]
    default: poweredon
    type: str
extends_documentation_fragment: vmware.documentation
'''

EXAMPLES = '''
- name: test
  vmware_guest_powered_on_operation_question:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    validate_certs: no
    name: "{{ vm_name }}"
    answer: moved
    state: poweredon
'''

try:
    from pyVmomi import vim, vmodl
    HAS_PYVMOMI = True
except ImportError:
    HAS_PYVMOMI = False

from ansible.module_utils.vmware import PyVmomi, vmware_argument_spec, find_vm_by_name
from ansible.module_utils.basic import AnsibleModule


class VMwareGuestPoweredOnOperationQuestion(PyVmomi):
    def __init__(self, module):
        super(VMwareGuestPoweredOnOperationQuestion, self).__init__(module)
        self.folder = module.params["folder"]
        self.name = module.params["name"]
        self.answer = module.params["answer"]
        self.state = module.params["state"]

    def execute(self):
        result = dict(changed=False)

        folder_obj = self.content.searchIndex.FindByInventoryPath(inventoryPath="%s" % self.folder)
        if (not (folder_obj)):
            self.module.fail_json(msg="folder %s not found." % self.folder)

        answers = {
            "cancel": "0",
            "moved": "1",
            "copied": "2"
        }

        vm_obj = find_vm_by_name(self.content, self.name, folder=folder_obj)
        if(vm_obj.runtime.powerState == "poweredOff"):
            task = vm_obj.PowerOn()
            while task.info.state not in [vim.TaskInfo.State.success,
                                          vim.TaskInfo.State.error]:

                if vm_obj.runtime.question is not None:
                    question_id = vm_obj.runtime.question.id
                    if question_id not in answers.keys():
                        try:
                            vm_obj.AnswerVM(question_id, answers[self.answer])
                        except Exception as e:
                            self.module.fail_json(msg="%s" % e)

            result.update(changed=True)
            self.module.exit_json(**result)

        self.module.exit_json(**result)


def main():
    argument_spec = vmware_argument_spec()
    argument_spec.update(folder=dict(type="str", default="/ha-datacenter/vm"),
                         name=dict(type="str", required=True),
                         answer=dict(type="str", choices=["cancel", "moved", "copied"], default="copied"),
                         state=dict(type="str", choices=["poweredon"], default="poweredon"),
                         )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    vmware_guest_powere_question = VMwareGuestPoweredOnOperationQuestion(module)
    vmware_guest_powere_question.execute()


if __name__ == '__main__':
    main()
