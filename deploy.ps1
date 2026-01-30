# GORA Hotel Bot Deployment Script
$SERVER_IP = "89.104.66.21"
$SERVER_USER = "root"
$REMOTE_PATH = "/root/garabotprofi"

Write-Host "--- 1. Syncing files via SCP ---"
# Note: This requires SSH key auth or password prompt
scp -r ./* ${SERVER_USER}@${SERVER_IP}:${REMOTE_PATH}

Write-Host "--- 2. Server setup (Python, venv, deps) ---"
ssh ${SERVER_USER}@${SERVER_IP} "apt update && apt install -y python3-pip python3-venv && mkdir -p ${REMOTE_PATH} && cd ${REMOTE_PATH} && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"

Write-Host "--- 3. Setting up Systemd service ---"
$SERVICE_CONTENT = "[Unit]`nDescription=GORA Telegram Bot`nAfter=network.target`n`n[Service]`nType=simple`nUser=root`nWorkingDirectory=${REMOTE_PATH}`nExecStart=${REMOTE_PATH}/venv/bin/python -m bot.main`nRestart=always`nRestartSec=5`n`n[Install]`nWantedBy=multi-user.target"
$SERVICE_CONTENT | Out-File -FilePath "./gora_bot.service" -Encoding ascii

scp ./gora_bot.service ${SERVER_USER}@${SERVER_IP}:/etc/systemd/system/gora_bot.service

ssh ${SERVER_USER}@${SERVER_IP} "systemctl daemon-reload && systemctl enable gora_bot && systemctl restart gora_bot && systemctl status gora_bot --no-pager"

Write-Host "--- Deployment Complete! ---"
