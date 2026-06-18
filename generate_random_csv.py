import csv
import random
from datetime import datetime, timedelta

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Generate 24 months of data
records = []
base_rev = 20000
base_exp = 12000
debt = 2500

for i in range(24):
    year = 2024 + (i // 12)
    month = months[i % 12]
    
    # Add an upward trend + some random noise
    rev = base_rev + (i * 500) + random.randint(-2000, 3000)
    exp = base_exp + (i * 200) + random.randint(-1000, 1500)
    
    # Introduce a couple of bad months to test volatility
    if i in (7, 14):
        rev -= 6000
        exp += 2000

    records.append({
        "Month": f"{month} {year}",
        "Revenue": round(rev, 2),
        "Expenses": round(exp, 2),
        "Debt": debt
    })

with open("random_business_history.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Month", "Revenue", "Expenses", "Debt"])
    writer.writeheader()
    writer.writerows(records)

print("Generated random_business_history.csv with 24 months of data.")
