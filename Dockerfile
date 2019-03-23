FROM quay.io/ansible/default-test-container:latest
RUN ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
RUN cd /opt && \
    git clone https://github.com/ansible/ansible.git && \
    cd ansible && \
    mkdir lib/ansible/modules/salf_made/ && \
    mkdir test/units/modules/salf_made
RUN apt-get -y install man-db