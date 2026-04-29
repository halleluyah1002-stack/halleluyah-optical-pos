import os
from datetime import datetime, date
from functools import wraps
from decimal import Decimal
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-secret-key')
db_url = os.getenv('DATABASE_URL', 'sqlite:///halleluyah_pos.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    address = db.Column(db.String(255), default='')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    branch = db.relationship('Branch')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # lens, frame, case, cloth, cleaner, accessory
    subcategory = db.Column(db.String(80), default='')
    lens_type = db.Column(db.String(80), default='')  # SV, Bifocal, Progressive
    lens_material = db.Column(db.String(80), default='') # White, Photo AR, Blue Cut Photo AR
    frame_type = db.Column(db.String(80), default='') # metal, plastic, rimless, designer
    retail_price = db.Column(db.Numeric(12,2), default=0)
    wholesale_price = db.Column(db.Numeric(12,2), default=0)
    low_stock = db.Column(db.Integer, default=2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    product = db.relationship('Product')
    branch = db.relationship('Branch')
    __table_args__ = (db.UniqueConstraint('product_id','branch_id', name='uq_stock_product_branch'),)

class LensPower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    sph = db.Column(db.String(20), default='')
    cyl = db.Column(db.String(20), default='')
    axis = db.Column(db.String(10), default='')
    add = db.Column(db.String(20), default='')
    quantity = db.Column(db.Integer, default=0)
    product = db.relationship('Product')
    branch = db.relationship('Branch')
    __table_args__ = (db.UniqueConstraint('product_id','branch_id','sph','cyl','axis','add', name='uq_lens_power'),)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(80), default='')
    address = db.Column(db.String(255), default='')

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(40), unique=True, nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    customer_name = db.Column(db.String(160), default='Walk-in Customer')
    subtotal = db.Column(db.Numeric(12,2), default=0)
    discount = db.Column(db.Numeric(12,2), default=0)
    total = db.Column(db.Numeric(12,2), default=0)
    amount_paid = db.Column(db.Numeric(12,2), default=0)
    balance = db.Column(db.Numeric(12,2), default=0)
    payment_method = db.Column(db.String(50), default='Cash')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    branch = db.relationship('Branch')
    user = db.relationship('User')
    customer = db.relationship('Customer')

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    lens_power_id = db.Column(db.Integer, db.ForeignKey('lens_power.id'))
    qty = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(12,2), default=0)
    line_total = db.Column(db.Numeric(12,2), default=0)
    product = db.relationship('Product')
    lens_power = db.relationship('LensPower')
    sale = db.relationship('Sale', backref='items')

def money(v):
    try: return f"₦{float(v):,.2f}"
    except Exception: return "₦0.00"
app.jinja_env.filters['money'] = money

def current_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user(): return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper

def manager_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u=current_user()
        if not u or u.role != 'manager':
            flash('Manager permission required.', 'danger')
            return redirect(url_for('dashboard'))
        return fn(*args, **kwargs)
    return wrapper

@app.before_request
def setup_db():
    if not getattr(app, '_db_ready', False):
        db.create_all()
        if not Branch.query.first():
            main=Branch(name='Main Branch', address='Sobi Junction, Gambari, Ilorin, Kwara State')
            db.session.add(main); db.session.commit()
        if not User.query.filter_by(username='manager').first():
            db.session.add(User(username='manager', password_hash=generate_password_hash('manager123'), role='manager', branch_id=1))
            db.session.commit()
        app._db_ready=True

