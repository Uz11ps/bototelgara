import paramiko
import sys

def run_checks():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect('89.104.66.21', username='root', password='01IJHGebMbaHr4Qj')
        
        def execute(cmd):
            stdin, stdout, stderr = ssh.exec_command(cmd)
            return stdout.read().decode('utf-8', 'ignore'), stderr.read().decode('utf-8', 'ignore')

        print('--- Nginx sites-enabled ---')
        out, _ = execute('ls -F /etc/nginx/sites-enabled/')
        print(out)

        print('--- Nginx ISPmanager vhosts ---')
        out, _ = execute('ls -F /etc/nginx/conf.d/vhosts/ 2>/dev/null')
        print(out)

        print('--- Checking SSL configs ---')
        out, _ = execute('grep -l "listen.*443" /etc/nginx/vhosts/www-root/*.conf 2>/dev/null')
        print(out)
        
        print('--- Checking all listen for gora.ru.net ---')
        out, _ = execute('grep -r "gora.ru.net" /etc/nginx/ | grep listen')
        print(out)
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_checks()
