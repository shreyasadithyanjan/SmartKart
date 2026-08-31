# SmartKart 🛒

**AI-powered multi-agent shopping comparison platform**  
Compare prices across Amazon, Flipkart, Croma, BigBasket & more — instantly.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm or yarn

### 1. Backend

```bash
cd backend

# Copy env file
cp .env.example .env
# (Add your GEMINI_API_KEY if you have one — optional for preloaded mode)

# Install dependencies
pip install -r requirements.txt

# Run the API server
python run.py
# → Backend runs at http://localhost:8000
```

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
# → Frontend runs at http://localhost:3000
```

Open [http://localhost:3000](http://localhost:3000) 🎉

---

## Architecture

```
SmartKart/
├── backend/                 # Python FastAPI backend
│   ├── agents/              # AI agent modules
│   │   ├── search_agent.py
│   │   ├── price_agent.py
│   │   ├── review_agent.py
│   │   ├── deals_agent.py
│   │   ├── price_history_agent.py
│   │   └── conversation_agent.py
│   ├── data/
│   │   ├── products/        # Preloaded JSON datasets (20 products)
│   │   │   ├── phones.json
│   │   │   ├── laptops.json
│   │   │   ├── audio.json
│   │   │   ├── grocery.json
│   │   │   └── appliances.json
│   │   └── index.json
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── services/
│   │   ├── data_service.py  # Loads + searches preloaded data
│   │   └── event_stream.py  # SSE streaming helpers
│   ├── main.py              # FastAPI app
│   └── requirements.txt
├── frontend/                # Next.js 14 frontend
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   ├── components/      # React components
│   │   └── lib/             # Utilities + API client
│   └── package.json
└── README.md
```

## Preloaded Products (Phase 1)

| Category | Products |
|----------|----------|
| 📱 Phones | iPhone 15, Galaxy S24, OnePlus 12R, Pixel 8a, Vivo V30 Pro |
| 💻 Laptops | MacBook Air M3, ASUS ROG Strix G16, HP Pavilion 15, Lenovo IdeaPad Slim 5, Dell XPS 15 |
| 🎧 Audio | Sony WH-1000XM5, boAt Rockerz 550, AirPods Pro 2, JBL Flip 6 |
| 🛒 Grocery | Tata Sampann Tur Dal, Aashirvaad Atta, Amul Butter, Saffola Gold Oil |
| 🏠 Appliances | Dyson V12 Detect Slim, Samsung 1.5T AC |

Each product has:
- ✅ 10 ranked platform results with prices, discounts, offers
- ✅ 24 months of price history
- ✅ Reviews from real Indian users (pre-aggregated)
- ✅ Ready-to-render comparison table data
- ✅ Affiliate redirect URLs

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/trending` | 6 trending products |
| `GET` | `/api/categories` | All categories |
| `GET` | `/api/search?q=<query>` | SSE stream: agents → results |
| `GET` | `/api/product/{id}` | Full product detail |
| `GET` | `/api/product/{id}/price-history` | Price history |
| `POST` | `/api/compare` | Compare 2–3 products |
| `GET` | `/api/category/{cat}` | Products in category |

## Demo Search Queries

These will instantly return preloaded results:
- `iPhone 15`
- `Sony headphones`
- `MacBook Air`
- `boAt rockerz`
- `Samsung AC`
- `Tata Tur Dal`

## Roadmap

- [x] Phase 1: Preloaded datasets with full UI
- [x] Phase 2: Live search via SerpAPI / Google Shopping API
- [x] Phase 3: LLM-powered review summarization (Gemini)
- [ ] Phase 4: Conversational AI with memory
- [ ] Phase 5: Price drop alerts (email/push)
