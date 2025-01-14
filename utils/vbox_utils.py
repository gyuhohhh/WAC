import xml.etree.ElementTree as ET
import os

def find_virtualbox_vm_directory():
    try:
        home_path = os.path.expanduser("~")
        config_path = os.path.join(home_path, ".VirtualBox", "VirtualBox.xml")
        
        if os.path.exists(config_path):
            # namespace 처리를 위한 설정
            ns = {'ns0': 'http://www.virtualbox.org/'}

            tree = ET.parse(config_path)
            root = tree.getroot()

            # SystemProperties 태그에서 defaultMachineFolder 속성 찾기
            system_properties = root.find('ns0:Global/ns0:SystemProperties', ns)
            if system_properties is not None:
                default_machine_folder = system_properties.get('defaultMachineFolder')
                if default_machine_folder:
                    return default_machine_folder
    except Exception:
        return None

def construct_vbox_path(log_pattern):
    try:
        vbox_directory_path = find_virtualbox_vm_directory()
        if vbox_directory_path:
            # vbox 디렉터리 경로와 log 패턴을 결합
            full_log_path = os.path.join(vbox_directory_path, log_pattern)
            return full_log_path
        else:
            return log_pattern  # 경로를 찾지 못하면 원래 패턴을 반환
    except Exception:
        return log_pattern