import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# Wait 60 seconds and then check
print("Waiting 60 seconds to see if conflict resolves...")
time.sleep(60)

print("=== Bot logs (last 15 lines) ===")
_, o, _ = c.exec_command('journalctl -u gora_bot --since "2 minutes ago" --no-pager')
logs = o.read().decode()
print(logs)

# Check if there are any successful polling messages (no ERROR lines in recent logs)
if "TelegramConflictError" in logs:
    # Count conflict errors in last 2 minutes
    conflict_count = logs.count("TelegramConflictError")
    print(f"\nConflict errors in last 2 min: {conflict_count}")
    
    # Check if bot is still active
    _, o, _ = c.exec_command('systemctl is-active gora_bot')
    print(f"Bot status: {o.read().decode().strip()}")
else:
    print("\nNo conflict errors - bot is working!")

c.close()
