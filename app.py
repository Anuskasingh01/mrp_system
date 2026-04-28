from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from datetime import date, timedelta

app = Flask(__name__)
app.secret_key = 'mrp_secret_key'

app.config['MYSQL_HOST']        = 'localhost'
app.config['MYSQL_USER']        = 'root'
app.config['MYSQL_PASSWORD']    = 'nmit123$'
app.config['MYSQL_DB']          = 'mrp_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as c FROM Products")
    products = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM materials")
    materials = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM PurchaseOrders WHERE status='PENDING'")
    pending = cur.fetchone()['c']
    cur.execute("""
        SELECT COUNT(*) as c FROM (
            SELECT (p.demand * b.quantity_required - m.stock) AS shortage
            FROM Products p
            JOIN BOM b ON p.product_id = b.product_id
            JOIN materials m ON b.material_id = m.material_id
            WHERE (p.demand * b.quantity_required - m.stock) > 0
        ) t
    """)
    shortages = cur.fetchone()['c']
    cur.close()
    return render_template('index.html', products=products, materials=materials,
                           pending=pending, shortages=shortages)

@app.route('/products')
def products():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Products ORDER BY product_name")
    rows = cur.fetchall()
    cur.close()
    return render_template('products/index.html', products=rows)

@app.route('/products/add', methods=['GET','POST'])
def add_product():
    if request.method == 'POST':
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Products (product_name,product_code,demand,unit) VALUES (%s,%s,%s,%s)",
            (request.form['product_name'], request.form['product_code'],
             request.form['demand'], request.form['unit']))
        mysql.connection.commit()
        cur.close()
        flash('Product added!', 'success')
        return redirect(url_for('products'))
    return render_template('products/add.html')

