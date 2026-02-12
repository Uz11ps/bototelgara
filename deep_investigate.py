import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# Check ALL connections to Telegram API
print("=== Network connections to Telegram ===")
_, o, _ = c.exec_command("ss -tnp | grep -i 'api.telegram\\|149.154'")
print(o.read().decode())

# Check ALL systemd services with Python
print("=== All active Python systemd services ===")
_, o, _ = c.exec_command("systemctl list-units --type=service --state=active | grep -i python")
print(o.read().decode())

# Check ALL systemd service files referencing garabotprofi or bot
print("=== All systemd service files with bot ===")
_, o, _ = c.exec_command("grep -rl 'bot\\|garabotprofi\\|telegram' /etc/systemd/system/ 2>/dev/null")
print(o.read().decode())

# Check Docker
print("=== Docker containers ===")
_, o, _ = c.exec_command("docker ps 2>&1")
print(o.read().decode())

# Check supervisor
print("=== Supervisor ===")
_, o, _ = c.exec_command("supervisorctl status 2>&1")
print(o.read().decode())

# Check pm2
print("=== PM2 ===")
_, o, _ = c.exec_command("pm2 list 2>&1")
print(o.read().decode())

# Check ISPmanager services
print("=== ISPmanager Python processes ===")
_, o, _ = c.exec_command("ls /usr/local/mgr5/etc/cron.d/ 2>/dev/null")
print(o.read().decode())

# Check ALL running processes with open network connections
print("=== All processes with Telegram API connections ===")
_, o, _ = c.exec_command("lsof -i -P -n 2>/dev/null | grep -i '149.154\\|api.telegram'")
print(o.read().decode())

# Check for any old deployments elsewhere
print("=== Other directories with .env containing BOT_TOKEN ===")
_, o, _ = c.exec_command("find /root /home /var /opt -name '.env' -exec grep -l 'TELEGRAM_BOT_TOKEN' {} \\; 2>/dev/null")
print(o.read().decode())

c.close()
