# Agentic Commerce

An autonomous agent-driven commerce platform demonstrating the next evolution of e-commerce.

## Architecture

* **Frontend:** Next.js 14 (App Router), Tailwind CSS, Lucide Icons, Recharts.
* **Backend:** FastAPI, PostgreSQL, LangChain, LangGraph.
* **Agent:** LangGraph StateGraph controlling deterministic execution flows.
* **Database:** PostgreSQL (with SQLAlchemy).
* **Payments:** Razorpay integration for checkout.

## Key Features

- **Agentic Commerce Tool Layer:** A registry of AI tools (Catalog, Inventory, Cart, Policy) accessible to the AI.
- **Revenue Intelligence Engine:** LLM-based upsell/cross-sell generation with explainable scores.
- **Policy & Consent Engine:** Validates pricing and cart amounts, requiring merchant consent for bulk orders.
- **Executive Dashboard:** Analytics on AI vs Direct conversions, funnel dropoffs, and real-time activity feeds.
- **Full Transaction Traceability:** Complete AI reasoning attribution on every order.

## Running Locally

1. **Database Setup**
Ensure PostgreSQL is running locally on port 5432 with a database named `razorpay_hackathon`.
You can change the connection string in `backend/.env`.

2. **Backend Setup**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env # Add your OpenAI and Razorpay keys
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

3. **Frontend Setup**
```bash
cd frontend
npm install
npm run dev
```

## Demo Mode

The platform includes a demo mode. From the Merchant Dashboard sidebar, click **Reset Demo Data** to wipe the database and seed realistic high-fidelity scenarios (Accepted Upsell, Policy Rejection, Consent Required) for the activity timeline.

## Environment Variables

**Backend (`backend/.env`)**
```env
DATABASE_URL=postgresql://user:password@localhost/razorpay_hackathon
OPENAI_API_KEY=sk-...
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
DEMO_MODE=true
```

**Frontend (`frontend/.env.local`)**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```
