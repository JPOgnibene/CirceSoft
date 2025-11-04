import React, { useState, useRef, useEffect } from "react";
import { useTransformContext } from "react-zoom-pan-pinch";
import { useWebSocket } from "./Websocket"; // Import the WebSocket hook
import GridMap from "./GridMap";

const ClickToPath = ({
  path,
  setPath,
  imgDimensions,
  setImgDimensions,
  image,
  messageBoxRef,
}) => {
  const [mode, setMode] = useState("path");
  const containerRef = useRef(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [gridBounds, setGridBounds] = useState(null);
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragPosition, setDragPosition] = useState(null);
  
  // Obstacle refs and state - MOVED INSIDE THE COMPONENT
  const exportObstaclesRef = useRef(null);
  const clearObstaclesRef = useRef(null);
  const revertObstaclesRef = useRef(null);
  const [obstacleCount, setObstacleCount] = useState(0);
  const [hasUnsavedObstacleChanges, setHasUnsavedObstacleChanges] = useState(false);
  
  // Get WebSocket data - store in local state to ensure re-renders
  const ws = useWebSocket();
  const [distanceTraveled, setDistanceTraveled] = useState(0);
  const [isMoving, setIsMoving] = useState(false);
  
  // Update local state when WebSocket values change
  useEffect(() => {
    if (ws) {
      setDistanceTraveled(ws.distanceTraveled || 0);
      setIsMoving(ws.isMoving || false);
      console.log('ClickToPath - Distance updated:', ws.distanceTraveled, 'Moving:', ws.isMoving);
    }
  }, [ws?.distanceTraveled, ws?.isMoving]);
  
  const transformContext = useTransformContext();
  const scale = transformContext?.state?.scale ?? 1;

  const PATH_ENDPOINT = "http://localhost:8765/grid/path";
  const WAYPOINT_ENDPOINT = "http://localhost:8765/waypoints";
  
  // CONFIGURATION: Real-world size of one grid cell
  const GRID_CELL_SIZE_FEET = 2; // Change this to match your actual grid cell size

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const resize = () => {
      const rect = el.getBoundingClientRect();
      setSize({ width: rect.width, height: rect.height });
    };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  // Calculate Euclidean distance between two points in grid coordinates
  const calculateDistance = (point1, point2) => {
    const dx = point2.x - point1.x;
    const dy = point2.y - point1.y;
    return Math.sqrt(dx * dx + dy * dy);
  };

  // Calculate total path length in grid units and real-world units
  const calculatePathLength = () => {
    if (path.length < 2) {
      return { gridUnits: 0, feet: 0, meters: 0 };
    }

    let totalDistance = 0;
    for (let i = 0; i < path.length - 1; i++) {
      totalDistance += calculateDistance(path[i], path[i + 1]);
    }

    const distanceFeet = totalDistance * GRID_CELL_SIZE_FEET;
    const distanceMeters = distanceFeet * 0.3048; // Convert feet to meters

    return {
      gridUnits: totalDistance,
      feet: distanceFeet,
      meters: distanceMeters
    };
  };

  // Export path to server
  const exportPath = async () => {
    if (path.length === 0) {
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('warning', 'No path to export');
      }
      return;
    }

    // Calculate path length
    const pathLength = calculatePathLength();

    // Create path data with labels
    const pathData = path.map((point, index) => {
      if (index === 0) {
        return { r: point.y, c: point.x, label: "START" };
      } else if (index === path.length - 1) {
        return { r: point.y, c: point.x, label: "END" };
      }
      return { r: point.y, c: point.x, label: "WAYPOINT" };
    });

    try {
      const response = await fetch(WAYPOINT_ENDPOINT, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(pathData),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      const result = await response.json();
      console.log("Path exported:", result);
      console.log("Path length:", pathLength);
      
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage(
          'success', 
          `Path exported: ${path.length} waypoints, ` +
          `Distance: ${pathLength.feet.toFixed(2)} ft (${pathLength.meters.toFixed(2)} m)`
        );
      }
    } catch (error) {
      console.error("Failed to export path:", error);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('error', 'Failed to export path');
      }
    }
  };

  // Clear current path
  const clearPath = () => {
    setPath([]);
    if (messageBoxRef?.current) {
      messageBoxRef.current.addMessage('info', 'Path cleared');
    }
  };

  // Delete a specific point
  const deletePoint = (index) => {
    const deletedPoint = path[index];
    setPath(path.filter((_, i) => i !== index));
    if (messageBoxRef?.current) {
      messageBoxRef.current.addMessage('info', `Waypoint removed at (${deletedPoint.x}, ${deletedPoint.y})`);
    }
  };

  // Handle mouse down on path point (start drag)
  const handlePointMouseDown = (e, index) => {
    if (mode !== "path") return;
    e.stopPropagation();
    setDraggedIndex(index);
    setIsDragging(true);
  };

  // Handle mouse move (dragging)
  const handleMouseMove = (e) => {
    if (!isDragging || draggedIndex === null || mode !== "path" || !gridBounds) return;

    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    
    const px = (clickX / rect.width) * imgDimensions.width;
    const py = (clickY / rect.height) * imgDimensions.height;

    if (
      px < gridBounds.minPX || 
      px > gridBounds.maxPX || 
      (imgDimensions.height-py) < gridBounds.minPY || 
      (imgDimensions.height-py) > gridBounds.maxPY
    ){
      return;
    }
    
    const xCoord = ((px - gridBounds.minPX) / (gridBounds.maxPX - gridBounds.minPX)) * gridBounds.maxCols;
    const pyFlipped = imgDimensions.height - py;
    const yCoord = ((pyFlipped - gridBounds.minPY) / (gridBounds.maxPY - gridBounds.minPY)) * gridBounds.maxRows;
    
    // Update the path in real-time while dragging
    const newPath = [...path];
    newPath[draggedIndex] = {
      x: Math.round(xCoord),
      y: Math.round(yCoord)
    };
    setPath(newPath);
  };

  // Handle mouse up (end drag)
  const handleMouseUp = () => {
    if (isDragging && draggedIndex !== null) {
      const movedPoint = path[draggedIndex];
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('success', `Waypoint moved to (${movedPoint.x}, ${movedPoint.y})`);
      }
    }
    setIsDragging(false);
    
    // Delay clearing draggedIndex to prevent click handler from firing
    setTimeout(() => {
      setDraggedIndex(null);
    }, 0);
    
    setDragPosition(null);
  };

  useEffect(() => {
    if (isDragging) {
      const moveHandler = (e) => handleMouseMove(e);
      const upHandler = () => handleMouseUp();
      
      window.addEventListener('mousemove', moveHandler);
      window.addEventListener('mouseup', upHandler);
      return () => {
        window.removeEventListener('mousemove', moveHandler);
        window.removeEventListener('mouseup', upHandler);
      };
    }
  }, [isDragging, draggedIndex, gridBounds, imgDimensions, dragPosition]);

  const handleClick = (e) => {
    if (mode !== "path" || isDragging) return;
    
    // Don't add a point if we just finished dragging
    if (draggedIndex !== null) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    
    const px = (clickX / rect.width) * imgDimensions.width;
    const py = (clickY / rect.height) * imgDimensions.height;

    if (
      px < gridBounds.minPX || 
      px > gridBounds.maxPX || 
      (imgDimensions.height-py) < gridBounds.minPY || 
      (imgDimensions.height-py) > gridBounds.maxPY
    ){
      console.log(`Click at ${px.toFixed(1)}, ${py.toFixed(1)} is outside grid bounds`);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('error', 'Click is outside grid bounds');
      }
      return;
    }
    
    const xCoord = ((px - gridBounds.minPX) / (gridBounds.maxPX - gridBounds.minPX)) * gridBounds.maxCols;
    const pyFlipped = imgDimensions.height - py;
    const yCoord = ((pyFlipped - gridBounds.minPY) / (gridBounds.maxPY - gridBounds.minPY)) * gridBounds.maxRows;
    
    console.log("Path set at (", xCoord, ", ", yCoord, ")");
    if (messageBoxRef?.current) {
      messageBoxRef.current.addMessage('success', `Waypoint added at (${Math.round(xCoord)}, ${Math.round(yCoord)})`);
    }
    setPath((p) => [...p, { 
      x: Math.round(xCoord), 
      y: Math.round(yCoord)
    }]);
  };

  const graphToPixel = (dot) => {
    const { width, height } = size;
    
    if (!gridBounds) {
      return { px: width / 2, py: height / 2 };
    }
    
    const imgX = gridBounds.minPX + (dot.x / gridBounds.maxCols) * (gridBounds.maxPX - gridBounds.minPX);
    const imgY = gridBounds.minPY + (dot.y / gridBounds.maxRows) * (gridBounds.maxPY - gridBounds.minPY);
    
    const px = (imgX / imgDimensions.width) * width;
    const py = ((imgDimensions.height - imgY) / imgDimensions.height) * height;
    return { px, py };
  };

  // Calculate position based on distance traveled (in feet)
  const getPositionFromDistance = () => {
    if (path.length === 0) return { x: 0, y: 0, index: 0 };
    if (path.length === 1) return { ...path[0], index: 0 };
    
    // Calculate cumulative distances along the path
    const segmentDistances = [];
    let cumulativeDistance = 0;
    
    for (let i = 0; i < path.length - 1; i++) {
      const segmentLength = calculateDistance(path[i], path[i + 1]) * GRID_CELL_SIZE_FEET;
      segmentDistances.push({
        start: cumulativeDistance,
        end: cumulativeDistance + segmentLength,
        length: segmentLength,
        startPoint: path[i],
        endPoint: path[i + 1],
        index: i
      });
      cumulativeDistance += segmentLength;
    }
    
    // Clamp distance traveled to the total path length
    const clampedDistance = Math.min(Math.max(0, distanceTraveled), cumulativeDistance);
    
    console.log('getPositionFromDistance - Distance:', distanceTraveled, 'Clamped:', clampedDistance, 'Total:', cumulativeDistance);
    
    // Find which segment the bot is currently on
    for (let i = 0; i < segmentDistances.length; i++) {
      const segment = segmentDistances[i];
      if (clampedDistance >= segment.start && clampedDistance <= segment.end) {
        // Calculate position within this segment
        const distanceInSegment = clampedDistance - segment.start;
        const t = segment.length > 0 ? distanceInSegment / segment.length : 0;
        
        const position = {
          x: segment.startPoint.x + (segment.endPoint.x - segment.startPoint.x) * t,
          y: segment.startPoint.y + (segment.endPoint.y - segment.startPoint.y) * t,
          index: segment.index,
        };
        
        console.log('Position calculated:', position, 'Segment:', i, 't:', t);
        return position;
      }
    }
    
    // If we've traveled the full distance, return the end point
    console.log('At end of path');
    return { ...path[path.length - 1], index: path.length - 1 };
  };

  const currentDot = getPositionFromDistance();
  const { px, py } = graphToPixel(currentDot);

  let completed = [];
  let remaining = [];
  if (path.length > 1) {
    completed = path.slice(0, currentDot.index + 1);
    completed.push({ x: currentDot.x, y: currentDot.y });
    remaining = [{ x: currentDot.x, y: currentDot.y }, ...path.slice(currentDot.index + 1)];
  }

  // Calculate current path length for display
  const pathLength = calculatePathLength();

  return (
    <>
      {/* === MODE TOGGLE === */}
      <div style={{ marginBottom: "8px", display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
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
                onClick={exportPath}
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
                onClick={clearPath}
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
              onClick={() => exportObstaclesRef.current?.()}
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
              onClick={() => clearObstaclesRef.current?.()}
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
              onClick={() => revertObstaclesRef.current?.()}
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

      <div
        style={{
          position: "relative",
          width: `${imgDimensions.width}px`,
          height: `${imgDimensions.height}px`,
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
          }}
          onClick={handleClick}
          ref={containerRef}
        >
          <GridMap 
            points={path} 
            mode={mode}
            gridBounds={gridBounds}
            imgDimensions={imgDimensions}
            setGridBounds={setGridBounds} 
            setImgDimensions={setImgDimensions} 
            image={image}
            messageBoxRef={messageBoxRef}
            onExportObstacles={exportObstaclesRef}
            onClearObstacles={clearObstaclesRef}
            onRevertObstacles={revertObstaclesRef}
            onObstacleCountChange={setObstacleCount}
            onUnsavedChangesChange={setHasUnsavedObstacleChanges}
          />
          
          {/* === PATH DRAWING === */}
          <svg
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              pointerEvents: "none",
            }}
          >
            {/* When editing (path mode) or dragging, show the full path in white */}
            {(mode === "path" || isDragging) && path.length > 1 && (
              <polyline
                points={path
                  .map((dot) => {
                    const p = graphToPixel(dot);
                    return `${p.px},${p.py}`;
                  })
                  .join(" ")}
                fill="none"
                stroke="white"
                strokeWidth="2"
              />
            )}
            
            {/* When not in path mode and not dragging, show progress animation */}
            {mode !== "path" && !isDragging && (
              <>
                {completed.length > 1 && (
                  <polyline
                    points={completed
                      .map((dot) => {
                        const p = graphToPixel(dot);
                        return `${p.px},${p.py}`;
                      })
                      .join(" ")}
                    fill="none"
                    stroke="green"
                    strokeWidth="3"
                  />
                )}
                {remaining.length > 1 && (
                  <polyline
                    points={remaining
                      .map((dot) => {
                        const p = graphToPixel(dot);
                        return `${p.px},${p.py}`;
                      })
                      .join(" ")}
                    fill="none"
                    stroke="white"
                    strokeWidth="2"
                  />
                )}
              </>
            )}
          </svg>
          
          {/* Draw clicked path dots */}
          {path.map((dot, index) => {
            const { px, py } = graphToPixel(dot);
            return (
              <div
                key={index}
                style={{
                  position: "absolute",
                  left: px - 8,
                  top: py - 8,
                  pointerEvents: mode === "path" ? "auto" : "none",
                }}
              >
                {/* Main waypoint circle */}
                <div
                  onMouseDown={(e) => handlePointMouseDown(e, index)}
                  style={{
                    width: 14,
                    height: 14,
                    borderRadius: "50%",
                    backgroundColor: draggedIndex === index ? "yellow" : "white",
                    border: "2px solid black",
                    cursor: mode === "path" ? "move" : "default",
                    position: "relative",
                  }}
                />
                
                {/* Delete button (X) */}
                {mode === "path" && !isDragging && (
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      deletePoint(index);
                    }}
                    style={{
                      position: "absolute",
                      top: -8,
                      right: -8,
                      width: 13,
                      height: 12,
                      borderRadius: "50%",
                      backgroundColor: "red",
                      color: "white",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "10px",
                      fontWeight: "bold",
                      cursor: "pointer",
                      border: "1px solid black",
                      userSelect: "none",
                    }}
                    title="Delete waypoint"
                  >
                    ×
                  </div>
                )}
              </div>
            );
          })}
          
          {/* Moving icon */}
          <img
            src="/contents/images/circe.png"
            alt="moving"
            style={{
              position: "absolute",
              left: px - 16 * scale,
              top: py - 16 * scale,
              width: 32 * scale,
              height: 32 * scale,
              pointerEvents: "none",
              filter: isMoving ? "none" : "grayscale(0.5) opacity(0.7)",
            }}
          />
        </div>
      </div>
    </>
  );
};

export default ClickToPath;