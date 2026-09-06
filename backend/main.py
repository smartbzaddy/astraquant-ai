from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx,numpy as np

app=FastAPI(title="AstraQuant AI",version="2.0.1")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
URL="https://api.binance.com/api/v3/klines"

async def data(symbol):
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.get(URL,params={"symbol":symbol.upper(),"interval":"1h","limit":200})
        r.raise_for_status()
        return r.json()

def ema(x,n):
    x=np.asarray(x,float); y=np.empty_like(x); y[0]=x[0]; a=2/(n+1)
    for i in range(1,len(x)): y[i]=a*x[i]+(1-a)*y[i-1]
    return y

def rollmean(x,n):
    x=np.asarray(x,float); y=np.full(len(x),np.nan)
    if len(x)>=n:y[n-1:]=np.convolve(x,np.ones(n)/n,mode="valid")
    return y

def rollstd(x,n):
    x=np.asarray(x,float); y=np.full(len(x),np.nan)
    for i in range(n-1,len(x)):y[i]=np.std(x[i-n+1:i+1])
    return y

def rsi(x,n=14):
    d=np.diff(x,prepend=x[0]); g=np.maximum(d,0); l=np.maximum(-d,0)
    ag=ema(g,n); al=ema(l,n); z=np.full(len(x),50.0); v=al>0
    z[v]=100-100/(1+ag[v]/al[v]); z[(al==0)&(ag>0)]=100
    return z

def indicators(rows):
    c=np.array([float(x[4]) for x in rows])
    e20,e50=ema(c,20),ema(c,50)
    m=ema(c,12)-ema(c,26); ms=ema(m,9); rm=rollmean(c,20); s=rollstd(c,20)
    ret=np.zeros(len(c)); ret[1:]=np.diff(c)/c[:-1]
    return c,e20,e50,rsi(c),m,ms,rm+2*s,rm-2*s,rollstd(ret,20)*np.sqrt(24)

def val(x,d=0):
    x=float(x[-1]); return x if np.isfinite(x) else d

@app.get("/")
async def root():
    return {"app":"AstraQuant AI","version":"2.0.1","status":"online","message":"Live market-analysis engine"}

@app.get("/health")
async def health():
    return {"status":"healthy"}

@app.get("/api/analysis/{symbol}")
async def analysis(symbol:str):
    try:
        rows=await data(symbol)
        if not rows: raise HTTPException(502,"No market data")
        c,e20,e50,r,m,ms,bu,bl,v=indicators(rows)
        price=val(c); score=0; reasons=[]
        if val(e20)>val(e50):score+=1;reasons.append("EMA20 is above EMA50")
        else:score-=1;reasons.append("EMA20 is below EMA50")
        if val(r,50)<30:score+=1;reasons.append("RSI indicates oversold conditions")
        elif val(r,50)>70:score-=1;reasons.append("RSI indicates overbought conditions")
        if val(m)>val(ms):score+=1;reasons.append("MACD is bullish")
        else:score-=1;reasons.append("MACD is bearish")
        if price>val(bu,price):score-=1;reasons.append("Price is above the upper Bollinger Band")
        elif price<val(bl,price):score+=1;reasons.append("Price is below the lower Bollinger Band")
        signal="BUY" if score>=2 else "SELL" if score<=-2 else "HOLD"
        return {"symbol":symbol.upper(),"price":round(price,8),"signal":signal,"confidence":round(min(.95,.5+abs(score)*.1),3),
        "indicators":{"rsi":round(val(r,50),2),"ema20":round(val(e20),8),"ema50":round(val(e50),8),"macd":round(val(m),8),"macd_signal":round(val(ms),8),"bollinger_upper":round(val(bu,price),8),"bollinger_lower":round(val(bl,price),8),"volatility":round(val(v),6)},
        "reasons":reasons,"disclaimer":"Probabilistic market analysis, not financial advice or a guarantee of future performance."}
    except httpx.HTTPStatusError as e:
        raise HTTPException(502,f"Market data provider returned HTTP {e.response.status_code}")
    except HTTPException: raise
    except Exception as e: raise HTTPException(500,f"Analysis failed: {e}")
