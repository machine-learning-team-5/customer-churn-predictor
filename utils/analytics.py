from datetime import datetime, timedelta
from utils.db import users_collection, predictions_collection


# =====================================================
# HELPER FUNCTION (SAFE DATE CONVERSION)
# =====================================================

def safe_parse_date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except:
            return None
    return None


# =====================================================
# ADMIN DASHBOARD MAIN ANALYTICS
# =====================================================

def get_admin_analytics():

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    registered_users = users_collection.distinct("email")
    prediction_users = predictions_collection.distinct("user")

    combined_users = set(registered_users) | set(prediction_users)
    total_users = len(combined_users)

    total_predictions = predictions_collection.count_documents({})

    last_30_days_users = predictions_collection.distinct(
        "user",
        {"created_at": {"$gte": thirty_days_ago}}
    )

    last_30_days_users_count = len(last_30_days_users)

    all_predictions = list(predictions_collection.find({}))

    # -------------------------
    # OVERALL PROBABILITY
    # -------------------------

    if all_predictions:
        overall = (
            sum(p.get("probability", 0) for p in all_predictions)
            / len(all_predictions)
        )
    else:
        overall = 0

    # -------------------------
    # RISK DISTRIBUTION (LATEST PER USER)
    # -------------------------

    latest_predictions = {}

    for p in all_predictions:
        user = p.get("user")
        created = safe_parse_date(p.get("created_at"))

        if not user or not created:
            continue

        if user not in latest_predictions:
            latest_predictions[user] = p
        else:
            prev_created = safe_parse_date(
                latest_predictions[user].get("created_at")
            )
            if prev_created and created > prev_created:
                latest_predictions[user] = p

    risk_distribution = {"Low": 0, "Medium": 0, "High": 0}

    for p in latest_predictions.values():
        risk = p.get("risk", "Low")
        if risk in risk_distribution:
            risk_distribution[risk] += 1

    # -------------------------
    # MONTHLY RANKING
    # -------------------------

    monthly_data = {}

    for p in all_predictions:

        created = safe_parse_date(p.get("created_at"))
        if not created:
            continue

        month_key = created.strftime("%Y-%m")

        monthly_data.setdefault(month_key, [])
        monthly_data[month_key].append(p.get("probability", 0))

    monthly_ranking = []

    for month, values in monthly_data.items():
        avg = sum(values) / len(values)
        monthly_ranking.append({
            "month": month,
            "avg": round(avg * 100, 2)
        })

    monthly_ranking.sort(key=lambda x: x["avg"], reverse=True)

    for i, item in enumerate(monthly_ranking):
        item["rank"] = i + 1

    # -------------------------
    # HISTORY
    # -------------------------

    history_records = list(
        predictions_collection
        .find({})
        .sort("created_at", -1)
        .limit(50)
    )

    formatted_history = []

    for r in history_records:
        created = safe_parse_date(r.get("created_at"))

        formatted_history.append({
            "user": r.get("user", "N/A"),
            "probability": r.get("probability", 0),
            "risk": r.get("risk", "Unknown"),
            "suggestion": r.get("suggestion", "N/A"),
            "created_at": created.isoformat() if created else ""
        })

    # -------------------------
    # REVENUE CALCULATION
    # -------------------------

    subscription_prices = {
        "basic": 299,
        "standard": 599,
        "premium": 999
    }

    total_revenue = 0
    revenue_loss = 0

    for p in all_predictions:
        inputs = p.get("inputs", {})
        sub = inputs.get("subscription_type", "standard").lower()
        price = subscription_prices.get(sub, 599)

        total_revenue += price

        if p.get("risk") == "High":
            revenue_loss += price

    revenue_data = {
        "total_revenue": total_revenue,
        "revenue_loss": revenue_loss
    }

    return {
        "total_users": total_users,
        "total_predictions": total_predictions,
        "last_30_days_users_count": last_30_days_users_count,
        "overall": overall,
        "history": formatted_history,
        "risk_distribution": risk_distribution,
        "monthly_ranking": monthly_ranking,
        "revenue": revenue_data
    }


# =====================================================
# DATE RANGE ANALYTICS (FIXED & SAFE)
# =====================================================

def get_date_range_analytics(start_date, end_date):

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        end = end + timedelta(days=1)  # include full end date
    except:
        return {
            "total_predictions": 0,
            "average_probability": "0%",
            "high_risk_rate": 0,
            "monthly_ranking": [],
            "risk_distribution": {"Low": 0, "Medium": 0, "High": 0}
        }

    all_predictions = list(predictions_collection.find({}))

    # Filter manually (safe for mixed date types)
    filtered = []

    for p in all_predictions:
        created = safe_parse_date(p.get("created_at"))
        if not created:
            continue

        if start <= created < end:
            filtered.append(p)

    total_predictions = len(filtered)

    if total_predictions == 0:
        return {
            "total_predictions": 0,
            "average_probability": "0%",
            "high_risk_rate": 0,
            "monthly_ranking": [],
            "risk_distribution": {"Low": 0, "Medium": 0, "High": 0}
        }

    avg_probability = (
        sum(p.get("probability", 0) for p in filtered)
        / total_predictions
    )

    avg_probability_percent = round(avg_probability * 100, 2)

    high_risk_count = sum(
        1 for p in filtered
        if p.get("risk", "").lower() == "high"
    )

    high_risk_rate = round(
        (high_risk_count / total_predictions) * 100
    )

    # Monthly ranking inside date range
    monthly_data = {}

    for p in filtered:
        created = safe_parse_date(p.get("created_at"))
        month_key = created.strftime("%Y-%m")

        monthly_data.setdefault(month_key, [])
        monthly_data[month_key].append(p.get("probability", 0))

    monthly_ranking = []

    for month, values in monthly_data.items():
        avg = sum(values) / len(values)
        monthly_ranking.append({
            "month": month,
            "avg": round(avg * 100, 2)
        })

    monthly_ranking.sort(key=lambda x: x["avg"], reverse=True)

    risk_distribution = {"Low": 0, "Medium": 0, "High": 0}

    for p in filtered:
        risk = p.get("risk", "Low")
        if risk in risk_distribution:
            risk_distribution[risk] += 1

    return {
        "total_predictions": total_predictions,
        "average_probability": f"{avg_probability_percent}%",
        "high_risk_rate": high_risk_rate,
        "monthly_ranking": monthly_ranking,
        "risk_distribution": risk_distribution
    }