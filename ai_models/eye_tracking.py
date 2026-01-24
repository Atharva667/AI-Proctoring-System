import cv2
import mediapipe as mp
import numpy as np

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)


if not cap.isOpened():
    print("❌ Camera not opened")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Frame not received")
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_mesh.process(rgb_frame)

    h, w, _ = frame.shape

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:

            # Left eye landmarks
            left_eye = [33, 133]
            for id in left_eye:
                x = int(face_landmarks.landmark[id].x * w)
                y = int(face_landmarks.landmark[id].y * h)
                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            # Right eye landmarks
            right_eye = [362, 263]
            for id in right_eye:
                x = int(face_landmarks.landmark[id].x * w)
                y = int(face_landmarks.landmark[id].y * h)
                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            # Basic gaze detection (left/right)
            left_x = int(face_landmarks.landmark[33].x * w)
            right_x = int(face_landmarks.landmark[263].x * w)

            eye_center = (left_x + right_x) // 2

            if eye_center < w * 0.4:
                status = "Looking Left"
            elif eye_center > w * 0.6:
                status = "Looking Right"
            else:
                status = "Looking Center"

            cv2.putText(frame, status, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            if status != "Looking Center":
                print("⚠️ Suspicious: Candidate looking away")

    cv2.imshow("AI Proctoring - Eye Tracking", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
