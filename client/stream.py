from flask import Flask, render_template, Response, request, jsonify
import cv2
import time
import threading

user_input = ""
Islocked = False
face = []
app = Flask(__name__)

camera = cv2.VideoCapture(0)  # use 0 for web camera
#  for cctv camera use rtsp://username:password@ip_address:554/user=username_password='password'_channel=channel_number_stream=0.sdp' instead of camera


def gen_frames():  # generate frame by frame from camera
    while True:
        time.sleep(0.001)
        # Capture frame-by-frame
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
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


@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')


@app.route('/face-identified', methods=['POST'])
def face_identified():
    global face
    face = request.get_json()
    return jsonify(success=True)


def ReadRfid(user_input, Islocked):
    while True:
        if not Islocked:
            try:
                user_input = input()
                # Islocked = True
            except KeyboardInterrupt:
                break
        time.sleep(0.1)


def LoopCheck(user_input):
    global face
    while True:
        print(face)
        if user_input != "" and len(face) != 0:
            if user_input in face:
                print("yes")
            else:
                print("no")
            user_input = ""
        time.sleep(0.1)


if __name__ == '__main__':
    mythread = threading.Thread(target=ReadRfid, args=(user_input, Islocked,))
    mythread.daemon = True
    mythread.start()

    mythread1 = threading.Thread(target=LoopCheck, args=(user_input,))
    mythread1.daemon = True
    mythread1.start()
    app.run(host="127.0.0.1", port="8000", threaded=True)
