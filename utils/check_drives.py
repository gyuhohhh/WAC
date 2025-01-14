import psutil

def list_system_drives():
    drives = []
    try:
        for partition in psutil.disk_partitions():
            if 'cdrom' in partition.opts or partition.fstype == '':
                # CD-ROM 드라이브는 제외합니다 (빈 fstype 또한 제외)
                continue
            drives.append(partition.device)
    except Exception:
        pass
    return drives
