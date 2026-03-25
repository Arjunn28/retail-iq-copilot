from fastapi import FastAPI
import mysql.connector
import os
from dotenv import load_dotenv
from openai import OpenAI
import re

app = FastAPI()
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root123",
    database="retail_db",
    unix_socket="/tmp/mysql.sock"
)

@app.get("/")
def home():
    return {"message": "API is working 🚀"}

@app.get("/sales")
def get_sales():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales LIMIT 10")
    data = cursor.fetchall()
    cursor.close()
    return {"data": data}

from fastapi import Query

@app.get("/query")
def run_query(q: str = Query(...)):
    cursor = conn.cursor()
    cursor.execute(q)
    data = cursor.fetchall()
    cursor.close()
    return {"data": data}

# @app.get("/ask")
# def ask(question: str):
#     prompt = f"""
#     You are a SQL expert.

#     Convert the following question into a MySQL query.

#     Tables:
#     - customers(customer_id, customer_name, segment)
#     - products(product_id, product_name, category, sub_category)
#     - orders(order_id, order_date, ship_date, ship_mode, customer_id, region, state, city)
#     - sales(order_id, product_id, sales, quantity, discount, profit)

#     Question: {question}

#     Only return SQL query. No explanation.
#     """

#     response = client.chat.completions.create(
#         model="gpt-4.1-mini",
#         messages=[{"role": "user", "content": prompt}]
#     )

#     sql_query = response.choices[0].message.content.strip()

#     cursor = conn.cursor()
#     cursor.execute(sql_query)
#     data = cursor.fetchall()
#     cursor.close()

#     return {
#         "query": sql_query,
#         "data": data
#     }


@app.get("/ask")
def ask(question: str):
    question = question.lower()

    # Extract "top N" (default = 5)
    match = re.search(r'top (\d+)', question)
    limit = int(match.group(1)) if match else 5

    regions = ["west", "east", "central", "south"]

    region_filter = None
    for r in regions:
        if r in question:
            region_filter = r.capitalize()
            break

    if ("top" in question or "bottom" in question) and "profit" in question:
        order = "DESC" if "top" in question else "ASC"

        if region_filter:
            sql_query = f"""
            SELECT p.product_name, SUM(s.profit) as total_profit
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            JOIN orders o ON s.order_id = o.order_id
            WHERE o.region = '{region_filter}'
            GROUP BY p.product_name
            ORDER BY total_profit {order}
            LIMIT {limit}
            """
        else:
            sql_query = f"""
            SELECT p.product_name, SUM(s.profit) as total_profit
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            GROUP BY p.product_name
            ORDER BY total_profit {order}
            LIMIT {limit}
            """

    elif ("top" in question or "bottom" in question) and "sales" in question:
        order = "DESC" if "top" in question else "ASC"

        if region_filter:
            sql_query = f"""
            SELECT p.product_name, SUM(s.sales) as total_sales
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            JOIN orders o ON s.order_id = o.order_id
            WHERE o.region = '{region_filter}'
            GROUP BY p.product_name
            ORDER BY total_sales {order}
            LIMIT {limit}
            """
        else:
            sql_query = f"""
            SELECT p.product_name, SUM(s.sales) as total_sales
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            GROUP BY p.product_name
            ORDER BY total_sales {order}
            LIMIT {limit}
            """

    elif "total sales" in question:
        sql_query = "SELECT SUM(sales) as total_sales FROM sales"

    elif "sales by region" in question:
        sql_query = """
        SELECT o.region, SUM(s.sales) as total_sales
        FROM sales s
        JOIN orders o ON s.order_id = o.order_id
        GROUP BY o.region
        """

    else:
        return {"error": "Question not supported yet"}

    cursor = conn.cursor()
    cursor.execute(sql_query)
    data = cursor.fetchall()

    columns = [desc[0] for desc in cursor.description]
    formatted_data = [dict(zip(columns, row)) for row in data]

    cursor.close()

    return {
        "query": sql_query,
        "data": formatted_data
    }