@app.route('/')
def index(): return redirect(url_for('dashboard') if current_user() else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        user=User.query.filter_by(username=request.form['username'].strip()).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            session['user_id']=user.id
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    u=current_user()
    branch_id = u.branch_id if u.role!='manager' else request.args.get('branch_id', u.branch_id, type=int)
    today_start=datetime.combine(date.today(), datetime.min.time())
    sales_q=Sale.query.filter(Sale.created_at>=today_start)
    if branch_id: sales_q=sales_q.filter_by(branch_id=branch_id)
    sales=sales_q.all()
    total=sum(float(s.total) for s in sales); paid=sum(float(s.amount_paid) for s in sales); balance=sum(float(s.balance) for s in sales)
    debtors=Sale.query.filter(Sale.balance>0).order_by(Sale.created_at.desc()).limit(10).all()
    low=[]
    for st in Stock.query.all():
        if st.quantity <= st.product.low_stock: low.append((st.product.name, st.branch.name, st.quantity))
    for lp in LensPower.query.filter(LensPower.quantity<=2).limit(15).all():
        low.append((f"{lp.product.name} SPH {lp.sph} CYL {lp.cyl} AXIS {lp.axis} ADD {lp.add}", lp.branch.name, lp.quantity))
    return render_template('dashboard.html', u=u, total=total, paid=paid, balance=balance, debtors=debtors, low=low, branches=Branch.query.all())

@app.route('/products')
@login_required
def products():
    return render_template('products.html', products=Product.query.order_by(Product.category, Product.name).all(), u=current_user())

@app.route('/products/add', methods=['GET','POST'])
@login_required
@manager_required
def add_product():
    if request.method=='POST':
        p=Product(name=request.form['name'], category=request.form['category'], subcategory=request.form.get('subcategory',''), lens_type=request.form.get('lens_type',''), lens_material=request.form.get('lens_material',''), frame_type=request.form.get('frame_type',''), retail_price=Decimal(request.form.get('retail_price') or 0), wholesale_price=Decimal(request.form.get('wholesale_price') or 0), low_stock=int(request.form.get('low_stock') or 2))
        db.session.add(p); db.session.commit(); flash('Product added.', 'success'); return redirect(url_for('products'))
    return render_template('product_form.html')

@app.route('/stock', methods=['GET','POST'])
@login_required
@manager_required
def stock():
    if request.method=='POST':
        product_id=int(request.form['product_id']); branch_id=int(request.form['branch_id']); qty=int(request.form['quantity'])
        st=Stock.query.filter_by(product_id=product_id, branch_id=branch_id).first()
        if not st: st=Stock(product_id=product_id, branch_id=branch_id, quantity=0); db.session.add(st)
        st.quantity += qty; db.session.commit(); flash('Stock updated.', 'success'); return redirect(url_for('stock'))
    return render_template('stock.html', products=Product.query.all(), branches=Branch.query.all(), stocks=Stock.query.all())

@app.route('/lens-powers', methods=['GET','POST'])
@login_required
@manager_required
def lens_powers():
    if request.method=='POST':
        lp=LensPower.query.filter_by(product_id=int(request.form['product_id']), branch_id=int(request.form['branch_id']), sph=request.form.get('sph',''), cyl=request.form.get('cyl',''), axis=request.form.get('axis',''), add=request.form.get('add','')).first()
        if not lp:
            lp=LensPower(product_id=int(request.form['product_id']), branch_id=int(request.form['branch_id']), sph=request.form.get('sph',''), cyl=request.form.get('cyl',''), axis=request.form.get('axis',''), add=request.form.get('add',''), quantity=0)
            db.session.add(lp)
        lp.quantity += int(request.form.get('quantity') or 0); db.session.commit(); flash('Lens power quantity updated.', 'success'); return redirect(url_for('lens_powers'))
    return render_template('lens_powers.html', products=Product.query.filter_by(category='lens').all(), branches=Branch.query.all(), powers=LensPower.query.order_by(LensPower.product_id).all())

@app.route('/branches', methods=['GET','POST'])
@login_required
@manager_required
def branches():
    if request.method=='POST':
        db.session.add(Branch(name=request.form['name'], address=request.form.get('address',''))); db.session.commit(); flash('Branch added.', 'success')
    return render_template('branches.html', branches=Branch.query.all())

@app.route('/staff', methods=['GET','POST'])
@login_required
@manager_required
def staff():
    if request.method=='POST':
        db.session.add(User(username=request.form['username'], password_hash=generate_password_hash(request.form['password']), role=request.form['role'], branch_id=int(request.form['branch_id']))); db.session.commit(); flash('Staff account created.', 'success')
    return render_template('staff.html', users=User.query.all(), branches=Branch.query.all())

@app.route('/pos', methods=['GET','POST'])
@login_required
def pos():
    u=current_user(); branch_id=u.branch_id
    if request.method=='POST':
        customer_name=request.form.get('customer_name') or 'Walk-in Customer'
        customer=Customer(name=customer_name, phone=request.form.get('phone',''), address=request.form.get('address',''))
        db.session.add(customer); db.session.flush()
        product_ids=request.form.getlist('product_id[]'); power_ids=request.form.getlist('lens_power_id[]'); qtys=request.form.getlist('qty[]'); prices=request.form.getlist('unit_price[]')
        subtotal=Decimal('0')
        sale=Sale(invoice_no='HOL-'+datetime.utcnow().strftime('%Y%m%d%H%M%S'), branch_id=branch_id, user_id=u.id, customer_id=customer.id, customer_name=customer_name, payment_method=request.form.get('payment_method','Cash'))
        db.session.add(sale); db.session.flush()
        for i,pid in enumerate(product_ids):
            if not pid: continue
            qty=int(qtys[i] or 1); price=Decimal(prices[i] or 0); line=qty*price; subtotal += line
            power_id=int(power_ids[i]) if power_ids[i] else None
            product=Product.query.get(int(pid))
            if power_id:
                lp=LensPower.query.get(power_id)
                if not lp or lp.quantity < qty: raise ValueError('Not enough lens power stock')
                lp.quantity -= qty
            else:
                st=Stock.query.filter_by(product_id=int(pid), branch_id=branch_id).first()
                if st and st.quantity >= qty: st.quantity -= qty
            db.session.add(SaleItem(sale_id=sale.id, product_id=int(pid), lens_power_id=power_id, qty=qty, unit_price=price, line_total=line))
        discount=Decimal(request.form.get('discount') or 0); paid=Decimal(request.form.get('amount_paid') or 0)
        total=max(Decimal('0'), subtotal-discount)
        sale.subtotal=subtotal; sale.discount=discount; sale.total=total; sale.amount_paid=paid; sale.balance=max(Decimal('0'), total-paid)
        db.session.commit(); flash(f'Sale saved. Invoice {sale.invoice_no}', 'success'); return redirect(url_for('receipt', sale_id=sale.id))
    return render_template('pos.html', products=Product.query.order_by(Product.name).all(), powers=LensPower.query.filter_by(branch_id=branch_id).all())

@app.route('/receipt/<int:sale_id>')
@login_required
def receipt(sale_id):
    return render_template('receipt.html', sale=Sale.query.get_or_404(sale_id))

@app.route('/sales')
@login_required
def sales():
    u=current_user(); q=Sale.query.order_by(Sale.created_at.desc())
    if u.role!='manager': q=q.filter_by(branch_id=u.branch_id)
    return render_template('sales.html', sales=q.limit(300).all())

@app.route('/debtors')
@login_required
def debtors():
    u=current_user(); q=Sale.query.filter(Sale.balance>0).order_by(Sale.created_at.desc())
    if u.role!='manager': q=q.filter_by(branch_id=u.branch_id)
    return render_template('debtors.html', sales=q.all())

@app.route('/api/powers/<int:product_id>')
@login_required
def api_powers(product_id):
    u=current_user()
    powers=LensPower.query.filter_by(product_id=product_id, branch_id=u.branch_id).filter(LensPower.quantity>0).all()
    return jsonify([{'id':p.id,'label':f'SPH {p.sph} CYL {p.cyl} AXIS {p.axis} ADD {p.add} - Qty {p.quantity}'} for p in powers])

@app.route('/backup')
@login_required
@manager_required
def backup():
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
        path=os.path.join(app.instance_path, 'halleluyah_pos.db')
        return send_file(path, as_attachment=True) if os.path.exists(path) else ('No local database file found', 404)
    return 'Render PostgreSQL backups are managed from your Render dashboard.', 200

if __name__ == '__main__':
    app.run(debug=True)
