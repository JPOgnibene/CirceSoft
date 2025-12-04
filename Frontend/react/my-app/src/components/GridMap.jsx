import React, { useRef, useState, useEffect } from "react";

const GridMap = ({ 
  mode, 
  gridBounds, 
  imgDimensions, 
  image, 
  setGridBounds, 
  messageBoxRef,
  onImportObstacles,
  onExportObstacles,
  onClearObstacles,
  onRevertObstacles,
  onObstacleCountChange,
  onUnsavedChangesChange,
  revertPathRef,
  onHasUnsavedPathChanges,
  onPathPointClick, // NEW: Callback for when a valid path point is clicked
}) => {
  const [gridData, setGridData] = useState([]);
  const [obstacles, setObstacles] = useState([]); // Last saved/imported state
  const [unsavedObstacles, setUnsavedObstacles] = useState([]); // Current working state
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isDraggingObstacle, setIsDraggingObstacle] = useState(false);
  const [lastObstaclePoint, setLastObstaclePoint] = useState(null);
  const imgRef = useRef(null);
  const svgRef = useRef(null);
  
  const GRID_ENDPOINT = "http://localhost:8765/grid/coordinates";
  const IMAGE_ENDPOINT = "http://localhost:8765/grid/image";
  const OBSTACLE_ENDPOINT = "http://localhost:8765/grid/obstacles";
  const OBSTACLE_JSON_ENDPOINT = "http://localhost:8765/grid/obstacles";

  useEffect(() => {
    if (gridData.length > 0) {
      const bounds = {
        minPX: Math.min(...gridData.map(p => p.x)),
        maxPX: Math.max(...gridData.map(p => p.x)),
        minPY: Math.min(...gridData.map(p => p.y)),
        maxPY: Math.max(...gridData.map(p => p.y)),
        maxRows: Math.max(...gridData.map(p => p.r)),
        maxCols: Math.max(...gridData.map(p => p.c))
      };
      setGridBounds(bounds);
    }
  }, [gridData]);

  // Fetch grid data on startup
  useEffect(() => {
    const fetchGrid = async () => {
      try {
        const response = await fetch(GRID_ENDPOINT);
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
        const json = await response.json();
        const mappedData = (json.data || json || []).map(point => ({
          row: point.row,
          col: point.col,
          x: point.x,
          y: imgDimensions.height - point.y,
          r: point.row,
          c: point.col
        }));
        setGridData(mappedData || []);
      } catch (error) {
        console.error("Failed to fetch grid data:", error);
      }
    };
    fetchGrid();
  }, [imgDimensions.height]);

  const isObstacle = (r, c) => {
    const found = unsavedObstacles.some((obs) => {
      const obsR = obs.r !== undefined ? obs.r : obs.row;
      const obsC = obs.c !== undefined ? obs.c : obs.col;
      return obsR === r && obsC === c;
    });
    return found;
  };

  // NEW: Validate if a point can be clicked for path mode
  const validatePathClick = (r, c) => {
    if (isObstacle(r, c)) {
      return {
        valid: false,
        reason: 'obstacle',
        message: 'Cannot click on obstacle point'
      };
    }
    
    return { valid: true };
  };

  // Get the pixel coordinates for a grid point
  const getGridPointCoords = (r, c) => {
    const point = gridData.find(p => p.r === r && p.c === c);
    return point ? { x: point.x, y: point.y } : null;
  };

  // Generate filled polygons for obstacle visualization
  const generateObstaclePolygons = () => {
    if (gridData.length === 0) return [];
    
    const polygons = [];
    const maxR = Math.max(...gridData.map(p => p.r));
    const maxC = Math.max(...gridData.map(p => p.c));

    for (let r = 0; r < maxR; r++) {
      for (let c = 0; c < maxC; c++) {
        const corners = [
          { r, c, pos: getGridPointCoords(r, c) },
          { r, c: c + 1, pos: getGridPointCoords(r, c + 1) },
          { r: r + 1, c: c + 1, pos: getGridPointCoords(r + 1, c + 1) },
          { r: r + 1, c, pos: getGridPointCoords(r + 1, c) }
        ];

        const obstacleCorners = corners.filter(
          corner => corner.pos && isObstacle(corner.r, corner.c)
        );

        if (obstacleCorners.length >= 3) {
          const points = obstacleCorners
            .map(corner => `${corner.pos.x},${corner.pos.y}`)
            .join(' ');
          
          polygons.push({
            key: `poly-${r}-${c}`,
            points,
            cornerCount: obstacleCorners.length
          });
        }
      }
    }

    return polygons;
  };

  const obstaclePolygons = generateObstaclePolygons();

  // Handle clicks on the SVG container
  const handleSvgClick = (e) => {
    if (gridData.length === 0) return;

    const svg = svgRef.current;
    if (!svg) return;

    // Get click position relative to SVG
    const rect = svg.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Convert to SVG coordinates
    const svgX = (clickX / rect.width) * imgDimensions.width;
    const svgY = (clickY / rect.height) * imgDimensions.height;

    // Find the closest grid point
    let closestPoint = null;
    let minDistance = Infinity;

    gridData.forEach((point) => {
      const dx = point.x - svgX;
      const dy = point.y - svgY;
      const distance = Math.sqrt(dx * dx + dy * dy);
      
      if (distance < minDistance) {
        minDistance = distance;
        closestPoint = point;
      }
    });

    if (closestPoint) {
      handlePointClick(closestPoint, e);
    }
  };

  // Handle point clicks - with validation for path mode
  const handlePointClick = (point, e) => {
    const { r, c } = point;
    
    // NEW: Validate path mode clicks
    if (mode === 'path') {
      const validation = validatePathClick(r, c);
      if (!validation.valid) {
        // Prevent the event from bubbling to ClickToPath
        if (e) {
          e.stopPropagation();
        }
        
        if (messageBoxRef?.current) {
          messageBoxRef.current.addMessage('error', validation.message);
        }
        console.warn(`Invalid click at (${r}, ${c}): ${validation.message}`);
        return;
      }
      
      
      // Call the parent's callback if provided
      if (onPathPointClick) {
        onPathPointClick(point);
      }
      return;
    }
    
    // Obstacle mode logic
    if (mode !== "obstacle") return;

    let updatedObstacles;
    let added = true;

    if (isObstacle(r, c)) {
      updatedObstacles = unsavedObstacles.filter((obs) => !(obs.r === r && obs.c === c));
      console.log(`Removing obstacle at (r=${r}, c=${c}) - NOT SAVED YET`);
      added = false;
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('info', `Obstacle removed at (${r}, ${c}) - not saved`);
      }
    } else {
      updatedObstacles = [...unsavedObstacles, { r, c }];
      console.log(`Adding obstacle at (r=${r}, c=${c}) - NOT SAVED YET`);
      added = true;
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('info', `Obstacle added at (${r}, ${c}) - not saved`);
      }
    }

    setUnsavedObstacles(updatedObstacles);
    setHasUnsavedChanges(true);
  };

  // Import obstacles from server
  const importObstacles = async () => {
    console.log("=== IMPORT OBSTACLES STARTED ===");
    console.log("Fetching from:", OBSTACLE_JSON_ENDPOINT);
    try {
      const response = await fetch(OBSTACLE_JSON_ENDPOINT);
      console.log("Response status:", response.status);
      
      if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
      
      const json = await response.json();
      console.log("Raw JSON response:", json);
      
      let obstaclesData = json.data || json || [];
      
      obstaclesData = obstaclesData.map(obs => ({
        r: obs.r !== undefined ? obs.r : obs.row,
        c: obs.c !== undefined ? obs.c : obs.col
      }));
      
      console.log("Normalized obstacles data:", obstaclesData);
      console.log("Number of obstacles:", obstaclesData.length);
      
      setObstacles(obstaclesData);
      setUnsavedObstacles(obstaclesData);
      setHasUnsavedChanges(false);
      
      console.log("=== IMPORT OBSTACLES COMPLETED ===");
      
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage(
          'success', 
          `Obstacles imported: ${obstaclesData.length} total obstacles`
        );
      }
    } catch (error) {
      console.error("=== IMPORT OBSTACLES FAILED ===");
      console.error("Error:", error);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('error', `Failed to import obstacles: ${error.message}`);
      }
    }
  };

  // Export obstacles to server
  const exportObstacles = async () => {
    try {
      const response = await fetch(OBSTACLE_ENDPOINT, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(unsavedObstacles),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      const result = await response.json();
      console.log("Obstacles exported:", result);
      
      setObstacles(unsavedObstacles);
      setHasUnsavedChanges(false);
      
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage(
          'success', 
          `Obstacles exported: ${unsavedObstacles.length} total obstacles`
        );
      }
    } catch (error) {
      console.error("Failed to export obstacles:", error);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('error', 'Failed to export obstacles');
      }
    }
  };

  // Clear all obstacles
  const clearObstacles = () => {
    setUnsavedObstacles([]);
    setHasUnsavedChanges(true);
    if (messageBoxRef?.current) {
      messageBoxRef.current.addMessage('info', 'All obstacles cleared - not saved');
    }
  };

  // Revert to last saved state
  const revertObstacles = () => {
    setUnsavedObstacles(obstacles);
    setHasUnsavedChanges(false);
    if (messageBoxRef?.current) {
      messageBoxRef.current.addMessage('info', 'Changes reverted to last saved state');
    }
  };

  // Wire up the callback refs
  useEffect(() => {
    if (onImportObstacles) {
      onImportObstacles.current = importObstacles;
    }
  }, [onImportObstacles]);

  useEffect(() => {
    if (onExportObstacles) {
      onExportObstacles.current = exportObstacles;
    }
  }, [unsavedObstacles, hasUnsavedChanges]);

  useEffect(() => {
    if (onClearObstacles) {
      onClearObstacles.current = clearObstacles;
    }
  }, [unsavedObstacles]);

  useEffect(() => {
    if (onRevertObstacles) {
      onRevertObstacles.current = revertObstacles;
    }
  }, [obstacles, unsavedObstacles, hasUnsavedChanges]);

  // Update obstacle count
  useEffect(() => {
    if (onObstacleCountChange) {
      onObstacleCountChange(unsavedObstacles.length);
    }
  }, [unsavedObstacles.length, onObstacleCountChange]);

  // Update unsaved changes status
  useEffect(() => {
    if (onUnsavedChangesChange) {
      onUnsavedChangesChange(hasUnsavedChanges);
    }
  }, [hasUnsavedChanges, onUnsavedChangesChange]);

  return (
    <div
      style={{
        position: "relative",
        display: "inline-block",
        width: "100%",
      }}
    >
      {image && (
        <img
          ref={imgRef}
          src={image}
          alt="Football Field"
          style={{
            width: "100%",
            height: "auto",
            display: "block",
          }}
        />
      )}
      
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox={`0 0 ${imgDimensions.width || 1049} ${imgDimensions.height || 488}`}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          cursor: mode === "obstacle" ? "pointer" : "crosshair",
          pointerEvents: "auto", // Allow SVG to receive events
        }}
        onClick={handleSvgClick}
      >
        {/* Draw grid lines */}
        {gridData.length > 0 && (() => {
          const rows = [...new Set(gridData.map(p => p.r))].sort((a, b) => a - b);
          const cols = [...new Set(gridData.map(p => p.c))].sort((a, b) => a - b);
          
          return (
            <g>
              {/* Horizontal lines */}
              {rows.map(r => {
                const rowPoints = gridData.filter(p => p.r === r).sort((a, b) => a.c - b.c);
                if (rowPoints.length < 2) return null;
                const x1 = rowPoints[0].x;
                const x2 = rowPoints[rowPoints.length - 1].x;
                const y = rowPoints[0].y;
                return (
                  <line
                    key={`h-${r}`}
                    x1={x1}
                    y1={y}
                    x2={x2}
                    y2={y}
                    stroke="red"
                    strokeWidth="3"
                    opacity="0.4"
                    style={{ pointerEvents: "none" }}
                  />
                );
              })}
              
              {/* Vertical lines */}
              {cols.map(c => {
                const colPoints = gridData.filter(p => p.c === c).sort((a, b) => a.r - b.r);
                if (colPoints.length < 2) return null;
                const x = colPoints[0].x;
                const y1 = colPoints[0].y;
                const y2 = colPoints[colPoints.length - 1].y;
                return (
                  <line
                    key={`v-${c}`}
                    x1={x}
                    y1={y1}
                    x2={x}
                    y2={y2}
                    stroke="red"
                    strokeWidth="3"
                    opacity="0.4"
                    style={{ pointerEvents: "none" }}
                  />
                );
              })}
            </g>
          );
        })()}
        
        {/* Draw filled obstacle regions */}
        {obstaclePolygons.map(poly => (
          <polygon
            key={poly.key}
            points={poly.points}
            fill="#00a6ff"
            opacity="0.7"
            stroke="none"
            style={{ pointerEvents: "none" }}
          />
        ))}
        
        {/* Draw obstacle circles */}
        {gridData.map((point, index) => {
          const obstacle = isObstacle(point.r, point.c);
          if (!obstacle) return null;
          return (
            <circle
              key={index}
              cx={point.x}
              cy={point.y}
              r={6}
              fill="#00a6ffff"
              stroke="black"
              strokeWidth={2}
              opacity={0.95}
              style={{
                pointerEvents: "none",
              }}
            />
          );
        })}
      </svg>
    </div>
  );
};

export default GridMap;