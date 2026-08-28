import requests
import sqlite3

db = sqlite3.connect("commerce.db")
c = db.cursor()
c.execute("SELECT id, product_id, merchant_id FROM offers WHERE is_active = 1 LIMIT 1")
offer_id, product_id, merchant_id = c.fetchone()
c.execute("SELECT id FROM customers WHERE merchant_id = ? LIMIT 1", (merchant_id,))
customer_id = c.fetchone()[0]

payload = {
    "merchant_id": merchant_id,
    "customer_id": customer_id,
    "product_id": product_id,
    "offer_id": offer_id,
    "quantity": 1,
    "human_approval": True
}

print("Payload:", payload)
res = requests.post("http://localhost:8000/api/payments/create-direct-order", json=payload)
print(res.status_code)
print(res.text)
