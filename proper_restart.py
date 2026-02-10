import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# Stop bot completely
print("=== Stopping bot service ===")
_, o, _ = c.exec_command("systemctl stop gora_bot")
time.sleep(2)
_, o, _ = c.exec_command("pkill -9 -f 'bot.main'")
time.sleep(1)

# Verify dead
_, o, _ = c.exec_command("pgrep -c -f 'bot.main'")
count = o.read().decode().strip()
print(f"Remaining processes: {count}")

# Wait 30 seconds for Telegram's long-polling to expire
print("Waiting 30 seconds for Telegram long-polling to expire...")
time.sleep(30)

# Start fresh
print("Starting bot...")
_, o, _ = c.exec_command("systemctl start gora_bot")
time.sleep(8)

# Check logs
print("\n=== Bot logs ===")
_, o, _ = c.exec_command('journalctl -u gora_bot --since "30 seconds ago" --no-pager')
print(o.read().decode())

c.close()
print("Done!")
