import winreg

def enable_long_paths():
    try:
        value = 0
        reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem", 0, winreg.KEY_ALL_ACCESS)
        current_value, _ = winreg.QueryValueEx(reg_key, "LongPathsEnabled")
        
        if current_value == 1:
            value = 1
        else:
            # LongPathsEnabled 값을 1로 변경
            winreg.SetValueEx(reg_key, "LongPathsEnabled", 0, winreg.REG_DWORD, 1)
            value = 0
        winreg.CloseKey(reg_key)
    except (FileNotFoundError, PermissionError, OSError):
        pass
    
    return value
