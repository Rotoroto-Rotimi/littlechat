from flask import Flask, request, jsonify, render_template_string, session, redirect, send_from_directory
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "littlechat-secret-change-later"

DATABASE = "littlechat.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            time TEXT NOT NULL,
            user_id INTEGER,
            recipient_id INTEGER
        )
    """)

    columns = conn.execute(
        "PRAGMA table_info(messages)"
    ).fetchall()

    names = [column["name"] for column in columns]

    if "user_id" not in names:
        conn.execute(
            "ALTER TABLE messages ADD COLUMN user_id INTEGER"
        )

    if "file_name" not in names:
        conn.execute("ALTER TABLE messages ADD COLUMN file_name TEXT")

    if "file_type" not in names:
        conn.execute("ALTER TABLE messages ADD COLUMN file_type TEXT")
    if "recipient_id" not in names:
        conn.execute(
            "ALTER TABLE messages ADD COLUMN recipient_id INTEGER"
        )

    conn.commit()
    conn.close()



    conn.execute("""
        CREATE TABLE IF NOT EXISTS statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            media_url TEXT NOT NULL,
            media_type TEXT NOT NULL,
            caption TEXT DEFAULT "",
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)



@app.route("/status", methods=["GET", "POST"])
def status():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        media_url = str(data.get("media_url", "")).strip()
        media_type = str(data.get("media_type", "")).strip().lower()
        caption = str(data.get("caption", "")).strip()

        if not media_url:
            conn.close()
            return {"error": "Media is required"}, 400

        if media_type not in ("image", "video", "audio"):
            conn.close()
            return {"error": "Unsupported media type"}, 400

        conn.execute(
            """
            INSERT INTO statuses
            (user_id, media_url, media_type, caption, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                media_url,
                media_type,
                caption,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        conn.commit()
        conn.close()
        return {"success": True}

    rows = conn.execute(
        """
        SELECT
            statuses.id,
            statuses.media_url,
            statuses.media_type,
            statuses.caption,
            statuses.created_at,
            users.username
        FROM statuses
        JOIN users ON users.id = statuses.user_id
        ORDER BY statuses.id DESC
        """
    ).fetchall()

    conn.close()

    return {
        "statuses": [dict(row) for row in rows]
    }

HTML = """
<!DOCTYPE html>
<html>
<head>

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>Little Chat</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #eef6ff;
}

.auth {
    max-width: 420px;
    margin: 60px auto;
    padding: 30px;
    background: #ffffff;
    border-radius: 25px;
    box-shadow: 0 3px 15px rgba(0,0,0,.15);
}

.auth h1 {
    text-align: center;
    color: #1677ff;
}

.auth input {
    width: 100%;
    padding: 15px;
    margin: 8px 0;
    border: 1px solid #b8d7ff;
    border-radius: 12px;
    font-size: 17px;
}

.auth button {
    width: 100%;
    padding: 15px;
    margin-top: 10px;
    border: none;
    border-radius: 12px;
    background: #1677ff;
    color: white;
    font-size: 18px;
}

.auth a {
    display: block;
    text-align: center;
    margin-top: 18px;
    color: #1677ff;
}

.error {
    color: #d00;
    text-align: center;
    margin: 10px;
}

.header {
    background: #086b61;
    color: white;
    padding: 15px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.profile {
    display: flex;
    align-items: center;
    gap: 12px;
}

.avatar {
    width: 65px;
    height: 65px;
    background: #20d66b;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 35px;
    font-weight: bold;
}

.name {
    font-size: 26px;
    font-weight: bold;
}

.online {
    font-size: 15px;
}

.logout {
    color: white;
    text-decoration: none;
}

.contacts {
    background: #ffffff;
    padding: 15px;
}

.contacts h3 {
    margin-top: 0;
    color: #1677ff;
}

.user {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border-bottom: 1px solid #eee;
    cursor: pointer;
}

.user:hover {
    background: #f5f5f5;
}

.user-avatar {
    width: 45px;
    height: 45px;
    background: #1677ff;
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 22px;
}

.user-name {
    font-size: 18px;
    font-weight: bold;
}

#chatArea {
    display: none;
}

.chat-header {
    background: #1677ff;
    padding: 12px 20px;
    font-size: 19px;
    font-weight: bold;
}

.privacy {
    text-align: center;
    color: #777;
    font-size: 17px;
    padding: 12px;
}

#messages {
    padding: 10px 20px 100px;
}

.message {
    background: #ffffff;
    border-radius: 18px;
    padding: 14px 18px;
    margin-bottom: 10px;
    max-width: 85%;
}

.message.mine {
    margin-left: auto;
    background: #dbeafe;
}

.sender {
    color: #1677ff;
    font-weight: bold;
    font-size: 13px;
    margin-bottom: 5px;
}

.message-text {
    font-size: 18px;
    word-wrap: break-word;
}

.time {
    text-align: right;
    color: #888;
    font-size: 12px;
    margin-top: 6px;
}

.input-area {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #ffffff;
    padding: 10px;
    display: none;
    gap: 8px;
    border-top: 1px solid #ddd;
}

#messageInput {
    flex: 1;
    border: 1px solid #b8d7ff;
    border-radius: 25px;
    padding: 14px;
    font-size: 17px;
}

#sendButton {
    background: #1677ff;
    color: white;
    border: none;
    border-radius: 50%;
    width: 55px;
    height: 55px;
    font-size: 22px;
}


/* LITTLE CHAT GALAXY LOGIN */

