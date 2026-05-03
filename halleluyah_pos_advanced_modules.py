import os
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from flask import Flask, request, redirect, url_for, session, render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# IMPORTANT: On Render, keep the PostgreSQL DATABASE_URL attached.
# If DATABASE_URL is missing, Render will use temporary local SQLite and data can disappear after redeploy.
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///local.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "halleluyah-secret-key")

db = SQLAlchemy(app)


class Branch(db.Model):
    __tablename__ = "hol_branch"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.String(255))


class User(db.Model):
    __tablename__ = "hol_user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="staff")
    branch_id = db.Column(db.Integer, db.ForeignKey("hol_branch.id"))


class Product(db.Model):
    __tablename__ = "hol_product"
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("hol_branch.id"))
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    subcategory = db.Column(db.String(80))
    retail_price = db.Column(db.Float, default=0)
    wholesale_price = db.Column(db.Float, default=0)
    quantity = db.Column(db.Integer, default=0)


class LensPower(db.Model):
    __tablename__ = "hol_lens_power"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("hol_product.id"))
    branch_id = db.Column(db.Integer, db.ForeignKey("hol_branch.id"))
    sph = db.Column(db.String(20))
    cyl = db.Column(db.String(20))
    axis = db.Column(db.String(20))
    add_power = db.Column(db.String(20))
    quantity = db.Column(db.Integer, default=0)


class Sale(db.Model):
    __tablename__ = "hol_sale"
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("hol_branch.id"))
    customer_name = db.Column(db.String(120))
    customer_phone = db.Column(db.String(50))
    total = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    amount_paid = db.Column(db.Float, default=0)
    balance = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SaleItem(db.Model):
    __tablename__ = "hol_sale_item"
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("hol_sale.id"))
    product_name = db.Column(db.String(150))
    lens_power = db.Column(db.String(120))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0)
    subtotal = db.Column(db.Float, default=0)


class OfficeSetting(db.Model):
    __tablename__ = "hol_office_setting"
    id = db.Column(db.Integer, primary_key=True)
    office_name = db.Column(db.String(180), default="Halleluyah Optical Laboratory")
    phone = db.Column(db.String(80), default="")
    address = db.Column(db.String(255), default="Sobi Junction, Gambari, Ilorin, Kwara State")


class GoodsRequest(db.Model):
    __tablename__ = "hol_goods_request"
    id = db.Column(db.Integer, primary_key=True)
    requester_branch_id = db.Column(db.Integer, db.ForeignKey("hol_branch.id"))
    supplier_branch_id = db.Column(db.Integer, db.ForeignKey("hol_branch.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("hol_product.id"))
    requested_by = db.Column(db.Integer, db.ForeignKey("hol_user.id"))
    item_name = db.Column(db.String(180))
    quantity = db.Column(db.Integer, default=1)
    note = db.Column(db.String(255))
    status = db.Column(db.String(30), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)


class PatientPrescription(db.Model):
    __tablename__ = "hol_patient_prescription"
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("hol_branch.id"))
    patient_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    age = db.Column(db.String(20))
    gender = db.Column(db.String(20))
    address = db.Column(db.String(255))
    od_sph = db.Column(db.String(20))
    od_cyl = db.Column(db.String(20))
    od_axis = db.Column(db.String(20))
    od_add = db.Column(db.String(20))
    os_sph = db.Column(db.String(20))
    os_cyl = db.Column(db.String(20))
    os_axis = db.Column(db.String(20))
    os_add = db.Column(db.String(20))
    pd = db.Column(db.String(30))
    seg_height = db.Column(db.String(30))
    frame_measurement = db.Column(db.String(120))
    lens_recommendation = db.Column(db.String(180))
    doctor_name = db.Column(db.String(120))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NotificationLog(db.Model):
    __tablename__ = "hol_notification_log"
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("hol_branch.id"))
    customer_name = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    message = db.Column(db.Text)
    channel = db.Column(db.String(30), default="WhatsApp")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def logged_in():
    return "user_id" in session


def is_manager():
    return session.get("role") == "manager"


def money(value):
    try:
        return "{:,.2f}".format(float(value or 0))
    except Exception:
        return "0.00"


def fmt_power(value):
    d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if d > 0:
        return f"+{d:.2f}"
    return f"{d:.2f}"


def decimal_range(start, stop, step):
    start_d = Decimal(str(start)).quantize(Decimal("0.01"))
    stop_d = Decimal(str(stop)).quantize(Decimal("0.01"))
    step_d = abs(Decimal(str(step or "0.25"))).quantize(Decimal("0.01"))
    if step_d == 0:
        step_d = Decimal("0.25")
    vals = []
    if start_d <= stop_d:
        current = start_d
        while current <= stop_d:
            vals.append(current)
            current += step_d
    else:
        current = start_d
        while current >= stop_d:
            vals.append(current)
            current -= step_d
    return vals


STYLE = """
<style>
body{margin:0;font-family:Arial,Helvetica,sans-serif;background:#f4f7fb;color:#0f172a}
.header{background:linear-gradient(90deg,#003366,#0077b6);color:white;padding:24px}
.container{padding:24px}.card{background:white;border-radius:14px;padding:20px;margin-bottom:20px;box-shadow:0 4px 15px #0001}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:15px}.stat{background:linear-gradient(135deg,#fff,#eaf6ff);border-left:6px solid #0077b6}
nav a,.btn{display:inline-block;background:#0077b6;color:white;padding:10px 14px;border-radius:8px;text-decoration:none;margin:5px}.btn-green{background:#198754}.btn-red{background:#dc3545}.btn-gold{background:#f59e0b}.btn-gray{background:#475569}
input,select,textarea{padding:10px;width:100%;max-width:450px;border:1px solid #cbd5e1;border-radius:8px;margin-top:5px;box-sizing:border-box}
button{background:#0077b6;color:white;border:0;padding:11px 18px;border-radius:8px;cursor:pointer}table{width:100%;border-collapse:collapse;background:white}th{background:#003366;color:white}td,th{padding:10px;border:1px solid #ddd;text-align:left}.alert{background:#fff3cd;border-left:6px solid #f59e0b;padding:14px;border-radius:10px;margin-bottom:15px}.danger{background:#ffe5e5;border-left:6px solid #dc3545}.small{font-size:13px;color:#64748b}.badge-low{background:#dc3545;color:white;border-radius:12px;padding:3px 8px;font-size:12px}.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}.success{background:#e8fff2;border-left:6px solid #198754}
@media print{nav,.btn,button,.no-print{display:none}.card{box-shadow:none}body{background:white}.header{background:white;color:black;padding:0}.container{padding:0}}
</style>
"""


def page(title, content, **context):
    # Standard navigation appears on every page so users do not need to keep pressing Back.
    nav = """
    {% if session.get('user_id') %}
    <div class="card no-print" style="padding:12px;margin-bottom:15px">
        <nav>
            <a href="/">🏠 Dashboard</a>
            <a href="/products">📦 Products / Stock</a>
            <a href="/lens-powers">👓 Lens Powers</a>
            <a href="/pos" class="btn-gold">🧾 Make Sale</a>
            <a href="/sales">📊 Sales History</a>
            <a href="/debtors">💳 Debtors</a>
            <a href="/patient-rx">👁️ Patient Rx</a>
            <a href="/lens-search">🔎 Lens Search</a>
            <a href="/notifications">📩 Notifications</a>
            {% if session['role'] == 'manager' %}
            <a href="/add-product" class="btn-green">➕ Add Product</a>
            <a href="/add-lens-power" class="btn-green">🔢 Add Lens Power</a>
            <a href="/generate-power-grid" class="btn-green">⚙️ Generate Power Grid</a>
            <a href="/smart-transfer" class="btn-gray">🔄 Smart Transfer</a>
            <a href="/goods-requests" class="btn-gray">🚚 Goods Requests</a>
            <a href="/branches">🏬 Branches</a>
            <a href="/staff">👥 Staff</a>
            <a href="/daily-report" class="btn-gray">📊 Daily Report</a>
            <a href="/office-settings" class="btn-gray">🏢 Office Settings</a>
            {% endif %}
            <a href="/logout" class="btn-red">🚪 Logout</a>
        </nav>
    </div>
    {% endif %}
    """
    return render_template_string(f"""
    {STYLE}
    <div class="header">
        <h1>Halleluyah Optical Laboratory POS</h1>
        <p>Cloud Optical Inventory, Sales, Lens Power and Debtors System</p>
    </div>
    <div class="container">
        {nav}
        {content}
    </div>
    """, Branch=Branch, User=User, Product=Product, LensPower=LensPower,
       Sale=Sale, SaleItem=SaleItem, OfficeSetting=OfficeSetting, GoodsRequest=GoodsRequest, PatientPrescription=PatientPrescription, NotificationLog=NotificationLog, session=session,
       money=money, **context)


