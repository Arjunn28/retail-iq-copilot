import pandas as pd
import mysql.connector

print("Connecting to DB...")
print("HOST:", "127.0.0.1")

conn = mysql.connector.connect(
    user="root",
    password="root123",
    database="retail_db",
    unix_socket="/tmp/mysql.sock",
    use_pure=True
)

cursor = conn.cursor()

df = pd.read_csv("data/superstore.csv")
print(df.columns)

# customers
customers = df[['Customer ID','Customer Name','Segment']].drop_duplicates()
for _, row in customers.iterrows():
    cursor.execute(
        "INSERT IGNORE INTO customers VALUES (%s, %s, %s)",
        (row['Customer ID'], row['Customer Name'], row['Segment'])
    )

# products
products = df[['Product ID','Product Name','Category','Sub-Category']].drop_duplicates()
for _, row in products.iterrows():
    cursor.execute(
        "INSERT IGNORE INTO products VALUES (%s, %s, %s, %s)",
        (row['Product ID'], row['Product Name'], row['Category'], row['Sub-Category'])
    )

# orders
orders = df[['Order ID','Order Date','Ship Date','Ship Mode','Customer ID','Region','State','City']].drop_duplicates()
for _, row in orders.iterrows():
    cursor.execute(
        "INSERT IGNORE INTO orders VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (row['Order ID'], row['Order Date'], row['Ship Date'], row['Ship Mode'],
         row['Customer ID'], row['Region'], row['State'], row['City'])
    )

# sales
sales = df[['Order ID','Product ID','Sales','Quantity','Discount','Profit']]
for _, row in sales.iterrows():
    cursor.execute(
        "INSERT INTO sales (order_id, product_id, sales, quantity, discount, profit) VALUES (%s, %s, %s, %s, %s, %s)",
        (row['Order ID'], row['Product ID'], row['Sales'], row['Quantity'], row['Discount'], row['Profit'])
    )

conn.commit()
cursor.close()
conn.close()

print("Data loaded successfully!")