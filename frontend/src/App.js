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


  return (
    <div className="app">
      <h1 className="title">📊 Market Shift Intelligence</h1>

      {/* 🚨 ALERT */}
{data.some(item => item.shift.includes("Positive") || item.shift.includes("Negative")) && (
  <div style={{
    background: "#ff4d4d",
    padding: "10px",
    borderRadius: "8px",
    marginBottom: "20px",
    textAlign: "center",
    fontWeight: "bold"
  }}>
    ⚠️ Market Shift Detected!
  </div>
)}

{/* 📊 GRAPH */}
<div style={{ height: "300px", marginBottom: "30px" }}>
  <ResponsiveContainer width="100%" height="100%">
    <LineChart data={data}>
      <XAxis dataKey="company" stroke="#ccc" />
      <YAxis stroke="#ccc" />
      <Tooltip />
      <Line type="monotone" dataKey="change" stroke="#00ff9c" strokeWidth={2} />
    </LineChart>
  </ResponsiveContainer>
</div>

      <div className="grid">
        {data.map((item, index) => (
          <div key={index} className="card">
            <h2>{item.company}</h2>

            <p className="price">${item.price.toFixed(2)}</p>

            <p className="change">
              {(item.change * 100).toFixed(2)}%
            </p>

            <p
              className="shift"
              style={{ color: getColor(item.shift) }}
            >
              {item.shift}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;