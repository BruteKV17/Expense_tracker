from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from sqlalchemy import extract, func
import csv
import io

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key-change-this"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expense_tracker.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    monthly_budget = db.Column(db.Float, default=0.0)
    theme = db.Column(db.String(20), default="dark")

    expenses = db.relationship("Expense", backref="user", lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    expense_date = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.String(255))
    payment_method = db.Column(db.String(80), default="UPI")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


CATEGORIES = {
    "Food": "bi-basket2-fill",
    "Transport": "bi-car-front-fill",
    "Shopping": "bi-bag-fill",
    "Bills": "bi-receipt-cutoff",
    "Entertainment": "bi-film",
    "Health": "bi-heart-pulse-fill",
    "Education": "bi-book-fill",
    "Travel": "bi-airplane-fill",
    "Rent": "bi-house-door-fill",
    "Other": "bi-three-dots-circle-fill"
}


def create_notification(user_id, message):
    notification = Notification(user_id=user_id, message=message)
    db.session.add(notification)
    db.session.commit()


def get_dashboard_data(user):
    today = date.today()
    current_month = today.month
    current_year = today.year

    all_expenses = Expense.query.filter_by(user_id=user.id).order_by(Expense.expense_date.desc()).all()
    month_expenses = Expense.query.filter(
        Expense.user_id == user.id,
        extract("month", Expense.expense_date) == current_month,
        extract("year", Expense.expense_date) == current_year
    ).all()

    total_expense = sum(exp.amount for exp in all_expenses)
    monthly_expense = sum(exp.amount for exp in month_expenses)
    total_transactions = len(all_expenses)
    average_expense = round(total_expense / total_transactions, 2) if total_transactions else 0
    remaining_budget = round((user.monthly_budget or 0) - monthly_expense, 2)

    category_totals = db.session.query(
        Expense.category,
        func.sum(Expense.amount)
    ).filter(
        Expense.user_id == user.id
    ).group_by(Expense.category).all()

    highest_category = max(category_totals, key=lambda x: x[1])[0] if category_totals else "N/A"

    recent_expenses = Expense.query.filter_by(user_id=user.id).order_by(Expense.created_at.desc()).limit(5).all()
    unread_notifications = Notification.query.filter_by(user_id=user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
    notification_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()

    return {
        "total_expense": round(total_expense, 2),
        "monthly_expense": round(monthly_expense, 2),
        "remaining_budget": remaining_budget,
        "highest_category": highest_category,
        "total_transactions": total_transactions,
        "average_expense": average_expense,
        "recent_expenses": recent_expenses,
        "unread_notifications": unread_notifications,
        "notification_count": notification_count,
        "category_totals": category_totals
    }


def build_chart_data(user):
    current_year = date.today().year

    category_data = db.session.query(
        Expense.category,
        func.sum(Expense.amount)
    ).filter(
        Expense.user_id == user.id
    ).group_by(Expense.category).all()

    monthly_data = db.session.query(
        extract("month", Expense.expense_date).label("month"),
        func.sum(Expense.amount)
    ).filter(
        Expense.user_id == user.id,
        extract("year", Expense.expense_date) == current_year
    ).group_by("month").order_by("month").all()

    weekly_data = db.session.query(
        func.strftime("%W", Expense.expense_date),
        func.sum(Expense.amount)
    ).filter(
        Expense.user_id == user.id
    ).group_by(func.strftime("%W", Expense.expense_date)).order_by(func.strftime("%W", Expense.expense_date)).limit(8).all()

    trend_data = Expense.query.filter_by(user_id=user.id).order_by(Expense.expense_date.asc()).all()

    current_month = date.today().month
    monthly_expense = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == user.id,
        extract("month", Expense.expense_date) == current_month,
        extract("year", Expense.expense_date) == current_year
    ).scalar() or 0

    budget = user.monthly_budget or 0
    budget_used = round((monthly_expense / budget) * 100, 2) if budget > 0 else 0
    budget_left = max(0, 100 - budget_used) if budget > 0 else 0

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_map = {int(month): float(amount) for month, amount in monthly_data}

    return {
        "pie_labels": [row[0] for row in category_data],
        "pie_values": [float(row[1]) for row in category_data],
        "bar_labels": month_names,
        "bar_values": [monthly_map.get(i, 0) for i in range(1, 13)],
        "line_labels": [exp.expense_date.strftime("%d %b") for exp in trend_data],
        "line_values": [exp.amount for exp in trend_data],
        "weekly_labels": [f"Week {row[0]}" for row in weekly_data],
        "weekly_values": [float(row[1]) for row in weekly_data],
        "budget_labels": ["Used", "Left"],
        "budget_values": [min(budget_used, 100), budget_left]
    }


