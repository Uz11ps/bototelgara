import paramiko
import os
import scp
import sys

# UTF-8 for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

def deploy():
    host = "89.104.66.21"
    user = "root"
    # Тщательно проверяем пароль со скриншота: 01IJHGeBMbaHr4Qj
    passwords = ["01IJHGeBMbaHr4Qj", "O1IJHGeBMbaHr4Qj"]
    remote_path = "/root/garabotprofi"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    connected = False
    for pwd in passwords:
        print(f"--- Trying connection to {host} with password... ---")
        try:
            client.connect(host, username=user, password=pwd, look_for_keys=False, allow_agent=False, timeout=15)
            print("SUCCESS: Connected!")
            connected = True
            break
        except Exception as e:
            print(f"FAILED: {str(e)}")
            continue
    
    if not connected:
        print("CRITICAL: All authentication attempts failed. Please check the password.")
        return

    try:
        print(f"Creating remote directory: {remote_path}")
        client.exec_command(f"mkdir -p {remote_path}")

        print("--- Starting file upload ---")
        with scp.SCPClient(client.get_transport()) as scp_client:
            for item in os.listdir('.'):
                if item in ['.git', '.venv', 'venv', '__pycache__', 'gora_bot.db', 'auto_deploy.py', 'deploy.ps1', 'check_shelter_connection.py', 'gora_bot.service']:
                    continue
                print(f"Uploading: {item}")
                try:
                    scp_client.put(item, remote_path, recursive=True)
                except Exception as e:
                    print(f"Warning: Error uploading {item}: {e}")

        print("--- Configuring server environment ---")
        # Combined commands for efficiency
        setup_cmd = (
            f"apt update && apt install -y python3-pip python3-venv && "
            f"cd {remote_path} && python3 -m venv venv && "
            f"./venv/bin/pip install -r requirements.txt"
        )
        
        print("Installing dependencies (this may take a minute)...")
        stdin, stdout, stderr = client.exec_command(setup_cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"Error during setup: {stderr.read().decode()}")

        print("Configuring systemd service...")
        service_content = (
            "[Unit]\nDescription=GORA Telegram Bot\nAfter=network.target\n\n"
            "[Service]\nType=simple\nUser=root\n"
            f"WorkingDirectory={remote_path}\n"
            f"ExecStart={remote_path}/venv/bin/python -m bot.main\n"
            "Restart=always\nRestartSec=5\n\n"
            "[Install]\nWantedBy=multi-user.target"
        )
        
        # Use cat to write the file safely
        client.exec_command(f"cat <<EOF > /etc/systemd/system/gora_bot.service\n{service_content}\nEOF")
        
        client.exec_command("systemctl daemon-reload && systemctl enable gora_bot && systemctl restart gora_bot")
        
        print("\n✅ DEPLOYMENT SUCCESSFUL!")
        stdin, stdout, stderr = client.exec_command("systemctl status gora_bot --no-pager")
        print(stdout.read().decode())

    finally:
        client.close()

if __name__ == "__main__":
    deploy()
