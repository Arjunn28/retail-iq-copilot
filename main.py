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

def generate_summary(question, name_alias, metric, top_name, second_name, top_value, second_value, difference):
    
    try:
        prompt = f"""
        You are a business analyst.

        Return ONLY valid JSON:
        {{
        "insight": "string"
        }}

Rules:
- One sentence only
- Start with {top_name}
- Mention ${top_value}
- Compare with {second_name}
- Mention difference ${difference}
- No percentages, no ratios, no extra text

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
            return parsed.get("insight", "")
        except:
            return ""

    except Exception as e:
        print("Ollama error:", e)
        return ""

@app.get("/ask")
def ask(question: str):
    question = question.lower()

    cursor = conn.cursor()

    # -------------------------
    # Detect intent
    # -------------------------
    is_growth_query = any(word in question for word in ["grow", "growth", "grew", "increase"])
    is_decline_query = any(word in question for word in ["decline", "drop", "decrease", "fell"])

    # -------------------------
    # Extract LIMIT
    # -------------------------
    match = re.search(r'\d+', question)
    limit = int(match.group()) if match else 5

    # -------------------------
    # Detect metric
    # -------------------------
    if re.search(r"(profit|margin)", question):
        metric = "profit"
        alias = "total_profit"
    else:
        metric = "sales"
        alias = "total_sales"

    # -------------------------
    # Detect region & year
    # -------------------------
    region_match = re.search(r"(west|east|central|south)", question)
    region_filter = region_match.group().capitalize() if region_match else None

    year_match = re.search(r'(20\d{2})', question)
    year_filter = year_match.group(1) if year_match else None

    # -------------------------
    # Detect grouping
    # -------------------------
    if re.search(r"(category|categories)", question):
        group_field = "p.category"
        name_alias = "category"
    else:
        group_field = "p.product_name"
        name_alias = "product_name"

    sql_query = None

    # -------------------------
    # 1. Growth Query
    # -------------------------
    if (is_growth_query or is_decline_query) and year_filter:
        year = int(year_filter)
        prev_year = year - 1

        order_clause = "ASC" if is_decline_query else "DESC"

        sql_query = f"""
        SELECT 
            curr.category as category,
            (curr.total_sales - prev.total_sales) as growth
        FROM
            (
                SELECT p.category, SUM(s.sales) AS total_sales
                FROM sales s
                JOIN products p ON s.product_id = p.product_id
                JOIN orders o ON s.order_id = o.order_id
                WHERE YEAR(o.order_date) = {year}
                GROUP BY p.category
            ) curr
        JOIN
            (
                SELECT p.category, SUM(s.sales) AS total_sales
                FROM sales s
                JOIN products p ON s.product_id = p.product_id
                JOIN orders o ON s.order_id = o.order_id
                WHERE YEAR(o.order_date) = {prev_year}
                GROUP BY p.category
            ) prev
        ON curr.category = prev.category
        ORDER BY growth {order_clause}
        LIMIT {limit}
        """

        metric = "growth"
        name_alias = "category"

    # -------------------------
    # 2. Normal Query
    # -------------------------
    else:
        joins = """
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        """
        where_conditions = []
        if region_filter:
            joins += "\nJOIN orders o ON s.order_id = o.order_id"
            where_conditions.append(f"o.region = '{region_filter}'")
        
        if year_filter:
            if "JOIN orders o" not in joins:
                joins += "\nJOIN orders o ON s.order_id = o.order_id"
            where_conditions.append(f"YEAR(o.order_date) = {year_filter}")

        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        sql_query = f"""
        SELECT {group_field} as {name_alias}, SUM(s.{metric}) as {alias}
        {joins}
        {where_clause}
        GROUP BY {group_field}
        ORDER BY {alias} DESC
        LIMIT {limit}
        """

    # -------------------------
    # Execute Query
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

        # -------------------------
        # Metrics
        # -------------------------
        top_name = clean_data[0]["name"] if len(clean_data) > 0 else None
        second_name = clean_data[1]["name"] if len(clean_data) > 1 else None

        top_value = clean_data[0]["value"] if len(clean_data) > 0 else 0
        second_value = clean_data[1]["value"] if len(clean_data) > 1 else 0

        difference = round(abs(top_value - second_value), 2)

        # -------------------------
        # LLM Summary
        # -------------------------
        summary = generate_summary(
            question,
            name_alias,
            metric,
            top_name,
            second_name,
            top_value,
            second_value,
            difference
        )

        if (
            not summary
            or any(word in summary.lower() for word in [
                "outperformed", "surpasses", "decrease", "decline", "increased"
            ])
        ):
            summary = None

        # # -------------------------
        # # Fallback Summary
        # # -------------------------
        # if not summary or summary.strip() == "":
        #     if len(clean_data) >= 2:
        #         if metric == "growth":
        #             if is_decline_query:
        #                 if top_value < 0:
        #                     summary = (
        #                         f"{top_name} shows the biggest decline of ${abs(top_value):,.0f}, "
        #                         f"worse than {second_name} by ${abs(difference):,.0f}."
        #                     )
        #                 else:
        #                     summary = (
        #                         f"{top_name} shows the lowest growth of ${top_value:,.0f}, "
        #                         f"trailing {second_name} by ${abs(difference):,.0f}."
        #                     )
        #             else:
        #                 summary = (
        #                     f"{top_name} shows the highest growth of ${top_value:,.0f}, "
        #                     f"ahead of {second_name} by ${difference:,.0f}."
        #                 )
        #         else:
        #             summary = "No data available"

        # return {
        #     "insight": summary,
        #     "data": clean_data
        # }
    

        # -------------------------
        # Fallback Summary (FINAL)
        # -------------------------
        if not summary or "leads with" not in summary.lower():
            if len(clean_data) >= 2:
                if metric == "growth":
                    if is_decline_query:
                        if top_value < 0:
                            summary = (
                                f"{top_name} shows the biggest decline of ${abs(top_value):,.0f}, "
                                f"worse than {second_name} by ${abs(difference):,.0f}."
                            )
                        else:
                            summary = (
                                f"{top_name} shows the lowest growth of ${top_value:,.0f}, "
                                f"trailing {second_name} by ${abs(difference):,.0f}."
                            )

                    else:
                        summary = (
                            f"{top_name} shows the highest growth of ${top_value:,.0f}, "
                            f"ahead of {second_name} by ${difference:,.0f}."
                        )

                else:
                    summary = (
                        f"{top_name} leads with ${top_value:,.0f} in {metric}, "
                        f"outperforming {second_name} by ${difference:,.0f}."
                    )

            elif len(clean_data) == 1:
                summary = f"{top_name} leads with ${top_value:,.0f} in {metric}."

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