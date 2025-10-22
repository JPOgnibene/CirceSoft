import React from "react";

const DIRECTIONS_API = "http://localhost:8765/directions";

function EmergencyStop() {
  const emergencyStop = async () => {
    try {
      const response = await fetch(DIRECTIONS_API, {
        method: "PUT",
        headers: { "Content-Type": "text/plain" },
        body: "STOP",
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result = await response.text();
      console.log("Emergency STOP sent:", result);
      alert("🚨 EMERGENCY STOP issued!");
    } catch (error) {
      console.error("Error sending STOP:", error);
      alert("Failed to send STOP");
    }
  };

  return (
<button
  onClick={emergencyStop}
  style={{
    background: "#0699fb",         // Blue background
    border: "none",
    borderRadius: "50%",
    width: "44px",                 // Same as your other icons
    height: "44px",
    padding: 0,
    position: "relative",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer"
  }}
  title="Emergency Stop"
>
  {/* Centered red square */}
  <span
    style={{
      width: "15px",
      height: "15px",
      background: "#ea3323",        // Red color for square
      display: "block",
      position: "absolute",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      borderRadius: "4px"           // Slight rounding for modern look
    }}
  />
</button>
  );
}

export default EmergencyStop;
