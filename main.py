from flask import Flask, render_template, request, jsonify, redirect, Response;
from flask_socketio import SocketIO, send
import wmi;
import cv2;
import mediapipe as mp
import numpy as np
import tensorflow as tf
import utils.drawer as drawer;
from  utils.model_configuration import ModelConfiguration;
from utils.multipose_detector import MultiposeDetector;

import tensorflow_hub as hub
from matplotlib import pyplot as plt

app=Flask(__name__)
app.config["SECRET"] = "secret";
socketIO = SocketIO(app, cors_allowed_origins="*");

def get_connected_cameras_list():
    connected_cameras = [];
    index = 0;

    c = wmi.WMI();
    wql = "Select * From Win32_USBControllerDevice";
    devices = c.query(wql);

    for device in devices:
        if(device.Dependent.PNPClass == "Camera"):
            connected_cameras.append( { "id": index,  "name": device.Dependent.Caption} )
    return connected_cameras;

def releaseAllCameras():
    global cap;
    if(cap):
        cap.release(); 

read_1 = True;
cap = None;

connected_cameras_list = get_connected_cameras_list();

selected_cameras = [
    {
        "activated": False,
        "deviceId": None,
        "name": None,
        "activeModel": None ,
        "items": [],
        "inference": 0
    }
];

connected_devices =[];

def addCamera ( new_connected_devices_state ):
    global connected_devices;
    connected_devices = new_connected_devices_state["cameras"];


def get_model(model_name):
    model_configuration = model_manager.get_model_configuration(model_name);

    if(model_configuration["enable"]):
        if(model_configuration["name"] == "haar_cascade_face_detection"):
            return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml");
    
        elif(model_configuration["name"] == "object_detection"):
            return None;

        elif(model_configuration["name"] == "multipose-criminal_behaviour_detection"):
            print("modelo")
            model = hub.load('https://tfhub.dev/google/movenet/multipose/lightning/1')
            movenet = model.signatures['serving_default'];
            return MultiposeDetector(model = model, movenet = movenet);

    else:
        return None;



def loop_through_people(frame, keypoints_with_scores, edges, confidence_threshold): 
    for person in keypoints_with_scores:
        draw_connections(frame, person, edges, confidence_threshold)
        draw_keypoints(frame, person, confidence_threshold)


def draw_keypoints(frame, keypoints, confidence_threshold):
    y, x, c = frame.shape
    shaped = np.squeeze(np.multiply(keypoints, [y,x,1]))
    
    for kp in shaped:
        ky, kx, kp_conf = kp
        if kp_conf > confidence_threshold:
            cv2.circle(frame, (int(kx), int(ky)), 6, (0,255,0), -1)


def draw_connections(frame, keypoints, edges, confidence_threshold):
    y, x, c = frame.shape
    shaped = np.squeeze(np.multiply(keypoints, [y,x,1]))
    
    for edge, color in edges.items():
        p1, p2 = edge
        y1, x1, c1 = shaped[p1]
        y2, x2, c2 = shaped[p2]
        
        if (c1 > confidence_threshold) & (c2 > confidence_threshold):      
            cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0,0,255), 4)



def detect(camera_id):
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    face_detector = get_model("haar_cascade_face_detection");
    # join_points_detector = get_model("multipose-criminal_behaviour_detection");

    # model = hub.load('https://tfhub.dev/google/movenet/multipose/lightning/1')
    # movenet = model.signatures['serving_default'];


    while (cap.isOpened()):
        ret, frame = cap.read();
        if(ret):
            gray_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY);

            if(face_detector != None):
                drawer.draw_rectangle_on_face(gray_image = gray_image, frame= frame, model= face_detector)
                socketIO.emit('event', {
                    'type': 'warning',
                    'message': 'nueva cara detectada',
                    'date_time': ''  
                })

            # if(model != None):
            #     img = frame.copy()
            #     img = tf.image.resize_with_pad(tf.expand_dims(img, axis=0), 256,256)
            #     input_img = tf.cast(img, dtype=tf.int32)
            
            #     # Detection section
            #     results = movenet(input_img)
            #     keypoints_with_scores = results['output_0'].numpy()[:,:,:51].reshape((6,17,3))
            
            #     # Render keypoints 
            #     loop_through_people(frame, keypoints_with_scores, EDGES, 0.2)


            (flag, encodedImage) = cv2.imencode(".jpg", frame);
            
            if not flag:
                continue;
            yield( b'--frame\r\n' b'Content-Type: image\jepg\r\n\r\n' + bytearray(encodedImage) + b'\r\n' )
        else:
            cap.release(); 
            break; 

    cap.release();






            
