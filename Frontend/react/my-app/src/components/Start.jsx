import React from "react";

const DIRECTIONS_API = "http://localhost:8765/directions";

function StartCommand({ messageBoxRef }) {
  const startBot = async () => {
    try {
      const response = await fetch(DIRECTIONS_API, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "START" }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result = await response.json();
      console.log("START command sent:", result);

      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('success', 'START command sent to the bot');
      }
    } catch (error) {
      console.error("Error sending START:", error);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('error', `Failed to send START: ${error.message}`);
      }
    }
  };

  return (
    <button
      onClick={startBot}
      style={{
        backgroundColor: "green",
        color: "white",
        fontWeight: "bold",
        fontSize: "1.2rem",
        padding: "0.75rem 1.5rem",
        border: "none",
        borderRadius: "50%",
        cursor: "pointer",
        boxShadow: "0px 4px 8px rgba(0,0,0,0.2)",
      }}
      title="Start Command"
    >
      ▶️
    </button>
  );
}

export default StartCommand;
