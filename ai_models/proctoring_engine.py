# ai_models/proctoring_engine.py

import cv2
import numpy as np

class ProctoringEngine:

    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # Tracking
        self.prev_x = None
        self.prev_y = None

        self.face_present_frames = 0
        self.no_face_frames = 0
        self.multi_face_frames = 0

        # Violations
        self.violations = {
            "no_face": 0,
            "multiple_faces": 0,
            "movement": 0,
            "camera_block": 0
        }

    # -------------------------
    # DARK FRAME DETECTION
    # -------------------------
    def is_dark(self, frame):
        return np.mean(frame) < 50

    # -------------------------
    # MAIN PROCESS FUNCTION
    # -------------------------
    def process_frame(self, frame):

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=6,
            minSize=(50, 50)
        )

        # -------------------------
        # NO FACE (SMART TIMER)
        # -------------------------
        if len(faces) == 0:
            self.no_face_frames += 1
            self.face_present_frames = 0

            if self.no_face_frames > 5:
                self.violations["no_face"] += 1
                self.no_face_frames = 0

        else:
            self.face_present_frames += 1
            self.no_face_frames = 0

        # -------------------------
        # MULTIPLE FACES
        # -------------------------
        if len(faces) > 1:
            self.multi_face_frames += 1

            if self.multi_face_frames >= 3:
                self.violations["multiple_faces"] += 1
                self.multi_face_frames = 0
        else:
            self.multi_face_frames = 0

        # -------------------------
        # MOVEMENT DETECTION
        # -------------------------
        if len(faces) == 1:
            (x, y, w, h) = faces[0]

            if self.prev_x is not None:
                movement = abs(x - self.prev_x) + abs(y - self.prev_y)

                if movement > 50:
                    self.violations["movement"] += 1

            self.prev_x = x
            self.prev_y = y

        # -------------------------
        # CAMERA BLOCK
        # -------------------------
        if self.is_dark(frame):
            self.violations["camera_block"] += 1

        # -------------------------
        # AI METRICS (IMPORTANT)
        # -------------------------

        # Face Confidence
        face_confidence = min(self.face_present_frames * 10, 100)

        # Attention Score
        attention_score = 100 - (
            self.violations["no_face"] * 10 +
            self.violations["movement"] * 2 +
            self.violations["multiple_faces"] * 15
        )
        attention_score = max(0, attention_score)

        # Cheating Score
        cheating_score = (
            self.violations["no_face"] * 10 +
            self.violations["multiple_faces"] * 20 +
            self.violations["movement"] * 5 +
            self.violations["camera_block"] * 15
        )
        cheating_score = min(cheating_score, 100)

        # Risk Level
        if cheating_score <= 30:
            risk = "NORMAL"
        elif cheating_score <= 70:
            risk = "SUSPICIOUS"
        else:
            risk = "HIGH RISK"

        return {
            "violations": self.violations,
            "face_confidence": face_confidence,
            "attention_score": attention_score,
            "cheating_score": cheating_score,
            "risk_level": risk
        }