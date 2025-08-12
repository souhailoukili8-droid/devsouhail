from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import json
from datetime import datetime, timedelta
import os
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = "your-secret-key-change-this-in-production"

BASE_URL = "https://panle-ch9ayfa-9999.vercel.app"
INFO_URL = "https://info-ch9ayfa.vercel.app"
USERS_FILE = "/tmp/users.json"
USER_DATA_DIR = "/tmp/user_data"


DEVELOPER_USERNAME = "souhail"
DEVELOPER_PASSWORD = "ch9ayfa"



def get_user_data_path(username):
    """الحصول على مسار مجلد بيانات المستخدم"""
    user_dir = os.path.join(USER_DATA_DIR, username)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

def get_user_log_file(username):
    """الحصول على مسار ملف سجل المستخدم"""
    return os.path.join(get_user_data_path(username), "log.json")

def get_user_config_file(username):
    """الحصول على مسار ملف إعدادات المستخدم"""
    return os.path.join(get_user_data_path(username), "config.json")

def load_user_log(username):
    """تحميل سجل المستخدم"""
    log_file = get_user_log_file(username)
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_user_log(username, log):
    """حفظ سجل المستخدم"""
    log_file = get_user_log_file(username)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=4)

def load_user_config(username):
    """تحميل إعدادات المستخدم"""
    config_file = get_user_config_file(username)
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
   
    return {
        "token1": "",
        "token2": ""
    }

def save_user_config(username, config):
    """حفظ إعدادات المستخدم"""
    config_file = get_user_config_file(username)
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def developer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'developer':
            flash('يجب أن تكون مطور للوصول لهذه الصفحة', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def calculate_remaining_days(entry, username):
    if entry["action"] not in ["إضافة", "تمديد", "تقليل"]:
        return "-"
    try:
        
        return calculate_total_remaining_days(entry["uid"], username)
    except Exception:
        return "-"

def calculate_total_remaining_days(uid, username):
    """حساب إجمالي الأيام المتبقية للاعب مع مراعاة جميع العمليات"""
    try:
        log = load_user_log(username)
        player_entries = [entry for entry in log if entry["uid"] == uid]
        player_entries.sort(key=lambda e: e["date"])

        total_days = 0
        start_date = None

        for entry in player_entries:
            if entry["action"] == "إضافة":
                start_date = datetime.strptime(entry["date"], "%Y-%m-%d %H:%M:%S")
                total_days += int(entry["days"])
            elif entry["action"] == "تمديد":
                total_days += int(entry["days"])
            elif entry["action"] == "تقليل":
                
                days_str = str(entry["days"]).replace("-", "")
                total_days -= int(days_str)
            elif entry["action"] == "حذف":
                return "-"  

        if start_date is None:
            return "-"

        end_date = start_date + timedelta(days=total_days)
        remaining = (end_date - datetime.now()).days

        if remaining < 0:
            return 0
        return int(remaining)  
    except Exception:
        return "-"

def is_uid_already_added(log, uid):
    
    filtered = [entry for entry in log if entry["uid"] == uid]
    if not filtered:
        return False
    filtered.sort(key=lambda e: e["date"], reverse=True)
    return filtered[0]["action"] in ["إضافة", "تمديد", "تقليل"]

def get_currently_added_players(log):
    
    currently_added_uids = set()
    for entry in log:
        if entry["action"] == "إضافة" and is_uid_already_added(log, entry["uid"]):
            currently_added_uids.add(entry["uid"])
    return len(currently_added_uids)

def fetch_player_info(uid):
    """جلب معلومات اللاعب من API"""
    try:
        url = f"{INFO_URL}/{uid}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            ct = response.headers.get("Content-Type", "")
            if ct.startswith("application/json"):
                data = response.json()

              
                if "basicinfo" in data and len(data["basicinfo"]) > 0:
                    player_data = data["basicinfo"][0]
                    return {
                        "username": player_data.get("username", "غير متوفر"),
                        "likes": player_data.get("likes", 0),
                        "level": player_data.get("level", 0),
                        "region": player_data.get("region", "غير متوفر"),
                        "success": True
                    }
                else:
                    return {"success": False, "error": "لا توجد معلومات أساسية للاعب"}
            else:
                return {"success": False, "error": "الرد ليس JSON"}
        else:
            return {"success": False, "error": f"خطأ HTTP: {response.status_code}"}

    except Exception as e:
        return {"success": False, "error": f"خطأ في الاتصال: {str(e)}"}

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

       
        if username == DEVELOPER_USERNAME and password == DEVELOPER_PASSWORD:
            session['user_id'] = username
            session['username'] = username
            session['role'] = 'developer'
            flash('مرحباً بك أيها المطور!', 'success')
            return redirect(url_for('developer_panel'))

       
        users = load_users()
        if username in users and verify_password(password, users[username]['password']):
            session['user_id'] = username
            session['username'] = username
            session['role'] = users[username]['role']
            flash(f'مرحباً بك {username}!', 'success')
            return redirect(url_for('index'))

        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('login'))

