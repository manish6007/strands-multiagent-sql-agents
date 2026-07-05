# Business Rules and Calculations

## Return Policy Rules
- Customer is eligible for refunds if status is 'Returned' within 30 days of `order_date`.
- Returned items are excluded from net sales/revenue growth calculations.

## Churn Identification
- Query filters: `customers.churned = 'Yes'` or customers with no orders in `orders` table where `order_date > current_date - interval '90 days'`.

## Active Status Query Pattern
- When querying active customers, use: `customers.status = 'Active'`.
