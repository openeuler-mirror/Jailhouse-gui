CURRENT_DIR=$(cd $(dirname $0); pwd)

systemctl --version > /dev/null
if [ $? != 0 ]; then
    echo "run systemctl faield."
    exit 1
fi

set -o errexit

cat > jailhouse.service <<EOF
[Unit]
Description=jailhouse rpc service

[Service]
Type=simple

User=root
ExecStart=${CURRENT_DIR}/start-server.sh start

[Install]
WantedBy=multi-user.target
EOF

cp jailhouse.service /etc/systemd/system
rm jailhouse.service

systemctl enable jailhouse
systemctl start jailhouse
