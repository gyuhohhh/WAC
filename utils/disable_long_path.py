import winreg

def disable_long_paths():
    try:
        reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(reg_key, "LongPathsEnabled", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(reg_key)       
    except (PermissionError, FileNotFoundError, OSError):
        pass

