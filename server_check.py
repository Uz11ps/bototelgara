import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# 1. Kill any rogue bot processes (not managed by systemd)
print("=== Killing rogue bot processes ===")
_, o, _ = c.exec_command("ps aux | grep 'bot.main' | grep -v grep")
procs = o.read().decode().strip()
print(f"Bot processes:\n{procs}")

# Get the PID of the systemd-managed bot
_, o, _ = c.exec_command("systemctl show gora_bot --property=MainPID --value")
main_pid = o.read().decode().strip()
print(f"\nSystemd main PID: {main_pid}")

# Kill all bot.main processes except the systemd one
_, o, _ = c.exec_command(f"pgrep -f 'bot.main' | grep -v {main_pid}")
rogue_pids = o.read().decode().strip()
if rogue_pids:
    print(f"Killing rogue PIDs: {rogue_pids}")
    for pid in rogue_pids.split('\n'):
        pid = pid.strip()
        if pid and pid != main_pid:
            c.exec_command(f"kill -9 {pid}")
    print("Killed rogue processes")
else:
    print("No rogue processes found")

# 2. Restart bot cleanly
print("\n=== Restarting bot service ===")
_, o, e = c.exec_command("systemctl restart gora_bot")
time.sleep(2)

# 3. Check service status
_, o, _ = c.exec_command('systemctl is-active gora_bot')
status = o.read().decode().strip()
print(f"Bot service: {status}")

_, o, _ = c.exec_command('systemctl is-active gora_admin')
status = o.read().decode().strip()
print(f"Admin service: {status}")

# 4. Check logs for errors
print("\n=== Bot logs (last 20 lines) ===")
_, o, _ = c.exec_command('journalctl -u gora_bot -n 20 --no-pager')
print(o.read().decode())

# 5. Check admin user
print("\n=== Checking admin user ===")
_, o, e = c.exec_command("cd /root/garabotprofi && ./venv/bin/python -c \"from db.session import SessionLocal; from db.models import AdminUser; db=SessionLocal(); admins=db.query(AdminUser).all(); [print(f'ID={a.id} TG={a.telegram_id} Name={a.full_name} Active={a.is_active}') for a in admins]; db.close()\"")
print("STDOUT:", o.read().decode())
err = e.read().decode()
if err:
    print("STDERR:", err)

# 6. Check deployed admin_panel.py has the fix
print("\n=== Checking admin_panel.py for isdigit guard ===")
_, o, _ = c.exec_command("grep -n 'isdigit' /root/garabotprofi/bot/handlers/admin_panel.py")
print(o.read().decode())

# 7. Check deployed bridge has the fix
print("=== Checking bridge for isdigit guard ===")
_, o, _ = c.exec_command("grep -n 'isdigit' /root/garabotprofi/services/bot_api_bridge.py")
print(o.read().decode())

# 8. Check index.html has Telegram SDK
print("=== Checking mini_app index.html for Telegram SDK ===")
_, o, _ = c.exec_command("grep -n 'telegram-web-app' /root/garabotprofi/mini_app/index.html")
print(o.read().decode())

c.close()
print("Done!")
