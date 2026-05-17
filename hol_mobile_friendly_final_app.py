import os
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from flask import Flask, request, redirect, url_for, session, render_template_string, Response
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
    attended_by_id = db.Column(db.Integer, db.ForeignKey("hol_user.id"))
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
    office_name = db.Column(db.String(180), default="HALLELUYAH OPTICAL LABORATORY")
    phone = db.Column(db.String(80), default="")
    address = db.Column(db.String(255), default="Sobi Junction, Gambari, Ilorin, Kwara State")
    theme = db.Column(db.String(20), default="light")
    manager_pin_hash = db.Column(db.String(255), default="")


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
    processed_by_id = db.Column(db.Integer, db.ForeignKey("hol_user.id"))


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


class AuditLog(db.Model):
    __tablename__ = "hol_audit_log"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("hol_user.id"))
    branch_id = db.Column(db.Integer, db.ForeignKey("hol_branch.id"))
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def logged_in():
    return "user_id" in session


def is_manager():
    return session.get("role") == "manager"


def audit_log(action, details=""):
    try:
        db.session.add(AuditLog(
            user_id=session.get("user_id"),
            branch_id=session.get("branch_id"),
            action=action,
            details=details
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()


def check_manager_pin(pin):
    setting = OfficeSetting.query.first()
    saved_hash = getattr(setting, "manager_pin_hash", "") if setting else ""
    if not saved_hash:
        # First-time default security PIN. Manager should change it in Security Settings.
        return pin == "1234"
    return check_password_hash(saved_hash, pin or "")


def require_manager_pin_from_form():
    if not is_manager():
        return False
    return check_manager_pin(request.form.get("manager_pin"))


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
:root{
    --primary:#0b4f86;--primary-dark:#073763;--sidebar:#062f56;--sidebar2:#074b7b;
    --success:#16a34a;--danger:#dc2626;--warning:#f59e0b;--purple:#7c3aed;
    --gray:#475569;--muted:#64748b;--bg:#f4f7fb;--card:#ffffff;--border:#dbe4ee;--ink:#0f172a;
}
*{box-sizing:border-box}
body{margin:0;font-family:Arial,Helvetica,sans-serif;background:var(--bg);color:var(--ink)}
a{text-decoration:none}.small{font-size:13px;color:var(--muted)}
/* ===== APP SHELL / BETTER ARRANGEMENT ===== */
.app-layout{min-height:100vh;display:grid;grid-template-columns:280px minmax(0,1fr);background:var(--bg)}
.sidebar{position:sticky;top:0;height:100vh;background:linear-gradient(180deg,var(--sidebar),#031d36);color:white;padding:18px 14px;overflow-y:auto;box-shadow:8px 0 24px #00000014;z-index:20}
.brand-block{display:flex;gap:12px;align-items:center;padding:8px 8px 18px;border-bottom:1px solid rgba(255,255,255,.15);margin-bottom:14px}
.brand-logo{width:42px;height:42px;border-radius:14px;background:rgba(255,255,255,.12);display:flex;align-items:center;justify-content:center;font-size:25px}
.brand-title{font-size:17px;font-weight:900;line-height:1.05;letter-spacing:.4px}.brand-subtitle{font-size:11px;opacity:.82;margin-top:4px}
.nav-group-title{font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:.09em;color:#bfdbfe;margin:17px 10px 7px}.nav-section{display:flex;flex-direction:column;gap:3px;margin-bottom:6px}
nav a,.btn{display:flex;align-items:center;gap:9px;background:transparent;color:white;padding:10px 11px;border-radius:11px;text-decoration:none;font-size:14px;font-weight:700;line-height:1.15;transition:.18s;border:0;min-height:38px}
nav a:hover,.btn:hover{background:rgba(255,255,255,.12);transform:translateX(3px)}
nav a.active,.btn-green{background:var(--success)!important;color:white!important}.btn-red{background:var(--danger)!important;color:white!important}.btn-gold{background:var(--warning)!important;color:white!important}.btn-gray{background:rgba(255,255,255,.14)!important;color:white!important}.btn-purple{background:var(--purple)!important;color:white!important}.btn-blue{background:var(--primary)!important;color:white!important}
.logout-wrap{border-top:1px solid rgba(255,255,255,.15);margin-top:14px;padding-top:12px}
.main-area{min-width:0}.topbar{height:72px;background:white;border-bottom:1px solid #e2e8f0;display:flex;align-items:center;justify-content:space-between;padding:0 24px;position:sticky;top:0;z-index:10;box-shadow:0 2px 10px #00000008}.topbar h1{margin:0;font-size:22px}.topbar-right{display:flex;gap:12px;align-items:center}.pill{border:1px solid #dbe4ee;border-radius:12px;padding:10px 14px;background:#f8fafc;font-weight:700;color:#0f172a}.container{padding:24px;max-width:1500px;margin:0 auto}.header{display:none}
/* ===== GENERAL UI ===== */
.card{background:var(--card);border-radius:18px;padding:20px;margin-bottom:18px;box-shadow:0 4px 18px #0000000d;border:1px solid #eef2f7}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}.stat{background:linear-gradient(135deg,#fff,#eaf6ff);border-left:6px solid var(--primary)}.stat h1{margin:10px 0 0;font-size:36px}
input,select,textarea{padding:12px;width:100%;max-width:450px;border:1px solid #cbd5e1;border-radius:10px;margin-top:5px;background:white;font-size:14px}input:focus,select:focus,textarea:focus{outline:none;border-color:#0077b6;box-shadow:0 0 0 3px rgba(0,119,182,.15)}button{background:var(--primary);color:white;border:0;padding:12px 18px;border-radius:10px;cursor:pointer;font-weight:700;transition:.18s}button:hover{opacity:.94;transform:translateY(-1px)}
table{width:100%;border-collapse:collapse;background:white}th{background:var(--primary-dark);color:white}td,th{padding:10px;border:1px solid #e2e8f0;text-align:left;vertical-align:top}.alert{background:#fff7d6;border-left:6px solid var(--warning);padding:14px;border-radius:10px;margin-bottom:15px}.danger{background:#ffe5e5;border-left:6px solid var(--danger)}.success{background:#e8fff2;border-left:6px solid var(--success)}.badge-low{background:var(--danger);color:white;border-radius:12px;padding:3px 8px;font-size:12px}.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}
/* ===== PROFESSIONAL POS ===== */
.sales-layout{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(360px,.9fr);gap:22px;align-items:start}.checkout-panel{position:sticky;top:92px;align-self:start}.current-sale-box{max-height:420px;overflow-y:auto;overflow-x:hidden;border-radius:16px;padding-right:6px}.cart-table-wrap{max-height:260px;overflow-y:auto;border:1px solid #dbe4ee;border-radius:12px}.cart-table-wrap table{margin:0}.checkout-card{border:2px solid var(--success);background:#fbfffc}.checkout-card input,.checkout-card select{max-width:100%}.complete-sale-btn{width:100%;font-size:17px;padding:15px;background:var(--success);position:sticky;bottom:0}.quick-summary{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:10px 0 14px}.quick-summary .mini-card{background:#eef6ff;padding:10px;border-radius:12px;text-align:center;font-weight:700}.step-box{border:1px solid #e2e8f0;border-radius:16px;padding:18px;margin-bottom:18px;background:white}.selection-grid{display:flex;flex-wrap:wrap;gap:12px}.selection-btn{border:none;border-radius:14px;padding:16px 22px;min-width:160px;font-weight:bold;cursor:pointer;transition:.2s;color:white}.product-card{border:1px solid #e2e8f0;border-radius:16px;padding:18px;background:white;transition:.2s}.product-card:hover,.pos-item-card:hover{box-shadow:0 6px 20px #00000012}.pos-card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:15px}.pos-item-card{border:1px solid #dbe4ee;border-radius:16px;padding:16px;background:#fff;box-shadow:0 3px 10px #00000008}.floating-cart{border:2px solid #198754;background:#f8fff9}.cart-remove{padding:6px 10px;min-height:auto}.form-grid{display:grid;grid-template-columns:1fr;gap:8px}.cart-total-line{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}.pos-big-btn{display:block;color:white;padding:26px;border-radius:18px;text-decoration:none;font-size:22px;font-weight:bold;text-align:center;box-shadow:0 6px 18px #0002;min-height:90px}.pos-small-btn{display:inline-flex;align-items:center;justify-content:center;padding:14px 19px;border-radius:14px;text-decoration:none;margin:5px;font-weight:bold;background:#e8eef5;color:#0f172a}.pos-small-btn.active{background:#003366;color:white}
::-webkit-scrollbar{width:8px;height:8px}::-webkit-scrollbar-thumb{background:#94a3b8;border-radius:10px}.thermal-receipt{max-width:320px;margin:auto;font-family:Arial,monospace;font-size:12px;color:#000;background:white}.thermal-receipt table{font-size:11px}.thermal-receipt hr{border:0;border-top:1px dashed #000}
/* ===== DARK MODE ===== */
.dark{background:#0f172a;color:#e5e7eb;min-height:100vh}.dark .main-area,.dark .container{background:#0f172a}.dark .topbar,.dark .card{background:#111827;color:#e5e7eb;border-color:#1f2937}.dark table{background:#111827}.dark td{border-color:#374151}.dark input,.dark select,.dark textarea{background:#0b1220;color:#e5e7eb;border-color:#475569}.dark .small{color:#cbd5e1}.dark .stat{background:#111827}.dark .checkout-card{background:#0b1220}.dark .cart-table-wrap{border-color:#334155}.dark .quick-summary .mini-card{background:#172554}.dark .pill{background:#0b1220;color:#e5e7eb;border-color:#334155}
/* ===== RESPONSIVE ===== */
.mobile-nav-toggle{display:none}
@media(max-width:1100px){.app-layout{grid-template-columns:1fr}.sidebar{position:relative;height:auto;border-radius:0}.brand-block{padding-bottom:12px}.nav-section{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}.topbar{position:relative}.sales-layout{grid-template-columns:1fr}.checkout-panel{position:relative;top:auto}.current-sale-box{max-height:340px}}
@media(max-width:620px){.container{padding:12px}.card{padding:14px}.topbar{height:auto;padding:14px;align-items:flex-start;gap:8px;flex-direction:column}.topbar h1{font-size:18px}.topbar-right{flex-wrap:wrap}.nav-section{grid-template-columns:1fr}.quick-summary{grid-template-columns:1fr}.cart-table-wrap{max-height:220px}.pos-big-btn{font-size:18px;padding:20px}.sales-layout{gap:14px}}
@media print{.sidebar,.topbar,nav,.btn,button,.no-print{display:none!important}.app-layout{display:block}.card{box-shadow:none;border:0}body{background:white}.container{padding:0}.thermal-receipt{max-width:80mm}.thermal-receipt *{color:#000!important}}


/* ===== PHONE PROFESSIONAL + DARK MODE FINAL FIX ===== */
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{overflow-x:hidden}
img,table{max-width:100%}
.table-responsive{width:100%;overflow-x:auto}
.card table{display:table;width:100%}

/* Make every sales section readable and aligned */
.sales-left{min-width:0}.checkout-panel{min-width:0}.card,.pos-item-card,.product-card,.step-box{min-width:0}.pos-card-grid{grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}
.pos-big-btn{display:flex!important;flex-direction:column;align-items:center;justify-content:center;gap:4px;word-break:normal;line-height:1.15}.pos-small-btn{min-width:145px;text-align:center}.pos-item-card select,.pos-item-card input,.checkout-card input,.checkout-card select{max-width:100%}
.cart-table-wrap{overflow:auto}.cart-table-wrap table{min-width:430px}.cart-remove{display:inline-flex!important;align-items:center;justify-content:center}

/* Cleaner dark mode for every card, field, alert and POS control */
.dark{--bg:#0f172a;--card:#111827;--ink:#e5e7eb;--border:#334155;--muted:#cbd5e1;background:#0f172a;color:#e5e7eb}.dark .app-layout,.dark .main-area,.dark .container{background:#0f172a;color:#e5e7eb}.dark .topbar,.dark .card,.dark .step-box,.dark .product-card,.dark .pos-item-card,.dark .checkout-card,.dark .floating-cart{background:#111827!important;color:#e5e7eb!important;border-color:#334155!important}.dark .topbar{box-shadow:0 2px 12px #0007}.dark h1,.dark h2,.dark h3,.dark h4,.dark label,.dark p,.dark div,.dark span{color:inherit}.dark .small{color:#cbd5e1!important}.dark input,.dark select,.dark textarea{background:#0b1220!important;color:#f8fafc!important;border-color:#475569!important}.dark input::placeholder,.dark textarea::placeholder{color:#94a3b8!important}.dark option{background:#0b1220;color:#f8fafc}.dark table{background:#111827!important;color:#e5e7eb!important}.dark th{background:#0b3b66!important;color:#ffffff!important}.dark td{background:#111827!important;color:#e5e7eb!important;border-color:#334155!important}.dark .pos-small-btn{background:#1e293b!important;color:#e5e7eb!important;border:1px solid #334155}.dark .pos-small-btn.active{background:#2563eb!important;color:white!important}.dark .quick-summary .mini-card{background:#172554!important;color:#dbeafe!important}.dark .pill{background:#0b1220!important;color:#e5e7eb!important;border-color:#334155!important}.dark .alert{background:#422006!important;color:#fde68a!important;border-left-color:#f59e0b!important}.dark .success{background:#052e16!important;color:#bbf7d0!important;border-left-color:#22c55e!important}.dark .danger{background:#450a0a!important;color:#fecaca!important;border-left-color:#ef4444!important}.dark .badge-low{background:#dc2626!important;color:white!important}.dark [style*="background:#f8fafc"],.dark [style*="background:#eef6ff"],.dark [style*="background:#eaf6ff"],.dark [style*="background:white"],.dark [style*="background:#fff"]{background:#111827!important;color:#e5e7eb!important}.dark [style*="color:#0f172a"],.dark [style*="color:black"]{color:#e5e7eb!important}

/* Tablet arrangement */
@media(max-width:1100px){
  .app-layout{display:block!important;min-height:100vh}.main-area{width:100%;min-width:0}.topbar{position:sticky;top:0;z-index:30}.container{width:100%;max-width:100%;padding:16px}.sidebar{position:sticky;top:0;height:auto;max-height:none;width:100%;padding:12px;z-index:40;border-radius:0;overflow:visible}.brand-block{margin:0 0 10px;padding:4px 4px 10px}.brand-logo{width:36px;height:36px;font-size:20px}.brand-title{font-size:14px;line-height:1.05}.brand-subtitle{font-size:10px}.sidebar nav{display:block}.nav-group-title{display:none}.nav-section{display:flex!important;flex-direction:row!important;gap:8px;overflow-x:auto;padding-bottom:8px;margin-bottom:7px;scrollbar-width:thin;border-bottom:1px solid rgba(255,255,255,.12)}nav a,.btn{flex:0 0 auto!important;white-space:nowrap;min-height:38px;padding:10px 12px;font-size:13px}.logout-wrap{border-top:0;margin-top:2px;padding-top:2px}.sales-layout{grid-template-columns:1fr!important;gap:16px}.checkout-panel{position:relative!important;top:auto!important}.current-sale-box{max-height:none!important}.cart-table-wrap{max-height:260px}.two{grid-template-columns:1fr 1fr}.pos-card-grid{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
}

/* Phone arrangement */
@media(max-width:680px){
  .container{padding:10px!important}.topbar{padding:10px 12px;height:auto;display:block}.topbar h1{font-size:18px;margin-bottom:3px}.topbar-right{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.pill{font-size:12px;padding:7px 9px;border-radius:10px}.sidebar{padding:10px;position:relative}.brand-block{gap:9px}.brand-logo{width:34px;height:34px;border-radius:10px}.brand-title{font-size:13px}.brand-subtitle{display:none}.nav-section{gap:6px;margin-bottom:5px;padding-bottom:6px}nav a,.btn{font-size:12px;padding:9px 10px;border-radius:10px;min-height:36px}.card{padding:14px!important;border-radius:14px;margin-bottom:12px}.card h2{font-size:20px}.card h3{font-size:16px}.two{grid-template-columns:1fr!important;gap:10px}input,select,textarea{max-width:100%!important;font-size:16px!important;padding:12px!important}button{width:auto;max-width:100%;font-size:14px}.sales-layout{display:block!important}.checkout-panel{margin-top:12px}.pos-card-grid{grid-template-columns:1fr!important;gap:10px}.pos-big-btn{min-height:78px!important;font-size:18px!important;padding:18px 12px!important}.pos-big-btn span{font-size:12px!important}.pos-small-btn{display:flex!important;width:100%;min-width:0;margin:6px 0!important;padding:13px 12px!important}.step-box{padding:14px!important}.pos-item-card{padding:14px!important;border-radius:14px}.cart-table-wrap{max-height:230px;overflow:auto}.cart-table-wrap table{min-width:390px;font-size:13px}.quick-summary{grid-template-columns:1fr 1fr!important;gap:8px}.cart-total-line{align-items:stretch}.cart-total-line h2{font-size:18px;margin:8px 0}.complete-sale-btn{width:100%!important;position:relative!important;bottom:auto!important;margin-top:6px}.floating-cart{border-radius:14px}.checkout-card .form-grid{gap:6px}.sidebar::-webkit-scrollbar,.nav-section::-webkit-scrollbar{height:4px}.sidebar::-webkit-scrollbar-thumb,.nav-section::-webkit-scrollbar-thumb{background:#60a5fa;border-radius:10px}
}

/* Extra-small phones */
@media(max-width:390px){
  .container{padding:8px!important}.topbar h1{font-size:16px}.pill{font-size:11px}.pos-big-btn{font-size:16px!important}.quick-summary{grid-template-columns:1fr!important}.cart-table-wrap table{min-width:350px;font-size:12px}nav a,.btn{font-size:11px;padding:8px 9px}
}


/* ===== FINAL PHONE LIKE LAPTOP PROFESSIONAL FIX =====
   This override makes the phone/tablet view look clean like the laptop view,
   without the sidebar covering the sales page. */
@media(max-width:1200px), (pointer:coarse){
  html,body{width:100%!important;max-width:100%!important;overflow-x:hidden!important;background:var(--bg)!important}
  .app-layout{display:block!important;width:100%!important;min-width:0!important;min-height:100vh!important}
  .main-area{display:block!important;width:100%!important;min-width:0!important;margin:0!important;padding:0!important}
  .sidebar{position:relative!important;top:auto!important;left:auto!important;right:auto!important;width:100%!important;height:auto!important;max-height:none!important;min-height:0!important;overflow:visible!important;padding:12px!important;border-radius:0!important;box-shadow:0 6px 20px rgba(0,0,0,.18)!important;z-index:1!important}
  .brand-block{display:flex!important;align-items:center!important;margin:0 0 12px 0!important;padding:6px 6px 12px 6px!important;border-bottom:1px solid rgba(255,255,255,.18)!important}
  .brand-logo{width:42px!important;height:42px!important;min-width:42px!important;border-radius:14px!important;font-size:23px!important}
  .brand-title{font-size:17px!important;line-height:1.05!important;letter-spacing:.3px!important}
  .brand-subtitle{display:block!important;font-size:11px!important;opacity:.85!important}
  .sidebar nav{display:block!important;width:100%!important}
  .nav-group-title{display:block!important;margin:14px 4px 7px!important;color:#bfdbfe!important;font-size:10px!important;letter-spacing:.08em!important}
  .nav-section{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important;margin:0 0 10px 0!important;padding-bottom:10px!important;border-bottom:1px solid rgba(255,255,255,.12)!important;overflow:visible!important}
  .logout-wrap{border-top:1px solid rgba(255,255,255,.15)!important;margin-top:10px!important;padding-top:10px!important}
  nav a,.btn{width:100%!important;min-width:0!important;max-width:100%!important;white-space:normal!important;text-align:left!important;justify-content:flex-start!important;padding:11px 10px!important;min-height:44px!important;font-size:13px!important;border-radius:12px!important;transform:none!important;line-height:1.15!important}
  nav a:hover,.btn:hover{transform:none!important}
  .topbar{position:relative!important;top:auto!important;z-index:2!important;width:100%!important;height:auto!important;display:flex!important;align-items:center!important;justify-content:space-between!important;gap:10px!important;padding:14px 12px!important;box-shadow:0 2px 12px rgba(0,0,0,.08)!important}
  .topbar h1{font-size:20px!important;line-height:1.2!important;margin:0!important}.topbar .small{font-size:12px!important}.topbar-right{display:flex!important;gap:8px!important;flex-wrap:wrap!important;justify-content:flex-end!important}.pill{font-size:12px!important;padding:8px 10px!important;border-radius:10px!important}
  .container{width:100%!important;max-width:100%!important;margin:0!important;padding:14px!important;overflow-x:hidden!important}
  .card{width:100%!important;max-width:100%!important;border-radius:16px!important;padding:16px!important;margin-bottom:14px!important;overflow:hidden!important}
  .sales-layout{display:grid!important;grid-template-columns:1fr!important;gap:14px!important;width:100%!important;max-width:100%!important}
  .sales-left,.checkout-panel{width:100%!important;max-width:100%!important;min-width:0!important}.checkout-panel{position:relative!important;top:auto!important;margin-top:0!important}
  .two{grid-template-columns:1fr!important;gap:12px!important}.grid{grid-template-columns:1fr!important;gap:12px!important}.pos-card-grid{grid-template-columns:1fr!important;gap:12px!important}.selection-grid{display:grid!important;grid-template-columns:1fr 1fr!important;gap:10px!important}.pos-big-btn{min-height:86px!important;padding:18px 10px!important;font-size:19px!important;border-radius:16px!important}.pos-small-btn{width:100%!important;margin:5px 0!important;min-width:0!important}.step-box,.pos-item-card,.product-card{width:100%!important;max-width:100%!important;border-radius:16px!important;padding:16px!important;overflow:hidden!important}
  input,select,textarea{max-width:100%!important;width:100%!important;font-size:16px!important;padding:12px!important}button{max-width:100%!important}.checkout-card input,.checkout-card select,.pos-item-card input,.pos-item-card select{width:100%!important;max-width:100%!important}.current-sale-box{max-height:none!important;overflow:visible!important}.cart-table-wrap{width:100%!important;max-height:240px!important;overflow:auto!important;-webkit-overflow-scrolling:touch!important}.cart-table-wrap table{min-width:430px!important;font-size:13px!important}.quick-summary{grid-template-columns:1fr 1fr!important;gap:8px!important}.complete-sale-btn{width:100%!important;position:relative!important;bottom:auto!important;margin-top:8px!important}
}

@media(max-width:430px){
  .container{padding:10px!important}.sidebar{padding:10px!important}.nav-section{grid-template-columns:1fr!important}.brand-title{font-size:15px!important}.brand-subtitle{font-size:10px!important}.topbar{display:block!important}.topbar-right{justify-content:flex-start!important;margin-top:8px!important}.topbar h1{font-size:18px!important}.pill{font-size:11px!important}.selection-grid{grid-template-columns:1fr!important}.pos-big-btn{font-size:17px!important;min-height:76px!important}.quick-summary{grid-template-columns:1fr!important}.cart-table-wrap table{min-width:360px!important;font-size:12px!important}.card h2{font-size:20px!important}.card h3{font-size:16px!important}
}

/* Stronger dark-mode visibility on phone and laptop */
.dark .sidebar{background:linear-gradient(180deg,#031d36,#020617)!important}.dark .brand-block{border-color:rgba(255,255,255,.14)!important}.dark .nav-section{border-color:rgba(255,255,255,.10)!important}.dark nav a,.dark .btn{color:#f8fafc!important}.dark nav a.active,.dark .btn-green{background:#16a34a!important;color:#fff!important}.dark .topbar,.dark .card,.dark .step-box,.dark .product-card,.dark .pos-item-card,.dark .checkout-card,.dark .floating-cart{background:#111827!important;color:#f8fafc!important;border-color:#334155!important}.dark input,.dark select,.dark textarea{background:#020617!important;color:#f8fafc!important;border-color:#475569!important}.dark input::placeholder{color:#94a3b8!important}.dark .pos-big-btn,.dark .pos-small-btn{border:1px solid #334155!important}.dark .pos-small-btn{background:#1e293b!important;color:#f8fafc!important}.dark .pos-small-btn.active{background:#0f4c81!important;color:#fff!important}.dark .small{color:#cbd5e1!important}.dark .pill{background:#020617!important;color:#f8fafc!important;border-color:#334155!important}.dark .cart-table-wrap{border-color:#334155!important}.dark th{background:#073763!important;color:white!important}.dark td{background:#111827!important;color:#e5e7eb!important;border-color:#334155!important}

/* ===== MOBILE-FIRST PROFESSIONAL POS NAVIGATION ===== */
.mobile-bottom-nav{display:none}
.mobile-more-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.mobile-more-card{display:flex;align-items:center;gap:10px;padding:16px;border-radius:16px;background:#ffffff;border:1px solid #dbe4ee;color:#0f172a;font-weight:800;box-shadow:0 4px 14px rgba(15,23,42,.06)}
.mobile-cart-bar{display:none}

@media(max-width:760px){
  body{padding-bottom:78px!important}
  .sidebar{display:none!important}
  .app-layout{display:block!important}
  .topbar{position:sticky!important;top:0!important;z-index:50!important;background:#ffffff!important}
  .container{padding:12px!important}
  .card{border-radius:16px!important}
  .mobile-bottom-nav{
    position:fixed!important;left:0!important;right:0!important;bottom:0!important;z-index:999!important;
    height:68px!important;background:#ffffff!important;border-top:1px solid #dbe4ee!important;
    display:grid!important;grid-template-columns:repeat(5,1fr)!important;gap:0!important;
    box-shadow:0 -8px 28px rgba(15,23,42,.16)!important;padding:6px 4px env(safe-area-inset-bottom)!important
  }
  .mobile-bottom-nav a{
    display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;
    color:#475569!important;text-decoration:none!important;font-size:11px!important;font-weight:800!important;border-radius:12px!important;gap:2px!important
  }
  .mobile-bottom-nav a span:first-child{font-size:20px!important;line-height:1!important}
  .mobile-bottom-nav a.active{background:#e8f2ff!important;color:#0b4f86!important}
  .mobile-bottom-nav a.sale-active{background:#dcfce7!important;color:#15803d!important}
  .mobile-cart-bar{
    position:fixed!important;left:10px!important;right:10px!important;bottom:78px!important;z-index:998!important;
    display:flex!important;align-items:center!important;justify-content:space-between!important;gap:10px!important;
    background:#16a34a!important;color:#ffffff!important;border-radius:16px!important;padding:12px 14px!important;
    box-shadow:0 10px 28px rgba(22,163,74,.35)!important;font-weight:900!important
  }
  .mobile-cart-bar a{color:#fff!important;background:rgba(255,255,255,.18)!important;padding:9px 12px!important;border-radius:12px!important;text-decoration:none!important;font-weight:900!important}
  .sales-layout{display:block!important}
  .checkout-panel{margin-top:12px!important}
  .pos-big-btn,.pos-small-btn,button,.btn{min-height:44px!important}
  .card table{display:block!important;width:100%!important;overflow-x:auto!important;-webkit-overflow-scrolling:touch!important}
  .card table tbody{display:table!important;width:100%!important;min-width:520px!important}
  .mobile-more-card{background:#ffffff!important}
}

.dark .mobile-bottom-nav{background:#0f172a!important;border-top-color:#334155!important}
.dark .mobile-bottom-nav a{color:#cbd5e1!important}
.dark .mobile-bottom-nav a.active{background:#172554!important;color:#bfdbfe!important}
.dark .mobile-bottom-nav a.sale-active{background:#064e3b!important;color:#bbf7d0!important}
.dark .mobile-more-card{background:#111827!important;border-color:#334155!important;color:#f8fafc!important}
.dark .mobile-cart-bar{background:#15803d!important;color:#ffffff!important}
.dark .topbar{background:#111827!important}

</style>
"""


def page(title, content, **context):
    # Professional sidebar navigation: cleaner than many buttons at the top.
    active_path = request.path if request else "/"
    nav = """
    {% if session.get('user_id') %}
    <aside class="sidebar no-print">
        <div class="brand-block">
            <div class="brand-logo">👓</div>
            <div>
                <div class="brand-title">HALLELUYAH<br>OPTICAL LAB</div>
                <div class="brand-subtitle">Business Management System</div>
            </div>
        </div>
        <nav>
            <div class="nav-group-title">Main</div>
            <div class="nav-section">
                <a class="{% if active_path == '/' %}active{% endif %}" href="/">🏠 Dashboard</a>
                <a class="{% if active_path == '/daily-report' %}active{% endif %}" href="/daily-report">📊 Daily Report</a>
                <a class="{% if active_path == '/notifications' %}active{% endif %}" href="/notifications">🔔 Notifications</a>
                {% if session['role'] == 'manager' %}<a class="{% if active_path == '/audit-trail' %}active{% endif %}" href="/audit-trail">🧾 Audit Trail</a>{% endif %}
            </div>
            <div class="nav-group-title">Sales & Customers</div>
            <div class="nav-section">
                <a class="{% if active_path == '/pos' %}active{% endif %}" href="/pos">💰 Make Sale</a>
                <a class="{% if active_path == '/sales' %}active{% endif %}" href="/sales">🧾 Sales History</a>
                <a class="{% if active_path == '/debtors' %}active{% endif %}" href="/debtors">👥 Debtors</a>
                <a class="{% if active_path == '/customer-history' %}active{% endif %}" href="/customer-history">📁 Customer History</a>
                <a class="{% if active_path == '/debtor-reminders' %}active{% endif %}" href="/debtor-reminders">⏰ Debtor Reminder</a>
            </div>
            <div class="nav-group-title">Inventory</div>
            <div class="nav-section">
                <a class="{% if active_path == '/products' %}active{% endif %}" href="/products">📦 Products / Stock</a>
                <a class="{% if active_path == '/branch-stock' %}active{% endif %}" href="/branch-stock">🏬 Branch Stock</a>
                <a class="{% if active_path == '/lens-powers' %}active{% endif %}" href="/lens-powers">🔍 Lens Powers</a>
                <a class="{% if active_path == '/lens-restock-center' %}active{% endif %}" href="/lens-restock-center">➕ Lens Restock Center</a>
                <a class="{% if active_path == '/lens-search' %}active{% endif %}" href="/lens-search">🔎 Lens Search</a>
                {% if session['role'] == 'manager' %}<a class="{% if active_path == '/generate-power-grid' %}active{% endif %}" href="/generate-power-grid">🧮 Generate Power Grid</a>{% endif %}
            </div>
            <div class="nav-group-title">Transfers & Patients</div>
            <div class="nav-section">
                <a class="{% if active_path == '/request-goods' %}active{% endif %}" href="/request-goods">🔄 Request Goods</a>
                <a class="{% if active_path == '/goods-requests' %}active{% endif %}" href="/goods-requests">📥 Goods Requests</a>
                {% if session['role'] == 'manager' %}<a class="{% if active_path == '/smart-transfer' %}active{% endif %}" href="/smart-transfer">⚡ Smart Transfer</a>{% endif %}
                <a class="{% if active_path == '/patient-rx' %}active{% endif %}" href="/patient-rx">👁️ Patient Rx</a>
            </div>
            {% if session['role'] == 'manager' %}
            <div class="nav-group-title">Management</div>
            <div class="nav-section">
                <a class="{% if active_path == '/add-product' %}active{% endif %}" href="/add-product">➕ Add Product</a>
                <a class="{% if active_path == '/add-lens-power' %}active{% endif %}" href="/add-lens-power">➕ Add Lens Power</a>
                <a class="{% if active_path == '/staff' %}active{% endif %}" href="/staff">👨‍💼 Staff</a>
                <a class="{% if active_path == '/branches' %}active{% endif %}" href="/branches">🏢 Branches</a>
                <a class="{% if active_path == '/security-settings' %}active{% endif %}" href="/security-settings">🔒 Security</a>
                <a class="{% if active_path == '/backup-center' %}active{% endif %}" href="/backup-center">💾 Backup Center</a>
                <a class="{% if active_path == '/office-settings' %}active{% endif %}" href="/office-settings">⚙️ Office Settings</a>
                <a class="{% if active_path == '/appearance' %}active{% endif %}" href="/appearance">🎨 Appearance</a>
            </div>
            {% endif %}
            <div class="logout-wrap"><a class="btn-red" href="/logout">🚪 Logout</a></div>
        </nav>
    </aside>
    {% endif %}
    """
    return render_template_string(f"""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    {STYLE}
    <div class="{{{{ session.get('theme', 'light') }}}}">
        <div class="app-layout">
            {nav}
            <main class="main-area">
                <div class="topbar no-print">
                    <div>
                        <h1>{{{{ title }}}}</h1>
                        <div class="small">HALLELUYAH OPTICAL LABORATORY</div>
                    </div>
                    <div class="topbar-right">
                        <div class="pill">🏬 Branch ID: {{{{ session.get('branch_id', '') }}}}</div>
                        <div class="pill">👤 {{{{ session.get('username', '') }}}} · {{{{ session.get('role', '') }}}}</div>
                    </div>
                </div>
                <div class="container">
                    {content}
                </div>
            </main>
        </div>
        {{% if session.get('user_id') %}}
        <nav class="mobile-bottom-nav no-print">
            <a class="{{{{ 'active' if active_path == '/' else '' }}}}" href="/"><span>🏠</span><span>Home</span></a>
            <a class="{{{{ 'sale-active' if active_path == '/pos' else '' }}}}" href="/pos"><span>💰</span><span>Sale</span></a>
            <a class="{{{{ 'active' if active_path in ['/products','/lens-powers','/lens-restock-center','/branch-stock'] else '' }}}}" href="/products"><span>📦</span><span>Stock</span></a>
            <a class="{{{{ 'active' if active_path == '/patient-rx' else '' }}}}" href="/patient-rx"><span>👁️</span><span>Rx</span></a>
            <a class="{{{{ 'active' if active_path == '/mobile-more' else '' }}}}" href="/mobile-more"><span>☰</span><span>More</span></a>
        </nav>
        {{% endif %}}
    </div>
    """, title=title, active_path=active_path, Branch=Branch, User=User, Product=Product, LensPower=LensPower,
       Sale=Sale, SaleItem=SaleItem, OfficeSetting=OfficeSetting, GoodsRequest=GoodsRequest, PatientPrescription=PatientPrescription, NotificationLog=NotificationLog, AuditLog=AuditLog, session=session,
       money=money, **context)


@app.route("/mobile-more")
def mobile_more():
    if not logged_in():
        return redirect(url_for("login"))
    return page("More", """
    <div class="card">
        <h2>More Options</h2>
        <p class="small">Quick mobile menu for other parts of the system.</p>
        <div class="mobile-more-grid">
            <a class="mobile-more-card" href="/sales">🧾 Sales History</a>
            <a class="mobile-more-card" href="/debtors">👥 Debtors</a>
            <a class="mobile-more-card" href="/customer-history">📁 Customer History</a>
            <a class="mobile-more-card" href="/debtor-reminders">⏰ Debtor Reminder</a>
            <a class="mobile-more-card" href="/lens-powers">🔍 Lens Powers</a>
            <a class="mobile-more-card" href="/lens-restock-center">➕ Lens Restock</a>
            <a class="mobile-more-card" href="/branch-stock">🏬 Branch Stock</a>
            <a class="mobile-more-card" href="/request-goods">🔄 Request Goods</a>
            <a class="mobile-more-card" href="/goods-requests">📥 Goods Requests</a>
            {% if session['role'] == 'manager' %}
            <a class="mobile-more-card" href="/add-product">➕ Add Product</a>
            <a class="mobile-more-card" href="/add-lens-power">➕ Add Lens Power</a>
            <a class="mobile-more-card" href="/staff">👨‍💼 Staff</a>
            <a class="mobile-more-card" href="/branches">🏢 Branches</a>
            <a class="mobile-more-card" href="/generate-power-grid">🧮 Generate Grid</a>
            <a class="mobile-more-card" href="/security-settings">🔒 Security</a>
            <a class="mobile-more-card" href="/backup-center">💾 Backup Center</a>
            <a class="mobile-more-card" href="/office-settings">⚙️ Office Settings</a>
            <a class="mobile-more-card" href="/appearance">🎨 Appearance</a>
            <a class="mobile-more-card" href="/audit-trail">🧾 Audit Trail</a>
            {% endif %}
            <a class="mobile-more-card" href="/logout">🚪 Logout</a>
        </div>
    </div>
    """)


def ensure_schema():
    # db.create_all() never deletes existing records. It only creates missing tables.
    db.create_all()
    # Safe upgrades for old Render databases.
    try:
        db.session.execute(text("ALTER TABLE hol_sale_item ADD COLUMN IF NOT EXISTS lens_power VARCHAR(120)"))
        db.session.execute(text("ALTER TABLE hol_product ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_user ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_sale ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_sale ADD COLUMN IF NOT EXISTS attended_by_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_goods_request ADD COLUMN IF NOT EXISTS processed_by_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_lens_power ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        db.session.execute(text("ALTER TABLE hol_office_setting ADD COLUMN IF NOT EXISTS theme VARCHAR(20) DEFAULT 'light'"))
        db.session.execute(text("ALTER TABLE hol_office_setting ADD COLUMN IF NOT EXISTS manager_pin_hash VARCHAR(255) DEFAULT ''"))
        db.session.execute(text("ALTER TABLE hol_audit_log ADD COLUMN IF NOT EXISTS details TEXT"))
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
        db.session.add(OfficeSetting(theme="light", manager_pin_hash=generate_password_hash("1234")))
        db.session.commit()
    else:
        setting = OfficeSetting.query.first()
        if not getattr(setting, "theme", None):
            setting.theme = "light"
        if not getattr(setting, "manager_pin_hash", None):
            setting.manager_pin_hash = generate_password_hash("1234")
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
        if user and user.role != "deleted" and check_password_hash(user.password_hash, request.form.get("password")):
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
    </form><p style="color:red;">{{ error }}</p></div>
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
        setting.office_name = request.form.get("office_name") or "HALLELUYAH OPTICAL LABORATORY"
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


@app.route("/appearance", methods=["GET", "POST"])
def appearance():
    if not logged_in():
        return redirect(url_for("login"))
    setting = OfficeSetting.query.first()
    if request.method == "POST":
        theme = request.form.get("theme") or "light"
        if theme not in ["light", "dark"]:
            theme = "light"
        session["theme"] = theme
        if setting:
            setting.theme = theme
            db.session.commit()
        audit_log("Appearance Changed", f"Theme set to {theme}")
        return redirect(url_for("appearance"))
    current_theme = session.get("theme") or (setting.theme if setting else "light")
    return page("Appearance", """
    <div class="card">
        <h2>Appearance</h2>
        <p class="small">Choose light or dark mode. This makes the system more comfortable for day or night use.</p>
        <form method="post">
            <label>Theme</label><br>
            <select name="theme">
                <option value="light" {% if current_theme == 'light' %}selected{% endif %}>Light Mode</option>
                <option value="dark" {% if current_theme == 'dark' %}selected{% endif %}>Dark Mode</option>
            </select><br><br>
            <button class="btn-green">Save Appearance</button>
        </form>
    </div>
    """, current_theme=current_theme)


@app.route("/security-settings", methods=["GET", "POST"])
def security_settings():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can change security settings."
    setting = OfficeSetting.query.first()
    message = ""
    if request.method == "POST":
        old_pin = request.form.get("old_pin") or ""
        new_pin = request.form.get("new_pin") or ""
        if not check_manager_pin(old_pin):
            message = "Wrong current manager PIN."
        elif len(new_pin) < 4:
            message = "New manager PIN must be at least 4 digits/characters."
        else:
            setting.manager_pin_hash = generate_password_hash(new_pin)
            db.session.commit()
            audit_log("Manager PIN Changed", "Manager security PIN was changed")
            message = "Manager PIN changed successfully."
    return page("Security Settings", """
    <div class="card">
        <h2>Advanced Security</h2>
        <p class="small">Sensitive actions such as discount approval and debtor payment confirmation require manager PIN.</p>
        {% if message %}<div class="alert success"><b>{{ message }}</b></div>{% endif %}
        <form method="post">
            <label>Current Manager PIN</label><br><input name="old_pin" type="password" placeholder="Default PIN is 1234"><br><br>
            <label>New Manager PIN</label><br><input name="new_pin" type="password" placeholder="Enter new PIN"><br><br>
            <button class="btn-green">Change Manager PIN</button>
        </form>
    </div>
    """, message=message)


@app.route("/audit-trail")
def audit_trail():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can view audit trail."
    logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(300).all()
    users_map = {u.id: u.username for u in User.query.all()}
    branches_map = {b.id: b.name for b in Branch.query.all()}
    return page("Audit Trail", """
    <div class="card">
        <h2>Audit Trail</h2>
        <p class="small">This records sensitive business actions for accountability and security.</p>
        <table>
            <tr><th>Date</th><th>User</th><th>Branch</th><th>Action</th><th>Details</th></tr>
            {% for log in logs %}
            <tr>
                <td>{{ log.created_at }}</td>
                <td>{{ users_map.get(log.user_id, 'Unknown') }}</td>
                <td>{{ branches_map.get(log.branch_id, '') }}</td>
                <td>{{ log.action }}</td>
                <td>{{ log.details }}</td>
            </tr>
            {% else %}
            <tr><td colspan="5">No audit record yet.</td></tr>
            {% endfor %}
        </table>
    </div>
    """, logs=logs, users_map=users_map, branches_map=branches_map)


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
        audit_log("Product Added", f"Added product: {product.name}")
        return redirect(url_for("products"))
    return page("Add Product", PRODUCT_FORM, branches=Branch.query.all(), product=None)



@app.route("/branch-stock")
def branch_stock():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can view all branch stock."
    branches = Branch.query.order_by(Branch.name).all()
    products_by_branch = {}
    lens_by_branch = {}
    for b in branches:
        products_by_branch[b.id] = Product.query.filter_by(branch_id=b.id).order_by(Product.category, Product.name).all()
        lens_by_branch[b.id] = LensPower.query.filter_by(branch_id=b.id).order_by(LensPower.sph, LensPower.add_power).all()
    products_map = {p.id: p.name for p in Product.query.all()}
    return page("Branch Stock", """
    <div class="card">
        <h2>All Branch Stock Overview</h2>
        <p class="small">Manager can use this page to know goods and lens powers available at each branch.</p>
        {% for b in branches %}
            <div class="card" style="background:#f8fafc">
                <h3>{{ b.name }}</h3>
                <p class="small">{{ b.address }}</p>
                <h4>Products / Frames / Accessories</h4>
                <table>
                    <tr><th>Product</th><th>Category</th><th>Subcategory</th><th>Qty</th><th>Retail</th><th>Wholesale</th></tr>
                    {% for p in products_by_branch[b.id] %}
                    <tr><td>{{ p.name }}</td><td>{{ p.category }}</td><td>{{ p.subcategory }}</td><td>{% if p.quantity <= 5 %}<span class="badge-low">LOW</span> {% endif %}{{ p.quantity }}</td><td>{{ money(p.retail_price) }}</td><td>{{ money(p.wholesale_price) }}</td></tr>
                    {% else %}<tr><td colspan="6">No product in this branch.</td></tr>{% endfor %}
                </table>
                <h4>Lens Power Stock</h4>
                <table>
                    <tr><th>Lens</th><th>SPH</th><th>CYL</th><th>AXIS</th><th>ADD</th><th>Qty</th></tr>
                    {% for l in lens_by_branch[b.id] %}
                    <tr><td>{{ products_map.get(l.product_id, '') }}</td><td>{{ l.sph }}</td><td>{{ l.cyl }}</td><td>{{ l.axis }}</td><td>{{ l.add_power }}</td><td>{% if l.quantity <= 2 %}<span class="badge-low">LOW</span> {% endif %}{{ l.quantity }}</td></tr>
                    {% else %}<tr><td colspan="6">No lens power stock in this branch.</td></tr>{% endfor %}
                </table>
            </div>
        {% endfor %}
    </div>
    """, branches=branches, products_by_branch=products_by_branch, lens_by_branch=lens_by_branch, products_map=products_map)

@app.route("/products")
def products():
    if not logged_in():
        return redirect(url_for("login"))
    selected_branch = request.args.get("branch_id")
    if is_manager():
        product_query = Product.query
        if selected_branch:
            product_query = product_query.filter_by(branch_id=int(selected_branch))
        product_list = product_query.order_by(Product.id.desc()).all()
    else:
        selected_branch = str(session.get("branch_id"))
        product_list = Product.query.filter_by(branch_id=session.get("branch_id")).order_by(Product.id.desc()).all()
    branches = Branch.query.order_by(Branch.name).all()
    branches_map = {b.id: b.name for b in branches}
    return page("Products", """
    <div class="card"><h2>Products / Stock</h2>
    {% if session['role']=='manager' %}
    <form method="get" class="no-print" style="margin-bottom:15px">
        <label>View Products By Branch</label><br>
        <select name="branch_id" onchange="this.form.submit()" style="max-width:300px">
            <option value="">All Branches</option>
            {% for b in branches %}<option value="{{ b.id }}" {% if selected_branch and selected_branch|int == b.id %}selected{% endif %}>{{ b.name }}</option>{% endfor %}
        </select>
    </form>
    {% endif %}
    <table>
        <tr><th>Branch</th><th>Name</th><th>Category</th><th>Subcategory</th><th>Retail</th><th>Wholesale</th><th>Qty</th><th>Action</th></tr>
        {% for p in product_list %}<tr><td>{{ branches_map.get(p.branch_id, '') }}</td><td>{{ p.name }}</td><td>{{ p.category }}</td><td>{{ p.subcategory }}</td><td>{{ money(p.retail_price) }}</td><td>{{ money(p.wholesale_price) }}</td><td>{% if p.quantity <= 5 %}<span class="badge-low">LOW</span> {% endif %}{{ p.quantity }}</td>{% if session['role']=='manager' %}<td><a href="/edit-product/{{ p.id }}">Edit</a> | <a href="/restock-product/{{ p.id }}">Restock</a></td>{% endif %}</tr>{% endfor %}
    </table></div><a class="btn" href="/">Back</a>
    """, product_list=product_list, branches_map=branches_map, branches=branches, selected_branch=selected_branch)


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
        audit_log("Product Edited", f"Edited product: {product.name}")
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
        audit_log("Product Restocked", f"Restocked {product.name} by {add_qty}")
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
    branches = Branch.query.order_by(Branch.name).all()
    selected_branch = request.args.get("branch_id")
    selected_product = request.args.get("product_id")
    low_only = request.args.get("low_only") == "1"

    if is_manager():
        power_query = LensPower.query
        if selected_branch:
            power_query = power_query.filter(LensPower.branch_id == int(selected_branch))
    else:
        selected_branch = str(session.get("branch_id"))
        power_query = LensPower.query.filter_by(branch_id=session.get("branch_id"))

    if selected_product:
        power_query = power_query.filter(LensPower.product_id == int(selected_product))
    if low_only:
        power_query = power_query.filter(LensPower.quantity <= 2)

    power_list = power_query.order_by(LensPower.branch_id, LensPower.sph, LensPower.cyl, LensPower.add_power).all()
    products_query = Product.query.filter(Product.category.contains("Lens"))
    if selected_branch:
        products_query = products_query.filter(Product.branch_id == int(selected_branch))
    elif not is_manager():
        products_query = products_query.filter(Product.branch_id == session.get("branch_id"))
    product_filter_list = products_query.order_by(Product.name).all()
    products_map = {p.id: p.name for p in Product.query.all()}
    branches_map = {b.id: b.name for b in branches}
    return page("Lens Powers", """
    <div class="card"><h2>Lens Power Stock</h2>
    <p class="small">Use the branch filter before restocking. This prevents mixing lens powers from different branches.</p>
    {% if session['role']=='manager' %}
    <form method="get" class="no-print" style="margin-bottom:15px">
        <div class="two">
            <div>
                <label>Select Branch</label><br>
                <select name="branch_id" onchange="this.form.submit()">
                    <option value="">All Branches</option>
                    {% for b in branches %}<option value="{{ b.id }}" {% if selected_branch and selected_branch|int == b.id %}selected{% endif %}>{{ b.name }}</option>{% endfor %}
                </select>
            </div>
            <div>
                <label>Select Lens Product</label><br>
                <select name="product_id" onchange="this.form.submit()">
                    <option value="">All Lens Products</option>
                    {% for p in product_filter_list %}<option value="{{ p.id }}" {% if selected_product and selected_product|int == p.id %}selected{% endif %}>{{ p.name }} - {{ p.subcategory }}</option>{% endfor %}
                </select>
            </div>
        </div>
        <label><input type="checkbox" name="low_only" value="1" {% if low_only %}checked{% endif %} onchange="this.form.submit()"> Show low stock only</label>
        <br><br><a class="btn-green btn" href="/lens-restock-center{% if selected_branch %}?branch_id={{ selected_branch }}{% endif %}">Bulk Restock Selected Branch</a>
    </form>
    {% endif %}
    <table><tr><th>Branch</th><th>Lens</th><th>SPH</th><th>CYL</th><th>AXIS</th><th>ADD</th><th>Quantity</th>{% if session['role']=='manager' %}<th>Action</th>{% endif %}</tr>
    {% for l in power_list %}<tr><td>{{ branches_map.get(l.branch_id, '') }}</td><td>{{ products_map.get(l.product_id, '') }}</td><td>{{ l.sph }}</td><td>{{ l.cyl }}</td><td>{{ l.axis }}</td><td>{{ l.add_power }}</td><td>{% if l.quantity <= 2 %}<span class="badge-low">LOW</span> {% endif %}{{ l.quantity }}</td>{% if session['role']=='manager' %}<td><a href="/restock-lens/{{ l.id }}">Restock</a><form method="post" action="/delete-lens-power/{{ l.id }}" style="display:inline" onsubmit="return confirm('Delete this lens power? Manager PIN is required.');"><input type="password" name="manager_pin" placeholder="Manager PIN" required style="max-width:120px"><button class="btn-red" type="submit">Delete</button></form></td>{% endif %}</tr>{% else %}<tr><td colspan="8">No lens powers found for this selection.</td></tr>{% endfor %}
    </table></div>
    """, power_list=power_list, products_map=products_map, branches_map=branches_map, branches=branches, selected_branch=selected_branch, selected_product=selected_product, product_filter_list=product_filter_list, low_only=low_only)


@app.route("/delete-lens-power/<int:lens_id>", methods=["POST"])
def delete_lens_power(lens_id):
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return page("Manager Access Required", "<div class='card'><h2>Manager Access Required</h2><p>Only manager can delete wrong lens power entries.</p><a class='btn' href='/lens-powers'>Back</a></div>")
    if not check_manager_pin(request.form.get("manager_pin")):
        return page("Wrong Manager PIN", "<div class='card danger'><h2>Wrong Manager PIN</h2><p>This sensitive action was blocked.</p><a class='btn' href='/lens-powers'>Back</a></div>")
    lens = LensPower.query.get_or_404(lens_id)
    details = f"Deleted lens power SPH {lens.sph} CYL {lens.cyl} AXIS {lens.axis} ADD {lens.add_power} Qty {lens.quantity}"
    db.session.delete(lens)
    db.session.commit()
    audit_log("Lens Power Deleted", details)
    return redirect(url_for("lens_powers"))


@app.route("/restock-lens/<int:lens_id>", methods=["GET", "POST"])
def restock_lens(lens_id):
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can restock lens powers."
    lens = LensPower.query.get_or_404(lens_id)
    product = Product.query.get(lens.product_id)
    branches = Branch.query.order_by(Branch.name).all()
    if request.method == "POST":
        add_qty = int(request.form.get("add_qty") or 0)
        target_branch_id = int(request.form.get("branch_id") or lens.branch_id or 1)
        target_product = product

        # If manager selects another branch, find the same lens product in that branch.
        # If it does not exist, create it automatically so branch stock remains separate.
        if product and int(product.branch_id or 0) != target_branch_id:
            target_product = Product.query.filter_by(
                branch_id=target_branch_id,
                name=product.name,
                category=product.category,
                subcategory=product.subcategory
            ).first()
            if not target_product:
                target_product = Product(
                    branch_id=target_branch_id,
                    name=product.name,
                    category=product.category,
                    subcategory=product.subcategory,
                    retail_price=product.retail_price,
                    wholesale_price=product.wholesale_price,
                    quantity=0
                )
                db.session.add(target_product)
                db.session.flush()

        target_lens = LensPower.query.filter_by(
            product_id=target_product.id,
            branch_id=target_branch_id,
            sph=lens.sph or "",
            cyl=lens.cyl or "",
            axis=lens.axis or "",
            add_power=lens.add_power or ""
        ).first()
        if not target_lens:
            target_lens = LensPower(
                product_id=target_product.id,
                branch_id=target_branch_id,
                sph=lens.sph or "",
                cyl=lens.cyl or "",
                axis=lens.axis or "",
                add_power=lens.add_power or "",
                quantity=0
            )
            db.session.add(target_lens)
            db.session.flush()
        target_lens.quantity = int(target_lens.quantity or 0) + add_qty
        db.session.commit()
        audit_log("Lens Power Restocked", f"Restocked {target_product.name} branch ID {target_branch_id}: SPH {target_lens.sph} CYL {target_lens.cyl} ADD {target_lens.add_power} by {add_qty}")
        return redirect(url_for("lens_powers", branch_id=target_branch_id))
    return page("Restock Lens Power", """
    <div class="card"><h2>Restock Lens Power</h2>
    <p><b>{{ product.name if product else '' }}</b></p>
    <p>Current Branch: <b>{{ branches_map.get(lens.branch_id, '') }}</b></p>
    <p>SPH {{ lens.sph }} CYL {{ lens.cyl }} AXIS {{ lens.axis }} ADD {{ lens.add_power }}</p>
    <p>Current Quantity in this branch: <b id="currentQty">{{ lens.quantity }}</b></p>
    <form method="post">
        <label>Select Branch To Restock</label><br>
        <select name="branch_id" required>
            {% for b in branches %}<option value="{{ b.id }}" {% if lens.branch_id == b.id %}selected{% endif %}>{{ b.name }}</option>{% endfor %}
        </select><br><br>
        <label>Number of lenses to add</label><br>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0 12px 0">
            <button type="button" class="btn-gray" onclick="quickAdd('add_qty',1)">+1</button>
            <button type="button" class="btn-gray" onclick="quickAdd('add_qty',2)">+2</button>
            <button type="button" class="btn-gray" onclick="quickAdd('add_qty',5)">+5</button>
            <button type="button" class="btn-gray" onclick="quickAdd('add_qty',10)">+10</button>
            <button type="button" class="btn-gray" onclick="quickAdd('add_qty',20)">+20</button>
            <button type="button" class="btn-red" onclick="setQty('add_qty',0)">Clear</button>
        </div>
        <input id="add_qty" name="add_qty" type="number" min="1" value="0" placeholder="Type quantity e.g. 12" required style="max-width:220px;font-size:24px;font-weight:bold;text-align:center;padding:16px"><br>
        <p class="small">Use quick buttons or type the exact number of lenses you want to add.</p>
        <button class="btn-green" type="submit">Add Stock To Selected Branch</button>
    </form></div><a class="btn" href="/lens-powers">Back</a>
    <script>
    function setQty(id, value){
        const input = document.getElementById(id);
        input.value = Math.max(0, parseInt(value || 0));
        input.focus();
        input.select();
    }
    function quickAdd(id, amount){
        const input = document.getElementById(id);
        const current = parseInt(input.value || 0);
        input.value = current + amount;
        input.focus();
        input.select();
    }
    window.addEventListener('load', function(){
        const input = document.getElementById('add_qty');
        if(input){ input.focus(); input.select(); }
    });
    </script>
    """, lens=lens, product=product, branches=branches, branches_map={b.id: b.name for b in branches})


@app.route("/lens-restock-center", methods=["GET", "POST"])
def lens_restock_center():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can bulk restock lens powers."
    branches = Branch.query.order_by(Branch.name).all()
    selected_branch = int(request.values.get("branch_id") or (branches[0].id if branches else 1))
    selected_product = request.values.get("product_id")
    low_only = request.values.get("low_only") == "1"
    message = ""

    if request.method == "POST":
        updated = 0
        corrected = 0
        added = 0
        adjustment_reason = (request.form.get("adjustment_reason") or "Stock correction / restock").strip()

        for key, value in request.form.items():
            if not key.startswith("correct_qty_"):
                continue
            try:
                lens_id = int(key.replace("correct_qty_", ""))
                correct_qty = max(0, int(value or 0))
            except Exception:
                continue

            lens = LensPower.query.get(lens_id)
            if not lens or int(lens.branch_id or 0) != selected_branch:
                continue

            old_qty = int(lens.quantity or 0)
            if correct_qty != old_qty:
                lens.quantity = correct_qty
                corrected += 1
                updated += 1
                audit_log(
                    "Lens Quantity Corrected",
                    f"Lens power ID {lens.id}: old qty {old_qty}, corrected qty {correct_qty}. Reason: {adjustment_reason}"
                )

        for key, value in request.form.items():
            if not key.startswith("add_qty_"):
                continue
            try:
                lens_id = int(key.replace("add_qty_", ""))
                add_qty = max(0, int(value or 0))
            except Exception:
                continue

            if add_qty <= 0:
                continue

            lens = LensPower.query.get(lens_id)
            if lens and int(lens.branch_id or 0) == selected_branch:
                old_qty = int(lens.quantity or 0)
                lens.quantity = old_qty + add_qty
                added += 1
                updated += 1
                audit_log(
                    "Bulk Lens Restock Added",
                    f"Lens power ID {lens.id}: old qty {old_qty}, added {add_qty}, new qty {lens.quantity}. Reason: {adjustment_reason}"
                )

        db.session.commit()
        message = f"Saved successfully. Corrected {corrected} power(s), added stock to {added} power(s)."

    product_query = Product.query.filter(Product.branch_id == selected_branch, Product.category.contains("Lens"))
    products = product_query.order_by(Product.name).all()
    lens_query = LensPower.query.filter(LensPower.branch_id == selected_branch)
    if selected_product:
        lens_query = lens_query.filter(LensPower.product_id == int(selected_product))
    if low_only:
        lens_query = lens_query.filter(LensPower.quantity <= 2)
    lens_rows = lens_query.order_by(LensPower.product_id, LensPower.sph, LensPower.add_power).all()
    products_map = {p.id: p.name for p in Product.query.all()}
    return page("Lens Restock Center", """
    <div class="card"><h2>Bulk Lens Restock Center</h2>
    <p class="small">Select a branch, filter the lens powers, correct wrong stock quantities, add new stock, and save all at once.</p>
    {% if message %}<div class="alert success"><b>{{ message }}</b></div>{% endif %}
    <form method="get" class="no-print">
        <div class="two">
            <div><label>Select Branch</label><br><select name="branch_id" onchange="this.form.submit()">{% for b in branches %}<option value="{{ b.id }}" {% if selected_branch == b.id %}selected{% endif %}>{{ b.name }}</option>{% endfor %}</select></div>
            <div><label>Select Lens Product</label><br><select name="product_id" onchange="this.form.submit()"><option value="">All Lens Products</option>{% for p in products %}<option value="{{ p.id }}" {% if selected_product and selected_product|int == p.id %}selected{% endif %}>{{ p.name }} - {{ p.subcategory }}</option>{% endfor %}</select></div>
        </div>
        <label><input type="checkbox" name="low_only" value="1" {% if low_only %}checked{% endif %} onchange="this.form.submit()"> Show low stock only</label>
    </form>
    <hr>
    <form method="post">
        <input type="hidden" name="branch_id" value="{{ selected_branch }}">
        {% if selected_product %}<input type="hidden" name="product_id" value="{{ selected_product }}">{% endif %}
        {% if low_only %}<input type="hidden" name="low_only" value="1">{% endif %}

        <div class="alert success no-print">
            <b>New correction mode:</b> Edit <b>Correct Qty</b> when the current quantity is wrong. Use <b>Add Qty</b> when you are adding new stock. Both can be saved together.
        </div>

        <label>Reason for adjustment / correction</label><br>
        <input name="adjustment_reason" placeholder="e.g. Wrong input, stock count correction, new stock received, damaged lens" style="max-width:650px"><br><br>

        <table>
            <tr>
                <th>Lens</th>
                <th>SPH</th>
                <th>CYL</th>
                <th>AXIS</th>
                <th>ADD</th>
                <th>Current Qty</th>
                <th>Correct Qty</th>
                <th>Quick Correct</th>
                <th>Add Qty</th>
                <th>Quick Add</th>
            </tr>
        {% for l in lens_rows %}<tr>
            <td>{{ products_map.get(l.product_id, '') }}</td>
            <td>{{ l.sph }}</td><td>{{ l.cyl }}</td><td>{{ l.axis }}</td><td>{{ l.add_power }}</td>
            <td>{% if l.quantity <= 2 %}<span class="badge-low">LOW</span> {% endif %}<b>{{ l.quantity }}</b></td>
            <td>
                <input id="correct_qty_{{ l.id }}" type="number" name="correct_qty_{{ l.id }}" min="0" value="{{ l.quantity }}" style="max-width:115px;font-size:18px;font-weight:bold;text-align:center;padding:12px">
            </td>
            <td style="white-space:nowrap">
                <button type="button" class="btn-gray" onclick="quickCorrect('correct_qty_{{ l.id }}',1)">+1</button>
                <button type="button" class="btn-gray" onclick="quickCorrect('correct_qty_{{ l.id }}',5)">+5</button>
                <button type="button" class="btn-gray" onclick="quickCorrect('correct_qty_{{ l.id }}',10)">+10</button>
                <button type="button" class="btn-gray" onclick="quickCorrect('correct_qty_{{ l.id }}',-1)">-1</button>
                <button type="button" class="btn-gray" onclick="quickCorrect('correct_qty_{{ l.id }}',-5)">-5</button>
                <button type="button" class="btn-red" onclick="setQty('correct_qty_{{ l.id }}',0)">Zero</button>
            </td>
            <td>
                <input id="add_qty_{{ l.id }}" type="number" name="add_qty_{{ l.id }}" min="0" value="0" style="max-width:115px;font-size:18px;font-weight:bold;text-align:center;padding:12px">
            </td>
            <td style="white-space:nowrap">
                <button type="button" class="btn-gray" onclick="quickAdd('add_qty_{{ l.id }}',1)">+1</button>
                <button type="button" class="btn-gray" onclick="quickAdd('add_qty_{{ l.id }}',2)">+2</button>
                <button type="button" class="btn-gray" onclick="quickAdd('add_qty_{{ l.id }}',5)">+5</button>
                <button type="button" class="btn-gray" onclick="quickAdd('add_qty_{{ l.id }}',10)">+10</button>
                <button type="button" class="btn-gray" onclick="quickAdd('add_qty_{{ l.id }}',20)">+20</button>
                <button type="button" class="btn-red" onclick="setQty('add_qty_{{ l.id }}',0)">Clear</button>
            </td>
        </tr>{% else %}<tr><td colspan="10">No lens powers found for this branch/filter.</td></tr>{% endfor %}
        </table><br>
        <button class="btn-green" type="submit" style="font-size:18px;padding:15px 24px">Save All Corrections / Restock</button>
    </form></div>
    <script>
    function setQty(id, value){
        const input = document.getElementById(id);
        if(!input) return;
        input.value = Math.max(0, parseInt(value || 0));
        input.focus();
        input.select();
    }
    function quickAdd(id, amount){
        const input = document.getElementById(id);
        if(!input) return;
        const current = parseInt(input.value || 0);
        input.value = Math.max(0, current + amount);
        input.focus();
        input.select();
    }
    function quickCorrect(id, amount){
        quickAdd(id, amount);
    }
    window.addEventListener('load', function(){
        const first = document.querySelector('input[name^="correct_qty_"]');
        if(first){ first.focus(); first.select(); }
    });
    </script>
    """, branches=branches, selected_branch=selected_branch, products=products, selected_product=selected_product, low_only=low_only, lens_rows=lens_rows, products_map=products_map, message=message)



@app.route("/restock")
def restock():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can restock."
    return page("Restock Center", """
    <div class="card"><h2>Restock Center</h2><p>Use Products / Stock to restock general products. Use Lens Restock Center to restock exact lens powers by branch.</p><a class="btn-green btn" href="/products">Restock Products</a><a class="btn-green btn" href="/lens-restock-center">Bulk Restock Lens Powers</a><a class="btn" href="/lens-powers">View Lens Powers</a></div><a class="btn" href="/">Back</a>
    """)


@app.route("/generate-power-grid", methods=["GET", "POST"])
def generate_power_grid():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can generate power grid."

    branches = Branch.query.order_by(Branch.name).all()
    selected_branch = request.values.get("branch_id") or (str(branches[0].id) if branches else "1")
    selected_branch_id = int(selected_branch)

    # Show all lens products so the manager can copy/generate a lens grid into any selected branch.
    # The save logic below creates the same product under the selected branch if it is missing.
    product_list = Product.query.filter(Product.category.contains("Lens")).order_by(Product.branch_id, Product.name).all()
    branches_map = {b.id: b.name for b in branches}
    message = ""

    if request.method == "POST":
        product_id = request.form.get("product_id")
        product = Product.query.get(int(product_id)) if product_id else None
        lens_type = request.form.get("lens_type")
        sph_from = request.form.get("sph_from") or "-20.00"
        sph_to = request.form.get("sph_to") or "20.00"
        sph_step = request.form.get("sph_step") or request.form.get("step") or "0.25"
        add_from = request.form.get("add_from") or "1.00"
        add_to = request.form.get("add_to") or "3.00"
        add_step = request.form.get("add_step") or "0.25"
        generate_cylinder = request.form.get("generate_cylinder") == "1"
        cyl_from = request.form.get("cyl_from") or "-0.25"
        cyl_to = request.form.get("cyl_to") or "-6.00"
        cyl_step = request.form.get("cyl_step") or "0.25"
        axis_mode = request.form.get("axis_mode") or "blank"
        axis_from = int(request.form.get("axis_from") or 0)
        axis_to = int(request.form.get("axis_to") or 180)
        axis_step = int(request.form.get("axis_step") or 10)
        custom_axes = request.form.get("custom_axes") or ""
        default_qty = int(request.form.get("default_qty") or 0)
        created = 0
        updated = 0

        if product:
            # BRANCH SAFETY FIX:
            # Generate the grid under the selected branch only.
            # If the chosen lens product belongs to another branch, copy/create the same product
            # inside the selected branch first, then generate the powers under that branch product.
            if int(product.branch_id or 0) != selected_branch_id:
                target_product = Product.query.filter_by(
                    branch_id=selected_branch_id,
                    name=product.name,
                    category=product.category,
                    subcategory=product.subcategory
                ).first()
                if not target_product:
                    target_product = Product(
                        branch_id=selected_branch_id,
                        name=product.name,
                        category=product.category,
                        subcategory=product.subcategory,
                        retail_price=product.retail_price,
                        wholesale_price=product.wholesale_price,
                        quantity=0
                    )
                    db.session.add(target_product)
                    db.session.flush()
                product = target_product

            sph_values = decimal_range(sph_from, sph_to, sph_step)
            add_values = [None]
            if lens_type in ["Bifocal Lens", "Progressive Lens"]:
                add_values = decimal_range(add_from, add_to, add_step)

            cyl_values = [""]
            if generate_cylinder:
                cyl_values = [fmt_power(c) for c in decimal_range(cyl_from, cyl_to, cyl_step)]

            axis_values = [""]
            if generate_cylinder and axis_mode == "range":
                if axis_step <= 0:
                    axis_step = 10
                if axis_from <= axis_to:
                    axis_values = [str(a) for a in range(axis_from, axis_to + 1, axis_step)]
                else:
                    axis_values = [str(a) for a in range(axis_from, axis_to - 1, -axis_step)]
            elif generate_cylinder and axis_mode == "custom":
                axis_values = []
                for a in custom_axes.replace(";", ",").split(","):
                    a = a.strip()
                    if not a:
                        continue
                    try:
                        a_int = int(a)
                        if 0 <= a_int <= 180:
                            axis_values.append(str(a_int))
                    except Exception:
                        pass
                if not axis_values:
                    axis_values = [""]

            for sph in sph_values:
                sph_s = fmt_power(sph)
                for cyl_s in cyl_values:
                    current_axis_values = [""] if not cyl_s else axis_values
                    for axis_s in current_axis_values:
                        for add_val in add_values:
                            add_s = "" if add_val is None else fmt_power(add_val)
                            existing = LensPower.query.filter_by(
                                product_id=product.id,
                                branch_id=selected_branch_id,
                                sph=sph_s,
                                cyl=cyl_s,
                                axis=axis_s,
                                add_power=add_s
                            ).first()
                            if existing:
                                if default_qty:
                                    existing.quantity = int(existing.quantity or 0) + default_qty
                                updated += 1
                            else:
                                db.session.add(LensPower(
                                    product_id=product.id,
                                    branch_id=selected_branch_id,
                                    sph=sph_s,
                                    cyl=cyl_s,
                                    axis=axis_s,
                                    add_power=add_s,
                                    quantity=default_qty
                                ))
                                created += 1

            db.session.commit()
            audit_log(
                "Power Grid Generated",
                f"Branch ID {selected_branch_id}, Product {product.name}, Cylinder {generate_cylinder}, Created {created}, Updated {updated}"
            )
            message = f"Created {created} powers and updated {updated} existing powers for the selected branch."
        else:
            message = "Please select a valid lens product."

    return page("Generate Power Grid", """
    {% if message %}<div class="alert success"><b>{{ message }}</b></div>{% endif %}
    <div class="card"><h2>Generate Lens Power Grid</h2>
    <p>This page can generate SPH powers only, or SPH + CYL powers, for the selected branch without mixing branch stock.</p>
    <form method="get" class="no-print">
        <label>Select Branch First</label><br>
        <select name="branch_id" onchange="this.form.submit()" required>
            {% for b in branches %}<option value="{{ b.id }}" {% if selected_branch|int == b.id %}selected{% endif %}>{{ b.name }}</option>{% endfor %}
        </select>
    </form>
    <hr>
    <form method="post">
        <input type="hidden" name="branch_id" value="{{ selected_branch }}">
        <label>Select Lens Product</label><br>
        <select name="product_id" required>
            {% for p in product_list %}
            <option value="{{ p.id }}">{{ p.name }} - {{ p.category }} - {{ p.subcategory }} - {{ branches_map.get(p.branch_id, 'Branch ID ' ~ p.branch_id) }}</option>
            {% else %}<option value="">No lens product found</option>{% endfor %}
        </select><br><br>

        <label>Lens Type</label><br><select name="lens_type"><option>Single Vision Lens</option><option>Bifocal Lens</option><option>Progressive Lens</option></select><br><br>

        <div class="card" style="background:#f8fafc">
            <h3>1. SPH Power Range</h3>
            <div class="two"><div><label>SPH From</label><input name="sph_from" value="-20.00"></div><div><label>SPH To</label><input name="sph_to" value="20.00"></div></div><br>
            <label>SPH Step</label><br><input name="sph_step" value="0.25"><br>
            <p class="small">Example: -20.00 to +20.00 with 0.25 step.</p>
        </div>

        <div class="card" style="background:#eef6ff">
            <h3>2. Cylinder Power Generator</h3>
            <label><input type="checkbox" name="generate_cylinder" value="1"> Generate CYL powers also</label>
            <p class="small">Use this for cylinder lens stock. Example CYL -0.25 to -6.00 with 0.25 step.</p>
            <div class="two"><div><label>CYL From</label><input name="cyl_from" value="-0.25"></div><div><label>CYL To</label><input name="cyl_to" value="-6.00"></div></div><br>
            <label>CYL Step</label><br><input name="cyl_step" value="0.25"><br><br>

            <label>AXIS Option</label><br>
            <select name="axis_mode">
                <option value="blank">Leave AXIS blank / stock cylinder only</option>
                <option value="range">Generate AXIS by range</option>
                <option value="custom">Use custom AXIS list</option>
            </select><br><br>
            <div class="two"><div><label>AXIS From</label><input name="axis_from" type="number" value="0"></div><div><label>AXIS To</label><input name="axis_to" type="number" value="180"></div></div><br>
            <label>AXIS Step</label><br><input name="axis_step" type="number" value="10"><br><br>
            <label>Custom AXIS List</label><br><input name="custom_axes" placeholder="Example: 0, 90, 180"><br>
            <p class="small"><b>Important:</b> Axis range can create many rows. For normal stock, leaving AXIS blank is usually faster.</p>
        </div>

        <div class="card" style="background:#f8fafc">
            <h3>3. ADD Power Range</h3>
            <p class="small">Used for Bifocal and Progressive only.</p>
            <div class="two"><div><label>ADD From</label><input name="add_from" value="1.00"></div><div><label>ADD To</label><input name="add_to" value="3.00"></div></div><br>
            <label>ADD Step</label><br><input name="add_step" value="0.25"><br>
        </div>

        <label>Default Quantity for each generated power</label><br><input name="default_qty" type="number" value="0"><br><br>
        <button class="btn-green" type="submit">Generate SPH / CYL Powers For Selected Branch</button>
    </form></div><a class="btn" href="/">Back</a>
    """, product_list=product_list, message=message, branches=branches, selected_branch=selected_branch, branches_map=branches_map)


@app.route("/pos", methods=["GET", "POST"])
def pos():
    if not logged_in():
        return redirect(url_for("login"))

    # SMART, SIMPLE MAKE SALES PAGE
    # Flow: Lenses / Frames -> Lens Category -> Lens Material -> Matching Powers Only -> Cart -> Checkout
    view = request.values.get("view", "none")
    lens_category = request.values.get("lens_category", "")
    lens_material = request.values.get("lens_material", "")

    if "pos_cart" not in session:
        session["pos_cart"] = []

    if "pos_customer" not in session:
        session["pos_customer"] = {
            "customer_name": "",
            "customer_phone": "",
            "branch_id": session.get("branch_id"),
            "price_type": "retail"
        }

    customer = session.get("pos_customer", {})
    selected_branch_id = int(request.values.get("branch_id") or customer.get("branch_id") or session.get("branch_id") or 1)
    if not is_manager():
        selected_branch_id = int(session.get("branch_id") or 1)

    price_type = request.values.get("price_type") or customer.get("price_type") or "retail"
    customer_name = request.values.get("customer_name") or customer.get("customer_name", "")
    customer_phone = request.values.get("customer_phone") or customer.get("customer_phone", "")

    def short_lens_name(product):
        category = product.category or ""
        sub = product.subcategory or ""
        if "Single Vision" in category:
            prefix = "SV"
        elif "Bifocal" in category:
            prefix = "Bifocal"
        elif "Progressive" in category:
            prefix = "Prog"
        else:
            prefix = category or "Lens"

        if "Blue" in sub:
            material = "BlueCut Photo"
        elif "Photo" in sub:
            material = "Photo AR"
        elif "White" in sub:
            material = "White"
        else:
            material = sub or "Lens"
        return f"{prefix} {material}"

    def stock_badge(qty):
        qty = int(qty or 0)
        if qty <= 0:
            return "🔴 Out of Stock"
        if qty <= 2:
            return "🟡 Low Stock"
        return "🟢 Available"

    if request.method == "POST":
        selected_branch_id = int(request.form.get("branch_id") or selected_branch_id)
        if not is_manager():
            selected_branch_id = int(session.get("branch_id") or 1)

        price_type = request.form.get("price_type") or "retail"
        customer_name = request.form.get("customer_name") or ""
        customer_phone = request.form.get("customer_phone") or ""

        session["pos_customer"] = {
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "branch_id": selected_branch_id,
            "price_type": price_type
        }

        cart = session.get("pos_cart", [])
        added_count = 0

        if view == "lenses":
            lens_power_id = request.form.get("lens_power_id")
            unit_type = request.form.get("unit_type") or "half"
            custom_qty = int(request.form.get("custom_qty") or 0)

            if lens_power_id:
                lp = LensPower.query.get(int(lens_power_id))
                if not lp or int(lp.branch_id or 0) != selected_branch_id:
                    return page("Wrong Branch Lens", """
                    <div class="card">
                        <h2>Wrong Branch Lens</h2>
                        <p>This lens power does not belong to the selected branch.</p>
                        <a class="btn" href="/pos?view=lenses">Back</a>
                    </div>
                    """)

                product = Product.query.get(lp.product_id)
                if not product:
                    return page("Product Not Found", """
                    <div class="card">
                        <h2>Product Not Found</h2>
                        <p>The selected lens product was not found.</p>
                        <a class="btn" href="/pos?view=lenses">Back</a>
                    </div>
                    """)

                if unit_type == "pair":
                    qty = 2
                    unit_label = "1 Pair"
                elif unit_type == "custom":
                    qty = custom_qty
                    unit_label = "Custom Qty"
                else:
                    qty = 1
                    unit_label = "Half Pair"

                if qty <= 0:
                    return page("Invalid Quantity", """
                    <div class="card"><h2>Invalid Quantity</h2><p>Please enter a valid quantity.</p><a class="btn" href="/pos?view=lenses">Back</a></div>
                    """)

                if qty > int(lp.quantity or 0):
                    return page("Insufficient Lens Stock", """
                    <div class="card"><h2>Insufficient Lens Stock</h2><p>The selected power does not have enough stock.</p><a class="btn" href="/pos?view=lenses">Back</a></div>
                    """)

                price = product.wholesale_price if price_type == "wholesale" else product.retail_price
                lens_text = f"{unit_label} | SPH {lp.sph or ''} CYL {lp.cyl or ''} AXIS {lp.axis or ''} ADD {lp.add_power or ''}".strip()

                cart.append({
                    "type": "lens",
                    "product_id": product.id,
                    "lens_power_id": lp.id,
                    "product_name": short_lens_name(product),
                    "lens_power": lens_text,
                    "quantity": qty,
                    "unit_price": float(price or 0),
                    "subtotal": float(price or 0) * qty,
                })
                added_count += 1

        elif view == "frames":
            for key, value in request.form.items():
                if not key.startswith("qty_"):
                    continue
                product_id = int(key.replace("qty_", ""))
                qty = int(value or 0)
                if qty <= 0:
                    continue

                product = Product.query.get(product_id)
                if not product or int(product.branch_id or 0) != selected_branch_id:
                    continue

                if qty > int(product.quantity or 0):
                    return page("Insufficient Product Stock", """
                    <div class="card"><h2>Insufficient Product Stock</h2><p>You selected more quantity than available.</p><a class="btn" href="/pos?view=frames">Back</a></div>
                    """)

                price = product.wholesale_price if price_type == "wholesale" else product.retail_price
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
            return page("No Item Selected", """
            <div class="card">
                <h2>No Item Selected</h2>
                <p>Please select a lens power or enter quantity for a frame/accessory.</p>
                <a class="btn" href="/pos">Back to Make Sale</a>
            </div>
            """)

        return redirect(url_for("pos", view=view, lens_category=lens_category, lens_material=lens_material, branch_id=selected_branch_id, price_type=price_type, customer_name=customer_name, customer_phone=customer_phone))

    product_query = Product.query.filter_by(branch_id=selected_branch_id)

    if view == "lenses":
        product_query = product_query.filter(Product.category.contains("Lens"))
        if lens_category:
            product_query = product_query.filter(Product.category == lens_category)
        if lens_material:
            product_query = product_query.filter(Product.subcategory == lens_material)
    elif view == "frames":
        product_query = product_query.filter(~Product.category.contains("Lens"))
    else:
        product_query = Product.query.filter(Product.id == -1)

    product_list = product_query.order_by(Product.category, Product.subcategory, Product.name).all()

    lens_map = {}
    lens_stock_map = {}
    if view == "lenses":
        for p in product_list:
            powers = LensPower.query.filter_by(product_id=p.id, branch_id=selected_branch_id).filter(LensPower.quantity > 0).order_by(LensPower.sph, LensPower.cyl, LensPower.add_power).all()
            lens_map[p.id] = powers
            lens_stock_map[p.id] = sum(int(l.quantity or 0) for l in powers)

    cart = session.get("pos_cart", [])
    cart_total = sum(float(i.get("subtotal", 0) or 0) for i in cart)

    lens_categories = [
        ("Single Vision Lens", "🟦 Single Vision"),
        ("Bifocal Lens", "🟩 Bifocal"),
        ("Progressive Lens", "🟨 Progressive"),
    ]
    lens_materials = [
        ("White Lens", "White"),
        ("Photo AR", "Photo AR"),
        ("Blue Cut Photo AR", "BlueCut Photo"),
    ]

    return page("POS", """
    <style>
        .pos-big-btn{display:block;color:white;padding:26px;border-radius:18px;text-decoration:none;font-size:22px;font-weight:bold;text-align:center;box-shadow:0 6px 18px #0002;min-height:90px}
        .pos-small-btn{display:inline-block;padding:16px 22px;border-radius:14px;text-decoration:none;margin:6px;font-weight:bold;background:#e2e8f0;color:#0f172a}.pos-small-btn.active{background:#003366;color:white}
        .pos-card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:15px}.pos-item-card{border:1px solid #dbe4ee;border-radius:16px;padding:16px;background:#fff;box-shadow:0 3px 10px #0001}.floating-cart{border:2px solid #198754;background:#f8fff9}.dark .pos-item-card{background:#111827;border-color:#374151}.dark .floating-cart{background:#0b1220}
        .cart-total-line{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:12px;flex-wrap:wrap}.cart-remove{padding:7px 10px;min-height:auto}.checkout-card .form-grid{display:grid;grid-template-columns:1fr;gap:8px}.checkout-card label{font-weight:700;font-size:13px}
    </style>

    <div class="card">
        <h2>Make Sale - Simple Optical POS</h2>
        <p class="small">Choose category first, then material, then select only matching lens powers. No bulky full-table loading.</p>
        <div class="two">
            <div><label>Customer Name</label><input id="customer_name" value="{{ customer_name }}" placeholder="Customer Name"></div>
            <div><label>Customer Phone</label><input id="customer_phone" value="{{ customer_phone }}" placeholder="Customer Phone"></div>
        </div><br>
        {% if session['role'] == 'manager' %}
        <label>Branch</label><br>
        <select id="branch_id" onchange="reloadPOS()">
            {% for b in Branch.query.all() %}<option value="{{ b.id }}" {% if selected_branch_id == b.id %}selected{% endif %}>{{ b.name }}</option>{% endfor %}
        </select><br><br>
        {% else %}
        <input type="hidden" id="branch_id" value="{{ selected_branch_id }}">
        {% endif %}
        <label>Price Type</label><br>
        <select id="price_type" onchange="reloadPOS()">
            <option value="retail" {% if price_type == 'retail' %}selected{% endif %}>Retail / End User</option>
            <option value="wholesale" {% if price_type == 'wholesale' %}selected{% endif %}>Wholesale</option>
        </select>
    </div>

    <div class="sales-layout">
        <div class="sales-left">
            <div class="card step-box">
                <h3>Step 1: Select Sales Type</h3>
                <div class="pos-card-grid">
                    <a class="pos-big-btn" onclick="return posLink(this)" href="/pos?view=lenses" style="background:#2563eb">👓 Lenses<br><span style="font-size:14px;font-weight:normal">SV, Bifocal, Progressive</span></a>
                    <a class="pos-big-btn" onclick="return posLink(this)" href="/pos?view=frames" style="background:#16a34a">🕶️ Frames & Accessories<br><span style="font-size:14px;font-weight:normal">Frames, cases, cleaners, cloths</span></a>
                </div>
            </div>

            {% if view == 'lenses' %}
            <div class="card"><h3>Step 2: Select Lens Category</h3>
                {% for value, label in lens_categories %}
                <a class="pos-small-btn {% if lens_category == value %}active{% endif %}" onclick="return posLink(this)" href="/pos?view=lenses&lens_category={{ value }}">{{ label }}</a>
                {% endfor %}
            </div>
            {% if lens_category %}
            <div class="card"><h3>Step 3: Select Lens Material</h3>
                {% for value, label in lens_materials %}
                <a class="pos-small-btn {% if lens_material == value %}active{% endif %}" onclick="return posLink(this)" href="/pos?view=lenses&lens_category={{ lens_category }}&lens_material={{ value }}">{{ label }}</a>
                {% endfor %}
            </div>
            {% endif %}

            {% if lens_category and lens_material %}
            <div class="card">
                <h3>Step 4: Select Power</h3>
                <div class="pos-card-grid">
                    {% for p in product_list %}
                    <form class="pos-item-card lens-product-card saleForm" method="post" onsubmit="copyCustomerToForm(this)">
                        <input type="hidden" name="view" value="lenses"><input type="hidden" name="lens_category" value="{{ lens_category }}"><input type="hidden" name="lens_material" value="{{ lens_material }}">
                        <input type="hidden" name="customer_name"><input type="hidden" name="customer_phone"><input type="hidden" name="branch_id"><input type="hidden" name="price_type">
                        <h3>{{ short_lens_name(p) }}</h3>
                        <p><b>Stock:</b> {{ lens_stock_map.get(p.id, 0) }} | {{ stock_badge(lens_stock_map.get(p.id, 0)) }}</p>
                        <p class="small">Retail ₦{{ money(p.retail_price) }} | Wholesale ₦{{ money(p.wholesale_price) }}</p>
                        <label>Select Power</label>
                        <select name="lens_power_id" required><option value="">Choose power</option>{% for lp in lens_map.get(p.id, []) %}<option value="{{ lp.id }}">SPH {{ lp.sph }} CYL {{ lp.cyl }} AXIS {{ lp.axis }} ADD {{ lp.add_power }} | Qty {{ lp.quantity }}</option>{% endfor %}</select><br><br>
                        <label>Quantity Type</label><select name="unit_type"><option value="half">Half Pair / 1 Lens</option><option value="pair">1 Pair / 2 Lenses</option><option value="custom">Custom Quantity</option></select>
                        <input name="custom_qty" type="number" min="0" placeholder="Custom quantity only"><br><br>
                        <button class="btn-green" type="submit">Add Lens To Cart</button>
                    </form>
                    {% else %}<div class="alert"><b>No lens product found.</b> Check selected branch, category and material.</div>{% endfor %}
                </div>
            </div>
            {% endif %}
            {% endif %}

            {% if view == 'frames' %}
            <form class="card saleForm" method="post" onsubmit="copyCustomerToForm(this)">
                <input type="hidden" name="view" value="frames"><input type="hidden" name="customer_name"><input type="hidden" name="customer_phone"><input type="hidden" name="branch_id"><input type="hidden" name="price_type">
                <h3>Add Frames / Accessories</h3>
                <input id="productSearch" placeholder="🔍 Search frame, case, cleaner, cloth..." onkeyup="filterProductCards()"><br><br>
                <div class="pos-card-grid">
                    {% for p in product_list %}
                    <div class="pos-item-card product-card"><h3>{{ p.name }}</h3><p>{{ p.category }} - {{ p.subcategory }}</p><p><b>Stock:</b> {{ p.quantity }} | {{ stock_badge(p.quantity) }}</p><p class="small">Retail ₦{{ money(p.retail_price) }} | Wholesale ₦{{ money(p.wholesale_price) }}</p><input name="qty_{{ p.id }}" type="number" min="0" placeholder="Quantity"></div>
                    {% else %}<div class="alert"><b>No frame/accessory found.</b> Check selected branch and stock.</div>{% endfor %}
                </div><br><button class="btn-green" type="submit">Add Selected Products To Cart</button>
            </form>
            {% endif %}
        </div>

        <div class="checkout-panel" id="mobileCheckout">
            <div class="card floating-cart current-sale-box">
                <h3>🛒 Current Sale</h3>
                {% if cart %}
                <div class="quick-summary">
                    <div class="mini-card">Items<br>{{ cart|length }}</div>
                    <div class="mini-card">Total<br>₦{{ money(cart_total) }}</div>
                </div>
                <div class="cart-table-wrap">
                    <table><tr><th>Item</th><th>Qty</th><th>Total</th><th></th></tr>{% for item in cart %}<tr><td>{{ item.product_name }}<br><small>{{ item.lens_power }}</small></td><td>{{ item.quantity }}</td><td>₦{{ money(item.subtotal) }}</td><td><a class="btn-red btn cart-remove" href="/pos/remove/{{ loop.index0 }}">X</a></td></tr>{% endfor %}</table>
                </div>
                <div class="cart-total-line"><h2>Total: ₦{{ money(cart_total) }}</h2><a class="btn-red btn" href="/pos/clear">Clear Cart</a></div>
                {% else %}<div class="alert">No item in cart yet.</div>{% endif %}
            </div>
            {% if cart %}<div class="card checkout-card"><h3>Checkout</h3><form method="post" action="/pos/checkout"><div class="form-grid"><label>Discount</label><input name="discount" type="number" step="0.01" value="0"><label>Amount Paid</label><input name="amount_paid" type="number" step="0.01" placeholder="Amount Paid"><label>Manager PIN for Discount</label><input name="manager_pin" type="password" placeholder="Only if discount is used"><label>Payment Method</label><select name="payment_method"><option>Cash</option><option>Transfer</option><option>POS</option><option>Split Payment</option><option>Credit</option></select><br><button class="complete-sale-btn" type="submit">Complete Sale / Print Receipt</button></div></form></div>{% endif %}
        </div>
    </div>


    {% if cart %}
    <div class="mobile-cart-bar no-print">
        <div>🛒 {{ cart|length }} item(s) · ₦{{ money(cart_total) }}</div>
        <a href="#mobileCheckout">Checkout</a>
    </div>
    {% endif %}

    <script>
    function customerParams(){
        const params = new URLSearchParams();
        params.set('branch_id', document.getElementById('branch_id').value || '1');
        params.set('price_type', document.getElementById('price_type').value || 'retail');
        params.set('customer_name', document.getElementById('customer_name').value || '');
        params.set('customer_phone', document.getElementById('customer_phone').value || '');
        return params;
    }
    function posLink(a){
        const url = new URL(a.href, window.location.origin);
        const params = customerParams();
        params.forEach((v,k)=>url.searchParams.set(k,v));
        window.location.href = url.toString();
        return false;
    }
    function reloadPOS(){
        const url = new URL(window.location.href);
        const params = customerParams();
        params.forEach((v,k)=>url.searchParams.set(k,v));
        window.location.href = url.toString();
    }
    function copyCustomerToForm(form){
        form.querySelector('input[name="customer_name"]').value = document.getElementById('customer_name').value || '';
        form.querySelector('input[name="customer_phone"]').value = document.getElementById('customer_phone').value || '';
        form.querySelector('input[name="branch_id"]').value = document.getElementById('branch_id').value || '1';
        form.querySelector('input[name="price_type"]').value = document.getElementById('price_type').value || 'retail';
    }
    function filterProductCards(){const q=document.getElementById('productSearch').value.toLowerCase();document.querySelectorAll('.product-card').forEach(card=>{card.style.display=card.innerText.toLowerCase().includes(q)?'block':'none';});}
    </script>
    """, view=view, lens_category=lens_category, lens_material=lens_material, lens_categories=lens_categories, lens_materials=lens_materials, product_list=product_list, lens_map=lens_map, lens_stock_map=lens_stock_map, cart=cart, cart_total=cart_total, customer_name=customer_name, customer_phone=customer_phone, price_type=price_type, selected_branch_id=selected_branch_id, short_lens_name=short_lens_name, stock_badge=stock_badge)


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

    sale_branch_id = int(customer.get("branch_id") or session.get("branch_id") or 1)
    if not is_manager():
        sale_branch_id = int(session.get("branch_id") or 1)

    # Final stock validation before receipt is created.
    # BRANCH SAFETY FIX:
    # Lens stock is validated/deducted ONLY from LensPower.quantity for the sale branch.
    # Frames/accessories are validated/deducted ONLY from Product.quantity for the sale branch.
    # No product from another branch can be checked out on this receipt.
    product_deductions = {}
    for item in cart:
        qty = int(item.get("quantity") or 0)
        if qty <= 0:
            return page("Invalid Quantity", "<div class='card'><h2>Invalid Quantity</h2><p>One item in the cart has invalid quantity.</p><a class='btn' href='/pos'>Back</a></div>")

        product = Product.query.get(int(item.get("product_id")))
        if not product or int(product.branch_id or 0) != sale_branch_id:
            return page("Wrong Branch Product", "<div class='card'><h2>Wrong Branch Product</h2><p>This cart contains a product from another branch. Please clear the cart and sell from one branch only.</p><a class='btn' href='/pos/clear'>Clear Cart</a></div>")

        if item.get("type") == "lens":
            lp = LensPower.query.get(int(item.get("lens_power_id")))
            if not lp or int(lp.branch_id or 0) != sale_branch_id or qty > int(lp.quantity or 0):
                return page("Insufficient Lens Power Stock", "<div class='card'><h2>Insufficient Lens Power Stock</h2><p>A lens power in the cart is no longer available in the requested branch/quantity.</p><a class='btn' href='/pos'>Back</a></div>")
        else:
            product_id = int(item.get("product_id"))
            product_deductions[product_id] = product_deductions.get(product_id, 0) + qty

    for product_id, qty in product_deductions.items():
        product = Product.query.get(product_id)
        if not product or int(product.branch_id or 0) != sale_branch_id or qty > int(product.quantity or 0):
            return page("Insufficient Product Stock", "<div class='card'><h2>Insufficient Product Stock</h2><p>A product in the cart is no longer available in the requested quantity.</p><a class='btn' href='/pos'>Back</a></div>")

    subtotal = sum(float(i.get("subtotal", 0) or 0) for i in cart)
    discount = float(request.form.get("discount") or 0)
    amount_paid = float(request.form.get("amount_paid") or 0)
    payment_method = request.form.get("payment_method") or "Cash"
    if discount > 0 and not check_manager_pin(request.form.get("manager_pin")):
        return page("Manager PIN Required", """
        <div class='card'>
            <h2>Manager PIN Required</h2>
            <p>A discount was entered. Please enter the correct manager PIN to approve discount.</p>
            <a class='btn' href='/pos'>Back to POS</a>
        </div>
        """)

    final_total = max(subtotal - discount, 0)
    balance = max(final_total - amount_paid, 0)

    sale = Sale(
        branch_id=sale_branch_id,
        attended_by_id=session.get("user_id"),
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
    audit_log("Sale Completed", f"Sale #{sale.id} Total {final_total} Paid {amount_paid} Balance {balance} Items {len(cart)}")

    session["pos_cart"] = []
    session["pos_customer"] = {"customer_name": "", "customer_phone": "", "branch_id": session.get("branch_id"), "price_type": "retail"}
    session.modified = True

    return redirect(url_for("receipt", sale_id=sale.id))

def build_whatsapp_invoice(sale, items, branch, setting, attended_by, change_due):
    lines = [
        "HALLELUYAH OPTICAL LABORATORY",
        "Optical Business Management System",
        "Receipt / Invoice",
        f"Receipt No: HOL-{sale.id}",
        f"Date: {sale.created_at}",
        f"Branch: {branch.name if branch else ''}",
        f"Attended By: {attended_by.username if attended_by else 'Unknown'}",
        f"Customer: {sale.customer_name}",
        f"Phone: {sale.customer_phone}",
        "",
        "Items:"
    ]

    for i in items:
        power = f" | Power: {i.lens_power}" if i.lens_power else ""
        lines.append(f"- {i.product_name}{power} | Qty: {i.quantity} | ₦{money(i.subtotal)}")

    lines += [
        "",
        f"Discount: ₦{money(sale.discount)}",
        f"Total: ₦{money(sale.total)}",
        f"Amount Paid: ₦{money(sale.amount_paid)}",
        f"Balance: ₦{money(sale.balance)}",
        f"Change Due: ₦{money(change_due)}",
        f"Payment: {sale.payment_method}",
        "",
        f"Address: {setting.address}",
        f"Office Phone: {setting.phone}",
        "Thank you for choosing Halleluyah Optical Laboratory. Your vision is our priority."
    ]

    return "\n".join(lines)


@app.route("/receipt/<int:sale_id>")
def receipt(sale_id):
    if not logged_in():
        return redirect(url_for("login"))
    sale = Sale.query.get_or_404(sale_id)
    items = SaleItem.query.filter_by(sale_id=sale.id).all()
    branch = Branch.query.get(sale.branch_id)
    setting = OfficeSetting.query.first()
    attended_by = User.query.get(sale.attended_by_id) if getattr(sale, "attended_by_id", None) else None
    change_due = max(float(sale.amount_paid or 0) - float(sale.total or 0), 0)
    whatsapp_message = build_whatsapp_invoice(sale, items, branch, setting, attended_by, change_due)
    return page("Receipt", """
    <div class="card"><center><h2>HALLELUYAH OPTICAL LABORATORY</h2><h3>Optical Business Management System</h3><h3>Receipt / Invoice</h3></center>
    <p><b>Receipt No:</b> HOL-{{ sale.id }}</p><p><b>Address:</b> {{ setting.address }}</p><p><b>Phone:</b> {{ setting.phone }}</p><p><b>Branch:</b> {{ branch.name if branch else '' }}</p><p><b>Attended By:</b> {{ attended_by.username if attended_by else 'Unknown' }}</p><p><b>Date:</b> {{ sale.created_at }}</p><p><b>Customer:</b> {{ sale.customer_name }}</p><p><b>Customer Phone:</b> {{ sale.customer_phone }}</p>
    <table><tr><th>Product</th><th>Lens Power</th><th>Qty</th><th>Unit</th><th>Subtotal</th></tr>{% for i in items %}<tr><td>{{ i.product_name }}</td><td>{{ i.lens_power }}</td><td>{{ i.quantity }}</td><td>{{ money(i.unit_price) }}</td><td>{{ money(i.subtotal) }}</td></tr>{% endfor %}</table>
    <p><b>Discount:</b> {{ money(sale.discount) }}</p><p><b>Total:</b> {{ money(sale.total) }}</p><p><b>Amount Paid:</b> {{ money(sale.amount_paid) }}</p><p><b>Balance:</b> {{ money(sale.balance) }}</p><p><b>Change Due:</b> {{ money(change_due) }}</p><p><b>Payment:</b> {{ sale.payment_method }}</p>
    <div class="no-print">
        <button onclick="window.print()">Print Receipt</button>
        <a class="btn-green btn" target="_blank" href="https://wa.me/{% if sale.customer_phone %}{{ sale.customer_phone.replace('+','').replace(' ','').replace('-','') }}{% endif %}?text={{ whatsapp_message|urlencode }}">Share Invoice on WhatsApp</a>
        <a class="btn-green btn" href="/receipt/{{ sale.id }}/thermal">80mm Thermal Receipt</a>
        <a class="btn" href="/pos">New Sale</a>
        <a class="btn" href="/">Back</a>
    </div></div>
    """, sale=sale, items=items, branch=branch, setting=setting, attended_by=attended_by, change_due=change_due, whatsapp_message=whatsapp_message)


@app.route("/receipt/<int:sale_id>/thermal")
def thermal_receipt(sale_id):
    if not logged_in():
        return redirect(url_for("login"))
    sale = Sale.query.get_or_404(sale_id)
    items = SaleItem.query.filter_by(sale_id=sale.id).all()
    branch = Branch.query.get(sale.branch_id)
    setting = OfficeSetting.query.first()
    attended_by = User.query.get(sale.attended_by_id) if getattr(sale, "attended_by_id", None) else None
    change_due = max(float(sale.amount_paid or 0) - float(sale.total or 0), 0)
    return page("Thermal Receipt", """
    <div class="thermal-receipt">
        <center>
            <h3>HALLELUYAH OPTICAL LABORATORY</h3>
            <p>Optical Business Management System</p>
            <p>{{ setting.address }}<br>{{ setting.phone }}</p>
            <b>SALES RECEIPT</b><br>
            Receipt #: HOL-{{ sale.id }}<br>
            Branch: {{ branch.name if branch else '' }}<br>
            Staff: {{ attended_by.username if attended_by else 'Unknown' }}<br>
            Date: {{ sale.created_at }}
        </center>
        <hr>
        <p>Customer: {{ sale.customer_name }}<br>Phone: {{ sale.customer_phone }}</p>
        <table>
            <tr><th>Item</th><th>Qty</th><th>Total</th></tr>
            {% for i in items %}
            <tr>
                <td>{{ i.product_name }}<br><small>{{ i.lens_power }}</small></td>
                <td>{{ i.quantity }}</td>
                <td>{{ money(i.subtotal) }}</td>
            </tr>
            {% endfor %}
        </table>
        <hr>
        <p>Discount: {{ money(sale.discount) }}<br>
        Total: <b>{{ money(sale.total) }}</b><br>
        Paid: {{ money(sale.amount_paid) }}<br>
        Balance: {{ money(sale.balance) }}<br>
        Change: {{ money(change_due) }}<br>
        Payment: {{ sale.payment_method }}</p>
        <hr>
        <center>Thank you for choosing<br>Halleluyah Optical Laboratory<br>Your vision is our priority</center>
        <div class="no-print" style="text-align:center;margin-top:15px">
            <button onclick="window.print()">Print 80mm Thermal Receipt</button>
            <a class="btn" href="/receipt/{{ sale.id }}">Full Receipt</a>
        </div>
    </div>
    """, sale=sale, items=items, branch=branch, setting=setting, attended_by=attended_by, change_due=change_due)


@app.route("/sales")
def sales():
    if not logged_in():
        return redirect(url_for("login"))
    sale_list = Sale.query.order_by(Sale.id.desc()).all() if is_manager() else Sale.query.filter_by(branch_id=session.get("branch_id")).order_by(Sale.id.desc()).all()
    branches_map = {b.id: b.name for b in Branch.query.all()}
    users_map = {u.id: u.username for u in User.query.all()}
    return page("Sales", """
    <div class="card"><h2>Sales History</h2><table><tr><th>Date</th><th>Branch</th><th>Staff Who Attended</th><th>Customer</th><th>Total</th><th>Paid</th><th>Balance</th><th>Receipt</th></tr>{% for s in sale_list %}<tr><td>{{ s.created_at }}</td><td>{{ branches_map.get(s.branch_id, '') }}</td><td>{{ users_map.get(s.attended_by_id, 'Unknown') }}</td><td>{{ s.customer_name }}</td><td>{{ money(s.total) }}</td><td>{{ money(s.amount_paid) }}</td><td>{{ money(s.balance) }}</td><td><a href="/receipt/{{ s.id }}">View</a></td></tr>{% endfor %}</table></div><a class="btn" href="/">Back</a>
    """, sale_list=sale_list, branches_map=branches_map, users_map=users_map)


@app.route("/debtors", methods=["GET", "POST"])
def debtors():
    if not logged_in():
        return redirect(url_for("login"))

    # Only manager can confirm debtor payment.
    if request.method == "POST":
        if not is_manager():
            return page("Manager Access Required", "<div class='card'><h2>Manager Access Required</h2><p>Only the manager can confirm debtor payments.</p><a class='btn' href='/debtors'>Back</a></div>")

        if not check_manager_pin(request.form.get("manager_pin")):
            return page("Manager PIN Required", "<div class='card'><h2>Manager PIN Required</h2><p>Enter the correct manager PIN before confirming debtor payment.</p><a class='btn' href='/debtors'>Back</a></div>")

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
        audit_log("Debtor Payment Confirmed", f"Sale #{sale.id} balance now {sale.balance}")
        return redirect(url_for("debtors"))

    debtor_list = Sale.query.filter(Sale.balance > 0).order_by(Sale.id.desc()).all() if is_manager() else Sale.query.filter(Sale.branch_id == session.get("branch_id"), Sale.balance > 0).order_by(Sale.id.desc()).all()
    return page("Debtors", """
    <div class="card"><h2>Debtors</h2>
    <p class="small">Only manager can confirm full or part payment on debtor accounts.</p>
    <table>
        <tr><th>Date</th><th>Staff Who Attended</th><th>Customer</th><th>Phone</th><th>Total</th><th>Paid</th><th>Balance</th>{% if session['role']=='manager' %}<th>Manager Payment Confirmation</th>{% endif %}</tr>
        {% for s in debtor_list %}
        <tr>
            <td>{{ s.created_at }}</td>
            <td>{{ users_map.get(s.attended_by_id, 'Unknown') }}</td>
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
                    <input name="manager_pin" type="password" placeholder="Manager PIN" style="max-width:130px">
                    <select name="payment_method" style="max-width:140px"><option>Cash</option><option>Transfer</option><option>POS</option></select>
                    <button type="submit">Confirm Part Payment</button>
                </form>
                <form method="post">
                    <input type="hidden" name="sale_id" value="{{ s.id }}">
                    <input type="hidden" name="action" value="full">
                    <input name="manager_pin" type="password" placeholder="Manager PIN" style="max-width:130px">
                    <select name="payment_method" style="max-width:140px"><option>Cash</option><option>Transfer</option><option>POS</option></select>
                    <button class="btn-green" type="submit">Confirm Full Payment</button>
                </form>
            </td>
            {% endif %}
        </tr>
        {% endfor %}
    </table></div><a class="btn" href="/">Back</a>
    """, debtor_list=debtor_list, users_map={u.id: u.username for u in User.query.all()})


@app.route("/staff")
def staff():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can manage staff accounts."

    selected_branch = request.args.get("branch_id")
    user_query = User.query.filter(User.role != "deleted")

    if selected_branch:
        user_query = user_query.filter_by(branch_id=int(selected_branch))

    users = user_query.order_by(User.id.asc()).all()
    branches = Branch.query.order_by(Branch.name).all()
    branches_map = {b.id: b.name for b in branches}

    return page("Staff Accounts", """
    <div class="card">
        <h2>Staff Accounts</h2>
        <form method="get" class="no-print" style="margin-bottom:15px">
            <label>View Staff By Branch</label><br>
            <select name="branch_id" onchange="this.form.submit()" style="max-width:300px">
                <option value="">All Branches</option>
                {% for b in branches %}
                <option value="{{ b.id }}" {% if selected_branch and selected_branch|int == b.id %}selected{% endif %}>{{ b.name }}</option>
                {% endfor %}
            </select>
        </form>

        <p class="small">
            Manager can disable staff accounts that are no longer working for the company. 
            Old sales, goods request and audit records will remain safe.
        </p>

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
                    <form method="post" action="/delete-staff/{{ u.id }}" onsubmit="return confirm('Disable this staff account? The staff will no longer be able to login.');">
                        <input type="password" name="manager_pin" placeholder="Manager PIN" required style="max-width:120px">
                        <button class="btn-red" type="submit">Delete</button>
                    </form>
                    {% else %}
                    Protected
                    {% endif %}
                </td>
            </tr>
            {% else %}
            <tr><td colspan="4">No active staff account found.</td></tr>
            {% endfor %}
        </table>
    </div>
    <a class="btn" href="/">Back</a>
    """, users=users, branches_map=branches_map, branches=branches, selected_branch=selected_branch)


@app.route("/delete-staff/<int:user_id>", methods=["POST"])
def delete_staff(user_id):
    if not logged_in():
        return redirect(url_for("login"))

    if not is_manager():
        return "Only manager can delete staff accounts."

    if not check_manager_pin(request.form.get("manager_pin")):
        return page("Wrong Manager PIN", """
        <div class="card danger">
            <h2>Wrong Manager PIN</h2>
            <p>Staff deletion was blocked.</p>
            <a class="btn" href="/staff">Back</a>
        </div>
        """)

    user = User.query.get_or_404(user_id)

    if user.id == session.get("user_id") or user.username == "manager":
        return page("Protected Account", """
        <div class="card">
            <h2>Protected Account</h2>
            <p>You cannot delete the active login account or the default manager account.</p>
            <a class="btn" href="/staff">Back</a>
        </div>
        """)

    old_username = user.username
    old_role = user.role
    old_branch = user.branch_id

    # Safe staff removal:
    # Do not physically delete the user row because old sales, goods requests and audit records may reference it.
    # Instead, disable the account so it disappears from Staff list and cannot login again.
    user.username = f"DISABLED_{user.id}_{user.username}"
    user.password_hash = generate_password_hash(f"DISABLED_ACCOUNT_{user.id}_{datetime.utcnow().timestamp()}")
    user.role = "deleted"

    db.session.commit()

    audit_log(
        "Staff Account Disabled",
        f"Disabled staff username: {old_username}, old role: {old_role}, branch ID: {old_branch}"
    )

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
    branches_map = {b.id: b.name for b in branches}

    # Staff can request goods from another branch, but their requesting branch is locked
    # to their assigned branch for security. Manager can select any requesting branch.
    requester_branch_id = int(session.get("branch_id") or 1)
    if is_manager() and request.method == "GET" and request.args.get("requester_branch_id"):
        requester_branch_id = int(request.args.get("requester_branch_id"))

    if request.method == "POST":
        if is_manager():
            requester_branch_id = int(request.form.get("requester_branch_id") or session.get("branch_id") or 1)
        else:
            requester_branch_id = int(session.get("branch_id") or 1)

        product_id = int(request.form.get("product_id"))
        qty = int(request.form.get("quantity") or 1)
        product = Product.query.get(product_id)

        if not product:
            return page("Invalid Product", "<div class='card'><h2>Product not found</h2><a class='btn' href='/request-goods'>Back</a></div>")

        supplier_branch_id = int(product.branch_id or 0)
        if supplier_branch_id == requester_branch_id:
            return page("Same Branch", "<div class='card'><h2>Select product from another branch</h2><p>You cannot request goods from your own branch.</p><a class='btn' href='/request-goods'>Back</a></div>")

        if qty <= 0:
            return page("Invalid Quantity", "<div class='card'><h2>Invalid Quantity</h2><p>Enter quantity greater than zero.</p><a class='btn' href='/request-goods'>Back</a></div>")

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

    # Show staff only products from OTHER branches. Manager can also use this clean list.
    products = Product.query.filter(Product.branch_id != requester_branch_id).order_by(Product.branch_id, Product.name).all()

    return page("Request Goods", """
    <div class="card">
        <h2>Request Product From Another Branch</h2>
        <p class="small">Staff can request products from another branch when their branch is out of stock. The request will remain pending until the supplying branch/manager approves it.</p>

        <form method="post">
            <label>Your Branch</label><br>
            {% if session['role'] == 'manager' %}
                <select name="requester_branch_id">
                    {% for b in branches %}
                    <option value="{{ b.id }}" {% if b.id == requester_branch_id %}selected{% endif %}>{{ b.name }}</option>
                    {% endfor %}
                </select><br><br>
            {% else %}
                <input value="{{ branches_map.get(requester_branch_id, '') }}" readonly>
                <input type="hidden" name="requester_branch_id" value="{{ requester_branch_id }}">
                <br><br>
            {% endif %}

            <label>Select Product From Another Branch</label><br>
            <select name="product_id" required>
                {% for p in products %}
                <option value="{{ p.id }}">
                    {{ p.name }} - {{ p.category }} - {{ p.subcategory }} | Available: {{ p.quantity }} | Branch: {{ branches_map.get(p.branch_id, '') }}
                </option>
                {% endfor %}
            </select><br><br>

            <label>Quantity Needed</label><br>
            <input name="quantity" type="number" min="1" value="1" required><br><br>

            <label>Reason / Note</label><br>
            <textarea name="note" placeholder="Example: Customer needs this urgently; our branch is out of stock."></textarea><br><br>

            <button class="btn-green" type="submit">Submit Goods Request</button>
        </form>
    </div>
    """, branches=branches, branches_map=branches_map, products=products, requester_branch_id=requester_branch_id)


@app.route("/goods-requests")
def goods_requests():
    if not logged_in():
        return redirect(url_for("login"))

    if is_manager():
        requests = GoodsRequest.query.order_by(GoodsRequest.id.desc()).all()
    else:
        # Staff sees requests made by their branch and requests sent to their branch.
        requests = GoodsRequest.query.filter(
            (GoodsRequest.requester_branch_id == session.get("branch_id")) |
            (GoodsRequest.supplier_branch_id == session.get("branch_id"))
        ).order_by(GoodsRequest.id.desc()).all()

    branches_map = {b.id: b.name for b in Branch.query.all()}
    users_map = {u.id: u.username for u in User.query.all()}

    return page("Goods Requests", """
    <div class="card">
        <h2>Inter-Branch Goods Requests</h2>
        <p class="small">Staff can submit product requests from another branch. Manager or supplying-branch staff can approve/decline pending requests.</p>
        <a class="btn-green btn" href="/request-goods">New Goods Request</a>
        <table>
            <tr>
                <th>Date</th>
                <th>Supplying Branch</th>
                <th>Requesting Branch</th>
                <th>Product</th>
                <th>Qty</th>
                <th>Status</th>
                <th>Requested By</th>
                <th>Processed By</th>
                <th>Note</th>
                <th>Action</th>
            </tr>
            {% for r in requests %}
            <tr>
                <td>{{ r.created_at }}</td>
                <td>{{ branches_map.get(r.supplier_branch_id, '') }}</td>
                <td>{{ branches_map.get(r.requester_branch_id, '') }}</td>
                <td>{{ r.item_name }}</td>
                <td>{{ r.quantity }}</td>
                <td>{{ r.status }}</td>
                <td>{{ users_map.get(r.requested_by, '') }}</td>
                <td>{{ users_map.get(r.processed_by_id, '') }}</td>
                <td>{{ r.note }}</td>
                <td>
                    {% if r.status == 'Pending' and (session['role']=='manager' or r.supplier_branch_id == session['branch_id']) %}
                    <form method="post" action="/approve-goods-request/{{ r.id }}" style="display:inline"><button class="btn-green" type="submit">Approve Transfer</button></form>
                    <form method="post" action="/decline-goods-request/{{ r.id }}" style="display:inline"><button class="btn-red" type="submit">Decline</button></form>
                    {% elif r.status == 'Pending' %}
                    Waiting for supplying branch / manager
                    {% else %}
                    Processed
                    {% endif %}
                </td>
            </tr>
            {% else %}
            <tr><td colspan="10">No goods request yet.</td></tr>
            {% endfor %}
        </table>
    </div>
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
        return redirect(url_for("print_patient_rx", rx_id=rx.id))

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
    <tr><th>Date</th><th>Branch</th><th>Patient</th><th>Phone</th><th>OD</th><th>OS</th><th>PD</th><th>Lens Recommendation</th><th>Print</th></tr>
    {% for r in rx_list %}<tr><td>{{ r.created_at }}</td><td>{{ branches_map.get(r.branch_id, '') }}</td><td>{{ r.patient_name }}</td><td>{{ r.phone }}</td><td>{{ r.od_sph }} / {{ r.od_cyl }} x {{ r.od_axis }} Add {{ r.od_add }}</td><td>{{ r.os_sph }} / {{ r.os_cyl }} x {{ r.os_axis }} Add {{ r.os_add }}</td><td>{{ r.pd }}</td><td>{{ r.lens_recommendation }}</td><td><a class="btn" href="/patient-rx/print/{{ r.id }}">🖨️ Print</a></td></tr>{% endfor %}
    </table></div>
    """, rx_list=rx_list, branches_map=branches_map)


@app.route("/patient-rx/print/<int:rx_id>")
def print_patient_rx(rx_id):
    if not logged_in():
        return redirect(url_for("login"))
    rx = PatientPrescription.query.get_or_404(rx_id)
    if not is_manager() and rx.branch_id != session.get("branch_id"):
        return page("Access Denied", "<div class='card'><h2>Access Denied</h2><p>You can only print prescriptions from your branch.</p><a class='btn' href='/patient-rx'>Back</a></div>")
    branch = Branch.query.get(rx.branch_id)
    setting = OfficeSetting.query.first()
    return page("Print Patient Rx", """
    <div class="card" style="max-width:900px;margin:auto">
        <div style="text-align:center;border-bottom:2px solid #003366;padding-bottom:12px;margin-bottom:16px">
            <h1 style="margin:0">{{ setting.office_name }}</h1>
            <p style="margin:4px 0"><b>Address:</b> {{ setting.address }}</p>
            <p style="margin:4px 0"><b>Phone:</b> {{ setting.phone }}</p>
            <h2 style="margin-top:12px">PATIENT PRESCRIPTION / Rx CARD</h2>
        </div>

        <div class="two">
            <div><p><b>Patient Name:</b> {{ rx.patient_name }}</p><p><b>Phone:</b> {{ rx.phone }}</p><p><b>Age:</b> {{ rx.age }}</p><p><b>Gender:</b> {{ rx.gender }}</p></div>
            <div><p><b>Date:</b> {{ rx.created_at.strftime('%Y-%m-%d %H:%M') }}</p><p><b>Branch:</b> {{ branch.name if branch else '' }}</p><p><b>Doctor / Optometrist:</b> {{ rx.doctor_name }}</p><p><b>Address:</b> {{ rx.address }}</p></div>
        </div>

        <table style="margin-top:15px">
            <tr><th>Eye</th><th>SPH</th><th>CYL</th><th>AXIS</th><th>ADD</th></tr>
            <tr><td><b>OD / Right Eye</b></td><td>{{ rx.od_sph }}</td><td>{{ rx.od_cyl }}</td><td>{{ rx.od_axis }}</td><td>{{ rx.od_add }}</td></tr>
            <tr><td><b>OS / Left Eye</b></td><td>{{ rx.os_sph }}</td><td>{{ rx.os_cyl }}</td><td>{{ rx.os_axis }}</td><td>{{ rx.os_add }}</td></tr>
        </table>

        <div class="two" style="margin-top:15px">
            <div><p><b>PD:</b> {{ rx.pd }}</p><p><b>Segment Height:</b> {{ rx.seg_height }}</p></div>
            <div><p><b>Frame Measurement:</b> {{ rx.frame_measurement }}</p><p><b>Lens Recommendation:</b> {{ rx.lens_recommendation }}</p></div>
        </div>

        <div style="border:1px solid #cbd5e1;border-radius:10px;padding:12px;margin-top:15px;min-height:80px">
            <b>Clinical / Dispensing Note:</b><br>{{ rx.note }}
        </div>

        <div class="two" style="margin-top:35px">
            <div style="border-top:1px solid #000;padding-top:8px;text-align:center">Optician / Staff Signature</div>
            <div style="border-top:1px solid #000;padding-top:8px;text-align:center">Customer Signature</div>
        </div>

        <p class="small" style="text-align:center;margin-top:20px">Thank you for choosing {{ setting.office_name }}.</p>
        <div class="no-print" style="text-align:center;margin-top:15px">
            <button onclick="window.print()">🖨️ Print Patient Rx</button>
            <a class="btn" href="/patient-rx">Back to Patient Rx</a>
        </div>
    </div>
    """, rx=rx, branch=branch, setting=setting)



@app.route("/customer-history")
def customer_history():
    if not logged_in():
        return redirect(url_for("login"))

    keyword = request.args.get("keyword", "").strip()
    sales = []
    rx_records = []

    if keyword:
        sales_query = Sale.query.filter((Sale.customer_name.contains(keyword)) | (Sale.customer_phone.contains(keyword)))
        rx_query = PatientPrescription.query.filter((PatientPrescription.patient_name.contains(keyword)) | (PatientPrescription.phone.contains(keyword)))
        if not is_manager():
            sales_query = sales_query.filter_by(branch_id=session.get("branch_id"))
            rx_query = rx_query.filter_by(branch_id=session.get("branch_id"))
        sales = sales_query.order_by(Sale.created_at.desc()).all()
        rx_records = rx_query.order_by(PatientPrescription.created_at.desc()).all()

    users_map = {u.id: u.username for u in User.query.all()}
    branches_map = {b.id: b.name for b in Branch.query.all()}
    total_spent = sum(float(s.total or 0) for s in sales)
    total_balance = sum(float(s.balance or 0) for s in sales)

    return page("Customer History", """
    <div class="card">
        <h2>Customer History</h2>
        <p class="small">Search by customer name or phone number to see purchases, outstanding balance, prescription records, branch and staff that attended.</p>
        <form method="get">
            <input name="keyword" value="{{ keyword }}" placeholder="Enter customer name or phone number" required>
            <button>Search Customer</button>
        </form>
    </div>
    {% if keyword %}
    <div class="grid">
        <div class="card stat"><h3>Total Purchases</h3><h1>₦{{ money(total_spent) }}</h1></div>
        <div class="card stat"><h3>Outstanding Balance</h3><h1>₦{{ money(total_balance) }}</h1></div>
        <div class="card stat"><h3>Sales Visits</h3><h1>{{ sales|length }}</h1></div>
        <div class="card stat"><h3>Rx Records</h3><h1>{{ rx_records|length }}</h1></div>
    </div>
    <div class="card"><h3>Sales History</h3>
        <table><tr><th>Date</th><th>Branch</th><th>Customer</th><th>Phone</th><th>Total</th><th>Paid</th><th>Balance</th><th>Payment</th><th>Staff</th></tr>
        {% for s in sales %}<tr><td>{{ s.created_at }}</td><td>{{ branches_map.get(s.branch_id, '') }}</td><td>{{ s.customer_name }}</td><td>{{ s.customer_phone }}</td><td>₦{{ money(s.total) }}</td><td>₦{{ money(s.amount_paid) }}</td><td>₦{{ money(s.balance) }}</td><td>{{ s.payment_method }}</td><td>{{ users_map.get(s.attended_by_id, 'Unknown') }}</td></tr>{% else %}<tr><td colspan="9">No sales history found.</td></tr>{% endfor %}
        </table>
    </div>
    <div class="card"><h3>Prescription History</h3>
        <table><tr><th>Date</th><th>Patient</th><th>Phone</th><th>OD</th><th>OS</th><th>ADD</th><th>PD</th><th>Lens Recommendation</th></tr>
        {% for r in rx_records %}<tr><td>{{ r.created_at }}</td><td>{{ r.patient_name }}</td><td>{{ r.phone }}</td><td>{{ r.od_sph }} / {{ r.od_cyl }} x {{ r.od_axis }}</td><td>{{ r.os_sph }} / {{ r.os_cyl }} x {{ r.os_axis }}</td><td>OD {{ r.od_add }} / OS {{ r.os_add }}</td><td>{{ r.pd }}</td><td>{{ r.lens_recommendation }}</td></tr>{% else %}<tr><td colspan="8">No Rx record found.</td></tr>{% endfor %}
        </table>
    </div>
    {% endif %}
    """, keyword=keyword, sales=sales, rx_records=rx_records, users_map=users_map, branches_map=branches_map, total_spent=total_spent, total_balance=total_balance)


@app.route("/debtor-reminders")
def debtor_reminders():
    if not logged_in():
        return redirect(url_for("login"))
    sale_query = Sale.query.filter(Sale.balance > 0)
    if not is_manager():
        sale_query = sale_query.filter_by(branch_id=session.get("branch_id"))
    debtors = sale_query.order_by(Sale.created_at.desc()).all()
    return page("Debtor Reminders", """
    <div class="card">
        <h2>Debtor WhatsApp Reminder</h2>
        <p class="small">Send polite payment reminders to customers owing Halleluyah Optical Laboratory.</p>
        <table><tr><th>Date</th><th>Customer</th><th>Phone</th><th>Total</th><th>Paid</th><th>Balance</th><th>WhatsApp</th></tr>
        {% for d in debtors %}
        {% set msg = "Dear " ~ (d.customer_name or "Customer") ~ ", your outstanding balance at Halleluyah Optical Laboratory is ₦" ~ money(d.balance) ~ ". Kindly make payment. Thank you." %}
        <tr><td>{{ d.created_at }}</td><td>{{ d.customer_name }}</td><td>{{ d.customer_phone }}</td><td>₦{{ money(d.total) }}</td><td>₦{{ money(d.amount_paid) }}</td><td><b>₦{{ money(d.balance) }}</b></td><td><a class="btn-green btn" target="_blank" href="https://wa.me/{{ d.customer_phone.replace('+','').replace(' ','').replace('-','') }}?text={{ msg|urlencode }}">Send Reminder</a></td></tr>
        {% else %}<tr><td colspan="7">No outstanding debtor found.</td></tr>{% endfor %}
        </table>
    </div>
    """, debtors=debtors)


@app.route("/backup-center")
def backup_center():
    if not logged_in():
        return redirect(url_for("login"))
    if not is_manager():
        return "Only manager can access backup center."
    return page("Backup Center", """
    <div class="card"><h2>Backup Center</h2><p class="small">Download important business records for safety. Use this daily before closing.</p>
        <a class="btn-green btn" href="/download-sales-backup">Download Sales Backup CSV</a>
        <a class="btn-green btn" href="/download-products-backup">Download Products Backup CSV</a>
        <a class="btn-green btn" href="/download-lens-backup">Download Lens Power Backup CSV</a>
        <a class="btn-green btn" href="/download-debtors-backup">Download Debtors Backup CSV</a>
    </div>
    """)


def csv_response(filename, header, rows):
    def generate():
        yield header + "\n"
        for row in rows:
            clean = [str(x if x is not None else "").replace(",", " ").replace("\n", " ") for x in row]
            yield ",".join(clean) + "\n"
    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={filename}"})


@app.route("/download-sales-backup")
def download_sales_backup():
    if not logged_in() or not is_manager():
        return "Manager access required."
    sales = Sale.query.order_by(Sale.created_at.desc()).all()
    rows = [(s.created_at, s.customer_name, s.customer_phone, s.total, s.discount, s.amount_paid, s.balance, s.payment_method, s.branch_id, s.attended_by_id) for s in sales]
    return csv_response(f"HOL_sales_backup_{datetime.now().strftime('%Y%m%d')}.csv", "Date,Customer,Phone,Total,Discount,Amount Paid,Balance,Payment Method,Branch ID,Staff ID", rows)


@app.route("/download-products-backup")
def download_products_backup():
    if not logged_in() or not is_manager():
        return "Manager access required."
    products = Product.query.order_by(Product.id.desc()).all()
    rows = [(p.branch_id, p.name, p.category, p.subcategory, p.retail_price, p.wholesale_price, p.quantity) for p in products]
    return csv_response(f"HOL_products_backup_{datetime.now().strftime('%Y%m%d')}.csv", "Branch ID,Product Name,Category,Subcategory,Retail Price,Wholesale Price,Quantity", rows)


@app.route("/download-lens-backup")
def download_lens_backup():
    if not logged_in() or not is_manager():
        return "Manager access required."
    lens = LensPower.query.order_by(LensPower.id.desc()).all()
    rows = [(l.branch_id, l.product_id, l.sph, l.cyl, l.axis, l.add_power, l.quantity) for l in lens]
    return csv_response(f"HOL_lens_power_backup_{datetime.now().strftime('%Y%m%d')}.csv", "Branch ID,Product ID,SPH,CYL,Axis,ADD,Quantity", rows)


@app.route("/download-debtors-backup")
def download_debtors_backup():
    if not logged_in() or not is_manager():
        return "Manager access required."
    debtors = Sale.query.filter(Sale.balance > 0).order_by(Sale.created_at.desc()).all()
    rows = [(d.created_at, d.customer_name, d.customer_phone, d.total, d.amount_paid, d.balance, d.payment_method) for d in debtors]
    return csv_response(f"HOL_debtors_backup_{datetime.now().strftime('%Y%m%d')}.csv", "Date,Customer,Phone,Total,Amount Paid,Balance,Payment Method", rows)

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

    req = GoodsRequest.query.get_or_404(request_id)

    # Only manager or the supplying branch can approve the request.
    if not (is_manager() or int(req.supplier_branch_id or 0) == int(session.get("branch_id") or 0)):
        return "Only the manager or the supplying branch staff can accept goods requests."

    if req.status != "Pending":
        return redirect(url_for("goods_requests"))

    qty = int(req.quantity or 0)
    if qty <= 0:
        return page("Invalid Quantity", """
        <div class="card">
            <h2>Invalid Quantity</h2>
            <p>The requested transfer quantity is not valid.</p>
            <a class="btn" href="/goods-requests">Back</a>
        </div>
        """)

    source_product = Product.query.get(req.product_id)
    if not source_product:
        req.status = "Declined - Product Missing"
        req.processed_at = datetime.utcnow()
        req.processed_by_id = session.get("user_id")
        db.session.commit()
        return redirect(url_for("goods_requests"))

    # Branch safety: the product must truly belong to the supplying branch.
    if int(source_product.branch_id or 0) != int(req.supplier_branch_id or 0):
        return page("Wrong Supplying Branch", """
        <div class="card">
            <h2>Wrong Supplying Branch</h2>
            <p>This product does not belong to the selected supplying branch.</p>
            <a class="btn" href="/goods-requests">Back</a>
        </div>
        """)

    if int(source_product.quantity or 0) < qty:
        return page("Not Enough Stock", """
        <div class="card">
            <h2>Not Enough Stock</h2>
            <p>The supplying branch does not have enough quantity to transfer.</p>
            <p><b>Available:</b> {{ source_product.quantity }}</p>
            <p><b>Requested:</b> {{ qty }}</p>
            <a class="btn" href="/goods-requests">Back</a>
        </div>
        """, source_product=source_product, qty=qty)

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

    # Immediate confirmed transfer:
    # deduct from supplying branch and add to requesting branch at once.
    source_product.quantity = int(source_product.quantity or 0) - qty
    destination_product.quantity = int(destination_product.quantity or 0) + qty

    # Keep full audit record of who approved the transfer.
    req.status = "Approved and Transferred"
    req.processed_at = datetime.utcnow()
    req.processed_by_id = session.get("user_id")

    db.session.commit()
    return redirect(url_for("goods_requests"))


@app.route("/decline-goods-request/<int:request_id>", methods=["POST"])
def decline_goods_request(request_id):
    if not logged_in():
        return redirect(url_for("login"))
    req = GoodsRequest.query.get_or_404(request_id)
    if not (is_manager() or int(req.supplier_branch_id or 0) == int(session.get("branch_id") or 0)):
        return "Only the manager or the supplying branch staff can decline goods requests."
    if req.status == "Pending":
        req.status = "Declined"
        req.processed_at = datetime.utcnow()
        req.processed_by_id = session.get("user_id")
        db.session.commit()
        audit_log("Goods Request Declined", f"Request #{req.id}")
    return redirect(url_for("goods_requests"))


if __name__ == "__main__":
    app.run(debug=False)