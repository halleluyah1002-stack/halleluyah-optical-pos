import os
from datetime import datetime
from flask import Flask, request, redirect, url_for, session, render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

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
    cyl = db.Column(db.String(20), default="")
    axis = db.Column(db.String(20), default="")
    add_power = db.Column(db.String(20), default="")
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
    lens_power = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0)
    subtotal = db.Column(db.Float, default=0)


def logged_in():
    return "user_id" in session


def is_manager():
    return session.get("role") == "manager"


STYLE = """
<style>
body{margin:0;font-family:Arial,Helvetica,sans-serif;background:#f4f7fb;color:#1f2937}
.header{background:linear-gradient(90deg,#003366,#0077b6);color:white;padding:22px}
.container{padding:25px}.card{background:white;border-radius:14px;padding:20px;margin-bottom:20px;box-shadow:0 4px 15px #0001}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px}
.stat{background:linear-gradient(135deg,#ffffff,#eaf6ff);border-left:6px solid #0077b6}.stat h1{margin:5px 0;color:#003366}
nav a,.btn{display:inline-block;background:#0077b6;color:white;padding:10px 14px;border-radius:8px;text-decoration:none;margin:5px}
.btn-green{background:#198754}.btn-red{background:#dc3545}.btn-gold{background:#f59e0b}.btn-gray{background:#6b7280}
input,select{padding:10px;width:100%;max-width:420px;border:1px solid #ccc;border-radius:8px;margin-top:5px;box-sizing:border-box}
button{background:#0077b6;color:white;border:0;padding:11px 18px;border-radius:8px;cursor:pointer}
table{width:100%;border-collapse:collapse;background:white;overflow-x:auto}th{background:#003366;color:white}td,th{padding:10px;border:1px solid #ddd;text-align:left;vertical-align:top}
.alert{background:#fff3cd;border-left:6px solid #f59e0b;padding:14px;border-radius:10px;margin-bottom:15px}.danger{background:#ffe5e5;border-left:6px solid #dc3545}.small{font-size:13px;color:#6b7280}.badge-low{background:#dc3545;color:white;padding:3px 7px;border-radius:5px;font-size:12px}
@media(max-width:700px){.container{padding:12px}table{font-size:13px}nav a,.btn{display:block;margin:7px 0}}
@media print{nav,.btn,button{display:none}.card{box-shadow:none}.header{color:black;background:white}}
</style>
"""


def page(title, content, **context):
    html = STYLE + """
    <div class="header">
        <h1>Halleluyah Optical Laboratory POS</h1>
        <p>Cloud Optical Inventory, Sales, Lens Power and Debtors System</p>
    </div>
    <div class="container">""" + content + """</div>"""
    return render_template_string(
        html,
        Branch=Branch,
        User=User,
        Product=Product,
        LensPower=LensPower,
        Sale=Sale,
        SaleItem=SaleItem,
        session=session,
        **context,
    )


def ensure_schema():
    db.create_all()
    try:
        db.session.execute(text("ALTER TABLE hol_sale_item ADD COLUMN IF NOT EXISTS lens_power VARCHAR(100)"))
        db.session.execute(text("ALTER TABLE hol_product ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_user ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_sale ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_lens_power ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_lens_power ADD COLUMN IF NOT EXISTS cyl VARCHAR(20)"))
        db.session.execute(text("ALTER TABLE hol_lens_power ADD COLUMN IF NOT EXISTS axis VARCHAR(20)"))
        db.session.execute(text("ALTER TABLE hol_lens_power ADD COLUMN IF NOT EXISTS add_power VARCHAR(20)"))
        db.session.commit()
    except Exception:
        db.session.rollback()


def format_power(value):
    value = round(float(value), 2)
    if abs(value) < 0.001:
        return "0.00"
    return f"{value:+.2f}"


def quarter_range(start, stop):
    start_i = int(round(start * 100))
    stop_i = int(round(stop * 100))
    step = 25 if stop_i >= start_i else -25
    return [format_power(i / 100) for i in range(start_i, stop_i + step, step)]


