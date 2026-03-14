import mysql.connector
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(BASE_DIR, "exam_questions.txt")

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="localhost",
    database="ai_proctoring"
)

cursor = db.cursor()

if not os.path.exists(FILE):
    print("exam_questions.txt not found")
    exit()

with open(FILE, "r", encoding="utf-8") as f:

    for line in f:

        parts = line.strip().split("|")

        question = parts[0]
        qtype = parts[1]

        option1 = option2 = option3 = option4 = None
        answer = ""

        if qtype == "mcq":
            option1 = parts[2]
            option2 = parts[3]
            option3 = parts[4]
            option4 = parts[5]
            answer = parts[6]

        elif qtype in ["short","paragraph"]:
            answer = parts[2] if len(parts) > 2 else ""

        cursor.execute("""
        INSERT INTO exam_questions
        (question,question_type,option1,option2,option3,option4,correct_answer)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,(
            question,
            qtype,
            option1,
            option2,
            option3,
            option4,
            answer
        ))

db.commit()

cursor.close()
db.close()

print("✅ Questions migrated successfully")