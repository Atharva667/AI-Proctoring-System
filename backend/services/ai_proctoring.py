import cv2
import time
import numpy as np

# Global state to track users across frames
user_states = {}

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

def detect_faces(frame):
    if frame is None:
        return []
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # scaleFactor 1.1 and minNeighbors 5 are more stable for proctoring
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    # Standardize output to a list to prevent "len()" errors on tuples
    return list(faces) if len(faces) > 0 else []

def analyze_frame(user_id, frame):
    if frame is None:
        return {"faces": 0, "multiple_faces": False, "movement": False, "terminate": False}

    faces = detect_faces(frame)
    face_count = len(faces)

    if user_id not in user_states:
        user_states[user_id] = {
            "prev_center": None,
            "multi_count": 0,
            "movement_warnings": 0,
            "face_warnings": 0,
            "last_move_time": 0
        }

    state = user_states[user_id]
    multiple_faces = False
    movement = False

    # --- MULTIPLE FACE LOGIC ---
    if face_count >= 2:
        state["multi_count"] += 1
        if state["multi_count"] >= 2: # 2 consecutive frames to avoid glitches
            multiple_faces = True
            state["face_warnings"] += 1
            state["multi_count"] = 0
    else:
        state["multi_count"] = 0

    # --- MOVEMENT LOGIC ---
    if face_count == 1:
        (x, y, w, h) = faces[0]
        center = (int(x + w // 2), int(y + h // 2))

        if state["prev_center"] is not None:
            dx = abs(center[0] - state["prev_center"][0])
            dy = abs(center[1] - state["prev_center"][1])

            # 25 pixel threshold for 1.5s intervals
            if (dx + dy > 25) and (time.time() - state["last_move_time"] > 2):
                movement = True
                state["movement_warnings"] += 1
                state["last_move_time"] = time.time()
        state["prev_center"] = center
    else:
        state["prev_center"] = None

    # --- TERMINATION ---
    terminate = state["movement_warnings"] >= 3 or state["face_warnings"] >= 3

    return {
        "faces": face_count,
        "multiple_faces": multiple_faces,
        "movement": movement,
        "movement_warnings": state["movement_warnings"],
        "face_warnings": state["face_warnings"],
        "terminate": terminate
    }