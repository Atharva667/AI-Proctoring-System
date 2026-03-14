AI Based Online Exam Proctoring System
Overview

The AI Based Online Exam Proctoring System is a web-based platform designed to conduct secure online examinations with automated monitoring using Artificial Intelligence.

The system integrates Flask, OpenCV, and MySQL to monitor students during online exams and detect suspicious behavior through webcam-based proctoring.

This project was developed as a Capstone Project to demonstrate the integration of AI, web technologies, and database systems.

Features
Student Module

Student registration and login

Secure session management

Online exam interface

Automatic exam submission

View exam results

Teacher Module

Teacher registration

Admin approval workflow

Create exams (MCQ, Short Answer, Paragraph)

Review submitted exams

Evaluate subjective answers

View student results

Admin Module

Approve or reject teacher applications

Monitor exam sessions

View system activity logs

AI Proctoring Features

Face detection using OpenCV

Detect no face in frame

Detect multiple faces

Violation tracking

Automatic exam termination after excessive violations

Technologies Used
Backend

Python

Flask

OpenCV

MySQL

Frontend

HTML

CSS

JavaScript

FontAwesome

Database

MySQL

AI & Computer Vision

OpenCV

NumPy

Project Structure
AI BASED PROCTORING SYSTEM
│
├── backend
│   ├── app.py
│   ├── services
│   │   └── ai_proctoring.py
│   ├── templates
│   ├── static
│   └── requirements.txt
│
├── ai_models
│   └── proctor_engine.py
│
└── README.md
Database Tables

The system uses the following database tables:

students – stores student information

teachers – stores teacher registration and approval status

exam_questions – stores all exam questions

exam_results – stores student exam submissions and results

Setup Instructions
1 Clone the Repository
git clone https://github.com/Atharva667/AI-Proctoring-System.git
2 Navigate to Backend
cd backend
3 Install Dependencies
pip install -r requirements.txt
4 Configure MySQL

Update the database credentials inside app.py:

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="your_password",
        database="ai_proctoring"
    )
5 Run the Application
python app.py

Open in browser:

http://127.0.0.1:5000
AI Proctoring Workflow

Student starts the exam

Webcam captures video frames

Frames are sent to backend

OpenCV detects faces

Violations are recorded

Exam is terminated if violations exceed limit

Future Improvements

Head pose detection

Mobile phone detection

Voice detection

Eye tracking

Real-time admin monitoring dashboard

Advanced AI cheating detection

Developer

Atharva Deshpande
Capstone Project Developer

License

This project is developed for educational purposes only.
