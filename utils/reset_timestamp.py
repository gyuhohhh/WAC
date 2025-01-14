import win32file
import win32con

def set_file_timestamp(file_path, creation_time, atime, mtime):
    try:
        file_attributes = win32file.GetFileAttributes(file_path)
        if file_attributes & win32con.FILE_ATTRIBUTE_DIRECTORY:
            # 디렉터리 핸들 열기
            file_handle = win32file.CreateFile(
                file_path,
                win32con.GENERIC_WRITE | win32con.GENERIC_READ,  # 읽기/쓰기 권한
                win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_READ,  # 다른 프로세스의 읽기/쓰기 허용
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_FLAG_BACKUP_SEMANTICS,  # 디렉터리 핸들 열 때 필요한 플래그
                None
            )
        else:
            # 파일 핸들 열기
            file_handle = win32file.CreateFile(
                file_path,
                win32con.GENERIC_WRITE | win32con.GENERIC_READ,
                win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_READ,
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_ATTRIBUTE_NORMAL,
                None
            )
        
        # 생성 시간을 설정
        win32file.SetFileTime(file_handle, creation_time, atime, mtime)
        
        # 파일 핸들 닫기
        file_handle.close()
    except Exception as e:
        print("reset_timestamp Failed")
        print(f"예외 내용: {e}")
        pass
