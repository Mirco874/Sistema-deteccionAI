export const loadItem = ( itemName ) =>{
    item = localStorage.getItem(itemName)
    item? item : "[]";
}


export const saveConnectedCamerasList = ( state ) =>{
    localStorage.setItem("connected_cameras", JSON.stringify(state));
}