@app.route("/developer")
@developer_required
def developer_panel():
    users = load_users()


    stats = {
        'total_users': len(users),
        'developers': len([u for u in users.values() if u['role'] == 'developer']),
        'regular_users': len([u for u in users.values() if u['role'] == 'user']),
        'user_data_folders': 0
    }

   
    if os.path.exists(USER_DATA_DIR):
        stats['user_data_folders'] = len([d for d in os.listdir(USER_DATA_DIR) if os.path.isdir(os.path.join(USER_DATA_DIR, d))])

    return render_template("developer_panel.html", users=users, stats=stats)

@app.route("/create_user", methods=["POST"])
@developer_required
def create_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "user").strip()

    if not username or not password:
        flash('يجب ملء جميع الحقول', 'error')
        return redirect(url_for('developer_panel'))

    users = load_users()
    if username in users:
        flash('اسم المستخدم موجود بالفعل', 'error')
        return redirect(url_for('developer_panel'))

    users[username] = {
        'password': hash_password(password),
        'role': role,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'created_by': session['username']
    }

    save_users(users)
    flash(f'تم إنشاء المستخدم {username} بنجاح', 'success')
    return redirect(url_for('developer_panel'))

@app.route("/delete_user/<username>")
@developer_required
def delete_user(username):
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        flash(f'تم حذف المستخدم {username}', 'success')
    else:
        flash('المستخدم غير موجود', 'error')
    return redirect(url_for('developer_panel'))

@app.route("/user_settings", methods=["GET", "POST"])
@login_required
def user_settings():
    username = session['username']
    config = load_user_config(username)

    if request.method == "POST":
        token1 = request.form.get("token1", "").strip()
        token2 = request.form.get("token2", "").strip()

        if token1 and token2:
            config["token1"] = token1
            config["token2"] = token2
            save_user_config(username, config)
            flash('تم تحديث التوكنات بنجاح', 'success')
        else:
            flash('يجب ملء جميع الحقول', 'error')

        return redirect(url_for('user_settings'))

    return render_template("user_settings.html", config=config)

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    message = None
    username = session['username']
    log = load_user_log(username)
    config = load_user_config(username)

   
    for entry in log:
        entry["remaining_days"] = calculate_remaining_days(entry, username)

    if request.method == "POST":
       
        if "save_tokens" in request.form:
            token1 = request.form.get("token1", "").strip()
            token2 = request.form.get("token2", "").strip()
            if token1 and token2:
                config["token1"] = token1
                config["token2"] = token2
                save_user_config(username, config)
                message = "✅ تم تحديث التوكنات بنجاح"
            else:
                message = "❌ يجب ملء كلا التوكنين"
            currently_added_count = get_currently_added_players(log)
            return render_template("index.html", message=message, log=log, config=config, currently_added_count=currently_added_count)

      
        uid = request.form.get("uid", "").strip()
        days = request.form.get("days", "").strip()
        action = request.form.get("action")

        if not uid:
            message = "❌ الرجاء إدخال UID"
            currently_added_count = get_currently_added_players(log)
            return render_template("index.html", message=message, log=log, config=config, currently_added_count=currently_added_count)

        try:
            if action == "add":
              
                if is_uid_already_added(log, uid):
                    message = f"❌ هذا الـ UID ({uid}) موجود بالفعل كمضاف."
                    currently_added_count = get_currently_added_players(log)
                    return render_template("index.html", message=message, log=log, config=config, currently_added_count=currently_added_count)
                if not days or not days.isdigit() or int(days) <= 0:
                    message = "❌ الرجاء إدخال عدد أيام صالح (أكبر من 0)"
                    currently_added_count = get_currently_added_players(log)
                    return render_template("index.html", message=message, log=log, config=config, currently_added_count=currently_added_count)
                url = f"{BASE_URL}/add/{uid}/{days}/{config['token1']}/{config['token2']}"
            elif action == "remove":
                url = f"{BASE_URL}/remove/{uid}/{config['token1']}/{config['token2']}"
            else:
                message = "❌ خطأ: نوع العملية غير معروف"
                currently_added_count = get_currently_added_players(log)
                return render_template("index.html", message=message, log=log, config=config, currently_added_count=currently_added_count)

            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                message = f"❌ خطأ HTTP: {response.status_code}"
            else:
                ct = response.headers.get("Content-Type", "")
                if ct.startswith("application/json"):
                    data = response.json()
                    message = data.get("message") or data.get("error") or "⚠ لا يوجد رد من السيرفر"
                else:
                    message = f"⚠ الرد ليس JSON: {response.text[:200]}"

            if "✅" in message or "تم" in message:
               
                player_info = fetch_player_info(uid)

                log_entry = {
                    "uid": uid,
                    "action": "إضافة" if action == "add" else "حذف",
                    "days": days if action == "add" else "-",
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "result": message,
                    "username": player_info.get("username", "غير متوفر") if player_info.get("success") else "غير متوفر",
                    "likes": player_info.get("likes", 0) if player_info.get("success") else 0,
                    "level": player_info.get("level", 0) if player_info.get("success") else 0,
                    "region": player_info.get("region", "غير متوفر") if player_info.get("success") else "غير متوفر"
                }
                log.insert(0, log_entry)
                save_user_log(username, log)

               
                log = load_user_log(username)
                for entry in log:
                    entry["remaining_days"] = calculate_remaining_days(entry, username)

                
                if action == "remove" and request.form.get("from_added_page") == "true":
                    return redirect(url_for("added_players"))

        except Exception as e:
            message = f"❌ خطأ أثناء الاتصال: {str(e)}"

    
    currently_added_count = get_currently_added_players(log)

    return render_template("index.html", message=message, log=log, config=config, currently_added_count=currently_added_count)

