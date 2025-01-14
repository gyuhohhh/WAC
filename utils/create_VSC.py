import wmi
import win32com.client

def create_shadow_copy(Volume):
    #Volume = Volume + '\\'
    try:
        objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        objSWbemServices = objWMIService.ConnectServer(".", "root\\cimv2")
        objShadowCopyClass = objSWbemServices.Get("Win32_ShadowCopy")
        objInParams = objShadowCopyClass.Methods_("Create").InParameters.SpawnInstance_()
        objInParams.Properties_.Item("Volume").Value = Volume
        objInParams.Properties_.Item("Context").Value = "ClientAccessible"
        objOutParams = objShadowCopyClass.ExecMethod_("Create", objInParams)

        if objOutParams.ReturnValue == 0:
            shadow_id = objOutParams.Properties_("ShadowID").Value

            c = wmi.WMI()
            for shadow in c.Win32_ShadowCopy():
                if shadow.ID == shadow_id:
                    shadow_copy_path = shadow.DeviceObject
                    return shadow_copy_path, shadow_id
        return None, None
    except Exception:
        print("create_VSC Failed")
        return None, None