def get_lens_mode(category):
    cat = (category or "").lower()
    if "single" in cat:
        return "single"
    if "bifocal" in cat:
        return "bifocal"
    if "progressive" in cat:
        return "progressive"
    return "other"


def save_or_add_lens_power(product, sph, cyl="", axis="", add_power="", quantity=0):
    existing = LensPower.query.filter_by(
        product_id=product.id,
        branch_id=product.branch_id,
        sph=sph,
        cyl=cyl or "",
        axis=axis or "",
        add_power=add_power or "",
    ).first()
    if existing:
        existing.quantity = int(existing.quantity or 0) + int(quantity or 0)
        return False
    db.session.add(LensPower(
        product_id=product.id,
        branch_id=product.branch_id,
        sph=sph,
        cyl=cyl or "",
        axis=axis or "",
        add_power=add_power or "",
        quantity=int(quantity or 0),
    ))
    return True


def generate_standard_powers(product, default_quantity=0, cyl="", axis=""):
    mode = get_lens_mode(product.category)
    created = 0
    updated = 0
    if mode == "single":
        # 0.25 step from -20.00 to +20.00, including 0.00.
        for sph in quarter_range(-20.00, 20.00):
            if save_or_add_lens_power(product, sph=sph, cyl=cyl, axis=axis, add_power="", quantity=default_quantity):
                created += 1
            else:
                updated += 1
    elif mode in ("bifocal", "progressive"):
        # 0.25 step from -3.00 to +3.00, with ADD +1.00 to +3.00.
        for sph in quarter_range(-3.00, 3.00):
            for add_power in quarter_range(1.00, 3.00):
                if save_or_add_lens_power(product, sph=sph, cyl=cyl, axis=axis, add_power=add_power, quantity=default_quantity):
                    created += 1
                else:
                    updated += 1
    db.session.commit()
    return created, updated


