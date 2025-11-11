import React, { useEffect, useState } from "react";
import { useWebSocket } from './Websocket';

function IsMovingStatus({ messageBoxRef, isVisible }) {
  const ws = useWebSocket();
  const [isMoving, setIsMoving] = useState(false);
  
  // Update local state when WebSocket values change
  useEffect(() => {
    if (ws) {
      setIsMoving(ws.isMoving || false);
      console.log('IsMovingStatus - Moving state:', ws.isMoving);
    }
  }, [ws?.isMoving]);

  return (
    <div
      style={{
        maxWidth: isVisible ? "300px" : "0",
        opacity: isVisible ? 1 : 0,
        overflow: "hidden",
        transition: "max-width 0.3s ease, opacity 0.3s ease",
        marginLeft: isVisible ? "8px" : "0",
      }}
    >
      <div
        style={{
          padding: "12px 16px",
          backgroundColor: "rgba(15, 20, 30, 0.9)",
          color: isMoving ? "#00ff9f" : "#6b7280",
          border: isMoving
            ? "1px solid rgba(0, 255, 159, 0.3)"
            : "1px solid rgba(107, 114, 128, 0.3)",
          borderRadius: "2px",
          fontSize: "0.8rem",
          fontWeight: "600",
          letterSpacing: "0.5px",
          fontFamily: "'Courier New', monospace",
          textTransform: "uppercase",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          whiteSpace: "nowrap",
          minWidth: "200px",
        }}
      >
        <div
          style={{
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            backgroundColor: isMoving ? "#00ff9f" : "#6b7280",
            boxShadow: isMoving ? "0 0 10px rgba(0, 255, 159, 0.6)" : "none",
            transition: "all 0.3s ease",
          }}
        />
        <span>
          BOT STATUS:{" "}
          <span style={{ color: isMoving ? "#00ff9f" : "#ff4757", marginLeft: "6px" }}>
            {isMoving ? "MOVING" : "STOPPED"}
          </span>
        </span>
      </div>
    </div>
  );
}

export default IsMovingStatus;