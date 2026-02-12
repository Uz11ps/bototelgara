import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# Gracefully stop (SIGTERM, let aiogram clean up)
print("=== Gracefully stopping bot ===")
_, o, _ = c.exec_command("systemctl stop gora_bot")
# Wait for graceful shutdown (up to 30s)
time.sleep(5)

# Check if stopped
_, o, _ = c.exec_command("systemctl is-active gora_bot")
status = o.read().decode().strip()
print(f"Bot status after stop: {status}")

# Check no processes remain
_, o, _ = c.exec_command("pgrep -f 'bot.main'")
remaining = o.read().decode().strip()
if remaining:
    print(f"Remaining processes: {remaining}, sending SIGTERM")
    _, o, _ = c.exec_command("kill " + remaining.replace('\n', ' '))
    time.sleep(5)
else:
    print("No remaining processes")

# Wait a FULL MINUTE for any Telegram server-side state to clear
print("Waiting 60 seconds for Telegram to fully release...")
time.sleep(60)

# Start bot
print("=== Starting bot ===")
_, o, _ = c.exec_command("systemctl start gora_bot")
time.sleep(10)

# Check logs
_, o, _ = c.exec_command('journalctl -u gora_bot --since "15 seconds ago" --no-pager')
logs = o.read().decode()
print(logs)

if "TelegramConflictError" in logs:
    print("\n*** Still conflict ***")
    # Wait another 30s and check
    time.sleep(30)
    _, o, _ = c.exec_command('journalctl -u gora_bot --since "15 seconds ago" --no-pager')
    logs2 = o.read().decode()
    if "TelegramConflictError" not in logs2:
        print("Conflict resolved after additional wait!")
    else:
        print("Persistent conflict. Will try getMe to verify token is valid...")
        _, o, _ = c.exec_command(f"curl -s http://localhost:8000/api")
        print(f"API: {o.read().decode()[:100]}")
else:
    print("\n*** No conflict - bot is polling cleanly! ***")

c.close()