@app.route("/clear_log")
@login_required
def clear_log():
    username = session['username']
    log_file = get_user_log_file(username)
    if os.path.exists(log_file):
        os.remove(log_file)
    return redirect(url_for("index"))

@app.route("/added")
@login_required
def added_players():
    username = session['username']
    config = load_user_config(username)
    log = load_user_log(username)

    
    currently_added = []
    processed_uids = set()

    for entry in log:
        if entry["action"] in ["إضافة", "تمديد", "تقليل"] and entry["uid"] not in processed_uids:
            
            if is_uid_already_added(log, entry["uid"]):
                currently_added.append(entry)
                processed_uids.add(entry["uid"])

    
    for entry in currently_added:
        entry["remaining_days"] = calculate_remaining_days(entry, username)

    return render_template("added.html", added=currently_added, config=config)

@app.route("/removed")
@login_required
def removed_players():
    username = session['username']
    log = load_user_log(username)
    removed = [entry for entry in log if entry["action"] == "حذف"]
    return render_template("removed.html", removed=removed)

@app.route("/delete_from_added", methods=["POST"])
@login_required
def delete_from_added():
    uid = request.form.get("uid", "").strip()
    if not uid:
        return redirect(url_for("added_players"))

    username = session['username']
    config = load_user_config(username)
    log = load_user_log(username)

    
    try:
        url = f"{BASE_URL}/remove/{uid}/{config['token1']}/{config['token2']}"
        response = requests.get(url, timeout=10)
        message = None
        if response.status_code != 200:
            message = f"❌ خطأ HTTP: {response.status_code}"
        else:
            ct = response.headers.get("Content-Type", "")
            if ct.startswith("application/json"):
                data = response.json()
                message = data.get("message") or data.get("error") or "⚠ لا يوجد رد من السيرفر"
            else:
                message = f"⚠ الرد ليس JSON: {response.text[:200]}"

        if "✅" in message or "تم" in message:
           
            player_info = fetch_player_info(uid)

            log_entry = {
                "uid": uid,
                "action": "حذف",
                "days": "-",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "result": message,
                "username": player_info.get("username", "غير متوفر") if player_info.get("success") else "غير متوفر",
                "likes": player_info.get("likes", 0) if player_info.get("success") else 0,
                "level": player_info.get("level", 0) if player_info.get("success") else 0,
                "region": player_info.get("region", "غير متوفر") if player_info.get("success") else "غير متوفر"
            }
            log.insert(0, log_entry)
            save_user_log(username, log)
        

    except Exception:
        pass  

    return redirect(url_for("added_players"))

