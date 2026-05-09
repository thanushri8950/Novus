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
  const [open, setOpen] = useState(false);
  const [chat, setChat] = useState([]);
  const [input, setInput] = useState("");

  // 🔄 FETCH LIVE DATA
  useEffect(() => {
    const fetchData = () => {
      fetch(`/shifts_live.json?${Date.now()}`)
        .then((res) => res.json())
        .then((data) => setData(data))
        .catch((err) => console.log("FETCH ERROR:", err));
    };

    fetchData();
    const interval = setInterval(fetchData, 5000); // slower = smoother
    return () => clearInterval(interval);
  }, []);

  // 📈 BUILD HISTORY
  useEffect(() => {
    if (data.length > 0) {
      setHistory((prev) => [
        ...prev.slice(-20),
        ...data.map((d) => ({ ...d })),
      ]);
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

  const top = sorted.length > 0 ? sorted[0] : null;

  // 🤖 SIMPLE CHATBOT
  const handleSend = () => {
    if (!input) return;

    const userMsg = { sender: "user", text: input };
    let reply = "Ask about TSLA, AAPL or 'top stock'";

    const query = input.toLowerCase();

    for (let stock of sorted) {
      if (query.includes(stock.company.toLowerCase())) {
        reply = `${stock.company} is ${
          stock.change > 0 ? "Bullish 📈" : "Bearish 📉"
        } with ${(stock.change * 100).toFixed(2)}% change.`;
      }
    }

    if (query.includes("top")) {
      reply = `${top.company} is the top mover right now 🚀`;
    }

    setChat([...chat, userMsg, { sender: "bot", text: reply }]);
    setInput("");
  };

  return (
    <div className="app">

      {/* 🔝 NAVBAR */}
      <div className="navbar">
        <span className="menu" onClick={() => setOpen(!open)}>☰</span>
        <h1 className="title">NOVUS TERMINAL</h1>
        <span className="live">● LIVE</span>
      </div>

      {/* 📂 DROPDOWN */}
      {open && (
        <div className="dropdown">
          <p onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
            🏠 Home
          </p>
          <p onClick={() => document.getElementById("graph").scrollIntoView()}>
            📊 Graph
          </p>
          <p onClick={() => document.getElementById("cards").scrollIntoView()}>
            📦 Stocks
          </p>
        </div>
      )}

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
        <h3>Market Insight</h3>
        <p>
          {top
            ? `${top.company} is leading the market with strong movement.`
            : "Analyzing..."}
        </p>
      </div>

      {/* 📊 GRAPH */}
      <div className="graph" id="graph">
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

      {/* 📦 CARDS */}
      <div className="grid" id="cards">
        {sorted.map((item, index) => (
          <div
            key={index}
            className="card"
            onClick={() => setSelectedStock(item)}
          >
            <h3>
              {item.company}
              {index === 0 && <span className="badge">🔥</span>}
            </h3>
            <p>${item.price.toFixed(2)}</p>
            <p>{(item.change * 100).toFixed(2)}%</p>
            <p style={{ color: getColor(item.shift) }}>{item.shift}</p>
          </div>
        ))}
      </div>

      {/* 🔍 DETAIL VIEW */}
      {selectedStock && (
        <div className="detail">
          <h2>{selectedStock.company}</h2>
          <p>Price: ${selectedStock.price.toFixed(2)}</p>
          <p>Change: {(selectedStock.change * 100).toFixed(2)}%</p>

          <button onClick={() => setSelectedStock(null)}>Close</button>
        </div>
      )}

      {/* 🤖 CHATBOT */}
      <div className="chat">
        <h3>Market Assistant</h3>

        <div className="chat-box">
          {chat.map((msg, i) => (
            <p key={i}>
              <b>{msg.sender === "user" ? "You" : "Bot"}:</b> {msg.text}
            </p>
          ))}
        </div>

        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about stocks..."
        />
        <button onClick={handleSend}>Send</button>
      </div>

    </div>
  );
}

export default App;