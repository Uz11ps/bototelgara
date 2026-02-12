import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# Kill ALL python bot.main processes
print("=== Killing ALL bot processes ===")
_, o, _ = c.exec_command("pkill -9 -f 'bot.main'")
time.sleep(2)

# Make sure they're dead
_, o, _ = c.exec_command("pgrep -f 'bot.main'")
remaining = o.read().decode().strip()
print(f"Remaining bot processes: '{remaining}'")

# Wait for Telegram to release the connection
print("Waiting 5s for Telegram to release connection...")
time.sleep(5)

# Start fresh
print("=== Starting bot service ===")
_, o, e = c.exec_command("systemctl start gora_bot")
time.sleep(3)

# Check status
_, o, _ = c.exec_command('systemctl is-active gora_bot')
status = o.read().decode().strip()
print(f"Bot service: {status}")

# Check logs
print("\n=== Bot logs (last 15 lines) ===")
_, o, _ = c.exec_command('journalctl -u gora_bot -n 15 --no-pager')
print(o.read().decode())

c.close()
print("Done!")
