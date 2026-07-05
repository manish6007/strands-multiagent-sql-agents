import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_knowledge_base(base_path):
    os.makedirs(os.path.join(base_path, "data", "knowledge"), exist_ok=True)
    
    # 1. Business Glossary
    glossary_content = """# Business Glossary

## Active Customer
An active customer is defined as any customer who has placed at least one order within the last 90 days. Customers without orders in this period are classified as Inactive.

## Churn Rate
The percentage of customers who have not made a purchase in the last 90 days relative to the total active customer base.
Formula: Churned Customers / Total Registered Customers.

## Customer Churned
A customer is flagged as Churned if they have no active orders in the last 90 days and their historical churned flag is set to 'Yes'.

## Customer Acquisition Cost (CAC)
The total sales and marketing cost divided by the number of new customers acquired in a given period.
"""
    with open(os.path.join(base_path, "data", "knowledge", "business_glossary.md"), "w", encoding="utf-8") as f:
        f.write(glossary_content)

    # 2. KPI Definitions
    kpis_content = """# KPI Definitions

## Revenue Growth
The percentage increase/decrease in revenue over a specified time period (e.g., month-over-month or year-over-year).
Formula: ((Current Period Revenue - Prior Period Revenue) / Prior Period Revenue) * 100

## Average Order Value (AOV)
The average dollar amount spent each time a customer places an order.
Formula: Total Revenue / Total Number of Orders

## Total Revenue
Sum of all sales amounts, calculated as: `quantity * price * (1 - discount)` across order items.

## Sales Target Achievement
The percentage of net sales achieved against set targets for specific regions.
"""
    with open(os.path.join(base_path, "data", "knowledge", "kpi_definitions.md"), "w", encoding="utf-8") as f:
        f.write(kpis_content)

    # 3. Schema Documentation
    schema_content = """# Schema Documentation

## Database Schema Model
The analytics schema consists of the following tables:

### Table: regions
Contains geographical regions.
- `region_id` (INT, Primary Key): Unique identifier for the region.
- `name` (VARCHAR): Name of the region (e.g., North America, Europe, Asia Pacific, Latin America).
- `country` (VARCHAR): Name of the country.

### Table: customers
Contains customer profile details.
- `customer_id` (INT, Primary Key): Unique customer identifier.
- `name` (VARCHAR): Customer's full name.
- `email` (VARCHAR): Customer's email address.
- `region_id` (INT, Foreign Key referencing regions): Region the customer belongs to.
- `status` (VARCHAR): Status of the customer (e.g., 'Active', 'Inactive').
- `created_at` (TIMESTAMP): Customer creation date.
- `churned` (VARCHAR): Churn status ('Yes', 'No').

### Table: products
Contains product metadata.
- `product_id` (INT, Primary Key): Unique product identifier.
- `name` (VARCHAR): Name of the product.
- `category` (VARCHAR): Category (e.g., Electronics, Apparel, Home & Kitchen, Books).
- `price` (DECIMAL): Standard unit selling price.
- `cost` (DECIMAL): Standard unit manufacturing/procurement cost.

### Table: orders
Contains transaction headers.
- `order_id` (INT, Primary Key): Unique order identifier.
- `customer_id` (INT, Foreign Key referencing customers): Customer who placed the order.
- `order_date` (TIMESTAMP): Date and time of order.
- `total_amount` (DECIMAL): Net total value of the order.
- `status` (VARCHAR): Order status (e.g., 'Completed', 'Pending', 'Cancelled', 'Returned').

### Table: order_items
Contains transactional details.
- `order_item_id` (INT, Primary Key): Unique row identifier.
- `order_id` (INT, Foreign Key referencing orders): Order this item belongs to.
- `product_id` (INT, Foreign Key referencing products): Product ordered.
- `quantity` (INT): Number of units purchased.
- `price` (DECIMAL): Unit price at which the product was sold.
- `discount` (DECIMAL): Discount percentage applied (0.0 to 1.0).

### Table: sales_summary
Pre-aggregated daily sales metrics.
- `date` (DATE, Primary Key): Summary date.
- `region_id` (INT, Foreign Key referencing regions): Region aggregated.
- `total_revenue` (DECIMAL): Sum of sales revenues.
- `total_orders` (INT): Total count of orders.
- `new_customers` (INT): Number of new customers created on this date.
"""
    with open(os.path.join(base_path, "data", "knowledge", "schema_documentation.md"), "w", encoding="utf-8") as f:
        f.write(schema_content)

    # 4. Business Rules
    rules_content = """# Business Rules and Calculations

## Return Policy Rules
- Customer is eligible for refunds if status is 'Returned' within 30 days of `order_date`.
- Returned items are excluded from net sales/revenue growth calculations.

## Churn Identification
- Query filters: `customers.churned = 'Yes'` or customers with no orders in `orders` table where `order_date > current_date - interval '90 days'`.

## Active Status Query Pattern
- When querying active customers, use: `customers.status = 'Active'`.
"""
    with open(os.path.join(base_path, "data", "knowledge", "business_rules.md"), "w", encoding="utf-8") as f:
        f.write(rules_content)

