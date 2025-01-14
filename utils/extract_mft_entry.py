import os
import sys
import pytsk3
import hashlib
from utils import reset_timestamp
import pywintypes

# 파일 읽기 상한선 : 2GB
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024 # 2GB

# 주어진 파일에 대해 MD5와 SHA-256 해시를 계산하여 반환 (여기선 바이너리 값에 접근해서 해시값 산출함)
def calculate_hash(data):
    md5_hash = hashlib.md5()
    sha256_hash = hashlib.sha256()

    md5_hash.update(data)
    sha256_hash.update(data)
    
    return md5_hash.hexdigest(), sha256_hash.hexdigest()


# inode 찾아주는 로직
def find_inode_by_path(filesystem, path, target_file):
    directory = filesystem.open_dir(path=path)
    for entry in directory:
        file_name = entry.info.name.name.decode('utf-8')

        if file_name == target_file:
            return entry.info.meta.addr



# $SDS, $J, $T 의 경우 수집 로직
def extract_specific_attribute(filesystem, inode, attribute_name, output_dir):
    ntfs_file = filesystem.open_meta(inode=inode)

    for attr in ntfs_file:
        attr_name = attr.info.name

        if attr_name is not None and attr_name.decode('utf-8') == attribute_name:
            file_size = attr.info.size

            # 상한선을 넘지 않으면 한 번에 처리
            if file_size <= MAX_FILE_SIZE:
                with open(output_dir, "wb") as f:
                    data = ntfs_file.read_random(0, file_size, attr.info.type, attr.info.id)
                    md5_hash, sha256_hash = calculate_hash(data)
                    f.write(data)
                
            # 상한선을 넘으면 나눠서 읽기
            else:
                chunk_size = 1024 * 1024 * 1024 # 1GB
                md5_hash = hashlib.md5()
                sha256_hash = hashlib.sha256()

                with open(output_dir, "wb") as f:
                    for offset in range(0, file_size, chunk_size):
                        read_size = min(chunk_size, file_size - offset)
                        data = ntfs_file.read_random(offset, read_size, attr.info.type, attr.info.id)
                        f.write(data)
                        md5_hash.update(data)
                        sha256_hash.update(data)


    modified_time = ntfs_file.info.meta.mtime
    access_time = ntfs_file.info.meta.atime
    ctime = ntfs_file.info.meta.crtime
    creation_time = pywintypes.Time(ctime)
    atime = pywintypes.Time(access_time)
    mtime = pywintypes.Time(modified_time)

    # $SDS / $J / $T 의 타임스탬프 조정
    reset_timestamp.set_file_timestamp(output_dir, creation_time, atime, mtime)

    # $Secure / $UsnJrnl / $Tops 의 타임스탬프 조정 << 얘네는 디렉터리 구조지만 일반 파일이어서 따로 해줘야 함
    upper_path = os.path.abspath(os.path.join(output_dir, '..\\'))
    reset_timestamp.set_file_timestamp(upper_path, creation_time, atime, mtime)

    if file_size <= MAX_FILE_SIZE:
        return md5_hash, sha256_hash
    else:
        return md5_hash.hexdigest(), sha256_hash.hexdigest()


# $MFT, $MFTMirr, $LogFile, $Boot 의 경우 수집 로직
def extract_file_with_structure(filesystem, inode, output_dir):
    ntfs_file = filesystem.open_meta(inode=inode)
    file_size = ntfs_file.info.meta.size

    # 상한선 이하인 경우 한 번에 처리
    if file_size <= MAX_FILE_SIZE:
        with open(output_dir, "wb") as f:
            data = ntfs_file.read_random(0, ntfs_file.info.meta.size)
            md5_hash, sha256_hash = calculate_hash(data)
            f.write(data)
    
    # 상한선 초과 시 청크를 나누어 처리
    else:
        chunk_size = 1024 * 1024 * 1024 # 1GB
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()

        with open(output_dir, "wb") as f:
            for offset in range(0, file_size, chunk_size):
                read_size = min(chunk_size, file_size - offset)
                data = ntfs_file.read_random(offset, read_size)
                f.write(data)
                md5_hash.update(data)
                sha256_hash.update(data)

    modified_time = ntfs_file.info.meta.mtime
    access_time = ntfs_file.info.meta.atime
    ctime = ntfs_file.info.meta.crtime
    creation_time = pywintypes.Time(ctime)
    atime = pywintypes.Time(access_time)
    mtime = pywintypes.Time(modified_time)

    reset_timestamp.set_file_timestamp(output_dir, creation_time, atime, mtime)

    if file_size <= MAX_FILE_SIZE:
        return md5_hash, sha256_hash
    else:
        return md5_hash.hexdigest(), sha256_hash.hexdigest()
    
    






def extract_ntfs_files_with_structure(image_file, output_dir, artifact_name):
    try:
        # 이미지 파일을 RO 모드로 오픈
        img = pytsk3.Img_Info(image_file)

        # NTFS 파일 오픈
        filesystem = pytsk3.FS_Info(img)

        sds_inode = find_inode_by_path(filesystem, "/", "$Secure")
        j_inode = find_inode_by_path(filesystem, "/$Extend", "$UsnJrnl")
        t_inode = find_inode_by_path(filesystem, "/$Extend/$RmMetadata/$TxfLog", "$Tops")

        # 수집하기 위한 inode와 경로 정의
        files_to_extract = {
            "$MFT": 0, # C:\$MFT
            "$MFTMirr": 1, # C:\$MFTMirr
            "$LogFile": 2, # C:\$LogFile
            "$Boot": 7, # C:\$Boot
            "$SDS": sds_inode, # C:\$Secure\$SDS
            "$J": j_inode, # C:\$Extended\$UsnJrnl\$J
            "$T": t_inode # C:\$Extended\$RmMetadata\$TxfLog\$Tops\$T
        }

        for file_name, inode in files_to_extract.items():
            if file_name == artifact_name:
                if file_name in ["$SDS", "$J", "$T"]:
                    md5_hash, sha256_hash = extract_specific_attribute(filesystem, inode, file_name, output_dir)
                    return md5_hash, sha256_hash
                else:
                    md5_hash, sha256_hash = extract_file_with_structure(filesystem, inode, output_dir)
                    return md5_hash, sha256_hash
    except Exception:
        return None, None
