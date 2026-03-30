Retail IQ Copilot
-----------------
Retail IQ Copilot is an AI-powered analytics assistant that converts natural language questions into SQL queries 
and returns business-ready insights with structured data.

Overview
---------
Retail IQ Copilot enables non-technical users to interact with retail data using simple English queries like:
      “Top 5 products in west in 2017 by sales”
      “Which category grew the fastest in 2017?”

Instead of dashboards or manual SQL, users get:
- Instant results
- Clean insights
- Structured data for visualization

Problem Statement
------------------
Business teams often rely on analysts for routine questions such as:
- Top-performing products
- Category trends
- Regional performance

This leads to:
- Delays in decision-making
- Heavy dependency on technical teams
- Limited self-serve analytics

Solution
--------
Retail IQ Copilot bridges this gap by:
- Converting natural language → SQL
- Querying structured retail data
- Generating concise business insights

Architecture
-------------
User Query
   ↓
FastAPI (/ask endpoint)
   ↓
Intent Detection (metric, filters, grouping)
   ↓
SQL Generation (rule-based)
   ↓
MySQL Execution
   ↓
Data Cleaning & Formatting
   ↓
Insight Generation (LLM + fallback logic)
   ↓
JSON Response



Sample Questions
Basic
1. Top 5 products by sales
2. Bottom 3 products by profit

Category
1. Top categories by sales
2. Best performing category

Regional
1. Top products in west by sales
2. Best category in central region

Time-based
1. Top categories in 2017
2. Best products in 2016

Combined
1. Top 5 products in west in 2017 by sales
2. Bottom categories in east in 2016

Growth
1. Which category grew the fastest in 2017
2. Which category declined the most in 2016


API Usage
Endpoint:
GET /ask?question=<your_query>

Example: http://127.0.0.1:8000/ask?question=top 5 products by sales

Limitations
- LLM dependency for advanced phrasing
- Schema-specific (Superstore dataset)


Future Improvements
- Multi-metric queries (sales + profit together)
- More flexible NLP parsing
- Dashboard UI enhancements
- Caching for faster responses
- Cloud deployment (AWS/GCP)

Author
Arjun A N
