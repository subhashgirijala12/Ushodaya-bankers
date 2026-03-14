from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
import bcrypt
import random
from datetime import datetime, timedelta, date

app = Flask(__name__)
app.secret_key = "ushodaya-secret-key"

# =========================
# DB CONNECTION
# =========================
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Deepak@0543",
    database="ushodaya_bankers"
)
cursor = db.cursor(dictionary=True)

# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_input = request.form["username"].strip()
        password = request.form["password"]

        cursor.execute(
            "SELECT * FROM admins WHERE username=%s OR email=%s",
            (user_input, user_input)
        )
        admin = cursor.fetchone()

        if not admin:
            return render_template("login.html", error="User not found")

        if bcrypt.checkpw(password.encode("utf-8"), admin["password_hash"].encode("utf-8")):
            session["admin"] = admin["username"]
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Wrong password")

    return render_template("login.html")


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))


# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")


# ---------- FORGOT PASSWORD ----------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        user_input = request.form["email"].strip()

        cursor.execute(
            "SELECT * FROM admins WHERE username=%s OR email=%s",
            (user_input, user_input)
        )
        admin = cursor.fetchone()

        if not admin:
            return "❌ No account found"

        otp = str(random.randint(100000, 999999))
        expiry = datetime.now() + timedelta(minutes=5)

        cursor.execute(
            "UPDATE admins SET otp=%s, otp_expiry=%s WHERE id=%s",
            (otp, expiry, admin["id"])
        )
        db.commit()

        print("🔐 OTP (for testing):", otp)
        return redirect(url_for("verify_otp", user_id=admin["id"]))

    return render_template("forgot_password.html")


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    user_id = request.args.get("user_id")

    if not user_id:
        return "❌ Invalid request"

    if request.method == "POST":
        entered_otp = request.form["otp"].strip()

        cursor.execute(
            "SELECT otp, otp_expiry FROM admins WHERE id=%s",
            (user_id,)
        )
        admin = cursor.fetchone()

        if not admin:
            return "❌ User not found"

        if admin["otp"] != entered_otp:
            return "❌ Invalid OTP"

        if admin["otp_expiry"] < datetime.now():
            return "❌ OTP expired"

        return redirect(url_for("reset_password", user_id=user_id))

    return render_template("verify_otp.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    user_id = request.args.get("user_id")

    if not user_id:
        return "❌ Invalid request"

    if request.method == "POST":
        new_password = request.form["password"]
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        cursor.execute(
            "UPDATE admins SET password_hash=%s, otp=NULL, otp_expiry=NULL WHERE id=%s",
            (hashed, user_id)
        )
        db.commit()

        return redirect(url_for("login"))

    return render_template("reset_password.html")


# ---------- CREATE LOAN API ----------
@app.route("/api/loans", methods=["POST"])
def create_loan():
    if "admin" not in session:
        return {"success": False, "message": "Unauthorized"}, 401

    data = request.get_json()

    try:
        full_name = data["full_name"]
        address = data["address"]
        loan_date = data["loan_date"]
        loan_amount = float(data["loan_amount"])
        gold_items = data["gold_items"]
        total_weight = float(data["total_weight"])
        carats = int(data["carats"])
        ornament_name = data["ornament_name"]

        monthly_interest = round(loan_amount * 0.02, 2)

        cursor.execute(
            "INSERT INTO customers (full_name, address) VALUES (%s, %s)",
            (full_name, address)
        )
        customer_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO loans
            (customer_id, loan_date, loan_amount, gold_items, total_weight, carats, ornament_name, monthly_interest)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (customer_id, loan_date, loan_amount, gold_items, total_weight, carats, ornament_name, monthly_interest))

        db.commit()
        return {"success": True, "message": "Loan saved successfully"}

    except Exception as e:
        print("❌ Error:", e)
        return {"success": False, "message": str(e)}, 500


# ---------- GET LOANS + INTEREST TILL NOW ----------
@app.route("/api/loans", methods=["GET"])
def get_loans():
    if "admin" not in session:
        return {"success": False, "message": "Unauthorized"}, 401

    cursor.execute("""
        SELECT 
             l.id,
            c.full_name,
            l.loan_amount,
            l.monthly_interest,
            l.loan_date,
            IFNULL(l.interest_paid, 0) AS interest_paid,
            IFNULL(l.principal_paid, 0) AS principal_paid
            FROM loans l
            JOIN customers c ON l.customer_id = c.id
            ORDER BY l.id DESC
         """)
    loans = cursor.fetchall()

    today = date.today()
    result = []

    for loan in loans:
        loan_date = loan["loan_date"]
        months_passed = (today.year - loan_date.year) * 12 + (today.month - loan_date.month)
        months_passed = max(months_passed, 0)

        interest_till_now = round(months_passed * float(loan["monthly_interest"]), 2)
        remaining_interest = max(interest_till_now - float(loan["interest_paid"]), 0)
        remaining_principal = max(float(loan["loan_amount"]) - float(loan["principal_paid"]), 0)


        result.append({
             "loan_id": loan["id"], 
            "full_name": loan["full_name"],
            "loan_amount": float(loan["loan_amount"]),
            "monthly_interest": float(loan["monthly_interest"]),
            "interest_till_now": interest_till_now,
            "remaining_interest": remaining_interest, 
            "remaining_principal": remaining_principal,
            "months_passed": months_passed,
            "loan_date": loan_date.strftime("%Y-%m-%d")
        })

    return {"success": True, "loans": result}

# ---------- PAY API (NEW - ONLY ADDITION) ----------
@app.route("/api/pay", methods=["POST"])
def pay_amount():
    if "admin" not in session:
        return {"success": False, "message": "Unauthorized"}, 401

    data = request.get_json()
    loan_id = data["loan_id"]
    pay_interest = float(data.get("pay_interest", 0))
    pay_principal = float(data.get("pay_principal", 0))

    cursor.execute("SELECT interest_paid, principal_paid FROM loans WHERE id=%s", (loan_id,))
    loan = cursor.fetchone()

    new_interest_paid = float(loan["interest_paid"]) + pay_interest
    new_principal_paid = float(loan["principal_paid"]) + pay_principal

    cursor.execute("""
        UPDATE loans
        SET interest_paid=%s, principal_paid=%s
        WHERE id=%s
    """, (new_interest_paid, new_principal_paid, loan_id))

    db.commit()
    return {"success": True, "message": "Payment recorded successfully"}



if __name__ == "__main__":
    app.run(debug=True)
