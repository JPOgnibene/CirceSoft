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
  onExportObstacles,
  onClearObstacles,
  onRevertObstacles,
}) => {
  return (
    <div style={{ marginBottom: "8px", display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
      {/* MODE TOGGLE */}
      <button
        onClick={() => setMode("path")}
        style={{
          backgroundColor: mode === "path" ? "#4CAF50" : "#ccc",
          color: "white",
          padding: "6px 12px",
          border: "none",
          borderRadius: "6px",
          cursor: "pointer",
        }}
      >
        Path Mode
      </button>
      <button
        onClick={() => setMode("obstacle")}
        style={{
          backgroundColor: mode === "obstacle" ? "#f44336" : "#ccc",
          color: "white",
          padding: "6px 12px",
          border: "none",
          borderRadius: "6px",
          cursor: "pointer",
        }}
      >
        Obstacle Mode
      </button>
      
      {/* PATH CONTROLS */}
      {mode === "path" && (
        <>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={onExportPath}
              disabled={path.length === 0}
              style={{
                backgroundColor: path.length > 0 ? "#2196F3" : "#ccc",
                color: "white",
                padding: "6px 12px",
                border: "none",
                borderRadius: "6px",
                cursor: path.length > 0 ? "pointer" : "not-allowed",
              }}
            >
              Export Path
            </button>
            <button
              onClick={onClearPath}
              disabled={path.length === 0}
              style={{
                backgroundColor: path.length > 0 ? "#FF9800" : "#ccc",
                color: "white",
                padding: "6px 12px",
                border: "none",
                borderRadius: "6px",
                cursor: path.length > 0 ? "pointer" : "not-allowed",
              }}
            >
              Clear Path
            </button>
          </div>
          
          {path.length > 1 && (
            <div style={{ 
              display: "flex",
              gap: "10px",
              flexWrap: "wrap"
            }}>
              <div style={{ 
                padding: "6px 12px", 
                backgroundColor: "#333", 
                color: "white", 
                borderRadius: "6px",
                fontSize: "0.9rem"
              }}>
                Total: {pathLength.feet.toFixed(2)} ft ({pathLength.meters.toFixed(2)} m)
              </div>
              <div style={{ 
                padding: "6px 12px", 
                backgroundColor: isMoving ? "#4CAF50" : "#666", 
                color: "white", 
                borderRadius: "6px",
                fontSize: "0.9rem"
              }}>
                Traveled: {distanceTraveled.toFixed(2)} ft ({(distanceTraveled * 0.3048).toFixed(2)} m)
                {isMoving && " 🚶"}
              </div>
              <div style={{ 
                padding: "6px 12px", 
                backgroundColor: "#555", 
                color: "white", 
                borderRadius: "6px",
                fontSize: "0.9rem"
              }}>
                Progress: {pathLength.feet > 0 ? ((distanceTraveled / pathLength.feet) * 100).toFixed(1) : 0}%
              </div>
            </div>
          )}
        </>
      )}
      
      {/* OBSTACLE CONTROLS */}
      {mode === "obstacle" && (
        <>
          <button
            onClick={onExportObstacles}
            disabled={!hasUnsavedObstacleChanges}
            style={{
              backgroundColor: hasUnsavedObstacleChanges ? "#2196F3" : "#ccc",
              color: "white",
              padding: "6px 12px",
              border: "none",
              borderRadius: "6px",
              cursor: hasUnsavedObstacleChanges ? "pointer" : "not-allowed",
              fontWeight: hasUnsavedObstacleChanges ? "bold" : "normal"
            }}
          >
            Export Obstacles {hasUnsavedObstacleChanges && "●"}
          </button>
          <button
            onClick={onClearObstacles}
            disabled={obstacleCount === 0}
            style={{
              backgroundColor: obstacleCount > 0 ? "#FF9800" : "#ccc",
              color: "white",
              padding: "6px 12px",
              border: "none",
              borderRadius: "6px",
              cursor: obstacleCount > 0 ? "pointer" : "not-allowed",
            }}
          >
            Clear All
          </button>
          <button
            onClick={onRevertObstacles}
            disabled={!hasUnsavedObstacleChanges}
            style={{
              backgroundColor: hasUnsavedObstacleChanges ? "#f44336" : "#ccc",
              color: "white",
              padding: "6px 12px",
              border: "none",
              borderRadius: "6px",
              cursor: hasUnsavedObstacleChanges ? "pointer" : "not-allowed",
            }}
          >
            Revert Changes
          </button>
          <div style={{ 
            marginLeft: "auto",
            padding: "6px 12px", 
            backgroundColor: "#333", 
            color: "white", 
            borderRadius: "6px",
            fontSize: "0.9rem"
          }}>
            Obstacles: {obstacleCount}
            {hasUnsavedObstacleChanges && " (unsaved)"}
          </div>
        </>
      )}
    </div>
  );
};

export default PathControls;