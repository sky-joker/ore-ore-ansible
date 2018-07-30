# (c) 2018, sky-joker <sky.jokerxx@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from ansible.errors import AnsibleFilterError
from jinja2 import Template
from inspect import currentframe
import ansible

def set_ansible_vars(var, *args):
    ansible_unicode = []
    for v in args:
        if(isinstance(v, ansible.parsing.yaml.objects.AnsibleUnicode)):
            ansible_unicode.append(v.__str__())

    ansible_vars = {}
    for k in currentframe().f_back.f_locals.keys():
        if(k == "context"):
            for k, v in currentframe().f_back.f_locals[k].items():
                ansible_vars.update({k:v})

    if(not(ansible_vars)):
        raise AnsibleFilterError("Error not found context key in frame object")

    template = Template(str(var))
    return template.render(ansible_vars)

class FilterModule(object):
    def filters(self):
        return {
            'set_ansible_vars': set_ansible_vars
        }
