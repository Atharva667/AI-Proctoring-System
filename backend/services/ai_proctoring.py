import cv2
import mediapipe as mp
mp_face_detection = mp.solutions.face_detection

def detect_faces(frame):

    face_detection = mp_face_detection.FaceDetection(
        model_selection=0,
        min_detection_confidence=0.5
    )

    results = face_detection.process(frame)

    face_count = 0

    if results.detections:
        face_count = len(results.detections)

    return face_count