import os
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

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


def _get_local_user_profile():
    with get_connection() as conn:
        row = conn.execute("SELECT name, email, updated_at FROM user_profile WHERE id = 1").fetchone()
    if row is None:
        return {
            "name": "SpendSense User",
            "email": "user@spendsense.local",
            "updated_at": None,
        }
    return {
        "name": row["name"],
        "email": row["email"],
        "updated_at": row["updated_at"],
    }


def _save_local_user_profile(name: str, email: str):
    timestamp = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_profile (id, name, email, updated_at)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                email = excluded.email,
                updated_at = excluded.updated_at
            """,
            (name, email, timestamp),
        )
        conn.commit()


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route("/add_expense", methods=["POST"])
def add_expense():
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
            "INSERT INTO expenses (name, amount, category, timestamp) VALUES (?, ?, ?, ?)",
            (name, amount, category, timestamp),
        )
        conn.commit()
        expense_id = cursor.lastrowid

        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()

    saved = _row_to_expense(row)
    return jsonify(saved.to_dict()), 201


@app.route("/expenses", methods=["GET"])
def get_expenses():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM expenses ORDER BY timestamp DESC").fetchall()

    expenses = [_row_to_expense(row).to_dict() for row in rows]
    return jsonify(expenses), 200


@app.route("/summary", methods=["GET"])
def get_summary():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM expenses ORDER BY timestamp DESC").fetchall()

    expenses = [_row_to_expense(row) for row in rows]
    expense_data = [expense.to_dict() for expense in expenses]

    total_spending = round(sum(e.amount for e in expenses), 2)
    category_totals = defaultdict(float)
    for e in expenses:
        category_totals[e.category] += e.amount

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


@app.route("/user_profile", methods=["GET"])
def user_profile():
    local_profile = _get_local_user_profile()
    try:
        blackboard = _get_blackboard_service()
        provider_profile = blackboard.get_user_profile()
        return (
            jsonify(
                {
                    **local_profile,
                    "provider_info": provider_profile.get("profile_info", {}),
                }
            ),
            200,
        )
    except Exception as exc:
        return jsonify({**local_profile, "provider_error": str(exc)}), 200


@app.route("/user_profile", methods=["PUT"])
def update_user_profile():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip()

    if not name:
        return jsonify({"error": "Name is required."}), 400
    if not email or "@" not in email:
        return jsonify({"error": "A valid email is required."}), 400

    _save_local_user_profile(name=name, email=email)
    local_profile = _get_local_user_profile()
    return jsonify(local_profile), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
