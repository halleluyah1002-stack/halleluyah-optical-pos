@app.route("/pos", methods=["GET", "POST"])
def pos():
    if not logged_in():
        return redirect(url_for("login"))

    view = request.form.get("view") or request.args.get("view", "none")
    lens_category = request.args.get("lens_category", "")
    lens_material = request.args.get("lens_material", "")

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
    selected_branch_id = int(customer.get("branch_id") or session.get("branch_id") or 1)
    if not is_manager():
        selected_branch_id = int(session.get("branch_id") or 1)

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
            prefix = category

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
        customer = {
            "customer_name": request.form.get("customer_name") or "",
            "customer_phone": request.form.get("customer_phone") or "",
            "branch_id": int(request.form.get("branch_id") or selected_branch_id),
            "price_type": request.form.get("price_type") or "retail"
        }

        if not is_manager():
            customer["branch_id"] = int(session.get("branch_id") or 1)

        session["pos_customer"] = customer
        selected_branch_id = int(customer["branch_id"])
        price_type = customer["price_type"]

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
                    <div class="card">
                        <h2>Invalid Quantity</h2>
                        <p>Please enter a valid quantity.</p>
                        <a class="btn" href="/pos?view=lenses">Back</a>
                    </div>
                    """)

                if qty > int(lp.quantity or 0):
                    return page("Insufficient Lens Stock", """
                    <div class="card">
                        <h2>Insufficient Lens Stock</h2>
                        <p>The selected power does not have enough stock.</p>
                        <a class="btn" href="/pos?view=lenses">Back</a>
                    </div>
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
                    <div class="card">
                        <h2>Insufficient Product Stock</h2>
                        <p>You selected more quantity than available.</p>
                        <a class="btn" href="/pos?view=frames">Back</a>
                    </div>
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

        return redirect(url_for("pos", view=view, lens_category=lens_category, lens_material=lens_material))

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
    recent_lenses = []

    if view == "lenses":
        for p in product_list:
            powers = LensPower.query.filter_by(
                product_id=p.id,
                branch_id=selected_branch_id
            ).filter(LensPower.quantity > 0).order_by(
                LensPower.sph,
                LensPower.cyl,
                LensPower.add_power
            ).all()

            lens_map[p.id] = powers
            lens_stock_map[p.id] = sum(int(l.quantity or 0) for l in powers)

        recent_lenses = SaleItem.query.filter(
            SaleItem.lens_power != ""
        ).order_by(SaleItem.id.desc()).limit(5).all()

    cart = session.get("pos_cart", [])
    cart_total = sum(float(i.get("subtotal", 0) or 0) for i in cart)

    lens_categories = [
        ("Single Vision Lens", "🟦 Single Vision", "#2563eb"),
        ("Bifocal Lens", "🟩 Bifocal", "#16a34a"),
        ("Progressive Lens", "🟨 Progressive", "#f59e0b"),
    ]

    lens_materials = [
        ("White Lens", "White"),
        ("Photo AR", "Photo AR"),
        ("Blue Cut Photo AR", "BlueCut Photo"),
    ]

    return page("POS", """
    <style>
        .pos-big-btn{
            display:block;
            color:white;
            padding:26px;
            border-radius:18px;
            text-decoration:none;
            font-size:22px;
            font-weight:bold;
            text-align:center;
            box-shadow:0 6px 18px #0002;
            min-height:90px;
        }
        .pos-small-btn{
            display:inline-block;
            padding:16px 22px;
            border-radius:14px;
            text-decoration:none;
            margin:6px;
            font-weight:bold;
            background:#e2e8f0;
            color:#0f172a;
        }
        .pos-small-btn.active{
            background:#003366;
            color:white;
        }
        .pos-card-grid{
            display:grid;
            grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
            gap:15px;
        }
        .pos-item-card{
            border:1px solid #dbe4ee;
            border-radius:16px;
            padding:16px;
            background:#fff;
            box-shadow:0 3px 10px #0001;
        }
        .floating-cart{
            position:sticky;
            top:10px;
            border:2px solid #198754;
            background:#f8fff9;
        }
    </style>

    <div class="card">
        <h2>Make Sale - Simple Optical POS</h2>
        <p class="small">Clean step-by-step sales page: choose category first, then material, then select power/product.</p>

        <div class="two">
            <div>
                <label>Customer Name</label>
                <input form="posForm" name="customer_name" value="{{ customer.get('customer_name','') }}" placeholder="Customer Name">
            </div>
            <div>
                <label>Customer Phone</label>
                <input form="posForm" name="customer_phone" value="{{ customer.get('customer_phone','') }}" placeholder="Customer Phone">
            </div>
        </div>
        <br>

        {% if session['role'] == 'manager' %}
        <label>Branch</label><br>
        <select form="posForm" name="branch_id" onchange="this.form.submit()">
            {% for b in Branch.query.all() %}
            <option value="{{ b.id }}" {% if selected_branch_id == b.id %}selected{% endif %}>{{ b.name }}</option>
            {% endfor %}
        </select><br><br>
        {% endif %}

        <label>Price Type</label><br>
        <select form="posForm" name="price_type">
            <option value="retail" {% if customer.get('price_type') == 'retail' %}selected{% endif %}>Retail / End User</option>
            <option value="wholesale" {% if customer.get('price_type') == 'wholesale' %}selected{% endif %}>Wholesale</option>
        </select>
    </div>

    <div class="two">
        <div>
            <div class="card">
                <h3>Step 1: Select Sales Type</h3>
                <div class="pos-card-grid">
                    <a class="pos-big-btn" href="/pos?view=lenses" style="background:#2563eb">
                        👓 Lenses<br><span style="font-size:14px;font-weight:normal">SV, Bifocal, Progressive</span>
                    </a>
                    <a class="pos-big-btn" href="/pos?view=frames" style="background:#16a34a">
                        🕶️ Frames & Accessories<br><span style="font-size:14px;font-weight:normal">Frames, cases, cleaners, cloths</span>
                    </a>
                </div>
            </div>

            {% if view == 'lenses' %}
            <div class="card">
                <h3>Step 2: Select Lens Category</h3>
                {% for value, label, color in lens_categories %}
                    <a class="pos-small-btn {% if lens_category == value %}active{% endif %}"
                       href="/pos?view=lenses&lens_category={{ value }}">{{ label }}</a>
                {% endfor %}
            </div>

            {% if lens_category %}
            <div class="card">
                <h3>Step 3: Select Lens Material</h3>
                {% for value, label in lens_materials %}
                    <a class="pos-small-btn {% if lens_material == value %}active{% endif %}"
                       href="/pos?view=lenses&lens_category={{ lens_category }}&lens_material={{ value }}">{{ label }}</a>
                {% endfor %}
            </div>
            {% endif %}

            {% if lens_category and lens_material %}
            <form id="posForm" method="post">
                <input type="hidden" name="view" value="lenses">

                <div class="card">
                    <h3>Step 4: Select Power</h3>
                    <input id="powerSearch" placeholder="🔍 Search power e.g. -2.00, +1.50, cyl, add" onkeyup="filterPowerCards()">
                    <br><br>

                    {% if recent_lenses %}
                    <div class="alert success">
                        <b>Recent Lens Sales:</b>
                        {% for r in recent_lenses %}
                            <span style="display:inline-block;background:white;padding:6px 10px;border-radius:10px;margin:4px">
                                {{ r.product_name }} - {{ r.lens_power }}
                            </span>
                        {% endfor %}
                    </div>
                    {% endif %}

                    <div class="pos-card-grid">
                        {% for p in product_list %}
                        <div class="pos-item-card lens-product-card">
                            <h3>{{ short_lens_name(p) }}</h3>
                            <p><b>Stock:</b> {{ lens_stock_map.get(p.id, 0) }} | {{ stock_badge(lens_stock_map.get(p.id, 0)) }}</p>
                            <p class="small">Retail ₦{{ money(p.retail_price) }} | Wholesale ₦{{ money(p.wholesale_price) }}</p>

                            <label>Select Power</label>
                            <select name="lens_power_id" class="powerSelect">
                                <option value="">Choose power</option>
                                {% for lp in lens_map.get(p.id, []) %}
                                <option value="{{ lp.id }}">
                                    SPH {{ lp.sph }} CYL {{ lp.cyl }} AXIS {{ lp.axis }} ADD {{ lp.add_power }} | Qty {{ lp.quantity }}
                                </option>
                                {% endfor %}
                            </select>

                            <br><br>
                            <label>Quantity Type</label>
                            <select name="unit_type">
                                <option value="half">Half Pair / 1 Lens</option>
                                <option value="pair">1 Pair / 2 Lenses</option>
                                <option value="custom">Custom Quantity</option>
                            </select>

                            <input name="custom_qty" type="number" min="0" placeholder="Custom quantity only">
                            <br><br>
                            <button class="btn-green" type="submit">Add Lens To Cart</button>
                        </div>
                        {% else %}
                        <div class="alert">
                            <b>No lens product found.</b> Check the selected branch, category and material.
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </form>
            {% endif %}
            {% endif %}

            {% if view == 'frames' %}
            <form id="posForm" method="post">
                <input type="hidden" name="view" value="frames">
                <div class="card">
                    <h3>Add Frames / Accessories</h3>
                    <input id="productSearch" placeholder="🔍 Search frame, case, cleaner, cloth..." onkeyup="filterProductCards()">
                    <br><br>

                    <div class="pos-card-grid">
                        {% for p in product_list %}
                        <div class="pos-item-card product-card">
                            <h3>{{ p.name }}</h3>
                            <p>{{ p.category }} - {{ p.subcategory }}</p>
                            <p><b>Stock:</b> {{ p.quantity }} | {{ stock_badge(p.quantity) }}</p>
                            <p class="small">Retail ₦{{ money(p.retail_price) }} | Wholesale ₦{{ money(p.wholesale_price) }}</p>
                            <input name="qty_{{ p.id }}" type="number" min="0" placeholder="Quantity">
                        </div>
                        {% else %}
                        <div class="alert">
                            <b>No frame/accessory found.</b> Check the selected branch and stock.
                        </div>
                        {% endfor %}
                    </div>
                    <br>
                    <button class="btn-green" type="submit">Add Selected Products To Cart</button>
                </div>
            </form>
            {% endif %}
        </div>

        <div>
            <div class="card floating-cart">
                <h3>🛒 Current Sale</h3>
                {% if cart %}
                <table>
                    <tr><th>Item</th><th>Qty</th><th>Total</th><th></th></tr>
                    {% for item in cart %}
                    <tr>
                        <td>{{ item.product_name }}<br><small>{{ item.lens_power }}</small></td>
                        <td>{{ item.quantity }}</td>
                        <td>₦{{ money(item.subtotal) }}</td>
                        <td><a class="btn-red btn" href="/pos/remove/{{ loop.index0 }}">X</a></td>
                    </tr>
                    {% endfor %}
                </table>
                <h2>Total: ₦{{ money(cart_total) }}</h2>
                <a class="btn-red btn" href="/pos/clear">Clear Cart</a>
                {% else %}
                <div class="alert">No item in cart yet.</div>
                {% endif %}
            </div>

            {% if cart %}
            <div class="card" style="border:2px solid #198754">
                <h3>Checkout</h3>
                <form method="post" action="/pos/checkout">
                    <label>Discount</label>
                    <input name="discount" type="number" step="0.01" value="0">

                    <label>Amount Paid</label>
                    <input name="amount_paid" type="number" step="0.01" placeholder="Amount Paid">

                    <label>Manager PIN for Discount</label>
                    <input name="manager_pin" type="password" placeholder="Only if discount is used">

                    <label>Payment Method</label>
                    <select name="payment_method">
                        <option>Cash</option>
                        <option>Transfer</option>
                        <option>POS</option>
                        <option>Split Payment</option>
                        <option>Credit</option>
                    </select>
                    <br><br>
                    <button class="btn-green" type="submit">Complete Sale / Print Receipt</button>
                </form>
            </div>
            {% endif %}
        </div>
    </div>

    <script>
    function filterPowerCards(){
        const q = document.getElementById("powerSearch").value.toLowerCase();
        document.querySelectorAll(".lens-product-card").forEach(card => {
            const text = card.innerText.toLowerCase();
            card.style.display = text.includes(q) ? "block" : "none";
        });
    }

    function filterProductCards(){
        const q = document.getElementById("productSearch").value.toLowerCase();
        document.querySelectorAll(".product-card").forEach(card => {
            const text = card.innerText.toLowerCase();
            card.style.display = text.includes(q) ? "block" : "none";
        });
    }
    </script>
    """,
    view=view,
    lens_category=lens_category,
    lens_material=lens_material,
    lens_categories=lens_categories,
    lens_materials=lens_materials,
    product_list=product_list,
    lens_map=lens_map,
    lens_stock_map=lens_stock_map,
    recent_lenses=recent_lenses,
    cart=cart,
    cart_total=cart_total,
    customer=customer,
    selected_branch_id=selected_branch_id,
    short_lens_name=short_lens_name,
    stock_badge=stock_badge)
