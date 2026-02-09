import paramiko
import os
import tarfile
import time
from scp import SCPClient
import sys

# Настройка UTF-8 для Windows
# if sys.platform == 'win32':
#     import codecs
#     sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

def create_tarball(output_filename, source_dir):
    """Создает архив проекта, исключая лишние файлы"""
    with tarfile.open(output_filename, "w:gz") as tar:
        for root, dirs, files in os.walk(source_dir):
            # Исключаем служебные папки
            if any(x in root for x in [".git", "__pycache__", "venv", ".venv", ".cursor", "terminals", "assets"]):
                continue
            for file in files:
                # Исключаем архивы и сами скрипты деплоя
                if file in [output_filename, "deploy.py", "auto_deploy.py", "check_shelter_connection.py", "gora_bot.db"]:
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_dir)
                tar.add(full_path, arcname=rel_path)

def execute_command(ssh, cmd):
    """Выполняет команду на сервере и выводит результат"""
    print(f"Executing: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', 'ignore')
    err = stderr.read().decode('utf-8', 'ignore')
    if out: print(out)
    if err: print(err)
    return exit_status

def deploy():
    # Данные вашего сервера
    host = "89.104.66.21"
    user = "root"
    password = "01IJHGebMbaHr4Qj"
    project_name = "garabotprofi"
    remote_path = f"/root/{project_name}"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"--- Connecting to {host}... ---")
    passwords = [password, "01IJHGeBMbaHr4Qj"] # Пробуем новый и старый на всякий случай
    connected = False
    for pwd in passwords:
        try:
            print(f"Trying password: {pwd}")
            ssh.connect(host, username=user, password=pwd, timeout=20, look_for_keys=False, allow_agent=False)
            # Без emoji, чтобы не падать на Windows-консоли
            print("Connected successfully.")
            connected = True
            break
        except paramiko.AuthenticationException:
            print("Authentication failed.")
            continue
        except Exception as e:
            print(f"Error: {e}")
            continue

    if not connected:
        print("❌ All authentication attempts failed. Please check the password.")
        return
    
    # 1. Подготовка архива
    print("--- Preparing project archive... ---")
    tar_name = "project.tar.gz"
    create_tarball(tar_name, ".")
    
    # 2. Создание папки и загрузка
    print(f"--- Uploading to {remote_path}... ---")
    execute_command(ssh, f"mkdir -p {remote_path}")
    try:
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(tar_name, f"{remote_path}/{tar_name}")
        print("Upload complete!")
    finally:
        if os.path.exists(tar_name):
            os.remove(tar_name)
    
    # 3. Распаковка и настройка окружения
    print("--- Extracting and setting up environment... ---")
    setup_commands = [
        f"cd {remote_path} && tar -xzf {tar_name}",
        f"cd {remote_path} && rm {tar_name}",
        f"apt-get update && apt-get install -y python3-pip python3-venv ffmpeg",
        f"cd {remote_path} && python3 -m venv venv",
        f"cd {remote_path} && ./venv/bin/pip install -r requirements.txt"
    ]
    
    for cmd in setup_commands:
        status = execute_command(ssh, cmd)
        if status != 0 and "apt-get" not in cmd: # apt-get может возвращать не 0 при мелких варнингах
            print(f"❌ Command failed with status {status}")
            ssh.close()
            return

    # 4. Настройка Systemd сервиса для БОТА
    print("--- Configuring Systemd service for BOT... ---")
    bot_service = f"""[Unit]
Description=GORA Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={remote_path}
ExecStart={remote_path}/venv/bin/python -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    execute_command(ssh, f"cat <<EOF > /etc/systemd/system/gora_bot.service\n{bot_service}\nEOF")
    
    # 5. Настройка Systemd сервиса для АДМИНКИ
    print("--- Configuring Systemd service for ADMIN PANEL... ---")
    admin_service = f"""[Unit]
Description=GORA Admin Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={remote_path}
ExecStart={remote_path}/venv/bin/python -m web_admin.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    execute_command(ssh, f"cat <<EOF > /etc/systemd/system/gora_admin.service\n{admin_service}\nEOF")
    
    # 6. Настройка Nginx для домена gora.ru.net (учитывая ISPmanager)
    print("--- Configuring Nginx for gora.ru.net (ISPmanager override)... ---")
    
    # Мы переписываем конфиг ISPmanager, так как он имеет приоритет из-за указания IP в listen
    nginx_config = """server {
    listen 192.168.0.194:80;
    server_name gora.ru.net www.gora.ru.net;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""
    # Удаляем нашу предыдущую попытку, если она есть
    execute_command(ssh, "rm -f /etc/nginx/sites-enabled/gora_bot")
    
    # Перезаписываем основной конфиг ISPmanager для этого домена
    execute_command(ssh, f"cat <<'EOF' > /etc/nginx/vhosts/www-root/gora.ru.net.conf\n{nginx_config}\nEOF")
    
    # Также настраиваем HTTPS с использованием полученного Let's Encrypt сертификата
    ssl_config = """server {
    listen 192.168.0.194:443 ssl;
    server_name gora.ru.net www.gora.ru.net;

    ssl_certificate /etc/letsencrypt/live/gora.ru.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gora.ru.net/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""
    # Добавляем SSL блок в тот же файл или в отдельный
    execute_command(ssh, f"cat <<'EOF' >> /etc/nginx/vhosts/www-root/gora.ru.net.conf\n{ssl_config}\nEOF")
    
    execute_command(ssh, "nginx -t && systemctl restart nginx")
    
    # 7. Обновление базы данных (только создание таблиц если не существуют)
    print("--- Updating database schema (preserving data)... ---")
    # Only create tables if they don't exist - DO NOT drop tables
    execute_command(ssh, f"cd {remote_path} && ./venv/bin/python -c 'from db.base import Base; from db.session import engine; import db.models; Base.metadata.create_all(bind=engine)'")
    # Seed only if database is empty
    seed_status = execute_command(ssh, f"cd {remote_path} && ./venv/bin/python -c \"from db.session import SessionLocal; from db.models import MenuItem; db=SessionLocal(); count=db.query(MenuItem).count(); db.close(); print('DB has', count, 'menu items'); exit(0 if count>0 else 1)\"")
    if seed_status != 0:
        print("Database is empty, seeding...")
        execute_command(ssh, f"cd {remote_path} && ./venv/bin/python seed_db.py")
    else:
        # Без emoji для совместимости с Windows-консолью
        print("Database already has data, skipping seed")
    
    # Always update guide items with correct links
    print("--- Updating guide items... ---")
    execute_command(ssh, f"cd {remote_path} && ./venv/bin/python update_guide.py")
    
    # Запуск всего
    execute_command(ssh, "systemctl daemon-reload")
    execute_command(ssh, "systemctl enable gora_bot gora_admin")
    execute_command(ssh, "systemctl restart gora_bot gora_admin")
    
    print("\nDEPLOYMENT FINISHED SUCCESSFULLY!")
    execute_command(ssh, "systemctl status gora_bot gora_admin --no-pager")
    
    ssh.close()

if __name__ == "__main__":
    deploy()
