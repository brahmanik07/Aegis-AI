from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_aegis_ai'

# Mock Database
users_db = {
    "9440047837": {"password": "1234", "name": "Test User", "id": "P-10021"}
}

appointments_db = [
    {"patientId": "P-10021", "hospital": "City Hospital", "doctor": "Dr. Smith", "timing": "2026-03-05T10:00", "issue": "Routine Checkup"}
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        phone = data.get('phone')
        password = data.get('password')
        
        if phone in users_db and users_db[phone]['password'] == password:
            session['user_phone'] = phone
            return jsonify({"status": "success", "message": "Login Successful"})
        else:
            return jsonify({"status": "error", "message": "Invalid credentials"})
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.json
        phone = data.get('phone')
        password = data.get('password')
        name = data.get('name', 'New User')
        
        if phone in users_db:
             return jsonify({"status": "error", "message": "User already exists"})
             
        users_db[phone] = {"password": password, "name": name, "id": f"P-{10000 + len(users_db) + 1}"}
        return jsonify({"status": "success", "message": "Signup Successful"})
        
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'user_phone' not in session:
        return redirect(url_for('login'))
    
    user = users_db[session['user_phone']]
    return render_template('patient_dashboard.html', user=user)

@app.route('/api/appointments', methods=['GET', 'POST'])
def api_appointments():
    if 'user_phone' not in session:
         return jsonify({"status": "error", "message": "Unauthorized"}), 401
         
    user = users_db[session['user_phone']]
    
    if request.method == 'POST':
        data = request.json
        appointments_db.append({
            "patientId": user['id'],
            "hospital": data.get('hospital'),
            "doctor": data.get('doctor'),
            "timing": data.get('timing'),
            "issue": data.get('issue')
        })
        return jsonify({"status": "success", "message": "Appointment booked!"})
        
    # GET method
    user_appointments = [a for a in appointments_db if a['patientId'] == user['id']]
    return jsonify({"status": "success", "data": user_appointments})

@app.route('/logout')
def logout():
    session.pop('user_phone', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
