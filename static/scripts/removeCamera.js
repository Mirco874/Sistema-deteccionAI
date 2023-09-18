const removeCamera = (id) => {
  const updated_connected_cameras = loadItem("connected_cameras").filter(
    (camera) => camera.id != id
  );

    saveConnectedCamerasList(updated_connected_cameras);

    fetch(`/surveillance/remove-camera/${id}`, {
        method: 'post'
      }).then(
        ()=> window.location.replace("/surveillance")
       );


};