@app.route("/")
def dashboardPage():
    releaseAllCameras();
    return render_template("dashboard/dashboard.html");

@app.route("/auth/login")
def loginPage():
    releaseAllCameras();
    return render_template("login/login.html");

@app.route("/auth/register")
def registerPage():
    releaseAllCameras();
    return render_template("register/register.html");

# @app.route("/surveillancePage", methods = ["GET"])
# def surveillancePage():
#     return render_template("surveillance/surveillance.html", connected_cameras = connected_cameras_list, connected_devices=connected_devices );


# @app.route("/load_connected_cameras", methods = ["POST"])
# def loadCamerasPage():
#     selected_cameras.clear();
#     selected_cameras.append(request.json.get("cameras"))
#     return redirect(location="");

@app.route("/surveillance/one-camera-image")
def oneCameraImage():
    if(len(connected_devices) != 1 ):
        return redirect("/surveillance");
    return render_template("surveillance/one_camera_image.html", connected_cameras=connected_cameras_list, connected_devices=connected_devices );

@app.route("/surveillance/two-camera-image")
def twoCameraImage():
    if(len(connected_devices) != 2 ):
        return redirect("/surveillance");
    return render_template("surveillance/two_camera_image.html", connected_cameras=connected_cameras_list, connected_devices=connected_devices );

@app.route("/surveillance/more-cameras-image")
def moreThanTwoCameraImage():
    if(len(connected_devices) == 0 or len(connected_devices) < 3 ):
        return redirect("/surveillance");
    return render_template("surveillance/more_cameras_image.html", connected_cameras=connected_cameras_list, connected_devices=connected_devices );

@app.route("/surveillance/no-cameras-added")
def noCamerasAdded():
    global connected_devices;
    if(len(connected_devices) > 0 ):
        return redirect("/surveillance");
    return render_template("surveillance/surveillance.html", connected_cameras = connected_cameras_list, connected_devices=connected_devices );


@app.route("/surveillance")
def CameraImagePage():
    global connected_devices;

    if(len(connected_devices) == 0):
        return redirect("surveillance/no-cameras-added");

    elif(len(connected_devices) == 1 ):
        return redirect("surveillance/one-camera-image");

    elif(len(connected_devices) == 2 ):
        return redirect("surveillance/two-camera-image");

    elif(len(connected_devices) > 2 ):
        return redirect("surveillance/more-cameras-image");


@app.route("/surveillance/register", methods = ["POST"])
def registerCameraPage():
    addCamera(request.json)
    return redirect("surveillance", 200);


@app.route("/surveillance/remove-camera/<id>", methods = ["POST"])
def disconnectCamera(id):
    global connected_devices;
    connected_devices = [camera for camera in connected_devices if camera["id"] != id]

    print(connected_devices)
    return redirect("surveillance", 200);

@socketIO.on("detections")
def handle_detections():
    send("mensaje del servidor", broadcast=True)

@app.route("/video_feed/<id>")
def video_feed(id):
    print(id);
    return Response(detect(id), mimetype = "multipart/x-mixed-replace; boundary=frame")


@app.route("/video-test")
def index():
    return render_template("surveillance/video_test.html");



@socketIO.on('connect')
def connect():
    print('client connected');





# @app.route("/")
# def index():
#     return render_template("index.html");

# @app.route("/video_feed")
# def video_feed():
#     return Response(detect(), mimetype = "multipart/x-mixed-replace; boundary=frame")
 

            # <!-- <img src="{{ url_for('video_feed') }}" alt="" srcset=""> -->
if __name__ == "__main__":
    socketIO.run(app, host = "localhost");