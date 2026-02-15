import os
from collections import defaultdict
from datetime import datetime
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

from blackboard_service import BlackboardService
from database import get_connection, init_db
from gemini_service import GeminiService
from models import Expense


load_dotenv()

app = Flask(__name__)
CORS(app)
init_db()


def _get_gemini_service():
    return GeminiService()


def _get_blackboard_service():
    return BlackboardService()


def _row_to_expense(row):
    return Expense(
        id=row["id"],
        name=row["name"],
        amount=row["amount"],
        category=row["category"],
        timestamp=row["timestamp"],
    )


def _auth_error(message="Unauthorized"):
    return jsonify({"error": message}), 401


def _month_key(ts: datetime | None = None):
    now = ts or datetime.utcnow()
    return now.strftime("%Y-%m")


def _get_current_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "", 1).strip()
    if not token:
        return None

    with get_connection() as conn:
        user = conn.execute(
            """
            SELECT id, name, email, phone, account_details, auth_token
            FROM users
            WHERE auth_token = ?
            """,
            (token,),
        ).fetchone()
    return user


def _require_user():
    user = _get_current_user()
    if user is None:
        return None, _auth_error()
    return user, None


def _load_budget(user_id: int, month: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT amount, updated_at FROM budgets WHERE user_id = ? AND month = ?",
            (user_id, month),
        ).fetchone()
    if row is None:
        return None
    return {"amount": round(float(row["amount"]), 2), "updated_at": row["updated_at"]}


def _get_month_debits(user_id: int, month: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ? AND substr(timestamp, 1, 7) = ?",
            (user_id, month),
        ).fetchone()
    return round(float(row["total"] or 0), 2)


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route("/auth/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    if not name:
        return jsonify({"error": "Name is required."}), 400
    if not email or "@" not in email:
        return jsonify({"error": "A valid email is required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    now = datetime.utcnow().isoformat()
    token = str(uuid4())

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (name, email, phone, account_details, password_hash, auth_token, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, email, "", "", generate_password_hash(password), token, now, now),
            )
            user_id = cursor.lastrowid
            conn.commit()
    except Exception:
        return jsonify({"error": "Email is already registered."}), 409

    return (
        jsonify(
            {
                "token": token,
                "user": {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "phone": "",
                    "account_details": "",
                },
            }
        ),
        201,
    )


@app.route("/auth/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    with get_connection() as conn:
        user = conn.execute(
            "SELECT id, name, email, phone, account_details, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid email or password."}), 401

        token = str(uuid4())
        conn.execute(
            "UPDATE users SET auth_token = ?, updated_at = ? WHERE id = ?",
            (token, datetime.utcnow().isoformat(), user["id"]),
        )
        conn.commit()

    return (
        jsonify(
            {
                "token": token,
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "phone": user["phone"] or "",
                    "account_details": user["account_details"] or "",
                },
            }
        ),
        200,
    )


@app.route("/auth/me", methods=["GET"])
def auth_me():
    user, error = _require_user()
    if error:
        return error
    return (
        jsonify(
            {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "phone": user["phone"] or "",
                "account_details": user["account_details"] or "",
            }
        ),
        200,
    )


@app.route("/add_expense", methods=["POST"])
def add_expense():
    user, error = _require_user()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    amount = payload.get("amount")

    if not name:
        return jsonify({"error": "Expense name is required."}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Amount must be a positive number."}), 400

    try:
        gemini = _get_gemini_service()
        category = gemini.categorize_expense(name)
    except Exception as exc:
        return jsonify({"error": f"Gemini initialization failed: {str(exc)}"}), 500

    timestamp = datetime.utcnow().isoformat()

    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, name, amount, category, timestamp) VALUES (?, ?, ?, ?, ?)",
            (user["id"], name, amount, category, timestamp),
        )
        conn.commit()
        expense_id = cursor.lastrowid

        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()

    saved = _row_to_expense(row)
    return jsonify(saved.to_dict()), 201


@app.route("/expenses", methods=["GET"])
def get_expenses():
    user, error = _require_user()
    if error:
        return error

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY timestamp DESC",
            (user["id"],),
        ).fetchall()

    expenses = [_row_to_expense(row).to_dict() for row in rows]
    return jsonify(expenses), 200


@app.route("/summary", methods=["GET"])
def get_summary():
    user, error = _require_user()
    if error:
        return error

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY timestamp DESC",
            (user["id"],),
        ).fetchall()

    expenses = [_row_to_expense(row) for row in rows]
    expense_data = [expense.to_dict() for expense in expenses]

    total_spending = round(sum(e.amount for e in expenses), 2)
    category_totals = defaultdict(float)
    for expense in expenses:
        category_totals[expense.category] += expense.amount

    spending_per_category = {
        category: round(amount, 2) for category, amount in category_totals.items()
    }

    insight = "No expenses yet. Add one to generate AI insights."
    if expense_data:
        try:
            gemini = _get_gemini_service()
            insight = gemini.generate_insights(expense_data)
        except Exception as exc:
            insight = f"Unable to generate insights: {str(exc)}"

    return (
        jsonify(
            {
                "total_spending": total_spending,
                "spending_per_category": spending_per_category,
                "ai_insight": insight,
            }
        ),
        200,
    )


