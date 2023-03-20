#! /bin/bash

set -o errexit

CURRENT_DIR=$(cd $(dirname $0); pwd)
cd ${CURRENT_DIR}

export PYTHON_ENV=$(pwd)/python-env
source python-env/bin/activate

linux_loader=/usr/local/libexec/jailhouse/linux-loader.bin
hypervisor=/lib/firmware/jailhouse.bin
if [ ! -d `dirname ${linux_loader}` ]; then
    mkdir -p `dirname ${linux_loader}`
fi

echo "create symbol link."
ln -sf ${CURRENT_DIR}/jailhouse_bin/linux-loader.bin ${linux_loader}
ln -sf ${CURRENT_DIR}/jailhouse_bin/jailhouse.bin ${hypervisor}
ln -sf ${CURRENT_DIR}/jailhouse_bin/jailhouse /usr/local/bin/jailhouse
ln -sf ${CURRENT_DIR}/ivsm-p2p-tool /usr/local/bin/ivsm-p2p-tool

# install driver
if [ "`lsmod | grep -q ivsm_p2p || echo noexit`" = "noexit" ]; then
    if [ -f ${CURRENT_DIR}/ivsm-p2p.ko ]; then
        echo "install driver module"
        insmod ${CURRENT_DIR}/ivsm-p2p.ko
    fi
fi

python server_host.py
