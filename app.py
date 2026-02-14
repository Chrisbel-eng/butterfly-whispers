from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ----------------------------
# PATH CONFIGURATION (IMPORTANT FOR RENDER)
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "test.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ----------------------------
# DATABASE INITIALIZATION
# ----------------------------
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        content TEXT,
        date TEXT,
        mood TEXT,
        image_path TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        pin TEXT
    )
    """)

    conn.commit()
    conn.close()


# Run DB init immediately (so it works on Render)
init_db()


# ----------------------------
# LANDING PAGE
# ----------------------------
@app.route("/")
def landing():
    return render_template("landing.html")


# ----------------------------
# REGISTER
# ----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
            conn.close()
            return redirect("/login")
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("register.html", error="Username already exists.")

    return render_template("register.html")


# ----------------------------
# LOGIN
# ----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]

            if user[3] is None:
                return redirect("/create_pin")
            else:
                return redirect("/enter_pin")
        else:
            return render_template("invalid.html")

    return render_template("login.html")


# ----------------------------
# CREATE PIN
# ----------------------------
@app.route("/create_pin", methods=["GET", "POST"])
def create_pin():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        pin = request.form["pin"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE users SET pin=? WHERE id=?",
            (pin, session["user_id"])
        )

        conn.commit()
        conn.close()

        return redirect("/welcome")

    return render_template("create_pin.html")


# ----------------------------
# ENTER PIN
# ----------------------------
@app.route("/enter_pin", methods=["GET", "POST"])
def enter_pin():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        entered_pin = request.form["pin"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT pin FROM users WHERE id=?",
            (session["user_id"],)
        )

        result = cursor.fetchone()
        conn.close()

        if result and entered_pin == result[0]:
            return redirect("/welcome")
        else:
            return "Incorrect PIN"

    return render_template("enter_pin.html")


# ----------------------------
# WELCOME PAGE
# ----------------------------
@app.route("/welcome")
def welcome():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("welcome.html", username=session["username"])


# ----------------------------
# JOURNAL PAGE
# ----------------------------
@app.route("/journal", methods=["GET", "POST"])
def journal():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form.get("title", "")
        content1 = request.form.get("content1", "")
        content2 = request.form.get("content2", "")
        content3 = request.form.get("content3", "")
        gratitude = request.form.get("gratitude", "")
        entry_id = request.form.get("entry_id")

        content = f"{content1}\n\n{content2}\n\n{content3}\n\nGrateful for: {gratitude}"
        date = datetime.now().strftime("%d-%m-%Y")

        image = request.files.get("image")
        image_path = ""

        if image and image.filename != "":
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + image.filename
            image_path = os.path.join("static", "uploads", filename)
            image.save(os.path.join(UPLOAD_FOLDER, filename))

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        if entry_id:
            if image_path:
                cursor.execute("""
                    UPDATE entries
                    SET title=?, content=?, image_path=?
                    WHERE id=? AND user_id=?
                """, (title, content, image_path, entry_id, session["user_id"]))
            else:
                cursor.execute("""
                    UPDATE entries
                    SET title=?, content=?
                    WHERE id=? AND user_id=?
                """, (title, content, entry_id, session["user_id"]))
        else:
            cursor.execute("""
                INSERT INTO entries (user_id, title, content, date, image_path)
                VALUES (?, ?, ?, ?, ?)
            """, (session["user_id"], title, content, date, image_path))

        conn.commit()
        conn.close()

        return redirect("/entries")

    today = datetime.now().strftime("%d-%m-%Y")
    return render_template("journal.html", date=today)


# ----------------------------
# ENTRIES PAGE
# ----------------------------
@app.route("/entries")
def entries():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM entries WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    )

    entries = cursor.fetchall()
    conn.close()

    return render_template("entries.html", entries=entries)


# ----------------------------
# DELETE ENTRY
# ----------------------------
@app.route("/delete/<int:entry_id>")
def delete_entry(entry_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM entries WHERE id=? AND user_id=?",
        (entry_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/entries")


# ----------------------------
# LOGOUT
# ----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ----------------------------
# RUN LOCAL ONLY
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)


# from flask import Flask, render_template, request, redirect, session
# import sqlite3
# import os
# from datetime import datetime

# app = Flask(__name__)
# app.secret_key = "supersecretkey"


# # ----------------------------
# # DATABASE INITIALIZATION
# # ----------------------------
# def init_db():
#     conn = sqlite3.connect("test.db")
#     cursor = conn.cursor()
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS entries (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id INTEGER,
#         title TEXT,
#         content TEXT,
#         date TEXT,
#         mood TEXT,
#         image_path TEXT
#     )
#     """)

