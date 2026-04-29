import os
from datetime import datetime
from flask import Flask, request, redirect, url_for, session, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///local.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "secret")

db = SQLAlchemy(app)

# ---------------- MODELS ----------------

class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    address = db.Column(db.String(255))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20))
    branch_id = db.Column(db.Integer, db.ForeignKey("branch.id"))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer)
    name = db.Column(db.String(150))
    category = db.Column(db.String(80))
    subcategory = db.Column(db.String(80))
    retail_price = db.Column(db.Float)
    wholesale_price = db.Column(db.Float)
    quantity = db.Column(db.Integer)
    low_stock = db.Column(db.Integer, default=5)


class LensPower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer)
    sph = db.Column(db.String(20))
    cyl = db.Column(db.String(20))
    axis = db.Column(db.String(20))
    add_power = db.Column(db.String(20))
    quantity = db.Column(db.Integer)
    low_stock = db.Column(db.Integer, default=2)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120))
    total = db.Column(db.Float)
    amount_paid = db.Column(db.Float)
    balance = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------- AUTO SETUP ----------------

@app.before_request
def setup():
    db.create_all()

    if not Branch.query.first():
        db.session.add(Branch(name="Main Branch"))
        db.session.commit()

    if not User.query.filter_by(username="manager").first():
        db.session.add(User(
            username="manager",
            password_hash=generate_password_hash("manager123"),
            role="manager",
            branch_id=1
        ))
        db.session.commit()


# ---------------- UI TEMPLATE ----------------

def page(title, body):
    return render_template_string(f"""
    <html>
    <head>
    <style>
    body {{font-family: Arial; background:#f4f7fb}}
    .nav {{background:#063970;color:white;padding:15px}}
    .box {{background:white;padding:20px;margin:20px;border-radius:10px}}
    .btn {{background:#0b8f83;color:white;padding:10px;border:none}}
    .low {{color:red;font-weight:bold}}
    </style>
    </head>

    <body>
    <div class="nav">
    <h2>Halleluyah Optical POS</h2>
    </div>

    <div class="box">
    {body}
    </div>
    </body>
    </html>
    """)


# ---------------- ROUTES ----------------

@app.route("/", methods=["GET"])
def home():
    if "user" not in session:
        return redirect("/login")

    low_products = Product.query.filter(Product.quantity <= Product.low_stock).count()
    low_lens = LensPower.query.filter(LensPower.quantity <= LensPower.low_stock).count()

    alert = ""
    if low_products or low_lens:
        alert = f"<p class='low'>⚠ Low Stock: {low_products} products, {low_lens} lens powers</p>"

    return page("Dashboard", f"""
    <h2>Dashboard</h2>
    {alert}

    <a href='/add-product'>Add Product</a><br><br>
    <a href='/add-lens'>Add Lens Power</a><br><br>
    <a href='/lens'>View Lens Power</a><br><br>
    """)


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["u"]).first()
        if user and check_password_hash(user.password_hash, request.form["p"]):
            session["user"] = user.username
            return redirect("/")

    return page("Login", """
    <form method='post'>
    Username <input name='u'><br><br>
    Password <input type='password' name='p'><br><br>
    <button class='btn'>Login</button>
    </form>
    """)


@app.route("/add-product", methods=["GET","POST"])
def add_product():
    if request.method == "POST":
        db.session.add(Product(
            name=request.form["name"],
            category=request.form["cat"],
            subcategory=request.form["sub"],
            retail_price=float(request.form["rp"]),
            wholesale_price=float(request.form["wp"]),
            quantity=int(request.form["qty"]),
            low_stock=int(request.form["low"])
        ))
        db.session.commit()
        return redirect("/")

    return page("Add Product", """
    <form method='post'>
    Name <input name='name'><br><br>
    Category <input name='cat'><br><br>
    Subcategory <input name='sub'><br><br>
    Retail Price <input name='rp'><br><br>
    Wholesale Price <input name='wp'><br><br>
    Quantity <input name='qty'><br><br>
    Low Stock Level <input name='low'><br><br>
    <button class='btn'>Save</button>
    </form>
    """)


@app.route("/add-lens", methods=["GET","POST"])
def add_lens():
    products = Product.query.all()

    if request.method == "POST":
        db.session.add(LensPower(
            product_id=int(request.form["p"]),
            sph=request.form["sph"],
            cyl=request.form["cyl"],
            axis=request.form["axis"],
            add_power=request.form["add"],
            quantity=int(request.form["qty"]),
            low_stock=int(request.form["low"])
        ))
        db.session.commit()
        return redirect("/lens")

    options = "".join([f"<option value='{p.id}'>{p.name}</option>" for p in products])

    return page("Add Lens", f"""
    <form method='post'>
    Product <select name='p'>{options}</select><br><br>
    SPH <input name='sph'><br><br>
    CYL <input name='cyl'><br><br>
    AXIS <input name='axis'><br><br>
    ADD <input name='add'><br><br>
    Quantity <input name='qty'><br><br>
    Low Stock Level <input name='low'><br><br>
    <button class='btn'>Save</button>
    </form>
    """)


@app.route("/lens")
def lens():
    lens = LensPower.query.all()

    rows = ""
    for l in lens:
        status = "LOW" if l.quantity <= l.low_stock else "OK"
        color = "red" if status == "LOW" else "green"

        rows += f"""
        <tr>
        <td>{l.sph}</td>
        <td>{l.cyl}</td>
        <td>{l.axis}</td>
        <td>{l.add_power}</td>
        <td>{l.quantity}</td>
        <td style='color:{color}'>{status}</td>
        </tr>
        """

    return page("Lens", f"""
    <table border=1>
    <tr><th>SPH</th><th>CYL</th><th>AXIS</th><th>ADD</th><th>Qty</th><th>Status</th></tr>
    {rows}
    </table>
    """)


if __name__ == "__main__":
    app.run(debug=True)
