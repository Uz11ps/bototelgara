import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj', timeout=10)

# Wait for the bot's internal 12s delay + startup
print("Waiting 25 seconds for bot startup (includes 12s close() wait)...")
time.sleep(25)

# Check logs
print("=== Bot logs (last 20 lines) ===")
_, o, _ = c.exec_command('journalctl -u gora_bot --since "30 seconds ago" --no-pager')
logs = o.read().decode()
print(logs)

if "TelegramConflictError" in logs:
    conflict_count = logs.count("TelegramConflictError")
    print(f"\nConflict errors: {conflict_count}")
    
    # Wait more and check again
    print("Waiting 30 more seconds...")
    time.sleep(30)
    _, o, _ = c.exec_command('journalctl -u gora_bot --since "15 seconds ago" --no-pager')
    logs2 = o.read().decode()
    print(logs2)
    if "TelegramConflictError" not in logs2:
        print("\nConflict resolved!")
    else:
        print("\nStill conflicting")
else:
    print("\n*** No conflict - bot is working! ***")

c.close()
