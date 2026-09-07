from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx,numpy as np

app=FastAPI(title="AstraQuant AI",version="2.0.1")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
COINGECKO_BASE="https://api.coingecko.com/api/v3/coins/{}"
COIN_IDS={
    "BTCUSDT":"bitcoin",
    "BTC":"bitcoin",
    "ETHUSDT":"ethereum",
    "ETH":"ethereum",
    "BNBUSDT":"binancecoin",
    "BNB":"binancecoin",
    "SOLUSDT":"solana",
    "SOL":"solana",
    "XRPUSDT":"ripple",
    "XRP":"ripple",
    "ADAUSDT":"cardano",
    "ADA":"cardano",
    "DOGEUSDT":"dogecoin",
    "DOGE":"dogecoin",
    "AVAXUSDT":"avalanche-2",
    "AVAX":"avalanche-2",
    "DOTUSDT":"polkadot",
    "DOT":"polkadot",
    "LINKUSDT":"chainlink",
    "LINK":"chainlink"
}
async def data(symbol):
    key=symbol.upper()
    coin_id=COIN_IDS.get(key)
    if not coin_id: raise HTTPException(400,"Unsupported symbol")
    url=COINGECKO_BASE.format(coin_id)+"/market_chart"
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.get(url,params={"vs_currency":"usd","days":"30","interval":"hourly"})
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
    c=np.array([float(x[1]) for x in rows["prices"]])
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


def backtest(c, lookahead=24, threshold=0.01):
    c=np.asarray(c,float)
    if len(c)<=lookahead:
        return {"trades":0,"wins":0,"losses":0,"win_rate":0,"total_return":0}

    wins=losses=0
    total_return=0.0
    trades=[]

    for i in range(50,len(c)-lookahead):
        e20=ema(c[:i+1],20)[-1]
        e50=ema(c[:i+1],50)[-1]
        rr=rsi(c[:i+1])[-1]
        macd_line=(ema(c[:i+1],12)-ema(c[:i+1],26))[-1]
        macd_signal=ema(ema(c[:i+1],12)-ema(c[:i+1],26),9)[-1]

        score=0
        if e20>e50: score+=1
        else: score-=1
        if rr<30: score+=1
        elif rr>70: score-=1
        if macd_line>macd_signal: score+=1
        else: score-=1

        if score>=2:
            entry=c[i]
            exit_price=c[i+lookahead]
            result=(exit_price-entry)/entry
            trades.append(result)
        elif score<=-2:
            entry=c[i]
            exit_price=c[i+lookahead]
            result=(entry-exit_price)/entry
            trades.append(result)

    for result in trades:
        total_return += result
        if result>threshold:
            wins+=1
        elif result<0:
            losses+=1

    count=len(trades)
    return {
        "trades":count,
        "wins":wins,
        "losses":losses,
        "win_rate":round((wins/count)*100,2) if count else 0,
        "total_return":round(total_return*100,2)
    }


@app.get("/api/backtest/{symbol}")
async def run_backtest(symbol:str):
    try:
        rows=await data(symbol)
        if not rows:
            raise HTTPException(502,"No market data")

        c=np.array([float(x[1]) for x in rows["prices"]])
        result=backtest(c)

        return {
            "symbol":symbol.upper(),
            "period":"30 days",
            "lookahead_hours":24,
            "strategy":"EMA20/EMA50 + RSI + MACD",
            "backtest":result,
            "disclaimer":"Historical backtest results do not guarantee future performance."
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(502,f"Market data provider returned HTTP {e.response.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500,f"Backtest failed: {e}")
