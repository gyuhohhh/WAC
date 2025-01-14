import os
import shutil
import json
import logging
import glob
import hashlib
import sys
import pywintypes
import zipfile
from utils import apache_utils, create_VSC, delete_VSC, wsl_utils, vbox_utils, vmware_utils, check_drives, extract_mft_entry
from utils import create_collect_report
from utils import enable_long_path, disable_long_path
from utils import create_hash_report, reset_timestamp


collected_data = [] # DataFrame용 변수

def list_existing_files(directory):
    existing_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            existing_files.append(os.path.join(root, file))
    return existing_files

def store_zip(output_zip, root_dir, exclude_files, existing_files_before_run):
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subforlder, filenames in os.walk(root_dir):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                if filename in exclude_files or file_path in existing_files_before_run:
                    continue
                arcname = os.path.relpath(file_path, root_dir)
                zipf.write(file_path, arcname)

# 디렉터리 타임스탬프 수정 로직
def update_directory_timestamps(base_target_directory, drive_paths):
    for drive_key, vsc_path in drive_paths.items():
        drive_letter = drive_key.split('_')[-1]
        drive_target_directory = os.path.join(base_target_directory, drive_letter)

        if not os.path.exists(drive_target_directory):
            continue

    
        for root, dirs, files in os.walk(base_target_directory):
            for dir_name in dirs:
                target_dir = os.path.join(root, dir_name)

                relative_path = os.path.relpath(target_dir, drive_target_directory)
                source_dir_full = os.path.join(vsc_path, relative_path)

                if os.path.exists(source_dir_full):
                    creation_time = pywintypes.Time(os.path.getctime(source_dir_full))
                    dir_stat = os.stat(source_dir_full)
                    atime = pywintypes.Time(dir_stat.st_atime)
                    mtime = pywintypes.Time(dir_stat.st_mtime)
                    reset_timestamp.set_file_timestamp(target_dir, creation_time, atime, mtime)


# 패키징 대비 경로 설정
def resource_path(relative_path):
    try: # EXE로 패키징 했을 때 pyinstaller에서 실행될 임시 경로
        base_path = sys._MEIPASS
    except AttributeError: # 개발 환경에서는 현재 경로를 사용
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# 드라이브 별 VSC 생성
def create_vsc(progress_callback=None):
    try:
        drive_paths = {}
        drives = check_drives.list_system_drives()
        total_drives = len(drives)
        shadow_ids = []

        for idx, drive in enumerate(drives):
            tmp, tmp2= create_VSC.create_shadow_copy(drive)
            shadow_ids.append(tmp2)
            drive_letter = drive.rstrip(':\\')
            drive_paths[f"copy_path_{drive_letter}"] = tmp

            if progress_callback:
                progress_percentage = int(((idx + 1) / total_drives) * 25)
                progress_callback(progress_percentage, "Volume Shadow Copy 생성 중..")

        return drive_paths, shadow_ids
    except Exception:
        return {}, []


# 로깅 설정
def setup_logging(log_file):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)  # Ensure the log directory exists
    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_separator(sep):
    separator = sep * 120
    logging.info(separator)