def generate_ai_insights(user):
    current_month = date.today().month
    current_year = date.today().year

    expenses = Expense.query.filter_by(user_id=user.id).all()
    monthly_expenses = Expense.query.filter(
        Expense.user_id == user.id,
        extract("month", Expense.expense_date) == current_month,
        extract("year", Expense.expense_date) == current_year
    ).all()

    if not expenses:
        return [
            "No expense history yet. Start by adding your first transaction to unlock insights.",
            "Set a monthly budget to track spending progress in real time.",
            "Use categories consistently to get sharper analytics and cleaner charts."
        ]

    total = sum(e.amount for e in expenses)
    monthly_total = sum(e.amount for e in monthly_expenses)

    category_totals = {}
    for e in expenses:
        category_totals[e.category] = category_totals.get(e.category, 0) + e.amount

    top_category = max(category_totals, key=category_totals.get) if category_totals else "Other"
    top_category_amount = category_totals.get(top_category, 0)

    insights = [
        f"Your top spending category is {top_category}, accounting for ₹{top_category_amount:.2f} overall.",
        f"This month you have spent ₹{monthly_total:.2f}. Track weekly changes to avoid month-end spikes.",
        "Small repeated expenses often create the biggest hidden drain. Review food, shopping, and transport entries first."
    ]

    if user.monthly_budget > 0:
        usage = (monthly_total / user.monthly_budget) * 100
        if usage > 100:
            insights.append("You have exceeded your monthly budget. Consider reducing non-essential spending categories.")
        elif usage > 80:
            insights.append("You have crossed 80% of your monthly budget. Keep upcoming expenses controlled.")
        else:
            insights.append("Your spending is within budget. Maintain this pace to finish the month safely.")

    return insights[:4]


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password or not confirm_password:
            flash("Please fill all fields.", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash("User already exists with this email or username.", "warning")
            return redirect(url_for("register"))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        create_notification(user.id, "Welcome aboard. Your finance dashboard is ready.")
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = True if request.form.get("remember") else False

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash("Login successful. Welcome back.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    data = get_dashboard_data(current_user)
    chart_data = build_chart_data(current_user)
    insights = generate_ai_insights(current_user)

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str)
    category = request.args.get("category", "", type=str)
    sort = request.args.get("sort", "latest", type=str)
    filter_date = request.args.get("date", "", type=str)

    query = Expense.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(Expense.notes.ilike(f"%{search}%"))

    if category:
        query = query.filter_by(category=category)

    if filter_date:
        try:
            parsed_date = datetime.strptime(filter_date, "%Y-%m-%d").date()
            query = query.filter_by(expense_date=parsed_date)
        except ValueError:
            pass

    if sort == "amount_asc":
        query = query.order_by(Expense.amount.asc())
    elif sort == "amount_desc":
        query = query.order_by(Expense.amount.desc())
    elif sort == "oldest":
        query = query.order_by(Expense.expense_date.asc())
    else:
        query = query.order_by(Expense.expense_date.desc())

    expenses = query.paginate(page=page, per_page=6)

    return render_template(
        "dashboard.html",
        data=data,
        chart_data=chart_data,
        insights=insights,
        expenses=expenses,
        categories=CATEGORIES
    )


@app.route("/add-expense", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        amount = request.form.get("amount", type=float)
        category = request.form.get("category")
        expense_date = request.form.get("expense_date")
        notes = request.form.get("notes", "").strip()
        payment_method = request.form.get("payment_method", "UPI")

        if not amount or amount <= 0:
            flash("Please enter a valid amount.", "danger")
            return redirect(url_for("add_expense"))

        if category not in CATEGORIES:
            flash("Please select a valid category.", "danger")
            return redirect(url_for("add_expense"))

        try:
            expense_date = datetime.strptime(expense_date, "%Y-%m-%d").date()
        except Exception:
            flash("Please select a valid date.", "danger")
            return redirect(url_for("add_expense"))

        expense = Expense(
            amount=amount,
            category=category,
            expense_date=expense_date,
            notes=notes,
            payment_method=payment_method,
            user_id=current_user.id
        )

        db.session.add(expense)
        db.session.commit()

        current_month = date.today().month
        current_year = date.today().year
        monthly_spend = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            extract("month", Expense.expense_date) == current_month,
            extract("year", Expense.expense_date) == current_year
        ).scalar() or 0

        if current_user.monthly_budget and monthly_spend > current_user.monthly_budget:
            create_notification(current_user.id, "Warning: You have exceeded your monthly budget.")
            flash("Expense added, but your monthly budget has been exceeded.", "warning")
        else:
            create_notification(current_user.id, f"New expense added: ₹{amount:.2f} for {category}.")
            flash("Expense added successfully.", "success")

        return redirect(url_for("dashboard"))

    return render_template("add_expense.html", categories=CATEGORIES)


@app.route("/edit-expense/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        amount = request.form.get("amount", type=float)
        category = request.form.get("category")
        expense_date = request.form.get("expense_date")
        notes = request.form.get("notes", "").strip()
        payment_method = request.form.get("payment_method", "UPI")

        if not amount or amount <= 0:
            flash("Please enter a valid amount.", "danger")
            return redirect(url_for("edit_expense", expense_id=expense.id))

        expense.amount = amount
        expense.category = category
        expense.expense_date = datetime.strptime(expense_date, "%Y-%m-%d").date()
        expense.notes = notes
        expense.payment_method = payment_method

        db.session.commit()
        flash("Expense updated successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_expense.html", categories=CATEGORIES, expense=expense, edit_mode=True)


@app.route("/delete-expense/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted successfully.", "info")
    return redirect(url_for("dashboard"))


@app.route("/analytics")
@login_required
def analytics():
    chart_data = build_chart_data(current_user)
    data = get_dashboard_data(current_user)
    insights = generate_ai_insights(current_user)
    return render_template("analytics.html", chart_data=chart_data, data=data, insights=insights)


@app.route("/budget", methods=["POST"])
@login_required
def budget():
    budget = request.form.get("monthly_budget", type=float)
    current_user.monthly_budget = budget if budget and budget >= 0 else 0
    db.session.commit()
    flash("Monthly budget updated successfully.", "success")
    return redirect(url_for("settings"))


@app.route("/profile")
@login_required
def profile():
    data = get_dashboard_data(current_user)
    return render_template("profile.html", data=data)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        theme = request.form.get("theme", "dark")
        current_user.theme = theme
        db.session.commit()
        flash("Settings updated successfully.", "success")
        return redirect(url_for("settings"))

    notification_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template("settings.html", notification_count=notification_count)


@app.route("/reports")
@login_required
def reports():
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.expense_date.desc()).all()
    data = get_dashboard_data(current_user)
    return render_template("reports.html", expenses=expenses, data=data, now=datetime.utcnow())


@app.route("/export/csv")
@login_required
def export_csv():
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.expense_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Amount", "Category", "Date", "Payment Method", "Notes", "Created At"])

    for exp in expenses:
        writer.writerow([
            exp.id,
            exp.amount,
            exp.category,
            exp.expense_date,
            exp.payment_method,
            exp.notes,
            exp.created_at.strftime("%Y-%m-%d %H:%M")
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=expense_report.csv"
    response.headers["Content-type"] = "text/csv"
    return response


@app.context_processor
def inject_globals():
    if current_user.is_authenticated:
        return {
            "global_notifications": Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).order_by(Notification.created_at.desc()).limit(5).all(),
            "global_notification_count": Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count(),
            "category_icons": CATEGORIES
        }
    return {
        "global_notifications": [],
        "global_notification_count": 0,
        "category_icons": CATEGORIES
    }


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)