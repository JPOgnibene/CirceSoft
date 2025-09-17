import React, { useState, useEffect, useRef } from "react";

const WS_URL = "ws://localhost:8765/ws";                // WebSocket endpoint
const DIRECTIONS_API = "http://localhost:8765/directions";

function WebsocketTester() {
  const [status, setStatus] = useState("Disconnected");
  const [messages, setMessages] = useState([]);
  const [turnLeft, setTurnLeft] = useState(20);
  const [speed, setSpeed] = useState(2.0);
  const wsRef = useRef(null);

  // --- Connect to WebSocket ---
  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setStatus("Connected");
    ws.onmessage = (event) =>
      setMessages((prev) => [...prev, event.data]);
    ws.onclose = () => setStatus("Disconnected");
    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      setStatus("Error");
    };

    return () => ws.close();
  }, []);

  // --- PUT request to update directions.txt ---
  const updateDirections = async () => {
  try {
    const textBody = `TURN_LEFT=${turnLeft}\nSPEED=${speed}`;
    const response = await fetch(DIRECTIONS_API, {
      method: "PUT",
      headers: { "Content-Type": "text/plain" },
      body: textBody,
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const result = await response.text();
    console.log("Updated directions:", result);
    alert("Directions updated successfully!");
  } catch (error) {
    console.error("Error updating directions:", error);
    alert("Failed to update directions");
  }
};


  return (
    <div style={{ border: "1px solid #aaa", padding: "1rem", marginTop: "1rem" }}>
      <h2>WebSocket Tester</h2>
      <p><strong>Status:</strong> {status}</p>

      {/* Update directions form */}
      <div style={{ marginBottom: "1rem" }}>
        <label>
          TURN_LEFT:
          <input
            type="number"
            value={turnLeft}
            onChange={(e) => setTurnLeft(e.target.value)}
            style={{ marginLeft: "0.5rem" }}
          />
        </label>
        <br />
        <label>
          SPEED:
          <input
            type="number"
            step="0.1"
            value={speed}
            onChange={(e) => setSpeed(e.target.value)}
            style={{ marginLeft: "0.5rem" }}
          />
        </label>
        <br />
        <button onClick={updateDirections} style={{ marginTop: "0.5rem" }}>
          Update Directions
        </button>
      </div>

      <h3>Messages from WebSocket (directions.txt)</h3>
      {messages.length === 0 ? (
        <p>No messages yet...</p>
      ) : (
        <ul>
          {messages.map((msg, idx) => (
            <li key={idx}><code>{msg}</code></li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default WebsocketTester;
