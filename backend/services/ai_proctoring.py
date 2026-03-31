import os
import time

user_states = {}

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
    

    

def analyze_frame(user_id, frame):
    faces = detect_faces(frame)

    # Initialize user state
    if user_id not in user_states:
        user_states[user_id] = {
            "prev_center": None,
            "multi_count": 0
        }

    state = user_states[user_id]

    # -------------------------
    # MULTIPLE FACE DETECTION
    # -------------------------
    if len(faces) >= 2:
        state["multi_count"] += 1
    else:
        state["multi_count"] = 0

    multiple_faces = state["multi_count"] >= 3

    # -------------------------
    # MOVEMENT DETECTION
    # -------------------------
    movement = False

    if len(faces) == 1:
        (x, y, w, h) = faces[0]
        center = (x + w//2, y + h//2)

        if state["prev_center"] is not None:
            dx = abs(center[0] - state["prev_center"][0])
            dy = abs(center[1] - state["prev_center"][1])

            if dx + dy > 40:
                movement = True

        state["prev_center"] = center

    return {
        "faces": len(faces),
        "multiple_faces": multiple_faces,
        "movement": movement
    }



import time

def analyze_frame(user_id, frame):
    faces = detect_faces(frame)

    # INIT STATE
    if user_id not in user_states:
        user_states[user_id] = {
            "prev_center": None,
            "multi_count": 0,
            "movement_warnings": 0,
            "face_warnings": 0
        }

    state = user_states[user_id]

    # -------------------------
    # MULTIPLE FACE DETECTION
    # -------------------------
    multiple_faces = False

    if len(faces) >= 2:
        state["multi_count"] += 1
    else:
        state["multi_count"] = 0

    if state["multi_count"] >= 3:
        multiple_faces = True
        state["face_warnings"] += 1
        state["multi_count"] = 0

    # -------------------------
    # MOVEMENT DETECTION
    # -------------------------
    movement = False

    if len(faces) == 1:
        (x, y, w, h) = faces[0]
        center = (x + w//2, y + h//2)

        if state["prev_center"] is not None:
            dx = abs(center[0] - state["prev_center"][0])
            dy = abs(center[1] - state["prev_center"][1])

            if dx + dy > 40:
                movement = True
                state["movement_warnings"] += 1

        state["prev_center"] = center

    # -------------------------
    # TERMINATION CHECK
    # -------------------------
    terminate = False

    if state["movement_warnings"] >= 3 or state["face_warnings"] >= 3:
        terminate = True

    return {
        "faces": len(faces),
        "multiple_faces": multiple_faces,
        "movement": movement,
        "movement_warnings": state["movement_warnings"],
        "face_warnings": state["face_warnings"],
        "terminate": terminate
    }