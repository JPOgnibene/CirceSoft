import React from "react";

const DIRECTIONS_API = "http://localhost:8765/directions";

function EmergencyStop({ messageBoxRef }) {
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
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('warning', 'Emergency STOP command sent to the bot');
      }
    } catch (error) {
      console.error("Error sending STOP:", error);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('error', `Failed to send STOP: ${error.message}`);
      }
    }
  };

  return (
    <button
      onClick={emergencyStop}
      style={{
        backgroundColor: "red",
        color: "white",
        fontWeight: "bold",
        fontSize: "1.2rem",
        padding: "0.75rem 1.5rem",
        border: "none",
        borderRadius: "50%",
        cursor: "pointer",
        boxShadow: "0px 4px 8px rgba(0,0,0,0.2)",
      }}
      title="Emergency Stop"
    >
      ⏹️
    </button>
  );
}

export default EmergencyStop;
