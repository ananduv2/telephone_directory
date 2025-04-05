# 📞 Telephone Directory App

A Flask-based web application for managing personal contacts. Users can register, log in, and manage a list of contacts with profile images uploaded to AWS S3.

---

## 🗂️ Folder Structure

```
/flask_contacts_app/
│
├── static/
│   └── uploads/              # Temporary directory for uploaded display pictures (DPs)
│
├── templates/
│   ├── dashboard.html        # Dashboard displaying contacts
│   ├── login.html            # User login page
│   └── register.html         # User registration page
│
├── app.py                    # Main Flask application
├── config.py                 # Configuration settings (e.g., DB, S3)
├── requirements.txt          # Python dependencies
└── scripts.sql               # SQL script to create required tables
```


---

## ⚙️ Setup Instructions

### 1. 🔧 Create and Activate a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
```

### 2. 📦 Install Required Packages

```bash
pip install -r requirements.txt
```

### 3. ▶️ Running the App
```bash
python app.py
```
Visit: http://localhost:5000

