import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj')

stdin, stdout, stderr = ssh.exec_command("cd /root/garabotprofi && ./venv/bin/python add_admin.py 5868421234 'Main Administrator'")
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())

ssh.close()
