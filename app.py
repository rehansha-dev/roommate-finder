import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

HOSTELS = {
    "boys": ["Vedavanti", "Ganga A", "Ganga B"],
    "girls": ["Krishna", "Yamuna", "Godavari", "Narmada"],
    "gays": ["brothel"],
}
CAPACITY_PRESETS = [2, 3, 4, 5, 6]
MIN_CAPACITY = 1
MAX_CAPACITY = 12

DATABASE_URL = os.environ.get("DATABASE_URL")
DATABASE = os.path.join(app.root_path, "database.db")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "258025")


def database_is_postgres():
    return bool(DATABASE_URL and DATABASE_URL.startswith(("postgres://", "postgresql://")))


def get_db():
    """Return a fresh connection for this application."""
    if database_is_postgres():
        import psycopg
        return psycopg.connect(DATABASE_URL)
    return sqlite3.connect(DATABASE)


def placeholder():
    """Use the parameter placeholder expected by the active database driver."""
    return "%s" if database_is_postgres() else "?"


def _add_column_if_missing(conn, name, coltype):
    """Best-effort migration: add a column, ignore failure if it already exists."""
    try:
        conn.execute(f"ALTER TABLE students ADD COLUMN {name} {coltype}")
        conn.commit()
    except Exception:
        conn.rollback()


def init_db():
    conn = get_db()
    try:
        if database_is_postgres():
            conn.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    room TEXT NOT NULL,
                    room_type TEXT NOT NULL,
                    contact TEXT NOT NULL
                )
            """)
        else:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    room TEXT NOT NULL,
                    room_type TEXT NOT NULL,
                    contact TEXT NOT NULL
                )
            """)
        conn.commit()

        # Migrate older databases that predate the gender/hostel fields.
        _add_column_if_missing(conn, "gender", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "hostel", "TEXT NOT NULL DEFAULT ''")
    finally:
        conn.close()


init_db()


def admin_required():
    return session.get("is_admin", False)


@app.route("/")
def home():
    return render_template(
        "index.html", hostels=HOSTELS, capacity_presets=CAPACITY_PRESETS,
        min_capacity=MIN_CAPACITY, max_capacity=MAX_CAPACITY
    )


@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name", "").strip()
    gender = request.form.get("gender", "").strip().lower()
    hostel = request.form.get("hostel", "").strip()
    room = request.form.get("room", "").strip()
    room_type = request.form.get("room_type", "").strip()
    contact = request.form.get("contact", "").strip()

    valid_hostels = HOSTELS.get(gender, [])

    if not all([name, gender, hostel, room, room_type, contact]) \
            or hostel not in valid_hostels or not room_type.isdigit():
        return render_template(
            "result.html", error="Please complete every field correctly.",
            roommates=[], count=0, limit=0
        ), 400

    limit = int(room_type)
    if limit < MIN_CAPACITY or limit > MAX_CAPACITY:
        return render_template(
            "result.html",
            error=f"Room capacity must be between {MIN_CAPACITY} and {MAX_CAPACITY}.",
            roommates=[], count=0, limit=0
        ), 400

    with get_db() as conn:
        if not database_is_postgres():
            conn.execute("BEGIN IMMEDIATE")
        mark = placeholder()
        students = conn.execute(
            "SELECT id, name, gender, hostel, room, room_type, contact FROM students "
            f"WHERE hostel = {mark} AND room = {mark} AND room_type = {mark}",
            (hostel, room, room_type),
        ).fetchall()
        existing = next((s for s in students if s[1].lower() == name.lower()), None)

        if len(students) >= limit and existing is None:
            return render_template(
                "result.html", error="This room is already full.", roommates=[],
                count=len(students), limit=limit
            )

        if existing is None:
            conn.execute(
                "INSERT INTO students (name, gender, hostel, room, room_type, contact) "
                f"VALUES ({mark}, {mark}, {mark}, {mark}, {mark}, {mark})",
                (name, gender, hostel, room, room_type, contact),
            )

        roommates = conn.execute(
            "SELECT name, contact FROM students "
            f"WHERE hostel = {mark} AND room = {mark} AND room_type = {mark} "
            f"AND lower(name) != lower({mark}) ORDER BY name",
            (hostel, room, room_type, name),
        ).fetchall()
        count = len(students) + (1 if existing is None else 0)

    return render_template(
        "result.html", error=None, roommates=roommates, count=count, limit=limit,
        room=room, room_type=room_type, hostel=hostel
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") != ADMIN_PASSWORD:
            return render_template("admin_login.html", error="Wrong password."), 401
        session["is_admin"] = True

    if not admin_required():
        return render_template("admin_login.html", error=None)

    with get_db() as conn:
        users = conn.execute(
            "SELECT id, name, gender, hostel, room, room_type, contact FROM students "
            "ORDER BY hostel, room, room_type, name"
        ).fetchall()
    return render_template("admin.html", total=len(users), users=users)


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:student_id>", methods=["POST"])
def admin_delete(student_id):
    if not admin_required():
        return redirect(url_for("admin"))
    with get_db() as conn:
        mark = placeholder()
        conn.execute(f"DELETE FROM students WHERE id = {mark}", (student_id,))
    return redirect(url_for("admin"))


@app.route("/admin/reset_room", methods=["POST"])
def admin_reset_room():
    if not admin_required():
        return redirect(url_for("admin"))
    hostel = request.form.get("hostel", "")
    room = request.form.get("room", "")
    room_type = request.form.get("room_type", "")
    with get_db() as conn:
        mark = placeholder()
        conn.execute(
            f"DELETE FROM students WHERE hostel = {mark} AND room = {mark} AND room_type = {mark}",
            (hostel, room, room_type),
        )
    return redirect(url_for("admin"))


@app.route("/admin/reset_all", methods=["POST"])
def admin_reset_all():
    if not admin_required():
        return redirect(url_for("admin"))
    with get_db() as conn:
        conn.execute("DELETE FROM students")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=False)
