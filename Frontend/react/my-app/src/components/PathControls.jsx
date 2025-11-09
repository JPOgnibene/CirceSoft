import React from "react";

const PathControls = ({
  mode,
  setMode,
  path,
  pathLength,
  distanceTraveled,
  isMoving,
  obstacleCount,
  hasUnsavedObstacleChanges,
  onExportPath,
  onClearPath,
  onImportObstacles,
  onExportObstacles,
  onClearObstacles,
  onRevertObstacles,
}) => {
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
    // Clicking same button again -> deselects mode
    if (mode === selectedMode) {
      setMode(null);
    } else {
      setMode(selectedMode);
    }
  };

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
          width: "100%", // ✅ fills full width like others
        }}
      >
        <button
          onClick={() => toggleMode("path")}
          style={modeButtonStyle(mode === "path", "#00ff9f")}
        >
          ◉ PATH MODE
        </button>
        <button
          onClick={() => toggleMode("obstacle")}
          style={modeButtonStyle(mode === "obstacle", "#ff4757")}
        >
          ▲ OBSTACLE MODE
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
          width: "100%", // ✅ match button width
        }}
      >
        {/* Button grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "12px",
            marginBottom: "12px",
            width: "100%",
          }}
        >
          <button
            onClick={onExportPath}
            disabled={path.length === 0}
            style={actionButtonStyle(
              path.length > 0,
              "#00d9ff",
              "rgba(0, 217, 255, 0.2)"
            )}
          >
            ⬇ EXPORT PATH
          </button>
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
                textAlign: "center",
              }}
            >
              TOTAL{" "}
              <span style={{ color: "#fff", marginLeft: "8px" }}>
                {pathLength.feet.toFixed(2)} FT
              </span>
              <span style={{ color: "#6b7280", marginLeft: "6px" }}>
                ({pathLength.meters.toFixed(2)} M)
              </span>
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
          width: "100%", // ✅ match other buttons
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
          <button
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
          </button>

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
