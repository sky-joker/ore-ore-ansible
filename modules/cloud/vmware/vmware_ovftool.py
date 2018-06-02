#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, sky_jokerxx
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
module: vmware_ovftool
short_description: Download or deploy ovf.
description:
  - Module to download or deploy ovf.
requirements:
  - python >= 2.6
  - PyVmomi
  - requests
options:
  name:
    description:
      - The virtual machine name.
    required: True
  path:
    description:
      - Local directory path.
    required: True
  datacenter:
    description:
      - The datacenter hosting the virtual machine.
    default: ha-datacenter
  compute_resource:
    description:
      - If deploy to compute resource, requires compute resource name.(host or cluster name)
  resource_pool:
    description:
      - If deploy to resource pool, requires resource pool name.
  datastore:
    description:
      - Data store name to save virtual machine.
  folder:
    description:
      - Path to folder to deploy virtual machine.
    default: /vm
  disk_type:
    description:
      - Type of vmdk.(see diskProvisioning: https://goo.gl/KCBTP4)
    default: thin
  method:
    description:
      - ovf download or deploy.
    choices:
      - download
      - deploy
    required: True
'''

EXAMPLES = '''
---
- name: OVF Download Task.
  vmware_ovftool:
    hostname: vCenter or ESXi
    username: Username
    password: Secret
    validate_certs: no
    method: download
    name: devel # myVMName
    path: ./devel # ovf download to local path(full or current directory path)

- name: OVF Deploy Task.
  vmware_ovftool:
    hostname: vCenter or ESXi
    username: Username
    password: Secret
    validate_certs: no
    method: deploy
    compute_resource: esxi-07.local
    name: new_devel
    path: ./devel
    datastore: datastore1

- name: OVF Deploy Task.
  vmware_ovftool:
    hostname: vCenter
    username: Username
    password: Secret
    validate_certs: no
    method: deploy
    datacenter: DC
    compute_resource: Cluster
    name: new_devel
    path: ./devel
    folder: /vm/example
    datastore: NFS
    
- name: OVF Deploy Task.
  vmware_ovftool:
    hostname: vCenter
    username: Username
    password: Secret
    validate_certs: no
    method: deploy
    datacenter: DC
    resource_pool: example
    name: new_devel
    path: ./devel
    datastore: NFS
'''

try:
    from pyVmomi import vim, vmodl
    HAS_PYVMOMI = True
except ImportError:
    HAS_PYVMOMI = False

from ansible.module_utils.vmware import find_obj, connect_to_api, vmware_argument_spec
from ansible.module_utils.basic import AnsibleModule
import os
import threading
import re
import time
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class VMwareOvfTool():
    def __init__(self, module):
        self.module = module
        self.name = module.params["name"]
        self.method = module.params["method"]
        self.datacenter = module.params["datacenter"]
        self.path = module.params["path"]
        self.compute_resource = module.params["compute_resource"]
        self.resource_pool = module.params["resource_pool"]
        self.datastore = module.params["datastore"]
        self.folder = module.params["folder"]
        self.disk_type = module.params["disk_type"]
        self.content = connect_to_api(module)

    def execute(self):
        method = {
            'download': self.download,
            'deploy': self.deploy
        }
        method[self.method]()

    def deploy(self):
        result = dict(changed=False)

        # Thread class
        class deployThread(threading.Thread):
            def __init__(self):
                threading.Thread.__init__(self)

            def run(self):
                url = self.deviceUrl.url
                if (re.search(r"\*", url)): url = url.replace("*", self.host)
                file_path = os.path.join(self.path, self.targetId)

                headers = {"Content-Type": "application/x-vnd.vmware-streamVmdk"}
                requests.post(url, headers=headers, data=open(file_path, 'rb'), verify=self.ssl_verify)

        # Check exist of directory path.
        if (not (os.path.isdir(self.path))): self.module.fail_json(msg="%s not found" % self.path)

        # Search of Managed Objects.
        datastore = find_obj(self.content, [vim.Datastore], self.datastore)
        if(datastore == None): self.module.fail_json(msg="%s not found" % self.datastore)
        folder = self.content.searchIndex.FindByInventoryPath("/%s/%s" % (self.datacenter, self.folder))
        if(folder == None): self.module.fail_json(msg="/%s/%s not found. There is no datacenter or folder, or both." % (self.datacenter, self.folder))
        if(self.resource_pool):
            resource_pool = find_obj(self.content, [vim.ResourcePool], self.resource_pool)
            if(resource_pool == None): self.module.fail_json(msg="%s not found" % self.resource_pool)
        elif(self.compute_resource):
            compute_resource = find_obj(self.content, [vim.ComputeResource], self.compute_resource)
            if(compute_resource == None): self.module.fail_json(msg="%s not found" % self.compute_resource)
            resource_pool = compute_resource.resourcePool
        else:
            self.module.fail_json(msg="Please specify resource_pool or compute_resource")

        # Get file list related to ovf.
        files = os.listdir(self.path)

        # Read ovf file.
        ovf_file_path = os.path.join(self.path, list(filter(lambda x: re.match(r".*\.ovf$", x), files))[0])
        if(os.path.isfile(ovf_file_path)):
            with open(ovf_file_path, "r") as f:
                ovf_file = f.read()
        else:
            self.module.fail_json(msg="%s not found" % ovf_file_path)

        # Import ovf.
        spec_params = vim.OvfManager.CreateImportSpecParams()
        spec_params.entityName = self.name
        spec_params.diskProvisioning = self.disk_type
        ovf_manager = self.content.ovfManager
        ovf_import_spec = ovf_manager.CreateImportSpec(ovf_file,
                                                       resource_pool,
                                                       datastore,
                                                       spec_params)
        lease = resource_pool.ImportVApp(ovf_import_spec.importSpec,
                                         folder)

        while True:
            if (lease.state == vim.HttpNfcLease.State.ready): break
            elif(lease.state == vim.HttpNfcLease.State.error): self.module.fail_json(msg="ovf import state error")
            time.sleep(1)

        threads = []
        for deviceUrl in lease.info.deviceUrl:
            if (deviceUrl.targetId):
                t = deployThread()
                t.host = self.module.params["hostname"]
                t.ssl_verify = self.module.params["validate_certs"]
                t.path = self.path
                t.deviceUrl = deviceUrl
                t.targetId = deviceUrl.targetId
                t.start()
                threads.append(t)

        # Check Threads.
        while True:
            if (threads):
                for t in threads:
                    if (not (t.is_alive())):
                        lease.HttpNfcLeaseProgress(percent=int(100 / len(threads)))
                        threads.remove(t)
                    else:
                        time.sleep(1)
            else:
                break

        lease.HttpNfcLeaseComplete()
        self.module.exit_json(**result)

    def download(self):
        ovf_files = []
        result = dict(changed=False)

        # Thread class.
        class downloadThread(threading.Thread):
            def __init__(self):
                threading.Thread.__init__(self)

            def run(self):
                url = self.deviceUrl.url
                if(re.search(r"\*", url)): url = url.replace("*", self.host)
                file_name = url.split("/").pop()
                save_path = os.path.join(self.path, file_name)

                headers = {"Content-Type": "application/x-vnd.vmware-streamVmdk"}
                r = requests.get(url, headers=headers  , stream=True, verify=self.ssl_verify)
                if(r.status_code == 200):
                    total_byte = 0
                    with open(save_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=2048):
                            if(chunk):
                                f.write(chunk)
                                f.flush()
                            total_byte += len(chunk)

                    ovf_file = vim.OvfManager.OvfFile()
                    ovf_file.deviceId = self.deviceUrl.key
                    ovf_file.path = self.deviceUrl.targetId
                    ovf_file.size = total_byte
                    ovf_files.append(ovf_file)

        # Check exist of directory path.
        if(not(os.path.isdir(self.path))): self.module.fail_json(msg="%s not found" % self.path)

        # Get VirtualMachine obj.
        obj = find_obj(self.content, [vim.VirtualMachine], self.name)
        if(obj == None): self.module.fail_json(msg="%s not found" % self.name)

        # Export ovf.
        lease = obj.ExportVm()
        while True:
            if(lease.state == vim.HttpNfcLease.State.ready): break
            elif(lease.state == vim.HttpNfcLease.State.error): self.module.fail_json(msg="ovf export state error")
            time.sleep(1)

        threads = []
        for deviceUrl in lease.info.deviceUrl:
            if(deviceUrl.targetId):
                t = downloadThread()
                t.host = self.module.params["hostname"]
                t.ssl_verify = self.module.params["validate_certs"]
                t.path = self.path
                t.deviceUrl = deviceUrl
                t.start()
                threads.append(t)

        # Check Threads.
        while True:
            if(threads):
                for t in threads:
                    if(not(t.is_alive())):
                        lease.HttpNfcLeaseProgress(percent=int(100 / len(threads)))
                        threads.remove(t)
                    else:
                        time.sleep(1)
            else:
                break

        # Create of ovf file.
        ovf_manager = self.content.ovfManager
        ovf_parameters = vim.OvfManager.CreateDescriptorParams()
        ovf_parameters.name = obj.name
        ovf_parameters.ovfFiles = ovf_files
        vm_descriptor_result = ovf_manager.CreateDescriptor(obj=obj, cdp=ovf_parameters)
        save_path = os.path.join(self.path, "%s.ovf" % obj.name)
        with open(save_path, "w") as f:
            f.writelines(vm_descriptor_result.ovfDescriptor)

        # ovf download finish.
        lease.HttpNfcLeaseComplete()
        self.module.exit_json(**result)

def main():
    argument_spec = vmware_argument_spec()
    argument_spec.update(name=dict(required=True, type="str"),
                         path=dict(required=True, type="str"),
                         datacenter=(dict(default="ha-datacenter", type="str")),
                         compute_resource=dict(default=None, type="str"),
                         resource_pool=dict(default=None, type="str"),
                         datastore=dict(default="datastore1", type="str"),
                         folder=dict(default="/vm", type="str"),
                         disk_type=dict(default="thin", type="str"),
                         method=dict(required=True, choices=["download", "deploy"], type="str"))

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    if not HAS_PYVMOMI:
        module.fail_json(msg='pyvmomi python library not found')

    vmware_ovf_tool = VMwareOvfTool(module)
    vmware_ovf_tool.execute()

if __name__ == "__main__":
    main()