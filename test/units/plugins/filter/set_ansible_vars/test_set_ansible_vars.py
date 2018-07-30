#!/usr/bin/env python3
from collections import defaultdict
import json
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def main():
    # Ansible Tower
    url = "https://192.168.0.234/api/v1/job_templates/11/launch/"
    user = "admin"
    passwd = "redhat"

    # AWX
    #url = ""
    #user = "admin"
    #passwd = "password"

    headers = {"Content-Type": "application/json"}
    nested_dict = lambda: defaultdict(nested_dict)
    data = nested_dict()
    data["extra_vars"]["msg1"] = "{{ message1 }}"
    data["extra_vars"]["msg2"] = "{{ message2.msg }}"
    data["extra_vars"]["msg3"] = "{{ message3 }}"
    data["extra_vars"]["msg4"] = {"msg1": "{{ message1 }}", "msg2": "{{ message2.msg }}", "msg3": "{{ message3 }}"}
    data["extra_vars"]["msg5"] = ["{{ message1 }}", "{{ message2 }}", "{{ message3 }}"]
    data["extra_vars"]["msg6"] = "{{ message4 }}"
    data["extra_vars"]["msg7"] = "{{ shell_ret.stdout }}"

    r = requests.post(url,
                      headers=headers,
                      auth=(user, passwd),
                      data=json.dumps(data),
                      verify=False)

    print(r.status_code)
    print(json.dumps(json.loads(r.text), indent=2))

if __name__ == "__main__":
    main()