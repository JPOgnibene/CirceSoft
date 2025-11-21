import React, { useState, useEffect } from "react";

const DIRECTIONS_API = "http://localhost:8765/directions";

function StartStopButton({ messageBoxRef, onRunningChange, isPathComplete, setIsPathComplete }) {
  const [isRunning, setIsRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Reset isRunning when path completes
  useEffect(() => {
    if (isPathComplete) {
      setIsRunning(false);
    }
  }, [isPathComplete]);

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
    if (isLoading || isPathComplete) return;
    sendCommand(isRunning ? "STOP" : "START");
  };

  const getButtonText = () => {
    if (isLoading) return "⏳ PROCESSING...";
    if (isPathComplete) return "✓ PATH COMPLETE";
    return isRunning ? "⏹ STOP BOT" : "▶ START BOT";
  };

  const buttonStyle = {
    width: "100%",
    padding: "12px 20px",
    border: isPathComplete
      ? "1px solid rgba(0, 255, 159, 0.5)"
      : isRunning 
        ? "1px solid #ff4757" 
        : "1px solid rgba(0, 255, 159, 0.3)",
    borderRadius: "2px",
    cursor: isLoading || isPathComplete ? "not-allowed" : "pointer",
    fontSize: "0.9rem",
    fontWeight: "700",
    letterSpacing: "1px",
    textTransform: "uppercase",
    transition: "all 0.3s ease",
    fontFamily: "'Courier New', monospace",
    backgroundColor: isPathComplete
      ? "rgba(0, 255, 159, 0.25)"
      : isRunning 
        ? "rgba(255, 71, 87, 0.15)" 
        : "rgba(0, 255, 159, 0.15)",
    color: isPathComplete
      ? "#00ff9f"
      : isRunning ? "#ff4757" : "#00ff9f",
    boxShadow: isPathComplete
      ? "0 0 25px rgba(0, 255, 159, 0.5)"
      : isRunning
        ? "0 0 20px rgba(255, 71, 87, 0.3)"
        : "0 0 20px rgba(0, 255, 159, 0.3)",
    opacity: isLoading ? 0.6 : 1,
  };

  return (
    <button
      onClick={handleClick}
      disabled={isLoading || isPathComplete}
      style={buttonStyle}
      title={isPathComplete ? "Path Complete - Reset to Continue" : isRunning ? "Stop Bot" : "Start Bot"}
    >
      {getButtonText()}
    </button>
  );
}

export default StartStopButton;