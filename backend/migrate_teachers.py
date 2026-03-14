import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="localhost",
    database="ai_proctoring"
)

cursor = db.cursor()

with open("teacher_applications.txt","r") as file:

    for line in file:

        parts = line.strip().split(",")

        if len(parts) < 5:
            continue

        name = parts[0]
        email = parts[1]
        mobile = parts[2]
        status = parts[3]
        rejection_reason = parts[4]

        query = """
      INSERT IGNORE INTO teachers(name,email,mobile,status,rejection_reason)
        VALUES (%s,%s,%s,%s,%s)
        """

        cursor.execute(query,(name,email,mobile,status,rejection_reason))

db.commit()

cursor.close()
db.close()

print("Teachers migrated successfully.")