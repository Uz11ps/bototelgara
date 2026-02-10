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

# Step 1: Stop bot and kill all processes
print("=== Step 1: Stop all bot processes ===")
_, o, _ = c.exec_command("systemctl stop gora_bot")
time.sleep(2)
_, o, _ = c.exec_command("pkill -9 -f 'bot.main'")
time.sleep(2)

# Verify
_, o, _ = c.exec_command("pgrep -f 'bot.main'")
remaining = o.read().decode().strip()
print(f"Remaining processes: '{remaining}'")

# Step 2: Call getUpdates with short timeout to flush any pending connections
print("\n=== Step 2: Flush Telegram pending connections ===")
for i in range(3):
    resp = requests.post(f"{API}/getUpdates", json={"offset": -1, "timeout": 1}, timeout=10)
    result = resp.json()
    print(f"  getUpdates call {i+1}: ok={result.get('ok')}, updates={len(result.get('result', []))}")
    time.sleep(2)

# Step 3: Delete webhook just in case
print("\n=== Step 3: Delete webhook ===")
resp = requests.post(f"{API}/deleteWebhook", json={"drop_pending_updates": True})
print(f"  deleteWebhook: {resp.json()}")

# Step 4: Wait for Telegram to fully release
print("\n=== Step 4: Waiting 10 seconds ===")
time.sleep(10)

# Step 5: One final getUpdates to clear
resp = requests.post(f"{API}/getUpdates", json={"offset": -1, "timeout": 1}, timeout=10)
print(f"Final getUpdates: ok={resp.json().get('ok')}")
time.sleep(2)

# Step 6: Start bot
print("\n=== Step 6: Starting bot ===")
_, o, _ = c.exec_command("systemctl start gora_bot")
time.sleep(8)

# Step 7: Check logs
print("\n=== Step 7: Check logs ===")
_, o, _ = c.exec_command('journalctl -u gora_bot --since "15 seconds ago" --no-pager')
logs = o.read().decode()
print(logs)

if "TelegramConflictError" in logs:
    print("\n*** STILL CONFLICT - checking further ***")
    time.sleep(15)
    _, o, _ = c.exec_command('journalctl -u gora_bot --since "10 seconds ago" --no-pager')
    logs2 = o.read().decode()
    print(logs2)
    if "TelegramConflictError" not in logs2:
        print("\n*** Conflict resolved after waiting! ***")
    else:
        print("\n*** Persistent conflict - another instance exists somewhere! ***")
else:
    print("\n*** No conflict - bot is working cleanly! ***")

c.close()
print("\nDone!")
