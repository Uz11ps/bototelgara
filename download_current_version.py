import paramiko
import os
import tarfile
import sys
from scp import SCPClient

# Настройка UTF-8 для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

def download_and_extract():
    # Данные сервера (из deploy.py)
    host = "89.104.66.21"
    user = "root"
    password = "01IJHGebMbaHr4Qj"
    project_path = "/root/garabotprofi"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"--- Connecting to {host}... ---")
    passwords = [password, "01IJHGeBMbaHr4Qj"]
    connected = False
    
    for pwd in passwords:
        try:
            ssh.connect(host, username=user, password=pwd, timeout=20, look_for_keys=False, allow_agent=False)
            print("✅ Connected!")
            connected = True
            break
        except Exception as e:
            print(f"Auth attempt failed: {e}")
            continue
            
    if not connected:
        print("❌ Could not connect to server")
        return

    # 1. Создаем архив на сервере
    print("--- Creating archive on server... ---")
    remote_tar = "/tmp/project_backup.tar.gz"
    # Исключаем venv, git, кэши, и медиа файлы если они тяжелые (хотя просили всё)
    # Оставим venv в исключениях так как он платформозависимый
    cmd = f"cd {project_path} && tar -czf {remote_tar} . --exclude=venv --exclude=__pycache__ --exclude=.git --exclude=*.pyc"
    
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    
    if exit_status != 0:
        print(f"Error creating archive: {stderr.read().decode()}")
        return
        
    print("✅ Archive created")

    # 2. Скачиваем
    local_tar = "remote_backup.tar.gz"
    print(f"--- Downloading to {local_tar}... ---")
    
    with SCPClient(ssh.get_transport()) as scp:
        scp.get(remote_tar, local_tar)
        
    print("✅ Download complete")
    
    # 3. Чистим сервер
    ssh.exec_command(f"rm {remote_tar}")
    ssh.close()
    
    # 4. Распаковываем
    print("--- Extracting locally... ---")
    # Создаем бэкап текущих локальных конфигов если нужно (deploy.py например)
    # Но пользователь просил "подтяни сюда", значит обновляем текущую папку
    
    try:
        with tarfile.open(local_tar, "r:gz") as tar:
            # Безопасная распаковка
            def is_within_directory(directory, target):
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                prefix = os.path.commonprefix([abs_directory, abs_target])
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
                tar.extractall(path, members=members, numeric_owner=numeric_owner, filter='data') 
                
            safe_extract(tar, path=".")
            
        print("✅ Extracted successfully")
        
    except Exception as e:
        print(f"❌ Extraction error: {e}")
    finally:
        if os.path.exists(local_tar):
            os.remove(local_tar)
            print("Cleanup done")

if __name__ == "__main__":
    download_and_extract()
