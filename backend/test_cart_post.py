import requests

cart_id = "a9f21c42-f798-4d34-9a2b-44f6e59e074d" # from screenshot
product_id = "00000000-0000-0000-0000-000000000000" # dummy, just to see the error

resp = requests.post(f"http://localhost:8000/api/carts/{cart_id}/items", json={"product_id": product_id, "quantity": 1})
print(resp.status_code)
print(resp.text)
