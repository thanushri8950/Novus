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
  const [selectedStock, setSelectedStock] = useState(null);
  const [time, setTime] = useState(new Date());

  // 🔄 LIVE DATA
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

  // ⏰ CLOCK
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const getColor = (shift) => {
    if (shift.includes("Positive")) return "#00c896";
    if (shift.includes("Negative")) return "#ff3b3b";
    return "#999";
  };

  const cleanShift = (shift) =>
    shift.replace("🚀", "").replace("⚠️", "").trim();

  const sorted = [...data].sort(
    (a, b) => Math.abs(b.change) - Math.abs(a.change)
  );

  const top = sorted[0];

  return (
    <div className="app">
      <h1 className="title">NOVUS TERMINAL</h1>

      <p className="meta">
        LIVE • Market Signal Engine • {time.toLocaleTimeString()}
      </p>

      {/* 🔥 HERO */}
      {top && (
        <div className="hero">
          <div>
            <h2>TOP SIGNAL</h2>
            <h1>{top.company}</h1>
          </div>
          <div>
            <p className="price">${top.price.toFixed(2)}</p>
            <p>{(top.change * 100).toFixed(2)}%</p>
            <p style={{ color: getColor(top.shift) }}>
              {cleanShift(top.shift)}
            </p>
          </div>
        </div>
      )}

      {/* 📊 TICKER */}
      <div className="ticker">
        {sorted.map((item, i) => (
          <div key={i}>
            {item.company}{" "}
            <span style={{ color: getColor(item.shift) }}>
              {(item.change * 100).toFixed(2)}%
            </span>
          </div>
        ))}
      </div>

      {/* 📈 GRAPH */}
      <div className="graph">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={sorted}>
            <XAxis dataKey="company" stroke="#777" />
            <YAxis stroke="#777" />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="change"
              stroke={top && top.change > 0 ? "#00c896" : "#ff3b3b"}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 🚨 ALERT */}
      {sorted.some((d) => !d.shift.includes("Stable")) && (
        <div className="alert">MARKET SHIFT DETECTED</div>
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
            className={`card ${
              item.shift.includes("Positive")
                ? "positive"
                : item.shift.includes("Negative")
                ? "negative"
                : ""
            }`}
            onClick={() => setSelectedStock(item)}
          >
            <h3>{item.company}</h3>
            <p>${item.price.toFixed(2)}</p>
            <p>{(item.change * 100).toFixed(2)}%</p>
            <p style={{ color: getColor(item.shift) }}>
              {cleanShift(item.shift)}
            </p>

            <p className="tag">
              {item.change > 0.002
                ? "Strong Bullish"
                : item.change < -0.002
                ? "Strong Bearish"
                : "Neutral"}
            </p>
          </div>
        ))}
      </div>

      {/* 🔍 DETAIL PANEL */}
      {selectedStock && (
        <div className="detail">
          <h2>{selectedStock.company}</h2>

          <p>Price: ${selectedStock.price.toFixed(2)}</p>
          <p>
            Change: {(selectedStock.change * 100).toFixed(2)}%
          </p>
          <p style={{ color: getColor(selectedStock.shift) }}>
            {cleanShift(selectedStock.shift)}
          </p>

          <ResponsiveContainer width="100%" height={220}>
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

          <button
            className="close-btn"
            onClick={() => setSelectedStock(null)}
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}

export default App;