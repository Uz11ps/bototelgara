import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=20)

def run(cmd):
    print(f">>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', 'ignore')
    err = stderr.read().decode('utf-8', 'ignore')
    if out:
        print(out)
    return out, err

# Check for other bot instances
print('=== CHECKING FOR OTHER BOT INSTANCES ===')
run('ls -la /root/')
run('systemctl list-units --type=service --all | grep -i bot || echo "No bot services found"')
run('ps aux | grep python | grep -v grep')

# Stop all bots
print('\n=== STOPPING ALL BOT INSTANCES ===')
run('systemctl stop gora_bot')
run('pkill -9 -f "bot.main" || true')
run('pkill -9 -f "python.*bot" || true')
run('pkill -9 -f "aiogram" || true')

time.sleep(2)

print('\n=== CHECKING PROCESSES ===')
out, _ = run('ps aux | grep -E "bot.main|gora_bot|aiogram" | grep -v grep')
if not out.strip():
    print('No bot processes running - GOOD!')

# Do NOT call Telegram close API - it is rate limited
print('\n=== WAITING 30 SECONDS ===')
time.sleep(30)

print('\n=== STARTING BOT ===')
run('systemctl start gora_bot')
time.sleep(10)

print('\n=== CHECKING STATUS ===')
run('systemctl status gora_bot --no-pager -l')

print('\n=== CHECKING LOGS ===')
run('journalctl -u gora_bot -n 10 --no-pager')

ssh.close()
