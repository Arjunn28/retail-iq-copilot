from fastapi import FastAPI
import mysql.connector
import os
from dotenv import load_dotenv
from openai import OpenAI
import re
import requests


app = FastAPI()
load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root123",
    database="retail_db",
    unix_socket="/tmp/mysql.sock"
)

cursor = conn.cursor()

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

def generate_sql_with_ollama(question):
    prompt = f"""
You are a SQL expert.

Convert the following question into a valid MySQL query.

Schema:
customers(customer_id, customer_name, segment)
products(product_id, product_name, category, sub_category)
orders(order_id, customer_id, region)
sales(order_id, product_id, sales, profit)

Rules:
- Only return SQL
- No explanation
- ALWAYS include LIMIT 5 unless specified
- Use proper joins
- Use GROUP BY where needed
- Do NOT use subqueries with LIMIT
- Do NOT use nested SELECT
- Use simple GROUP BY + ORDER BY + LIMIT

Question: {question}
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
    )

    raw_sql = response.json()["response"]

# Clean markdown + extra text
    clean_sql = raw_sql.strip()

    if "```" in clean_sql:
        clean_sql = clean_sql.split("```")[1]

    if "limit" not in clean_sql.lower():
        clean_sql += " LIMIT 5"

    return clean_sql.strip()

def generate_summary(question, data, name_alias, metric, top_value, second_value, difference):
    if not data:
        return "No data available"

    try:
        # -------------------------
        # Extract keys dynamically
        # -------------------------
        name_key = list(data[0].keys())[0]
        value_key = list(data[0].keys())[1]

        label = "category" if name_alias == "category" else "product"

        top_name = data[0][name_key]
        top_value = round(data[0][value_key], 2)

        second_name = None
        second_value = None
        ratio = None

        if len(data) > 1:
            second_name = data[1][name_key]
            second_value = round(data[1][value_key], 2)

            if second_value != 0:
                ratio = round(top_value / second_value, 2)

        # -------------------------
        # prompt
        # -------------------------
        prompt = f"""
You are a sharp business analyst.

Return ONLY a valid JSON. No explanation.

Format:
{{
  "insight": "string"
}}

Rules:
- One sentence only
- Start with top {name_alias} name
- Mention top value
- Compare with second {name_alias}
- Mention absolute difference
- No percentages, no ratios
- No markdown, no extra text

Top {name_alias}: {clean_data[0]["name"]} with {top_value}
Second {name_alias}: {clean_data[1]["name"]} with {second_value}
Difference: {difference}

