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
  const imgRef = useRef(null);
  const svgRef = useRef(null);
  
  const GRID_ENDPOINT = "http://localhost:8765/grid/coordinates/json";
  const IMAGE_ENDPOINT = "http://localhost:8765/grid/image";
  const OBSTACLE_ENDPOINT = "http://localhost:8765/grid/obstacles";
  const OBSTACLE_JSON_ENDPOINT = "http://localhost:8765/grid/obstacles/json";

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
        setGridData(json.data || []);
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
        setObstacles(json.data || []);
      } catch (error) {
        console.error("Failed to fetch obstacle data:", error);
      }
    };
    fetchObstacles();
  }, []);

  const isObstacle = (r, c) => obstacles.some((obs) => obs.r === r && obs.c === c);

  // NEW: Handle clicks on the SVG container
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