import paramiko
import time
import requests

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# 1. Check bridge is running
print("=== Bridge status in logs ===")
_, o, _ = c.exec_command("journalctl -u gora_bot --since '5 minutes ago' --no-pager | grep -i bridge")
print(o.read().decode())

# 2. Test admin API endpoints
print("=== Test admin API ===")
_, o, _ = c.exec_command("curl -s http://localhost:8000/api/undelivered-admin-messages")
print(f"Undelivered messages: {o.read().decode()[:200]}")

_, o, _ = c.exec_command("curl -s http://localhost:8000/api/pending-order-notifications")
print(f"Pending notifications: {o.read().decode()[:200]}")

# 3. Check that the deployed admin_panel.py handles mini_app correctly
print("\n=== Verify admin_panel.py fix ===")
_, o, _ = c.exec_command("grep -A2 'guest_cid and guest_cid.isdigit' /root/garabotprofi/bot/handlers/admin_panel.py")
print(o.read().decode())

# 4. Check that deployed bridge handles mini_app correctly
print("=== Verify bridge fix ===")
_, o, _ = c.exec_command("grep -B1 -A2 'isdigit' /root/garabotprofi/services/bot_api_bridge.py")
print(o.read().decode())

# 5. Check that mini_app index.html has Telegram SDK
print("=== Verify Telegram SDK in mini app ===")
_, o, _ = c.exec_command("cat /root/garabotprofi/mini_app/index.html")
print(o.read().decode())

# 6. Test sending a message directly via bot API (to verify bot can SEND)
print("\n=== Test bot send_message capability ===")
BOT_TOKEN = None
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            BOT_TOKEN = line.strip().split('=', 1)[1].strip('"').strip("'")
            break

resp = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    json={"chat_id": 5868421234, "text": "Test: Bot can send messages successfully!"}
)
result = resp.json()
print(f"Send test message: ok={result.get('ok')}, error={result.get('description', 'none')}")

c.close()
print("\nDone!")
