import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=20)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', 'ignore')
    err = stderr.read().decode('utf-8', 'ignore')
    if out:
        print(out)
    if err:
        print("STDERR:", err)
    return out

# Stop bot
print("=== Stopping bot ===")
run("systemctl stop gora_bot")
run("pkill -9 -f 'bot.main' || true")

# Log out from Telegram completely
print("\n=== Logging out from Telegram ===")
run("curl -s 'https://api.telegram.org/bot8500302975:AAEkZs54gdwisQZKcxyzm9VuVVDYuEF4Tgo/logOut'")
run("curl -s 'https://api.telegram.org/bot8500302975:AAEkZs54gdwisQZKcxyzm9VuVVDYuEF4Tgo/deleteWebhook?drop_pending_updates=true'")

print("\n=== Waiting 5 minutes for Telegram to clear all sessions ===")
for i in range(300, 0, -30):
    print(f"  {i} seconds remaining...")
    time.sleep(30)

# Start bot
print("\n=== Starting bot ===")
run("systemctl start gora_bot")
time.sleep(10)

# Check the logs
print("\n=== Bot logs (last 30 lines) ===")
run("journalctl -u gora_bot -n 30 --no-pager")

print("\n=== Bot status ===")
run("systemctl status gora_bot --no-pager")

ssh.close()
