FROM quay.io/ansible/default-test-container:latest
RUN ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
RUN cd /opt && \
    git clone https://github.com/ansible/ansible.git && \
    cd ansible && \
    mkdir lib/ansible/modules/salf_made/ && \
    mkdir test/units/modules/salf_made
ADD ansible_module_test.sh /opt
ADD modules /opt/ansible/lib/ansible/modules/salf_made/
RUN chmod +x /opt/ansible_module_test.sh
RUN apt-get -y install man-db