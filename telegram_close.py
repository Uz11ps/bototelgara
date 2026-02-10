import paramiko
import time
import requests

# Read bot token
BOT_TOKEN = None
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            BOT_TOKEN = line.strip().split('=', 1)[1].strip('"').strip("'")
            break

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# 1. Stop bot
print("=== Stopping bot ===")
_, o, _ = c.exec_command("systemctl stop gora_bot")
time.sleep(3)

# 2. Call Telegram's 'close' method to force-close the server session
print("=== Calling Telegram close() API ===")
resp = requests.post(f"{API}/close")
print(f"close() result: {resp.json()}")

# 3. Wait 15 seconds (Telegram docs say 10s after close)
print("Waiting 15 seconds after close()...")
time.sleep(15)

# 4. Call deleteWebhook 
resp = requests.post(f"{API}/deleteWebhook", json={"drop_pending_updates": True})
print(f"deleteWebhook: {resp.json()}")
time.sleep(2)

# 5. Flush with getUpdates
resp = requests.post(f"{API}/getUpdates", json={"offset": -1, "timeout": 1}, timeout=10)
print(f"getUpdates flush: ok={resp.json().get('ok')}")
time.sleep(2)

# 6. Start bot
print("\n=== Starting bot ===")
_, o, _ = c.exec_command("systemctl start gora_bot")
time.sleep(10)

# 7. Check
_, o, _ = c.exec_command('journalctl -u gora_bot --since "15 seconds ago" --no-pager')
logs = o.read().decode()
print(logs)

if "TelegramConflictError" in logs:
    print("\n*** Still conflict after close() ***")
else:
    print("\n*** SUCCESS - No conflict! ***")

c.close()
