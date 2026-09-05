import razorpay
import os
from dotenv import load_dotenv

load_dotenv()
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

try:
    # Attempting to create an order with UPI mandate params (SBMD)
    data = {
        "amount": 1000,
        "currency": "INR",
        "method": "upi",
        "token": {
            "max_amount": 10000,
            "expire_at": 1893456000,
            "frequency": "as_presented"
        },
        "receipt": "test_receipt_123"
    }
    order = client.order.create(data=data)
    print("SUCCESS: ", order)
except Exception as e:
    print("ERROR: ", str(e))
