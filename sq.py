import sqlite3

# Function to create tables if they don't exist


def create_tables():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("drop table users")
    cursor.execute("drop table products")
    cursor.execute("drop table transactions")
    # Create users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user VARCHAR(100),
                        email VARCHAR(100),
                        password VARCHAR(100),
                        mobile VARCHAR(100),
                        name VARCHAR(100),
                        role VARCHAR(100),
                        address VARCHAR(100),
                        privatekey VARCHAR(100),
                        isapprove int
                    )''')

    # Create products table
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        manufacturer_id INTEGER,
                        product_name VARCHAR(100),
                        product_sn VARCHAR(100),
                        productbrand VARCHAR(100),
                        price REAL,
                        owner_id INTEGER,
                        qr varchar(1000),
                        FOREIGN KEY (manufacturer_id) REFERENCES users(id),
                        FOREIGN KEY (owner_id) REFERENCES users(id)
                    )''')

    conn.commit()
    c = conn.cursor()
    #c.execute('''drop table transactions''')
    # Create a table to store transaction hashes and dates if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                (id INTEGER PRIMARY KEY AUTOINCREMENT, hash TEXT, date TEXT,fromid int,toid int,productid int)''')
    conn.commit()
    conn.close()

# Function to insert a user into the users table


# Test the functions
if __name__ == "__main__":
    create_tables()
