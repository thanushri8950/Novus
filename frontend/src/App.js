import React, { useEffect, useState } from "react";
import "./App.css";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

function App() {
  const [data, setData] = useState([]);
  const [history, setHistory] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);

  // 🔄 FETCH LIVE DATA
  useEffect(() => {
    const fetchData = () => {
      fetch("/shifts_live.json")
        .then((res) => res.json())
        .then((data) => setData(data));
    };

    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  // 📈 BUILD HISTORY (for real-time graph)
  useEffect(() => {
    if (data.length > 0) {
      setHistory((prev) => [...prev.slice(-20), ...data]);
    }
  }, [data]);

  const getColor = (shift) => {
    if (shift.includes("Positive")) return "#00c896";
    if (shift.includes("Negative")) return "#ff3b3b";
    return "#999";
  };

  const sorted = [...data].sort(
    (a, b) => Math.abs(b.change) - Math.abs(a.change)
  );

  const top = sorted[0];

  return (
    <div className="app">
      <h1 className="title">NOVUS TERMINAL</h1>

      {/* 🔥 TOP SIGNAL */}
      {top && (
        <div className="hero">
          <h2>Top Signal</h2>
          <h1>{top.company}</h1>
          <p>${top.price.toFixed(2)}</p>
          <p>{(top.change * 100).toFixed(2)}%</p>
          <p style={{ color: getColor(top.shift) }}>{top.shift}</p>
        </div>
      )}

      {/* 🧠 AI INSIGHT */}
      <div className="insight">
        <h3>AI Insight</h3>
        <p>
          {top
            ? `${top.company} shows strongest movement (${(
                top.change * 100
              ).toFixed(2)}%). Possible momentum forming.`
            : "Analyzing..."}
        </p>
      </div>

      {/* ❓ WHY PANEL */}
      <div className="why">
        <h3>Why this signal?</h3>
        <p>
          {top?.change > 0
            ? "Price increased → positive sentiment detected."
            : "Price decreased → negative sentiment detected."}
        </p>
      </div>

      {/* 📊 MAIN GRAPH (REAL-TIME) */}
      <div className="graph">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={history}>
            <XAxis dataKey="company" stroke="#888" />
            <YAxis stroke="#888" />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="change"
              stroke={top && top.change > 0 ? "#00c896" : "#ff3b3b"}
              strokeWidth={3}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 🔥 HEATMAP */}
      <div className="heatmap">
        {sorted.map((item, i) => (
          <div
            key={i}
            className="heatbox"
            style={{
              background: item.change > 0 ? "#1f8f5f" : "#8f2f2f",
            }}
          >
            {item.company}
            <br />
            {(item.change * 100).toFixed(2)}%
          </div>
        ))}
      </div>

      {/* 🚨 ALERT */}
      {sorted.some((d) => !d.shift.includes("Stable")) && (
        <div className="alert">Market Shift Detected</div>
      )}

      {/* 🧭 TOP MOVERS */}
      <div className="top-movers">
        <h3>Top Movers</h3>
        {sorted.slice(0, 3).map((item, i) => (
          <p key={i}>
            {item.company} — {(item.change * 100).toFixed(2)}%
          </p>
        ))}
      </div>

      {/* 📦 CARDS */}
      <div className="grid">
        {sorted.map((item, index) => (
          <div
            key={index}
            className="card"
            onClick={() => setSelectedStock(item)}
          >
            <h3>{item.company}</h3>
            <p>${item.price.toFixed(2)}</p>
            <p>{(item.change * 100).toFixed(2)}%</p>

            <p style={{ color: getColor(item.shift) }}>
              {item.shift}
            </p>

            {/* 📊 BULLISH / BEARISH */}
            <p className="tag">
              {item.change > 0
                ? "Bullish 📈"
                : item.change < 0
                ? "Bearish 📉"
                : "Neutral"}
            </p>
          </div>
        ))}
      </div>

      {/* 🔍 INDIVIDUAL STOCK GRAPH */}
      {selectedStock && (
        <div className="detail">
          <h2>{selectedStock.company} Analysis</h2>

          <p>Price: ${selectedStock.price.toFixed(2)}</p>
          <p>
            Change: {(selectedStock.change * 100).toFixed(2)}%
          </p>

          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={sorted}>
              <XAxis dataKey="company" />
              <YAxis />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="change"
                stroke="#00c896"
              />
            </LineChart>
          </ResponsiveContainer>

          <button onClick={() => setSelectedStock(null)}>
            Close
          </button>
        </div>
      )}

      {/* 📘 EXPLANATION */}
      <div className="explain">
        <h3>Market Terms</h3>
        <p><b>Bullish:</b> Expect price increase</p>
        <p><b>Bearish:</b> Expect price decrease</p>
        <p><b>Neutral:</b> No strong movement</p>
      </div>
    </div>
  );
}

export default App;