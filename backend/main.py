def backtest(c, lookahead=24, starting_capital=1000):
    c=np.asarray(c,float)

    if len(c)<=lookahead+50:
        return {
            "trades":0,
            "wins":0,
            "losses":0,
            "win_rate":0,
            "profit_factor":0,
            "total_return":0,
            "max_drawdown":0,
            "final_capital":starting_capital
        }

    capital=float(starting_capital)
    peak=capital
    max_drawdown=0.0
    wins=losses=0
    gross_profit=0.0
    gross_loss=0.0
    trades=[]

    for i in range(50,len(c)-lookahead):
        history=c[:i+1]

        e20=ema(history,20)[-1]
        e50=ema(history,50)[-1]
        rr=rsi(history)[-1]

        macd_values=ema(history,12)-ema(history,26)
        macd_line=macd_values[-1]
        macd_signal=ema(macd_values,9)[-1]

        score=0

        if e20>e50:
            score+=1
        else:
            score-=1

        if rr<30:
            score+=1
        elif rr>70:
            score-=1

        if macd_line>macd_signal:
            score+=1
        else:
            score-=1

        if score>=2:
            direction=1
        elif score<=-2:
            direction=-1
        else:
            continue

        entry=c[i]
        exit_price=c[i+lookahead]

        trade_return=direction*(exit_price-entry)/entry
        capital*=1+trade_return

        if trade_return>0:
            wins+=1
            gross_profit+=trade_return
        else:
            losses+=1
            gross_loss+=abs(trade_return)

        trades.append(trade_return)

        if capital>peak:
            peak=capital

        drawdown=(peak-capital)/peak

        if drawdown>max_drawdown:
            max_drawdown=drawdown

    count=len(trades)

    if gross_loss>0:
        profit_factor=gross_profit/gross_loss
    else:
        profit_factor=float("inf") if gross_profit>0 else 0

    return {
        "trades":count,
        "wins":wins,
        "losses":losses,
        "win_rate":round((wins/count)*100,2) if count else 0,
        "profit_factor":round(profit_factor,2) if np.isfinite(profit_factor) else "infinite",
        "total_return":round(((capital/starting_capital)-1)*100,2),
        "max_drawdown":round(max_drawdown*100,2),
        "starting_capital":starting_capital,
        "final_capital":round(capital,2)
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
