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
  importObstaclesRef,
  exportObstaclesRef,
  clearObstaclesRef,
  revertObstaclesRef,
  setObstacleCount,
  setHasUnsavedObstacleChanges,
  exportPathRef,
  clearPathRef,
  revertPathRef,
  setHasUnsavedPathChanges,
  hasUnsavedPathChanges
}) => {
  const containerRef = useRef(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [gridBounds, setGridBounds] = useState(null);
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragPosition, setDragPosition] = useState(null);

  const [savedPath, setSavedPath] = useState([]);
  const [unsavedPath, setUnsavedPath] = useState([]);
  
  const ws = useWebSocket();
  const [distanceTraveled, setDistanceTraveled] = useState(0);
  const [isMoving, setIsMoving] = useState(false);

  const [animatedDistance, setAnimatedDistance] = useState(0);
  const animationFrameRef = useRef(null);
  const lastUpdateTimeRef = useRef(Date.now());
  
  // CONFIGURATION
  const MAX_PATH_LENGTH_FEET = 300;
  const CELL_WIDTH_FT = 7.5;
  const CELL_HEIGHT_FT = 5.16;
  
  useEffect(() => {
    if (ws) {
      setDistanceTraveled(ws.distanceTraveled || 0);
      setIsMoving(ws.isMoving || false);
      console.log('ClickToPath - Distance updated:', ws.distanceTraveled, 'Moving:', ws.isMoving);
    }
  }, [ws?.distanceTraveled, ws?.isMoving]);

  useEffect(() => {
    const animate = () => {
      const now = Date.now();
      const deltaTime = (now - lastUpdateTimeRef.current) / 1000;
      lastUpdateTimeRef.current = now;
      
      setAnimatedDistance(prev => {
        const diff = distanceTraveled - prev;
        
        if (Math.abs(diff) < 0.01) {
          return distanceTraveled;
        }
        
        const interpolationSpeed = Math.min(5, Math.abs(diff) * 2);
        const step = diff * interpolationSpeed * deltaTime;
        
        return prev + step;
      });
      
      animationFrameRef.current = requestAnimationFrame(animate);
    };
    
    animationFrameRef.current = requestAnimationFrame(animate);
    
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [distanceTraveled]);

  const transformContext = useTransformContext();
  const scale = transformContext?.state?.scale ?? 1;
  const PATH_ENDPOINT = "http://localhost:8765/grid/path";
  const WAYPOINT_ENDPOINT = "http://localhost:8765/waypoints";
  
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

  const calculateDistance = (point1, point2) => {
    const dx = point2.x - point1.x;
    const dy = point2.y - point1.y;
    const dx_feet = dx * CELL_WIDTH_FT;
    const dy_feet = dy * CELL_HEIGHT_FT;
    return Math.sqrt(dx_feet * dx_feet + dy_feet * dy_feet);
  };

  const calculatePathLength = (pathArray = path) => {
    if (pathArray.length < 2) {
      return { gridUnits: 0, feet: 0, meters: 0 };
    }
    let totalDistance = 0;
    for (let i = 0; i < pathArray.length - 1; i++) {
      totalDistance += calculateDistance(pathArray[i], pathArray[i + 1]);
    }
    const distanceFeet = totalDistance;
    const distanceMeters = distanceFeet * 0.3048;
    return {
      gridUnits: totalDistance,
      feet: distanceFeet,
      meters: distanceMeters
    };
  };

  // NEW: Check if adding a new point would exceed the max length
  const wouldExceedMaxLength = (newPoint) => {
    if (path.length === 0) return false;
    
    const testPath = [...path, newPoint];
    const testLength = calculatePathLength(testPath);
    
    return testLength.feet > MAX_PATH_LENGTH_FEET;
  };

  // NEW: Check if moving a point would exceed the max length
  const wouldMovingExceedMaxLength = (index, newPoint) => {
    const testPath = [...path];
    testPath[index] = newPoint;
    const testLength = calculatePathLength(testPath);
    
    return testLength.feet > MAX_PATH_LENGTH_FEET;
  };

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
      
      setSavedPath(path);
      setHasUnsavedPathChanges(false);
      
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

  const revertPath = () => {
    setPath(savedPath);
    setUnsavedPath(savedPath);
    setHasUnsavedPathChanges(false);
    if (messageBoxRef?.current) {
      messageBoxRef.current.addMessage('info', 'Path changes reverted to last saved state');
    }
  };

  const clearPath = () => {
    setPath([]);
    setUnsavedPath([]);
    setHasUnsavedPathChanges(true);
    if (messageBoxRef?.current) {
      messageBoxRef.current.addMessage('info', 'Path cleared - not saved');
    }
  };

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

  useEffect(() => {
    setUnsavedPath(path);
  }, [path]);

  useEffect(() => {
    if (revertPathRef) {
      revertPathRef.current = revertPath;
    }
  }, [savedPath, unsavedPath, hasUnsavedPathChanges, revertPathRef]);

  useEffect(() => {
    if (JSON.stringify(path) !== JSON.stringify(savedPath)) {
      setHasUnsavedPathChanges(true);
    } else {
      setHasUnsavedPathChanges(false);
    }
  }, [path, savedPath]);

  useEffect(() => {
    if (setHasUnsavedPathChanges) {
      setHasUnsavedPathChanges(hasUnsavedPathChanges);
    }
  }, [hasUnsavedPathChanges, setHasUnsavedPathChanges]);

  const deletePoint = (index) => {
    const deletedPoint = path[index];
    setPath(path.filter((_, i) => i !== index));
    if (messageBoxRef?.current) {
      messageBoxRef.current.addMessage('info', `Waypoint removed at (${deletedPoint.x}, ${deletedPoint.y})`);
    }
  };

  const handlePointMouseDown = (e, index) => {
    if (mode !== "path") return;
    e.stopPropagation();
    setDraggedIndex(index);
    setIsDragging(true);
  };

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
    
    const newPoint = {
      x: Math.round(xCoord),
      y: Math.round(yCoord)
    };

    // NEW: Check if moving this point would exceed max length
    if (wouldMovingExceedMaxLength(draggedIndex, newPoint)) {
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('warning', `Cannot move: Path would exceed ${MAX_PATH_LENGTH_FEET} ft limit`);
      }
      return;
    }
    
    const newPath = [...path];
    newPath[draggedIndex] = newPoint;
    setPath(newPath);
  };

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
    
    const newPoint = { 
      x: Math.round(xCoord), 
      y: Math.round(yCoord)
    };

    // NEW: Check if adding this point would exceed max length
    if (wouldExceedMaxLength(newPoint)) {
      const currentLength = calculatePathLength();
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage(
          'error', 
          `Cannot add waypoint: Path would exceed ${MAX_PATH_LENGTH_FEET} ft limit. Current: ${currentLength.feet.toFixed(2)} ft`
        );
      }
      console.warn(`⛔ Path length limit exceeded: Would be > ${MAX_PATH_LENGTH_FEET} ft`);
      return;
    }

    console.log("Path set at (", xCoord, ", ", yCoord, ")");
    if (messageBoxRef?.current) {
      messageBoxRef.current.addMessage('success', `Waypoint added at (${Math.round(xCoord)}, ${Math.round(yCoord)})`);
    }
    setPath((p) => [...p, newPoint]);
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

  const getPositionFromDistance = () => {
    if (path.length === 0) return { x: 0, y: 0, index: 0 };
    if (path.length === 1) return { ...path[0], index: 0 };
    
    const segmentDistances = [];
    let cumulativeDistance = 0;
    
    for (let i = 0; i < path.length - 1; i++) {
      const segmentLength = calculateDistance(path[i], path[i + 1]);
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
    
    const clampedDistance = Math.min(Math.max(0, animatedDistance), cumulativeDistance);
    
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
        width: "100%",
        paddingBottom: `${(imgDimensions.height / imgDimensions.width) * 100}%`,
        height: 0,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
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
          onImportObstacles={importObstaclesRef}
          onExportObstacles={exportObstaclesRef}
          onClearObstacles={clearObstaclesRef}
          onRevertObstacles={revertObstaclesRef}
          onObstacleCountChange={setObstacleCount}
          onUnsavedChangesChange={setHasUnsavedObstacleChanges}
        />
        
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
            filter: isMoving 
              ? "drop-shadow(0 0 8px rgba(0, 255, 157, 1)) drop-shadow(0 0 16px rgba(0, 255, 159, 0.4))" 
              : "grayscale(0.5) drop-shadow(0 0 6px rgba(255, 81, 0, 1))",
            transition: "filter 0.3s ease-in-out",
          }}
        />
      </div>
    </div>
  );
};

export default ClickToPath;