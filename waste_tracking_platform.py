# waste_tracking_platform.py

from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd
import os
import io
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from openpyxl import Workbook

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'secret_key_for_demo_only')

users = {
    "admin": {"password": generate_password_hash("admin123"), "role": "admin", "email": "admin@example.com"},
    "viewer": {"password": generate_password_hash("viewer123"), "role": "viewer", "email": "viewer@example.com"}
}
bins = {}
waste_movements = []

EXPORT_FOLDER = os.environ.get("GOOGLE_DRIVE_MOUNT", "./shared_exports")
os.makedirs(EXPORT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        user = users.get(username)
        if user and check_password_hash(user['password'], request.form['password']):
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    df = pd.DataFrame(waste_movements)
    return render_template('dashboard.html', records=df.to_dict(orient='records'))

@app.route('/dashboard')
def dashboard():
    # Example: load records from CSV
    try:
        with open('data.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            records = list(reader)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        records = []

    return render_template('dashboard.html', records=records)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['csv_file']
        if file and file.filename.endswith('.csv'):
            df = pd.read_csv(file)
            waste_movements.extend(df.to_dict(orient='records'))
            return redirect(url_for('tracking_log'))
    return render_template('upload.html')

@app.route('/tracking-log')
def tracking_log():
    df = pd.DataFrame(waste_movements)
    return render_template('tracking_log.html', records=df.to_dict(orient='records'))

@app.route('/generate-report')
def generate_report():
    df = pd.DataFrame(waste_movements)
    return render_template('report.html', records=df.to_dict(orient='records'))

@app.route('/send-email', methods=['GET', 'POST'])
def send_email():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        subject = request.form['subject']
        body = request.form['body']
        recipient = request.form['email']

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = os.environ.get('SMTP_USER')
        msg['To'] = recipient
        msg.set_content(body)

        try:
            with smtplib.SMTP(os.environ.get('SMTP_SERVER'), int(os.environ.get('SMTP_PORT', 587))) as smtp:
                smtp.starttls()
                smtp.login(os.environ.get('SMTP_USER'), os.environ.get('SMTP_PASSWORD'))
                smtp.send_message(msg)
            return 'Email sent successfully'
        except Exception as e:
            return f'Email failed: {str(e)}'

    return render_template('email_form.html')

@app.route('/download_excel')
def download_excel():
    df = pd.DataFrame(waste_movements)
    wb = Workbook()
    ws = wb.active
    ws.append(df.columns.tolist())
    for row in df.itertuples(index=False):
        ws.append(list(row))

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    return send_file(stream, as_attachment=True, download_name='waste_report.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/download_pdf')
def download_pdf():
    df = pd.DataFrame(waste_movements)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(100, 800, "Waste Report PDF")
    y = 750
    for i, row in df.iterrows():
        if y < 100:
            c.showPage()
            y = 800
        c.drawString(50, y, str(row.to_dict()))
        y -= 20
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='waste_report.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

