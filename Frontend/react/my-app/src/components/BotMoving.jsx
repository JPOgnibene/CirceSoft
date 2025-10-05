// src/components/IsMovingStatus.jsx
import React, { useEffect, useState } from "react";

const API_URL = "http://localhost:8765/current-values";

function IsMovingStatus() {
  const [isMoving, setIsMoving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Function to fetch and parse the endpoint
    const fetchStatus = async () => {
      try {
        const response = await fetch(API_URL);
        if (!response.ok) throw new Error("Network response was not ok");
        const text = await response.text();

        // Parse the "isMoving" line (e.g. "isMoving=true")
        const match = text.match(/isMoving=(true|false)/);
        if (match) setIsMoving(match[1] === "true");
      } catch (err) {
        console.error("Error fetching current_values:", err);
        setError(err);
      }
    };

    // Fetch immediately, then every 2 seconds
    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);

    // Cleanup interval on unmount
    return () => clearInterval(interval);
  }, []);

  // Simple visual indicator
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        padding: "4px 8px",
      }}
    >
      <div
        style={{
          width: "14px",
          height: "14px",
          borderRadius: "50%",
          backgroundColor: isMoving ? "limegreen" : "red",
          transition: "background-color 0.3s ease",
        }}
        title={isMoving ? "Moving" : "Stopped"}
      ></div>
      <span style={{ fontSize: "0.9rem", color: "#fff" }}>
        {error ? "Error" : isMoving ? "Moving" : "Stopped"}
      </span>
    </div>
  );
}

export default IsMovingStatus;
