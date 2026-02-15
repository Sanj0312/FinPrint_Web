import os
import csv
from collections import Counter, defaultdict
from datetime import datetime
from functools import lru_cache
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
    _seed_csv_expenses_for_user(user["id"])
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


def _load_income_profile(user_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT monthly_income, savings_goal_pct, updated_at
            FROM income_profiles
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "monthly_income": round(float(row["monthly_income"]), 2),
        "savings_goal_pct": round(float(row["savings_goal_pct"]), 2),
        "updated_at": row["updated_at"],
    }


def _dataset_file_path():
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "us_expense_dataset_large.csv",
    )


def _parse_dataset_date(raw_value: str):
    value = (raw_value or "").strip()
    if not value:
        return None

    date_formats = ("%m/%d/%Y %H:%M", "%m/%d/%Y", "%Y-%m-%d")
    for fmt in date_formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@lru_cache(maxsize=1)
def _compute_dataset_analytics():
    dataset_path = _dataset_file_path()
    if not os.path.exists(dataset_path):
        raise FileNotFoundError("Dataset file 'us_expense_dataset_large.csv' was not found.")

    total_income = 0.0
    total_expense = 0.0
    row_count = 0
    currency = "USD"

    category_totals = Counter()
    subcategory_totals = Counter()
    account_totals = Counter()
    monthly_expense = Counter()
    monthly_income = Counter()

    with open(dataset_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_count += 1
            tx_type = str(row.get("Income/Expense", "")).strip().lower()
            category = str(row.get("Category", "Other")).strip() or "Other"
            subcategory = str(row.get("Subcategory", "Other")).strip() or "Other"
            account = str(row.get("Account", "Unknown")).strip() or "Unknown"
            date_raw = str(row.get("Date", "")).strip()
            currency = str(row.get("Currency", currency)).strip() or currency

            try:
                amount = float(row.get("Amount") or 0)
            except ValueError:
                amount = 0.0

            parsed_date = _parse_dataset_date(date_raw)
            month_key = parsed_date.strftime("%Y-%m") if parsed_date else "Unknown"

            if tx_type == "income":
                total_income += amount
                monthly_income[month_key] += amount
            else:
                total_expense += amount
                category_totals[category] += amount
                subcategory_totals[subcategory] += amount
                account_totals[account] += amount
                monthly_expense[month_key] += amount

    top_categories = [
        {"name": name, "value": round(value, 2)}
        for name, value in category_totals.most_common(8)
    ]
    top_subcategories = [
        {"name": name, "value": round(value, 2)}
        for name, value in subcategory_totals.most_common(8)
    ]
    top_accounts = [
        {"name": name, "value": round(value, 2)}
        for name, value in account_totals.most_common(8)
    ]

    months = sorted(set(monthly_expense.keys()) | set(monthly_income.keys()))
    monthly_trend = [
        {
            "month": month,
            "expense": round(monthly_expense.get(month, 0.0), 2),
            "income": round(monthly_income.get(month, 0.0), 2),
        }
        for month in months
        if month != "Unknown"
    ]

    return {
        "currency": currency,
        "rows": row_count,
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "net_balance": round(total_income - total_expense, 2),
        "category_share": {
            category: round((value / total_expense), 4) if total_expense > 0 else 0.0
            for category, value in category_totals.items()
        },
        "top_categories": top_categories,
        "top_subcategories": top_subcategories,
        "top_accounts": top_accounts,
        "monthly_trend": monthly_trend,
    }


@lru_cache(maxsize=1)
def _load_csv_expense_history():
    dataset_path = _dataset_file_path()
    if not os.path.exists(dataset_path):
        return []

    entries = []
    with open(dataset_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            tx_type = str(row.get("Income/Expense", "")).strip().lower()
            if tx_type != "expense":
                continue

            try:
                amount = float(row.get("Amount") or 0)
            except ValueError:
                amount = 0.0

            if amount <= 0:
                continue

            raw_date = str(row.get("Date", "")).strip()
            parsed_date = _parse_dataset_date(raw_date)
            timestamp = parsed_date.isoformat() if parsed_date else raw_date
            note = str(row.get("Note", "")).strip()
            subcategory = str(row.get("Subcategory", "")).strip()
            category = str(row.get("Category", "")).strip() or "Other"
            name = note or subcategory or category

            entries.append(
                {
                    "id": f"csv-{idx}",
                    "name": name,
                    "amount": round(amount, 2),
                    "category": category,
                    "timestamp": timestamp,
                    "source": "csv",
                    "can_edit": False,
                    "can_delete": False,
                }
            )

    return entries


def _seed_csv_expenses_for_user(user_id: int):
    csv_expenses = _load_csv_expense_history()
    if not csv_expenses:
        return

    with get_connection() as conn:
        for expense in csv_expenses:
            conn.execute(
                """
                INSERT OR IGNORE INTO expenses (user_id, external_id, name, amount, category, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    str(expense["id"]),
                    expense["name"],
                    float(expense["amount"]),
                    expense["category"],
                    expense["timestamp"],
                ),
            )
        conn.commit()


def _categorize_expense_name(expense_name: str, fallback: str = "Other"):
    try:
        gemini = _get_gemini_service()
        return gemini.categorize_expense(expense_name)
    except Exception:
        return fallback


def _format_share_comparison(category: str, user_share: float, avg_share: float):
    if avg_share <= 0:
        return f"Your {category} spend is significant, but there is no dataset benchmark available."

    delta_pct = ((user_share - avg_share) / avg_share) * 100
    if delta_pct >= 0:
        direction = "more"
    else:
        direction = "less"

    return f"You spend {abs(round(delta_pct))}% {direction} on {category} than average."


def _load_user_expenses(user_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,),
        ).fetchall()
    return [_row_to_expense(row) for row in rows]


def _load_user_month_expenses(user_id: int, month: str):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM expenses
            WHERE user_id = ? AND substr(timestamp, 1, 7) = ?
            ORDER BY timestamp DESC
            """,
            (user_id, month),
        ).fetchall()
    return [_row_to_expense(row) for row in rows]


def _build_money_context(user_id: int):
    month = _month_key()
    expenses = _load_user_expenses(user_id)
    month_expenses = _load_user_month_expenses(user_id, month)

    total_spend = round(sum(item.amount for item in expenses), 2)
    category_totals = defaultdict(float)
    for item in expenses:
        category_totals[item.category] += item.amount

    spending_per_category = {k: round(v, 2) for k, v in category_totals.items()}
    total_for_shares = sum(category_totals.values())
    user_shares = {
        category: (value / total_for_shares if total_for_shares > 0 else 0.0)
        for category, value in category_totals.items()
    }

    try:
        dataset_analytics = _compute_dataset_analytics()
    except Exception:
        dataset_analytics = {}
    dataset_category_share = dataset_analytics.get("category_share", {})
    dataset_lookup = {k.lower(): float(v) for k, v in dataset_category_share.items()}

    comparisons = []
    for category, user_share in sorted(user_shares.items(), key=lambda x: x[1], reverse=True):
        avg_share = dataset_lookup.get(category.lower(), 0.0)
        comparisons.append(
            {
                "category": category,
                "user_share": round(user_share, 4),
                "average_share": round(avg_share, 4),
                "message": _format_share_comparison(category, user_share, avg_share),
            }
        )
    comparisons = comparisons[:4]

    month_category_totals = defaultdict(float)
    for item in month_expenses:
        month_category_totals[item.category] += item.amount
    month_total = round(sum(month_category_totals.values()), 2)

    recommendations = []
    subscription_monthly = 0.0
    for category, value in month_category_totals.items():
        if "subscription" in category.lower():
            subscription_monthly += value
    if subscription_monthly > 0:
        potential = round(subscription_monthly * 0.3, 2)
        recommendations.append(
            f"You can save about ${potential:.2f}/month by trimming subscription usage by 30%."
        )

    if comparisons:
        top_gap = max(
            comparisons,
            key=lambda item: ((item["user_share"] - item["average_share"]) / item["average_share"])
            if item["average_share"] > 0
            else 0,
        )
        if top_gap["average_share"] > 0 and top_gap["user_share"] > top_gap["average_share"]:
            monthly_spend_on_top = month_category_totals.get(top_gap["category"], 0.0)
            reduction_target = round(monthly_spend_on_top * 0.15, 2)
            if monthly_spend_on_top > 0 and reduction_target > 0:
                recommendations.append(
                    f"Cutting {top_gap['category']} by 15% could save around ${reduction_target:.2f}/month."
                )

    if not recommendations:
        recommendations.append("You are tracking well. Keep reviewing recurring costs monthly for extra savings.")

    income_profile = _load_income_profile(user_id)
    goal_pct = float((income_profile or {}).get("savings_goal_pct") or 20.0)
    monthly_income = (income_profile or {}).get("monthly_income")

    budget_goal = None
    target_savings = None
    remaining_budget = None
    expected_savings = None
    if monthly_income is not None:
        monthly_income_value = float(monthly_income)
        target_savings = round(monthly_income_value * (goal_pct / 100), 2)
        budget_goal = round(monthly_income_value - target_savings, 2)
        remaining_budget = round(budget_goal - month_total, 2)
        expected_savings = round(monthly_income_value - month_total, 2)

    return {
        "month": month,
        "total_spending": total_spend,
        "month_spending": month_total,
        "spending_per_category": spending_per_category,
        "comparisons": comparisons,
        "recommendations": recommendations,
        "expense_count": len(expenses),
        "income_profile": {
            "monthly_income": monthly_income,
            "savings_goal_pct": round(goal_pct, 2),
            "updated_at": (income_profile or {}).get("updated_at"),
        },
        "budget_goal": budget_goal,
        "target_savings": target_savings,
        "remaining_budget": remaining_budget,
        "expected_savings": expected_savings,
    }


def _local_coach_reply(user_message: str, context: dict):
    text = (user_message or "").lower()
    month_spending = float(context.get("month_spending") or 0.0)
    categories = context.get("spending_per_category") or {}
    top_category = None
    if categories:
        top_category = max(categories.items(), key=lambda item: float(item[1]))[0]

    lines = []

    if "wedding" in text or "marriage" in text:
        base = month_spending if month_spending > 0 else float(context.get("total_spending") or 0.0)
        monthly_goal = round(base * 0.15, 2) if base > 0 else 150.0
        ninety_day_goal = round(monthly_goal * 3, 2)
        lines.append(
            f"For the next 3 months, target saving ${monthly_goal:.2f}/month "
            f"(about ${ninety_day_goal:.2f} total) for wedding expenses."
        )
        if top_category:
            cut_amount = round((float(categories.get(top_category) or 0) * 0.2), 2)
            lines.append(
                f"Cap `{top_category}` spending by 20%; that can free about ${cut_amount:.2f} this month."
            )
        lines.append(
            "Create 3 envelopes now: venue/events, outfits/gifts, travel. Transfer money weekly into each envelope."
        )
    elif "10 percent" in text or "10%" in text:
        base = month_spending if month_spending > 0 else float(context.get("total_spending") or 0.0)
        target = round(base * 0.10, 2) if base > 0 else 100.0
        lines.append(f"To save 10%, set a monthly auto-transfer of ${target:.2f} on payday.")
        if top_category:
            cut_amount = round((float(categories.get(top_category) or 0) * 0.15), 2)
            lines.append(f"Start with `{top_category}`: reduce it by 15% to free about ${cut_amount:.2f}.")
        lines.append("Use a weekly spending cap of one quarter of your monthly budget target.")
    else:
        if top_category:
            lines.append(f"Your highest spend category is `{top_category}`. Start optimizing this first.")
        if month_spending > 0:
            weekly_cut = round((month_spending * 0.1) / 4, 2)
            lines.append(f"Cut ${weekly_cut:.2f} per week to create a consistent savings buffer.")
        lines.append("Review subscriptions and impulse purchases every Sunday and remove one recurring cost this week.")

    return "\n".join(lines)




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


@app.route("/blackboard/models", methods=["GET"])
def get_blackboard_models():
    user, error = _require_user()
    if error:
        return error

    try:
        blackboard = _get_blackboard_service()
        models = blackboard.list_models()
        return jsonify({"models": models}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/income_profile/current", methods=["GET"])
def get_income_profile():
    user, error = _require_user()
    if error:
        return error

    profile = _load_income_profile(user["id"])
    if profile is None:
        profile = {"monthly_income": None, "savings_goal_pct": 20.0, "updated_at": None}

    return jsonify(profile), 200


@app.route("/income_profile/current", methods=["PUT"])
def set_income_profile():
    user, error = _require_user()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    try:
        monthly_income = float(payload.get("monthly_income"))
        if monthly_income <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Monthly income must be a positive number."}), 400

    raw_goal = payload.get("savings_goal_pct", 20)
    try:
        savings_goal_pct = float(raw_goal)
        if savings_goal_pct <= 0 or savings_goal_pct >= 90:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Savings goal % must be between 1 and 89."}), 400

    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO income_profiles (user_id, monthly_income, savings_goal_pct, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                monthly_income = excluded.monthly_income,
                savings_goal_pct = excluded.savings_goal_pct,
                updated_at = excluded.updated_at
            """,
            (user["id"], monthly_income, savings_goal_pct, now),
        )
        conn.commit()

    return jsonify({"monthly_income": round(monthly_income, 2), "savings_goal_pct": round(savings_goal_pct, 2), "updated_at": now}), 200


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

    category = _categorize_expense_name(name, fallback="Other")

    timestamp = datetime.utcnow().isoformat()

    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, external_id, name, amount, category, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user["id"], None, name, amount, category, timestamp),
        )
        conn.commit()
        expense_id = cursor.lastrowid

        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()

    saved = _row_to_expense(row)
    created = saved.to_dict()
    created["source"] = "user"
    created["can_edit"] = True
    created["can_delete"] = True
    return jsonify(created), 201


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

    user_expenses = []
    for row in rows:
        item = _row_to_expense(row).to_dict()
        item["source"] = "user"
        item["can_edit"] = True
        item["can_delete"] = True
        user_expenses.append(item)

    return jsonify(user_expenses), 200


@app.route("/expenses/<int:expense_id>", methods=["PUT"])
def update_expense(expense_id: int):
    user, error = _require_user()
    if error:
        return error

    payload = request.get_json(silent=True) or {}

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user["id"]),
        ).fetchone()

        if row is None:
            return jsonify({"error": "Expense not found."}), 404

        current = _row_to_expense(row)

        incoming_name = payload.get("name")
        incoming_amount = payload.get("amount")

        new_name = str(incoming_name).strip() if incoming_name is not None else current.name
        if not new_name:
            return jsonify({"error": "Expense name is required."}), 400

        if incoming_amount is None:
            new_amount = float(current.amount)
        else:
            try:
                new_amount = float(incoming_amount)
                if new_amount <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                return jsonify({"error": "Amount must be a positive number."}), 400

        new_category = current.category
        if new_name != current.name:
            new_category = _categorize_expense_name(new_name, fallback=current.category or "Other")

        conn.execute(
            "UPDATE expenses SET name = ?, amount = ?, category = ? WHERE id = ? AND user_id = ?",
            (new_name, new_amount, new_category, expense_id, user["id"]),
        )
        conn.commit()

        updated_row = conn.execute(
            "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user["id"]),
        ).fetchone()

    updated = _row_to_expense(updated_row).to_dict()
    updated["source"] = "user"
    updated["can_edit"] = True
    updated["can_delete"] = True
    return jsonify(updated), 200


@app.route("/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id: int):
    user, error = _require_user()
    if error:
        return error

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user["id"]),
        ).fetchone()

        if row is None:
            return jsonify({"error": "Expense not found."}), 404

        conn.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user["id"]))
        conn.commit()

    return jsonify({"success": True, "id": expense_id}), 200


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


@app.route("/money_dna", methods=["GET"])
def get_money_dna():
    user, error = _require_user()
    if error:
        return error

    context = _build_money_context(user["id"])
    requested_model = str(request.args.get("model") or "").strip() or None

    ai_narrative = "Not enough data yet. Add more expenses to build your Money DNA."
    blackboard_comparisons = []
    generated_by = "local_rules"
    provider_info = {}
    provider_error = ""
    try:
        blackboard = _get_blackboard_service()
        provider_profile = blackboard.get_user_profile()
        provider_info = provider_profile.get("profile_info", {}) if isinstance(provider_profile, dict) else {}
        generated = blackboard.generate_money_dna_stats(
            {
                "month": context["month"],
                "total_spending": context["total_spending"],
                "month_spending": context["month_spending"],
                "spending_per_category": context["spending_per_category"],
                "comparisons": context["comparisons"],
                "recommendations": context["recommendations"],
                "income_profile": context["income_profile"],
                "budget_goal": context["budget_goal"],
                "target_savings": context["target_savings"],
                "remaining_budget": context["remaining_budget"],
                "expected_savings": context["expected_savings"],
            },
            requested_model=requested_model,
        )
        if generated.get("ai_narrative"):
            ai_narrative = generated["ai_narrative"]
        if generated.get("recommendations"):
            context["recommendations"] = generated["recommendations"]
        blackboard_comparisons = generated.get("comparisons") or []
        generated_by = f"blackboard:{generated.get('model') or 'unknown'}"
    except Exception as exc:
        raw_error = str(exc)
        if "inference endpoint" in raw_error.lower() or "chat endpoint" in raw_error.lower() or "404" in raw_error:
            provider_error = (
                f"{raw_error} | Set BACKBOARD_CHAT_COMPLETIONS_URL in .env to your valid endpoint, "
                "then restart backend."
            )
        else:
            provider_error = raw_error
        if context["expense_count"] > 0 and ai_narrative.startswith("Not enough data yet"):
            ai_narrative = (
                "Your Money DNA is generated from category trends, monthly recurring costs, and benchmark comparisons."
            )

    return (
        jsonify(
            {
                "month": context["month"],
                "total_spending": context["total_spending"],
                "month_spending": context["month_spending"],
                "spending_per_category": context["spending_per_category"],
                "comparisons": context["comparisons"],
                "blackboard_comparisons": blackboard_comparisons,
                "recommendations": context["recommendations"],
                "ai_narrative": ai_narrative,
                "generated_by": generated_by,
                "income_profile": context["income_profile"],
                "budget_goal": context["budget_goal"],
                "target_savings": context["target_savings"],
                "remaining_budget": context["remaining_budget"],
                "expected_savings": context["expected_savings"],
                "provider_info": provider_info,
                "provider_error": provider_error,
            }
        ),
        200,
    )


@app.route("/coach/messages", methods=["GET"])
def get_coach_messages():
    user, error = _require_user()
    if error:
        return error

    limit_raw = request.args.get("limit")
    try:
        limit = min(max(int(limit_raw), 1), 100) if limit_raw else 30
    except ValueError:
        return jsonify({"error": "Limit must be a number."}), 400

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, model, created_at
            FROM coach_messages
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user["id"], limit),
        ).fetchall()

    messages = [
        {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
            "model": row["model"] or "",
            "created_at": row["created_at"],
        }
        for row in reversed(rows)
    ]
    return jsonify({"messages": messages}), 200


@app.route("/coach/messages", methods=["POST"])
def post_coach_message():
    user, error = _require_user()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    requested_model = str(payload.get("model") or "").strip() or None

    if not message:
        return jsonify({"error": "Message is required."}), 400

    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO coach_messages (user_id, role, content, model, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user["id"], "user", message, requested_model or "", now),
        )
        history_rows = conn.execute(
            """
            SELECT role, content
            FROM coach_messages
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 12
            """,
            (user["id"],),
        ).fetchall()

    history = [
        {"role": row["role"], "content": row["content"]}
        for row in reversed(history_rows)
    ]
    context = _build_money_context(user["id"])

    provider_error = ""
    model_used = ""
    reply = ""
    try:
        blackboard = _get_blackboard_service()
        generated = blackboard.generate_financial_coach_reply(
            conversation=history,
            context_payload={
                "month": context["month"],
                "month_spending": context["month_spending"],
                "spending_per_category": context["spending_per_category"],
                "recommendations": context["recommendations"],
                "comparisons": context["comparisons"],
            },
            requested_model=requested_model,
        )
        reply = generated.get("reply") or ""
        model_used = generated.get("model") or ""
    except Exception as exc:
        provider_error = str(exc)
        return jsonify({"error": f"Blackboard coach failed: {provider_error}"}), 502

    if not reply.strip():
        return jsonify({"error": "Blackboard coach returned empty output."}), 502

    assistant_time = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO coach_messages (user_id, role, content, model, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user["id"], "assistant", reply, model_used, assistant_time),
        )
        conn.commit()
        message_id = cursor.lastrowid

    return (
        jsonify(
            {
                "message": {
                    "id": message_id,
                    "role": "assistant",
                    "content": reply,
                    "model": model_used,
                    "created_at": assistant_time,
                },
                "provider_error": provider_error,
            }
        ),
        201,
    )


@app.route("/ai/experiments", methods=["POST"])
def run_ai_experiment():
    user, error = _require_user()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    prompt = str(payload.get("prompt", "")).strip()
    model_a = str(payload.get("model_a") or "").strip() or None
    model_b = str(payload.get("model_b") or "").strip() or None

    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400
    if model_a is None or model_b is None:
        return jsonify({"error": "Both model_a and model_b are required."}), 400

    context = _build_money_context(user["id"])
    full_prompt = (
        "Using this money context, respond to the request with concise, actionable financial guidance.\n"
        f"Context: {context}\n"
        f"Request: {prompt}"
    )

    outputs = []
    errors = []
    try:
        blackboard = _get_blackboard_service()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    for model in (model_a, model_b):
        try:
            result = blackboard.run_prompt(full_prompt, requested_model=model)
            text = result.get("output") or ""
            outputs.append(
                {
                    "model": result.get("model") or model,
                    "output": text,
                    "length": len(text),
                }
            )
        except Exception as exc:
            errors.append({"model": model, "error": str(exc)})

    winner = None
    if len(outputs) == 2:
        winner = outputs[0]["model"] if outputs[0]["length"] >= outputs[1]["length"] else outputs[1]["model"]

    return jsonify({"outputs": outputs, "errors": errors, "winner": winner}), 200


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


@app.route("/dataset_analytics", methods=["GET"])
def dataset_analytics():
    user, error = _require_user()
    if error:
        return error

    try:
        return jsonify(_compute_dataset_analytics()), 200
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"Failed to process dataset analytics: {str(exc)}"}), 500




if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
