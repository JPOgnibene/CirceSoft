import React, { useEffect, useState } from 'react';

const ResetCurrentValues = ({ messageBoxRef }) => {
  const CURRENT_VALUES_ENDPOINT = "http://localhost:8765/current-values";
  const [isResetting, setIsResetting] = useState(false);

  // Default state for current_values
  const DEFAULT_STATE = {
    X_ECI: 0.0,
    Y_ECI: 0.0,
    Z_ECI: 0.0,
    Vx_ECI: 0.0,
    Vy_ECI: 0.0,
    Vz_ECI: 0.0,
    Heading: "",
    cableRemaining: 300.0,
    percentBatteryRemaining: 100,
    errorCode: 0,
    cableDispenseStatus: false,
    cableDispenseCommand: false,
    SequenceNum: "0",
    isMoving: false,
    distanceTraveled: 0.0,
    distanceRemaining: 0.0,
    debug_note: "System initialized"
  };

  // Function to reset current values to default state
  const resetCurrentValues = async () => {
    setIsResetting(true);
    try {
      const response = await fetch(CURRENT_VALUES_ENDPOINT, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(DEFAULT_STATE),
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const result = await response.json();
      console.log("Current values reset to default state:", result);

      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('success', 'Current values reset to default state');
      }
    } catch (error) {
      console.error("Failed to reset current values:", error);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('error', `Failed to reset current values: ${error.message}`);
      }
    } finally {
      setIsResetting(false);
    }
  };

  // Reset on component mount (startup)
  useEffect(() => {
    console.log("ResetCurrentValues mounted - resetting current values on startup");
    resetCurrentValues();
  }, []); // Empty dependency array means this runs once on mount

  const buttonStyle = {
    padding: "10px 20px",
    border: "1px solid rgba(255, 170, 0, 0.3)",
    borderRadius: "2px",
    cursor: isResetting ? "not-allowed" : "pointer",
    fontSize: "0.85rem",
    fontWeight: "600",
    letterSpacing: "0.5px",
    textTransform: "uppercase",
    transition: "all 0.15s ease",
    fontFamily: "'Courier New', monospace",
    backgroundColor: isResetting ? "rgba(20, 25, 35, 0.5)" : "rgba(255, 170, 0, 0.15)",
    color: isResetting ? "#4b5563" : "#ffaa00",
    borderColor: isResetting ? "rgba(75, 85, 99, 0.3)" : "#ffaa00",
    boxShadow: isResetting ? "none" : "0 0 15px rgba(255, 170, 0, 0.2)",
    width: "100%",
  };

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <button
        onClick={resetCurrentValues}
        disabled={isResetting}
        style={buttonStyle}
      >
        {isResetting ? "⏳ RESETTING..." : "🔄 RESET DATA"}
      </button>
    </div>
  );
};

export default ResetCurrentValues;