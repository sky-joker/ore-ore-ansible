#!/bin/sh
version=$1
module_dir="lib/ansible/modules/salf_made/"

cd /opt/ansible
. hacking/env-setup
for module in $(find $module_dir | grep "\.py$" | awk -F / '{print $(NF)}' | sed -e "s/\.py$//g" | grep -v "__init__") ; do
    ansible-test sanity --python $version $module
done