def generate_sample_data(base_path):
    data_dir = os.path.join(base_path, "data", "sample_data")
    os.makedirs(data_dir, exist_ok=True)
    
    np.random.seed(42)
    
    # 1. Regions
    regions_df = pd.DataFrame([
        {"region_id": 1, "name": "North America", "country": "United States"},
        {"region_id": 2, "name": "Europe", "country": "United Kingdom"},
        {"region_id": 3, "name": "Asia Pacific", "country": "Japan"},
        {"region_id": 4, "name": "Latin America", "country": "Brazil"},
    ])
    os.makedirs(os.path.join(data_dir, "regions"), exist_ok=True)
    regions_df.to_parquet(os.path.join(data_dir, "regions", "regions.parquet"), index=False)
    
    # 2. Products
    products_df = pd.DataFrame([
        {"product_id": 101, "name": "CloudBook Pro 15", "category": "Electronics", "price": 1299.99, "cost": 750.00},
        {"product_id": 102, "name": "SoundWave Noise Cancelling Headphones", "category": "Electronics", "price": 299.99, "cost": 120.00},
        {"product_id": 103, "name": "EcoFit Premium Running Shoes", "category": "Apparel", "price": 120.00, "cost": 45.00},
        {"product_id": 104, "name": "Aura Comfort ergonomic chair", "category": "Home & Kitchen", "price": 349.99, "cost": 160.00},
        {"product_id": 105, "name": "Infinite Knowledge: AWS Architecture", "category": "Books", "price": 49.99, "cost": 15.00},
        {"product_id": 106, "name": "SmartHome Hub Mini", "category": "Electronics", "price": 89.99, "cost": 35.00},
    ])
    os.makedirs(os.path.join(data_dir, "products"), exist_ok=True)
    products_df.to_parquet(os.path.join(data_dir, "products", "products.parquet"), index=False)

    # 3. Customers
    num_customers = 100
    customer_ids = list(range(1001, 1001 + num_customers))
    names = [
        "John Doe", "Jane Smith", "Alice Johnson", "Bob Brown", "Charlie Green", "Diana Prince", 
        "Evan Wright", "Fiona Gallagher", "George Costanza", "Helen Mirren", "Ian Malcolm", "Julia Roberts"
    ]
    # expand list to match num_customers
    full_names = [names[i % len(names)] + f" {1000 + i}" for i in range(num_customers)]
    emails = [name.lower().replace(" ", "") + "@enterprise.com" for name in full_names]
    region_ids = np.random.choice(regions_df["region_id"], size=num_customers)
    statuses = np.random.choice(["Active", "Inactive"], size=num_customers, p=[0.8, 0.2])
    churned_flags = ["Yes" if s == "Inactive" else "No" for s in statuses]
    
    start_date = datetime.now() - timedelta(days=365)
    created_dates = [start_date + timedelta(days=int(np.random.randint(0, 300))) for _ in range(num_customers)]
    
    customers_df = pd.DataFrame({
        "customer_id": customer_ids,
        "name": full_names,
        "email": emails,
        "region_id": region_ids,
        "status": statuses,
        "created_at": created_dates,
        "churned": churned_flags
    })
    os.makedirs(os.path.join(data_dir, "customers"), exist_ok=True)
    customers_df.to_parquet(os.path.join(data_dir, "customers", "customers.parquet"), index=False)

    # 4. Orders and Order Items
    num_orders = 300
    order_ids = list(range(50001, 50001 + num_orders))
    order_customers = np.random.choice(customer_ids, size=num_orders)
    order_dates = [start_date + timedelta(days=int(np.random.randint(0, 365))) for _ in range(num_orders)]
    order_statuses = np.random.choice(["Completed", "Pending", "Cancelled", "Returned"], size=num_orders, p=[0.85, 0.08, 0.04, 0.03])
    
    orders_data = []
    order_items_data = []
    
    order_item_id_counter = 1
    
    for i in range(num_orders):
        order_id = order_ids[i]
        cust_id = order_customers[i]
        order_date = order_dates[i]
        order_status = order_statuses[i]
        
        # Determine number of items in order
        num_items = np.random.randint(1, 4)
        total_amount = 0.0
        
        # Pick products
        order_prods = np.random.choice(products_df["product_id"], size=num_items, replace=False)
        for prod_id in order_prods:
            qty = int(np.random.randint(1, 3))
            unit_price = float(products_df.loc[products_df["product_id"] == prod_id, "price"].values[0])
            discount = float(np.random.choice([0.0, 0.05, 0.1, 0.2], p=[0.7, 0.15, 0.1, 0.05]))
            item_total = qty * unit_price * (1 - discount)
            total_amount += item_total
            
            order_items_data.append({
                "order_item_id": order_item_id_counter,
                "order_id": order_id,
                "product_id": prod_id,
                "quantity": qty,
                "price": unit_price,
                "discount": discount
            })
            order_item_id_counter += 1
            
        orders_data.append({
            "order_id": order_id,
            "customer_id": cust_id,
            "order_date": order_date,
            "total_amount": round(total_amount, 2),
            "status": order_status
        })
        
    orders_df = pd.DataFrame(orders_data)
    order_items_df = pd.DataFrame(order_items_data)
    
    os.makedirs(os.path.join(data_dir, "orders"), exist_ok=True)
    orders_df.to_parquet(os.path.join(data_dir, "orders", "orders.parquet"), index=False)
    
    os.makedirs(os.path.join(data_dir, "order_items"), exist_ok=True)
    order_items_df.to_parquet(os.path.join(data_dir, "order_items", "order_items.parquet"), index=False)

    # 5. Sales Summary (Pre-aggregated daily sales metrics)
    # Aggregating daily revenue, orders, and new customers per region
    dates = pd.date_range(start=start_date, end=datetime.now(), freq='D')
    sales_summary_data = []
    
    # Pre-calculate lists of customers by created date to quickly count new customers
    new_custs_by_date = customers_df.groupby(customers_df["created_at"].dt.date)["customer_id"].count().to_dict()
    
    for dt in dates:
        dt_date = dt.date()
        # Find orders on this date
        day_orders = orders_df[orders_df["order_date"].dt.date == dt_date]
        
        for region_id in regions_df["region_id"]:
            # Customers in this region
            region_cust_ids = customers_df[customers_df["region_id"] == region_id]["customer_id"].values
            
            # Orders in this region on this day
            region_day_orders = day_orders[day_orders["customer_id"].isin(region_cust_ids)]
            
            total_rev = region_day_orders[region_day_orders["status"] == "Completed"]["total_amount"].sum()
            total_ords = len(region_day_orders)
            
            # count new customers in this region on this date
            new_custs = customers_df[
                (customers_df["created_at"].dt.date == dt_date) & 
                (customers_df["region_id"] == region_id)
            ].shape[0]
            
            sales_summary_data.append({
                "date": dt_date,
                "region_id": region_id,
                "total_revenue": round(total_rev, 2),
                "total_orders": total_ords,
                "new_customers": new_custs
            })
            
    sales_summary_df = pd.DataFrame(sales_summary_data)
    os.makedirs(os.path.join(data_dir, "sales_summary"), exist_ok=True)
    sales_summary_df.to_parquet(os.path.join(data_dir, "sales_summary", "sales_summary.parquet"), index=False)

    print("Knowledge base files and Parquet sample datasets successfully generated.")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    create_knowledge_base(base_dir)
    generate_sample_data(base_dir)
