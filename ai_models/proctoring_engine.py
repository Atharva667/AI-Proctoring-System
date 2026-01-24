import cv2
import mediapipe as mp
import os
import numpy as np
import datetime
import requests


print("🔥 PROCTOR ENGINE FILE EXECUTED")
input("Press ENTER to start camera...")



# ----------------- INITIALIZATION -----------------
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5)

cap = cv2.VideoCapture(2)
print("Camera opened:", cap.isOpened())
 

if not cap.isOpened():
    print("❌ Camera not opened")
    exit()

print("✅ AI Proctoring Engine Started")

def send_violation(event):
    try:
        requests.post("http://127.0.0.1:5000/log_event", json={
            "event": event
        })
    except Exception as e:
        print("❌ Error sending violation to backend:", e)

        


# ----------------- LOG FUNCTION -----------------
def log_event(message):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "..", "backend", "activity_log.txt")

    with open(log_path, "a") as log:
        log.write(f"{datetime.datetime.now()} - {message}\n")


# ----------------- MAIN LOOP -----------------
while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Frame not received")
        break

    frame = cv2.flip(frame, 1)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    h, w, _ = frame.shape

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    status_text = "Normal"
    color = (0, 255, 0)

    # ----------------- FACE COUNT LOGIC -----------------
    if len(faces) > 1:
        status_text = "Multiple Faces Detected"
        color = (0, 0, 255)
        print("⚠️ Multiple faces detected")
        log_event("Multiple faces detected")
        send_violation("VIOLATION|MULTIPLE_FACES")



    elif len(faces) == 0:
        status_text = "No Face Detected"
        color = (0, 0, 255)
        print("⚠️ No face detected")
        log_event("No face detected")
        send_violation("VIOLATION|NO_FACE")

    # Draw face rectangles
    for (x, y, fw, fh) in faces:
        cv2.rectangle(frame, (x, y), (x + fw, y + fh), color, 2)

    # ----------------- MEDIAPIPE PROCESS -----------------
    results = face_mesh.process(rgb_frame)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:

            # ----------------- EYE TRACKING -----------------
            left_eye = face_landmarks.landmark[33]
            right_eye = face_landmarks.landmark[263]

            left_x = int(left_eye.x * w)
            right_x = int(right_eye.x * w)
            eye_center = (left_x + right_x) // 2

            if eye_center < w * 0.4:
                status_text = "Looking Left"
                color = (0, 0, 255)
                log_event("Looking left")
                send_violation("VIOLATION|LOOKING_LEFT")
            elif eye_center > w * 0.6:
                status_text = "Looking Right"
                color = (0, 0, 255)
                log_event("Looking right")
                send_violation("VIOLATION|LOOKING_RIGHT")
            # ----------------- HEAD POSE -----------------
            face_2d = []
            face_3d = []

            for idx, lm in enumerate(face_landmarks.landmark):
                if idx in [33, 263, 1, 61, 291, 199]:
                    x, y = int(lm.x * w), int(lm.y * h)
                    face_2d.append([x, y])
                    face_3d.append([x, y, lm.z])

            face_2d = np.array(face_2d, dtype=np.float64)
            face_3d = np.array(face_3d, dtype=np.float64)

            focal_length = 1 * w
            cam_matrix = np.array([[focal_length, 0, w / 2],
                                    [0, focal_length, h / 2],
                                    [0, 0, 1]])

            dist_matrix = np.zeros((4, 1), dtype=np.float64)

            success, rot_vec, trans_vec = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_matrix)

            rmat, _ = cv2.Rodrigues(rot_vec)
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

            x_angle = angles[0] * 360
            y_angle = angles[1] * 360

            if y_angle < -10:
                status_text = "Head Turned Left"
                color = (0, 0, 255)
                log_event("Head turned left")
                send_violation("VIOLATION|HEAD_TURNED_LEFT")
            elif y_angle > 10:
                status_text = "Head Turned Right"
                color = (0, 0, 255)
                log_event("Head turned right")
                send_violation("VIOLATION|HEAD_TURNED_RIGHT")
            elif x_angle < -10:
                status_text = "Looking Down"
                color = (0, 0, 255)
                log_event("Looking down")
                send_violation("VIOLATION|LOOKING_DOWN")
            elif x_angle > 10:
                status_text = "Looking Up"
                color = (0, 0, 255)
                log_event("Looking up")
                send_violation("VIOLATION|LOOKING_UP")
    # ----------------- DISPLAY -----------------
    cv2.putText(frame, status_text, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    cv2.imshow("AI Proctoring Engine", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