#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS users (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         username TEXT UNIQUE,
#         password TEXT,
#         pin TEXT
#     )
#     """)

#     conn.commit()
#     conn.close()


# # ----------------------------
# # LANDING PAGE
# # ----------------------------
# @app.route("/")
# def landing():
#     return render_template("landing.html")


# # ----------------------------
# # REGISTER
# # ----------------------------
# @app.route("/register", methods=["GET", "POST"])
# def register():
#     if request.method == "POST":
#         username = request.form["username"]
#         password = request.form["password"]

#         conn = sqlite3.connect("test.db")
#         cursor = conn.cursor()

#         try:
#             cursor.execute(
#                 "INSERT INTO users (username, password) VALUES (?, ?)",
#                 (username, password)
#             )
#             conn.commit()
#             conn.close()
#             return redirect("/login")
#         except sqlite3.IntegrityError:
#             conn.close()
#             return render_template("register.html", error="Username already exists. Please choose a different one.")

#     return render_template("register.html")


# # ----------------------------
# # LOGIN
# # ----------------------------
# @app.route("/login", methods=["GET", "POST"])
# def login():
#     if request.method == "POST":
#         username = request.form["username"]
#         password = request.form["password"]

#         conn = sqlite3.connect("test.db")
#         cursor = conn.cursor()

#         cursor.execute(
#             "SELECT * FROM users WHERE username=? AND password=?",
#             (username, password)
#         )

#         user = cursor.fetchone()
#         conn.close()

#         if user:
#             session["user_id"] = user[0]
#             session["username"] = user[1]

#             if user[3] is None:
#                 return redirect("/create_pin")
#             else:
#                 return redirect("/enter_pin")
#         else:
#             return render_template("invalid.html")

#     return render_template("login.html")


# # ----------------------------
# # CREATE PIN
# # ----------------------------
# @app.route("/create_pin", methods=["GET", "POST"])
# def create_pin():
#     if "user_id" not in session:
#         return redirect("/login")

#     if request.method == "POST":
#         pin = request.form["pin"]

#         conn = sqlite3.connect("test.db")
#         cursor = conn.cursor()

#         cursor.execute(
#             "UPDATE users SET pin=? WHERE id=?",
#             (pin, session["user_id"])
#         )

#         conn.commit()
#         conn.close()

#         return redirect("/welcome")

#     return render_template("create_pin.html")


# # ----------------------------
# # ENTER PIN
# # ----------------------------
# @app.route("/enter_pin", methods=["GET", "POST"])
# def enter_pin():
#     if "user_id" not in session:
#         return redirect("/login")

#     if request.method == "POST":
#         entered_pin = request.form["pin"]

#         conn = sqlite3.connect("test.db")
#         cursor = conn.cursor()

#         cursor.execute(
#             "SELECT pin FROM users WHERE id=?",
#             (session["user_id"],)
#         )

#         result = cursor.fetchone()
#         conn.close()

#         if result and entered_pin == result[0]:
#             return redirect("/welcome")
#         else:
#             return "Incorrect PIN"

#     return render_template("enter_pin.html")


# # ----------------------------
# # WELCOME PAGE
# # ----------------------------
# @app.route("/welcome")
# def welcome():
#     if "user_id" not in session:
#         return redirect("/login")

#     return render_template("welcome.html", username=session["username"])


# # ----------------------------
# # JOURNAL PAGE
# # ----------------------------
# @app.route("/journal", methods=["GET", "POST"])
# def journal():
#     if "user_id" not in session:
#         return redirect("/login")

#     if request.method == "POST":
#         title = request.form.get("title", "")
#         content1 = request.form.get("content1", "")
#         content2 = request.form.get("content2", "")
#         content3 = request.form.get("content3", "")
#         gratitude = request.form.get("gratitude", "")
#         entry_id = request.form.get("entry_id", None)
        
