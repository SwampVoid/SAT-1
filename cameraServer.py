import cv2
import time
import os
import threading
import numpy as np
import notificationServer
import addNotification
import datetime
import requests
from flask import Flask, Response, render_template, jsonify, send_from_directory
from deepface import DeepFace
from flask_cors import CORS

dataBasePath = "dataBase"
faceBox = None       # (x, y, w, h) in full-resolution coordinates
faceName = None       # name of whoever was last matched, or "Unknown"
lock = threading.Lock()
busy = False

outputFrame = None            # latest processed frame, shared with Flask
outputLock = threading.Lock()  # separate lock just for the output frame

DETECT_SCALE = 0.5      # shrink frame before detection
FRAME_SKIP = 15          # run recognition every N frames
MODEL_NAME = "SFace"    # much lighter/faster than VGG-Face
DETECTOR = "opencv"     # fast; swap to "mediapipe" if this keeps causing issues
MATCH_THRESHOLD = 0.6   # lower = stricter match, tune as needed

lastUnauthorizedAlert = 0
ALERT_DEBOUNCE_SECONDS = 30
alertLock = threading.Lock()

knownFaces = {}

app = Flask(__name__)
CORS(app)


def cosineDistance(a, b):
    a = np.array(a)
    b = np.array(b)
    return 1 - (np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def sendUnauthorizedAlert():
    try:
        response = requests.post(
            "http://127.0.0.1:5001/notifications",
            json={
                "type": "Motion",
                "location": "Front Door",
                "img": "/Icons/unauthorizedPerson.jpg"
            }
        )
        if response.ok:
            print("Unauthorized alert sent.")
        else:
            print(f"Failed to send alert: {response.status_code} {response.text}")
    except Exception as e:
        print("Error sending unauthorized alert:", e)


def loadKnownFaces():
    """Compute a reference embedding for every image in dataBase.
    The filename (without extension) is used as that person's display name."""
    global knownFaces
    for fname in os.listdir(dataBasePath):
        if fname.lower().endswith((".png", ".jpg", ".jpeg")):
            path = os.path.join(dataBasePath, fname)
            name = os.path.splitext(fname)[0]
            rep = DeepFace.represent(img_path=path, model_name=MODEL_NAME,
                                      detector_backend=DETECTOR, enforce_detection=False)
            knownFaces[name] = rep[0]["embedding"]
            print("Loaded known face:", name)

    if not knownFaces:
        print("No reference images found in", dataBasePath)
        exit()


def findBestMatch(embedding):
    """Compare against every known face, return (name, distance) of the closest one."""
    bestName = None
    bestDistance = None
    for name, knownEmbedding in knownFaces.items():
        distance = cosineDistance(knownEmbedding, embedding)
        if bestDistance is None or distance < bestDistance:
            bestDistance = distance
            bestName = name
    return bestName, bestDistance


def runRecognition(frame):
    global faceBox, faceName, busy, lastUnauthorizedAlert
    try:
        small = cv2.resize(frame, (0, 0), fx=DETECT_SCALE, fy=DETECT_SCALE)

        faces = DeepFace.extract_faces(img_path=small, detector_backend=DETECTOR,
                                        enforce_detection=False)

        if not faces or faces[0]["confidence"] == 0:
            with lock:
                faceBox = None
                faceName = None
            return

        area = faces[0]["facial_area"]
        x = int(area["x"] / DETECT_SCALE)
        y = int(area["y"] / DETECT_SCALE)
        w = int(area["w"] / DETECT_SCALE)
        h = int(area["h"] / DETECT_SCALE)

        faceCrop = frame[y:y+h, x:x+w]
        if faceCrop.size == 0:
            with lock:
                faceBox = None
                faceName = None
            return

        rep = DeepFace.represent(img_path=faceCrop, model_name=MODEL_NAME,
                                  detector_backend="skip", enforce_detection=False)
        embedding = rep[0]["embedding"]

        name, distance = findBestMatch(embedding)
        print(f"Best match: {name}  Distance: {distance:.3f}")

        matchedName = name if distance < MATCH_THRESHOLD else "Unknown"

        with lock:
            faceBox = (x, y, w, h)
            faceName = matchedName

        # --- Debounced unauthorized-user notification ---
        if matchedName == "Unknown":
            now = time.time()
            with alertLock:
                if now - lastUnauthorizedAlert >= ALERT_DEBOUNCE_SECONDS:
                    lastUnauthorizedAlert = now
                    threading.Thread(target=sendUnauthorizedAlert, daemon=True).start()

    except Exception as e:
        print("Recognition error:", e)
        with lock:
            faceBox = None
            faceName = None
    finally:
        busy = False


def cameraLoop():
    """Runs forever in a background thread. Grabs frames, kicks off recognition
    every FRAME_SKIP frames, draws the box/label, and stores the result in
    outputFrame so the Flask route can read it."""
    global busy, outputFrame

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    time.sleep(1)

    if not cap.isOpened():
        print("Camera failed to open at all.")
        return

    frameCount = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            continue

        frameCount += 1

        if frameCount % FRAME_SKIP == 0 and not busy:
            busy = True
            threading.Thread(target=runRecognition, args=(frame.copy(),), daemon=True).start()

        with lock:
            currentBox = faceBox
            currentName = faceName

        if currentBox is not None:
            x, y, w, h = currentBox
            color = (0, 255, 0) if currentName != "Unknown" else (0, 0, 255)
            label = currentName if currentName else ""

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, label, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        with outputLock:
            outputFrame = frame.copy()


def encodeCamera():
    """Continuously yields the latest processed frame as an MJPEG stream."""
    global outputFrame
    while True:
        with outputLock:
            if outputFrame is None:
                continue
            ret, buffer = cv2.imencode(".jpg", outputFrame)
            if not ret:
                continue
            frameBytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frameBytes + b'\r\n')

        time.sleep(0.03)  # roughly caps output at ~30fps


@app.route('/video_feed')
def video_feed():
    return Response(encodeCamera(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/dataBase/<path:filename>')
def serve_face(filename):
    return send_from_directory(dataBasePath, filename)


@app.route('/current_face')
def current_face():
    with lock:
        name = faceName

    if name is None:
        return jsonify({"name": None, "img": None})

    if name == "Unknown":
        return jsonify({"name": "Unknown", "img": None})

    # Match found — locate their reference image file (extension may vary)
    for fname in os.listdir(dataBasePath):
        if os.path.splitext(fname)[0] == name:
            return jsonify({"name": name, "img": f"/dataBase/{fname}"})

    return jsonify({"name": name, "img": None})


if __name__ == "__main__":
    if not os.path.exists(dataBasePath):
        print("Data Base Path does not exist!")
        exit()

    print("Loading known faces...")
    loadKnownFaces()

    print("Warming up model...")
    DeepFace.build_model(task="facial_recognition", model_name=MODEL_NAME)
    print("Model ready.")

    threading.Thread(target=cameraLoop, daemon=True).start()
    threading.Thread(target=notificationServer.start, daemon=True).start()

    time.sleep(1)
    addNotification.addNotf()

    # use_reloader=False is important: Flask's debug reloader spawns a second
    # process, which would start the camera thread (and open the webcam) twice
    app.run(debug=True, use_reloader=False)