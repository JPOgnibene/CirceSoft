import React, { useState } from "react";

const DIRECTIONS_API = "http://localhost:8765/directions";

function StartStopButton({ messageBoxRef, onRunningChange }) {
  const [isRunning, setIsRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const sendCommand = async (command) => {
    setIsLoading(true);
    try {
      const response = await fetch(DIRECTIONS_API, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const result = await response.json();
      console.log(`${command} command sent:`, result);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage(
          command === "START" ? "success" : "warning",
          `${command} command sent to the bot`
        );
      }
      const newRunningState = command === "START";
      setIsRunning(newRunningState);
      if (onRunningChange) {
        onRunningChange(newRunningState);
      }
    } catch (error) {
      console.error(`Error sending ${command}:`, error);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage(
          "error",
          `Failed to send ${command}: ${error.message}`
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleClick = () => {
    if (isLoading) return;
    sendCommand(isRunning ? "STOP" : "START");
  };

  const buttonStyle = {
    width: "100%",
    padding: "12px 20px",
    border: isRunning 
      ? "1px solid #ff4757" 
      : "1px solid rgba(0, 255, 159, 0.3)",
    borderRadius: "2px",
    cursor: isLoading ? "not-allowed" : "pointer",
    fontSize: "0.9rem",
    fontWeight: "700",
    letterSpacing: "1px",
    textTransform: "uppercase",
    transition: "all 0.3s ease",
    fontFamily: "'Courier New', monospace",
    backgroundColor: isRunning 
      ? "rgba(255, 71, 87, 0.15)" 
      : "rgba(0, 255, 159, 0.15)",
    color: isRunning ? "#ff4757" : "#00ff9f",
    boxShadow: isRunning
      ? "0 0 20px rgba(255, 71, 87, 0.3)"
      : "0 0 20px rgba(0, 255, 159, 0.3)",
    opacity: isLoading ? 0.6 : 1,
  };

  return (
    <button
      onClick={handleClick}
      disabled={isLoading}
      style={buttonStyle}
      title={isRunning ? "Stop Bot" : "Start Bot"}
    >
      {isLoading ? "⏳ PROCESSING..." : isRunning ? "⏹ STOP BOT" : "▶ START BOT"}
    </button>
  );
}

export default StartStopButton;