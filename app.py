import os
import uuid
import boto3 #type:ignore
import bcrypt #type:ignore
from flask import Flask, render_template, request, redirect, url_for, session, flash #type:ignore
import mysql.connector #type:ignore
from config import DB_CONFIG
from werkzeug.utils import secure_filename #type:ignore

app = Flask(__name__)
app.secret_key = 'testkey'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
S3_BUCKET = 'tkm-aws-workshop'
S3_REGION = 'ap-south-1'
s3_client = boto3.client('s3')

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------- LOGIN -------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')


# ------------------- REGISTER -------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("Username already taken. Please choose another.", "danger")
            cursor.close()
            conn.close()
            return render_template('register.html')

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()

        cursor.close()
        conn.close()

        flash("Registered successfully. You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


# ------------------- DASHBOARD -------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM contacts WHERE user_id=%s ORDER BY name ASC", (session['user_id'],))
    contacts = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('dashboard.html', contacts=contacts)

# ------------------- ADD CONTACT -------------------
@app.route('/add', methods=['POST'])
def add_contact():
    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    dp = request.files.get('dp')

    image_url = None
    if dp and dp.filename:
        original_filename = secure_filename(dp.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        upload_folder = os.path.join('static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        local_path = os.path.join(upload_folder, unique_filename)
        dp.save(local_path)

        s3_key = f'uploads/{unique_filename}'

        try:
            with open(local_path, 'rb') as f:
                s3_client.upload_fileobj(
                    f,
                    S3_BUCKET,
                    s3_key,
                    ExtraArgs={'ACL': 'public-read', 'ContentType': dp.content_type}
                )
            image_url = f'https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}'

            os.remove(local_path)

        except Exception as e:
            print("S3 Upload Error:", e)
            flash('Image upload failed', 'danger')
            return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO contacts (user_id, name, phone, email, dp) VALUES (%s, %s, %s, %s, %s)",
        (session['user_id'], name, phone, email, image_url)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))


# ------------------- EDIT CONTACT -------------------
@app.route('/edit_contact/<int:id>', methods=['POST'])
def edit_contact(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']

    dp_file = request.files.get('dp')
    dp_url = None

    if dp_file and dp_file.filename != '' and allowed_file(dp_file.filename):
        original_filename = secure_filename(dp_file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        upload_folder = os.path.join('static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        local_path = os.path.join(upload_folder, unique_filename)
        dp_file.save(local_path)

        s3_key = f'uploads/{unique_filename}'

        try:
            with open(local_path, 'rb') as f:
                s3_client.upload_fileobj(
                    f,
                    S3_BUCKET,
                    s3_key,
                    ExtraArgs={'ACL': 'public-read', 'ContentType': dp_file.content_type}
                )
            dp_url = f'https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}'

            os.remove(local_path)

        except Exception as e:
            print("S3 Upload Error:", e)
            flash('Failed to update profile picture', 'danger')
            return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if dp_url:
        cursor.execute("""
            UPDATE contacts
            SET name = %s, phone = %s, email = %s, dp = %s
            WHERE id = %s AND user_id = %s
        """, (name, phone, email, dp_url, id, session['user_id']))
    else:
        cursor.execute("""
            UPDATE contacts
            SET name = %s, phone = %s, email = %s
            WHERE id = %s AND user_id = %s
        """, (name, phone, email, id, session['user_id']))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))


# ------------------- DELETE CONTACT -------------------
@app.route('/delete_contact/<int:id>', methods=['POST'])
def delete_contact(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contacts WHERE id = %s AND user_id = %s", (id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))


# ------------------- CHANGE PASSWORD -------------------
@app.route('/change-password', methods=['POST'])
def change_password():
    current = request.form['current'].encode('utf-8')
    new = request.form['new'].encode('utf-8')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT password FROM users WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()

    if user and bcrypt.checkpw(current, user['password'].encode('utf-8')):
        new_hashed = bcrypt.hashpw(new, bcrypt.gensalt()).decode('utf-8')
        cursor.execute("UPDATE users SET password=%s WHERE id=%s", (new_hashed, session['user_id']))
        conn.commit()
        flash("Password changed successfully.", "success")
    else:
        flash("Current password is incorrect.", "danger")

    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))

# ------------------- LOGOUT -------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
