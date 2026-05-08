import React, { useEffect, useState } from "react";
import "./App.css";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";


function App() {
  const [data, setData] = useState([]);

  useEffect(() => {
    const fetchData = () => {
      fetch("/shifts_live.json")
        .then(res => res.json())
        .then(data => setData(data));
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getColor = (shift) => {
    if (shift.includes("Positive")) return "#00ff9c";
    if (shift.includes("Negative")) return "#ff4d4d";
    return "#999";
  };

  const sorted = [...data].sort((a, b) => Math.abs(b.change) - Math.abs(a.change));
  const top = sorted[0];

  return (
    <div className="app">

      <h1 className="title">NOVUS TERMINAL</h1>

      {/* 🔥 TOP SIGNAL */}
      {top && (
        <div className="hero">
          <div>
            <h2>TOP SIGNAL</h2>
            <h1>{top.company}</h1>
          </div>

          <div>
            <p className="price">${top.price.toFixed(2)}</p>
            <p className="change">{(top.change * 100).toFixed(2)}%</p>
            <p className="shift" style={{ color: getColor(top.shift) }}>
              {top.shift}
            </p>
          </div>
        </div>
      )}

      {/* 📊 MARKET STRIP */}
      <div className="ticker">
        {data.map((item, i) => (
          <div key={i} className="ticker-item">
            {item.company}{" "}
            <span style={{ color: getColor(item.shift) }}>
              {(item.change * 100).toFixed(2)}%
            </span>
          </div>
        ))}
      </div>



      {/* 📈 GRAPH */}
<div style={{ height: "300px", marginBottom: "20px" }}>
  <ResponsiveContainer width="100%" height="100%">
    <LineChart data={data}>
      <XAxis dataKey="company" stroke="#888" />
      <YAxis stroke="#888" />
      <Tooltip />
      <Line
        type="monotone"
        dataKey="change"
        stroke="#00ff9c"
        strokeWidth={2}
      />
    </LineChart>
  </ResponsiveContainer>
</div>





      {/* 🚨 ALERT */}
      {data.some(d => !d.shift.includes("Stable")) && (
        <div className="alert">
          ⚠️ LIVE MARKET SHIFT DETECTED
        </div>
      )}

      {/* 📦 GRID */}
      <div className="grid">
        {data.map((item, index) => (
          <div key={index} className="card">
            <h3>{item.company}</h3>
            <p>${item.price.toFixed(2)}</p>
            <p>{(item.change * 100).toFixed(2)}%</p>
            <p style={{ color: getColor(item.shift) }}>
              {item.shift}
            </p>
          </div>
        ))}
      </div>

    </div>
  );
}

export default App;