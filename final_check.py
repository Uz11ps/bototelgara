import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

time.sleep(5)

_, o, _ = c.exec_command("journalctl -u gora_bot -n 10 --no-pager --since '15 seconds ago'")
logs = o.read().decode()
print("Bot logs (last 15s):")
print(logs)

if "ConflictError" in logs:
    print("STILL CONFLICT - but bot will keep retrying")
else:
    print("NO CONFLICT - bot is running clean!")

# Test if bot can actually send messages
_, o, e = c.exec_command("cd /root/garabotprofi && ./venv/bin/python -c \"import asyncio; from aiogram import Bot; from config import get_settings; s=get_settings(); bot=Bot(token=s.bot_token); asyncio.run(bot.send_message(chat_id=5868421234, text='Test: bot is working and can send messages!')); print('Message sent!')\"")
print("\nSend test message result:")
print(o.read().decode())
err = e.read().decode()
if err:
    print("STDERR:", err)

c.close()
