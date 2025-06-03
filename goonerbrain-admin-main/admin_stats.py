from flask import Flask, request, jsonify, render_template, redirect, session
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime
import requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "changeme")

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client['goonerbrain']
users = db['user_activity']

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")
IPINFO_TOKEN = os.getenv("IPINFO_TOKEN", "")  # optional, add to .env

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect("/admin/stats")
        else:
            return render_template("admin_login.html", error="Invalid credentials")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect("/admin/login")

@app.route("/admin/stats")
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect("/admin/login")

    stats = {
        "total_users": users.count_documents({}),
        "top_search_terms": get_top_searches(10),
        "least_search_terms": get_least_searches(10),
        "average_time_on_site": get_avg_time(),
        "total_ad_clicks": users.count_documents({"clicked_ad": True}),
        "gender_distribution": get_gender_stats(),
        "locations": get_location_stats()
    }
    return render_template("admin_stats.html", stats=stats)

@app.route("/track", methods=["POST"])
def track_user():
    try:
        data = request.get_json(force=True)
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        geo = ip_lookup(ip)

        user_data = {
            "user_id": data.get("user_id"),
            "time_spent_seconds": data.get("time_spent_seconds", 0),
            "search_terms": data.get("search_terms", []),
            "clicked_ad": data.get("clicked_ad", False),
            "gender": data.get("gender", "unknown"),
            "ip": ip,
            "location": geo,
            "timestamp": datetime.utcnow()
        }
        users.insert_one(user_data)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def ip_lookup(ip):
    if not IPINFO_TOKEN:
        return ip
    try:
        res = requests.get(f"https://ipinfo.io/{ip}?token={IPINFO_TOKEN}", timeout=3)
        info = res.json()
        return f"{info.get('city', '')}, {info.get('country', '')}"
    except:
        return ip

def get_top_searches(limit=10):
    return list(users.aggregate([
        {"$unwind": "$search_terms"},
        {"$group": {"_id": "$search_terms", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]))

def get_least_searches(limit=10):
    return list(users.aggregate([
        {"$unwind": "$search_terms"},
        {"$group": {"_id": "$search_terms", "count": {"$sum": 1}}},
        {"$sort": {"count": 1}},
        {"$limit": limit}
    ]))

def get_avg_time():
    result = list(users.aggregate([
        {"$group": {"_id": None, "avg_time": {"$avg": "$time_spent_seconds"}}}
    ]))
    return result[0]['avg_time'] if result else 0

def get_gender_stats():
    return list(users.aggregate([
        {"$group": {"_id": "$gender", "count": {"$sum": 1}}}
    ]))

def get_location_stats():
    return list(users.aggregate([
        {"$group": {"_id": "$location", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]))

@app.route("/")
def home():
    return "✅ Flask is running. Go to <a href='/admin/login'>/admin/login</a>"

if __name__ == '__main__':
    app.run(debug=True)
