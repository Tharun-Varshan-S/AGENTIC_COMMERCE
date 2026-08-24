# 🚀 Agentic Commerce Platform

> An AI-Native Merchant Commerce Platform built for the Razorpay Hackathon (Track 01).
> **Goal:** "Grow the merchant's revenue, and make them sellable to AI buyers."

---

## 📖 Overview

Welcome to the **Agentic Commerce Platform** MVP! This project provides a foundational monorepo that connects a modern Next.js frontend to a robust FastAPI backend. It is designed to eventually integrate an intelligent LLM agent orchestrating commerce tasks via explicit tools (e.g., catalog search, cart management, policy checks, and Razorpay order creation).

---

## 🏗 Architecture

The platform uses a clean, decoupled architecture:
- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS v4, shadcn/ui, Recharts
- **Backend**: FastAPI (Python), Pydantic, SQLAlchemy
- **Database**: PostgreSQL
- **Infrastructure**: Docker Compose (for DB isolation)

---

## ⚙️ Prerequisites

Before you begin, ensure you have the following installed:
- [Node.js](https://nodejs.org/) (v18+ recommended)
- [Python](https://www.python.org/) (3.10+ recommended)
- [Docker](https://www.docker.com/) & Docker Compose
- Git

---

## 🛠️ Quick Start (Developer Setup)

Follow these steps to get both the frontend and backend running locally.

### 1. Clone the Repository
```bash
git clone https://github.com/Tharun-Varshan-S/AGENTIC_COMMERCE.git
cd AGENTIC_COMMERCE
```

### 2. Set Up Environment Variables
Copy the example environment variables file and configure your secrets:
```bash
cp .env.example .env
```
*(You will need to set `DATABASE_URL`, Razorpay keys, and `LLM_API_KEY` for later phases).*

### 3. Start the PostgreSQL Database
We use Docker to quickly spin up an isolated database instance.
```bash
docker-compose up -d
```
> The database will run on `localhost:5432`.

### 4. Start the FastAPI Backend
Open a terminal and navigate to the backend directory:
```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the backend development server
uvicorn app.main:app --reload --port 8000

```
> **API Docs**: Available at [http://localhost:8000/docs](http://localhost:8000/docs)
> **Health Check**: Available at [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 5. Start the Next.js Frontend
Open a **new** terminal and navigate to the frontend directory:
```bash
cd frontend

# Install dependencies
npm install

# Run the frontend development server
npm run dev
```
> **Web UI**: Available at [http://localhost:3000](http://localhost:3000)

---

## 🧪 Testing

To ensure the backend is functioning correctly, you can run the test suite:
```bash
cd backend
source venv/bin/activate  # Ensure venv is active
pytest
```

---

## 🔮 Future Roadmap (Phase 2 & Beyond)
- **AI Agent Integration:** Connect LLM to explicit Python commerce tools.
- **Razorpay Integration:** Implement checkout flows and webhooks.
- **Revenue & Policy Engines:** Add business logic gates for LLM actions.
- **Consent Gate:** Require user consent for major purchase actions.

---

<div align="center">
  <i>Built with ❤️ for the Razorpay Hackathon</i>
</div>
