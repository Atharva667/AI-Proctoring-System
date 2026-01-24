.

🎯 AI Based Proctoring System

An AI-powered online examination proctoring system designed to ensure fair and secure exams by monitoring candidates using automated checks like camera verification, activity logging, and exam flow control.

🚀 Features

🔐 Secure Login & Registration system

📷 Camera verification before exam

📝 Online exam interface

🤖 AI-based behavior & activity monitoring (foundation)

📊 Result generation & viewing

🧑‍💼 Admin panel for monitoring

📁 Properly structured backend & frontend

🗂 Activity logging for audit purposes

🧩 Project Structure
AI BASED PROCTORING SYSTEM
│
├── admin_panel
│   └── index.html
│
├── ai_models
│   └── (AI/ML related models)
│
├── backend
│   ├── static
│   │   ├── css
│   │   │   ├── dashboard.css
│   │   │   ├── home.css
│   │   │   ├── login.css
│   │   │   ├── register.css
│   │   │   └── view_result.css
│   │   ├── js
│   │   └── models
│   │
│   ├── templates
│   │   ├── camera_verify.html
│   │   ├── dashboard.html
│   │   ├── exam.html
│   │   ├── exam_success.html
│   │   ├── home.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── result.html
│   │   └── view_result.html
│   │
│   ├── app.py
│   ├── activity_log.txt
│   └── exam_results.txt
│
├── student_exam
│   ├── exam_fixed.html
│   └── test.html
│
├── tempCodeRunnerFile.py
└── README.md

🛠 Tech Stack

Frontend: HTML5, CSS3, JavaScript

Backend: Python (Flask)

AI Layer: Computer Vision (OpenCV – planned/extendable)

Database: File-based (can be extended to MySQL / MongoDB)

Tools: VS Code, Git, GitHub

⚙️ How to Run the Project
1️⃣ Clone the Repository
git clone https://github.com/Atharva667/AI-Proctoring-System.git

2️⃣ Navigate to Project Folder
cd "AI BASED PROCTORING SYSTEM"

3️⃣ Install Required Packages
pip install flask opencv-python

4️⃣ Run the Server
python backend/app.py

5️⃣ Open in Browser
http://127.0.0.1:5000/

🔮 Future Enhancements

👁 Eye-gaze & head-movement detection

📱 Mobile compatibility

📡 Live admin monitoring dashboard

🧠 Advanced ML-based cheating detection

🗄 Database integration (MySQL/MongoDB)

🔐 JWT-based authentication

👨‍💻 Author

Atharva Deshpande
📌 AI & Software Developer
🔗 GitHub: Atharva667
