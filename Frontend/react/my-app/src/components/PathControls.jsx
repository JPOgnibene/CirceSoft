import React, { useState, useEffect } from "react";
import { useWebSocket } from "./Websocket"; // Adjust path as needed

const PathControls = ({
  mode,
  setMode,
  path,
  setPath,
  pathLength,
  distanceTraveled,
  isMoving,
  obstacleCount,
  hasUnsavedObstacleChanges,
  hasUnsavedPathChanges,
  onExportPath,
  onClearPath,
  onImportObstacles,
  onExportObstacles,
  onClearObstacles,
  onRevertObstacles,
  onRevertPath,
  onPathImported,
  messageBoxRef,
}) => {
  const PATH_JSON_ENDPOINT = "http://localhost:8765/grid/path";
  const PATH_WAYPOINTS_ENDPOINT = "http://localhost:8765/grid/waypoints";
  const OBSTACLES_JSON_ENDPOINT = "http://localhost:8765/grid/obstacles";

  const ws = useWebSocket();
  const [waitingForPathUpdate, setWaitingForPathUpdate] = useState(false);

  // Listen for path updates via WebSocket
  useEffect(() => {
    if (!waitingForPathUpdate || !ws?.wsClient) return;

    // Store the original onMessage handler
    const originalOnMessage = ws.wsClient.onMessage;

    // Set a 10-second timeout
    const timeoutId = setTimeout(() => {
      console.log('Path update timeout - stopped waiting after 10 seconds');
      setWaitingForPathUpdate(false);
      
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage(
          'warning',
          'Timeout: No path update received. Please try importing manually.'
        );
      }
    }, 10000);

    // Create a wrapper that checks for path updates
    const handlePathUpdate = async (message) => {
      // Call the original handler first
      originalOnMessage(message);

      // Check if this is a path or waypoints update
      if (message.type === 'path_update' || message.type === 'waypoints_update') {
        console.log('Path update received via WebSocket');
        clearTimeout(timeoutId);
        setWaitingForPathUpdate(false);
        
        if (messageBoxRef?.current) {
          messageBoxRef.current.addMessage(
            'success',
            'Path endpoint updated! Importing path...'
          );
        }

        // Automatically import the updated path
        try {
          const response = await fetch(PATH_JSON_ENDPOINT);
          if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
          }
          
          const json = await response.json();
          const pathData = json.data || json || [];
          
          if (pathData.length === 0) {
            if (messageBoxRef?.current) {
              messageBoxRef.current.addMessage('info', 'No path data found to import');
            }
            return;
          }
          
          const convertedPath = pathData.map(point => ({
            x: point.c || 0,
            y: point.r || 0
          }));
          
          setPath(convertedPath);
          
          // Notify ClickToPath that this is a saved state - this will update the saved/unsaved status
          if (onPathImported) {
            onPathImported(convertedPath);
          }
          
          if (messageBoxRef?.current) {
            messageBoxRef.current.addMessage('success', `Path imported and plotted: ${convertedPath.length} waypoints`);
          }
        } catch (error) {
          console.error("Failed to import path after update:", error);
          if (messageBoxRef?.current) {
            messageBoxRef.current.addMessage('error', 'Failed to import path after update');
          }
        }
      }
    };

    // Temporarily replace the onMessage handler
    ws.wsClient.onMessage = handlePathUpdate;

    // Cleanup: restore original handler and clear timeout when done waiting
    return () => {
      clearTimeout(timeoutId);
      if (ws.wsClient) {
        ws.wsClient.onMessage = originalOnMessage;
      }
    };
  }, [waitingForPathUpdate, ws, messageBoxRef]);

  const handleImportPath = async () => {
    try {
      const response = await fetch(PATH_JSON_ENDPOINT);
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      const json = await response.json();
      const pathData = json.data || json || [];
      
      if (pathData.length === 0) {
        if (messageBoxRef?.current) {
          messageBoxRef.current.addMessage('info', 'No path data found to import');
        }
        return;
      }
      
      const convertedPath = pathData.map(point => ({
        x: point.c || 0,
        y: point.r || 0
      }));
      
      setPath(convertedPath);
      
      // Notify ClickToPath that this is a saved state
      if (onPathImported) {
        onPathImported(convertedPath);
      }
      
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('success', `Path imported: ${convertedPath.length} waypoints`);
      }
      
    } catch (error) {
      console.error("Failed to import path:", error);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('error', 'Failed to import path');
      }
    }
  };

  const handleCombinedExport = async () => {
    let pathSuccess = false;
    let obstaclesSuccess = false;
    
    try {
      // Export path if there are unsaved path changes
      if (hasUnsavedPathChanges && onExportPath) {
        await onExportPath();
        pathSuccess = true;
      }
      
      // Export obstacles if there are unsaved obstacle changes
      if (hasUnsavedObstacleChanges && onExportObstacles) {
        await onExportObstacles();
        obstaclesSuccess = true;
      }
      
      // Show initial success message
      if (pathSuccess && obstaclesSuccess) {
        if (messageBoxRef?.current) {
          messageBoxRef.current.addMessage('success', 'Path & Obstacles exported successfully');
        }
      } else if (pathSuccess) {
        if (messageBoxRef?.current) {
          messageBoxRef.current.addMessage('success', 'Path exported successfully');
        }
      } else if (obstaclesSuccess) {
        if (messageBoxRef?.current) {
          messageBoxRef.current.addMessage('success', 'Obstacles exported successfully');
        }
      }
      
      // If path was exported, wait for WebSocket confirmation
      if (pathSuccess) {
        setWaitingForPathUpdate(true);
        if (messageBoxRef?.current) {
          messageBoxRef.current.addMessage('info', 'Waiting for path endpoint update...');
        }
      }
      
    } catch (error) {
      console.error("Failed to export path/obstacles:", error);
      setWaitingForPathUpdate(false);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('error', 'Failed to export path and/or obstacles');
      }
    }
  };

  const buttonBaseStyle = {
    padding: "10px 20px",
    border: "1px solid rgba(0, 255, 159, 0.2)",
    borderRadius: "2px",
    cursor: "pointer",
    fontSize: "0.85rem",
    fontWeight: "600",
    letterSpacing: "0.5px",
    textTransform: "uppercase",
    transition: "all 0.15s ease",
    fontFamily: "'Courier New', monospace",
    position: "relative",
    overflow: "hidden",
    flex: 1,
    minWidth: 0,
  };

  const modeButtonStyle = (isActive, color) => ({
    ...buttonBaseStyle,
    backgroundColor: isActive ? `${color}25` : "rgba(20, 25, 35, 0.8)",
    color: isActive ? color : "#6b7280",
    borderColor: isActive ? color : "rgba(107, 114, 128, 0.3)",
    boxShadow: isActive ? `0 0 20px ${color}40` : "none",
  });

  const actionButtonStyle = (enabled, color, glowColor) => ({
    ...buttonBaseStyle,
    backgroundColor: enabled ? `${color}15` : "rgba(20, 25, 35, 0.5)",
    color: enabled ? color : "#4b5563",
    borderColor: enabled ? color : "rgba(75, 85, 99, 0.3)",
    cursor: enabled ? "pointer" : "not-allowed",
    boxShadow: enabled ? `0 0 15px ${glowColor}` : "none",
  });

  const toggleMode = (selectedMode) => {
    if (mode === selectedMode) {
      setMode(null);
    } else {
      setMode(selectedMode);
    }
  };

  const hasAnyUnsavedChanges = hasUnsavedPathChanges || hasUnsavedObstacleChanges;

  return (
    <div style={{ marginBottom: "16px", fontFamily: "'Courier New', monospace" }}>
      {/* MODE TOGGLE */}
      <div
        style={{
          display: "flex",
          gap: "12px",
          marginBottom: "16px",
          padding: "6px",
          backgroundColor: "rgba(15, 20, 30, 0.9)",
          border: "1px solid rgba(107, 114, 128, 0.3)",
          borderRadius: "2px",
          width: "100%",
        }}
      >
        <button
          onClick={() => toggleMode("path")}
          style={modeButtonStyle(mode === "path", "#00ff9f")}
        >
          ◉ EDIT PATH
        </button>
        <button
          onClick={() => toggleMode("obstacle")}
          style={modeButtonStyle(mode === "obstacle", "#ff4757")}
        >
          ▲ EDIT OBSTACLES
        </button>
      </div>

      {/* PATH CONTROLS */}
      <div
        style={{
          maxHeight: mode === "path" ? "500px" : "0",
          overflow: "hidden",
          transition:
            "max-height 0.25s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.25s ease",
          opacity: mode === "path" ? 1 : 0,
          width: "100%",
        }}
      >
        <div
         style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "12px",
            marginBottom: "12px",
            width: "100%",
          }}
        >
          {/* <button
            onClick={handleImportPath}
            style={{
              ...actionButtonStyle(true, "#00ff9f", "rgba(0, 255, 159, 0.2)"),
              position: "relative",
            }}
          >
            ⬆ IMPORT PATH
            {waitingForPathUpdate && (
              <span
                style={{
                  position: "absolute",
                  top: "6px",
                  right: "6px",
                  width: "8px",
                  height: "8px",
                  backgroundColor: "#ffaa00",
                  borderRadius: "0",
                  border: "1px solid #ffaa00",
                  boxShadow: "0 0 10px rgba(255, 170, 0, 0.8)",
                  animation: "pulse 2s ease-in-out infinite",
                }}
              />
            )}
          </button>
          <button
            onClick={onExportPath}
            disabled={!hasUnsavedPathChanges}
            style={{
              ...actionButtonStyle(
                hasUnsavedPathChanges,
                "#00d9ff",
                "rgba(0, 217, 255, 0.2)"
              ),
              position: "relative",
            }}
          >
            ⬇ EXPORT PATH
            {hasUnsavedPathChanges && (
              <span
                style={{
                  position: "absolute",
                  top: "6px",
                  right: "6px",
                  width: "8px",
                  height: "8px",
                  backgroundColor: "#ff4757",
                  borderRadius: "0",
                  border: "1px solid #ff4757",
                  boxShadow: "0 0 10px rgba(255, 71, 87, 0.8)",
                  animation: "pulse 2s ease-in-out infinite",
                }}
              />
            )}
          </button> */}

        {/* Button grid - 3 BUTTONS */}

          
          <button
            onClick={onClearPath}
            disabled={path.length === 0}
            style={actionButtonStyle(
              path.length > 0,
              "#ffaa00",
              "rgba(255, 170, 0, 0.2)"
            )}
          >
            ✕ CLEAR PATH
          </button>
          <button
            onClick={onRevertPath}
            disabled={!hasUnsavedPathChanges}
            style={actionButtonStyle(
              hasUnsavedPathChanges,
              "#ff4757",
              "rgba(255, 71, 87, 0.2)"
            )}
          >
            ↺ REVERT
          </button>
        </div>

        {path.length > 1 && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              animation: "slideIn 0.25s ease-out",
            }}
          >
            <div
              style={{
                padding: "10px 16px",
                backgroundColor: "rgba(15, 20, 30, 0.9)",
                color: "#00ff9f",
                border: "1px solid rgba(0, 255, 159, 0.3)",
                borderRadius: "2px",
                fontSize: "0.8rem",
                fontWeight: "600",
                letterSpacing: "0.5px",
                fontFamily: "'Courier New', monospace",
                textTransform: "uppercase",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "10px",
              }}
            >
              <span>
                TOTAL{" "}
                <span style={{ color: "#fff", marginLeft: "8px" }}>
                  {pathLength.feet.toFixed(2)} FT
                </span>
                <span style={{ color: "#6b7280", marginLeft: "6px" }}>
                  ({pathLength.meters.toFixed(2)} M)
                </span>
              </span>
              {hasUnsavedPathChanges && (
                <span
                  style={{
                    fontSize: "0.7rem",
                    padding: "3px 8px",
                    backgroundColor: "rgba(255, 71, 87, 0.2)",
                    border: "1px solid #ff4757",
                    borderRadius: "2px",
                    fontWeight: "700",
                    letterSpacing: "1px",
                    boxShadow: "0 0 10px rgba(255, 71, 87, 0.3)",
                    color: "#ff4757",
                  }}
                >
                  UNSAVED
                </span>
              )}
            </div>
            <div
              style={{
                padding: "10px 16px",
                backgroundColor: "rgba(15, 20, 30, 0.9)",
                color: isMoving ? "#ffaa00" : "#6b7280",
                border: isMoving
                  ? "1px solid rgba(255, 170, 0, 0.3)"
                  : "1px solid rgba(107, 114, 128, 0.3)",
                borderRadius: "2px",
                fontSize: "0.8rem",
                fontWeight: "600",
                letterSpacing: "0.5px",
                fontFamily: "'Courier New', monospace",
                textTransform: "uppercase",
                textAlign: "center",
              }}
            >
              DISTANCE TRAVELED{" "}
              <span style={{ color: "#fff", marginLeft: "8px" }}>
                {distanceTraveled.toFixed(2)} FT
              </span>
            </div>
          </div>
        )}
      </div>

      {/* OBSTACLE CONTROLS */}
      <div
        style={{
          maxHeight: mode === "obstacle" ? "500px" : "0",
          overflow: "hidden",
          transition:
            "max-height 0.25s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.25s ease",
          opacity: mode === "obstacle" ? 1 : 0,
          width: "100%",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "12px",
            marginBottom: "12px",
            width: "100%",
          }}
        >
          {/* <button
            onClick={onImportObstacles}
            style={actionButtonStyle(true, "#00ff9f", "rgba(0, 255, 159, 0.2)")}
          >
            ⬆ IMPORT OBSTACLES
          </button>
          <button
            onClick={onExportObstacles}
            disabled={!hasUnsavedObstacleChanges}
            style={{
              ...actionButtonStyle(
                hasUnsavedObstacleChanges,
                "#00d9ff",
                "rgba(0, 217, 255, 0.2)"
              ),
              position: "relative",
            }}
          >
            ⬇ EXPORT OBSTACLES
            {hasUnsavedObstacleChanges && (
              <span
                style={{
                  position: "absolute",
                  top: "6px",
                  right: "6px",
                  width: "8px",
                  height: "8px",
                  backgroundColor: "#ff4757",
                  borderRadius: "0",
                  border: "1px solid #ff4757",
                  boxShadow: "0 0 10px rgba(255, 71, 87, 0.8)",
                  animation: "pulse 2s ease-in-out infinite",
                }}
              />
            )}
          </button> */}

          <button
            onClick={onClearObstacles}
            disabled={obstacleCount === 0}
            style={actionButtonStyle(
              obstacleCount > 0,
              "#ffaa00",
              "rgba(255, 170, 0, 0.2)"
            )}
          >
            ✕ CLEAR ALL
          </button>
          <button
            onClick={onRevertObstacles}
            disabled={!hasUnsavedObstacleChanges}
            style={actionButtonStyle(
              hasUnsavedObstacleChanges,
              "#ff4757",
              "rgba(255, 71, 87, 0.2)"
            )}
          >
            ↺ REVERT
          </button>
        </div>

        <div
          style={{
            padding: "10px 16px",
            backgroundColor: "rgba(15, 20, 30, 0.9)",
            color: "#ff4757",
            border: "1px solid rgba(255, 71, 87, 0.3)",
            borderRadius: "2px",
            fontSize: "0.8rem",
            fontWeight: "600",
            letterSpacing: "0.5px",
            fontFamily: "'Courier New', monospace",
            textTransform: "uppercase",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "10px",
          }}
        >
          <span>
            OBSTACLES{" "}
            <span style={{ color: "#fff", marginLeft: "6px" }}>
              {obstacleCount}
            </span>
          </span>
          {hasUnsavedObstacleChanges && (
            <span
              style={{
                fontSize: "0.7rem",
                padding: "3px 8px",
                backgroundColor: "rgba(255, 71, 87, 0.2)",
                border: "1px solid #ff4757",
                borderRadius: "2px",
                fontWeight: "700",
                letterSpacing: "1px",
                boxShadow: "0 0 10px rgba(255, 71, 87, 0.3)",
              }}
            >
              UNSAVED
            </span>
          )}
        </div>
      </div>

      {/* COMBINED EXPORT BUTTON */}
      <div
        style={{
          marginTop: "16px",
          width: "100%",
        }}
      >
        <button
          onClick={handleCombinedExport}
          disabled={!hasAnyUnsavedChanges || waitingForPathUpdate}
          style={{
            ...actionButtonStyle(
              hasAnyUnsavedChanges && !waitingForPathUpdate,
              waitingForPathUpdate ? "#ffaa00" : "#9d4edd",
              waitingForPathUpdate ? "rgba(255, 170, 0, 0.2)" : "rgba(157, 78, 221, 0.2)"
            ),
            width: "100%",
            position: "relative",
          }}
        >
          {waitingForPathUpdate ? "WAITING FOR NEW PATH..." : "CALCULATE NEW PATH"}
          {(hasAnyUnsavedChanges || waitingForPathUpdate) && (
            <span
              style={{
                position: "absolute",
                top: "6px",
                right: "6px",
                width: "8px",
                height: "8px",
                backgroundColor: waitingForPathUpdate ? "#ffaa00" : "#ff4757",
                borderRadius: "0",
                border: `1px solid ${waitingForPathUpdate ? "#ffaa00" : "#ff4757"}`,
                boxShadow: `0 0 10px ${waitingForPathUpdate ? "rgba(255, 170, 0, 0.8)" : "rgba(255, 71, 87, 0.8)"}`,
                animation: "pulse 2s ease-in-out infinite",
              }}
            />
          )}
        </button>
      </div>

      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
};

export default PathControls;