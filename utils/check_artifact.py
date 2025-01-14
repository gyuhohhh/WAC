from datetime import datetime, timezone
import json
import os
import sys
import glob
import re
import dateutil.tz

from utils import apache_utils, vbox_utils, vmware_utils

from utils.Artifacts import Artifacts

# 패키징 대비 경로 설정
def resource_path(relative_path):
    try: # EXE로 패키징 했을 때 pyinstaller에서 실행될 임시 경로
        base_path = sys._MEIPASS
    except AttributeError: # 개발 환경에서는 현재 경로를 사용
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# json 파일 읽기
def load_config(config_file):
    try:
        json_path = resource_path(os.path.join('config', config_file))
        with open(json_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def normalize_name(name):
    normalized_name = re.sub(r'\d+', '', name)
    return normalized_name

def convert_wsl_path(path):
    fixed_part = "LocalState"

    if fixed_part in path:
        trimmed_path = path.split(fixed_part)[0] + fixed_part
    else:
        trimmed_path = path
    
    return trimmed_path

# 경로 별 타임스탬프 반환
def check_timestamp(source_pattern):
    expanded_source_pattern = os.path.expandvars(source_pattern)
    expanded_source_pattern = os.path.expanduser(expanded_source_pattern)
    matched_directories = glob.glob(expanded_source_pattern)
    
    atime = datetime.min.replace(tzinfo=timezone.utc)
    mtime = datetime.min.replace(tzinfo=timezone.utc)
    ctime = datetime.max.replace(tzinfo=timezone.utc)

    if not matched_directories:
        return atime, mtime, ctime, False
    
    for source_dir in matched_directories:
        try:
            if os.path.isfile(source_dir):
                file_stats = os.stat(source_dir)
                last_access_time = datetime.fromtimestamp(file_stats.st_atime, timezone.utc)
                last_modified_time = datetime.fromtimestamp(file_stats.st_mtime, timezone.utc)
                creation_time = datetime.fromtimestamp(file_stats.st_birthtime, timezone.utc)
                
                if last_access_time > atime:
                    atime = last_access_time
                if last_modified_time > mtime:
                    mtime = last_modified_time
                if creation_time < ctime:
                    ctime = creation_time
                
            elif os.path.isdir(source_dir):
                for root, dirs, files in os.walk(source_dir):
                    if root == source_dir:
                        dir_stats = os.stat(root)
                        dir_atime = datetime.fromtimestamp(dir_stats.st_atime, timezone.utc)
                        dir_mtime = datetime.fromtimestamp(dir_stats.st_mtime, timezone.utc)
                        dir_ctime = datetime.fromtimestamp(dir_stats.st_birthtime, timezone.utc)

                        if dir_atime > atime:
                            atime = dir_atime
                        if dir_mtime > mtime:
                            mtime = dir_mtime
                        if dir_ctime < ctime:
                            ctime = dir_ctime
                        
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_stats = os.stat(file_path)
                        last_access_time = datetime.fromtimestamp(file_stats.st_atime, timezone.utc)
                        last_modified_time = datetime.fromtimestamp(file_stats.st_mtime, timezone.utc)
                        creation_time = datetime.fromtimestamp(file_stats.st_birthtime, timezone.utc)

                        if last_access_time > atime:
                            atime = last_access_time
                        if last_modified_time > mtime:
                            mtime = last_modified_time
                        if creation_time < ctime:
                            ctime = creation_time

        except (OSError, FileNotFoundError, PermissionError) as e:
            continue
    
    return atime, mtime, ctime, True

def check_condition(instance, active_names):
    if instance.name in active_names:
        return True
    return False

# 메인
def check_all_config(progress_callback=None, is_running_callback=None):
    config_dir = resource_path('config')
    config_files = glob.glob(os.path.join(config_dir, '*.json'))

    local_timezone = dateutil.tz.tzlocal()

    total_directories = 0
    directories_processed = 0

    for config_file in config_files:
        if is_running_callback and not is_running_callback():
            break

        config = load_config(config_file)
        for entry in config['directories']:
            source_directories = entry['source_directory']
            if isinstance(source_directories, str):
                source_directories = [source_directories]
            total_directories += len(source_directories)
        

    for config_file in config_files:
        if is_running_callback and not is_running_callback():
            break

        config = load_config(config_file)
        config_name = os.path.splitext(os.path.basename(config_file))[0]


        atime = datetime.min.replace(tzinfo=timezone.utc)
        mtime = datetime.min.replace(tzinfo=timezone.utc)
        ctime = datetime.max.replace(tzinfo=timezone.utc)

        active_names = []

        for entry in config['directories']:
            if is_running_callback and not is_running_callback():
                break

            source_directories = entry['source_directory']

            if isinstance(source_directories, str):
                source_directories = [source_directories]

            # Apache 설치 경로 탐색 후 경로 결합
            if config_name == 'ApacheLogFiles':
                # source_directory를 리스트로 처리하여 Apache 경로와 결합
                source_directories = [apache_utils.construct_apache_log_path(source_directory) for source_directory in source_directories]

            # VirtualBox 가상머신 디렉터리 탐색 후 경로 결합
            if config_name == 'VirtualBox':
                source_directories = [vbox_utils.construct_vbox_path(source_directory) for source_directory in source_directories]  

            # VMware 가상머신 디렉터리 탐색 후 경로 결합          
            if config_name == 'VMwareDir':
                source_directories = [vmware_utils.construct_vmware_path(source_directory) for source_directory in source_directories]
            
            if config_name in ["Ubuntu1", "Ubuntu2", "Debian1", "Debian2", "Kali1", "Kali2", "OracleLinux1", "OracleLinux2", "openSUSE1",
                               "openSUSE2", "SUSELinuxEnterpriseServer1", "SUSELinuxEnterpriseServer2"]:
                source_directories = [convert_wsl_path(source_directory) for source_directory in source_directories]
                config_name = normalize_name(config_name)
            
            for source_directory in source_directories:
                if is_running_callback and not is_running_callback():
                    break
                
                last_access_time, last_modified_time, creation_time, stat = check_timestamp(source_directory)
                if last_access_time > atime:
                    atime = last_access_time
                if last_modified_time > mtime:
                    mtime = last_modified_time
                if creation_time < ctime:
                    ctime = creation_time
                if stat:
                    if config_name not in active_names:
                        active_names.append(config_name)
                
                directories_processed += 1

                if progress_callback:
                    progress_percentage = int((directories_processed / total_directories) * 100)
                    progress_callback(progress_percentage)

        
        
        
        for instance in Artifacts.instances:
            if instance.name == config_name:
                if atime != datetime.min.replace(tzinfo=timezone.utc):
                    input_atime = atime.astimezone(local_timezone)
                    input_atime = input_atime.replace(tzinfo=None)
                    instance.atime = input_atime
                if mtime != datetime.min.replace(tzinfo=timezone.utc):
                    input_mtime = mtime.astimezone(local_timezone)
                    input_mtime = input_mtime.replace(tzinfo=None)
                    instance.mtime = input_mtime
                if ctime != datetime.max.replace(tzinfo=timezone.utc):
                    input_ctime = ctime.astimezone(local_timezone)
                    input_ctime = input_ctime.replace(tzinfo=None)
                    instance.ctime = input_ctime


        for instance in Artifacts.instances:
            if instance.name == "$MFT":
                mft_time = instance.ctime
                instance.atime = datetime.now()
                instance.mtime = datetime.now()

                
        for instance in Artifacts.instances:
            if instance.name in ['$Boot', '$J', '$LogFile', '$MFTMirr', '$SDS', '$T']:
                instance.atime = datetime.now()
                instance.mtime = datetime.now()
                instance.ctime = mft_time
                    
        for instance in Artifacts.instances:
            if check_condition(instance, active_names):
                instance.exist = True
        
    #디버깅 출력
    # for instance in Artifacts.instances:
    #     print(f"Name: {instance.name} | Exist: {instance.exist} | atime: {instance.atime} | mtime: {instance.mtime} | ctime: {instance.ctime}")