body:has(.galaxy-login) {
    margin: 0;
    min-height: 100vh;
    overflow-x: hidden;
    background:
        radial-gradient(circle at 20% 20%, rgba(145, 55, 255, .28), transparent 25%),
        radial-gradient(circle at 80% 70%, rgba(76, 35, 190, .30), transparent 30%),
        linear-gradient(135deg, #080318, #17052d 48%, #05020d);
}

.galaxy-login {
    position: relative;
    min-height: 100vh;
    width: 100%;
    overflow: hidden;
    display: flex;
    justify-content: center;
    align-items: center;
    background:
        radial-gradient(circle at 50% 45%,
            rgba(116, 35, 190, .28) 0%,
            rgba(48, 8, 92, .22) 28%,
            rgba(8, 2, 20, .75) 58%,
            #020106 100%);
}

.galaxy-login::before {
    content: "";
    position: absolute;
    width: 850px;
    height: 850px;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    background:
        radial-gradient(circle,
            rgba(157, 57, 255, .20) 0%,
            rgba(100, 20, 180, .12) 30%,
            transparent 68%);
    filter: blur(8px);
    pointer-events: none;
}

.stars {
    z-index: 1;
    background-image:
        radial-gradient(circle, #ffffff 1px, transparent 1.5px),
        radial-gradient(circle, #c77cff 1px, transparent 1.5px);
    background-size: 90px 90px, 150px 150px;
    opacity: .55;

    position: absolute;
    inset: 0;
    background-image:
        radial-gradient(circle, rgba(255,255,255,.9) 1px, transparent 1.5px),
        radial-gradient(circle, rgba(202,130,255,.8) 1px, transparent 1.5px),
        radial-gradient(circle, rgba(255,255,255,.65) 1px, transparent 1.5px);
    background-size: 95px 95px, 145px 145px, 210px 210px;
    background-position: 10px 20px, 60px 80px, 120px 30px;
    opacity: .55;
    z-index: 1;
    pointer-events: none;
}

.planet-one {
    position: absolute;
    width: 230px;
    height: 230px;
    border-radius: 50%;
    left: -115px;
    top: 12%;
    background:
        radial-gradient(circle at 35% 30%,
            rgba(220,150,255,.8),
            rgba(100,20,160,.65) 45%,
            rgba(18,3,35,.95) 78%);
    box-shadow:
        0 0 35px rgba(154,55,255,.65),
        0 0 100px rgba(100,25,190,.35);
    z-index: 2;
    pointer-events: none;
}

.planet-two {
    position: absolute;
    width: 150px;
    height: 150px;
    border-radius: 50%;
    right: -65px;
    bottom: 8%;
    background:
        radial-gradient(circle at 35% 30%,
            rgba(196,110,255,.75),
            rgba(73,15,120,.7) 48%,
            rgba(12,2,25,.95) 80%);
    box-shadow:
        0 0 30px rgba(170,65,255,.65),
        0 0 90px rgba(105,25,200,.3);
    z-index: 2;
    pointer-events: none;
}

.login-card {
    position: relative;
    z-index: 5;
    width: min(430px, 100%);
    min-height: 650px;
    padding: 55px 38px 35px;
    border: none;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    backdrop-filter: none;
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.login-card::before {
    content: "";
    position: absolute;
    width: 430px;
    height: 430px;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    background:
        radial-gradient(circle at 50% 42%,
            rgba(116, 25, 190, .38) 0%,
            rgba(57, 10, 105, .28) 48%,
            rgba(5, 1, 15, .92) 76%);
    border: 1.5px solid rgba(187, 105, 255, .55);
    box-shadow:
        0 0 22px rgba(165, 67, 255, .60),
        0 0 55px rgba(123, 37, 255, .30),
        inset 0 0 55px rgba(164, 69, 255, .18);
    z-index: -1;
    pointer-events: none;
}

.login-card > * {
    position: relative;
    z-index: 2;
}

@media (max-width: 480px) {
    .login-card {
        min-height: 620px;
        padding: 45px 28px 30px;
    }

    .login-card::before {
        width: 430px;
        height: 430px;
    }
}

.login-card::before {
    content: "";
    position: absolute;
    width: 520px;
    height: 520px;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    background:
        radial-gradient(circle,
            rgba(177, 76, 255, .28) 0%,
            rgba(120, 35, 220, .16) 38%,
            rgba(70, 15, 130, .08) 58%,
            transparent 72%);
    box-shadow:
        0 0 80px rgba(145, 50, 255, .25);
    z-index: -1;
    pointer-events: none;
}

.little-logo {
    display: flex;
    justify-content: center;
    margin-bottom: 8px;
}

.logo-planet {
    width: 72px;
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    font-size: 32px;
    background: radial-gradient(circle at 35% 30%, #d88cff, #7521b9 55%, #220633);
    box-shadow: 0 0 35px rgba(183, 91, 255, .65);
}

.login-card h1 {
    margin: 8px 0 3px;
    font-size: 34px;
    letter-spacing: .5px;
}

.tagline {
    margin: 0;
    color: #cda7ff;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 3px;
}

.welcome {
    margin: 25px 0 18px;
}

.welcome h2 {
    margin: 0 0 5px;
    font-size: 25px;
}

.welcome p {
    margin: 0;
    color: #b7a9c9;
    font-size: 14px;
}

.galaxy-login form {
    text-align: left;
}

.galaxy-login form > label {
    display: block;
    margin: 13px 0 7px;
    color: #e5d9ef;
    font-size: 13px;
    font-weight: 600;
}

.galaxy-login form input[name="username"],
.galaxy-login form input[name="password"] {
    width: 100%;
    padding: 15px 16px;
    border: 1px solid rgba(190, 137, 255, .28);
    border-radius: 13px;
    outline: none;
    color: white;
    background: rgba(255, 255, 255, .07);
    font-size: 15px;
}

.galaxy-login form input::placeholder {
    color: #887a99;
}

.galaxy-login form input:focus {
    border-color: #a85cff;
    box-shadow: 0 0 18px rgba(168, 92, 255, .22);
}

.login-options {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 14px 0 18px;
    font-size: 12px;
}

.remember {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #aaa0b5;
}

.remember input {
    accent-color: #8d42ff;
}

.forgot {
    color: #bb82ff;
    text-decoration: none;
}

.login-button {
    width: 100%;
    padding: 15px;
    border: none;
    border-radius: 14px;
    color: white;
    background: linear-gradient(90deg, #7b2cff, #b044ff);
    font-size: 17px;
    font-weight: bold;
    cursor: pointer;
    box-shadow: 0 8px 25px rgba(139, 49, 255, .35);
}

.login-button:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 30px rgba(163, 72, 255, .5);
}

.divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 22px 0 15px;
    color: #76677f;
    font-size: 11px;
}

.divider::before,
.divider::after {
    content: "";
    flex: 1;
    height: 1px;
    background: rgba(255, 255, 255, .10);
}

.google-button {
    width: 100%;
    padding: 13px;
    border: 1px solid rgba(255, 255, 255, .13);
    border-radius: 13px;
    background: rgba(255, 255, 255, .06);
    color: #eee;
    font-size: 14px;
    cursor: pointer;
}

.google-icon {
    margin-right: 8px;
    font-weight: bold;
    color: white;
}

.create-text {
    margin: 22px 0 8px;
    color: #91869b;
    font-size: 13px;
}

.create-text a {
    color: #bd7cff;
    font-weight: bold;
    text-decoration: none;
}

.security {
    margin: 0;
    color: #74697d;
    font-size: 10px;
}

.error {
    margin: 10px 0;
    padding: 10px;
    border-radius: 10px;
    background: rgba(255, 60, 100, .12);
    color: #ff9caf;
    font-size: 13px;
}

@media (max-width: 480px) {
    .login-card {
        padding: 25px 20px 20px;
        border-radius: 23px;
    }

    .login-card h1 {
        font-size: 30px;
    }
}


</style>


<style>
.little-logo {
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 0 auto 12px;
    width: 110px;
    height: 110px;
}

.little-logo-orbit {
    position: relative;
    width: 92px;
    height: 92px;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    background: radial-gradient(circle, rgba(180,80,255,.45), rgba(70,10,120,.35) 55%, transparent 70%);
    box-shadow:
        0 0 18px rgba(190,90,255,.9),
        0 0 45px rgba(130,35,255,.7);
}

.little-logo-ring {
    position: absolute;
    width: 78px;
    height: 78px;
    border-radius: 50%;
    border: 2px solid rgba(220,155,255,.95);
    box-shadow:
        inset 0 0 15px rgba(190,80,255,.7),
        0 0 15px rgba(190,80,255,.8);
}

.little-logo-core {
    position: relative;
    width: 58px;
    height: 58px;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    background: radial-gradient(circle at 35% 30%, #d99aff, #7625bd 55%, #26053f);
    border: 2px solid rgba(238,202,255,.95);
    box-shadow:
        0 0 12px rgba(220,130,255,.95),
        inset 0 0 15px rgba(255,255,255,.15);
}

.little-logo-chat {
    font-size: 27px;
    filter: drop-shadow(0 0 7px rgba(255,255,255,.9));
}

.little-logo-orbit::after {
    content: "";
    position: absolute;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #e3b1ff;
    box-shadow: 0 0 12px #c56cff, 0 0 25px #9c38ff;
    top: 5px;
    right: 12px;
}

</style>


<style>
.galaxy-login .welcome h2 {
    margin: 8px 0 5px;
    color: #ffffff;
    font-size: 30px;
    font-weight: 700;
    text-shadow: 0 0 14px rgba(190,90,255,.65);
}

.galaxy-login .welcome p {
    margin: 0 0 22px;
    color: rgba(235,215,250,.78);
    font-size: 14px;
}

.galaxy-login form {
    width: 100%;
}

.galaxy-login form > label {
    display: block;
    text-align: left;
    margin: 12px 0 7px;
    color: #ead9f7;
    font-size: 13px;
    font-weight: 600;
}

.galaxy-login form input:not([type="checkbox"]) {
    width: 100%;
    height: 50px;
    padding: 0 17px;
    box-sizing: border-box;
    border: 1px solid rgba(190,105,255,.38);
    border-radius: 12px;
    outline: none;
    background: rgba(30,8,48,.72);
    color: #ffffff;
    font-size: 14px;
    box-shadow:
        inset 0 0 12px rgba(100,25,160,.18),
        0 0 12px rgba(100,25,160,.10);
}

.galaxy-login form input:not([type="checkbox"])::placeholder {
    color: rgba(220,195,235,.48);
}

.galaxy-login form input:not([type="checkbox"]):focus {
    border-color: rgba(207,125,255,.85);
    box-shadow:
        0 0 12px rgba(174,65,255,.45),
        inset 0 0 12px rgba(100,25,160,.2);
}

.login-options {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 14px 0 20px;
    font-size: 12px;
}

.login-options .remember {
    display: flex;
    align-items: center;
    gap: 7px;
    color: rgba(235,215,250,.75);
}

.login-options .remember input[type="checkbox"] {
    accent-color: #a83cff;
}

.login-options .forgot {
    color: #c77aff;
    text-decoration: none;
}

.login-options .forgot:hover {
    color: #e1b5ff;
}

</style>


<style>
.galaxy-login .login-button {
    width: 100%;
    height: 52px;
    border: none;
    border-radius: 14px;
    margin-top: 2px;
    background: linear-gradient(90deg, #7624c7, #b84cff, #7624c7);
    background-size: 200% 100%;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    box-shadow:
        0 0 12px rgba(174,65,255,.75),
        0 0 30px rgba(130,35,230,.45);
    transition: .25s ease;
}

.galaxy-login .login-button:hover {
    transform: translateY(-2px);
    box-shadow:
        0 0 18px rgba(205,110,255,.95),
        0 0 45px rgba(130,35,230,.65);
}

.galaxy-login .divider {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    margin: 22px 0 16px;
    color: rgba(220,195,235,.45);
    font-size: 11px;
}

.galaxy-login .divider::before,
.galaxy-login .divider::after {
    content: "";
    flex: 1;
    height: 1px;
    background: rgba(190,105,255,.22);
}

.galaxy-login .google-button {
    width: 100%;
    height: 50px;
    border: 1px solid rgba(205,155,235,.28);
    border-radius: 13px;
    background: rgba(255,255,255,.06);
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    transition: .25s ease;
}

.galaxy-login .google-button:hover {
    background: rgba(255,255,255,.10);
    border-color: rgba(205,155,235,.5);
}

.galaxy-login .google-icon {
    width: 25px;
    height: 25px;
    border-radius: 50%;
    background: #ffffff;
    color: #4285f4;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 15px;
}

.galaxy-login .create-text {
    margin: 20px 0 8px;
    color: rgba(235,215,250,.68);
    font-size: 13px;
}

.galaxy-login .create-text a {
    color: #c77aff;
    font-weight: 700;
    text-decoration: none;
}

.galaxy-login .security {
    margin: 8px 0 0;
    color: rgba(210,190,225,.42);
    font-size: 10px;
}

.galaxy-login .error {
    margin: 10px 0;
    padding: 9px 12px;
    border-radius: 10px;
    background: rgba(255,50,80,.10);
    border: 1px solid rgba(255,80,100,.25);
    color: #ff9eae;
    font-size: 12px;
}

</style>


<style>
@media (max-width: 600px) {

    .galaxy-login {
        min-height: 100svh;
        padding: 15px 0;
        box-sizing: border-box;
    }

    .login-card {
        width: 100%;
        min-height: 650px;
        padding: 35px 32px 25px;
        box-sizing: border-box;
    }

    .login-card::before {
        width: 410px;
        height: 410px;
    }

    .little-logo {
        width: 95px;
        height: 95px;
    }

    .little-logo-orbit {
        width: 82px;
        height: 82px;
    }

    .little-logo-ring {
        width: 70px;
        height: 70px;
    }

    .little-logo-core {
        width: 53px;
        height: 53px;
    }

    .galaxy-login h1 {
        font-size: 27px;
    }

    .galaxy-login .welcome h2 {
        font-size: 26px;
    }

    .planet-one {
        width: 170px;
        height: 170px;
        left: -95px;
    }

    .planet-two {
        width: 110px;
        height: 110px;
        right: -55px;
    }
}

@media (max-width: 380px) {

    .login-card {
        padding-left: 25px;
        padding-right: 25px;
    }

    .login-card::before {
        width: 395px;
        height: 395px;
    }

    .galaxy-login .welcome h2 {
        font-size: 24px;
    }

}
</style>


<style>
.little-logo-mark {
    position: relative;
    width: 82px;
    height: 82px;
    margin: 0 auto;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background:
        radial-gradient(circle at 35% 30%,
            #dca2ff 0%,
            #9b3fe0 38%,
            #4a1175 72%,
            #160522 100%);
    border: 2px solid rgba(229,190,255,.9);
    box-shadow:
        0 0 15px rgba(198,91,255,.95),
        0 0 35px rgba(140,38,230,.75),
        inset 0 0 20px rgba(255,255,255,.15);
}

.logo-bubble {
    position: relative;
    width: 45px;
    height: 34px;
    border-radius: 13px;
    background: #ffffff;
    box-shadow:
        0 0 10px rgba(255,255,255,.8),
        0 0 20px rgba(215,140,255,.6);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
}

.logo-bubble::after {
    content: "";
    position: absolute;
    left: 7px;
    bottom: -7px;
    width: 13px;
    height: 13px;
    background: #ffffff;
    clip-path: polygon(0 0, 100% 0, 0 100%);
}

.logo-bubble span {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #7924b9;
    box-shadow: 0 0 5px rgba(121,36,185,.7);
}

.logo-tail {
    position: absolute;
    width: 8px;
    height: 8px;
    right: 7px;
    top: 8px;
    border-radius: 50%;
    background: #e8b5ff;
    box-shadow:
        0 0 8px #d27aff,
        0 0 18px #a43cff;
}

</style>

.galaxy-login {
    position: relative;
    min-height: 100vh;
    width: 100%;
    overflow: hidden;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 12px 10px 25px;
    box-sizing: border-box;
    background:
        radial-gradient(circle at 50% 20%, rgba(120,45,220,.32), transparent 30%),
        radial-gradient(circle at 10% 70%, rgba(55,35,190,.25), transparent 35%),
        radial-gradient(circle at 90% 60%, rgba(205,45,230,.18), transparent 32%),
        linear-gradient(145deg,#02020d,#09032d 48%,#02010a);
}

.galaxy-login::before {
    content: "";
    position: absolute;
    width: 700px;
    height: 220px;
    left: -180px;
    top: 100px;
    border: 2px solid rgba(158,78,255,.18);
    border-radius: 50%;
    transform: rotate(-24deg);
    box-shadow: 0 0 35px rgba(130,55,255,.18);
}

.galaxy-login::after {
    content: "";
    position: absolute;
    width: 650px;
    height: 190px;
    right: -220px;
    bottom: 100px;
    border: 2px solid rgba(225,70,255,.16);
    border-radius: 50%;
    transform: rotate(25deg);
}

.login-page-content {
    position: relative;
    z-index: 10;
    width: min(440px,100%);
    display: flex;
    flex-direction: column;
    align-items: center;
}

.stars {
    position: absolute;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background-image:
        radial-gradient(circle,rgba(255,255,255,.9) 1px,transparent 1.5px),
        radial-gradient(circle,rgba(190,120,255,.8) 1px,transparent 1.5px);
    background-size: 82px 82px,137px 137px;
    background-position: 12px 20px,40px 70px;
    opacity: .5;
}

.planet-one,
.planet-two {
    opacity: 0;
}

/* TOP LOGO */

.brand-area {
    position: relative;
    z-index: 20;
    text-align: center;
    margin-bottom: 4px;
}

.brand-orb {
    position: relative;
    width: 142px;
    height: 105px;
    margin: 0 auto;
}

.brand-globe {
    position: absolute;
    width: 82px;
    height: 82px;
    left: 30px;
    top: 10px;
    border-radius: 50%;
    background:
        radial-gradient(circle at 30% 20%,#dfc4ff,#9a5cff 20%,#5420b4 50%,#15043f 82%);
    box-shadow:
        0 0 16px rgba(166,91,255,.85),
        0 0 40px rgba(102,40,255,.5),
        inset -12px -12px 20px rgba(0,0,0,.5);
}

.brand-globe::before {
    content: "";
    position: absolute;
    width: 105px;
    height: 35px;
    left: -11px;
    top: 24px;
    border: 2px solid rgba(225,195,255,.55);
    border-radius: 50%;
    transform: rotate(-18deg);
}

.brand-globe::after {
    content: "";
    position: absolute;
    width: 32px;
    height: 92px;
    left: 25px;
    top: -5px;
    border-left: 2px solid rgba(220,185,255,.45);
    border-right: 2px solid rgba(220,185,255,.2);
    border-radius: 50%;
    transform: rotate(-18deg);
}

.brand-chat {
    position: absolute;
    width: 45px;
    height: 29px;
    left: 18px;
    top: 25px;
    border-radius: 16px;
    background: linear-gradient(135deg,#fff,#ddd4ff);
    box-shadow: 0 0 13px rgba(255,255,255,.6);
    z-index: 5;
}

.brand-chat::after {
    content: "";
    position: absolute;
    left: 7px;
    bottom: -8px;
    border-width: 9px 11px 0 0;
    border-style: solid;
    border-color: #ddd4ff transparent transparent transparent;
}

.brand-chat span {
    display: inline-block;
    width: 5px;
    height: 5px;
    margin: 12px 2px 0;
    border-radius: 50%;
    background: #6730c8;
}

.brand-ring {
    position: absolute;
    width: 142px;
    height: 48px;
    left: 0;
    top: 28px;
    border: 2px solid rgba(224,110,255,.75);
    border-radius: 50%;
    transform: rotate(-18deg);
    box-shadow: 0 0 12px rgba(213,73,255,.55);
}

.brand-heart {
    position: absolute;
    right: 6px;
    top: 15px;
    color: #ff9dea;
    font-size: 18px;
    text-shadow: 0 0 10px #e35cff;
}

.brand-area h1 {
    margin: 0;
    color: white;
    font-size: 33px;
    line-height: 1;
    font-weight: 800;
    text-shadow: 0 0 20px rgba(170,80,255,.5);
}

.brand-area h1 span {
    color: #c76cff;
}

.worldwide {
    margin-top: 7px;
    color: rgba(229,216,255,.82);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 7px;
}

.heart-divider {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin: 8px 0 5px;
}

.heart-divider i {
    width: 43px;
    height: 1px;
    background: linear-gradient(90deg,transparent,#b66aff);
    box-shadow: 0 0 7px #a855ff;
}

.heart-divider i:last-child {
    background: linear-gradient(90deg,#b66aff,transparent);
}

.heart-divider span {
    color: #ff8eea;
    font-size: 13px;
    text-shadow: 0 0 10px #ff58db;
}

/* LOGIN CIRCLE */

.login-orb {
    position: relative;
    z-index: 15;
    width: min(395px,calc(100vw - 24px));
    min-height: 485px;
    padding: 40px 48px 35px;
    box-sizing: border-box;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background:
        radial-gradient(circle at 50% 35%,
        rgba(105,40,175,.43),
        rgba(34,10,72,.58) 48%,
        rgba(5,2,18,.96) 82%);
    border: 1.5px solid rgba(198,117,255,.75);
    box-shadow:
        0 0 18px rgba(182,83,255,.65),
        0 0 50px rgba(121,47,255,.35),
        inset 0 0 55px rgba(161,65,255,.18);
}

.login-orb::before {
    content: "";
    position: absolute;
    inset: 9px;
    border-radius: 50%;
    border: 1px solid rgba(151,82,255,.25);
}

.login-inner {
    position: relative;
    z-index: 5;
    width: 100%;
    text-align: center;
}

.login-inner h2 {
    margin: 0;
    color: white;
    font-size: 42px;
    line-height: 1;
    font-weight: 800;
    text-shadow: 0 0 18px rgba(189,105,255,.5);
}

.login-subtitle {
    margin: 8px auto 20px;
    max-width: 245px;
    color: rgba(225,218,245,.72);
    font-size: 10px;
    line-height: 1.5;
}

.login-inner .error {
    margin-bottom: 10px;
    padding: 7px;
    border-radius: 10px;
    font-size: 10px;
    color: #ffb7c9;
    background: rgba(255,60,100,.12);
    border: 1px solid rgba(255,90,130,.35);
}

.input-box {
    position: relative;
    width: 100%;
    height: 41px;
    margin-bottom: 10px;
}

.input-box input {
    width: 100% !important;
    height: 41px !important;
    box-sizing: border-box !important;
    padding: 0 40px !important;
    border-radius: 22px !important;
    border: 1px solid rgba(192,124,255,.38) !important;
    outline: none !important;
    background: rgba(7,3,24,.62) !important;
    color: white !important;
    font-size: 11px !important;
}

.input-box input::placeholder {
    color: rgba(218,207,238,.48) !important;
}

.input-icon {
    position: absolute;
    z-index: 3;
    left: 16px;
    top: 10px;
    color: #bd79ff;
    font-size: 15px;
}

.eye-icon {
    position: absolute;
    z-index: 3;
    right: 16px;
    top: 11px;
    color: rgba(218,196,242,.55);
    font-size: 12px;
}

.forgot-row {
    text-align: right;
    margin: 0 5px 14px;
}

.forgot-row a {
    color: #c68aff !important;
    font-size: 10px !important;
    text-decoration: none !important;
}

.login-button {
    width: 100% !important;
    height: 42px !important;
    border: 0 !important;
    border-radius: 23px !important;
    background: linear-gradient(100deg,#5e22c8,#a54cff,#6727c9) !important;
    color: white !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    box-shadow: 0 0 16px rgba(160,66,255,.6) !important;
}

.login-button span {
    margin-right: 6px;
    font-size: 15px;
}

.or-divider {
    display: flex;
    align-items: center;
    gap: 9px;
    margin: 16px 0 13px;
}

.or-divider i {
    flex: 1;
    height: 1px;
    background: rgba(180,126,235,.22);
}

.or-divider span {
    color: rgba(226,211,244,.55);
    font-size: 10px;
}

.create-account {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 41px;
    box-sizing: border-box;
    border-radius: 22px;
    border: 1px solid rgba(194,119,255,.6);
    color: #e5d5ff !important;
    text-decoration: none !important;
    font-size: 11px;
    font-weight: 600;
    background: rgba(24,8,50,.3);
}

.create-account span {
    margin-right: 6px;
    color: #c27cff;
}

@media(max-width:430px) {
    .galaxy-login {
        padding-top: 5px;
    }

    .brand-orb {
        transform: scale(.82);
        margin-top: -8px;
        margin-bottom: -9px;
    }

    .brand-area h1 {
        font-size: 30px;
    }

    .worldwide {
        font-size: 9px;
        letter-spacing: 6px;
    }

    .login-orb {
        width: calc(100vw - 20px);
        min-height: 465px;
        padding: 38px 42px 33px;
    }

    .login-inner h2 {
        font-size: 38px;
    }
}

@media(max-width:360px) {
    .login-orb {
        min-height: 445px;
        padding-left: 35px;
        padding-right: 35px;
    }

    .login-inner h2 {
        font-size: 35px;
    }
}

<style id="little-chat-galaxy-clean">
* {
    box-sizing: border-box;
}

.galaxy-login {
    position: fixed !important;
    inset: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    min-height: 100vh !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
    margin: 0 !important;
    padding: 12px 12px 40px !important;
    color: #fff !important;
    font-family: Arial, Helvetica, sans-serif !important;
    text-align: center !important;
    background:
        radial-gradient(ellipse at 50% 25%, rgba(44, 41, 255, .55) 0%, transparent 30%),
        radial-gradient(ellipse at 15% 65%, rgba(65, 15, 245, .65) 0%, transparent 32%),
        radial-gradient(ellipse at 88% 72%, rgba(103, 15, 255, .55) 0%, transparent 30%),
        linear-gradient(145deg, #02052e 0%, #04096b 42%, #071ca3 100%) !important;
    z-index: 999999 !important;
}

.galaxy-login::before,
.galaxy-login::after {
    content: "";
    position: absolute;
    pointer-events: none;
    z-index: 0;
}

.galaxy-login::before {
    width: 720px;
    height: 300px;
    top: -120px;
    left: -270px;
    border-radius: 50%;
    border: 55px solid rgba(36, 31, 255, .42);
    box-shadow: 0 0 60px rgba(58, 38, 255, .45);
    transform: rotate(-20deg);
}

.galaxy-login::after {
    width: 820px;
    height: 330px;
    bottom: -160px;
    right: -300px;
    border-radius: 50%;
    border: 65px solid rgba(50, 25, 255, .38);
    box-shadow: 0 0 80px rgba(80, 45, 255, .5);
    transform: rotate(-18deg);
}

.stars {
    position: absolute;
    inset: 0;
    pointer-events: none;
    opacity: .45;
    z-index: 0;
    background-image:
        radial-gradient(circle, #fff 1px, transparent 1.6px),
        radial-gradient(circle, #bda8ff 1px, transparent 1.5px);
    background-size: 92px 92px, 137px 137px;
}

.brand-area {
    position: relative;
    z-index: 5;
    width: 100%;
    max-width: 430px;
    margin: 0 auto;
}

.brand-logo {
    position: relative;
    width: 150px;
    height: 130px;
    margin: 0 auto -2px;
}

.globe {
    position: absolute;
    width: 94px;
    height: 94px;
    left: 28px;
    top: 14px;
    border-radius: 50%;
    overflow: visible;
    background:
        radial-gradient(circle at 32% 25%, #fff 0 3%, transparent 4%),
        radial-gradient(circle at 64% 32%, #e4c8ff 0 7%, transparent 8%),
        radial-gradient(circle at 40% 62%, #9f6cff 0 12%, transparent 13%),
        linear-gradient(145deg, #dcbcff 0%, #754cff 38%, #2317d0 72%, #050b68 100%);
    box-shadow:
        inset -15px -14px 25px rgba(0, 5, 80, .75),
        inset 9px 8px 18px rgba(255, 255, 255, .32),
        0 0 22px #654cff,
        0 0 45px rgba(94, 56, 255, .9);
}

.globe::before {
    content: "";
    position: absolute;
    inset: 10px;
    border-radius: 50%;
    border-top: 9px solid rgba(255,255,255,.65);
    border-bottom: 7px solid rgba(38,31,196,.7);
    transform: rotate(-25deg);
}

.globe::after {
    content: "";
    position: absolute;
    width: 65px;
    height: 30px;
    left: 14px;
    top: 30px;
    border: 2px solid rgba(255,255,255,.5);
    border-radius: 50%;
    transform: rotate(-18deg);
}

.chat-bubble {
    position: absolute;
    width: 58px;
    height: 42px;
    right: -19px;
    top: 25px;
    border-radius: 24px;
    background: #fff;
    box-shadow: 0 0 20px rgba(255,255,255,.8);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    z-index: 4;
}

.chat-bubble::after {
    content: "";
    position: absolute;
    left: 8px;
    bottom: -13px;
    border-style: solid;
    border-width: 15px 15px 0 0;
    border-color: white transparent transparent transparent;
    transform: rotate(-12deg);
}

.chat-bubble b {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #3122c9;
}

.orbit {
    position: absolute;
    width: 142px;
    height: 55px;
    left: 3px;
    top: 42px;
    border: 4px solid #ed9cff;
    border-radius: 50%;
    transform: rotate(-12deg);
    box-shadow:
        0 0 9px #ff8eff,
        0 0 25px rgba(236,99,255,.8);
    z-index: 3;
}

.logo-heart {
    position: absolute;
    right: 0;
    bottom: 17px;
    font-size: 26px;
    color: #ff76ed;
    text-shadow:
        0 0 8px #ff65e7,
        0 0 20px #ff25d7;
    z-index: 6;
}

.brand-area h1 {
    position: relative;
    z-index: 5;
    margin: 0;
    font-size: clamp(39px, 10vw, 62px);
    line-height: .95;
    font-weight: 800;
    letter-spacing: -2px;
    color: #fff;
    text-shadow: 0 0 18px rgba(255,255,255,.25);
}

.brand-area h1 span {
    color: #fff;
}

.worldwide {
    margin-top: 9px;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 8px;
    color: #cba3ff;
    text-shadow: 0 0 15px rgba(199,125,255,.8);
}

.brand-line {
    width: 245px;
    height: 30px;
    margin: 8px auto 2px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
}

.brand-line i {
    display: block;
    width: 95px;
    height: 3px;
    background: #d875ff;
    box-shadow: 0 0 9px #d875ff;
}

.brand-line span {
    color: #ff75ec;
    font-size: 22px;
    text-shadow: 0 0 12px #ff5cdd;
}

.login-orb {
    position: relative;
    z-index: 4;
    width: min(850px, 94vw);
    height: min(850px, 92vw);
    min-height: 610px;
    margin: 0 auto;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 65px;
    background:
        radial-gradient(circle at 50% 38%, rgba(23, 30, 142, .95), rgba(3, 9, 83, .92) 65%, rgba(2, 5, 55, .94) 100%);
    border: 3px solid #c874ff;
    box-shadow:
        0 0 10px #e28aff,
        0 0 30px #703dff,
        0 0 80px rgba(70, 38, 255, .75),
        inset 0 0 70px rgba(50, 70, 255, .45);
}

.login-orb::before {
    content: "";
    position: absolute;
    inset: 10px;
    border-radius: 50%;
    border: 1px solid rgba(95, 101, 255, .55);
    box-shadow: inset 0 0 45px rgba(75, 60, 255, .25);
    pointer-events: none;
}

.login-content {
    position: relative;
    z-index: 5;
    width: min(640px, 76%);
    margin: 0 auto;
}

.login-content h2 {
    margin: 0;
    font-size: clamp(48px, 9vw, 70px);
    line-height: 1;
    font-weight: 800;
    color: #fff;
}

.login-content > p {
    margin: 17px 0 38px;
    font-size: clamp(15px, 3vw, 23px);
    color: #c4b9ff;
}

.field {
    position: relative;
    width: 100%;
    height: 78px;
    margin-bottom: 18px;
}

.field input {
    width: 100%;
    height: 100%;
    border: 2px solid #453cff;
    border-radius: 45px;
    outline: none;
    background: rgba(20, 28, 129, .55);
    color: #fff;
    padding: 0 75px;
    font-size: 20px;
    box-shadow:
        0 0 12px rgba(56,52,255,.3),
        inset 0 0 18px rgba(34,40,170,.35);
}

.field input::placeholder {
    color: #b7afff;
    opacity: 1;
}

.field input:focus {
    border-color: #a96cff;
    box-shadow: 0 0 20px rgba(132,72,255,.7);
}

.icon {
    position: absolute;
    left: 28px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 3;
    color: white;
    font-size: 30px;
}

.eye {
    position: absolute;
    right: 28px;
    top: 50%;
    transform: translateY(-50%);
    color: white;
    font-size: 22px;
}

.forgot {
    width: 100%;
    text-align: right;
    margin: 8px 4px 31px 0;
}

.forgot a {
    color: #d2b7ff;
    font-size: 18px;
    text-decoration: underline;
}

.login-btn {
    width: 100%;
    height: 76px;
    border: none;
    border-radius: 42px;
    color: white;
    background: linear-gradient(100deg, #b05aff 0%, #6738ff 45%, #6174ff 100%);
    font-size: 22px;
    font-weight: 700;
    box-shadow:
        0 0 18px rgba(177,83,255,.65),
        0 9px 25px rgba(38,30,190,.55);
    cursor: pointer;
}

.login-btn span {
    font-size: 34px;
    vertical-align: middle;
    margin-right: 10px;
}

.or {
    display: flex;
    align-items: center;
    gap: 22px;
    margin: 32px 0;
    color: #bdb1ff;
    font-size: 21px;
}

.or i {
    flex: 1;
    height: 2px;
    background: #6558ff;
    box-shadow: 0 0 7px rgba(101,88,255,.6);
}

.register-btn {
    width: 86%;
    height: 70px;
    margin: 0 auto;
    border: 2px solid #735cff;
    border-radius: 38px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 15px;
    color: #d9d0ff;
    background: rgba(10,15,90,.28);
    text-decoration: none;
    font-size: 20px;
    box-shadow: inset 0 0 15px rgba(60,50,255,.12);
}

.register-btn span {
    font-size: 29px;
}

.error {
    margin: -15px 0 15px;
    padding: 8px;
    color: #ff9fc9;
    font-size: 14px;
}

@media (max-width: 600px) {
    .galaxy-login {
        padding-top: 4px !important;
    }

    .brand-logo {
        transform: scale(.72);
        transform-origin: center top;
        margin-bottom: -30px;
    }

    .brand-area h1 {
        font-size: 40px;
    }

    .worldwide {
        font-size: 11px;
        letter-spacing: 5px;
    }

    .brand-line {
        margin-bottom: 5px;
    }

    .login-orb {
        width: 96vw;
        height: 96vw;
        min-height: 500px;
        padding-top: 55px;
    }

    .login-content {
        width: 76%;
    }

    .login-content h2 {
        font-size: 42px;
    }

    .login-content > p {
        font-size: 13px;
        margin: 12px 0 25px;
    }

    .field {
        height: 55px;
        margin-bottom: 11px;
    }

    .field input {
        font-size: 14px;
        padding: 0 48px;
    }

    .icon {
        left: 18px;
        font-size: 21px;
    }

    .eye {
        right: 18px;
        font-size: 16px;
    }

    .forgot {
        margin-bottom: 18px;
    }

    .forgot a {
        font-size: 12px;
    }

    .login-btn {
        height: 55px;
        font-size: 16px;
    }

    .login-btn span {
        font-size: 25px;
    }

    .or {
        margin: 18px 0;
        font-size: 14px;
    }

    .register-btn {
        height: 52px;
        font-size: 13px;
    }

    .register-btn span {
        font-size: 22px;
    }
}

</style>
</head>

<body>

<div id="lc-main-tabs">
    <button class="lc-tab active" onclick="lcShowSection('chats', this)">
        💬 Chats
    </button>

    <button class="lc-tab" onclick="lcShowSection('status', this)">
        ⭕ Status
    </button>
</div>

<div id="lc-status-section" style="display:none;">
    <div class="lc-status-header">
        <h2>Status</h2>
        <p>View updates from people on Little Chat.</p>
    </div>

    <div id="lc-status-list">
        <div class="lc-status-empty">
            No status updates yet.
        </div>
    </div>
</div>

<style>
#lc-main-tabs {
    display: flex;
    gap: 10px;
    margin: 15px auto;
    max-width: 900px;
    padding: 8px;
}

.lc-tab {
    flex: 1;
    border: 0;
    border-radius: 14px;
    padding: 14px 18px;
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
}

.lc-tab.active {
    box-shadow: 0 0 18px rgba(150, 80, 255, .55);
}

#lc-status-section {
    max-width: 900px;
    margin: 0 auto;
    padding: 15px;
}

.lc-status-header {
    margin-bottom: 15px;
}

.lc-status-header h2 {
    margin-bottom: 5px;
}

.lc-status-header p {
    opacity: .75;
}

.lc-status-card {
    border-radius: 18px;
    padding: 14px;
    margin-bottom: 12px;
}

.lc-status-card img,
.lc-status-card video {
    width: 100%;
    max-height: 420px;
    object-fit: contain;
    border-radius: 14px;
    margin-top: 10px;
}

.lc-status-card audio {
    width: 100%;
    margin-top: 10px;
}

.lc-status-empty {
    text-align: center;
    padding: 40px 15px;
    opacity: .7;
}
</style>

<script>
function lcShowSection(section, button) {
    document.querySelectorAll(".lc-tab").forEach(function(tab) {
        tab.classList.remove("active");
    });

    button.classList.add("active");

    const chatArea = document.getElementById("chat");
    const statusArea = document.getElementById("lc-status-section");

    if (section === "status") {
        if (chatArea) chatArea.style.display = "none";
        statusArea.style.display = "block";
        lcLoadStatuses();
    } else {
        if (chatArea) chatArea.style.display = "";
        statusArea.style.display = "none";
    }
}

async function lcLoadStatuses() {
    try {
        const response = await fetch("/status");
        const data = await response.json();

        const list = document.getElementById("lc-status-list");
        list.innerHTML = "";

        if (!data.statuses || data.statuses.length === 0) {
            list.innerHTML =
                '<div class="lc-status-empty">No status updates yet.</div>';
            return;
        }

        data.statuses.forEach(function(status) {
            const card = document.createElement("div");
            card.className = "lc-status-card";

            const title = document.createElement("strong");
            title.textContent =
                status.username + " • " + status.created_at;

            card.appendChild(title);

            if (status.caption) {
                const caption = document.createElement("p");
                caption.textContent = status.caption;
                card.appendChild(caption);
            }

            if (status.media_type === "image") {
                const img = document.createElement("img");
                img.src = status.media_url;
                img.alt = "Status photo";
                card.appendChild(img);
            }

            if (status.media_type === "video") {
                const video = document.createElement("video");
                video.src = status.media_url;
                video.controls = true;
                video.playsInline = true;
                card.appendChild(video);
            }

            if (status.media_type === "audio") {
                const audio = document.createElement("audio");
                audio.src = status.media_url;
                audio.controls = true;
                card.appendChild(audio);
            }

            list.appendChild(card);
        });

    } catch (error) {
        console.error("Could not load statuses:", error);
    }
}
</script>



{% if page == "login" %}
<div class="galaxy-login">
    <div class="stars"></div>

    <div class="brand-area">
        <div class="brand-logo">
            <div class="globe">
                <div class="chat-bubble"><b></b><b></b><b></b></div>
            </div>
            <div class="orbit"></div>
            <div class="logo-heart">♥</div>
        </div>

        <h1>Little Chat<span>,</span></h1>
        <div class="worldwide">WORLDWIDE.</div>
        <div class="brand-line"><i></i><span>♥</span><i></i></div>
    </div>

    <div class="login-orb">
        <div class="login-content">
            <h2>Login</h2>
            <p>Welcome back! Glad to see you again.</p>

            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}

            <form method="POST">
                <div class="field">
                    <span class="icon">♙</span>
                    <input name="username" placeholder="Username" required>
                </div>

                <div class="field">
                    <span class="icon">▣</span>
                    <input name="password" type="password" placeholder="Password" required>
                    <span class="eye">◉</span>
                </div>

                <div class="forgot">
                    <a href="/forgot-password">Forgot password?</a>
                </div>

                <button type="submit" class="login-btn"><span>↪</span> Login</button>
            </form>

            <div class="or"><i></i><span>or</span><i></i></div>

            <a href="/register" class="register-btn"><span>♙+</span> Create an account</a>
        </div>
    </div>
</div>

{% elif page == "register" %}

<div class="auth">

<h1>💬 Little Chat</h1>

<h2>Create Account</h2>

{% if error %}
<div class="error">{{ error }}</div>
{% endif %}

<form method="POST">

<input
name="username"
placeholder="Choose a username"
required
>

<input
name="password"
type="password"
placeholder="Choose a password"
required
>

<input
name="confirm_password"
type="password"
placeholder="Confirm password"
required
>

<button type="submit">
Create Account
</button>

</form>

<a href="/login">
Already have an account? Login
</a>

</div>

{% else %}

<div class="header">

<div class="profile">

<div class="avatar">
{{ username[0].upper() }}
</div>

<div>

<div class="name">
Little Chat
</div>

<div class="online">
@{{ username }} · online
</div>

</div>

</div>

<a class="logout" href="/logout">
Logout
</a>

</div>


<div class="contacts">

<h3>👥 Little Chat Users</h3>

<div id="users">
Loading users...
</div>

</div>


<div id="chatArea">

<div class="chat-header" id="chatTitle">
Private Chat
</div>

<div class="privacy">
🔒 Private conversation
</div>

<div id="messages"></div>

</div>


<div class="input-area" id="inputArea">

<input
id="messageInput"
type="text"
placeholder="Type a message..."
autocomplete="off"
>

<button
id="sendButton"
onclick="sendMessage()">
➤
</button>

</div>


<script>

let selectedUser = null;


async function loadUsers() {

    const response =
        await fetch("/users");

    const users =
        await response.json();

    const container =
        document.getElementById("users");

    container.innerHTML = "";

    users.forEach(user => {

        const div =
            document.createElement("div");

        div.className = "user";

        div.onclick = function() {
            openChat(user.id, user.username);
        };

        const avatar =
            document.createElement("div");

        avatar.className = "user-avatar";

        avatar.textContent =
            user.username[0].toUpperCase();

        const name =
            document.createElement("div");

        name.className = "user-name";

        name.textContent =
            "@" + user.username;

        div.appendChild(avatar);
        div.appendChild(name);

        container.appendChild(div);

    });

}


function openChat(id, username) {

    selectedUser = id;

    document.getElementById("chatArea").style.display =
        "block";

    document.getElementById("inputArea").style.display =
        "flex";

    document.getElementById("chatTitle").textContent =
        "💬 Chat with @" + username;

    loadMessages();

}


async function loadMessages() {

    if (!selectedUser) {
        return;
    }

    const response =
        await fetch("/messages/" + selectedUser);

    if (!response.ok) {
        return;
    }

    const data =
        await response.json();

    const container =
        document.getElementById("messages");

    container.innerHTML = "";

    data.forEach(message => {

        const div =
            document.createElement("div");

        div.className = "message";

        if (message.mine) {
            div.classList.add("mine");
        }

        const sender =
            document.createElement("div");

        sender.className = "sender";

        sender.textContent =
            "@" + message.username;

        const text =
            document.createElement("div");

        text.className = "message-text";

        text.textContent =
            message.text;

        const time =
            document.createElement("div");

        time.className = "time";

        time.textContent =
            message.time;

        div.appendChild(sender);
        div.appendChild(text);
        div.appendChild(time);

        container.appendChild(div);

    });

    container.scrollTop =
        container.scrollHeight;

}


async function sendMessage() {

    if (!selectedUser) {
        return;
    }

    const input =
        document.getElementById("messageInput");

    const text =
        input.value.trim();

    if (!text) {
        return;
    }

    const response =
        await fetch("/send", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                text: text,
                recipient_id: selectedUser
            })

        });

    if (response.ok) {

        input.value = "";

        loadMessages();

    }

}


document
.getElementById("messageInput")
.addEventListener(
    "keypress",
    function(event) {

        if (event.key === "Enter") {
            sendMessage();
        }

    }
);


loadUsers();

setInterval(loadMessages, 2000);

</script>

{% endif %}

</body>
</html>
"""


@app.route("/")
def home():

    if "user_id" not in session:
        return redirect("/login")

    return render_template_string(
        HTML,
        page="chat",
        username=session["username"]
    )


@app.route("/register", methods=["GET", "POST"])
def register():

    error = None

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if len(username) < 3:
            error = "Username must be at least 3 characters."

        elif len(password) < 6:
            error = "Password must be at least 6 characters."

        elif password != confirm:
            error = "Passwords do not match."

        else:

            conn = get_db()

            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            if existing:

                error = "That username already exists."

                conn.close()

            else:

                password_hash = generate_password_hash(password)

                conn.execute(
                    """
                    INSERT INTO users
                    (username, password)
                    VALUES (?, ?)
                    """,
                    (username, password_hash)
                )

                conn.commit()
                conn.close()

                return redirect("/login")

    return render_template_string(
        HTML,
        page="register",
        error=error
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            """
            SELECT id, username, password
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect("/")

        error = "Incorrect username or password."

    return render_template_string(
        HTML,
        page="login",
        error=error
    )



@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    message = None
    if request.method == "POST":
        message = "If an account exists with that username, password reset instructions will be provided."
    return render_template_string("""
    <div class="galaxy-login">
        <div class="login-card">
            <div class="little-logo">
                <div class="logo-planet">💬</div>
            </div>

            <h1>Little Chat</h1>
            <p class="tagline">CONNECT. SHARE. BELONG.</p>

            <div class="welcome">
                <h2>Forgot password?</h2>
                <p>Enter your username to reset your password.</p>
            </div>

            {% if message %}
            <div class="error">{{ message }}</div>
            {% endif %}

            <form method="POST">
                <label>Username</label>
                <input
                    name="username"
                    placeholder="Enter your username"
                    required
                >

                <button type="submit" class="login-button">
                    Continue
                </button>
            </form>

            <p class="create-text">
                Remember your password?
                <a href="/login">Log in</a>
            </p>

            <p class="security">
                🔒 Your conversations are private and secure
            </p>
        </div>
    </div>
    """)

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


@app.route("/users")
def users():

    if "user_id" not in session:
        return jsonify([]), 401

    conn = get_db()

    rows = conn.execute(
        """
        SELECT id, username
        FROM users
        WHERE id != ?
        ORDER BY username
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return jsonify([
        {
            "id": row["id"],
            "username": row["username"]
        }
        for row in rows
    ])


@app.route("/messages/<int:other_id>")
def get_private_messages(other_id):

    if "user_id" not in session:
        return jsonify([]), 401

    my_id = session["user_id"]

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            messages.id,
            messages.text,
            messages.time,
            messages.user_id,
            users.username
        FROM messages
        JOIN users
        ON messages.user_id = users.id
        WHERE
            (
                messages.user_id = ?
                AND messages.recipient_id = ?
            )
            OR
            (
                messages.user_id = ?
                AND messages.recipient_id = ?
            )
        ORDER BY messages.id
        """,
        (
            my_id,
            other_id,
            other_id,
            my_id
        )
    ).fetchall()

    conn.close()

    return jsonify([
        {
            "id": row["id"],
            "text": row["text"],
            "time": row["time"],
            "username": row["username"],
            "mine": row["user_id"] == my_id
        }
        for row in rows
    ])


@app.route("/send", methods=["POST"])
def send_message():

    if "user_id" not in session:
        return jsonify({
            "error": "Login required"
        }), 401

    data = request.get_json()

    text = data.get("text", "").strip()

    recipient_id = data.get("recipient_id")

    if not text or not recipient_id:
        return jsonify({
            "error": "Message and recipient are required"
        }), 400

    conn = get_db()

    recipient = conn.execute(
        "SELECT id FROM users WHERE id = ?",
        (recipient_id,)
    ).fetchone()

    if not recipient:
        conn.close()

        return jsonify({
            "error": "User not found"
        }), 404

    conn.execute(
        """
        INSERT INTO messages
        (text, time, user_id, recipient_id)
        VALUES (?, ?, ?, ?)
        """,
        (
            text,
            datetime.now().strftime("%H:%M"),
            session["user_id"],
            recipient_id
        )
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })



@app.route("/upload", methods=["POST"])
def upload_file():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    recipient_id = request.form.get("recipient_id")

    if not recipient_id:
        return jsonify({"error": "Recipient is required"}), 400

    if "file" not in request.files:
        return jsonify({"error": "No file selected"}), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)

    if not filename:
        return jsonify({"error": "Invalid filename"}), 400

    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    conn = get_db()

    recipient = conn.execute(
        "SELECT id FROM users WHERE id = ?",
        (recipient_id,)
    ).fetchone()

    if not recipient:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    conn.execute(
        """
        INSERT INTO messages
        (text, time, user_id, recipient_id, file_name, file_type)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            filename,
            datetime.now().strftime("%H:%M"),
            session["user_id"],
            recipient_id,
            filename,
            file.content_type or "application/octet-stream"
        )
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "file_name": filename,
        "file_type": file.content_type or "application/octet-stream"
    })


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    return send_from_directory(upload_dir, filename)

init_db()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
