# Model Context Protocol (MCP) & Athena Integration Guide

This document describes how the Model Context Protocol is implemented to manage data retrieval tools and details the Amazon Athena query execution layer.

---

## 1. Model Context Protocol (MCP) Architecture
The system integrates Model Context Protocol design patterns to separate tool providers from LLM orchestration logic. 

```
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Backend Core                      │
│                                                              │
│  ┌───────────────┐        Calls       ┌───────────────────┐  │
│  │ RAG/SQL/Exec  │ ─────────────────> │   MCP Client      │  │
│  │    Agents     │                    │ (app/mcp/client)  │  │
│  └───────────────┘                    └─────────┬─────────┘  │
│                                                 │            │
│                                                 ▼            │
│                                       ┌───────────────────┐  │
│                                       │   MCP Registry    │  │
│                                       │ (app/mcp/registry)│  │
│                                       └─────────┬─────────┘  │
│                                                 │            │
│                       ┌─────────────────────────┼─────────────────────────┐
│                       ▼                         ▼                         ▼
│             ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│             │  Postgres MCP Server│     │  Athena MCP Server│     │   S3 MCP Server   │
│             │ (semantic search) │     │ (execute query)   │     │ (read documents)  │
│             └───────────────────┘     └───────────────────┘     └───────────────────┘
└──────────────────────────────────────────────────────────────┘
```

### Exposed MCP Tools
1. **`execute_sql_query(sql: str) -> str`**: Exposes query execution capabilities to downstream agents.
2. **`semantic_search_glossary(query: str, limit: int) -> str`**: Queries the pgvector instance for glossary matching metadata.
3. **`retrieve_knowledge_document(document_name: str) -> str`**: Loads raw knowledge markdown files.

---

## 2. Amazon Athena Database Setup

In a production environment, Athena queries files stored in Amazon S3:

### S3 Path Layout
```
s3://your-analytics-bucket/
├── sample_data/
│   ├── customers/
│   │   └── customers.parquet
│   ├── products/
│   │   └── products.parquet
│   ├── orders/
│   │   └── orders.parquet
│   ├── order_items/
│   │   └── order_items.parquet
│   ├── sales_summary/
│   │   └── sales_summary.parquet
│   └── regions/
│       └── regions.parquet
└── query_results/
```

### Table Schema Definitions (DDL)
To load this data model in Athena, execute the following SQL DDL statements:

```sql
-- CREATE DATABASE
CREATE DATABASE IF NOT EXISTS analytics_db;

-- 1. REGIONS TABLE
CREATE EXTERNAL TABLE IF NOT EXISTS analytics_db.regions (
  region_id INT,
  name STRING,
  country STRING
)
STORED AS PARQUET
LOCATION 's3://your-analytics-bucket/sample_data/regions/';

-- 2. CUSTOMERS TABLE
CREATE EXTERNAL TABLE IF NOT EXISTS analytics_db.customers (
  customer_id INT,
  name STRING,
  email STRING,
  region_id INT,
  status STRING,
  created_at TIMESTAMP,
  churned STRING
)
STORED AS PARQUET
LOCATION 's3://your-analytics-bucket/sample_data/customers/';

-- 3. PRODUCTS TABLE
CREATE EXTERNAL TABLE IF NOT EXISTS analytics_db.products (
  product_id INT,
  name STRING,
  category STRING,
  price DOUBLE,
  cost DOUBLE
)
STORED AS PARQUET
LOCATION 's3://your-analytics-bucket/sample_data/products/';

-- 4. ORDERS TABLE
CREATE EXTERNAL TABLE IF NOT EXISTS analytics_db.orders (
  order_id INT,
  customer_id INT,
  order_date TIMESTAMP,
  total_amount DOUBLE,
  status STRING
)
STORED AS PARQUET
LOCATION 's3://your-analytics-bucket/sample_data/orders/';

-- 5. ORDER ITEMS TABLE
CREATE EXTERNAL TABLE IF NOT EXISTS analytics_db.order_items (
  order_item_id INT,
  order_id INT,
  product_id INT,
  quantity INT,
  price DOUBLE,
  discount DOUBLE
)
STORED AS PARQUET
LOCATION 's3://your-analytics-bucket/sample_data/order_items/';

-- 6. SALES SUMMARY TABLE
CREATE EXTERNAL TABLE IF NOT EXISTS analytics_db.sales_summary (
  date DATE,
  region_id INT,
  total_revenue DOUBLE,
  total_orders INT,
  new_customers INT
)
STORED AS PARQUET
LOCATION 's3://your-analytics-bucket/sample_data/sales_summary/';
```
Once mounted, the same queries generated locally will execute identically against Athena.
