import React, { useEffect, useState } from "react"

const API = window.location.origin

export default function App() {
  const [symbol, setSymbol] = useState("BTCUSDT")
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  async function loadAnalysis() {
    try {
      setLoading(true)
      setError("")
      const res = await fetch(`${API}/api/analysis/${symbol}`)
      if (!res.ok) throw new Error("Unable to load market analysis")
      setData(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAnalysis()
  }, [symbol])

  const indicators = data?.indicators || {}

  return (
    <main className="dashboard">
      <header>
        <div>
          <h1>AstraQuant AI</h1>
          <p>AI-powered crypto market analysis</p>
        </div>

        <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
          <option>BTCUSDT</option>
          <option>ETHUSDT</option>
          <option>BNBUSDT</option>
          <option>SOLUSDT</option>
          <option>XRPUSDT</option>
          <option>ADAUSDT</option>
          <option>DOGEUSDT</option>
          <option>AVAXUSDT</option>
          <option>DOTUSDT</option>
          <option>LINKUSDT</option>
        </select>
      </header>

      {loading && <section className="card">Loading market data...</section>}

      {error && <section className="card error">{error}</section>}

      {data && !loading && (
        <>
          <section className="hero card">
            <div>
              <span className="label">{data.symbol}</span>
              <h2>${Number(data.price).toLocaleString()}</h2>
            </div>

            <div className={`signal ${data.signal.toLowerCase()}`}>
              {data.signal}
            </div>

            <div className="confidence">
              Confidence
              <strong>{(data.confidence * 100).toFixed(0)}%</strong>
            </div>
          </section>

          <section className="grid">
            <Metric title="RSI" value={indicators.rsi?.toFixed(2)} />
            <Metric title="EMA 20" value={indicators.ema20?.toFixed(2)} />
            <Metric title="EMA 50" value={indicators.ema50?.toFixed(2)} />
            <Metric title="MACD" value={indicators.macd?.toFixed(2)} />
            <Metric title="MACD Signal" value={indicators.macd_signal?.toFixed(2)} />
            <Metric title="Volatility" value={indicators.volatility?.toFixed(4)} />
          </section>

          <section className="card">
            <h3>Market reasoning</h3>
            {data.reasons?.length ? (
              <ul>
                {data.reasons.map((reason, index) => (
                  <li key={index}>{reason}</li>
                ))}
              </ul>
            ) : (
              <p>No additional signals available.</p>
            )}
          </section>

          <section className="card">
            <h3>Risk notice</h3>
            <p>
              This is probabilistic market analysis, not financial advice or a
              guarantee of future performance.
            </p>
          </section>
        </>
      )}
    </main>
  )
}

function Metric({ title, value }) {
  return (
    <div className="card metric">
      <span>{title}</span>
      <strong>{value ?? "--"}</strong>
    </div>
  )
}
