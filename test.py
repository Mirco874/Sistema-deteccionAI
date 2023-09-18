import wmi;

def get_camera_model(dev):
    try:
        return dev.Caption
    except AttributeError:
        return "Modelo desconocido"

def get_connected_cameras_list():
    connected_cameras = []
    c = wmi.WMI()
    wql = "Select * From Win32_USBControllerDevice";
    devices = c.query(wql)
    for device in devices:
        if(device.Dependent.PNPClass == "Camera"):
            connected_cameras.append( device.Dependent.Caption )
    return connected_cameras

get_connected_cameras_list();