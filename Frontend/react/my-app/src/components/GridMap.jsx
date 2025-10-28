import React, { useRef, useState, useEffect } from "react";

const GridMap = ({ 
  mode, 
  gridBounds, 
  imgDimensions, 
  image, 
  setGridBounds, 
  messageBoxRef,
}) => {
  const [gridData, setGridData] = useState([]);
  const [obstacles, setObstacles] = useState([]);
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
          y: point.y,
          r: point.row,
          c: point.col
        }));
        setGridData(mappedData || []);
      } catch (error) {
        console.error("Failed to fetch grid data:", error);
      }
    };
    fetchGrid();
  }, []);

  useEffect(() => {
    const fetchObstacles = async () => {
      try {
        const response = await fetch(OBSTACLE_JSON_ENDPOINT);
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
        const json = await response.json();
        // Handle both {data: [...]} or direct array format
        const obstaclesData = json.data || json || [];
        setObstacles(obstaclesData);
      } catch (error) {
        console.error("Failed to fetch obstacle data:", error);
      }
    };
    fetchObstacles();
  }, []);

  const isObstacle = (r, c) => obstacles.some((obs) => obs.r === r && obs.c === c);

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

    // Check each grid cell
    for (let r = 0; r < maxR; r++) {
      for (let c = 0; c < maxC; c++) {
        // Check the 4 corners of this cell
        const corners = [
          { r, c, pos: getGridPointCoords(r, c) },
          { r, c: c + 1, pos: getGridPointCoords(r, c + 1) },
          { r: r + 1, c: c + 1, pos: getGridPointCoords(r + 1, c + 1) },
          { r: r + 1, c, pos: getGridPointCoords(r + 1, c) }
        ];

        // Filter corners that are obstacles and have valid coordinates
        const obstacleCorners = corners.filter(
          corner => corner.pos && isObstacle(corner.r, corner.c)
        );

        if (obstacleCorners.length >= 3) {
          // Create polygon from obstacle corners
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
    if (mode !== "obstacle") return;
    if (gridData.length === 0) return;

    const svg = svgRef.current;
    if (!svg) return;

    // Get click position relative to SVG
    const rect = svg.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Convert to SVG coordinates (accounting for viewBox)
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
      handlePointClick(closestPoint);
    }
  };

  // Drag to add/remove obstacles
  // useEffect(() => {
  //   const handleMouseMove = (e) => {
  //     if (!isDraggingObstacle) return;
  //     if (gridData.length === 0) return;
  //     const svg = svgRef.current;
  //     if (!svg) return;
  //     const rect = svg.getBoundingClientRect();
  //     const moveX = e.clientX - rect.left;
  //     const moveY = e.clientY - rect.top;
  //     const svgX = (moveX / rect.width) * imgDimensions.width;
  //     const svgY = (moveY / rect.height) * imgDimensions.height;
  //     let closestPoint = null;
  //     let minDistance = Infinity; 
  //     gridData.forEach((point) => {
  //       const dx = point.x - svgX;
  //       const dy = point.y - svgY;
  //       const distance = Math.sqrt(dx * dx + dy * dy);
  //       if (distance < minDistance) {
  //         minDistance = distance;
  //         closestPoint = point;
  //       }
  //     });
  //     if (closestPoint) {
  //       if (!lastObstaclePoint || lastObstaclePoint.r !== closestPoint.r || lastObstaclePoint.c !== closestPoint.c) {
  //         handlePointClick(closestPoint);
  //         setLastObstaclePoint(closestPoint);
  //       }
  //     }
  //   };

  //   const handleMouseUp = () => {
  //     setIsDraggingObstacle(false);
  //     setLastObstaclePoint(null);
  //   };
  //   window.addEventListener("mousemove", handleMouseMove);
  //   window.addEventListener("mouseup", handleMouseUp);  
  //   return () => {
  //     window.removeEventListener("mousemove", handleMouseMove);
  //     window.removeEventListener("mouseup", handleMouseUp);
  //   };
  // }, [isDraggingObstacle, lastObstaclePoint, gridData]);

  const handlePointClick = async (point) => {
    if (mode !== "obstacle") return;

    const { r, c } = point;
    let updatedObstacles;
    let added = true;

    if (isObstacle(r, c)) {
      updatedObstacles = obstacles.filter((obs) => !(obs.r === r && obs.c === c));
      console.log(`Removing obstacle at (r=${r}, c=${c})`);
      added = false;
    } else {
      updatedObstacles = [...obstacles, { r, c }];
      console.log(`Adding obstacle at (r=${r}, c=${c})`);
      added = true;
    }

    setObstacles(updatedObstacles);

    try {
      const response = await fetch(OBSTACLE_ENDPOINT, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedObstacles),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(`Failed: ${result.error || response.statusText}`);
      console.log("Obstacles updated:", result);
      
      if (messageBoxRef?.current) {
        if (added) messageBoxRef.current.addMessage('success', `Obstacle added at (${r}, ${c})`);
        else messageBoxRef.current.addMessage('info', `Obstacle removed at (${r}, ${c})`);
      }
    } catch (error) {
      console.error("Error updating obstacles:", error);
    }
  };

  return (
    <div
      style={{
        position: "relative",
        display: "inline-block",
        width: "100%",
        maxWidth: "1049px",
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
          cursor: mode === "obstacle" ? "pointer" : "default",
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