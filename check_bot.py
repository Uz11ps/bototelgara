import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# Check service status
_, o, _ = c.exec_command('systemctl is-active gora_bot')
status = o.read().decode().strip()
print(f"Bot service status: {status}")

# Get recent logs
_, o, _ = c.exec_command('journalctl -u gora_bot -n 10 --no-pager')
logs = o.read().decode()
print("Recent logs:")
print(logs)

c.close()
