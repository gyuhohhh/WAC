import win32com.client

def delete_shadow_copy(shadow_id):
    try:
        objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        objSWbemServices = objWMIService.ConnectServer(".", "root\\cimv2")
        objShadowCopy = objSWbemServices.Get(f"Win32_ShadowCopy.ID='{shadow_id}'")
        
        if objShadowCopy:
            objShadowCopy.Delete_()

    except Exception:
        print("delete_VSC Failed")
        pass


