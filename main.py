from flask import Flask, render_template, request, redirect, session
import psycopg2
import psycopg2.extras
import json

con = psycopg2.connect(dbname='shop', user='postgres', host='local', password='1234')

app = Flask(__name__, template_folder='templates')
app.secret_key = b'1234'


def process_login(domain, passwd):
    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    result = {"C": None, "D": None, "S": None}
    cur.execute("SELECT domain FROM customers WHERE domain='%s' AND passwd='%s'" % (domain, passwd))
    rows = list(map(dict, cur.fetchall()))
    if len(rows) > 0:
        result["C"] = rows[0]["domain"]
    cur.execute("SELECT did FROM delivery WHERE domain='%s' AND passwd='%s'" % (domain, passwd))
    rows = list(map(dict, cur.fetchall()))
    if len(rows) > 0:
        result["D"] = rows[0]["did"]
    cur.execute("SELECT seller_id FROM sellers WHERE domain='%s' AND passwd='%s'" % (domain, passwd))
    rows = list(map(dict, cur.fetchall()))
    if len(rows) > 0:
        result["S"] = rows[0]["seller_id"]
    cur.close()
    return result


"""
def process_seller_change_info(domain, passwd, name):
    cur.execute("UPDATE seller SET passwd='%s', name='%s' WHERE domain='%s" % (domain, passwd, name))
    con.commit()


def process_customer_change_info(domain, passwd, name):
    cur.execute("UPDATE customer SET passwd='%s', name='%s' WHERE domain='%s" % (domain, passwd, name))
    con.commit()

"""


@app.route("/")
def route_index():
    if session.get("login", False):
        return redirect("/route")
    return render_template('index.html')


## 구매자 관련
@app.route("/customer")
def route_customer():
    if session.get("C", None) is None:
        return redirect("/", code=302)
    return render_template('customer.html')


## 판매자 관련
@app.route("/seller")
def route_seller():
    if session.get("S", None) is None:
        return redirect("/", code=302)

    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM sellers WHERE seller_id='%s'" % (session["S"]))
    seller = list(map(dict, cur.fetchall()))[0]

    cur.execute("SELECT * FROM stores WHERE seller_id='%s'" % (session["S"]))
    stores = list(map(dict, cur.fetchall()))

    orders = []
    for store in stores:
        store["schedules"] = json.loads(store["schedules"])
        cur.execute("SELECT * FROM menu WHERE sid='%s'" % (store["sid"]))
        store["menus"] = list(map(dict, cur.fetchall()))

        cur.execute("SELECT * FROM orders WHERE sid='%s' AND state='대기'" % (store["sid"]))
        orders.extend(list(map(dict, cur.fetchall())))

    cur.close()
    return render_template('seller.html', stores=stores, seller=seller, orders=orders)


@app.route("/seller/change-password", methods=["POST"])
def route_seller_change_password():
    if session.get("S", None) is None:
        return redirect("/", code=302)

    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("UPDATE sellers SET passwd='%s' WHERE seller_id='%s'" % (request.form.get("passwd"), session["S"]))
    con.commit()
    cur.close()

    return json.dumps({"success": True})


@app.route("/seller/change-name", methods=["POST"])
def route_seller_change_name():
    if session.get("S", None) is None:
        return redirect("/", code=302)

    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("UPDATE sellers SET name='%s' WHERE seller_id='%s'" % (request.form.get("sname"), session["S"]))
    con.commit()
    cur.close()

    return json.dumps({"success": True})


@app.route("/seller/change-menu-name", methods=["POST"])
def route_seller_change_menu_name():
    if session.get("S", None) is None:
        return redirect("/", code=302)

    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("UPDATE menu SET menu='%s' WHERE mid='%s'" % (request.form.get("menu"), request.form.get("mid")))
    con.commit()
    cur.close()

    return json.dumps({"success": True})


@app.route("/seller/delete-menu", methods=["POST"])
def route_seller_delete_menu():
    if session.get("S", None) is None:
        return redirect("/", code=302)

    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("DELETE FROM menu WHERE mid='%s'" % (request.form.get("mid")))
    con.commit()
    cur.close()

    return json.dumps({"success": True})


@app.route("/seller/add-menu", methods=["POST"])
def route_seller_add_menu():
    if session.get("S", None) is None:
        return redirect("/", code=302)

    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        "INSERT INTO menu(menu, sid) VALUES('%s', '%s')" % (request.form.get("menu"), request.form.get("store_id")))
    con.commit()
    cur.close()

    return json.dumps({"success": True})


@app.route("/seller/cancel-order", methods=["POST"])
def route_seller_cancel_order():
    if session.get("S", None) is None:
        return redirect("/", code=302)

    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("UPDATE orders SET state='취소' WHERE oid='%s'" % (request.form.get("oid")))
    con.commit()
    cur.close()

    return json.dumps({"success": True})


@app.route("/seller/confirm-order", methods=["POST"])
def route_seller_confirm_order():
    if session.get("S", None) is None:
        return redirect("/", code=302)

    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("UPDATE orders SET state='배송중' WHERE oid='%s'" % (request.form.get("oid")))
    con.commit()
    cur.close()

    return json.dumps({"success": True})


@app.route("/seller/popup", methods=["GET"])
def route_seller_popup():
    if session.get("S", None) is None:
        return redirect("/", code=302)

    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        "SELECT *, POINT(%s, %s) <-> POINT(lat, lng) as distance FROM delivery WHERE stock < 5 ORDER BY distance ASC LIMIT 5" % (
            request.args.get("lat"), request.args.get("lng")))
    deliver = list(map(dict, cur.fetchall()))
    cur.close()
    return render_template("popup.html", deliver=deliver)


## 배달부 관련
@app.route("/deliver")
def route_delivery():
    if session.get("D", False) is None:
        return redirect("/", code=302)

    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM orders WHERE did='%s'" % (session.get("D", False)))
    orders = list(map(dict, cur.fetchall()))
    cur.close()
    return render_template('deliver.html', orders=orders)


@app.route("/login", methods=["POST"])
def route_login():
    domain = request.form.get('domain')
    passwd = request.form.get('passwd')

    result = process_login(domain, passwd)

    if result.get("C", None) is None and result.get("D", None) is None and result.get("S", None) is None:
        return redirect("/", code=302)

    for key in result:
        session[key] = result[key]

    session["domain"] = domain
    session["login"] = True

    return redirect("/route", code=302)


@app.route("/route")
def route_route():
    if not session.get("login", False):
        return redirect("/", code=302)

    if session.get("C", False) is not None and session.get("D", False) is None and session.get("S", False) is None:
        return redirect("/customer", code=302)

    if session.get("C", False) is None and session.get("D", False) is not None and session.get("S", False) is None:
        return redirect("/delivery", code=302)

    if session.get("C", False) is None and session.get("D", False) is None and session.get("S", False) is not None:
        return redirect("/seller", code=302)

    return render_template("choose.html")


if __name__ == "__main__":
    app.run()
