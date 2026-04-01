import cv2
import time

# ================= GLOBAL STATE =================
user_states = {}

# ================= FACE DETECTION =================
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

def detect_faces(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(40, 40)
    )
    return faces


# ================= MAIN ANALYSIS =================
def analyze_frame(user_id, frame):

    # ✅ FIX 1: Frame safety
    if frame is None:
        return {
            "faces": 0,
            "multiple_faces": False,
            "movement": False,
            "movement_warnings": 0,
            "face_warnings": 0,
            "terminate": False
        }

    faces = detect_faces(frame)

    # ✅ SAFE face count
    face_count = len(faces) if isinstance(faces, (list, tuple)) else 0

    # ================= INIT USER STATE =================
    if user_id not in user_states:
        user_states[user_id] = {
            "prev_center": None,
            "multi_count": 0,
            "movement_warnings": 0,
            "face_warnings": 0,
            "last_move_time": 0
        }

    state = user_states[user_id]

    # ================= MULTIPLE FACE DETECTION =================
    multiple_faces = False

    if face_count >= 2:
        state["multi_count"] += 1
    else:
        state["multi_count"] = 0

    if state["multi_count"] >= 3:
        multiple_faces = True
        state["face_warnings"] += 1
        state["multi_count"] = 0

    # ================= MOVEMENT DETECTION =================
    movement = False

    if face_count == 1:
        (x, y, w, h) = faces[0]
        center = (x + w // 2, y + h // 2)

        if state["prev_center"] is not None:
            dx = abs(center[0] - state["prev_center"][0])
            dy = abs(center[1] - state["prev_center"][1])

            if (dx + dy > 40) and (time.time() - state["last_move_time"] > 2):
                movement = True
                state["movement_warnings"] += 1
                state["last_move_time"] = time.time()

        state["prev_center"] = center

    # ================= TERMINATION =================
    terminate = False

    if state["movement_warnings"] >= 3 or state["face_warnings"] >= 3:
        terminate = True

    # ================= RESPONSE =================
    return {
        "faces": face_count,
        "multiple_faces": multiple_faces,
        "movement": movement,
        "movement_warnings": state["movement_warnings"],
        "face_warnings": state["face_warnings"],
        "terminate": terminate
    }