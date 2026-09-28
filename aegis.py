from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import sys
import json

# Ensure UTF-8 stdout encoding on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from hindsight import hindsight
from memory_manager import memory_manager

app = Flask(__name__, template_folder='.')
app.secret_key = 'super_secret_key_aegis_ai'

# --- Persistent User Database ---
USERS_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users_db.json')

DEFAULT_USERS = {
    "9440047837": {"password": "1234", "name": "Test User", "id": "P-10021"}
}

def load_users_db():
    """Load users from JSON file, or create with defaults if missing."""
    if os.path.exists(USERS_DB_FILE):
        try:
            with open(USERS_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # First run or corrupted file — initialize with defaults
    save_users_db(DEFAULT_USERS)
    return dict(DEFAULT_USERS)

def save_users_db(db=None):
    """Persist current users_db to disk."""
    if db is None:
        db = users_db
    with open(USERS_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

users_db = load_users_db()

appointments_db = [
    {
        "patientId": "P-10021",
        "hospital": "City Hospital",
        "doctor": "Dr. Smith",
        "dept": "Cardiology",
        "apptType": "Routine",
        "timing": "2026-03-05T10:00",
        "issue": "Routine Checkup"
    }
]

def get_current_user():
    """Helper to retrieve logged-in user or default test user."""
    phone = session.get('user_phone')
    if phone and phone in users_db:
        return users_db[phone]
    return users_db.get("9440047837")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json or {}
        phone = data.get('phone')
        password = data.get('password')

        if phone in users_db and users_db[phone]['password'] == password:
            session['user_phone'] = phone
            user = users_db[phone]
            # Retain login in Hindsight memory
            hindsight.retain_login(user['id'], name=user['name'])
            return jsonify({"status": "success", "message": "Login Successful"})
        else:
            return jsonify({"status": "error", "message": "Invalid credentials"})

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.json or {}
        phone = data.get('phone')
        password = data.get('password')
        name = data.get('name', 'New User')

        if phone in users_db:
            return jsonify({"status": "error", "message": "User already exists"})

        new_id = f"P-{10000 + len(users_db) + 1}"
        users_db[phone] = {"password": password, "name": name, "id": new_id}
        save_users_db()  # Persist to disk so the account survives server restarts
        # Initialize memory bank in Hindsight
        hindsight.get_or_create_user(new_id, name=name, phone=phone)
        return jsonify({"status": "success", "message": "Signup Successful"})

    return render_template('signup.html')


@app.route('/dashboard')
def dashboard():
    if 'user_phone' not in session:
        # For ease of testing/evaluating, log in default test user if session empty
        session['user_phone'] = "9440047837"

    user = users_db[session['user_phone']]
    hindsight.retain_login(user['id'], name=user['name'])
    return render_template('patient_dashboard.html', user=user)


# ═════════════════════════════════════════════════════════════════════
# APPOINTMENTS API
# ═════════════════════════════════════════════════════════════════════

@app.route('/api/appointments', methods=['GET', 'POST'])
def api_appointments():
    user = get_current_user()
    if not user:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    if request.method == 'POST':
        data = request.json or {}
        appointment = {
            "patientId": user['id'],
            "hospital": data.get('hospital'),
            "doctor": data.get('doctor'),
            "dept": data.get('dept', 'General'),
            "apptType": data.get('apptType', 'New'),
            "timing": data.get('timing'),
            "issue": data.get('issue')
        }
        appointments_db.append(appointment)
        # Retain appointment in Hindsight Memory & update learned preferences
        hindsight.retain_appointment(user['id'], appointment)

        return jsonify({"status": "success", "message": "Appointment booked! Hindsight learned your preferences."})

    # GET method
    user_appointments = [a for a in appointments_db if a.get('patientId') == user['id']]
    return jsonify({"status": "success", "data": user_appointments})


# ═════════════════════════════════════════════════════════════════════
# HINDSIGHT MEMORY APIS
# ═════════════════════════════════════════════════════════════════════

@app.route('/api/hindsight', methods=['GET'])
def api_hindsight():
    """Returns reflected memory insights, smart suggestions, and learned preferences."""
    user = get_current_user()
    data = hindsight.reflect(user['id'])
    return jsonify({"status": "success", "data": data})


@app.route('/api/memory/health', methods=['POST'])
def api_memory_health():
    """Adds a condition, allergy, medication, or symptom to patient memory bank."""
    user = get_current_user()
    data = request.json or {}
    info_type = data.get('type', 'condition')
    value = data.get('value', '').strip()

    if not value:
        return jsonify({"status": "error", "message": "Value is required"}), 400

    hindsight.retain_health_info(user['id'], info_type, value)
    return jsonify({"status": "success", "message": f"{info_type.title()} '{value}' saved to Hindsight memory!"})


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """
    AI Chat endpoint powered by Hindsight Memory.
    Supports enable_hindsight flag to toggle between amnesic and memory-augmented modes.
    """
    user = get_current_user()
    data = request.json or {}
    message = data.get('message', '').strip()
    enable_hindsight = data.get('enable_hindsight', True)

    if not message:
        return jsonify({"status": "error", "message": "Message cannot be empty"}), 400

    if enable_hindsight:
        hindsight.retain_conversation(user['id'], "user", message)

    res = hindsight.generate_response(user['id'], message, use_hindsight=enable_hindsight)

    if enable_hindsight:
        hindsight.retain_conversation(user['id'], "assistant", res["response"])

    return jsonify({
        "status": "success",
        "response": res["response"],
        "recalled_items": res.get("recalled_items", []),
        "mode": res.get("mode"),
        "critique": res.get("critique"),
        "advantage": res.get("advantage")
    })


@app.route('/api/demonstrations', methods=['GET'])
def api_demonstrations():
    """Provides the structured 4-scenario Before vs. After Hindsight demonstrations."""
    user = get_current_user()
    scenarios = hindsight.get_demonstration_scenarios(user['id'])
    return jsonify({"status": "success", "data": scenarios})


@app.route('/api/demo/compare', methods=['POST'])
def api_demo_compare():
    """Runs a side-by-side comparison for any arbitrary user message."""
    user = get_current_user()
    data = request.json or {}
    message = data.get('message', '').strip()

    if not message:
        return jsonify({"status": "error", "message": "Message required"}), 400

    before_res = hindsight.generate_response(user['id'], message, use_hindsight=False)
    after_res = hindsight.generate_response(user['id'], message, use_hindsight=True)

    return jsonify({
        "status": "success",
        "query": message,
        "before": before_res,
        "after": after_res
    })


@app.route('/logout')
def logout():
    session.pop('user_phone', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and any(arg in sys.argv for arg in ['demo', '--demo', '-d']):
        from hindsight import print_demonstration
        print_demonstration()
        sys.exit(0)

    print("\n" + "=" * 70)
    print("  AEGIS AI - HOSPITAL MANAGEMENT SYSTEM WITH HINDSIGHT MEMORY")
    print("=" * 70)
    print("  * Web Portal:      http://127.0.0.1:5000")
    print("  * Patient Portal:  http://127.0.0.1:5000/dashboard")
    print("  * Before vs After: http://127.0.0.1:5000/dashboard (Click 'Before vs After Demo')")
    print("  * Terminal Demo:   python demo.py  OR  python aegis.py --demo")
    print("=" * 70 + "\n")
    app.run(debug=True, port=5000)
