# AI-Native Merchant Commerce Platform for Razorpay (Track 01)

## Project Purpose
"Grow the merchant's revenue, and make them sellable to AI buyers."
This is a production-style MVP built for the Razorpay hackathon. It serves as a foundational monorepo combining a modern Next.js frontend with a robust FastAPI backend and PostgreSQL database.

## Architecture
- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, Recharts.
- **Backend:** FastAPI, Python, Pydantic, SQLAlchemy, PostgreSQL.
- **Database:** PostgreSQL.

## Frontend Setup
1. Navigate to the `frontend` directory: `cd frontend`
2. Install dependencies: `npm install`
3. Run development server: `npm run dev`

## Backend Setup
1. Navigate to the `backend` directory: `cd backend`
2. Create a virtual environment (optional but recommended): `python -m venv venv`
3. Activate the virtual environment:
   - Linux/Mac: `source venv/bin/activate`
   - Windows: `.\venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the server: `fastapi dev app/main.py` (or `uvicorn app.main:app --reload`)
6. Run tests: `pytest`

## PostgreSQL Setup (Docker)
1. Run `docker-compose up -d` in the root directory.
2. The database will be exposed on port `5432`.

## Environment Variables
Copy `.env.example` to `.env` in the root directory (or respective frontend/backend directories based on your deployment strategy) and configure the variables.

- `NEXT_PUBLIC_API_URL`: Points the frontend to the backend API.
- `DATABASE_URL`: PostgreSQL connection string.
- `RAZORPAY_*`: Razorpay integration keys.
- `LLM_API_KEY`: API key for the AI agent (future implementation).

## Running Locally
To start everything locally:
1. Start PostgreSQL: `docker-compose up -d`
2. Start backend API: `cd backend && fastapi run app/main.py`
3. Start frontend App: `cd frontend && npm run dev`