def remove_directory_except(directory, exclude_files, existing_files_before_run):
    for root, dirs, files in os.walk(directory, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            if file not in exclude_files and file_path not in existing_files_before_run:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            contains_exclude_file = any(
                file.startswith(dir_path) for file in existing_files_before_run
            )
            if dir not in exclude_files and not contains_exclude_file:
                try:
                    shutil.rmtree(dir_path)
                except OSError:
                    pass
    remove_empty_directory(directory)

def remove_empty_directory(directory):
    for root, dirs, _ in os.walk(directory, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):
                try:
                    shutil.rmtree(dir_path)
                except OSError:
                    pass

# 주어진 파일에 대해 MD5와 SHA-256 해시를 계산하여 반환
def calculate_hash(file_path):
    md5_hash = hashlib.md5()
    sha256_hash = hashlib.sha256()

    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            md5_hash.update(chunk)
            sha256_hash.update(chunk)
    
    return md5_hash.hexdigest(), sha256_hash.hexdigest()

# MFT Entry에 대해 수집
def collect_artifact_mft_entry(source_pattern, target_base_dir, drive_paths, config_file):
    global collected_data

    source_drive, source_path = os.path.splitdrive(source_pattern)
    drive_folder = os.path.join(target_base_dir, source_drive.strip(':'))
    target_file = os.path.join(drive_folder, source_path.strip('\\'))

    if source_path.startswith('\\'):
        modified_path = source_path[1:]
    else:
        modified_path = source_path
    drive = drive_paths['copy_path_C']

    logging.info(f'Starting copy from {source_pattern} to {target_file}.')
    source2_dir = os.path.join(drive, modified_path)
    artifact_name = os.path.splitext(config_file)[0]

    
    # 수집 수행
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    md5, sha256 = extract_mft_entry.extract_ntfs_files_with_structure(drive, target_file, artifact_name)

    logging.info(f'Successfully copied from {source_pattern} to {target_file}.')
    log_separator('-')

    
    file_name_for_df = os.path.basename(source2_dir)

    collected_data.append({
        "아티팩트명": artifact_name,
        "원본 경로": source_pattern,
        "추출 경로": source2_dir,
        "파일명": file_name_for_df,
        "MD5": md5,
        "SHA-256": sha256
    })



# 파일 및 디렉토리 수집 (MFT Entry 제외)
def collect_artifacts(source_pattern, target_base_dir, drive_paths, config_file):
    global collected_data

    expanded_source_pattern = os.path.expandvars(source_pattern)
    expanded_source_pattern = os.path.expanduser(expanded_source_pattern)
    matched_directories = glob.glob(expanded_source_pattern)

    if not matched_directories: # matched_directories가 비어있을 때 / 복사 수행 X
        logging.info('Failed copy, ')
        logging.info(f'{source_pattern} : is not exists')
        log_separator('-')

    else: # matched_directories가 존재할 때 복사 수행
        for source_dir in matched_directories:
            try:
                if os.path.isfile(source_dir):
                    # 파일일 경우 
                    source_drive, source_path = os.path.splitdrive(source_dir)
                    drive_folder = os.path.join(target_base_dir, source_drive.strip(':'))
                    target_file = os.path.join(drive_folder, source_path.strip('\\'))
                    
                    if source_path.startswith('\\'):
                        modified_path = source_path[1:]
                    else:
                        modified_path = source_path
                    drive_letter = source_drive.rstrip(':\\')
                    drive_name = f"copy_path_{drive_letter}"

                    
                    logging.info(f'Starting copy from {source_dir} to {target_file}.')
                    log_separator('-')

                    if drive_name in drive_paths:
                        tmp = drive_paths[drive_name]
                        source2_dir = os.path.join(tmp, modified_path)

                        os.makedirs(os.path.dirname(target_file), exist_ok=True)
                        shutil.copy2(source2_dir, target_file)
                        stat = os.stat(source2_dir)
                        atime = pywintypes.Time(stat.st_atime)
                        mtime = pywintypes.Time(stat.st_mtime)
                        creation_time = pywintypes.Time(os.path.getctime(source2_dir))
                        reset_timestamp.set_file_timestamp(target_file, creation_time, atime, mtime)
                        logging.info(f'Successfully copied from {source_dir} to {target_file}.')
                        log_separator('-')
                        
                        file_name_for_df = os.path.basename(source2_dir)
                        md5, sha256 = calculate_hash(source2_dir)

                        collected_data.append({
                            "아티팩트명": os.path.splitext(config_file)[0],
                            "원본 경로": source_dir,
                            "추출 경로": source2_dir,
                            "파일명": file_name_for_df,
                            "MD5": md5,
                            "SHA-256": sha256
                        })
                            

                    log_separator('-')

                elif os.path.isdir(source_dir):
                    # 디렉토리일 경우
                    source_drive, source_path = os.path.splitdrive(source_dir)
                    drive_folder = os.path.join(target_base_dir, source_drive.strip(':'))
                    target_dir = os.path.join(drive_folder, source_path.strip('\\'))

                    if source_path.startswith('\\'):
                        modified_path = source_path[1:]
                    else:
                        modified_path = source_path
                    drive_letter = source_drive.rstrip(':\\')
                    drive_name = f"copy_path_{drive_letter}"
            
                    logging.info(f'Starting copy from {source_dir} to {target_dir}.')

                    if drive_name in drive_paths:
                        tmp = drive_paths[drive_name]
                        source2_dir = os.path.join(tmp, modified_path)

                        if not os.path.exists(target_dir):
                            os.makedirs(target_dir, exist_ok=True)
                        for root, dirs, files in os.walk(source2_dir):
                            for dir_name in dirs:
                                src_dir = os.path.join(root, dir_name)
                                dest_dir = os.path.join(target_dir, os.path.relpath(src_dir, source2_dir))
                                if not os.path.exists(dest_dir):
                                    os.makedirs(dest_dir, exist_ok=True)
                        
                            for file_name in files:
                                src_file = os.path.join(root, file_name)
                                dest_file = os.path.join(target_dir, os.path.relpath(src_file, source2_dir))

                                shutil.copy2(src_file, dest_file)
                                stat = os.stat(src_file)
                                atime = pywintypes.Time(stat.st_atime)
                                mtime = pywintypes.Time(stat.st_mtime)
                                creation_time = pywintypes.Time(os.path.getctime(src_file))
                                reset_timestamp.set_file_timestamp(dest_file, creation_time, atime, mtime)
                                file_name_for_df = os.path.basename(src_file)
                                md5, sha256 = calculate_hash(src_file)

                                collected_data.append({
                                    "아티팩트명": os.path.splitext(config_file)[0],
                                    "원본 경로": source_dir,
                                    "추출 경로": src_file,
                                    "파일명": file_name_for_df,
                                    "MD5": md5,
                                    "SHA-256": sha256
                                })

                        
                        logging.info(f'Successfully copied from {source_dir} to {target_dir}.')
                    log_separator('-')

                else:
                    logging.warning(f"{source_dir} is neither a file nor a directory.")

            except Exception as e:
                logging.error(f'Error during collection from {source_dir} to {target_base_dir}: {e}')
                log_separator('=')


def load_config(config_file):
    json_path = resource_path(os.path.join('config', config_file))
    with open(json_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def collect_main(checked_list, output_path, export_type, zip_name="", progress_callback=None):
    existing_files_before_run = list_existing_files(output_path) if os.path.exists(output_path) else []
    
    try:
        total_steps = 5
        current_step = 0
        def update_progress(percentage, message=""):
            if progress_callback:
                progress_percentage = int(((current_step / total_steps) + (percentage / 100) / total_steps) * 100)
                progress_callback(progress_percentage, message)

        # 시스템에 존재하는 드라이브 파악 후, 각 드라이브 별 VSC 생성 및 경로/Shadow ID 저장
        drive_paths, shadow_ids = create_vsc(progress_callback)
        current_step += 1

        # 긴 경로 지원 여부 확인 및 활성화 (이미 활성화된 경우 1, 활성화시킨 경우 0 반환)
        path_value = enable_long_path.enable_long_paths()

        wslList = {
            'Ubuntu' : 'Ubuntu',
            'Debian' : 'Debian',
            'Kali' : 'Kali',
            'OpenSUSE' : 'OpenSUSE',
            'OracleLinux' : 'OracleLinux'
        }
        wsl_versions = wsl_utils.check_wsl_versions()
        if not wsl_versions:
            logging.info('WSL is not installed')
        config_files = []
        for item in checked_list:
            if item in wslList:
                key = item.lower()
                if key in wsl_versions:
                    config_files.append(f'{wslList[item]}{wsl_versions[key]}.json')
            elif item == 'SUSELinuxEnterpriseServer':
                config_files.append(f'SUSELinuxEnterpriseServer{wsl_versions["suselinuxenterprisesp"]}.json')
            else:
                config_files.append(f'{item}.json')
            
        
        base_target_directory = output_path
        os.makedirs(base_target_directory, exist_ok=True)
        total_files = len(config_files)

        log_file = os.path.join(base_target_directory, 'collection_log.txt')
        setup_logging(log_file)
        log_separator('-')
        log_separator(' ')
        log_separator(' ')
        log_separator(' ')
        logging.info('Windows Artifact Collector Program is Working.......!')
        log_separator(' ')
        log_separator(' ')
        log_separator(' ')
        log_separator('-')


        for idx, config_file in enumerate(config_files):
            log_separator(' ')
            logging.info(f'Processing configuration file: {os.path.basename(config_file)}')
            log_separator('=')
            config = load_config(config_file)
            
            config_name = os.path.splitext(config_file)[0]
            percentage_per_file = 100 / total_files
            update_progress(idx * percentage_per_file, f"{config_name} 수집 중..")

            # 앞에 $가 붙은 MFT Entry 설정파일인 경우
            if config_name.startswith("$"):
                for entry in config['directories']:
                    source_pattern = entry['source_directory'][0]
                    collect_artifact_mft_entry(source_pattern, base_target_directory, drive_paths, config_file)


            # 앞에 $가 안 붙은 일반 파일에 대한 설정파일인 경우
            else:
                for entry in config['directories']:
                    source_directories = entry['source_directory']

                    # source_directory가 리스트가 아닐 경우 처리
                    if isinstance(source_directories, str):
                        source_directories = [source_directories]

                    # Apache 설치 경로 탐색 후 경로 결합
                    if config_file == 'ApacheLogFiles.json':
                        # source_directory를 리스트로 처리하여 Apache 경로와 결합
                        source_directories = [apache_utils.construct_apache_log_path(source_directory) for source_directory in source_directories]

                    # VirtualBox 가상머신 디렉터리 탐색 후 경로 결합
                    if config_file == 'VirtualBox.json':
                        source_directories = [vbox_utils.construct_vbox_path(source_directory) for source_directory in source_directories]  

                    # VMware 가상머신 디렉터리 탐색 후 경로 결합          
                    if config_file == 'VMwareDir.json':
                        source_directories = [vmware_utils.construct_vmware_path(source_directory) for source_directory in source_directories]


                    # 여러 source_directory에 대해 수집 작업
                    for source_directory in source_directories:
                        collect_artifacts(source_directory, base_target_directory, drive_paths, config_file)

        current_step += 1
        update_progress(100, "파일 수집 완료")

        # 디렉터리 타임스탬프 재설정
        update_directory_timestamps(base_target_directory, drive_paths)


        # 압축 선택했으면 압축해주기
        if export_type:
            if not zip_name.lower().endswith(".zip"):
                contain_name = zip_name + '.zip'
            else:
                contain_name = zip_name
            root_directory = base_target_directory
            output_zip_file = os.path.join(base_target_directory, contain_name)
            exclude_files = ["Artifact Hash Report.xlsx", "Collection Report.html", "collection_log.txt", contain_name]
            store_zip(output_zip_file, root_directory, exclude_files, existing_files_before_run)
            remove_directory_except(base_target_directory, exclude_files, existing_files_before_run)
        
        current_step += 1
        update_progress(100, "압축 완료")
        
        
        # 사용이 끝났으면 생성한 섀도우 카피 삭제하기
        for shadow_id in shadow_ids:
            delete_VSC.delete_shadow_copy(shadow_id)
        
        # 수집 보고서 생성
        if progress_callback:
            progress_callback(75, "수집 보고서 생성 중..")
        collect_report_path = os.path.join(base_target_directory, "Collection Report.html")
        create_collect_report.create_report(config_files, collect_report_path)

        

        # 해시 보고서 생성
        if progress_callback:
            progress_callback(90, "해시 보고서 생성 중..")
        hash_report_path = os.path.join(base_target_directory, "Artifact Hash Report.xlsx")
        create_hash_report.create_hash_report(collected_data, hash_report_path)
        
        current_step += 1
        update_progress(100, "보고서 생성 완료")

        # 긴 경로 지원이 비활성화된 시스템이었을 경우, 사용이 끝난 후 다시 비활성화 시켜줌
        if path_value == 0:
            disable_long_path.disable_long_paths()

        logging.info('Overall artifact collection completed !!!')
        log_separator(' ')

        
    except Exception:
        pass