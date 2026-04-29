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
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0)
    subtotal = db.Column(db.Float, default=0)


def logged_in():
    return "user_id" in session


def is_manager():
    return session.get("role") == "manager"


@app.before_request
def setup_database():
    db.create_all()

    if not Branch.query.first():
        branch = Branch(name="Main Branch", address="Sobi Junction, Gambari, Ilorin, Kwara State")
        db.session.add(branch)
        db.session.commit()

    if not User.query.filter_by(username="manager").first():
        main_branch = Branch.query.first()
        manager = User(
            username="manager",
            password_hash=generate_password_hash("manager123"),
            role="manager",
            branch_id=main_branch.id
        )
        db.session.add(manager)
        db.session.commit()


@app.route("/")
def home():
    if not logged_in():
        return redirect(url_for("login"))

    total_products = Product.query.count() if is_manager() else Product.query.filter_by(branch_id=session["branch_id"]).count()
    total_sales = Sale.query.count() if is_manager() else Sale.query.filter_by(branch_id=session["branch_id"]).count()
    debtors = Sale.query.filter(Sale.balance > 0).count() if is_manager() else Sale.query.filter(Sale.branch_id == session["branch_id"], Sale.balance > 0).count()

    return render_template_string("""
    <h1>Halleluyah Optical Laboratory POS</h1>
    <p>Welcome, {{ session['username'] }} | Role: {{ session['role'] }}</p>

    <h3>Dashboard</h3>
    <p>Total Products: {{ total_products }}</p>
    <p>Total Sales: {{ total_sales }}</p>
    <p>Total Debtors: {{ debtors }}</p>

    <hr>
    <a href="/products">Products / Stock</a><br>
    {% if session['role'] == 'manager' %}
    <a href="/add-product">Add Product</a><br>
    <a href="/branches">Branches</a><br>
    <a href="/add-staff">Add Staff</a><br>
    {% endif %}
    <a href="/pos">Make Sale - Multiple Products</a><br>
    <a href="/sales">Sales History</a><br>
    <a href="/debtors">Debtors</a><br>
    <a href="/logout">Logout</a>
    """, total_products=total_products, total_sales=total_sales, debtors=debtors)


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

    return render_template_string("""
    <h1>Halleluyah Optical Laboratory POS Login</h1>
    <form method="post">
        <input name="username" placeholder="Username" required><br><br>
        <input name="password" type="password" placeholder="Password" required><br><br>
        <button type="submit">Login</button>
    </form>
    <p style="color:red;">{{ error }}</p>
    <p>Default: manager / manager123</p>
    """, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/branches", methods=["GET", "POST"])
def branches():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can manage branches."

    if request.method == "POST":
        db.session.add(Branch(name=request.form.get("name"), address=request.form.get("address")))
        db.session.commit()
        return redirect(url_for("branches"))

    branches = Branch.query.all()
    return render_template_string("""
    <h1>Branches</h1>
    <form method="post">
        <input name="name" placeholder="Branch Name" required><br><br>
        <input name="address" placeholder="Address"><br><br>
        <button>Add Branch</button>
    </form>

    <hr>
    <table border="1" cellpadding="8">
    <tr><th>Name</th><th>Address</th></tr>
    {% for b in branches %}
    <tr><td>{{ b.name }}</td><td>{{ b.address }}</td></tr>
    {% endfor %}
    </table>
    <br><a href="/">Back</a>
    """, branches=branches)


@app.route("/add-product", methods=["GET", "POST"])
def add_product():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can add products."

    branches = Branch.query.all()

    if request.method == "POST":
        product = Product(
            branch_id=int(request.form.get("branch_id")),
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
    <h1>Add Product</h1>
    <form method="post">
        <label>Branch</label><br>
        <select name="branch_id">
        {% for b in branches %}
            <option value="{{ b.id }}">{{ b.name }}</option>
        {% endfor %}
        </select><br><br>

        <input name="name" placeholder="Product Name" required><br><br>

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

        <input name="retail_price" type="number" step="0.01" placeholder="Retail Price ₦"><br><br>
        <input name="wholesale_price" type="number" step="0.01" placeholder="Wholesale Price ₦"><br><br>
        <input name="quantity" type="number" placeholder="Quantity"><br><br>

        <button>Save Product</button>
    </form>
    <br><a href="/">Back</a>
    """, branches=branches)


@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can edit products."

    product = Product.query.get_or_404(product_id)
    branches = Branch.query.all()

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

    return render_template_string("""
    <h1>Edit Product</h1>
    <form method="post">
        <label>Branch</label><br>
        <select name="branch_id">
        {% for b in branches %}
            <option value="{{ b.id }}" {% if product.branch_id == b.id %}selected{% endif %}>{{ b.name }}</option>
        {% endfor %}
        </select><br><br>

        <input name="name" value="{{ product.name }}" required><br><br>
        <input name="category" value="{{ product.category }}"><br><br>
        <input name="subcategory" value="{{ product.subcategory }}"><br><br>
        <input name="retail_price" type="number" step="0.01" value="{{ product.retail_price }}"><br><br>
        <input name="wholesale_price" type="number" step="0.01" value="{{ product.wholesale_price }}"><br><br>
        <input name="quantity" type="number" value="{{ product.quantity }}"><br><br>
        <button>Update Product</button>
    </form>
    <br><a href="/products">Back</a>
    """, product=product, branches=branches)


@app.route("/products")
def products():
    if not logged_in():
        return redirect(url_for("login"))

    if is_manager():
        products = Product.query.order_by(Product.id.desc()).all()
    else:
        products = Product.query.filter_by(branch_id=session["branch_id"]).order_by(Product.id.desc()).all()

    branches = {b.id: b.name for b in Branch.query.all()}

    return render_template_string("""
    <h1>Products / Stock</h1>
    <a href="/">Back</a>
    <table border="1" cellpadding="8">
        <tr>
            <th>Branch</th><th>Name</th><th>Category</th><th>Subcategory</th>
            <th>Retail ₦</th><th>Wholesale ₦</th><th>Qty</th>
            {% if session['role'] == 'manager' %}<th>Action</th>{% endif %}
        </tr>
        {% for p in products %}
        <tr>
            <td>{{ branches.get(p.branch_id, '') }}</td>
            <td>{{ p.name }}</td>
            <td>{{ p.category }}</td>
            <td>{{ p.subcategory }}</td>
            <td>{{ p.retail_price }}</td>
            <td>{{ p.wholesale_price }}</td>
            <td>{{ p.quantity }}</td>
            {% if session['role'] == 'manager' %}
            <td><a href="/edit-product/{{ p.id }}">Edit</a></td>
            {% endif %}
        </tr>
        {% endfor %}
    </table>
    """, products=products, branches=branches)


@app.route("/pos", methods=["GET", "POST"])
def pos():
    if not logged_in():
        return redirect(url_for("login"))

    if is_manager():
        products = Product.query.filter(Product.quantity > 0).all()
    else:
        products = Product.query.filter(Product.branch_id == session["branch_id"], Product.quantity > 0).all()

    if request.method == "POST":
        customer_name = request.form.get("customer_name")
        customer_phone = request.form.get("customer_phone")
        price_type = request.form.get("price_type")
        discount = float(request.form.get("discount") or 0)
        amount_paid = float(request.form.get("amount_paid") or 0)
        payment_method = request.form.get("payment_method")
        branch_id = int(request.form.get("branch_id") or session["branch_id"])

        total = 0
        selected_items = []

        for product in products:
            qty = int(request.form.get(f"qty_{product.id}") or 0)
            if qty > 0:
                price = product.wholesale_price if price_type == "wholesale" else product.retail_price
                subtotal = price * qty
                total += subtotal
                selected_items.append((product, qty, price, subtotal))

        if not selected_items:
            return "Please enter quantity for at least one product. <br><br><a href='/pos'>Back</a>"

        final_total = total - discount
        balance = final_total - amount_paid

        sale = Sale(
            branch_id=branch_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            total=final_total,
            discount=discount,
            amount_paid=amount_paid,
            balance=balance,
            payment_method=payment_method
        )
        db.session.add(sale)
        db.session.commit()

        for product, qty, price, subtotal in selected_items:
            item = SaleItem(
                sale_id=sale.id,
                product_name=product.name,
                quantity=qty,
                unit_price=price,
                subtotal=subtotal
            )
            product.quantity = max(0, product.quantity - qty)
            db.session.add(item)

        db.session.commit()
        return redirect(url_for("receipt", sale_id=sale.id))

    branches = Branch.query.all()

    return render_template_string("""
    <h1>Make Sale - Multiple Products</h1>
    <form method="post">
        <input name="customer_name" placeholder="Customer Name"><br><br>
        <input name="customer_phone" placeholder="Customer Phone"><br><br>

        {% if session['role'] == 'manager' %}
        <label>Branch</label><br>
        <select name="branch_id">
        {% for b in branches %}
            <option value="{{ b.id }}">{{ b.name }}</option>
        {% endfor %}
        </select><br><br>
        {% else %}
        <input type="hidden" name="branch_id" value="{{ session['branch_id'] }}">
        {% endif %}

        <label>Price Type</label><br>
        <select name="price_type">
            <option value="retail">Retail / End User</option>
            <option value="wholesale">Wholesale</option>
        </select><br><br>

        <h3>Select Products</h3>
        <table border="1" cellpadding="8">
            <tr>
                <th>Product</th><th>Category</th><th>Retail ₦</th><th>Wholesale ₦</th><th>Stock</th><th>Qty to Sell</th>
            </tr>
            {% for p in products %}
            <tr>
                <td>{{ p.name }}</td>
                <td>{{ p.category }} - {{ p.subcategory }}</td>
                <td>{{ p.retail_price }}</td>
                <td>{{ p.wholesale_price }}</td>
                <td>{{ p.quantity }}</td>
                <td><input type="number" name="qty_{{ p.id }}" min="0" value="0"></td>
            </tr>
            {% endfor %}
        </table>

        <br>
        <input name="discount" type="number" step="0.01" value="0" placeholder="Discount ₦"><br><br>
        <input name="amount_paid" type="number" step="0.01" placeholder="Amount Paid ₦"><br><br>

        <select name="payment_method">
            <option>Cash</option>
            <option>Transfer</option>
            <option>POS</option>
            <option>Credit</option>
        </select><br><br>

        <button>Complete Sale</button>
    </form>
    <br><a href="/">Back</a>
    """, products=products, branches=branches)


@app.route("/receipt/<int:sale_id>")
def receipt(sale_id):
    if not logged_in():
        return redirect(url_for("login"))

    sale = Sale.query.get_or_404(sale_id)
    items = SaleItem.query.filter_by(sale_id=sale.id).all()
    branch = Branch.query.get(sale.branch_id)

    return render_template_string("""
    <h1>Halleluyah Optical Laboratory</h1>
    <h3>Receipt / Invoice</h3>

    <p><b>Branch:</b> {{ branch.name if branch else '' }}</p>
    <p><b>Date:</b> {{ sale.created_at }}</p>
    <p><b>Customer:</b> {{ sale.customer_name }}</p>
    <p><b>Phone:</b> {{ sale.customer_phone }}</p>

    <table border="1" cellpadding="8">
        <tr><th>Product</th><th>Qty</th><th>Unit ₦</th><th>Subtotal ₦</th></tr>
        {% for i in items %}
        <tr>
            <td>{{ i.product_name }}</td>
            <td>{{ i.quantity }}</td>
            <td>{{ i.unit_price }}</td>
            <td>{{ i.subtotal }}</td>
        </tr>
        {% endfor %}
    </table>

    <p><b>Discount:</b> ₦{{ sale.discount }}</p>
    <p><b>Total:</b> ₦{{ sale.total }}</p>
    <p><b>Amount Paid:</b> ₦{{ sale.amount_paid }}</p>
    <p><b>Balance:</b> ₦{{ sale.balance }}</p>
    <p><b>Payment:</b> {{ sale.payment_method }}</p>

    <button onclick="window.print()">Print Receipt</button>
    <br><br><a href="/">Back</a>
    """, sale=sale, items=items, branch=branch)


@app.route("/sales")
def sales():
    if not logged_in():
        return redirect(url_for("login"))

    sales = Sale.query.order_by(Sale.id.desc()).all() if is_manager() else Sale.query.filter_by(branch_id=session["branch_id"]).order_by(Sale.id.desc()).all()
    branches = {b.id: b.name for b in Branch.query.all()}

    return render_template_string("""
    <h1>Sales History</h1>
    <a href="/">Back</a>
    <table border="1" cellpadding="8">
        <tr><th>Date</th><th>Branch</th><th>Customer</th><th>Total ₦</th><th>Paid ₦</th><th>Balance ₦</th><th>Receipt</th></tr>
        {% for s in sales %}
        <tr>
            <td>{{ s.created_at }}</td>
            <td>{{ branches.get(s.branch_id, '') }}</td>
            <td>{{ s.customer_name }}</td>
            <td>{{ s.total }}</td>
            <td>{{ s.amount_paid }}</td>
            <td>{{ s.balance }}</td>
            <td><a href="/receipt/{{ s.id }}">View</a></td>
        </tr>
        {% endfor %}
    </table>
    """, sales=sales, branches=branches)


@app.route("/debtors")
def debtors():
    if not logged_in():
        return redirect(url_for("login"))

    debtors = Sale.query.filter(Sale.balance > 0).order_by(Sale.id.desc()).all() if is_manager() else Sale.query.filter(Sale.branch_id == session["branch_id"], Sale.balance > 0).order_by(Sale.id.desc()).all()

    return render_template_string("""
    <h1>Debtors</h1>
    <a href="/">Back</a>
    <table border="1" cellpadding="8">
        <tr><th>Date</th><th>Customer</th><th>Phone</th><th>Total ₦</th><th>Paid ₦</th><th>Balance ₦</th></tr>
        {% for s in debtors %}
        <tr>
            <td>{{ s.created_at }}</td>
            <td>{{ s.customer_name }}</td>
            <td>{{ s.customer_phone }}</td>
            <td>{{ s.total }}</td>
            <td>{{ s.amount_paid }}</td>
            <td>{{ s.balance }}</td>
        </tr>
        {% endfor %}
    </table>
    """, debtors=debtors)


@app.route("/add-staff", methods=["GET", "POST"])
def add_staff():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can add staff."

    branches = Branch.query.all()

    if request.method == "POST":
        user = User(
            username=request.form.get("username"),
            password_hash=generate_password_hash(request.form.get("password")),
            role=request.form.get("role"),
            branch_id=int(request.form.get("branch_id"))
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("home"))

    return render_template_string("""
    <h1>Add Staff / Manager</h1>
    <form method="post">
        <input name="username" placeholder="Username" required><br><br>
        <input name="password" type="password" placeholder="Password" required><br><br>

        <select name="role">
            <option value="staff">Staff</option>
            <option value="manager">Manager</option>
        </select><br><br>

        <label>Branch</label><br>
        <select name="branch_id">
        {% for b in branches %}
            <option value="{{ b.id }}">{{ b.name }}</option>
        {% endfor %}
        </select><br><br>

        <button>Create User</button>
    </form>
    <br><a href="/">Back</a>
    """, branches=branches)


if __name__ == "__main__":
    app.run(debug=True)
