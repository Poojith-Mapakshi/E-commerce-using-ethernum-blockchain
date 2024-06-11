import os
import re
import urllib.request
from flask import *
import sqlite3
from werkzeug.utils import secure_filename
from solcx import compile_standard, install_solc
from web3 import Web3
from PIL import Image
from pyzbar.pyzbar import decode

app = Flask(__name__)


def connect():
    return sqlite3.connect("database.db")


app.secret_key = "secret key"


def contract(address, key, fromid, toid, pid):

    import json

    install_solc("0.6.0")
    with open("./SimpleStorage.sol", "r") as file:
        simple_storage_file = file.read()

    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {"SimpleStorage.sol": {"content": simple_storage_file}},
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["abi", "metadata", "evm.bytecode", "evm.bytecode.sourceMap"]
                    }
                }
            },
        },
        solc_version="0.6.0",
    )

    with open("compiled_code.json", "w") as file:
        json.dump(compiled_sol, file)

    bytecode = compiled_sol["contracts"]["SimpleStorage.sol"]["SimpleStorage"]["evm"][
        "bytecode"
    ]["object"]
    # get abi
    abi = json.loads(
        compiled_sol["contracts"]["SimpleStorage.sol"]["SimpleStorage"]["metadata"]
    )["output"]["abi"]

    import json

    w3 = Web3(Web3.HTTPProvider('HTTP://127.0.0.1:7545'))
    chain_id = 1337
    print(w3.is_connected())
    my_address = address
    private_key = key
    # initialize contract
    SimpleStorage = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(my_address)
    # set up transaction from constructor which executes when firstly
    transaction = SimpleStorage.constructor().build_transaction(
        {"chainId": chain_id, "from": my_address, "nonce": nonce}
    )
    signed_tx = w3.eth.account.sign_transaction(
        transaction, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Transacation completed")
    import datetime
    c = connect()
    transaction_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO transactions (hash, date,fromid,toid,productid) VALUES (?, ?,?,?,?)",
              (tx_hash, transaction_date, fromid, toid, pid))
    c.commit()

    return tx_hash


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route('/logon')
def logon():
    return render_template('signup.html')


@app.route("/signup", methods=["post"])
def signup():
    username = request.form['user']
    name = request.form['name']
    email = request.form['email']
    number = request.form["mobile"]
    password = request.form['password']
    address = request.form["address"]
    private = request.form['private']
    role = request.form['role']
    con = connect()
    cur = con.cursor()
    cur.execute("insert into `users` (`user`,`email`, `password`,`mobile`,`name`,'role',address,privatekey) VALUES (?, ?, ?, ?, ?,?,?,?)",
                (username, email, password, number, name, role, address, private))
    con.commit()
    con.close()
    return render_template("index.html")


@app.route("/signin", methods=["post"])
def signin():
    mail1 = request.form['user']
    password1 = request.form['password']
    con = connect()
    data = 0
    data = con.execute(
        "select `user`, `password`,role from users").fetchall()
    print(data)
    data = con.execute(
        "select `user`, `password`,role,isapprove,id from users where `user` = ? AND `password` = ?", (mail1, password1,)).fetchone()
    print(data)
    try:
        if mail1 == 'admin' and password1 == 'admin':
            session['username'] = "admin"
            return redirect("admin")
        elif mail1 == str(data[0]) and password1 == str(data[1]):
            if (data[3] == 1):
                if data[2] == "manufacturer":
                    session['username'] = data[0]
                    session['id'] = data[4]
                    return redirect("addproduct")
                elif data[2] == "seller":
                    session['username'] = data[0]
                    session['id'] = data[4]
                    return redirect("sellProductSeller")

            else:
                return render_template("index.html")

    except:
        return render_template("index.html")


@app.route('/insertproducts', methods=['POST'])
def insertproducts():
    # Extract data from the form
    manufacturer_id = request.form['manufacturer_id']
    print(manufacturer_id)
    product_name = request.form['product_name']
    product_sn = request.form['product_sn']
    productbrand = request.form['productbrand']
    price = request.form['price']
    owner_id = request.form['manufacturer_id']

    # Connect to SQLite database (or create it if it doesn't exist)
    conn = connect()
    cursor = conn.cursor()
    try:
        cursor.execute('select id from products order by id desc limit 1')
        id = cursor.fetchone()[0]+1
    except:
        id = 1

    # Insert data into the users table
    try:
        cursor.execute('''INSERT INTO products (id,manufacturer_id,product_name,product_sn,productbrand,price,owner_id)values(?,?,?,?,?,?,?)''',
                       (id, manufacturer_id, product_name, product_sn, productbrand, price, owner_id))
        # Commit the transaction
        conn.commit()
        cursor.close()
        conn.close()
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("select * from users where id=?",
                       [manufacturer_id])
        users = cursor.fetchone()
        print(users)
        contract(users[7], users[8], 0, manufacturer_id, id)

        return redirect("addproduct")
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route("/admin")
def admin():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("select * from users where role='manufacturer'")
    users = cursor.fetchall()
    return render_template('viewusers.html', data=users, column=['id', 'user', 'email', 'password', 'mobile', 'name', 'role', 'address', 'privatekey'])


@app.route('/viewtransactions', methods=["POST", "GET"])
def viewtransactions():
    productsn = request.args.get('productsn')
    conn = connect()
    cursor = conn.cursor()
    tx = "select * from transactions where productid=(select productid from products where product_sn='%s')" % (
        productsn)
    print(tx)
    cursor.execute(tx)
    users = cursor.fetchall()
    return render_template('viewtransactions.html', data=users, column=['id', 'hash', 'date', 'fromid', 'toid', 'productid'], c=len(users))


