// src/components/IsMovingStatus.jsx
import React, { useEffect, useState, useRef } from "react";
import { useWebSocket } from './Websocket'; // Adjust path as needed

function IsMovingStatus({ messageBoxRef }) {
  const [isMoving, setIsMoving] = useState(false);
  const [error, setError] = useState(null);
  const previousIsMoving = useRef(null); // Track previous state
  const ws = useWebSocket();

  useEffect(() => {
    // Only proceed if WebSocket is available
    if (!ws) {
      console.warn('WebSocket not available in IsMovingStatus');
      return;
    }

    // Store the original onMessage handler
    const originalHandler = ws.wsClient?.onMessage;

    // Create our custom handler that wraps the original
    const handleWebSocketMessage = (message) => {
      // Call the original handler first
      if (originalHandler) {
        originalHandler(message);
      }

      // Handle current_values_update messages
      if (message.type === 'current_values_update' && message.data) {
        // Check if isMoving field exists in the update
        if ('isMoving' in message.data) {
          const newIsMoving = message.data.isMoving === true;
          
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
          setError(null); // Clear any previous errors
        }
      }
    };

    // Replace the WebSocket handler
    if (ws.wsClient) {
      ws.wsClient.onMessage = handleWebSocketMessage;
    }

    // Cleanup: restore original handler on unmount
    return () => {
      if (ws.wsClient && originalHandler) {
        ws.wsClient.onMessage = originalHandler;
      }
    };
  }, [ws, messageBoxRef]);

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