import os

def find_vmware_vm_directory():
    try:
        # VMware 설정 파일 경로 (Windows 기준)
        config_path = os.path.join(os.environ['APPDATA'], "VMware", "preferences.ini")
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    if line.startswith('pref.ws.session.window0.tab1.file'):
                        # '=' 기호를 기준으로 문자열 분리하여 경로 추출
                        path = line.split('=')[1].strip().strip('"')
                        # 파일 이름을 제외한 디렉터리 경로만 반환
                        directory_path = os.path.dirname(path)
                        # 상위 디렉터리 경로 반환
                        parent_directory_path = os.path.dirname(directory_path)
                        return parent_directory_path
    except Exception:
        return None

def construct_vmware_path(log_pattern):
    try:
        vmware_directory_path = find_vmware_vm_directory()
        if vmware_directory_path:
            # vmware 디렉터리 경로와 log 패턴을 결합
            full_log_path = os.path.join(vmware_directory_path, log_pattern)
            return full_log_path
        else:
            return log_pattern  # 경로를 찾지 못하면 원래 패턴을 반환
    except Exception:
        return log_pattern