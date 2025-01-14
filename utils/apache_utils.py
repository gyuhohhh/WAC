import subprocess
import re
import os

def find_apache_install_path():
    try:
        result = subprocess.run(['sc', 'qc', 'Apache2.4'], capture_output=True, text=True)
        if result.returncode != 0:
            return None
        
        output = result.stdout
        match = re.search(r'BINARY_PATH_NAME\s*:\s*(.*httpd\.exe)', output)
        
        if match:
            httpd_path = match.group(1).replace('"', '').strip()
            install_dir = os.path.dirname(httpd_path)

            if os.path.basename(install_dir).lower() == "bin":
                install_dir = os.path.dirname(install_dir)
            return install_dir
        else:
            return None
    except Exception:
        return None

def construct_apache_log_path(log_pattern):
    apache_path = find_apache_install_path()
    if apache_path:
        # Apache 경로와 log 패턴을 결합
        full_log_path = os.path.join(apache_path, log_pattern)
        return full_log_path
    else:
        return log_pattern  # 경로를 찾지 못하면 원래 패턴을 반환