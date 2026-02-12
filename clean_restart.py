import paramiko
import time
import requests

# First, check and clean up via Telegram API
BOT_TOKEN = None

# Read token from .env
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            BOT_TOKEN = line.strip().split('=', 1)[1].strip('"').strip("'")
            break

print(f"Bot token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")

# Check webhook info
print("\n=== Checking Telegram webhook info ===")
resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo")
info = resp.json()
print(f"Webhook URL: {info['result'].get('url', 'NONE')}")
print(f"Pending updates: {info['result'].get('pending_update_count', 0)}")
print(f"Last error: {info['result'].get('last_error_message', 'NONE')}")

# Delete webhook and drop pending updates to clean slate
print("\n=== Deleting webhook and dropping pending updates ===")
resp = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", json={"drop_pending_updates": True})
print(f"deleteWebhook result: {resp.json()}")

# Now connect to server
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# Stop bot service
print("\n=== Stopping bot service ===")
_, o, _ = c.exec_command("systemctl stop gora_bot")
time.sleep(2)

# Kill any remaining
_, o, _ = c.exec_command("pkill -9 -f 'bot.main'")
time.sleep(1)

# Verify all dead
_, o, _ = c.exec_command("pgrep -c -f 'bot.main'")
count = o.read().decode().strip()
print(f"Remaining processes: {count}")

# Wait for Telegram to fully release
print("Waiting 10 seconds for Telegram to release...")
time.sleep(10)

# Start fresh
print("\n=== Starting bot service ===")
_, o, e = c.exec_command("systemctl start gora_bot")
time.sleep(5)

# Check status
_, o, _ = c.exec_command('systemctl is-active gora_bot')
status = o.read().decode().strip()
print(f"Bot service: {status}")

# Check logs
print("\n=== Bot logs (last 10 lines) ===")
_, o, _ = c.exec_command('journalctl -u gora_bot -n 10 --no-pager')
print(o.read().decode())

c.close()
print("Done!")