#         # Combine all content fields
#         content = f"{content1}\n\n{content2}\n\n{content3}\n\nGrateful for: {gratitude}"
#         date = datetime.now().strftime("%d-%m-%Y")

#         image = request.files.get("image")
#         image_path = ""

#         if image and image.filename != "":
#             filename = datetime.now().strftime("%Y%m%d%H%M%S_") + image.filename
#             image_path = os.path.join("static/uploads", filename)
#             image.save(image_path)

#         conn = sqlite3.connect("test.db")
#         cursor = conn.cursor()

#         if entry_id:
#             # Update existing entry
#             if image_path:
#                 cursor.execute("""
#                     UPDATE entries
#                     SET title=?, content=?, image_path=?
#                     WHERE id=? AND user_id=?
#                 """, (title, content, image_path, entry_id, session["user_id"]))
#             else:
#                 cursor.execute("""
#                     UPDATE entries
#                     SET title=?, content=?
#                     WHERE id=? AND user_id=?
#                 """, (title, content, entry_id, session["user_id"]))
#         else:
#             # Create new entry
#             cursor.execute("""
#                 INSERT INTO entries (user_id, title, content, date, image_path)
#                 VALUES (?, ?, ?, ?, ?)
#             """, (session["user_id"], title, content, date, image_path))

#         conn.commit()
#         conn.close()

#         return redirect("/entries")

#     today = datetime.now().strftime("%d-%m-%Y")
#     return render_template("journal.html", date=today)


# # ----------------------------
# # ENTRIES PAGE
# # ----------------------------
# @app.route("/entries")
# def entries():
#     if "user_id" not in session:
#         return redirect("/login")

#     conn = sqlite3.connect("test.db")
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT * FROM entries WHERE user_id=? ORDER BY id DESC",
#         (session["user_id"],)
#     )

#     entries = cursor.fetchall()
#     conn.close()

#     return render_template("entries.html", entries=entries)


# # ----------------------------
# # EDIT ENTRY
# # ----------------------------
# @app.route("/edit/<int:entry_id>", methods=["GET", "POST"])
# def edit_entry(entry_id):
#     if "user_id" not in session:
#         return redirect("/login")

#     conn = sqlite3.connect("test.db")
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT * FROM entries WHERE id=? AND user_id=?",
#         (entry_id, session["user_id"])
#     )

#     entry = cursor.fetchone()
#     conn.close()

#     if not entry:
#         return redirect("/entries")

#     # Parse combined content back into separate fields
#     content = entry[3]  # Combined content
#     content1 = ""
#     content2 = ""
#     content3 = ""
#     gratitude = ""

#     # Split by double newlines
#     parts = content.split("\n\n")
#     if len(parts) >= 1:
#         content1 = parts[0]
#     if len(parts) >= 2:
#         content2 = parts[1]
#     if len(parts) >= 3:
#         content3 = parts[2]
#     if len(parts) >= 4:
#         # Extract gratitude from the "Grateful for: ..." part
#         gratitude_part = parts[3]
#         if gratitude_part.startswith("Grateful for: "):
#             gratitude = gratitude_part[14:]  # Remove "Grateful for: " prefix

#     return render_template(
#         "journal.html",
#         entry_id=entry_id,
#         entry_title=entry[2],
#         entry_date=entry[4],
#         content1=content1,
#         content2=content2,
#         content3=content3,
#         gratitude=gratitude,
#         image_path=entry[6],  # image_path
#         button_text="Update Entry"
#     )


# # ----------------------------
# # DELETE ENTRY
# # ----------------------------
# @app.route("/delete/<int:entry_id>")
# def delete_entry(entry_id):
#     if "user_id" not in session:
#         return redirect("/login")

#     conn = sqlite3.connect("test.db")
#     cursor = conn.cursor()

#     cursor.execute(
#         "DELETE FROM entries WHERE id=? AND user_id=?",
#         (entry_id, session["user_id"])
#     )

#     conn.commit()
#     conn.close()

#     return redirect("/entries")


# # ----------------------------
# # LOGOUT
# # ----------------------------
# @app.route("/logout")
# def logout():
#     session.clear()
#     return redirect("/")

# # ----------------------------
# # RUN APP (MUST BE LAST)
# # ----------------------------
# if __name__ == "__main__":
#     init_db()
#     app.run(debug=True)