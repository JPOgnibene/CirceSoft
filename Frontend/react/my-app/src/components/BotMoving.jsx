// src/components/IsMovingStatus.jsx
import React, { useEffect, useState, useRef } from "react";

const API_URL = "http://localhost:8765/current-values";

function IsMovingStatus({ messageBoxRef }) {
  const [isMoving, setIsMoving] = useState(false);
  const [error, setError] = useState(null);
  const previousIsMoving = useRef(null); // Track previous state

  useEffect(() => {
    // Function to fetch and parse the endpoint
    const fetchStatus = async () => {
      try {
        const response = await fetch(API_URL);
        if (!response.ok) throw new Error("Network response was not ok");
        const text = await response.text();
        
        // Parse the "isMoving" line (e.g. "isMoving=true")
        const match = text.match(/isMoving=(true|false)/);
        if (match) {
          const newIsMoving = match[1] === "true";
          
          // Only update and show message if the value has changed
          if (previousIsMoving.current !== null && previousIsMoving.current !== newIsMoving) {
            if (messageBoxRef?.current) {
              messageBoxRef.current.addMessage(
                'info', 
                `Bot is now ${newIsMoving ? "moving" : "stopped"}`
              );
            }
          }
          
          // Update state and ref
          setIsMoving(newIsMoving);
          previousIsMoving.current = newIsMoving;
        }
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
  }, [messageBoxRef]);

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