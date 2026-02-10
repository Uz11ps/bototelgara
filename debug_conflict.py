import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# Check ALL python processes
print("=== ALL python processes ===")
_, o, _ = c.exec_command("ps aux | grep python | grep -v grep")
print(o.read().decode())

# Check for any auto_deploy or other scripts
print("=== Crontab ===")
_, o, _ = c.exec_command("crontab -l 2>&1")
print(o.read().decode())

# Check for screen/tmux sessions
print("=== Screen sessions ===")
_, o, _ = c.exec_command("screen -ls 2>&1")
print(o.read().decode())

print("=== Tmux sessions ===")
_, o, _ = c.exec_command("tmux ls 2>&1")
print(o.read().decode())

# Check systemd services related to bot
print("=== Systemd services with 'gora' ===")
_, o, _ = c.exec_command("systemctl list-units --type=service | grep -i gora")
print(o.read().decode())

# Check if auto_deploy is running
print("=== Any auto_deploy processes ===")
_, o, _ = c.exec_command("ps aux | grep auto_deploy | grep -v grep")
print(o.read().decode())

# Check if there's another bot token file or old deployment
print("=== Other Python projects ===")
_, o, _ = c.exec_command("find /root -maxdepth 2 -name '*.py' -path '*bot*' 2>/dev/null | head -20")
print(o.read().decode())

c.close()