def ensure_schema():
    # db.create_all() never deletes existing records. It only creates missing tables.
    db.create_all()
    # Safe upgrades for old Render databases.
    try:
        db.session.execute(text("ALTER TABLE hol_sale_item ADD COLUMN IF NOT EXISTS lens_power VARCHAR(120)"))
        db.session.execute(text("ALTER TABLE hol_product ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_user ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_sale ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_lens_power ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.before_request
def setup_database():
    ensure_schema()

    if not Branch.query.first():
        branch = Branch(name="Main Branch", address="Sobi Junction, Gambari, Ilorin, Kwara State")
        db.session.add(branch)
        db.session.commit()

    if not OfficeSetting.query.first():
        db.session.add(OfficeSetting())
        db.session.commit()

    main_branch = Branch.query.first()
    if not User.query.filter_by(username="manager").first():
        manager = User(username="manager", password_hash=generate_password_hash("manager123"), role="manager", branch_id=main_branch.id)
        db.session.add(manager)
        db.session.commit()

    # Attach older records to Main Branch. This does not delete data.
    User.query.filter(User.branch_id.is_(None)).update({User.branch_id: main_branch.id})
    Product.query.filter(Product.branch_id.is_(None)).update({Product.branch_id: main_branch.id})
    Sale.query.filter(Sale.branch_id.is_(None)).update({Sale.branch_id: main_branch.id})
    LensPower.query.filter(LensPower.branch_id.is_(None)).update({LensPower.branch_id: main_branch.id})
    db.session.commit()


@app.route("/")
def home():
    if not logged_in():
        return redirect(url_for("login"))

    product_query = Product.query if is_manager() else Product.query.filter_by(branch_id=session.get("branch_id"))
    sale_query = Sale.query if is_manager() else Sale.query.filter_by(branch_id=session.get("branch_id"))
    lens_query = LensPower.query if is_manager() else LensPower.query.filter_by(branch_id=session.get("branch_id"))

    low_products = product_query.filter(Product.quantity <= 5).all()
    low_lens = lens_query.filter(LensPower.quantity <= 2).all()
    using_database = "PostgreSQL / Persistent" if database_url else "Local SQLite / Not persistent on Render"

    content = """
    <div class="card">
        <h2>Welcome, {{ session['username'] }}</h2>
        <p>Role: <b>{{ session['role'] }}</b></p>
        <p class="small">Data storage: <b>{{ using_database }}</b></p>
    </div>

    {% if not database_url %}
    <div class="alert danger"><b>Important:</b> DATABASE_URL is not connected. On Render, use the PostgreSQL database environment variable so product data will remain saved.</div>
    {% endif %}

    {% if low_products or low_lens %}
    <div class="alert danger"><h3>Low Stock Notification</h3>
        {% for p in low_products %}<p><b>{{ p.name }}</b> is low in stock. Quantity: {{ p.quantity }}</p>{% endfor %}
        {% for l in low_lens %}<p><b>Lens power SPH {{ l.sph }} CYL {{ l.cyl }} AXIS {{ l.axis }} ADD {{ l.add_power }}</b> is low. Quantity: {{ l.quantity }}</p>{% endfor %}
    </div>
    {% endif %}

    <div class="grid">
        <div class="card stat"><h3>Total Products</h3><h1>{{ products }}</h1></div>
        <div class="card stat"><h3>Total Lens Powers</h3><h1>{{ lens_powers }}</h1></div>
        <div class="card stat"><h3>Total Sales</h3><h1>{{ sales }}</h1></div>
        <div class="card stat"><h3>Total Debtors</h3><h1>{{ debtors }}</h1></div>
    </div>

    """
    return page("Dashboard", content, products=product_query.count(), lens_powers=lens_query.count(), sales=sale_query.count(), debtors=sale_query.filter(Sale.balance > 0).count(), low_products=low_products, low_lens=low_lens, database_url=database_url, using_database=using_database)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username")).first()
        if user and check_password_hash(user.password_hash, request.form.get("password")):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            session["branch_id"] = user.branch_id
            return redirect(url_for("home"))
        error = "Invalid username or password"
    return page("Login", """
    <div class="card"><h2>Login</h2><form method="post">
        <input name="username" placeholder="Username" required><br><br>
        <input name="password" type="password" placeholder="Password" required><br><br><button>Login</button>
    </form><p style="color:red;">{{ error }}</p><p class="small">Default login: manager / manager123</p></div>
    """, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/office-settings", methods=["GET", "POST"])
def office_settings():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can change office settings."
    setting = OfficeSetting.query.first()
    if request.method == "POST":
        setting.office_name = request.form.get("office_name") or "Halleluyah Optical Laboratory"
        setting.phone = request.form.get("phone") or ""
        setting.address = request.form.get("address") or ""
        db.session.commit()
        return redirect(url_for("home"))
    return page("Office Settings", """
    <div class="card"><h2>Office Phone and Address for Receipt</h2>
    <form method="post">
        <label>Office Name</label><br><input name="office_name" value="{{ setting.office_name }}"><br><br>
        <label>Office Phone Number</label><br><input name="phone" value="{{ setting.phone }}" placeholder="e.g. 080xxxxxxxx"><br><br>
        <label>Office Address</label><br><textarea name="address">{{ setting.address }}</textarea><br><br>
        <button>Save Settings</button>
    </form></div><a class="btn" href="/">Back</a>
    """, setting=setting)


@app.route("/branches", methods=["GET", "POST"])
def branches():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can manage branches."
    if request.method == "POST":
        name = request.form.get("name")
        address = request.form.get("address")
        if name:
            db.session.add(Branch(name=name, address=address))
            db.session.commit()
        return redirect(url_for("branches"))
    return page("Branches", """
    <div class="card"><h2>Add Branch</h2><form method="post"><input name="name" placeholder="Branch Name" required><br><br><input name="address" placeholder="Address"><br><br><button>Add Branch</button></form></div>
    <div class="card"><h2>Branch List</h2><table><tr><th>Name</th><th>Address</th></tr>{% for b in branches %}<tr><td>{{ b.name }}</td><td>{{ b.address }}</td></tr>{% endfor %}</table></div><a class="btn" href="/">Back</a>
    """, branches=Branch.query.all())


PRODUCT_FORM = """
<div class="card"><h2>{{ 'Edit Product' if product else 'Add Product / Stock' }}</h2>
<form method="post">
    <label>Branch</label><br><select name="branch_id">{% for b in branches %}<option value="{{ b.id }}" {% if product and product.branch_id == b.id %}selected{% endif %}>{{ b.name }}</option>{% endfor %}</select><br><br>
    <label>Product Name</label><br><input name="name" placeholder="Product Name" value="{{ product.name if product else '' }}" required><br><br>
    <label>Category</label><br><select name="category">{% for c in ['Single Vision Lens','Bifocal Lens','Progressive Lens','Frame','Case','Lens Cloth','Liquid Lens Cleaner','Accessory'] %}<option {% if product and product.category == c %}selected{% endif %}>{{ c }}</option>{% endfor %}</select><br><br>
    <label>Subcategory</label><br><select name="subcategory">{% for s in ['White Lens','Photo AR','Blue Cut Photo AR','Metal Frame','Plastic Frame','Rimless Frame','Designer Frame','Other'] %}<option {% if product and product.subcategory == s %}selected{% endif %}>{{ s }}</option>{% endfor %}</select><br><br>
    <input name="retail_price" type="number" step="0.01" placeholder="Retail Price" value="{{ product.retail_price if product else '' }}"><br><br>
    <input name="wholesale_price" type="number" step="0.01" placeholder="Wholesale Price" value="{{ product.wholesale_price if product else '' }}"><br><br>
    <input name="quantity" type="number" placeholder="Quantity" value="{{ product.quantity if product else '' }}"><br><br><button>Save Product</button>
</form></div><a class="btn" href="/products">Back</a>
"""


@app.route("/add-product", methods=["GET", "POST"])
def add_product():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can add products."
    if request.method == "POST":
        product = Product(branch_id=int(request.form.get("branch_id")), name=request.form.get("name"), category=request.form.get("category"), subcategory=request.form.get("subcategory"), retail_price=float(request.form.get("retail_price") or 0), wholesale_price=float(request.form.get("wholesale_price") or 0), quantity=int(request.form.get("quantity") or 0))
        db.session.add(product)
        db.session.commit()
        return redirect(url_for("products"))
    return page("Add Product", PRODUCT_FORM, branches=Branch.query.all(), product=None)


@app.route("/products")
def products():
    if not logged_in():
        return redirect(url_for("login"))
    product_list = Product.query.order_by(Product.id.desc()).all() if is_manager() else Product.query.filter_by(branch_id=session.get("branch_id")).order_by(Product.id.desc()).all()
    branches_map = {b.id: b.name for b in Branch.query.all()}
    return page("Products", """
    <div class="card"><h2>Products / Stock</h2><table>
        <tr><th>Branch</th><th>Name</th><th>Category</th><th>Subcategory</th><th>Retail</th><th>Wholesale</th><th>Qty</th>{% if session['role']=='manager' %}<th>Action</th>{% endif %}</tr>
        {% for p in product_list %}<tr><td>{{ branches_map.get(p.branch_id, '') }}</td><td>{{ p.name }}</td><td>{{ p.category }}</td><td>{{ p.subcategory }}</td><td>{{ money(p.retail_price) }}</td><td>{{ money(p.wholesale_price) }}</td><td>{% if p.quantity <= 5 %}<span class="badge-low">LOW</span> {% endif %}{{ p.quantity }}</td>{% if session['role']=='manager' %}<td><a href="/edit-product/{{ p.id }}">Edit</a> | <a href="/restock-product/{{ p.id }}">Restock</a></td>{% endif %}</tr>{% endfor %}
    </table></div><a class="btn" href="/">Back</a>
    """, product_list=product_list, branches_map=branches_map)


@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can edit products."
    product = Product.query.get_or_404(product_id)
    if request.method == "POST":
        product.branch_id = int(request.form.get("branch_id"))
        product.name = request.form.get("name")
        product.category = request.form.get("category")
        product.subcategory = request.form.get("subcategory")
        product.retail_price = float(request.form.get("retail_price") or 0)
        product.wholesale_price = float(request.form.get("wholesale_price") or 0)
        product.quantity = int(request.form.get("quantity") or 0)
        db.session.commit()
        return redirect(url_for("products"))
    return page("Edit Product", PRODUCT_FORM, product=product, branches=Branch.query.all())


@app.route("/restock-product/<int:product_id>", methods=["GET", "POST"])
def restock_product(product_id):
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can restock products."
    product = Product.query.get_or_404(product_id)
    if request.method == "POST":
        add_qty = int(request.form.get("add_qty") or 0)
        product.quantity = int(product.quantity or 0) + add_qty
        db.session.commit()
        return redirect(url_for("products"))
    return page("Restock Product", """
    <div class="card"><h2>Restock Product</h2><p><b>{{ product.name }}</b></p><p>Current Quantity: {{ product.quantity }}</p>
    <form method="post"><input name="add_qty" type="number" min="1" placeholder="Quantity to add" required><br><br><button>Add Stock</button></form></div><a class="btn" href="/products">Back</a>
    """, product=product)


@app.route("/add-lens-power", methods=["GET", "POST"])
def add_lens_power():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can add lens powers."
    product_list = Product.query.filter(Product.category.contains("Lens")).order_by(Product.name).all()
    if request.method == "POST":
        product = Product.query.get(int(request.form.get("product_id")))
        if product:
            existing = LensPower.query.filter_by(product_id=product.id, sph=request.form.get("sph") or "", cyl=request.form.get("cyl") or "", axis=request.form.get("axis") or "", add_power=request.form.get("add_power") or "").first()
            qty = int(request.form.get("quantity") or 0)
            if existing:
                existing.quantity = int(existing.quantity or 0) + qty
            else:
                db.session.add(LensPower(product_id=product.id, branch_id=product.branch_id, sph=request.form.get("sph") or "", cyl=request.form.get("cyl") or "", axis=request.form.get("axis") or "", add_power=request.form.get("add_power") or "", quantity=qty))
            db.session.commit()
        return redirect(url_for("lens_powers"))
    return page("Add Lens Power", """
    <div class="card"><h2>Add Lens Power and Quantity</h2><form method="post">
        <label>Select Lens Product</label><br><select name="product_id" required>{% for p in product_list %}<option value="{{ p.id }}">{{ p.name }} - {{ p.subcategory }}</option>{% endfor %}</select><br><br>
        <input name="sph" placeholder="SPH e.g. -1.00 or +2.00"><br><br><input name="cyl" placeholder="CYL e.g. -0.50"><br><br><input name="axis" placeholder="AXIS e.g. 180"><br><br><input name="add_power" placeholder="ADD e.g. +2.00"><br><br><input name="quantity" type="number" placeholder="Quantity for this power"><br><br><button>Save Lens Power</button>
    </form></div><a class="btn" href="/">Back</a>
    """, product_list=product_list)


@app.route("/lens-powers")
def lens_powers():
    if not logged_in():
        return redirect(url_for("login"))
    power_list = LensPower.query.order_by(LensPower.id.desc()).all() if is_manager() else LensPower.query.filter_by(branch_id=session.get("branch_id")).order_by(LensPower.id.desc()).all()
    products_map = {p.id: p.name for p in Product.query.all()}
    branches_map = {b.id: b.name for b in Branch.query.all()}
    return page("Lens Powers", """
    <div class="card"><h2>Lens Power Stock</h2><p class="small">Manager can delete a wrong lens power entry. Deleting a power does not delete old sales receipts.</p><table><tr><th>Branch</th><th>Lens</th><th>SPH</th><th>CYL</th><th>AXIS</th><th>ADD</th><th>Quantity</th>{% if session['role']=='manager' %}<th>Action</th>{% endif %}</tr>
    {% for l in power_list %}<tr><td>{{ branches_map.get(l.branch_id, '') }}</td><td>{{ products_map.get(l.product_id, '') }}</td><td>{{ l.sph }}</td><td>{{ l.cyl }}</td><td>{{ l.axis }}</td><td>{{ l.add_power }}</td><td>{% if l.quantity <= 2 %}<span class="badge-low">LOW</span> {% endif %}{{ l.quantity }}</td>{% if session['role']=='manager' %}<td><a href="/restock-lens/{{ l.id }}">Restock</a><form method="post" action="/delete-lens-power/{{ l.id }}" style="display:inline" onsubmit="return confirm('Delete this lens power? This is for wrong input correction only.');"><button class="btn-red" type="submit">Delete</button></form></td>{% endif %}</tr>{% endfor %}
    </table></div>
    """, power_list=power_list, products_map=products_map, branches_map=branches_map)


@app.route("/delete-lens-power/<int:lens_id>", methods=["POST"])
def delete_lens_power(lens_id):
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return page("Manager Access Required", "<div class='card'><h2>Manager Access Required</h2><p>Only manager can delete wrong lens power entries.</p><a class='btn' href='/lens-powers'>Back</a></div>")
    lens = LensPower.query.get_or_404(lens_id)
    db.session.delete(lens)
    db.session.commit()
    return redirect(url_for("lens_powers"))


@app.route("/restock-lens/<int:lens_id>", methods=["GET", "POST"])
def restock_lens(lens_id):
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can restock lens powers."
    lens = LensPower.query.get_or_404(lens_id)
    product = Product.query.get(lens.product_id)
    if request.method == "POST":
        add_qty = int(request.form.get("add_qty") or 0)
        lens.quantity = int(lens.quantity or 0) + add_qty
        db.session.commit()
        return redirect(url_for("lens_powers"))
    return page("Restock Lens Power", """
    <div class="card"><h2>Restock Lens Power</h2><p><b>{{ product.name if product else '' }}</b></p><p>SPH {{ lens.sph }} CYL {{ lens.cyl }} AXIS {{ lens.axis }} ADD {{ lens.add_power }}</p><p>Current Quantity: {{ lens.quantity }}</p>
    <form method="post"><input name="add_qty" type="number" min="1" placeholder="Quantity to add" required><br><br><button>Add Stock</button></form></div><a class="btn" href="/lens-powers">Back</a>
    """, lens=lens, product=product)


@app.route("/restock")
def restock():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can restock."
    return page("Restock Center", """
    <div class="card"><h2>Restock Center</h2><p>Use Products / Stock to restock general products. Use Lens Powers to restock exact powers.</p><a class="btn-green btn" href="/products">Restock Products</a><a class="btn-green btn" href="/lens-powers">Restock Lens Powers</a></div><a class="btn" href="/">Back</a>
    """)


@app.route("/generate-power-grid", methods=["GET", "POST"])
def generate_power_grid():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can generate power grid."
    product_list = Product.query.filter(Product.category.contains("Lens")).order_by(Product.name).all()
    message = ""
    if request.method == "POST":
        product = Product.query.get(int(request.form.get("product_id")))
        lens_type = request.form.get("lens_type")
        sph_from = request.form.get("sph_from") or "-20.00"
        sph_to = request.form.get("sph_to") or "20.00"
        add_from = request.form.get("add_from") or "1.00"
        add_to = request.form.get("add_to") or "3.00"
        step = request.form.get("step") or "0.25"
        default_qty = int(request.form.get("default_qty") or 0)
        created = 0
        updated = 0
        if product:
            sph_values = decimal_range(sph_from, sph_to, step)
            add_values = [None]
            if lens_type in ["Bifocal Lens", "Progressive Lens"]:
                add_values = decimal_range(add_from, add_to, step)
            for sph in sph_values:
                for add_val in add_values:
                    sph_s = fmt_power(sph)
                    add_s = "" if add_val is None else fmt_power(add_val)
                    existing = LensPower.query.filter_by(product_id=product.id, sph=sph_s, cyl="", axis="", add_power=add_s).first()
                    if existing:
                        if default_qty:
                            existing.quantity = int(existing.quantity or 0) + default_qty
                        updated += 1
                    else:
                        db.session.add(LensPower(product_id=product.id, branch_id=product.branch_id, sph=sph_s, cyl="", axis="", add_power=add_s, quantity=default_qty))
                        created += 1
            db.session.commit()
            message = f"Created {created} powers and updated {updated} existing powers."
    return page("Generate Power Grid", """
    {% if message %}<div class="alert success"><b>{{ message }}</b></div>{% endif %}
    <div class="card"><h2>Generate Lens Power Grid</h2><p>This lets you choose the exact range. Use step 0.25 for optical standard quarter steps.</p>
    <form method="post">
        <label>Select Lens Product</label><br><select name="product_id" required>{% for p in product_list %}<option value="{{ p.id }}">{{ p.name }} - {{ p.category }} - {{ p.subcategory }}</option>{% endfor %}</select><br><br>
        <label>Lens Type</label><br><select name="lens_type"><option>Single Vision Lens</option><option>Bifocal Lens</option><option>Progressive Lens</option></select><br><br>
        <div class="two"><div><label>SPH From</label><input name="sph_from" value="-20.00"></div><div><label>SPH To</label><input name="sph_to" value="20.00"></div></div><br>
        <div class="two"><div><label>ADD From (Bifocal/Progressive only)</label><input name="add_from" value="1.00"></div><div><label>ADD To</label><input name="add_to" value="3.00"></div></div><br>
        <label>Step</label><br><input name="step" value="0.25"><br><br>
        <label>Default Quantity for each generated power</label><br><input name="default_qty" type="number" value="0"><br><br><button>Generate Powers</button>
    </form></div><a class="btn" href="/">Back</a>
    """, product_list=product_list, message=message)


@app.route("/pos", methods=["GET", "POST"])
def pos():
    if not logged_in():
        return redirect(url_for("login"))

    # Clean American-standard POS screen with ONE shared cart.
    # Staff can load lenses, then frames/accessories, and still print ONE receipt.
    view = request.form.get("view") or request.args.get("view", "none")

    if "pos_cart" not in session:
        session["pos_cart"] = []
    if "pos_customer" not in session:
        session["pos_customer"] = {"customer_name": "", "customer_phone": "", "branch_id": session.get("branch_id"), "price_type": "retail"}

    def is_lens_product(product):
        return "Lens" in (product.category or "")

    def selected_product_query():
        # Manager can sell from any branch; staff can sell only from their own branch.
        # IMPORTANT FIX:
        # Lens products must NOT be filtered by Product.quantity because exact lens stock
        # is controlled by LensPower.quantity. Product.quantity is for frames/accessories.
        if is_manager():
            base_query = Product.query
        else:
            base_query = Product.query.filter(Product.branch_id == session.get("branch_id"))

        if view == "lenses":
            return base_query.filter(Product.category.contains("Lens")).order_by(Product.category, Product.name).all()
        if view == "frames":
            return base_query.filter(
                ~Product.category.contains("Lens"),
                Product.quantity > 0
            ).order_by(Product.category, Product.name).all()
        return []

    product_list = selected_product_query()

    if request.method == "POST":
        # Save customer details while building the cart.
        session["pos_customer"] = {
            "customer_name": request.form.get("customer_name") or session.get("pos_customer", {}).get("customer_name", ""),
            "customer_phone": request.form.get("customer_phone") or session.get("pos_customer", {}).get("customer_phone", ""),
            "branch_id": int(request.form.get("branch_id") or session.get("branch_id") or 1),
            "price_type": request.form.get("price_type") or session.get("pos_customer", {}).get("price_type", "retail"),
        }
        session.modified = True

        price_type = session["pos_customer"].get("price_type", "retail")
        added_count = 0
        cart = session.get("pos_cart", [])

        for product in product_list:
            price = product.wholesale_price if price_type == "wholesale" else product.retail_price

            if is_lens_product(product):
                powers = LensPower.query.filter_by(product_id=product.id).filter(LensPower.quantity > 0).all()
                for lp in powers:
                    sale_unit = request.form.get(f"lens_unit_{lp.id}", "none")
                    custom_qty = int(request.form.get(f"lens_qty_{lp.id}") or 0)

                    if sale_unit == "half_pair":
                        qty = 1
                        unit_label = "Half Pair"
                    elif sale_unit == "one_pair":
                        qty = 2
                        unit_label = "1 Pair"
                    elif sale_unit == "custom":
                        qty = custom_qty
                        unit_label = f"Custom Qty {custom_qty}"
                    else:
                        qty = 0
                        unit_label = ""

                    if qty <= 0:
                        continue

                    if qty > int(lp.quantity or 0):
                        return page(
                            "Insufficient Lens Power Stock",
                            """
                            <div class='card'>
                                <h2>Insufficient Lens Power Stock</h2>
                                <p>You selected more quantity than available.</p>
                                <p><b>Lens:</b> {{ product.name }}</p>
                                <p><b>Power:</b> SPH {{ lp.sph }} CYL {{ lp.cyl }} AXIS {{ lp.axis }} ADD {{ lp.add_power }}</p>
                                <p><b>Available:</b> {{ lp.quantity }}</p>
                                <p><b>Requested:</b> {{ qty }} ({{ unit_label }})</p>
                                <a class='btn' href='/pos?view=lenses'>Go Back</a>
                            </div>
                            """,
                            product=product,
                            lp=lp,
                            qty=qty,
                            unit_label=unit_label
                        )

                    lens_text = f"{unit_label} | SPH {lp.sph or ''} CYL {lp.cyl or ''} AXIS {lp.axis or ''} ADD {lp.add_power or ''}".strip()
                    cart.append({
                        "type": "lens",
                        "product_id": product.id,
                        "lens_power_id": lp.id,
                        "product_name": product.name,
                        "lens_power": lens_text,
                        "quantity": qty,
                        "unit_price": float(price or 0),
                        "subtotal": float(price or 0) * qty,
                    })
                    added_count += 1
            else:
                qty = int(request.form.get(f"qty_{product.id}") or 0)
                if qty <= 0:
                    continue

                if qty > int(product.quantity or 0):
                    return page(
                        "Insufficient Product Stock",
                        """
                        <div class='card'>
                            <h2>Insufficient Product Stock</h2>
                            <p>You selected more quantity than available.</p>
                            <p><b>Product:</b> {{ product.name }}</p>
                            <p><b>Available:</b> {{ product.quantity }}</p>
                            <p><b>Requested:</b> {{ qty }}</p>
                            <a class='btn' href='/pos?view=frames'>Go Back</a>
                        </div>
                        """,
                        product=product,
                        qty=qty
                    )

                cart.append({
                    "type": "product",
                    "product_id": product.id,
                    "lens_power_id": None,
                    "product_name": product.name,
                    "lens_power": "",
                    "quantity": qty,
                    "unit_price": float(price or 0),
                    "subtotal": float(price or 0) * qty,
                })
                added_count += 1

        session["pos_cart"] = cart
        session.modified = True

        if added_count == 0:
            return page(
                "No Product Selected",
                """
                <div class='card'>
                    <h2>No Product Selected</h2>
                    <p>Please select Half Pair, 1 Pair, Custom Qty, or enter quantity for at least one product.</p>
                    <a class='btn' href='/pos'>Back to Make Sale</a>
                </div>
                """
            )

        return redirect(url_for("pos", view=view))

    lens_map = {
        p.id: LensPower.query.filter_by(product_id=p.id).filter(LensPower.quantity > 0).order_by(LensPower.sph, LensPower.cyl, LensPower.add_power).all()
        for p in product_list
    }
    lens_stock_map = {
        p.id: sum(int(l.quantity or 0) for l in lens_map.get(p.id, []))
        for p in product_list
    }

    cart = session.get("pos_cart", [])
    customer = session.get("pos_customer", {})
    cart_total = sum(float(i.get("subtotal", 0) or 0) for i in cart)

    return page("POS", """
    <div class="card">
        <h2>Make Sale - HOL Optical POS Pro</h2>
        <p class="small">One shared cart: add lenses, add frames/accessories, then print one single receipt.</p>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin:20px 0">
            <a href="/pos?view=lenses" style="background:#2563eb;color:white;padding:28px;border-radius:16px;text-decoration:none;font-size:24px;font-weight:bold;text-align:center;box-shadow:0 6px 18px #0002">
                👓 Load Lenses<br><span style="font-size:14px;font-weight:normal">SV, Bifocal, Progressive + Powers</span>
            </a>
            <a href="/pos?view=frames" style="background:#16a34a;color:white;padding:28px;border-radius:16px;text-decoration:none;font-size:24px;font-weight:bold;text-align:center;box-shadow:0 6px 18px #0002">
                🕶️ Load Frames / Accessories<br><span style="font-size:14px;font-weight:normal">Frames, Cases, Rope, Cloth, Cleaner</span>
            </a>
        </div>

        <div class="card" style="background:#f8fafc">
            <h3>Current Cart</h3>
            {% if cart %}
            <table>
                <tr><th>Item</th><th>Lens Power</th><th>Qty</th><th>Unit Price</th><th>Subtotal</th><th>Remove</th></tr>
                {% for item in cart %}
                <tr>
                    <td>{{ item.product_name }}</td>
                    <td>{{ item.lens_power }}</td>
                    <td>{{ item.quantity }}</td>
                    <td>₦{{ money(item.unit_price) }}</td>
                    <td>₦{{ money(item.subtotal) }}</td>
                    <td><a class="btn-red btn" href="/pos/remove/{{ loop.index0 }}">Remove</a></td>
                </tr>
                {% endfor %}
            </table>
            <h2>Total in Cart: ₦{{ money(cart_total) }}</h2>
            <a class="btn-red btn" href="/pos/clear">Clear Cart</a>
            {% else %}
            <div class="alert"><b>No item in cart yet.</b> Load lenses or frames/accessories and add items.</div>
            {% endif %}
        </div>

        {% if view == 'none' %}
        <div class="alert">
            <h3>Select Category To Begin</h3>
            <p>Click <b>Load Lenses</b> to add lenses with powers, or click <b>Load Frames / Accessories</b> to add general optical products.</p>
        </div>
        {% endif %}

        {% if product_list %}
        <form method="post">
            <input type="hidden" name="view" value="{{ view }}">

            <div class="two">
                <div>
                    <label>Customer Name</label><br>
                    <input name="customer_name" value="{{ customer.get('customer_name','') }}" placeholder="Customer Name">
                </div>
                <div>
                    <label>Customer Phone</label><br>
                    <input name="customer_phone" value="{{ customer.get('customer_phone','') }}" placeholder="Customer Phone">
                </div>
            </div>
            <br>

            {% if session['role'] == 'manager' %}
            <label>Branch</label><br>
            <select name="branch_id">
                {% for b in Branch.query.all() %}
                <option value="{{ b.id }}" {% if customer.get('branch_id') == b.id %}selected{% endif %}>{{ b.name }}</option>
                {% endfor %}
            </select><br><br>
            {% endif %}

            <label>Price Type</label><br>
            <select name="price_type">
                <option value="retail" {% if customer.get('price_type') == 'retail' %}selected{% endif %}>Retail / End User</option>
                <option value="wholesale" {% if customer.get('price_type') == 'wholesale' %}selected{% endif %}>Wholesale</option>
            </select><br><br>

            {% if view == 'lenses' %}
                <h3>Add Lens Products and Powers To Cart</h3>
                <p class="small">Half Pair = 1 lens, 1 Pair = 2 lenses, Custom Qty = manual quantity.</p>
            {% elif view == 'frames' %}
                <h3>Add Frames / Accessories To Cart</h3>
                <p class="small">Enter quantity for frames, cases, ropes, cloth, cleaners and accessories.</p>
            {% endif %}

            <table>
                <tr>
                    <th>Product</th>
                    <th>Available Stock</th>
                    <th>{% if view == 'lenses' %}Power Selection{% else %}Quantity{% endif %}</th>
                </tr>

                {% for p in product_list %}
                <tr>
                    <td>
                        <b>{{ p.name }}</b><br>
                        <span class="small">{{ p.category }} / {{ p.subcategory }}</span><br>
                        <span class="small">Retail: ₦{{ money(p.retail_price) }} | Wholesale: ₦{{ money(p.wholesale_price) }}</span>
                    </td>
                    <td>{% if 'Lens' in p.category %}{{ lens_stock_map.get(p.id, 0) }} powers qty{% else %}{{ p.quantity }}{% endif %}</td>
                    <td>
                        {% if 'Lens' in p.category %}
                            <table>
                                <tr><th>Power</th><th>Available</th><th>Sale Type</th><th>Custom Qty</th></tr>
                                {% for l in lens_map[p.id] %}
                                <tr>
                                    <td>SPH {{ l.sph }} CYL {{ l.cyl }} AXIS {{ l.axis }} ADD {{ l.add_power }}</td>
                                    <td>{{ l.quantity }}</td>
                                    <td>
                                        <select name="lens_unit_{{ l.id }}" style="max-width:160px">
                                            <option value="none">Not Selected</option>
                                            <option value="half_pair">Half Pair (1 lens)</option>
                                            <option value="one_pair">1 Pair (2 lenses)</option>
                                            <option value="custom">Custom Qty</option>
                                        </select>
                                    </td>
                                    <td><input type="number" name="lens_qty_{{ l.id }}" min="0" max="{{ l.quantity }}" value="0" style="max-width:100px"></td>
                                </tr>
                                {% else %}
                                <tr><td colspan="4">No available power entered for this lens.</td></tr>
                                {% endfor %}
                            </table>
                        {% else %}
                            <input type="number" name="qty_{{ p.id }}" min="0" max="{{ p.quantity }}" value="0" style="max-width:120px">
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>

            <br>
            <button type="submit" class="btn-green">Add Selected To Cart</button>
        </form>
        {% elif view != 'none' %}
        <div class="alert">
            <h3>No Products Found</h3>
            <p>No available product was found under this category. Check your product category and stock quantity.</p>
        </div>
        {% endif %}

        {% if cart %}
        <div class="card" style="border:2px solid #198754">
            <h2>Complete Sale and Print One Receipt</h2>
            <form method="post" action="/pos/checkout">
                <div class="two">
                    <div>
                        <label>Discount</label><br>
                        <input name="discount" type="number" step="0.01" value="0" placeholder="Discount">
                    </div>
                    <div>
                        <label>Amount Paid</label><br>
                        <input name="amount_paid" type="number" step="0.01" placeholder="Amount Paid">
                    </div>
                </div>
                <br>
                <label>Payment Method</label><br>
                <select name="payment_method">
                    <option>Cash</option>
                    <option>Transfer</option>
                    <option>POS</option>
                    <option>Split Payment</option>
                    <option>Credit</option>
                </select><br><br>
                <button class="btn-green" type="submit">Complete Sale / One Receipt</button>
            </form>
        </div>
        {% endif %}
    </div>
    """, product_list=product_list, lens_map=lens_map, lens_stock_map=lens_stock_map, view=view, cart=cart, cart_total=cart_total, customer=customer)


@app.route("/pos/remove/<int:item_index>")
def remove_pos_cart_item(item_index):
    if not logged_in():
        return redirect(url_for("login"))
    cart = session.get("pos_cart", [])
    if 0 <= item_index < len(cart):
        cart.pop(item_index)
        session["pos_cart"] = cart
        session.modified = True
    return redirect(url_for("pos"))


@app.route("/pos/clear")
def clear_pos_cart():
    if not logged_in():
        return redirect(url_for("login"))
    session["pos_cart"] = []
    session.modified = True
    return redirect(url_for("pos"))


@app.route("/pos/checkout", methods=["POST"])
def pos_checkout():
    if not logged_in():
        return redirect(url_for("login"))

    cart = session.get("pos_cart", [])
    customer = session.get("pos_customer", {})
    if not cart:
        return page("Empty Cart", "<div class='card'><h2>Empty Cart</h2><p>Add lenses, frames or accessories before completing sale.</p><a class='btn' href='/pos'>Back</a></div>")

    # Final stock validation before receipt is created.
    # IMPORTANT FIX:
    # Lens stock is validated/deducted ONLY from LensPower.quantity.
    # Frames/accessories are validated/deducted ONLY from Product.quantity.
    product_deductions = {}
    for item in cart:
        qty = int(item.get("quantity") or 0)
        if qty <= 0:
            return page("Invalid Quantity", "<div class='card'><h2>Invalid Quantity</h2><p>One item in the cart has invalid quantity.</p><a class='btn' href='/pos'>Back</a></div>")

        if item.get("type") == "lens":
            lp = LensPower.query.get(int(item.get("lens_power_id")))
            if not lp or qty > int(lp.quantity or 0):
                return page("Insufficient Lens Power Stock", "<div class='card'><h2>Insufficient Lens Power Stock</h2><p>A lens power in the cart is no longer available in the requested quantity.</p><a class='btn' href='/pos'>Back</a></div>")
        else:
            product_id = int(item.get("product_id"))
            product_deductions[product_id] = product_deductions.get(product_id, 0) + qty

    for product_id, qty in product_deductions.items():
        product = Product.query.get(product_id)
        if not product or qty > int(product.quantity or 0):
            return page("Insufficient Product Stock", "<div class='card'><h2>Insufficient Product Stock</h2><p>A product in the cart is no longer available in the requested quantity.</p><a class='btn' href='/pos'>Back</a></div>")

    subtotal = sum(float(i.get("subtotal", 0) or 0) for i in cart)
    discount = float(request.form.get("discount") or 0)
    amount_paid = float(request.form.get("amount_paid") or 0)
    payment_method = request.form.get("payment_method") or "Cash"
    final_total = max(subtotal - discount, 0)
    balance = max(final_total - amount_paid, 0)

    sale = Sale(
        branch_id=int(customer.get("branch_id") or session.get("branch_id") or 1),
        customer_name=customer.get("customer_name") or "Walk-in Customer",
        customer_phone=customer.get("customer_phone") or "",
        total=final_total,
        discount=discount,
        amount_paid=amount_paid,
        balance=balance,
        payment_method=payment_method
    )
    db.session.add(sale)
    db.session.flush()

    for item in cart:
        item_qty = int(item.get("quantity") or 0)
        db.session.add(SaleItem(
            sale_id=sale.id,
            product_name=item.get("product_name"),
            lens_power=item.get("lens_power") or "",
            quantity=item_qty,
            unit_price=float(item.get("unit_price") or 0),
            subtotal=float(item.get("subtotal") or 0)
        ))

        if item.get("type") == "lens":
            lp = LensPower.query.get(int(item.get("lens_power_id")))
            if lp:
                # Half Pair deducts 1. Full Pair deducts 2. Custom deducts the selected quantity.
                lp.quantity = max(0, int(lp.quantity or 0) - item_qty)

    for product_id, qty in product_deductions.items():
        product = Product.query.get(product_id)
        if product:
            product.quantity = max(0, int(product.quantity or 0) - int(qty or 0))

    db.session.commit()

    session["pos_cart"] = []
    session["pos_customer"] = {"customer_name": "", "customer_phone": "", "branch_id": session.get("branch_id"), "price_type": "retail"}
    session.modified = True

    return redirect(url_for("receipt", sale_id=sale.id))


@app.route("/receipt/<int:sale_id>")
def receipt(sale_id):
    if not logged_in():
        return redirect(url_for("login"))
    sale = Sale.query.get_or_404(sale_id)
    items = SaleItem.query.filter_by(sale_id=sale.id).all()
    branch = Branch.query.get(sale.branch_id)
    setting = OfficeSetting.query.first()
    change_due = max(float(sale.amount_paid or 0) - float(sale.total or 0), 0)
    return page("Receipt", """
    <div class="card"><h2>{{ setting.office_name }}</h2><h3>Receipt / Invoice</h3>
    <p><b>Address:</b> {{ setting.address }}</p><p><b>Phone:</b> {{ setting.phone }}</p><p><b>Branch:</b> {{ branch.name if branch else '' }}</p><p><b>Date:</b> {{ sale.created_at }}</p><p><b>Customer:</b> {{ sale.customer_name }}</p><p><b>Customer Phone:</b> {{ sale.customer_phone }}</p>
    <table><tr><th>Product</th><th>Lens Power</th><th>Qty</th><th>Unit</th><th>Subtotal</th></tr>{% for i in items %}<tr><td>{{ i.product_name }}</td><td>{{ i.lens_power }}</td><td>{{ i.quantity }}</td><td>{{ money(i.unit_price) }}</td><td>{{ money(i.subtotal) }}</td></tr>{% endfor %}</table>
    <p><b>Discount:</b> {{ money(sale.discount) }}</p><p><b>Total:</b> {{ money(sale.total) }}</p><p><b>Amount Paid:</b> {{ money(sale.amount_paid) }}</p><p><b>Balance:</b> {{ money(sale.balance) }}</p><p><b>Change Due:</b> {{ money(change_due) }}</p><p><b>Payment:</b> {{ sale.payment_method }}</p><button onclick="window.print()">Print Receipt</button></div><a class="btn" href="/">Back</a>
    """, sale=sale, items=items, branch=branch, setting=setting, change_due=change_due)


@app.route("/sales")
def sales():
    if not logged_in():
        return redirect(url_for("login"))
    sale_list = Sale.query.order_by(Sale.id.desc()).all() if is_manager() else Sale.query.filter_by(branch_id=session.get("branch_id")).order_by(Sale.id.desc()).all()
    branches_map = {b.id: b.name for b in Branch.query.all()}
    return page("Sales", """
    <div class="card"><h2>Sales History</h2><table><tr><th>Date</th><th>Branch</th><th>Customer</th><th>Total</th><th>Paid</th><th>Balance</th><th>Receipt</th></tr>{% for s in sale_list %}<tr><td>{{ s.created_at }}</td><td>{{ branches_map.get(s.branch_id, '') }}</td><td>{{ s.customer_name }}</td><td>{{ money(s.total) }}</td><td>{{ money(s.amount_paid) }}</td><td>{{ money(s.balance) }}</td><td><a href="/receipt/{{ s.id }}">View</a></td></tr>{% endfor %}</table></div><a class="btn" href="/">Back</a>
    """, sale_list=sale_list, branches_map=branches_map)


@app.route("/debtors", methods=["GET", "POST"])
def debtors():
    if not logged_in():
        return redirect(url_for("login"))

    # Only manager can confirm debtor payment.
    if request.method == "POST":
        if not is_manager():
            return page("Manager Access Required", "<div class='card'><h2>Manager Access Required</h2><p>Only the manager can confirm debtor payments.</p><a class='btn' href='/debtors'>Back</a></div>")

        sale_id = int(request.form.get("sale_id"))
        action = request.form.get("action", "part")
        sale = Sale.query.get_or_404(sale_id)

        if action == "full":
            sale.amount_paid = float(sale.total or 0)
            sale.balance = 0
            sale.payment_method = request.form.get("payment_method") or sale.payment_method or "Cash"
        else:
            payment_amount = float(request.form.get("payment_amount") or 0)
            if payment_amount <= 0:
                return page("Invalid Payment", "<div class='card'><h2>Invalid Payment</h2><p>Enter a payment amount greater than zero.</p><a class='btn' href='/debtors'>Back</a></div>")
            sale.amount_paid = min(float(sale.total or 0), float(sale.amount_paid or 0) + payment_amount)
            sale.balance = max(float(sale.total or 0) - float(sale.amount_paid or 0), 0)
            sale.payment_method = request.form.get("payment_method") or sale.payment_method or "Cash"

        db.session.commit()
        return redirect(url_for("debtors"))

    debtor_list = Sale.query.filter(Sale.balance > 0).order_by(Sale.id.desc()).all() if is_manager() else Sale.query.filter(Sale.branch_id == session.get("branch_id"), Sale.balance > 0).order_by(Sale.id.desc()).all()
    return page("Debtors", """
    <div class="card"><h2>Debtors</h2>
    <p class="small">Only manager can confirm full or part payment on debtor accounts.</p>
    <table>
        <tr><th>Date</th><th>Customer</th><th>Phone</th><th>Total</th><th>Paid</th><th>Balance</th>{% if session['role']=='manager' %}<th>Manager Payment Confirmation</th>{% endif %}</tr>
        {% for s in debtor_list %}
        <tr>
            <td>{{ s.created_at }}</td>
            <td>{{ s.customer_name }}</td>
            <td>{{ s.customer_phone }}</td>
            <td>{{ money(s.total) }}</td>
            <td>{{ money(s.amount_paid) }}</td>
            <td>{{ money(s.balance) }}</td>
            {% if session['role']=='manager' %}
            <td>
                <form method="post" style="margin-bottom:8px">
                    <input type="hidden" name="sale_id" value="{{ s.id }}">
                    <input type="hidden" name="action" value="part">
                    <input name="payment_amount" type="number" step="0.01" min="0" placeholder="Part payment amount" style="max-width:180px">
                    <select name="payment_method" style="max-width:140px"><option>Cash</option><option>Transfer</option><option>POS</option></select>
                    <button type="submit">Confirm Part Payment</button>
                </form>
                <form method="post">
                    <input type="hidden" name="sale_id" value="{{ s.id }}">
                    <input type="hidden" name="action" value="full">
                    <select name="payment_method" style="max-width:140px"><option>Cash</option><option>Transfer</option><option>POS</option></select>
                    <button class="btn-green" type="submit">Confirm Full Payment</button>
                </form>
            </td>
            {% endif %}
        </tr>
        {% endfor %}
    </table></div><a class="btn" href="/">Back</a>
    """, debtor_list=debtor_list)


@app.route("/staff")
def staff():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can manage staff accounts."
    users = User.query.order_by(User.id.asc()).all()
    branches_map = {b.id: b.name for b in Branch.query.all()}
    return page("Staff Accounts", """
    <div class="card">
        <h2>Staff Accounts</h2>
        <p class="small">Manager can remove staff who are no longer working for the company. The default manager account cannot delete itself.</p>
        <a class="btn-green btn" href="/add-staff">Add New Staff</a>
        <table>
            <tr><th>Username</th><th>Role</th><th>Branch</th><th>Action</th></tr>
            {% for u in users %}
            <tr>
                <td>{{ u.username }}</td>
                <td>{{ u.role }}</td>
                <td>{{ branches_map.get(u.branch_id, '') }}</td>
                <td>
                    {% if u.id != session['user_id'] and u.username != 'manager' %}
                    <form method="post" action="/delete-staff/{{ u.id }}" onsubmit="return confirm('Delete this staff account?');">
                        <button class="btn-red" type="submit">Delete</button>
                    </form>
                    {% else %}
                    Protected
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
    <a class="btn" href="/">Back</a>
    """, users=users, branches_map=branches_map)


@app.route("/delete-staff/<int:user_id>", methods=["POST"])
def delete_staff(user_id):
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can delete staff accounts."
    user = User.query.get_or_404(user_id)
    if user.id == session.get("user_id") or user.username == "manager":
        return page("Protected Account", "<div class='card'><h2>Protected Account</h2><p>You cannot delete the active/default manager account.</p><a class='btn' href='/staff'>Back</a></div>")
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("staff"))


@app.route("/add-staff", methods=["GET", "POST"])
def add_staff():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can add staff."
    if request.method == "POST":
        username = request.form.get("username")
        existing = User.query.filter_by(username=username).first()
        if existing:
            return page("User Exists", "<div class='card'><h2>Username already exists</h2><p>Please choose another username.</p><a class='btn' href='/add-staff'>Back</a></div>")
        db.session.add(User(username=username, password_hash=generate_password_hash(request.form.get("password")), role=request.form.get("role"), branch_id=int(request.form.get("branch_id"))))
        db.session.commit()
        return redirect(url_for("staff"))
    return page("Add Staff", """
    <div class="card"><h2>Add Staff / Manager</h2><form method="post"><input name="username" placeholder="Username" required><br><br><input name="password" type="password" placeholder="Password" required><br><br><select name="role"><option value="staff">Staff</option><option value="manager">Manager</option></select><br><br><select name="branch_id">{% for b in branches %}<option value="{{ b.id }}">{{ b.name }}</option>{% endfor %}</select><br><br><button>Create User</button></form></div><a class="btn" href="/staff">Back</a>
    """, branches=Branch.query.all())


@app.route("/request-goods", methods=["GET", "POST"])
def request_goods():
    if not logged_in():
        return redirect(url_for("login"))
    branches = Branch.query.order_by(Branch.name).all()
    products = Product.query.order_by(Product.name).all()
    if request.method == "POST":
        requester_branch_id = int(request.form.get("requester_branch_id") or session.get("branch_id"))
        supplier_branch_id = int(request.form.get("supplier_branch_id"))
        product_id = int(request.form.get("product_id"))
        qty = int(request.form.get("quantity") or 1)
        product = Product.query.get(product_id)
        if not product:
            return page("Invalid Product", "<div class='card'><h2>Product not found</h2><a class='btn' href='/request-goods'>Back</a></div>")
        if supplier_branch_id == requester_branch_id:
            return page("Same Branch", "<div class='card'><h2>Select another branch</h2><p>You cannot request goods from the same branch.</p><a class='btn' href='/request-goods'>Back</a></div>")
        req = GoodsRequest(
            requester_branch_id=requester_branch_id,
            supplier_branch_id=supplier_branch_id,
            product_id=product_id,
            requested_by=session.get("user_id"),
            item_name=product.name,
            quantity=qty,
            note=request.form.get("note") or "",
            status="Pending"
        )
        db.session.add(req)
        db.session.commit()
        return redirect(url_for("goods_requests"))
    return page("Request Goods", """
    <div class="card">
        <h2>Request Goods From Another Branch</h2>
        <p class="small">Use this when your branch is out of stock and another branch has the product.</p>
        <form method="post">
            <label>Your Branch</label><br>
            {% if session['role'] == 'manager' %}
            <select name="requester_branch_id">{% for b in branches %}<option value="{{ b.id }}" {% if b.id == session['branch_id'] %}selected{% endif %}>{{ b.name }}</option>{% endfor %}</select><br><br>
            {% else %}
            <select name="requester_branch_id">{% for b in branches %}{% if b.id == session['branch_id'] %}<option value="{{ b.id }}">{{ b.name }}</option>{% endif %}{% endfor %}</select><br><br>
            {% endif %}
            <label>Request From Branch</label><br>
            <select name="supplier_branch_id">{% for b in branches %}<option value="{{ b.id }}">{{ b.name }}</option>{% endfor %}</select><br><br>
            <label>Product Needed</label><br>
            <select name="product_id">
                {% for p in products %}
                <option value="{{ p.id }}">{{ p.name }} - {{ p.category }} - {{ p.subcategory }} | Stock {{ p.quantity }} | Branch ID {{ p.branch_id }}</option>
                {% endfor %}
            </select><br><br>
            <label>Quantity Needed</label><br><input name="quantity" type="number" min="1" value="1" required><br><br>
            <label>Note</label><br><textarea name="note" placeholder="Reason for request, customer order, urgent need, etc."></textarea><br><br>
            <button>Submit Request</button>
        </form>
    </div>
    <a class="btn" href="/">Back</a>
    """, branches=branches, products=products)


@app.route("/goods-requests")
def goods_requests():
    if not logged_in():
        return redirect(url_for("login"))
    if is_manager():
        requests = GoodsRequest.query.order_by(GoodsRequest.id.desc()).all()
    else:
        requests = GoodsRequest.query.filter(
            (GoodsRequest.requester_branch_id == session.get("branch_id")) | 
            (GoodsRequest.supplier_branch_id == session.get("branch_id"))
        ).order_by(GoodsRequest.id.desc()).all()
    branches_map = {b.id: b.name for b in Branch.query.all()}
    users_map = {u.id: u.username for u in User.query.all()}
    return page("Goods Requests", """
    <div class="card">
        <h2>Inter-Branch Goods Requests</h2>
        <a class="btn-green btn" href="/request-goods">New Goods Request</a>
        <table>
            <tr><th>Date</th><th>From Branch</th><th>Requesting Branch</th><th>Product</th><th>Qty</th><th>Status</th><th>Requested By</th><th>Note</th>{% if session['role']=='manager' %}<th>Action</th>{% endif %}</tr>
            {% for r in requests %}
            <tr>
                <td>{{ r.created_at }}</td>
                <td>{{ branches_map.get(r.supplier_branch_id, '') }}</td>
                <td>{{ branches_map.get(r.requester_branch_id, '') }}</td>
                <td>{{ r.item_name }}</td>
                <td>{{ r.quantity }}</td>
                <td>{{ r.status }}</td>
                <td>{{ users_map.get(r.requested_by, '') }}</td>
                <td>{{ r.note }}</td>
                {% if session['role']=='manager' %}
                <td>
                    {% if r.status == 'Pending' %}
                    <form method="post" action="/approve-goods-request/{{ r.id }}" style="display:inline"><button class="btn-green" type="submit">Approve Transfer</button></form>
                    <form method="post" action="/decline-goods-request/{{ r.id }}" style="display:inline"><button class="btn-red" type="submit">Decline</button></form>
                    {% else %}
                    Processed
                    {% endif %}
                </td>
                {% endif %}
            </tr>
            {% endfor %}
        </table>
    </div>
    <a class="btn" href="/">Back</a>
    """, requests=requests, branches_map=branches_map, users_map=users_map)



def clean_phone_for_whatsapp(phone):
    phone = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if phone.startswith("0"):
        phone = "234" + phone[1:]
    return phone


@app.route("/patient-rx", methods=["GET", "POST"])
def patient_rx():
    if not logged_in():
        return redirect(url_for("login"))

    if request.method == "POST":
        rx = PatientPrescription(
            branch_id=int(request.form.get("branch_id") or session.get("branch_id") or 1),
            patient_name=request.form.get("patient_name") or "",
            phone=request.form.get("phone") or "",
            age=request.form.get("age") or "",
            gender=request.form.get("gender") or "",
            address=request.form.get("address") or "",
            od_sph=request.form.get("od_sph") or "",
            od_cyl=request.form.get("od_cyl") or "",
            od_axis=request.form.get("od_axis") or "",
            od_add=request.form.get("od_add") or "",
            os_sph=request.form.get("os_sph") or "",
            os_cyl=request.form.get("os_cyl") or "",
            os_axis=request.form.get("os_axis") or "",
            os_add=request.form.get("os_add") or "",
            pd=request.form.get("pd") or "",
            seg_height=request.form.get("seg_height") or "",
            frame_measurement=request.form.get("frame_measurement") or "",
            lens_recommendation=request.form.get("lens_recommendation") or "",
            doctor_name=request.form.get("doctor_name") or "",
            note=request.form.get("note") or ""
        )
        db.session.add(rx)
        db.session.commit()
        return redirect(url_for("patient_rx"))

    rx_list = PatientPrescription.query.order_by(PatientPrescription.id.desc()).limit(50).all() if is_manager() else PatientPrescription.query.filter_by(branch_id=session.get("branch_id")).order_by(PatientPrescription.id.desc()).limit(50).all()
    branches_map = {b.id: b.name for b in Branch.query.all()}
    return page("Patient Rx", """
    <div class="card"><h2>👁️ Patient Prescription (Rx)</h2>
    <p class="small">Save patient prescription, PD, segment height, frame measurement and lens recommendation.</p>
    <form method="post">
        {% if session['role'] == 'manager' %}
        <label>Branch</label><br><select name="branch_id">{% for b in Branch.query.all() %}<option value="{{ b.id }}">{{ b.name }}</option>{% endfor %}</select><br><br>
        {% endif %}
        <div class="two"><div><label>Patient Name</label><input name="patient_name" required></div><div><label>Phone</label><input name="phone"></div></div><br>
        <div class="two"><div><label>Age</label><input name="age"></div><div><label>Gender</label><select name="gender"><option></option><option>Male</option><option>Female</option></select></div></div><br>
        <label>Address</label><br><input name="address"><br><br>
        <h3>Right Eye - OD</h3>
        <div class="grid"><input name="od_sph" placeholder="OD SPH"><input name="od_cyl" placeholder="OD CYL"><input name="od_axis" placeholder="OD AXIS"><input name="od_add" placeholder="OD ADD"></div>
        <h3>Left Eye - OS</h3>
        <div class="grid"><input name="os_sph" placeholder="OS SPH"><input name="os_cyl" placeholder="OS CYL"><input name="os_axis" placeholder="OS AXIS"><input name="os_add" placeholder="OS ADD"></div><br>
        <div class="grid"><input name="pd" placeholder="PD"><input name="seg_height" placeholder="Segment Height"><input name="frame_measurement" placeholder="Frame Measurement"><input name="doctor_name" placeholder="Doctor / Optometrist"></div><br>
        <label>Lens Recommendation</label><br><input name="lens_recommendation" placeholder="e.g. Blue Cut Photochromic Progressive"><br><br>
        <label>Note</label><br><textarea name="note" placeholder="Clinical or dispensing note"></textarea><br><br>
        <button class="btn-green">Save Prescription</button>
    </form></div>

    <div class="card"><h2>Recent Prescriptions</h2><table>
    <tr><th>Date</th><th>Branch</th><th>Patient</th><th>Phone</th><th>OD</th><th>OS</th><th>PD</th><th>Lens Recommendation</th></tr>
    {% for r in rx_list %}<tr><td>{{ r.created_at }}</td><td>{{ branches_map.get(r.branch_id, '') }}</td><td>{{ r.patient_name }}</td><td>{{ r.phone }}</td><td>{{ r.od_sph }} / {{ r.od_cyl }} x {{ r.od_axis }} Add {{ r.od_add }}</td><td>{{ r.os_sph }} / {{ r.os_cyl }} x {{ r.os_axis }} Add {{ r.os_add }}</td><td>{{ r.pd }}</td><td>{{ r.lens_recommendation }}</td></tr>{% endfor %}
    </table></div>
    """, rx_list=rx_list, branches_map=branches_map)


@app.route("/lens-search")
def lens_search():
    if not logged_in():
        return redirect(url_for("login"))
    sph = request.args.get("sph", "").strip()
    cyl = request.args.get("cyl", "").strip()
    axis = request.args.get("axis", "").strip()
    add_power = request.args.get("add_power", "").strip()
    material = request.args.get("material", "").strip()

    q = LensPower.query
    if not is_manager():
        q = q.filter(LensPower.branch_id == session.get("branch_id"))
    if sph:
        q = q.filter(LensPower.sph.ilike(f"%{sph}%"))
    if cyl:
        q = q.filter(LensPower.cyl.ilike(f"%{cyl}%"))
    if axis:
        q = q.filter(LensPower.axis.ilike(f"%{axis}%"))
    if add_power:
        q = q.filter(LensPower.add_power.ilike(f"%{add_power}%"))

    results = q.order_by(LensPower.sph, LensPower.cyl, LensPower.add_power).limit(300).all() if any([sph, cyl, axis, add_power, material]) else []
    products_map = {p.id: p for p in Product.query.all()}
    if material:
        results = [r for r in results if material.lower() in ((products_map.get(r.product_id).subcategory if products_map.get(r.product_id) else "") + " " + (products_map.get(r.product_id).name if products_map.get(r.product_id) else "")).lower()]
    branches_map = {b.id: b.name for b in Branch.query.all()}
    return page("Advanced Lens Search", """
    <div class="card"><h2>🔎 Advanced Lens Search</h2>
    <p class="small">Search exact available lens power before selling: SPH, CYL, AXIS, ADD, coating/material.</p>
    <form method="get">
        <div class="grid">
            <input name="sph" value="{{ sph }}" placeholder="SPH e.g. -1.25">
            <input name="cyl" value="{{ cyl }}" placeholder="CYL e.g. -0.50">
            <input name="axis" value="{{ axis }}" placeholder="AXIS e.g. 180">
            <input name="add_power" value="{{ add_power }}" placeholder="ADD e.g. +2.00">
            <input name="material" value="{{ material }}" placeholder="Material/coating e.g. Photo AR">
        </div><br>
        <button>Search Lens</button> <a class="btn" href="/lens-search">Clear</a>
    </form></div>
    <div class="card"><h2>Search Results</h2>
    {% if results %}<table><tr><th>Branch</th><th>Lens Product</th><th>Subcategory</th><th>SPH</th><th>CYL</th><th>AXIS</th><th>ADD</th><th>Qty</th></tr>
    {% for l in results %}{% set p = products_map.get(l.product_id) %}<tr><td>{{ branches_map.get(l.branch_id, '') }}</td><td>{{ p.name if p else '' }}</td><td>{{ p.subcategory if p else '' }}</td><td>{{ l.sph }}</td><td>{{ l.cyl }}</td><td>{{ l.axis }}</td><td>{{ l.add_power }}</td><td>{% if l.quantity <= 2 %}<span class="badge-low">LOW</span> {% endif %}{{ l.quantity }}</td></tr>{% endfor %}</table>
    {% else %}<div class="alert">Enter search details above to find available lens powers.</div>{% endif %}
    </div>
    """, results=results, products_map=products_map, branches_map=branches_map, sph=sph, cyl=cyl, axis=axis, add_power=add_power, material=material)


@app.route("/notifications", methods=["GET", "POST"])
def notifications():
    if not logged_in():
        return redirect(url_for("login"))
    whatsapp_link = ""
    if request.method == "POST":
        customer_name = request.form.get("customer_name") or "Customer"
        phone = request.form.get("phone") or ""
        message_type = request.form.get("message_type") or "ready"
        custom_message = request.form.get("message") or ""
        if not custom_message:
            if message_type == "ready":
                custom_message = f"Dear {customer_name}, your glasses are ready for pickup at Halleluyah Optical Laboratory. Thank you."
            elif message_type == "debtor":
                custom_message = f"Dear {customer_name}, kindly remember your outstanding balance at Halleluyah Optical Laboratory. Thank you."
            else:
                custom_message = f"Dear {customer_name}, this is a reminder from Halleluyah Optical Laboratory. Thank you."
        db.session.add(NotificationLog(branch_id=session.get("branch_id"), customer_name=customer_name, phone=phone, message=custom_message, channel="WhatsApp"))
        db.session.commit()
        import urllib.parse
        whatsapp_link = "https://wa.me/" + clean_phone_for_whatsapp(phone) + "?text=" + urllib.parse.quote(custom_message)

    debtor_list = Sale.query.filter(Sale.balance > 0).order_by(Sale.id.desc()).limit(30).all() if is_manager() else Sale.query.filter(Sale.branch_id == session.get("branch_id"), Sale.balance > 0).order_by(Sale.id.desc()).limit(30).all()
    logs = NotificationLog.query.order_by(NotificationLog.id.desc()).limit(30).all()
    return page("Notifications", """
    <div class="card"><h2>📩 SMS / WhatsApp Notification</h2>
    <p class="small">This creates a WhatsApp message link. For real automatic SMS, you can later connect Termii, Twilio, BulkSMS Nigeria, or WhatsApp Business API.</p>
    {% if whatsapp_link %}<div class="alert success"><b>Message ready:</b> <a class="btn-green btn" href="{{ whatsapp_link }}" target="_blank">Open WhatsApp and Send</a></div>{% endif %}
    <form method="post">
        <div class="two"><div><label>Customer Name</label><input name="customer_name" required></div><div><label>Phone Number</label><input name="phone" placeholder="080..." required></div></div><br>
        <label>Message Type</label><br><select name="message_type"><option value="ready">Glasses Ready</option><option value="debtor">Debtor Reminder</option><option value="appointment">Appointment Reminder</option><option value="custom">Custom Message</option></select><br><br>
        <label>Custom Message Optional</label><br><textarea name="message" placeholder="Leave empty to auto-generate message"></textarea><br><br>
        <button class="btn-green">Create WhatsApp Message</button>
    </form></div>
    <div class="card"><h2>Debtor Quick Reminder</h2><table><tr><th>Customer</th><th>Phone</th><th>Balance</th><th>Quick Message</th></tr>{% for d in debtor_list %}<tr><td>{{ d.customer_name }}</td><td>{{ d.customer_phone }}</td><td>₦{{ money(d.balance) }}</td><td><a class="btn" target="_blank" href="https://wa.me/{{ clean_phone_for_whatsapp(d.customer_phone) }}?text=Dear%20{{ d.customer_name|replace(' ', '%20') }},%20kindly%20remember%20your%20outstanding%20balance%20of%20₦{{ money(d.balance)|replace(',', '') }}%20at%20Halleluyah%20Optical%20Laboratory.%20Thank%20you.">Send WhatsApp</a></td></tr>{% endfor %}</table></div>
    <div class="card"><h2>Recent Notification Log</h2><table><tr><th>Date</th><th>Customer</th><th>Phone</th><th>Message</th></tr>{% for n in logs %}<tr><td>{{ n.created_at }}</td><td>{{ n.customer_name }}</td><td>{{ n.phone }}</td><td>{{ n.message }}</td></tr>{% endfor %}</table></div>
    """, debtor_list=debtor_list, logs=logs, whatsapp_link=whatsapp_link, clean_phone_for_whatsapp=clean_phone_for_whatsapp)


def report_range_from_date(date_text):
    try:
        start = datetime.strptime(date_text, "%Y-%m-%d")
    except Exception:
        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


@app.route("/daily-report")
def daily_report():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can view daily financial report."
    report_date = request.args.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
    start, end = report_range_from_date(report_date)
    sales = Sale.query.filter(Sale.created_at >= start, Sale.created_at < end).order_by(Sale.id.desc()).all()
    total_sales = sum(float(s.total or 0) for s in sales)
    total_paid = sum(float(s.amount_paid or 0) for s in sales)
    total_balance = sum(float(s.balance or 0) for s in sales)
    total_discount = sum(float(s.discount or 0) for s in sales)
    payment_totals = {}
    for s in sales:
        payment_totals[s.payment_method or "Unknown"] = payment_totals.get(s.payment_method or "Unknown", 0) + float(s.amount_paid or 0)
    return page("Daily Report", """
    <div class="card"><h2>📊 Daily Financial Summary Auto Report</h2>
    <form method="get"><label>Select Date</label><br><input type="date" name="date" value="{{ report_date }}"><br><br><button>View Report</button> <a class="btn-green btn" href="/daily-report/export?date={{ report_date }}">Download CSV</a></form></div>
    <div class="grid">
        <div class="card stat"><h3>Total Sales</h3><h1>₦{{ money(total_sales) }}</h1></div>
        <div class="card stat"><h3>Total Paid</h3><h1>₦{{ money(total_paid) }}</h1></div>
        <div class="card stat"><h3>Total Balance</h3><h1>₦{{ money(total_balance) }}</h1></div>
        <div class="card stat"><h3>Total Discount</h3><h1>₦{{ money(total_discount) }}</h1></div>
    </div>
    <div class="card"><h2>Payment Breakdown</h2><table><tr><th>Payment Method</th><th>Amount</th></tr>{% for k,v in payment_totals.items() %}<tr><td>{{ k }}</td><td>₦{{ money(v) }}</td></tr>{% endfor %}</table></div>
    <div class="card"><h2>Sales List</h2><table><tr><th>Date</th><th>Customer</th><th>Total</th><th>Paid</th><th>Balance</th><th>Payment</th><th>Receipt</th></tr>{% for s in sales %}<tr><td>{{ s.created_at }}</td><td>{{ s.customer_name }}</td><td>₦{{ money(s.total) }}</td><td>₦{{ money(s.amount_paid) }}</td><td>₦{{ money(s.balance) }}</td><td>{{ s.payment_method }}</td><td><a href="/receipt/{{ s.id }}">View</a></td></tr>{% endfor %}</table></div>
    """, report_date=report_date, sales=sales, total_sales=total_sales, total_paid=total_paid, total_balance=total_balance, total_discount=total_discount, payment_totals=payment_totals)


@app.route("/daily-report/export")
def daily_report_export():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can export daily report."
    report_date = request.args.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
    start, end = report_range_from_date(report_date)
    sales = Sale.query.filter(Sale.created_at >= start, Sale.created_at < end).order_by(Sale.id.desc()).all()
    lines = ["Date,Customer,Phone,Total,Discount,Amount Paid,Balance,Payment Method"]
    for s in sales:
        lines.append(f'"{s.created_at}","{s.customer_name}","{s.customer_phone}",{float(s.total or 0)},{float(s.discount or 0)},{float(s.amount_paid or 0)},{float(s.balance or 0)},"{s.payment_method}"')
    csv_data = "\n".join(lines)
    return app.response_class(csv_data, mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=HOL_Daily_Report_{report_date}.csv"})


@app.route("/smart-transfer")
def smart_transfer():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can view Smart Transfer recommendations."

    branches = {b.id: b for b in Branch.query.all()}
    products = {p.id: p for p in Product.query.all()}
    lens_rows = LensPower.query.all()
    recommendations = []

    # Lens power intelligence: same product name + category + subcategory + exact power, but different branch.
    for low in lens_rows:
        if int(low.quantity or 0) > 2:
            continue
        low_product = products.get(low.product_id)
        if not low_product:
            continue
        for excess in lens_rows:
            if excess.id == low.id or excess.branch_id == low.branch_id:
                continue
            excess_product = products.get(excess.product_id)
            if not excess_product:
                continue
            same_lens = (
                low_product.name == excess_product.name and
                low_product.category == excess_product.category and
                low_product.subcategory == excess_product.subcategory and
                (low.sph or "") == (excess.sph or "") and
                (low.cyl or "") == (excess.cyl or "") and
                (low.axis or "") == (excess.axis or "") and
                (low.add_power or "") == (excess.add_power or "")
            )
            if same_lens and int(excess.quantity or 0) >= 10:
                recommended_qty = min(20, max(1, int(excess.quantity or 0) - 5), max(1, 20 - int(low.quantity or 0)))
                recommendations.append({
                    "kind": "Lens Power",
                    "item": f"{low_product.name} - SPH {low.sph} CYL {low.cyl} AXIS {low.axis} ADD {low.add_power}",
                    "low_branch": branches.get(low.branch_id).name if branches.get(low.branch_id) else "",
                    "excess_branch": branches.get(excess.branch_id).name if branches.get(excess.branch_id) else "",
                    "low_qty": int(low.quantity or 0),
                    "excess_qty": int(excess.quantity or 0),
                    "recommended_qty": recommended_qty,
                    "requester_branch_id": low.branch_id,
                    "supplier_branch_id": excess.branch_id,
                    "product_id": excess_product.id,
                    "note": f"Smart transfer: {low_product.name} SPH {low.sph} CYL {low.cyl} AXIS {low.axis} ADD {low.add_power}. Low branch has {low.quantity}; source branch has {excess.quantity}."
                })

    # General product intelligence: same product in different branches.
    product_rows = Product.query.all()
    for low in product_rows:
        if int(low.quantity or 0) > 5:
            continue
        for excess in product_rows:
            if excess.id == low.id or excess.branch_id == low.branch_id:
                continue
            same_product = (
                low.name == excess.name and
                low.category == excess.category and
                low.subcategory == excess.subcategory
            )
            if same_product and int(excess.quantity or 0) >= 20:
                recommended_qty = min(20, max(1, int(excess.quantity or 0) - 10), max(1, 20 - int(low.quantity or 0)))
                recommendations.append({
                    "kind": "Product",
                    "item": f"{low.name} - {low.category} - {low.subcategory}",
                    "low_branch": branches.get(low.branch_id).name if branches.get(low.branch_id) else "",
                    "excess_branch": branches.get(excess.branch_id).name if branches.get(excess.branch_id) else "",
                    "low_qty": int(low.quantity or 0),
                    "excess_qty": int(excess.quantity or 0),
                    "recommended_qty": recommended_qty,
                    "requester_branch_id": low.branch_id,
                    "supplier_branch_id": excess.branch_id,
                    "product_id": excess.id,
                    "note": f"Smart transfer: {low.name}. Low branch has {low.quantity}; source branch has {excess.quantity}."
                })

    return page("Smart Transfer", """
    <div class="card">
        <h2>Multi-Branch Inventory Intelligence</h2>
        <p class="small">This system detects low stock in one branch and excess stock in another branch, then recommends transfer quantity automatically.</p>
        <p class="small"><b>Rule:</b> Lens powers low at 2 or below; excess at 10 or above. Products low at 5 or below; excess at 20 or above.</p>
        <table>
            <tr><th>Type</th><th>Item</th><th>Low Branch</th><th>Low Qty</th><th>Excess Branch</th><th>Excess Qty</th><th>Recommended Transfer</th><th>Action</th></tr>
            {% for r in recommendations %}
            <tr>
                <td>{{ r.kind }}</td>
                <td>{{ r.item }}</td>
                <td>{{ r.low_branch }}</td>
                <td><span class="badge-low">{{ r.low_qty }}</span></td>
                <td>{{ r.excess_branch }}</td>
                <td>{{ r.excess_qty }}</td>
                <td><b>{{ r.recommended_qty }}</b></td>
                <td>
                    <form method="post" action="/smart-transfer/request">
                        <input type="hidden" name="requester_branch_id" value="{{ r.requester_branch_id }}">
                        <input type="hidden" name="supplier_branch_id" value="{{ r.supplier_branch_id }}">
                        <input type="hidden" name="product_id" value="{{ r.product_id }}">
                        <input type="hidden" name="quantity" value="{{ r.recommended_qty }}">
                        <input type="hidden" name="note" value="{{ r.note }}">
                        <button class="btn-green" type="submit">Create Transfer Request</button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="8">No smart transfer recommendation at the moment.</td></tr>
            {% endfor %}
        </table>
    </div>
    """, recommendations=recommendations)


@app.route("/smart-transfer/request", methods=["POST"])
def smart_transfer_request():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can create smart transfer requests."

    product_id = int(request.form.get("product_id"))
    product = Product.query.get_or_404(product_id)
    req = GoodsRequest(
        requester_branch_id=int(request.form.get("requester_branch_id")),
        supplier_branch_id=int(request.form.get("supplier_branch_id")),
        product_id=product_id,
        requested_by=session.get("user_id"),
        item_name=product.name,
        quantity=int(request.form.get("quantity") or 1),
        note=request.form.get("note") or "Smart transfer recommendation",
        status="Pending"
    )
    db.session.add(req)
    db.session.commit()
    return redirect(url_for("goods_requests"))


@app.route("/approve-goods-request/<int:request_id>", methods=["POST"])
def approve_goods_request(request_id):
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can approve goods requests."
    req = GoodsRequest.query.get_or_404(request_id)
    if req.status != "Pending":
        return redirect(url_for("goods_requests"))
    source_product = Product.query.get(req.product_id)
    if not source_product:
        req.status = "Declined - Product Missing"
        req.processed_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("goods_requests"))
    if int(source_product.quantity or 0) < int(req.quantity or 0):
        return page("Not Enough Stock", """
        <div class="card"><h2>Not Enough Stock</h2>
        <p>The supplying branch does not have enough quantity to transfer.</p>
        <p>Available: {{ source_product.quantity }} | Requested: {{ req.quantity }}</p>
        <a class="btn" href="/goods-requests">Back</a></div>
        """, source_product=source_product, req=req)

    source_product.quantity = int(source_product.quantity or 0) - int(req.quantity or 0)
    destination_product = Product.query.filter_by(
        branch_id=req.requester_branch_id,
        name=source_product.name,
        category=source_product.category,
        subcategory=source_product.subcategory
    ).first()
    if not destination_product:
        destination_product = Product(
            branch_id=req.requester_branch_id,
            name=source_product.name,
            category=source_product.category,
            subcategory=source_product.subcategory,
            retail_price=source_product.retail_price,
            wholesale_price=source_product.wholesale_price,
            quantity=0
        )
        db.session.add(destination_product)
        db.session.flush()
    destination_product.quantity = int(destination_product.quantity or 0) + int(req.quantity or 0)
    req.status = "Approved and Transferred"
    req.processed_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("goods_requests"))


@app.route("/decline-goods-request/<int:request_id>", methods=["POST"])
def decline_goods_request(request_id):
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can decline goods requests."
    req = GoodsRequest.query.get_or_404(request_id)
    if req.status == "Pending":
        req.status = "Declined"
        req.processed_at = datetime.utcnow()
        db.session.commit()
    return redirect(url_for("goods_requests"))


if __name__ == "__main__":
    app.run(debug=False)