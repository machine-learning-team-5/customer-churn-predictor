from flask import Flask, render_template, request, jsonify
from datetime import datetime
from utils.db import users_collection, predictions_collection
from utils.auth import register_user, login_user
from utils.analytics import get_admin_analytics, get_date_range_analytics
import pandas as pd

app = Flask(__name__)

# =====================================================
# SIMULATED ML MODEL
# =====================================================

def calculate_churn_probability(
    tenure,
    watch_hours,
    days_since_login,
    subscription_type,
    tickets_raised,
    profiles_used
):
    tenure_norm = min(tenure / 36.0, 1.0)
    watch_norm = min(watch_hours / 40.0, 1.0)
    days_norm = min(days_since_login / 30.0, 1.0)
    tickets_norm = min(tickets_raised / 5.0, 1.0)
    profiles_norm = min(profiles_used / 5.0, 1.0)

    sub_bonus = {
        "basic": 0.0,
        "standard": 0.05,
        "premium": 0.10
    }

    loyalty_bonus = sub_bonus.get(subscription_type.lower(), 0.05)

    churn_score = (
        0.30 * (1 - tenure_norm) +
        0.35 * (1 - watch_norm) +
        0.20 * days_norm +
        0.10 * tickets_norm -
        0.15 * profiles_norm -
        loyalty_bonus
    )

    probability = max(0.03, min(0.95, churn_score))
    return round(probability, 3)


# =====================================================
# PAGE ROUTES
# =====================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/user")
def user():
    return render_template("user.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


# =====================================================
# AUTH ROUTES
# =====================================================

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    result = register_user(data)

    if not result["success"]:
        return jsonify(result), 400

    return jsonify(result)


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    result = login_user(data)

    if not result["success"]:
        return jsonify(result), 401

    return jsonify(result)


# =====================================================
# SINGLE PREDICTION
# =====================================================

@app.route("/predict", methods=["POST"])
def predict():

    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email required"}), 400

    inputs = data.get("inputs", {})

    probability = calculate_churn_probability(
        float(inputs.get("tenure", 12)),
        float(inputs.get("watch_hours", 10)),
        float(inputs.get("days_since_login", 5)),
        inputs.get("subscription_type", "standard"),
        float(inputs.get("tickets_raised", 1)),
        float(inputs.get("profiles_used", 2))
    )

    risk = "High" if probability > 0.7 else \
           "Medium" if probability > 0.4 else \
           "Low"

    suggestion = (
        "Offer Premium trial" if risk == "High"
        else "Send recommendation" if risk == "Medium"
        else "No action required"
    )

    record = {
        "user": email,
        "probability": probability,
        "risk": risk,
        "suggestion": suggestion,
        "source": "single",
        "inputs": inputs,
        "created_at": datetime.utcnow()
    }

    predictions_collection.insert_one(record)

    return jsonify({
        "probability": probability,
        "risk": risk,
        "suggestion": suggestion
    })


# =====================================================
# BULK PREDICTION
# =====================================================

@app.route("/bulk-predict", methods=["POST"])
def bulk_predict():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    try:
        df = pd.read_csv(file)

        results = []
        docs_to_insert = []
        total_probability = 0

        for index, row in df.iterrows():

            probability = calculate_churn_probability(
                float(row.get("tenure", 12)),
                float(row.get("watch_hours", 10)),
                float(row.get("days_since_login", 5)),
                row.get("subscription_type", "standard"),
                float(row.get("tickets_raised", 1)),
                float(row.get("profiles_used", 2))
            )

            risk = "High" if probability > 0.7 else \
                   "Medium" if probability > 0.4 else \
                   "Low"

            user_email = row.get("email", f"User_{index+1}")

            created_at_value = row.get("created_at")

            if pd.notna(created_at_value):
                try:
                    created_at = datetime.fromisoformat(str(created_at_value))
                except:
                    created_at = datetime.utcnow()
            else:
                created_at = datetime.utcnow()

            results.append({
                "user": user_email,
                "probability": probability,
                "risk": risk
            })

            docs_to_insert.append({
                "user": user_email,
                "probability": probability,
                "risk": risk,
                "suggestion": "Bulk Upload",
                "source": "bulk",
                "created_at": created_at,
                "inputs": {
                    "subscription_type": row.get("subscription_type", "standard")
                }
            })

            total_probability += probability

        if docs_to_insert:
            predictions_collection.insert_many(docs_to_insert)

        overall_probability = round(total_probability / len(results), 3)

        return jsonify({
            "results": results,
            "overall_probability": overall_probability
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# =====================================================
# ADMIN ANALYTICS ROUTES
# =====================================================

@app.route("/admin-data")
def admin_data():
    return jsonify(get_admin_analytics())


@app.route("/admin/date-range", methods=["POST"])
def admin_date_range():

    data = request.get_json()

    if not data:
        return jsonify({
            "total_predictions": 0,
            "average_probability": "0%",
            "high_risk_rate": 0,
            "monthly_ranking": []
        })

    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not start_date or not end_date:
        return jsonify({
            "total_predictions": 0,
            "average_probability": "0%",
            "high_risk_rate": 0,
            "monthly_ranking": []
        })

    return jsonify(
        get_date_range_analytics(start_date, end_date)
    )

# =====================================================
# NEXT MONTH PREDICTION
# =====================================================

@app.route("/predict-next-month")
def predict_next_month():

    predictions = list(predictions_collection.find())

    if not predictions:
        return jsonify({
            "total_users": 0,
            "expected_churn": 0,
            "churn_rate": 0,
            "expected_revenue_loss": 0,
            "expected_revenue": 0
        })

    total_users = len(predictions)

    subscription_prices = {
        "basic": 299,
        "standard": 599,
        "premium": 999
    }

    expected_churn = 0
    expected_revenue_loss = 0
    total_revenue = 0

    for p in predictions:

        probability = p.get("probability", 0)

        sub_type = (
            p.get("inputs", {})
             .get("subscription_type", "standard")
             .lower()
        )

        price = subscription_prices.get(sub_type, 599)

        total_revenue += price

        expected_churn += probability
        expected_revenue_loss += probability * price

    expected_churn = round(expected_churn)
    expected_revenue_loss = round(expected_revenue_loss)

    expected_revenue = total_revenue - expected_revenue_loss

    churn_rate = round((expected_churn / total_users) * 100, 2)

    return jsonify({
        "total_users": total_users,
        "expected_churn": expected_churn,
        "churn_rate": churn_rate,
        "expected_revenue_loss": expected_revenue_loss,
        "expected_revenue": expected_revenue
    })

# =====================================================
# RUN APP
# =====================================================

app = app