@app.route("/userlogin")
def userlogin():
    return render_template("student.html")


@app.route("/manufacturer")
def manufacture():
    return render_template("manufacturer.html")


@app.route("/addproduct")
def addproduct():
    return render_template("addProduct.html")


@app.route("/addSeller")
def addSeller():
    return render_template("addSeller.html")


@app.route("/transferproducts", methods=["POST"])
def transferproducts():
    product_sn = request.form["product_sn"].split("-")[0]
    sellerCode = request.form["sellerCode"].split("-")[0]
    print(product_sn)
    print(sellerCode)
    conn = connect()
    cursor = conn.cursor()
    k="update products set owner_id='%s' where id='%s'"%(sellerCode, product_sn)
    print(k)
    cursor.execute(k)
    conn.commit()
    
    cursor = conn.cursor()
    cursor.execute("select * from users where id=?",
                   [session["id"]])
    
    users = cursor.fetchone()
    print(users)
    conn.close()
    contract(users[7], users[8], session["id"], sellerCode, product_sn)
    return redirect("sellProductManufacturer")


@app.route("/transferconsumer", methods=["POST"])
def transferconsumer():
    print(request.form)
    product_sn = request.form["product_sn"].split("-")[0]
    sellerCode = request.form["consumerCode"].split("-")[0]
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("select * from users where id=?",
                   [session["id"]])
    users = cursor.fetchone()
    print(users)
    contract(users[7], users[8], session["id"], sellerCode, product_sn)
    import qrcode
    # Function to generate QR code

    def generate_qr_code(data, filename):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save("static/qr/"+filename)
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("select product_sn from products where id=?",
                   [product_sn])
    fn = cursor.fetchone()
    data = "/viewtransactions?productsn=" + \
        str(fn[0])  # Data for the QR id (e.g., URL)
    filename = "product"+product_sn+".png"  # Output filename
    generate_qr_code(data, filename)
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("update products set owner_id=?,qr=? where id=?",
                   (sellerCode, filename, product_sn))
    conn.commit()
    conn.close()
    return redirect("sellProductSeller")


@app.route("/sellProductManufacturer")
def sellProductManufacturer():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("select * from products where owner_id=?", [session["id"]])
    users = cursor.fetchall()
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("select * from users where role='seller'")
    seller = cursor.fetchall()
    print(seller)
    return render_template("sellProductManufacturer.html", users=users, seller=seller)


@app.route("/querySeller")
def querySeller():
    return render_template("querySeller.html")


@app.route("/seller")
def seller():
    return render_template("seller.html")


@app.route('/approve', methods=['POST', "GET"])
def approvemanu():
    a = request.args.get('a')
    address = request.args.get('address')
    key = request.args.get('private')
    contract(address, key, 0, 0, 0)
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("update users set isapprove=? where  id=?", [1, a])
    conn.commit()
    conn.close()
    return redirect("admin")


@app.route('/deleteproducts', methods=['POST', "GET"])
def deleteproducts():
    a = request.args.get('a')
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("delete from products where id=?", [a])
    conn.commit()
    conn.close()
    return redirect("viewproducts")


@app.route('/deleteusers', methods=['POST', "GET"])
def deleteusers():
    a = request.args.get('a')
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("delete from users where id=?", [a])
    conn.commit()
    conn.close()
    return redirect("admin")


@app.route('/viewseller')
def viewseller():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("select * from users where role='seller'")
    users = cursor.fetchall()
    return render_template('viewusers.html', data=users, column=['id', 'user', 'email', 'password', 'mobile', 'name', 'role', 'address', 'privatekey'])


@app.route('/viewproducts')
def viewproducts():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("select * from products")
    users = cursor.fetchall()
    return render_template('viewproducts.html', data=users, column=['id', 'manufacturer_id', 'product_name', 'product_sn', "product_brand", 'price', 'owner_id'])


@app.route("/sellProductSeller")
def sellProductSeller():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("select * from products where owner_id=?", [session["id"]])
    users = cursor.fetchall()
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("select * from users where role='Consumer'")
    seller = cursor.fetchall()
    return render_template("sellProductSeller.html", users=users, seller=seller)


@app.route("/queryProducts")
def queryProducts():
    return render_template("queryProducts.html")


@app.route("/consumer")
def consumer():
    return render_template("consumer.html")


@app.route("/consumerPurchaseHistory")
def consumerPurchaseHistory():
    return render_template("consumerPurchaseHistory.html")


@app.route("/verifyProducts")
def verifyProducts():
    return render_template("verifyProducts.html")


@app.route("/connect")
def connectblockchain():
    return render_template("connect.html")


@app.route("/connectdata")
def connectblockdata():
    address = request.args.get('address')
    key = request.args.get('private')
    contract(address, key)

    return render_template("next.html")


@app.route('/upload_qr', methods=['POST'])
def upload_qr():
    # Check if a file was uploaded
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    # Check if the file has a valid format (image)
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    if file and allowed_file(file.filename):
        try:
            # Read the uploaded image file
            img = Image.open(file.stream)
            # Decode QR code from the image
            decoded_objects = decode(img)
            qr_data = [obj.data.decode('utf-8') for obj in decoded_objects]
            print(qr_data[0])
            if ("/viewtransactions?productsn=" in qr_data[0]):
                x = "genuine"
            else:
                x = "fake"
            return render_template("out.html", qr_data=qr_data[0], x=x)
        except Exception as e:
            print(e)
            return render_template("out.html", qr_data=e)

    return jsonify({"error": "Invalid file format", 'success': 'File uploaded failed'}), 400

# Helper function to check allowed file types


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}


@app.route('/logout')
def home():
    session.pop('username', None)
    return render_template("index.html")


if __name__ == '__main__':
    app.run(debug=True)
