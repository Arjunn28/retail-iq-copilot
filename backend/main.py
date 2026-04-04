from fastapi import FastAPI, Query
import mysql.connector
from dotenv import load_dotenv
import re
import requests
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()
load_dotenv()

def format_currency(value):
    if value is None:
        return "$0"
    if abs(value) < 100:
        return f"${value:,.2f}"
    else:
        return f"${value:,.0f}"

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root123",
    database="retail_db",
    unix_socket="/tmp/mysql.sock"
)

@app.get("/")
def home():
    return {"message": "API is working"}

@app.get("/sales")
def get_sales():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales LIMIT 10")
    data = cursor.fetchall()
    cursor.close()
    return {"data": data}

@app.get("/query")
def run_query(q: str = Query(...)):
    cursor = conn.cursor()
    cursor.execute(q)
    data = cursor.fetchall()
    cursor.close()
    return {"data": data}

# -------------------------
# LLM SUMMARY
# -------------------------
def generate_summary(question, metric, primary_name, secondary_name,
                     primary_value, secondary_value, difference, order):

    try:
        if order == "ASC":
            instruction = f"Start with {primary_name}. Emphasize it has the lowest {metric} and is behind {secondary_name}."
        else:
            instruction = f"Start with {primary_name}. Emphasize it leads in {metric} compared to {secondary_name}."

        prompt = f"""
You are a business analyst.

Return ONLY valid JSON:
{{
"insight": "string"
}}

Rules:
- One sentence only
- {instruction}
- Mention ${primary_value}
- Compare with {secondary_name}
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

# -------------------------
# MAIN ENDPOINT
# -------------------------
@app.get("/ask")
def ask(question: str):
    question = question.lower()

    # -------------------------
    # Guardrails
    # -------------------------
    irrelevant_patterns = [
        "hello", "hi", "hii","yo", "hey", "what's up", "how are you",
        "who are you", "help", "thanks", "thank you", "what can you do", "test"
    ]

    if any(re.search(rf"\b{p}\b", question) for p in irrelevant_patterns):
        return {
            "insight": "Hello. Ask something like 'top 5 products by sales'.",
            "data": []
        }

    if len(question.strip()) < 5:
        return {
            "insight": "Please ask a meaningful retail question.",
            "data": []
        }

    # -------------------------
    # Confidence Check (FIXED)
    # -------------------------
    has_metric = bool(re.search(r"(sales|profit|margin)", question))
    has_intent = bool(re.search(r"(top|bottom|best|worst|highest|lowest)", question))
    has_group = bool(re.search(r"(category|product)", question))

    if sum([has_metric, has_intent, has_group]) < 2:
        return {
            "insight": "I couldn't understand your question. Try something like 'top 5 products by sales' or 'lowest performing category in 2017'.",
            "data": []
        }

    cursor = conn.cursor()

    # -------------------------
    # Intent
    # -------------------------
    is_growth_query = any(word in question for word in ["grow", "growth", "grew", "increase"])
    is_decline_query = any(word in question for word in ["decline", "drop", "decrease", "fell"])

    # -------------------------
    # Limit
    # -------------------------
    limit_match = re.search(r"(top|bottom)\s+(\d+)", question)
    generic_match = re.search(r"\b(\d+)\b", question)

    if limit_match:
        limit = int(limit_match.group(2))
    elif generic_match and int(generic_match.group(1)) < 50:
        limit = int(generic_match.group(1))
    else:
        limit = 5

    # -------------------------
    # Order
    # -------------------------
    if re.search(r"(top|best|highest)", question):
        order = "DESC"
    elif re.search(r"(bottom|worst|lowest)", question):
        order = "ASC"
    else:
        order = "DESC"

    # -------------------------
    # Metric
    # -------------------------
    if re.search(r"(profit|margin)", question):
        metric = "profit"
        alias = "total_profit"
    else:
        metric = "sales"
        alias = "total_sales"

    # -------------------------
    # Filters
    # -------------------------
    region_match = re.search(r"(west|east|central|south)", question)
    region_filter = region_match.group().capitalize() if region_match else None

    year_match = re.search(r'(20\d{2})', question)
    year_filter = year_match.group(1) if year_match else None

    # -------------------------
    # Grouping
    # -------------------------
    if re.search(r"(category|categories)", question):
        group_field = "p.category"
        name_alias = "category"
    else:
        group_field = "p.product_name"
        name_alias = "product_name"

    # -------------------------
    # SQL
    # -------------------------
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
    SELECT *
    FROM (
        SELECT {group_field} as {name_alias}, SUM(s.{metric}) as {alias}
        {joins}
        {where_clause}
        GROUP BY {group_field}
    ) ranked
    ORDER BY {alias} {order}
    LIMIT {limit}
    """

    # -------------------------
    # Execute
    # -------------------------
    try:
        cursor.execute(sql_query)
        results = cursor.fetchall()

        columns = [col[0] for col in cursor.description]
        formatted_data = [dict(zip(columns, row)) for row in results]

        clean_data = [
            {
                "name": row[list(row.keys())[0]],
                "value": round(row[list(row.keys())[1]], 2),
                "display_value": format_currency(row[list(row.keys())[1]])
            }
            for row in formatted_data
        ]

        if not clean_data:
            return {"insight": "No data found.", "data": []}

        primary = clean_data[0]
        secondary = clean_data[1] if len(clean_data) > 1 else None

        primary_name = primary["name"]
        primary_value = primary["value"]

        secondary_name = secondary["name"] if secondary else None
        secondary_value = secondary["value"] if secondary else 0

        difference = round(abs(primary_value - secondary_value), 2)

        summary = generate_summary(
            question,
            metric,
            primary_name,
            secondary_name,
            primary_value,
            secondary_value,
            difference,
            order
        )

        # -------------------------
        # Fallback
        # -------------------------
        if not summary:
            if len(clean_data) >= 2:
                if order == "ASC":
                    summary = f"{primary_name} has the lowest {metric} at {format_currency(primary_value)}, trailing {secondary_name} by {format_currency(difference)}."
                else:
                    summary = f"{primary_name} leads with {format_currency(primary_value)} in {metric}, outperforming {secondary_name} by {format_currency(difference)}."
            else:
                summary = f"{primary_name} has {format_currency(primary_value)} in {metric}."

        return {"insight": summary, "data": clean_data}

    except Exception as e:
        return {"error": str(e), "query": sql_query}

    finally:
        cursor.close()