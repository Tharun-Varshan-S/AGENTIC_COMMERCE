import requests

# Fetch active cart
res = requests.get("http://localhost:8000/api/carts/active?customer_id=17f80b9c-2079-4f80-a7d3-2699d01d00f5")
print("Active cart:", res.status_code)
cart = res.json()
cart_id = cart["id"]
print("Cart ID:", cart_id)

# Now let's try to add a valid product to this cart
# We need a valid product_id and offer_id from DB
import sqlite3
import json

db = sqlite3.connect("commerce.db")
c = db.cursor()
c.execute("SELECT id, product_id FROM offers WHERE is_active = 1 LIMIT 1")
row = c.fetchone()
offer_id = row[0]
product_id = row[1]

# Make the request
payload = {"product_id": product_id, "quantity": 1, "offer_id": offer_id}
print("Sending payload:", payload)

res = requests.post(f"http://localhost:8000/api/carts/{cart_id}/items", json=payload)
print("Add item status:", res.status_code)
print("Headers:", res.headers)
print("Response:", res.text)
