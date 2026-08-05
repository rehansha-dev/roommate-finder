import os
import sqlite3

from flask import Flask, render_template, request


app = Flask(__name__)

# The key is the number selected in the "Room type" field.
ROOM_LIMITS = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6}
DATABASE_URL = os.environ.get("DATABASE_URL")
DATABASE = os.path.join(app.root_path, "database.db")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "822711")


def database_is_postgres():
    return bool(DATABASE_URL and DATABASE_URL.startswith(("postgres://", "postgresql://")))


def get_db():
    """Return a SQLite connection for this application."""
    if database_is_postgres():
        import psycopg
        return psycopg.connect(DATABASE_URL)
    return sqlite3.connect(DATABASE)


def placeholder():
    """Use the parameter placeholder expected by the active database driver."""
    return "%s" if database_is_postgres() else "?"


def init_db():
    with get_db() as conn:
        if database_is_postgres():
            conn.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    room TEXT NOT NULL,
                    room_type TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    UNIQUE(name, room, room_type)
                )
            """)
        else:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    room TEXT NOT NULL,
                    room_type TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    UNIQUE(name, room, room_type)
                )
            """)


init_db()


@app.route("/")
def home():
    return render_template("index.html", room_limits=ROOM_LIMITS)


@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name", "").strip()
    room = request.form.get("room", "").strip()
    room_type = request.form.get("room_type", "").strip()
    contact = request.form.get("contact", "").strip()

    if not all([name, room, room_type, contact]) or room_type not in ROOM_LIMITS:
        return render_template(
            "result.html", error="Please complete every field with a valid room type.",
            roommates=[], count=0, limit=0
        ), 400

    limit = ROOM_LIMITS[room_type]
    # BEGIN IMMEDIATE prevents two simultaneous requests from both taking the last bed.
    with get_db() as conn:
        if not database_is_postgres():
            conn.execute("BEGIN IMMEDIATE")
        mark = placeholder()
        students = conn.execute(
            "SELECT id, name, room, room_type, contact FROM students "
            f"WHERE room = {mark} AND room_type = {mark}",
            (room, room_type),
        ).fetchall()
        existing = next((student for student in students if student[1].lower() == name.lower()), None)

        if len(students) >= limit and existing is None:
            return render_template(
                "result.html", error="This room is already full.", roommates=[],
                count=len(students), limit=limit
            )

        if existing is None:
            conn.execute(
                f"INSERT INTO students (name, room, room_type, contact) VALUES ({mark}, {mark}, {mark}, {mark})",
                (name, room, room_type, contact),
            )

        roommates = conn.execute(
            "SELECT name, contact FROM students "
            f"WHERE room = {mark} AND room_type = {mark} AND lower(name) != lower({mark}) "
            "ORDER BY name",
            (room, room_type, name),
        ).fetchall()
        count = len(students) + (1 if existing is None else 0)

    return render_template(
        "result.html", error=None, roommates=roommates, count=count, limit=limit,
        room=room, room_type=room_type
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") != ADMIN_PASSWORD:
            return render_template("admin_login.html", error="Wrong password."), 401

        with get_db() as conn:
            users = conn.execute(
                "SELECT id, name, room, room_type, contact FROM students "
                "ORDER BY room, room_type, name"
            ).fetchall()
        return render_template("admin.html", total=len(users), users=users)

    return render_template("admin_login.html", error=None)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=False)