@app.route("/edit_player/<uid>")
@login_required
def edit_player(uid):
    """صفحة تعديل معلومات اللاعب"""
    username = session['username']
    log = load_user_log(username)

  
    player_entry = None
    for entry in log:
        if entry["uid"] == uid and entry["action"] == "إضافة":
            player_entry = entry
            break

    if not player_entry:
        return redirect(url_for("added_players"))

   
    player_entry["remaining_days"] = calculate_remaining_days(player_entry, username)

    return render_template("edit_player.html", player=player_entry)

@app.route("/update_player", methods=["POST"])
@login_required
def update_player():
    """تحديث معلومات اللاعب"""
    uid = request.form.get("uid", "").strip()
    action_type = request.form.get("action_type")  
    days_change = request.form.get("days_change", "").strip()

    if not uid or not action_type or not days_change:
        return redirect(url_for("added_players"))

    try:
        days_change = int(days_change)
        if days_change <= 0:
            return redirect(url_for("edit_player", uid=uid))
    except ValueError:
        return redirect(url_for("edit_player", uid=uid))

    username = session['username']
    log = load_user_log(username)
    config = load_user_config(username)

   
    if action_type == "extend":
       
        try:
            url = f"{BASE_URL}/add/{uid}/{days_change}/{config['token1']}/{config['token2']}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                ct = response.headers.get("Content-Type", "")
                if ct.startswith("application/json"):
                    data = response.json()
                    message = data.get("message") or data.get("error") or "⚠ لا يوجد رد من السيرفر"
                else:
                    message = f"⚠ الرد ليس JSON: {response.text[:200]}"
            else:
                message = f"❌ خطأ HTTP: {response.status_code}"

            if "✅" in message or "تم" in message:
              
                player_info = fetch_player_info(uid)

                log_entry = {
                    "uid": uid,
                    "action": "تمديد",
                    "days": str(days_change),
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "result": f"✅ تم تمديد المدة بـ {days_change} يوم",
                    "username": player_info.get("username", "غير متوفر") if player_info.get("success") else "غير متوفر",
                    "likes": player_info.get("likes", 0) if player_info.get("success") else 0,
                    "level": player_info.get("level", 0) if player_info.get("success") else 0,
                    "region": player_info.get("region", "غير متوفر") if player_info.get("success") else "غير متوفر"
                }
                log.insert(0, log_entry)
                save_user_log(username, log)

        except Exception:
            pass

    elif action_type == "reduce":
        
        try:
           
            player_info = fetch_player_info(uid)

            log_entry = {
                "uid": uid,
                "action": "تقليل",
                "days": f"-{days_change}",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "result": f"✅ تم تقليل المدة بـ {days_change} يوم",
                "username": player_info.get("username", "غير متوفر") if player_info.get("success") else "غير متوفر",
                "likes": player_info.get("likes", 0) if player_info.get("success") else 0,
                "level": player_info.get("level", 0) if player_info.get("success") else 0,
                "region": player_info.get("region", "غير متوفر") if player_info.get("success") else "غير متوفر"
            }
            log.insert(0, log_entry)
            save_user_log(username, log)

        except Exception:
            pass

    return redirect(url_for("added_players"))

@app.route("/search_friend", methods=["GET", "POST"])
@login_required
def search_friend():
    """البحث عن صديق بالـ UID"""
    result = None
    search_uid = None

    if request.method == "POST":
        search_uid = request.form.get("search_uid", "").strip()

        if search_uid:
           
            username = session['username']
            log = load_user_log(username)
            local_entries = [entry for entry in log if entry["uid"] == search_uid]

           
            player_info = fetch_player_info(search_uid)

           
            player_status = "غير موجود"
            remaining_days = "-"
            last_operation = None

            if local_entries:
               
                local_entries.sort(key=lambda e: e["date"], reverse=True)
                last_operation = local_entries[0]

                if is_uid_already_added(log, search_uid):
                    player_status = "مضاف حالياً"
                    remaining_days = calculate_total_remaining_days(search_uid, username)
                else:
                    player_status = "محذوف"

            result = {
                "uid": search_uid,
                "player_info": player_info,
                "status": player_status,
                "remaining_days": remaining_days,
                "last_operation": last_operation,
                "all_operations": local_entries,
                "operations_count": len(local_entries)
            }

    return render_template("search_friend.html", result=result, search_uid=search_uid)

# For Vercel deployment
if __name__ == "__main__":
    app.run(debug=True)