Question: {question}
"""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            }
        )

        import json

        result = response.json()
        raw_output = result.get("response", "").strip()

        raw_output = raw_output.replace("```json", "").replace("```", "").strip()

        try:
            parsed = json.loads(raw_output)
            summary = parsed.get("insight", "")
        except:
            summary = ""

        return summary

    except Exception as e:
        print("Ollama error:", e)

        # -------------------------
        # Fallback (rule-based)
        # -------------------------
        if len(data) > 1 and second_value:
            return (
                f"{top_name} leads with {top_value} in {metric}, "
                f"generating {round(top_value/second_value, 2)}x more than the next {label}."
            )

        return f"{top_name} is the top {label} with {top_value} in {metric}."


@app.get("/ask")
def ask(question: str):
    question = question.lower()

    cursor = conn.cursor()

    # -------------------------
    # 1. Extract LIMIT
    # -------------------------
    match = re.search(r'\d+', question)
    limit = int(match.group()) if match else 5

    # -------------------------
    # 2. Detect TOP / BOTTOM
    # -------------------------
    if re.search(r"(top|best|highest)", question):
        order = "DESC"
    elif re.search(r"(bottom|worst|lowest)", question):
        order = "ASC"
    else:
        order = "DESC"

    # -------------------------
    # 3. Detect METRIC (safe)
    # -------------------------
    if re.search(r"(profit|margin)", question):
        metric = "profit"
        alias = "total_profit"
    elif re.search(r"(sales|revenue)", question):
        metric = "sales"
        alias = "total_sales"
    else:
        metric = "sales"
        alias = "total_sales"

    # -------------------------
    # 4. Detect REGION
    # -------------------------
    region_match = re.search(r"(west|east|central|south)", question)
    region_filter = region_match.group().capitalize() if region_match else None

    year_match = re.search(r'(20\d{2})', question)
    year_filter = year_match.group(1) if year_match else None

    where_clause = ""

    if region_filter and year_filter:
        where_clause = f"WHERE o.region = '{region_filter}' AND YEAR(o.order_date) = {year_filter}"
    elif region_filter:
        where_clause = f"WHERE o.region = '{region_filter}'"
    elif year_filter:
        where_clause = f"WHERE YEAR(o.order_date) = {year_filter}"

    # Detect category vs product level
    if re.search(r"(category|categories)", question):
        group_field = "p.category"
        name_alias = "category"
    else:
        group_field = "p.product_name"
        name_alias = "product_name"
        
    # -------------------------
    # 5. Build SQL (rule-based)
    # -------------------------
    sql_query = None

    try:
        # -------------------------
        # Base FROM + JOIN
        # -------------------------
        joins = """
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        """

        where_conditions = []

        # -------------------------
        # Region filter
        # -------------------------
        if region_filter:
            joins += "\nJOIN orders o ON s.order_id = o.order_id"
            where_conditions.append(f"o.region = '{region_filter}'")

        # -------------------------
        # Year filter
        # -------------------------
        if year_filter:
            if "JOIN orders o" not in joins:
                joins += "\nJOIN orders o ON s.order_id = o.order_id"
            where_conditions.append(f"YEAR(o.order_date) = {year_filter}")

        # -------------------------
        # WHERE clause
        # -------------------------
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        # -------------------------
        # FINAL SQL
        # -------------------------
        sql_query = f"""
        SELECT {group_field} as {name_alias}, SUM(s.{metric}) as {alias}
        {joins}
        {where_clause}
        GROUP BY {group_field}
        ORDER BY {alias} {order}
        LIMIT {limit}
        """

    except Exception as e:
        print("SQL build error:", e)
        sql_query = None
    

    # -------------------------
# 6. Fallback to Ollama
# -------------------------
    if not sql_query:
        try:
            sql_query = generate_sql_with_ollama(question)
        except Exception as e:
            return {
                "error": "LLM failed to generate query",
                "details": str(e)
            }
    # -------------------------
# 7. Execute query
# -------------------------
    try:
        cursor.execute(sql_query)
        results = cursor.fetchall()

        columns = [col[0] for col in cursor.description]
        formatted_data = [dict(zip(columns, row)) for row in results]

        clean_data = [
            {
                "name": row[list(row.keys())[0]],
                "value": round(row[list(row.keys())[1]], 2)
            }
            for row in formatted_data
        ]
        
        top_value = clean_data[0]["value"] if len(clean_data) > 0 else 0
        second_value = clean_data[1]["value"] if len(clean_data) > 1 else 0
        difference = round(top_value - second_value, 2)

        summary = generate_summary(question, formatted_data, name_alias, metric, top_value=top_value, second_value=second_value, difference=difference)

        if not summary or "x more" in summary.lower() or "ratio" in summary.lower():
            if len(clean_data) >= 2:
                summary = (
                    f"{clean_data[0]['name']} leads with ${top_value:,.0f} in {metric}, "
                    f"outperforming {clean_data[1]['name']} by ${difference:,.0f}."
                )
            elif len(clean_data) == 1:
                summary = f"{clean_data[0]['name']} leads with ${top_value:,.0f} in {metric}."
            else:
                summary = "No data available"

        return {
            "insight": summary,
            "data": clean_data
        }

    except Exception as e:
        return {
        "error": "Query execution failed",
        "details": str(e),
        "query": sql_query
        }

    finally:
        cursor.close()