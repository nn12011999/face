from flask import Flask, render_template, Response, request, jsonify
import cv2
import time
import threading
#from pyrebase import Firebase
import pyrebase
import RPi.GPIO as GPIO
import datetime

config = {
    "apiKey": "AIzaSyCfTKQ-5sDNvN3QfC6S4oqeKOnbEv7AxzE",
    "authDomain": "iot-smart-home-door-lock-7ccc9.firebaseapp.com",
    "databaseURL": "https://iot-smart-home-door-lock-7ccc9.firebaseio.com",
    "projectId": "iot-smart-home-door-lock-7ccc9",
    "storageBucket": "iot-smart-home-door-lock-7ccc9.appspot.com",
    "messagingSenderId": "513607106040",
    "appId": "1:513607106040:web:d627644390357454e76a0d"
}

#firebase = Firebase(config)
firebase = pyrebase.initialize_app(config)
db = firebase.database()
auth = firebase.auth()
storage = firebase.storage()

ledPin = 23 # Broadcom pin 23 (P1 pin 16)
GPIO.setmode(GPIO.BCM)
GPIO.setup(ledPin, GPIO.OUT) # LED pin set as output
GPIO.output(ledPin, GPIO.LOW)

class FaceAndTime:
    def __init__(self, name, time):
        self.name = name
        self.time = time

user_input = None
Card_check = 0
Open_at = 0
Islocked = True
face = {}
lock = threading.Lock()
app = Flask(__name__)

camera = cv2.VideoCapture(0)  # use 0 for web camera
#  for cctv camera use rtsp://username:password@ip_address:554/user=username_password='password'_channel=channel_number_stream=0.sdp' instead of camera


def gen_frames():  # generate frame by frame from camera
    while True:
        time.sleep(0.001)
        # Capture frame-by-frame
        success, frame = camera.read()  # read the camera frame
        if not success:
            continue
        flag, buffer = cv2.imencode('.jpg', frame)
        if not flag:
            continue
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
                b'Content-Type:image/jpeg\r\n'
                b'Content-Length: ' + f"{len(frame)}".encode() + b'\r\n'
                b'\r\n' + frame + b'\r\n')  # concat frame one by one and show result


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# @app.route('/')
# def index():
#     """Video streaming home page."""
#     return render_template('index.html')


@app.route('/face-identified', methods=['POST'])
def face_identified():
    global face
    with lock:
        for f in request.get_json():
            face[f] = time.time()
        print(face)
        return jsonify(success=True)


def ReadRfid():
    global user_input,Card_check,Islocked
    while True:
        if Islocked and user_input == None:
            try:
                temp = input()
                # Islocked = True
                print("vui long doi")
                temp = db.child("Users").child(temp).get()
                if temp != None:
                    with lock:
                        user_input = temp.val()
                        Card_check = time.time()
                        print("plz wait for face recognization")
                #print(db.child('Users').equal_to(str(user_input)).get().val().values())
            except KeyboardInterrupt:
                break
        time.sleep(0.1)


def LoopCheck():
    global face ,user_input,Card_check, Open_at,Islocked,lock
    IsChange = False
    while True:

        t = time.time()
        with lock:
            for f in face.copy():
                if t-face[f] > 15:
                    face.pop(f)
                    IsChange = True
        if t-Card_check>15 and Card_check!=0:
            with lock:
                user_input = None
                Card_check = 0
                print("timeout")
        if t-Open_at > 15 and Open_at!=0:
            with lock:
                Islocked = True
                Open_at = 0
                GPIO.output(ledPin, GPIO.LOW)
                print("door close")
        if user_input in face and Islocked == True:
            data = {"name": face[user_input],"rfid":user_input,"time":str(datetime.datetime.now())}
            db.child("Access").push(data)
            with lock:
                user_input = None
                Card_check = 0
                Islocked = False
                Open_at = t 
                GPIO.output(ledPin, GPIO.HIGH) 
                print("door open")   
        if IsChange:
            print(face)
            IsChange = False
        time.sleep(0.1)


if __name__ == '__main__':
    try:
        mythread = threading.Thread(target=ReadRfid, args=())
        mythread.daemon = True
        mythread.start()

        mythread1 = threading.Thread(target=LoopCheck, args=())
        mythread1.daemon = True
        mythread1.start()
        app.run(host="192.168.137.189", port="8000", threaded=True)
    except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
        GPIO.cleanup() # cleanup all GPIO
