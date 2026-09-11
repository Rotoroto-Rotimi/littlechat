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
    background: #f1eee6;
}

.auth {
    max-width: 420px;
    margin: 60px auto;
    padding: 30px;
    background: white;
    border-radius: 25px;
    box-shadow: 0 3px 15px rgba(0,0,0,.15);
}

.auth h1 {
    text-align: center;
    color: #086b61;
}

.auth input {
    width: 100%;
    padding: 15px;
    margin: 8px 0;
    border: 1px solid #ccc;
    border-radius: 12px;
    font-size: 17px;
}

.auth button {
    width: 100%;
    padding: 15px;
    margin-top: 10px;
    border: none;
    border-radius: 12px;
    background: #20c968;
    color: white;
    font-size: 18px;
}

.auth a {
    display: block;
    text-align: center;
    margin-top: 18px;
    color: #086b61;
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
    background: white;
    padding: 15px;
}

.contacts h3 {
    margin-top: 0;
    color: #086b61;
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
    background: #20c968;
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
    background: #ddd;
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
    background: white;
    border-radius: 18px;
    padding: 14px 18px;
    margin-bottom: 10px;
    max-width: 85%;
}

.message.mine {
    margin-left: auto;
    background: #d8ffd9;
}

.sender {
    color: #086b61;
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
    background: white;
    padding: 10px;
    display: none;
    gap: 8px;
    border-top: 1px solid #ddd;
}

#messageInput {
    flex: 1;
    border: 1px solid #ccc;
    border-radius: 25px;
    padding: 14px;
    font-size: 17px;
}

#sendButton {
    background: #20c968;
    color: white;
    border: none;
    border-radius: 50%;
    width: 55px;
    height: 55px;
    font-size: 22px;
}

</style>

</head>

<body>

{% if page == "login" %}

<div class="auth">

<h1>💬 Little Chat</h1>

<h2>Login</h2>

{% if error %}
<div class="error">{{ error }}</div>
{% endif %}

<form method="POST">

<input
name="username"
placeholder="Username"
required
>

<input
name="password"
type="password"
placeholder="Password"
required
>

<button type="submit">
Login
</button>

</form>

<a href="/register">
Create an account
</a>

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
