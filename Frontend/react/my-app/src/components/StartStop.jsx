import React, { useState } from "react";

const DIRECTIONS_API = "http://localhost:8765/directions";

function StartStopButton({ messageBoxRef }) {
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

      setIsRunning(command === "START");
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

  // Base styles matching PathControls buttons
  const buttonBaseStyle = {
    padding: "10px 20px",
    border: "1px solid rgba(0, 255, 159, 0.2)",
    borderRadius: "2px",
    cursor: isLoading ? "not-allowed" : "pointer",
    fontSize: "0.85rem",
    fontWeight: "600",
    letterSpacing: "0.5px",
    textTransform: "uppercase",
    transition: "all 0.15s ease",
    fontFamily: "'Courier New', monospace",
    backgroundColor: "rgba(20, 25, 35, 0.8)",
    position: "relative",
    flex: 1,
  };

  // Active color themes
  const startStyle = {
    ...buttonBaseStyle,
    backgroundColor: `${isRunning ? "rgba(255, 50, 50, 0.15)" : "rgba(0,255,159,0.1)"}`,
    color: isRunning ? "#ff4757" : "#00ff9f",
    borderColor: isRunning ? "#ff4757" : "#00ff9f",
    boxShadow: isRunning
      ? "0 0 15px rgba(255, 71, 87, 0.3)"
      : "0 0 15px rgba(0, 255, 159, 0.2)",
    opacity: isLoading ? 0.6 : 1,
  };

  return (
    <button
      onClick={handleClick}
      disabled={isLoading}
      style={startStyle}
      title={isRunning ? "Stop Bot" : "Start Bot"}
    >
      {isLoading
        ? "PROCESSING..."
        : isRunning
        ? "⏹ STOP BOT"
        : "▶ START BOT"}
    </button>
  );
}

export default StartStopButton;
