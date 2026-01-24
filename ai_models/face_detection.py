import cv2
import datetime

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

if face_cascade.empty():
    print("❌ Error loading cascade")
    exit()

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Camera not opened")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Frame not received")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

    # ---- PROCTORING LOGIC ----
    if len(faces) > 1:
        print("⚠️ Multiple faces detected - Suspicious Activity")
    elif len(faces) == 0:
        print("⚠️ No face detected - Candidate away from screen")

    # ---- DRAW RECTANGLES ----
    for (x, y, w, h) in faces:
        if len(faces) > 1:
            color = (0, 0, 255)   # Red
        else:
            color = (0, 255, 0)   # Green

        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

    cv2.imshow("AI Proctoring - Face Monitoring", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC key
        break

cap.release()
cv2.destroyAllWindows()
