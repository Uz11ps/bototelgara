"""Verify deployed code and fix issues on server."""
import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

print("=" * 60)
print("1. VERIFY: admin_panel.py has .isdigit() guard")
print("=" * 60)
_, o, _ = c.exec_command("grep -n 'isdigit' /root/garabotprofi/bot/handlers/admin_panel.py")
print(o.read().decode())

print("=" * 60)
print("2. VERIFY: bridge has .isdigit() guard")
print("=" * 60)
_, o, _ = c.exec_command("grep -n 'isdigit' /root/garabotprofi/services/bot_api_bridge.py")
print(o.read().decode())

print("=" * 60)
print("3. VERIFY: mini_app/index.html has Telegram SDK")
print("=" * 60)
_, o, _ = c.exec_command("grep -n 'telegram-web-app' /root/garabotprofi/mini_app/index.html")
print(o.read().decode())

print("=" * 60)
print("4. VERIFY: web_admin has undelivered-admin-messages endpoint")
print("=" * 60)
_, o, _ = c.exec_command("grep -n 'undelivered-admin-messages' /root/garabotprofi/web_admin/main.py")
print(o.read().decode())

print("=" * 60)
print("5. VERIFY: admin user 5868421234 exists")
print("=" * 60)
_, o, e = c.exec_command("cd /root/garabotprofi && ./venv/bin/python -c \"from db.session import SessionLocal; from db.models import AdminUser; db=SessionLocal(); admins=db.query(AdminUser).all(); [print(f'Admin: id={a.id} tg={a.telegram_id} name={a.full_name} active={a.is_active}') for a in admins]; db.close()\"")
print(o.read().decode())
err = e.read().decode()
if err:
    print("STDERR:", err)

print("=" * 60)
print("6. Install requests module (for Telegram cleanup)")
print("=" * 60)
_, o, e = c.exec_command("cd /root/garabotprofi && ./venv/bin/pip install requests")
print(o.read().decode())

print("=" * 60)
print("7. Clean Telegram session and restart bot")
print("=" * 60)
# Kill any rogue bot processes
_, o, _ = c.exec_command("pkill -9 -f 'bot.main' || true")
time.sleep(2)

# Clean Telegram session using aiohttp (which is already installed)
_, o, e = c.exec_command("cd /root/garabotprofi && ./venv/bin/python -c \"import requests; import os; from dotenv import load_dotenv; load_dotenv(); token=os.getenv('TELEGRAM_BOT_TOKEN'); r=requests.post(f'https://api.telegram.org/bot{token}/close'); print('close:', r.json()); r=requests.post(f'https://api.telegram.org/bot{token}/deleteWebhook', json={'drop_pending_updates': True}); print('deleteWebhook:', r.json())\"")
print(o.read().decode())
err = e.read().decode()
if err:
    print("STDERR:", err)

print("Waiting 12 seconds for Telegram to release...")
time.sleep(12)

# Restart services
_, o, _ = c.exec_command("systemctl restart gora_admin")
time.sleep(1)
_, o, _ = c.exec_command("systemctl restart gora_bot")
time.sleep(3)

print("=" * 60)
print("8. Check bot status and logs")
print("=" * 60)
_, o, _ = c.exec_command("systemctl is-active gora_bot")
print(f"Bot status: {o.read().decode().strip()}")

_, o, _ = c.exec_command("systemctl is-active gora_admin")
print(f"Admin status: {o.read().decode().strip()}")

_, o, _ = c.exec_command("journalctl -u gora_bot -n 15 --no-pager")
print("Bot logs:")
print(o.read().decode())

print("=" * 60)
print("9. Check for process conflicts")
print("=" * 60)
_, o, _ = c.exec_command("ps aux | grep 'bot.main' | grep -v grep")
print(o.read().decode())

c.close()
print("\nDone!")
