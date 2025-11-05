import React, { useState, useRef, useEffect } from "react";
import { useTransformContext } from "react-zoom-pan-pinch";
import { useWebSocket } from "./Websocket";
import GridMap from "./GridMap";

const ClickToPath = ({
  path,
  setPath,
  imgDimensions,
  setImgDimensions,
  image,
  messageBoxRef,
  mode,
  setMode,
  exportObstaclesRef,
  clearObstaclesRef,
  revertObstaclesRef,
  setObstacleCount,
  setHasUnsavedObstacleChanges,
  exportPathRef,
  clearPathRef,
}) => {
  const containerRef = useRef(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [gridBounds, setGridBounds] = useState(null);
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragPosition, setDragPosition] = useState(null);
  
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
  const GRID_CELL_SIZE_FEET = 2;

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
    const distanceMeters = distanceFeet * 0.3048;

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

    const pathLength = calculatePathLength();

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

  // Expose path functions via refs
  useEffect(() => {
    if (exportPathRef) {
      exportPathRef.current = exportPath;
    }
  }, [path, exportPathRef]);

  useEffect(() => {
    if (clearPathRef) {
      clearPathRef.current = clearPath;
    }
  }, [clearPathRef]);

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
    
    const clampedDistance = Math.min(Math.max(0, distanceTraveled), cumulativeDistance);
    
    console.log('getPositionFromDistance - Distance:', distanceTraveled, 'Clamped:', clampedDistance, 'Total:', cumulativeDistance);
    
    for (let i = 0; i < segmentDistances.length; i++) {
      const segment = segmentDistances[i];
      if (clampedDistance >= segment.start && clampedDistance <= segment.end) {
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

  return (
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
  );
};

export default ClickToPath;