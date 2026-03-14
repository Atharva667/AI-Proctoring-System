import os

# Disable AI detection when running on Render
if os.environ.get("RENDER"):

    print("AI detection disabled on cloud")

    def detect_faces(frame):
        return 1

else:
    import mediapipe as mp

    mp_face_detection = mp.solutions.face_detection
    face_detection = mp_face_detection.FaceDetection()

    def detect_faces(frame):
        results = face_detection.process(frame)

        if not results.detections:
            return 0

        return len(results.detections)