@app.route("/user_settings", methods=["GET"])
def get_user_settings():
    user, error = _require_user()
    if error:
        return error

    month = str(request.args.get("month") or _month_key())
    budget = _load_budget(user["id"], month)
    debits = _get_month_debits(user["id"], month)

    response = {
        "name": user["name"],
        "email": user["email"],
        "phone": user["phone"] or "",
        "account_details": user["account_details"] or "",
        "month": month,
        "monthly_budget": budget["amount"] if budget else None,
        "monthly_debits": debits,
    }

    try:
        blackboard = _get_blackboard_service()
        provider_profile = blackboard.get_user_profile()
        response["provider_info"] = provider_profile.get("profile_info", {})
    except Exception as exc:
        response["provider_error"] = str(exc)

    return jsonify(response), 200


@app.route("/user_settings", methods=["PUT"])
def update_user_settings():
    user, error = _require_user()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    phone = str(payload.get("phone", "")).strip()
    account_details = str(payload.get("account_details", "")).strip()
    month = str(payload.get("month") or _month_key())
    budget_amount = payload.get("monthly_budget")

    if not name:
        return jsonify({"error": "Name is required."}), 400
    if not email or "@" not in email:
        return jsonify({"error": "A valid email is required."}), 400

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ? AND id != ?",
            (email, user["id"]),
        ).fetchone()
        if existing is not None:
            return jsonify({"error": "Email is already used by another account."}), 409

        conn.execute(
            "UPDATE users SET name = ?, email = ?, phone = ?, account_details = ?, updated_at = ? WHERE id = ?",
            (name, email, phone, account_details, datetime.utcnow().isoformat(), user["id"]),
        )

        if budget_amount not in (None, ""):
            try:
                budget_value = float(budget_amount)
                if budget_value <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                return jsonify({"error": "Monthly budget must be a positive number."}), 400

            now = datetime.utcnow().isoformat()
            conn.execute(
                """
                INSERT INTO budgets (user_id, month, amount, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, month) DO UPDATE SET
                    amount = excluded.amount,
                    updated_at = excluded.updated_at
                """,
                (user["id"], month, budget_value, now),
            )

        conn.commit()

    return get_user_settings()


@app.route("/budget/current", methods=["GET"])
def get_current_budget():
    user, error = _require_user()
    if error:
        return error

    month = str(request.args.get("month") or _month_key())
    budget = _load_budget(user["id"], month)

    return jsonify({"month": month, "budget": budget}), 200


@app.route("/budget/current", methods=["PUT"])
def set_current_budget():
    user, error = _require_user()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    month = str(payload.get("month") or _month_key())

    try:
        amount = float(payload.get("amount"))
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Budget amount must be a positive number."}), 400

    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO budgets (user_id, month, amount, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, month) DO UPDATE SET
                amount = excluded.amount,
                updated_at = excluded.updated_at
            """,
            (user["id"], month, amount, now),
        )
        conn.commit()

    return jsonify({"month": month, "amount": round(amount, 2), "updated_at": now}), 200


@app.route("/reports", methods=["GET"])
def reports():
    user, error = _require_user()
    if error:
        return error

    month = str(request.args.get("month") or _month_key())

    with get_connection() as conn:
        month_rows = conn.execute(
            """
            SELECT * FROM expenses
            WHERE user_id = ? AND substr(timestamp, 1, 7) = ?
            ORDER BY timestamp DESC
            """,
            (user["id"], month),
        ).fetchall()

    expenses = [_row_to_expense(row) for row in month_rows]
    total = round(sum(item.amount for item in expenses), 2)

    by_category = defaultdict(float)
    by_day = defaultdict(float)
    for item in expenses:
        by_category[item.category] += item.amount
        by_day[item.timestamp[:10]] += item.amount

    sorted_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    top_category = sorted_categories[0][0] if sorted_categories else None
    top_expense = max(expenses, key=lambda x: x.amount).to_dict() if expenses else None

    budget = _load_budget(user["id"], month)
    budget_amount = budget["amount"] if budget else None
    budget_remaining = None if budget_amount is None else round(budget_amount - total, 2)

    return (
        jsonify(
            {
                "month": month,
                "expense_count": len(expenses),
                "total_spending": total,
                "daily_average": round(total / len(by_day), 2) if by_day else 0,
                "top_category": top_category,
                "spending_per_category": {k: round(v, 2) for k, v in by_category.items()},
                "top_expense": top_expense,
                "budget": budget_amount,
                "budget_remaining": budget_remaining,
            }
        ),
        200,
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
