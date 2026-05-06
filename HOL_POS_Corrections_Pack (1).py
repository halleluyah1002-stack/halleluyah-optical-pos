
# Halleluyah Optical Laboratory POS
# Corrections Pack

# =========================
# 1. WhatsApp Invoice Share
# =========================

def build_whatsapp_invoice(sale, items, branch, setting, attended_by, change_due):
    lines = [
        f"{setting.office_name}",
        "Receipt / Invoice",
        f"Receipt No: #{sale.id}",
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
        "Thank you for choosing HOL. Your vision is our priority."
    ]

    return "\n".join(lines)


# =========================
# 2. Generate Power Grid Fix
# =========================

# Replace your current:
#
# product_list = Product.query.filter(
#     Product.branch_id == int(selected_branch),
#     Product.category.contains("Lens")
# ).order_by(Product.name).all()
#
# WITH THIS:

product_list = Product.query.filter(
    Product.category.contains("Lens")
).order_by(Product.branch_id, Product.name).all()


# Replace this:
#
# if product and int(product.branch_id or 0) == int(selected_branch):
#
# WITH THIS:

if product:
    selected_branch_id = int(selected_branch)

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


# =========================
# 3. Receipt Route Upgrade
# =========================

# Add this inside your receipt route BEFORE return page(...)

whatsapp_message = build_whatsapp_invoice(
    sale=sale,
    items=items,
    branch=branch,
    setting=setting,
    attended_by=attended_by,
    change_due=change_due
)


# =========================
# 4. WhatsApp Share Button
# =========================

# Add this inside receipt HTML buttons section:

"""
<div class="no-print">
    <button onclick="window.print()">Print Receipt</button>

    <a class="btn-green btn"
       target="_blank"
       href="https://wa.me/{% if sale.customer_phone %}{{ sale.customer_phone.replace('+','').replace(' ','').replace('-','') }}{% endif %}?text={{ whatsapp_message|urlencode }}">
       Share Invoice on WhatsApp
    </a>

    <a class="btn-green btn" href="/receipt/{{ sale.id }}/thermal">
        80mm Thermal Receipt
    </a>

    <a class="btn" href="/pos">New Sale</a>
</div>
"""


# =========================
# 5. Staff Delete Protection
# =========================

@app.route("/delete-staff/<int:user_id>", methods=["POST"])
def delete_staff(user_id):
    if not logged_in():
        return redirect(url_for("login"))

    if not is_manager():
        return "Only manager can delete staff accounts."

    user = User.query.get_or_404(user_id)

    if user.id == session.get("user_id") or user.username == "manager":
        return page(
            "Protected Account",
            """
            <div class='card'>
                <h2>Protected Account</h2>
                <p>You cannot delete the active login account or the default manager account.</p>
                <a class='btn' href='/staff'>Back</a>
            </div>
            """
        )

    deleted_username = user.username
    deleted_role = user.role
    deleted_branch = user.branch_id

    db.session.delete(user)
    db.session.commit()

    audit_log(
        "Staff Account Deleted",
        f"Deleted staff username: {deleted_username}, role: {deleted_role}, branch ID: {deleted_branch}"
    )

    return redirect(url_for("staff"))