@app.route('/products/edit/<int:id>', methods=['GET','POST'])
def edit_product(id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        cur.execute("UPDATE Products SET product_name=%s,product_code=%s,demand=%s,unit=%s WHERE product_id=%s",
            (request.form['product_name'], request.form['product_code'],
             request.form['demand'], request.form['unit'], id))
        mysql.connection.commit()
        cur.close()
        flash('Product updated!', 'success')
        return redirect(url_for('products'))
    cur.execute("SELECT * FROM Products WHERE product_id=%s", (id,))
    product = cur.fetchone()
    cur.close()
    return render_template('products/edit.html', product=product)

@app.route('/products/delete/<int:id>')
def delete_product(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Products WHERE product_id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Product deleted.', 'success')
    return redirect(url_for('products'))

@app.route('/materials')
def materials():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM materials ORDER BY material_name")
    rows = cur.fetchall()
    cur.close()
    return render_template('materials/index.html', materials=rows)

@app.route('/materials/add', methods=['GET','POST'])
def add_material():
    if request.method == 'POST':
        cur = mysql.connection.cursor()
        cur.execute("""INSERT INTO materials
            (material_name,material_code,stock,reorder_point,safety_stock,unit_cost,supplier_name,lead_time_days)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (request.form['material_name'], request.form['material_code'],
             request.form['stock'],         request.form['reorder_point'],
             request.form['safety_stock'],  request.form['unit_cost'],
             request.form['supplier_name'], request.form['lead_time_days']))
        mysql.connection.commit()
        cur.close()
        flash('Material added!', 'success')
        return redirect(url_for('materials'))
    return render_template('materials/add.html')

@app.route('/materials/edit/<int:id>', methods=['GET','POST'])
def edit_material(id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        cur.execute("""UPDATE materials SET
            material_name=%s,material_code=%s,stock=%s,reorder_point=%s,
            safety_stock=%s,unit_cost=%s,supplier_name=%s,lead_time_days=%s
            WHERE material_id=%s""",
            (request.form['material_name'], request.form['material_code'],
             request.form['stock'],         request.form['reorder_point'],
             request.form['safety_stock'],  request.form['unit_cost'],
             request.form['supplier_name'], request.form['lead_time_days'], id))
        mysql.connection.commit()
        cur.close()
        flash('Material updated!', 'success')
        return redirect(url_for('materials'))
    cur.execute("SELECT * FROM materials WHERE material_id=%s", (id,))
    material = cur.fetchone()
    cur.close()
    return render_template('materials/edit.html', material=material)

@app.route('/bom')
def bom():
    cur = mysql.connection.cursor()
    pid = request.args.get('product_id', 0, type=int)
    if pid:
        cur.execute("""SELECT p.product_name,m.material_name,b.quantity_required,
            m.stock,m.unit,b.bom_id FROM BOM b
            JOIN Products p ON b.product_id=p.product_id
            JOIN materials m ON b.material_id=m.material_id
            WHERE b.product_id=%s ORDER BY m.material_name""", (pid,))
    else:
        cur.execute("""SELECT p.product_name,m.material_name,b.quantity_required,
            m.stock,m.unit,b.bom_id FROM BOM b
            JOIN Products p ON b.product_id=p.product_id
            JOIN materials m ON b.material_id=m.material_id
            ORDER BY p.product_name,m.material_name""")
    bom_rows = cur.fetchall()
    cur.execute("SELECT * FROM Products ORDER BY product_name")
    prods = cur.fetchall()
    cur.close()
    return render_template('bom/index.html', bom=bom_rows, products=prods, selected=pid)

@app.route('/bom/add', methods=['GET','POST'])
def add_bom():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        try:
            cur.execute("INSERT INTO BOM (product_id,material_id,quantity_required) VALUES (%s,%s,%s)",
                (request.form['product_id'], request.form['material_id'], request.form['quantity_required']))
            mysql.connection.commit()
            flash('BOM entry added!', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
        cur.close()
        return redirect(url_for('bom'))
    cur.execute("SELECT * FROM Products ORDER BY product_name")
    prods = cur.fetchall()
    cur.execute("SELECT * FROM materials ORDER BY material_name")
    mats = cur.fetchall()
    cur.close()
    return render_template('bom/add.html', products=prods, materials=mats)

@app.route('/bom/delete/<int:id>')
def delete_bom(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM BOM WHERE bom_id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('BOM entry removed.', 'success')
    return redirect(url_for('bom'))

@app.route('/mrp/calculate')
def mrp_calculate():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.product_id, p.product_name, p.demand,
               m.material_id, m.material_name, m.stock,
               m.reorder_point, m.safety_stock, m.unit_cost,
               m.supplier_name, m.lead_time_days, SUM(b.quantity_required) AS quantity_required,
               (p.demand * SUM(b.quantity_required)) AS total_required,
               (p.demand * SUM(b.quantity_required) - m.stock) AS shortage
        FROM Products p
        JOIN BOM b ON p.product_id = b.product_id
        JOIN materials m ON b.material_id = m.material_id
         GROUP BY p.product_id, m.material_id
        ORDER BY shortage DESC, p.product_name
    """)
    rows = cur.fetchall()
    cur.close()
    from decimal import Decimal
    for r in rows:
        r['has_shortage']  = r['shortage'] > 0
        r['below_reorder'] = r['stock'] < r['reorder_point']
        r['order_qty']     = max(0, r['shortage'] + r['safety_stock']) 
        r['status'] = 'ORDER' if r['order_qty'] > 0 else 'OK'
        r['total_cost']    = round(Decimal(r['order_qty']) * (r['unit_cost']), 2)
    total_shortages = sum(1 for r in rows if r['has_shortage'])
    return render_template('mrp/calculate.html', rows=rows, total_shortages=total_shortages)

@app.route('/po')
def purchase_orders():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT po.*, m.material_name, m.unit,
        (po.quantity * po.unit_cost) AS total_cost
        FROM PurchaseOrders po
        JOIN materials m ON po.material_id = m.material_id
        ORDER BY po.po_id DESC""")
    orders = cur.fetchall()
    cur.close()
    return render_template('po/index.html', orders=orders)

@app.route('/po/generate', methods=['GET','POST'])
def generate_po():
    generated = 0
    if request.method == 'POST':
        cur = mysql.connection.cursor()
        cur.execute("""SELECT m.material_id, m.safety_stock, m.unit_cost,
            m.lead_time_days, p.product_name,
            (p.demand * b.quantity_required - m.stock) AS shortage
            FROM Products p
            JOIN BOM b ON p.product_id = b.product_id
            JOIN materials m ON b.material_id = m.material_id
            WHERE (p.demand * b.quantity_required - m.stock) > 0""")
        shortages = cur.fetchall()
        for s in shortages:
            oqty = s['shortage'] + s['safety_stock']
            exp  = date.today() + timedelta(days=s['lead_time_days'])
            cur.execute("""INSERT INTO PurchaseOrders
                (material_id,quantity,unit_cost,status,order_date,expected_date,notes)
                VALUES (%s,%s,%s,'PENDING',%s,%s,%s)""",
                (s['material_id'], oqty, s['unit_cost'],
                 date.today(), exp, f"Auto: {s['product_name']}"))
            generated += 1
        mysql.connection.commit()
        cur.close()
        flash(f'{generated} Purchase Order(s) generated!', 'success')
        return redirect(url_for('purchase_orders'))
    return render_template('po/generate.html')

@app.route('/po/receive/<int:id>')
def receive_po(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE PurchaseOrders SET status='RECEIVED' WHERE po_id=%s AND status='PENDING'",
        (id,))
    mysql.connection.commit()
    cur.close()
    flash('PO received! Stock updated automatically via DB trigger.', 'success')
    return redirect(url_for('purchase_orders'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


