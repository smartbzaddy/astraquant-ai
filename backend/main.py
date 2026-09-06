from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AstraQuant AI",
    description="AI-assisted cryptocurrency market analysis platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "app": "AstraQuant AI",
        "status": "online",
        "message": "AI-assisted crypto market analysis API",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/analysis/{symbol}")
def analysis(symbol: str):
    return {
        "symbol": symbol.upper(),
        "signal": "NEUTRAL",
        "confidence": 0.50,
        "message": "Market analysis engine ready for data integration.",
    }