@app.before_request
def setup_database():
    ensure_schema()
    if not Branch.query.first():
        db.session.add(Branch(name="Main Branch", address="Sobi Junction, Gambari, Ilorin, Kwara State"))
        db.session.commit()
    main_branch = Branch.query.first()
    if not User.query.filter_by(username="manager").first():
        db.session.add(User(username="manager", password_hash=generate_password_hash("manager123"), role="manager", branch_id=main_branch.id))
        db.session.commit()
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
    content = """
    <div class="card"><h2>Welcome, {{ session['username'] }}</h2><p>Role: <b>{{ session['role'] }}</b></p></div>
    {% if low_products or low_lens %}<div class="alert danger"><h3>Low Stock Notification</h3>
    {% for p in low_products %}<p><b>{{ p.name }}</b> is low in stock. Quantity: {{ p.quantity }} {% if session['role']=='manager' %}<a href="/add-stock/product/{{ p.id }}">Restock now</a>{% endif %}</p>{% endfor %}
    {% for l in low_lens %}<p><b>Lens power SPH {{ l.sph }} CYL {{ l.cyl }} AXIS {{ l.axis }} ADD {{ l.add_power }}</b> is low. Quantity: {{ l.quantity }} {% if session['role']=='manager' %}<a href="/add-stock/lens/{{ l.id }}">Restock now</a>{% endif %}</p>{% endfor %}
    </div>{% endif %}
    <div class="grid">
      <div class="card stat"><h3>Total Products</h3><h1>{{ products }}</h1></div>
      <div class="card stat"><h3>Total Lens Powers</h3><h1>{{ lens_powers }}</h1></div>
      <div class="card stat"><h3>Total Sales</h3><h1>{{ sales }}</h1></div>
      <div class="card stat"><h3>Total Debtors</h3><h1>{{ debtors }}</h1></div>
    </div>
    <div class="card"><h2>Menu</h2><nav>
      <a href="/products">Products / Stock</a><a href="/lens-powers">Lens Powers</a>
      {% if session['role']=='manager' %}<a href="/add-product" class="btn-green">Add Product</a><a href="/add-lens-power" class="btn-green">Add Lens Power</a><a href="/restock" class="btn-green">Restock</a><a href="/bulk-generate-powers" class="btn-green">Generate Power Grid</a><a href="/branches">Branches</a><a href="/add-staff">Add Staff</a>{% endif %}
      <a href="/pos" class="btn-gold">Make Sale</a><a href="/sales">Sales History</a><a href="/debtors">Debtors</a><a href="/logout" class="btn-red">Logout</a>
    </nav></div>
    """
    return page("Dashboard", content, products=product_query.count(), lens_powers=lens_query.count(), sales=sale_query.count(), debtors=sale_query.filter(Sale.balance > 0).count(), low_products=low_products, low_lens=low_lens)


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
    <div class="card"><h2>Login</h2><form method="post"><input name="username" placeholder="Username" required><br><br><input name="password" type="password" placeholder="Password" required><br><br><button>Login</button></form><p style="color:red;">{{ error }}</p><p class="small">Default login: manager / manager123</p></div>
    """, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/branches", methods=["GET", "POST"])
def branches():
    if not logged_in(): return redirect(url_for("login"))
    if not is_manager(): return "Only manager can manage branches."
    if request.method == "POST":
        if request.form.get("name"):
            db.session.add(Branch(name=request.form.get("name"), address=request.form.get("address")))
            db.session.commit()
        return redirect(url_for("branches"))
    content = """
    <div class="card"><h2>Add Branch</h2><form method="post"><input name="name" placeholder="Branch Name" required><br><br><input name="address" placeholder="Address"><br><br><button>Add Branch</button></form></div>
    <div class="card"><h2>Branch List</h2><table><tr><th>Name</th><th>Address</th></tr>{% for b in branches %}<tr><td>{{ b.name }}</td><td>{{ b.address }}</td></tr>{% endfor %}</table></div><a class="btn" href="/">Back</a>
    """
    return page("Branches", content, branches=Branch.query.all())


PRODUCT_FORM = """
<div class="card"><h2>{{ 'Edit Product' if product else 'Add Product / Stock' }}</h2><form method="post">
<label>Branch</label><br><select name="branch_id">{% for b in branches %}<option value="{{ b.id }}" {% if product and product.branch_id == b.id %}selected{% endif %}>{{ b.name }}</option>{% endfor %}</select><br><br>
<input name="name" placeholder="Product Name" value="{{ product.name if product else '' }}" required><br><br>
<label>Category</label><br><select name="category">{% for c in ['Single Vision Lens','Bifocal Lens','Progressive Lens','Frame','Case','Lens Cloth','Liquid Lens Cleaner','Accessory'] %}<option {% if product and product.category == c %}selected{% endif %}>{{ c }}</option>{% endfor %}</select><br><br>
<label>Subcategory</label><br><select name="subcategory">{% for s in ['White Lens','Photo AR','Blue Cut Photo AR','Metal Frame','Plastic Frame','Rimless Frame','Designer Frame','Other'] %}<option {% if product and product.subcategory == s %}selected{% endif %}>{{ s }}</option>{% endfor %}</select><br><br>
<input name="retail_price" type="number" step="0.01" placeholder="Retail Price" value="{{ product.retail_price if product else '' }}"><br><br>
<input name="wholesale_price" type="number" step="0.01" placeholder="Wholesale Price" value="{{ product.wholesale_price if product else '' }}"><br><br>
<input name="quantity" type="number" placeholder="Quantity" value="{{ product.quantity if product else '' }}"><br><br><button>Save Product</button></form></div><a class="btn" href="/products">Back</a>
"""


@app.route("/add-product", methods=["GET", "POST"])
def add_product():
    if not logged_in(): return redirect(url_for("login"))
    if not is_manager(): return "Only manager can add products."
    if request.method == "POST":
        db.session.add(Product(branch_id=int(request.form.get("branch_id")), name=request.form.get("name"), category=request.form.get("category"), subcategory=request.form.get("subcategory"), retail_price=float(request.form.get("retail_price") or 0), wholesale_price=float(request.form.get("wholesale_price") or 0), quantity=int(request.form.get("quantity") or 0)))
        db.session.commit()
        return redirect(url_for("products"))
    return page("Add Product", PRODUCT_FORM, branches=Branch.query.all(), product=None)


@app.route("/products")
def products():
    if not logged_in(): return redirect(url_for("login"))
    product_list = Product.query.order_by(Product.id.desc()).all() if is_manager() else Product.query.filter_by(branch_id=session.get("branch_id")).order_by(Product.id.desc()).all()
    branches = {b.id: b.name for b in Branch.query.all()}
    content = """
    <div class="card"><h2>Products / Stock</h2><table><tr><th>Branch</th><th>Name</th><th>Category</th><th>Subcategory</th><th>Retail</th><th>Wholesale</th><th>Qty</th>{% if session['role']=='manager' %}<th>Action</th>{% endif %}</tr>
    {% for p in product_list %}<tr><td>{{ branches.get(p.branch_id, '') }}</td><td>{{ p.name }}</td><td>{{ p.category }}</td><td>{{ p.subcategory }}</td><td>{{ p.retail_price }}</td><td>{{ p.wholesale_price }}</td><td>{% if p.quantity <= 5 %}<span class="badge-low">LOW</span> {% endif %}{{ p.quantity }}</td>{% if session['role']=='manager' %}<td><a href="/edit-product/{{ p.id }}">Edit</a> | <a href="/add-stock/product/{{ p.id }}">Add Stock</a></td>{% endif %}</tr>{% endfor %}</table></div><a class="btn" href="/">Back</a>
    """
    return page("Products", content, product_list=product_list, branches=branches)


@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if not logged_in(): return redirect(url_for("login"))
    if not is_manager(): return "Only manager can edit products."
    product = Product.query.get_or_404(product_id)
    if request.method == "POST":
        product.branch_id = int(request.form.get("branch_id")); product.name = request.form.get("name"); product.category = request.form.get("category"); product.subcategory = request.form.get("subcategory"); product.retail_price = float(request.form.get("retail_price") or 0); product.wholesale_price = float(request.form.get("wholesale_price") or 0); product.quantity = int(request.form.get("quantity") or 0)
        db.session.commit(); return redirect(url_for("products"))
    return page("Edit Product", PRODUCT_FORM, product=product, branches=Branch.query.all())


@app.route("/add-lens-power", methods=["GET", "POST"])
def add_lens_power():
    if not logged_in(): return redirect(url_for("login"))
    if not is_manager(): return "Only manager can add lens powers."
    product_list = Product.query.filter(Product.category.contains("Lens")).order_by(Product.name).all()
    if request.method == "POST":
        product = Product.query.get(int(request.form.get("product_id")))
        if product:
            save_or_add_lens_power(product, sph=request.form.get("sph") or "0.00", cyl=request.form.get("cyl") or "", axis=request.form.get("axis") or "", add_power=request.form.get("add_power") or "", quantity=int(request.form.get("quantity") or 0))
            db.session.commit()
        return redirect(url_for("lens_powers"))
    content = """
    <div class="card"><h2>Add Lens Power and Quantity</h2><form method="post"><label>Select Lens Product</label><br><select name="product_id" required>{% for p in product_list %}<option value="{{ p.id }}">{{ p.name }} - {{ p.subcategory }}</option>{% endfor %}</select><br><br><input name="sph" placeholder="SPH e.g. -1.00 or +2.00"><br><br><input name="cyl" placeholder="CYL optional"><br><br><input name="axis" placeholder="AXIS optional"><br><br><input name="add_power" placeholder="ADD e.g. +2.00"><br><br><input name="quantity" type="number" placeholder="Quantity for this power"><br><br><button>Save Lens Power</button></form></div><a class="btn" href="/bulk-generate-powers">Generate Full Power Grid</a><a class="btn" href="/">Back</a>
    """
    return page("Add Lens Power", content, product_list=product_list)


@app.route("/lens-powers")
def lens_powers():
    if not logged_in(): return redirect(url_for("login"))
    power_list = LensPower.query.order_by(LensPower.id.desc()).all() if is_manager() else LensPower.query.filter_by(branch_id=session.get("branch_id")).order_by(LensPower.id.desc()).all()
    products_map = {p.id: p.name for p in Product.query.all()}; branches = {b.id: b.name for b in Branch.query.all()}
    content = """
    <div class="card"><h2>Lens Power Stock</h2><table><tr><th>Branch</th><th>Lens</th><th>SPH</th><th>CYL</th><th>AXIS</th><th>ADD</th><th>Quantity</th>{% if session['role']=='manager' %}<th>Action</th>{% endif %}</tr>
    {% for l in power_list %}<tr><td>{{ branches.get(l.branch_id, '') }}</td><td>{{ products_map.get(l.product_id, '') }}</td><td>{{ l.sph }}</td><td>{{ l.cyl }}</td><td>{{ l.axis }}</td><td>{{ l.add_power }}</td><td>{% if l.quantity <= 2 %}<span class="badge-low">LOW</span> {% endif %}{{ l.quantity }}</td>{% if session['role']=='manager' %}<td><a href="/add-stock/lens/{{ l.id }}">Add Stock</a></td>{% endif %}</tr>{% endfor %}</table></div><a class="btn" href="/">Back</a>
    """
    return page("Lens Powers", content, power_list=power_list, products_map=products_map, branches=branches)


@app.route("/restock")
def restock():
    if not logged_in(): return redirect(url_for("login"))
    if not is_manager(): return "Only manager can restock."
    product_list = Product.query.order_by(Product.name).all(); power_list = LensPower.query.order_by(LensPower.id.desc()).limit(500).all(); products_map = {p.id: p.name for p in Product.query.all()}
    content = """
    <div class="card"><h2>Manager Restock Center</h2><p>Use this page when stock is low or when you receive more of the same items.</p><a class="btn btn-green" href="/bulk-generate-powers">Generate Full Lens Power Grid</a></div>
    <div class="card"><h2>Restock Products</h2><table><tr><th>Product</th><th>Category</th><th>Current Qty</th><th>Action</th></tr>{% for p in product_list %}<tr><td>{{ p.name }}</td><td>{{ p.category }} - {{ p.subcategory }}</td><td>{{ p.quantity }}</td><td><a href="/add-stock/product/{{ p.id }}">Add Stock</a></td></tr>{% endfor %}</table></div>
    <div class="card"><h2>Restock Lens Powers</h2><table><tr><th>Lens</th><th>Power</th><th>Current Qty</th><th>Action</th></tr>{% for l in power_list %}<tr><td>{{ products_map.get(l.product_id, '') }}</td><td>SPH {{ l.sph }} CYL {{ l.cyl }} AXIS {{ l.axis }} ADD {{ l.add_power }}</td><td>{{ l.quantity }}</td><td><a href="/add-stock/lens/{{ l.id }}">Add Stock</a></td></tr>{% endfor %}</table></div><a class="btn" href="/">Back</a>
    """
    return page("Restock", content, product_list=product_list, power_list=power_list, products_map=products_map)


@app.route("/add-stock/product/<int:product_id>", methods=["GET", "POST"])
def add_stock_product(product_id):
    if not logged_in(): return redirect(url_for("login"))
    if not is_manager(): return "Only manager can add stock."
    product = Product.query.get_or_404(product_id)
    if request.method == "POST":
        product.quantity = int(product.quantity or 0) + int(request.form.get("add_quantity") or 0)
        db.session.commit(); return redirect(url_for("products"))
    content = """
    <div class="card"><h2>Add Stock to Existing Product</h2><p><b>Product:</b> {{ product.name }}</p><p><b>Current Quantity:</b> {{ product.quantity }}</p><form method="post"><label>Quantity to Add</label><br><input name="add_quantity" type="number" min="1" required><br><br><button>Add to Stock</button></form></div><a class="btn" href="/products">Back</a>
    """
    return page("Add Product Stock", content, product=product)


@app.route("/add-stock/lens/<int:lens_id>", methods=["GET", "POST"])
def add_stock_lens(lens_id):
    if not logged_in(): return redirect(url_for("login"))
    if not is_manager(): return "Only manager can add lens power stock."
    lens = LensPower.query.get_or_404(lens_id); product = Product.query.get(lens.product_id)
    if request.method == "POST":
        lens.quantity = int(lens.quantity or 0) + int(request.form.get("add_quantity") or 0)
        db.session.commit(); return redirect(url_for("lens_powers"))
    content = """
    <div class="card"><h2>Add Stock to Existing Lens Power</h2><p><b>Lens:</b> {{ product.name if product else '' }}</p><p><b>Power:</b> SPH {{ lens.sph }} CYL {{ lens.cyl }} AXIS {{ lens.axis }} ADD {{ lens.add_power }}</p><p><b>Current Quantity:</b> {{ lens.quantity }}</p><form method="post"><label>Quantity to Add</label><br><input name="add_quantity" type="number" min="1" required><br><br><button>Add to Lens Power Stock</button></form></div><a class="btn" href="/lens-powers">Back</a>
    """
    return page("Add Lens Stock", content, lens=lens, product=product)


@app.route("/bulk-generate-powers", methods=["GET", "POST"])
def bulk_generate_powers():
    if not logged_in(): return redirect(url_for("login"))
    if not is_manager(): return "Only manager can generate lens power grids."
    product_list = Product.query.filter(Product.category.contains("Lens")).order_by(Product.name).all(); message = ""
    if request.method == "POST":
        product = Product.query.get(int(request.form.get("product_id")))
        default_quantity = int(request.form.get("default_quantity") or 0)
        cyl = request.form.get("cyl") or ""; axis = request.form.get("axis") or ""
        if product:
            created, updated = generate_standard_powers(product, default_quantity=default_quantity, cyl=cyl, axis=axis)
            message = "Power grid completed for " + product.name + ". New powers: " + str(created) + ". Existing powers updated: " + str(updated) + ". Quantity added to each power: " + str(default_quantity) + "."
    content = """
    <div class="card"><h2>Generate Standard Lens Power Grid</h2><p>This creates powers automatically in 0.25 steps.</p><ul><li>Single Vision: SPH -20.00 to +20.00, including 0.00.</li><li>Bifocal and Progressive: SPH -3.00 to +3.00, with ADD +1.00 to +3.00.</li></ul>{% if message %}<div class="alert"><b>{{ message }}</b></div>{% endif %}<form method="post"><label>Select Lens Product</label><br><select name="product_id" required>{% for p in product_list %}<option value="{{ p.id }}">{{ p.name }} - {{ p.category }} - {{ p.subcategory }}</option>{% endfor %}</select><br><br><label>Default quantity to add to EACH generated power</label><br><input name="default_quantity" type="number" min="0" value="0" required><br><br><label>CYL optional</label><br><input name="cyl" placeholder="Leave blank unless needed"><br><br><label>AXIS optional</label><br><input name="axis" placeholder="Leave blank unless needed"><br><br><button>Generate / Update Power Grid</button></form></div><a class="btn" href="/">Back</a>
    """
    return page("Generate Power Grid", content, product_list=product_list, message=message)


@app.route("/pos", methods=["GET", "POST"])
def pos():
    if not logged_in(): return redirect(url_for("login"))
    product_list = Product.query.filter(Product.quantity > 0).all() if is_manager() else Product.query.filter(Product.branch_id == session.get("branch_id"), Product.quantity > 0).all()
    if request.method == "POST":
        branch_id = int(request.form.get("branch_id") or session.get("branch_id")); price_type = request.form.get("price_type"); discount = float(request.form.get("discount") or 0); amount_paid = float(request.form.get("amount_paid") or 0); total = 0; selected_items = []
        for product in product_list:
            qty = int(request.form.get("qty_" + str(product.id)) or 0); lens_power_id = request.form.get("lens_" + str(product.id))
            if qty > 0:
                price = product.wholesale_price if price_type == "wholesale" else product.retail_price; subtotal = price * qty; lens_text = ""
                if lens_power_id:
                    lp = LensPower.query.get(int(lens_power_id))
                    if lp:
                        lens_text = "SPH " + str(lp.sph) + " CYL " + str(lp.cyl) + " AXIS " + str(lp.axis) + " ADD " + str(lp.add_power); lp.quantity = max(0, int(lp.quantity or 0) - qty)
                product.quantity = max(0, int(product.quantity or 0) - qty); total += subtotal; selected_items.append((product.name, lens_text, qty, price, subtotal))
        if not selected_items: return page("No Product Selected", "<div class='card'><h2>No Product Selected</h2><p>Please enter quantity for at least one product.</p><a class='btn' href='/pos'>Back</a></div>")
        final_total = total - discount; balance = final_total - amount_paid
        sale = Sale(branch_id=branch_id, customer_name=request.form.get("customer_name"), customer_phone=request.form.get("customer_phone"), total=final_total, discount=discount, amount_paid=amount_paid, balance=balance, payment_method=request.form.get("payment_method"))
        db.session.add(sale); db.session.commit()
        for name, lens_text, qty, price, subtotal in selected_items: db.session.add(SaleItem(sale_id=sale.id, product_name=name, lens_power=lens_text, quantity=qty, unit_price=price, subtotal=subtotal))
        db.session.commit(); return redirect(url_for("receipt", sale_id=sale.id))
    lens_map = {p.id: LensPower.query.filter_by(product_id=p.id).filter(LensPower.quantity > 0).all() for p in product_list}
    content = """
    <div class="card"><h2>Make Sale - Multiple Products</h2><form method="post"><input name="customer_name" placeholder="Customer Name"><br><br><input name="customer_phone" placeholder="Customer Phone"><br><br>{% if session['role'] == 'manager' %}<label>Branch</label><br><select name="branch_id">{% for b in Branch.query.all() %}<option value="{{ b.id }}">{{ b.name }}</option>{% endfor %}</select><br><br>{% endif %}<label>Price Type</label><br><select name="price_type"><option value="retail">Retail / End User</option><option value="wholesale">Wholesale</option></select><br><br><table><tr><th>Product</th><th>Stock</th><th>Lens Power</th><th>Qty</th></tr>{% for p in product_list %}<tr><td>{{ p.name }}<br><small>{{ p.retail_price }} retail / {{ p.wholesale_price }} wholesale</small></td><td>{{ p.quantity }}</td><td><select name="lens_{{ p.id }}"><option value="">No lens power</option>{% for l in lens_map[p.id] %}<option value="{{ l.id }}">SPH {{ l.sph }} CYL {{ l.cyl }} AXIS {{ l.axis }} ADD {{ l.add_power }} | Qty {{ l.quantity }}</option>{% endfor %}</select></td><td><input type="number" name="qty_{{ p.id }}" min="0" value="0"></td></tr>{% endfor %}</table><br><input name="discount" type="number" step="0.01" value="0" placeholder="Discount"><br><br><input name="amount_paid" type="number" step="0.01" placeholder="Amount Paid"><br><br><select name="payment_method"><option>Cash</option><option>Transfer</option><option>POS</option><option>Credit</option></select><br><br><button>Complete Sale</button></form></div><a class="btn" href="/">Back</a>
    """
    return page("POS", content, product_list=product_list, lens_map=lens_map)


@app.route("/receipt/<int:sale_id>")
def receipt(sale_id):
    if not logged_in(): return redirect(url_for("login"))
    sale = Sale.query.get_or_404(sale_id); items = SaleItem.query.filter_by(sale_id=sale.id).all(); branch = Branch.query.get(sale.branch_id)
    content = """
    <div class="card"><h2>Halleluyah Optical Laboratory</h2><h3>Receipt / Invoice</h3><p><b>Branch:</b> {{ branch.name if branch else '' }}</p><p><b>Date:</b> {{ sale.created_at }}</p><p><b>Customer:</b> {{ sale.customer_name }}</p><p><b>Phone:</b> {{ sale.customer_phone }}</p><table><tr><th>Product</th><th>Lens Power</th><th>Qty</th><th>Unit</th><th>Subtotal</th></tr>{% for i in items %}<tr><td>{{ i.product_name }}</td><td>{{ i.lens_power }}</td><td>{{ i.quantity }}</td><td>{{ i.unit_price }}</td><td>{{ i.subtotal }}</td></tr>{% endfor %}</table><p><b>Discount:</b> {{ sale.discount }}</p><p><b>Total:</b> {{ sale.total }}</p><p><b>Amount Paid:</b> {{ sale.amount_paid }}</p><p><b>Balance:</b> {{ sale.balance }}</p><p><b>Payment:</b> {{ sale.payment_method }}</p><button onclick="window.print()">Print Receipt</button></div><a class="btn" href="/">Back</a>
    """
    return page("Receipt", content, sale=sale, items=items, branch=branch)


@app.route("/sales")
def sales():
    if not logged_in(): return redirect(url_for("login"))
    sale_list = Sale.query.order_by(Sale.id.desc()).all() if is_manager() else Sale.query.filter_by(branch_id=session.get("branch_id")).order_by(Sale.id.desc()).all(); branches = {b.id: b.name for b in Branch.query.all()}
    content = """
    <div class="card"><h2>Sales History</h2><table><tr><th>Date</th><th>Branch</th><th>Customer</th><th>Total</th><th>Paid</th><th>Balance</th><th>Receipt</th></tr>{% for s in sale_list %}<tr><td>{{ s.created_at }}</td><td>{{ branches.get(s.branch_id, '') }}</td><td>{{ s.customer_name }}</td><td>{{ s.total }}</td><td>{{ s.amount_paid }}</td><td>{{ s.balance }}</td><td><a href="/receipt/{{ s.id }}">View</a></td></tr>{% endfor %}</table></div><a class="btn" href="/">Back</a>
    """
    return page("Sales", content, sale_list=sale_list, branches=branches)


@app.route("/debtors")
def debtors():
    if not logged_in(): return redirect(url_for("login"))
    debtor_list = Sale.query.filter(Sale.balance > 0).order_by(Sale.id.desc()).all() if is_manager() else Sale.query.filter(Sale.branch_id == session.get("branch_id"), Sale.balance > 0).order_by(Sale.id.desc()).all()
    content = """
    <div class="card"><h2>Debtors</h2><table><tr><th>Date</th><th>Customer</th><th>Phone</th><th>Total</th><th>Paid</th><th>Balance</th></tr>{% for s in debtor_list %}<tr><td>{{ s.created_at }}</td><td>{{ s.customer_name }}</td><td>{{ s.customer_phone }}</td><td>{{ s.total }}</td><td>{{ s.amount_paid }}</td><td>{{ s.balance }}</td></tr>{% endfor %}</table></div><a class="btn" href="/">Back</a>
    """
    return page("Debtors", content, debtor_list=debtor_list)


@app.route("/add-staff", methods=["GET", "POST"])
def add_staff():
    if not logged_in(): return redirect(url_for("login"))
    if not is_manager(): return "Only manager can add staff."
    if request.method == "POST":
        db.session.add(User(username=request.form.get("username"), password_hash=generate_password_hash(request.form.get("password")), role=request.form.get("role"), branch_id=int(request.form.get("branch_id"))))
        db.session.commit(); return redirect(url_for("home"))
    content = """
    <div class="card"><h2>Add Staff / Manager</h2><form method="post"><input name="username" placeholder="Username" required><br><br><input name="password" type="password" placeholder="Password" required><br><br><select name="role"><option value="staff">Staff</option><option value="manager">Manager</option></select><br><br><select name="branch_id">{% for b in branches %}<option value="{{ b.id }}">{{ b.name }}</option>{% endfor %}</select><br><br><button>Create User</button></form></div><a class="btn" href="/">Back</a>
    """
    return page("Add Staff", content, branches=Branch.query.all())


if __name__ == "__main__":
    app.run(debug=True)
