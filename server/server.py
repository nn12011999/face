from flask import Flask, render_template, Response, request, jsonify
from time import time
import face_recognition
import cv2
import numpy as np
import time
import requests
import threading

# This is a demo of running face recognition on live video from your webcam. It's a little more complicated than the
# other example, but it includes some basic performance tweaks to make things run a lot faster:
#   1. Process each video frame at 1/4 resolution (though still display it at full resolution)
#   2. Only detect faces in every other frame of video.

# PLEASE NOTE: This example requires OpenCV (the `cv2` library) to be installed only to read from your webcam.
# OpenCV is *not* required to use the face_recognition library. It's only required if you want to run this
# specific demo. If you have trouble installing it, try any of the other demos that don't require it instead.
client_url="http://192.168.137.189:8000"
video_url=client_url+"/video_feed"
face_url = client_url + "/face-identified"
# Get a reference to webcam #0 (the default one)
video_capture = cv2.VideoCapture(video_url)

# Load a sample picture and learn how to recognize it.
obama_image = face_recognition.load_image_file("obama.jpg")
obama_face_encoding = face_recognition.face_encodings(obama_image)[0]

# Load a second sample picture and learn how to recognize it.
biden_image = face_recognition.load_image_file("biden.jpg")
biden_face_encoding = face_recognition.face_encodings(biden_image)[0]

# Create arrays of known face encodings and their names
known_face_encodings = [
    obama_face_encoding,
    biden_face_encoding
]
known_face_names = [
    "Barack Obama",
    "Joe Biden"
]
frames = ""
lock = threading.Lock()
app = Flask(__name__)

def recognition():
    global frames,lock
    # Initialize some variables
    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = 0

    while True:
        # Grab a single frame of video
        ret, frame = video_capture.read()

        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = small_frame[:, :, ::-1]

        # Only process every other frame of video to save time
        if process_this_frame == 30:
            # Find all the faces and face encodings in the current frame of video
            first = time.time()
            face_locations = face_recognition.face_locations(rgb_small_frame)
            second = time.time()
            face_encodings = face_recognition.face_encodings(
                rgb_small_frame, face_locations)
            face_names = []
            face2send = []
            third = time.time()
            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                matches = face_recognition.compare_faces(
                    known_face_encodings, face_encoding)
                name = "Unknown"

                # # If a match was found in known_face_encodings, just use the first one.
                # if True in matches:
                #     first_match_index = matches.index(True)
                #     name = known_face_names[first_match_index]

                # Or instead, use the known face with the smallest distance to the new face
                face_distances = face_recognition.face_distance(
                    known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]

                if name != "Unknown":
                    face2send.append(name)
                face_names.append(name)
            if len(face2send) > 0:
                x = requests.post(
                    face_url, json=face2send)
                time.sleep(0.1)
            process_this_frame = 0
            # print("location " + str(round(second-first, 7))
            #     + "   encoding " + str(round(third-second, 7))
            #     + "   recognition " + str(round(time.time()-third, 7)))
        process_this_frame += 1

        # Display the results
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box around the face
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            # Draw a label with a name below the face
            cv2.rectangle(frame, (left, bottom - 35),
                        (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6),
                        font, 1.0, (255, 255, 255), 1)

        # Display the resulting image
        #cv2.imshow('Video', frame)
        with lock:
            frames = frame
    # Release handle to the webcam





@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('users_info.html')

def gen_frames():  # generate frame by frame from camera
    global frames,lock
    while True:
        time.sleep(0.001)
        # Capture frame-by-frame
        with lock:
            ret, buffer = cv2.imencode('.jpg', frames)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
                b'Content-Type:image/jpeg\r\n'
                b'Content-Length: ' + f"{len(frame)}".encode() + b'\r\n'
                b'\r\n' + frame + b'\r\n')  # concat frame one by one and show result

if __name__ == '__main__':
    try:
        mythread1 = threading.Thread(target=recognition, args=())
        mythread1.daemon = True
        mythread1.start()

        app.run(host="127.0.0.1", port="5000", threaded=True)
    except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
        GPIO.cleanup() # cleanup all GPIO
        video_capture.release()
