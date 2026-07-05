# Schema Documentation

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
