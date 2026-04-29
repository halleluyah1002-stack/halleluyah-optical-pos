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
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "halleluyah-secret-key")

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="staff")


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    subcategory = db.Column(db.String(80))
    retail_price = db.Column(db.Float, default=0)
    wholesale_price = db.Column(db.Float, default=0)
    quantity = db.Column(db.Integer, default=0)


class LensPower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    sph = db.Column(db.String(20))
    cyl = db.Column(db.String(20))
    axis = db.Column(db.String(20))
    add_power = db.Column(db.String(20))
    quantity = db.Column(db.Integer, default=0)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120))
    customer_phone = db.Column(db.String(50))
    product_name = db.Column(db.String(150))
    quantity = db.Column(db.Integer, default=1)
    total = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    amount_paid = db.Column(db.Float, default=0)
    balance = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def login_required():
    return "user_id" in session


def manager_required():
    return session.get("role") == "manager"


@app.before_request
def setup_database():
    db.create_all()

    if not User.query.filter_by(username="manager").first():
        manager = User(
            username="manager",
            password_hash=generate_password_hash("manager123"),
            role="manager"
        )
        db.session.add(manager)
        db.session.commit()


@app.route("/")
def home():
    if not login_required():
        return redirect(url_for("login"))

    products = Product.query.count()
    sales = Sale.query.count()
    debtors = Sale.query.filter(Sale.balance > 0).count()

    return render_template_string("""
    <h1>Halleluyah Optical Laboratory POS</h1>
    <p>Welcome, {{ session['username'] }} | Role: {{ session['role'] }}</p>

    <h3>Dashboard</h3>
    <p>Total Products: {{ products }}</p>
    <p>Total Sales: {{ sales }}</p>
    <p>Total Debtors: {{ debtors }}</p>

    <hr>
    <a href="/products">Products / Stock</a><br>
    <a href="/add-product">Add Product</a><br>
    <a href="/lens-power">Add Lens Power</a><br>
    <a href="/pos">Make Sale</a><br>
    <a href="/sales">Sales History</a><br>
    <a href="/debtors">Debtors</a><br>
    <a href="/add-staff">Add Staff</a><br>
    <a href="/logout">Logout</a>
    """, products=products, sales=sales, debtors=debtors)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("home"))

        error = "Invalid username or password"

    return render_template_string("""
    <h1>Halleluyah Optical Laboratory POS Login</h1>
    <form method="post">
        <label>Username</label><br>
        <input name="username" required><br><br>

        <label>Password</label><br>
        <input name="password" type="password" required><br><br>

        <button type="submit">Login</button>
    </form>

    <p style="color:red;">{{ error }}</p>

    <p>Default Login: manager / manager123</p>
    """, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/add-product", methods=["GET", "POST"])
def add_product():
    if not login_required():
        return redirect(url_for("login"))

    if not manager_required():
        return "Only manager can add products."

    if request.method == "POST":
        product = Product(
            name=request.form.get("name"),
            category=request.form.get("category"),
            subcategory=request.form.get("subcategory"),
            retail_price=float(request.form.get("retail_price") or 0),
            wholesale_price=float(request.form.get("wholesale_price") or 0),
            quantity=int(request.form.get("quantity") or 0)
        )
        db.session.add(product)
        db.session.commit()
        return redirect(url_for("products"))

    return render_template_string("""
    <h1>Add Product / Stock</h1>
    <form method="post">
        <label>Product Name</label><br>
        <input name="name" required><br><br>

        <label>Category</label><br>
        <select name="category">
            <option>Single Vision Lens</option>
            <option>Bifocal Lens</option>
            <option>Progressive Lens</option>
            <option>Frame</option>
            <option>Case</option>
            <option>Lens Cloth</option>
            <option>Liquid Lens Cleaner</option>
            <option>Accessory</option>
        </select><br><br>

        <label>Subcategory</label><br>
        <select name="subcategory">
            <option>White Lens</option>
            <option>Photo AR</option>
            <option>Blue Cut Photo AR</option>
            <option>Metal Frame</option>
            <option>Plastic Frame</option>
            <option>Rimless Frame</option>
            <option>Designer Frame</option>
            <option>Other</option>
        </select><br><br>

        <label>Retail Price ₦</label><br>
        <input name="retail_price" type="number" step="0.01"><br><br>

        <label>Wholesale Price ₦</label><br>
        <input name="wholesale_price" type="number" step="0.01"><br><br>

        <label>Quantity</label><br>
        <input name="quantity" type="number"><br><br>

        <button type="submit">Save Product</button>
    </form>
    <br>
    <a href="/">Back</a>
    """)


@app.route("/products")
def products():
    if not login_required():
        return redirect(url_for("login"))

    products = Product.query.order_by(Product.id.desc()).all()

    return render_template_string("""
    <h1>Products / Stock</h1>
    <a href="/">Back</a>
    <table border="1" cellpadding="8">
        <tr>
            <th>Name</th>
            <th>Category</th>
            <th>Subcategory</th>
            <th>Retail ₦</th>
            <th>Wholesale ₦</th>
            <th>Quantity</th>
        </tr>
        {% for p in products %}
        <tr>
            <td>{{ p.name }}</td>
            <td>{{ p.category }}</td>
            <td>{{ p.subcategory }}</td>
            <td>{{ p.retail_price }}</td>
            <td>{{ p.wholesale_price }}</td>
            <td>{{ p.quantity }}</td>
        </tr>
        {% endfor %}
    </table>
    """, products=products)


@app.route("/lens-power", methods=["GET", "POST"])
def lens_power():
    if not login_required():
        return redirect(url_for("login"))

    if not manager_required():
        return "Only manager can add lens powers."

    products = Product.query.all()

    if request.method == "POST":
        power = LensPower(
            product_id=int(request.form.get("product_id")),
            sph=request.form.get("sph"),
            cyl=request.form.get("cyl"),
            axis=request.form.get("axis"),
            add_power=request.form.get("add_power"),
            quantity=int(request.form.get("quantity") or 0)
        )
        db.session.add(power)
        db.session.commit()
        return redirect(url_for("lens_power"))

    powers = LensPower.query.order_by(LensPower.id.desc()).all()

    return render_template_string("""
    <h1>Add Lens Power</h1>
    <form method="post">
        <label>Select Lens Product</label><br>
        <select name="product_id">
            {% for p in products %}
            <option value="{{ p.id }}">{{ p.name }} - {{ p.subcategory }}</option>
            {% endfor %}
        </select><br><br>

        <label>SPH</label><br>
        <input name="sph"><br><br>

        <label>CYL</label><br>
        <input name="cyl"><br><br>

        <label>AXIS</label><br>
        <input name="axis"><br><br>

        <label>ADD</label><br>
        <input name="add_power"><br><br>

        <label>Quantity</label><br>
        <input name="quantity" type="number"><br><br>

        <button type="submit">Save Lens Power</button>
    </form>

    <hr>
    <h2>Lens Power List</h2>
    <table border="1" cellpadding="8">
        <tr>
            <th>Product ID</th>
            <th>SPH</th>
            <th>CYL</th>
            <th>AXIS</th>
            <th>ADD</th>
            <th>Quantity</th>
        </tr>
        {% for l in powers %}
        <tr>
            <td>{{ l.product_id }}</td>
            <td>{{ l.sph }}</td>
            <td>{{ l.cyl }}</td>
            <td>{{ l.axis }}</td>
            <td>{{ l.add_power }}</td>
            <td>{{ l.quantity }}</td>
        </tr>
        {% endfor %}
    </table>

    <br>
    <a href="/">Back</a>
    """, products=products, powers=powers)


@app.route("/pos", methods=["GET", "POST"])
def pos():
    if not login_required():
        return redirect(url_for("login"))

    products = Product.query.all()

    if request.method == "POST":
        product_id = int(request.form.get("product_id"))
        qty = int(request.form.get("quantity") or 1)
        price_type = request.form.get("price_type")

        product = Product.query.get(product_id)

        price = product.wholesale_price if price_type == "wholesale" else product.retail_price
        subtotal = price * qty
        discount = float(request.form.get("discount") or 0)
        total = subtotal - discount
        amount_paid = float(request.form.get("amount_paid") or 0)
        balance = total - amount_paid

        sale = Sale(
            customer_name=request.form.get("customer_name"),
            customer_phone=request.form.get("customer_phone"),
            product_name=product.name,
            quantity=qty,
            total=total,
            discount=discount,
            amount_paid=amount_paid,
            balance=balance,
            payment_method=request.form.get("payment_method")
        )

        product.quantity = max(0, product.quantity - qty)

        db.session.add(sale)
        db.session.commit()

        return redirect(url_for("receipt", sale_id=sale.id))

    return render_template_string("""
    <h1>POS - Make Sale</h1>
    <form method="post">
        <label>Customer Name</label><br>
        <input name="customer_name"><br><br>

        <label>Customer Phone</label><br>
        <input name="customer_phone"><br><br>

        <label>Product</label><br>
        <select name="product_id">
            {% for p in products %}
            <option value="{{ p.id }}">{{ p.name }} - ₦{{ p.retail_price }} / Stock: {{ p.quantity }}</option>
            {% endfor %}
        </select><br><br>

        <label>Price Type</label><br>
        <select name="price_type">
            <option value="retail">Retail / End User</option>
            <option value="wholesale">Wholesale</option>
        </select><br><br>

        <label>Quantity</label><br>
        <input name="quantity" type="number" value="1"><br><br>

        <label>Discount ₦</label><br>
        <input name="discount" type="number" step="0.01" value="0"><br><br>

        <label>Amount Paid ₦</label><br>
        <input name="amount_paid" type="number" step="0.01"><br><br>

        <label>Payment Method</label><br>
        <select name="payment_method">
            <option>Cash</option>
            <option>Transfer</option>
            <option>POS</option>
            <option>Credit</option>
        </select><br><br>

        <button type="submit">Complete Sale</button>
    </form>

    <br>
    <a href="/">Back</a>
    """, products=products)


@app.route("/receipt/<int:sale_id>")
def receipt(sale_id):
    if not login_required():
        return redirect(url_for("login"))

    sale = Sale.query.get_or_404(sale_id)

    return render_template_string("""
    <h1>Halleluyah Optical Laboratory</h1>
    <h3>Receipt / Invoice</h3>

    <p><b>Date:</b> {{ sale.created_at }}</p>
    <p><b>Customer:</b> {{ sale.customer_name }}</p>
    <p><b>Phone:</b> {{ sale.customer_phone }}</p>
    <p><b>Product:</b> {{ sale.product_name }}</p>
    <p><b>Quantity:</b> {{ sale.quantity }}</p>
    <p><b>Discount:</b> ₦{{ sale.discount }}</p>
    <p><b>Total:</b> ₦{{ sale.total }}</p>
    <p><b>Amount Paid:</b> ₦{{ sale.amount_paid }}</p>
    <p><b>Balance:</b> ₦{{ sale.balance }}</p>
    <p><b>Payment Method:</b> {{ sale.payment_method }}</p>

    <button onclick="window.print()">Print Receipt</button>
    <br><br>
    <a href="/">Back</a>
    """, sale=sale)


@app.route("/sales")
def sales():
    if not login_required():
        return redirect(url_for("login"))

    sales = Sale.query.order_by(Sale.id.desc()).all()

    return render_template_string("""
    <h1>Sales History</h1>
    <a href="/">Back</a>
    <table border="1" cellpadding="8">
        <tr>
            <th>Date</th>
            <th>Customer</th>
            <th>Phone</th>
            <th>Product</th>
            <th>Qty</th>
            <th>Total ₦</th>
            <th>Paid ₦</th>
            <th>Balance ₦</th>
        </tr>
        {% for s in sales %}
        <tr>
            <td>{{ s.created_at }}</td>
            <td>{{ s.customer_name }}</td>
            <td>{{ s.customer_phone }}</td>
            <td>{{ s.product_name }}</td>
            <td>{{ s.quantity }}</td>
            <td>{{ s.total }}</td>
            <td>{{ s.amount_paid }}</td>
            <td>{{ s.balance }}</td>
        </tr>
        {% endfor %}
    </table>
    """, sales=sales)


@app.route("/debtors")
def debtors():
    if not login_required():
        return redirect(url_for("login"))

    debtors = Sale.query.filter(Sale.balance > 0).order_by(Sale.id.desc()).all()

    return render_template_string("""
    <h1>Debtors Record</h1>
    <a href="/">Back</a>
    <table border="1" cellpadding="8">
        <tr>
            <th>Date</th>
            <th>Customer</th>
            <th>Phone</th>
            <th>Product</th>
            <th>Total ₦</th>
            <th>Paid ₦</th>
            <th>Balance ₦</th>
        </tr>
        {% for s in debtors %}
        <tr>
            <td>{{ s.created_at }}</td>
            <td>{{ s.customer_name }}</td>
            <td>{{ s.customer_phone }}</td>
            <td>{{ s.product_name }}</td>
            <td>{{ s.total }}</td>
            <td>{{ s.amount_paid }}</td>
            <td>{{ s.balance }}</td>
        </tr>
        {% endfor %}
    </table>
    """, debtors=debtors)


@app.route("/add-staff", methods=["GET", "POST"])
def add_staff():
    if not login_required():
        return redirect(url_for("login"))

    if not manager_required():
        return "Only manager can add staff."

    if request.method == "POST":
        user = User(
            username=request.form.get("username"),
            password_hash=generate_password_hash(request.form.get("password")),
            role=request.form.get("role")
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("home"))

    return render_template_string("""
    <h1>Add Staff / Manager</h1>
    <form method="post">
        <label>Username</label><br>
        <input name="username" required><br><br>

        <label>Password</label><br>
        <input name="password" type="password" required><br><br>

        <label>Role</label><br>
        <select name="role">
            <option value="staff">Staff</option>
            <option value="manager">Manager</option>
        </select><br><br>

        <button type="submit">Create User</button>
    </form>

    <br>
    <a href="/">Back</a>
    """)


if __name__ == "__main__":
    app.run(debug=True)
