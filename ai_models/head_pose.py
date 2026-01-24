import cv2
import mediapipe as mp
import numpy as np

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Camera not opened")
    exit()

while True:
    success, frame = cap.read()
    if not success:
        print("❌ Frame not received")
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    h, w, _ = frame.shape

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
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

            x = angles[0] * 360
            y = angles[1] * 360
            z = angles[2] * 360

            if y < -10:
                status = "Looking Left"
                color = (0, 0, 255)
            elif y > 10:
                status = "Looking Right"
                color = (0, 0, 255)
            elif x < -10:
                status = "Looking Down"
                color = (0, 0, 255)
            elif x > 10:
                status = "Looking Up"
                color = (0, 0, 255)
            else:
                status = "Looking Forward"
                color = (0, 255, 0)

            cv2.putText(frame, status, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

            if status != "Looking Forward":
                print(f"⚠️ Suspicious Head Movement: {status}")

    cv2.imshow("AI Proctoring - Head Pose Detection", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
