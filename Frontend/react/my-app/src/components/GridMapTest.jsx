import React, { useRef, useState, useEffect } from "react";

const GridMapTest = () => {
  const [image, setBackgroundImg] = useState(null);
  const [gridData, setGridData] = useState([]);
  const [obstacles, setObstacles] = useState([]);
  const [imgDimensions, setImgDimensions] = useState({ width: 0, height: 0 });
  const imgRef = useRef(null);

  // Fetch football field image
  useEffect(() => {
    const fetchImage = async () => {
      try {
        console.log("Fetching field image...");
        const response = await fetch("http://localhost:8765/grid/image");
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

        const blob = await response.blob();
        const imageUrl = URL.createObjectURL(blob);
        setBackgroundImg(imageUrl);
      } catch (error) {
        console.error("Failed to fetch map background:", error);
        setBackgroundImg("/imagefrombackend/aerialview.png"); // Fallback image
      }
    };

    fetchImage();
  }, []);

  // Fetch grid JSON
  useEffect(() => {
    const fetchGrid = async () => {
      try {
        console.log("Fetching grid data...");
        const response = await fetch("http://localhost:8765/grid/coordinates/json");
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

        const json = await response.json();
        setGridData(json.data || []);
      } catch (error) {
        console.error("Failed to fetch grid data:", error);
        setGridData([]); // fallback empty grid
      }
    };

    fetchGrid();
  }, []);

  // Fetch obstacles JSON
  useEffect(() => {
    const fetchObstacles = async () => {
      try {
        console.log("Fetching obstacles data...");
        const response = await fetch("http://localhost:8765/grid/obstacles/json");
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

        const json = await response.json();
        setObstacles(json.data || []);
      } catch (error) {
        console.error("Failed to fetch obstacles data:", error);
        setObstacles([]); // fallback empty obstacles
      }
    };

    fetchObstacles();
  }, []);

  // Match obstacles (r,c) to actual grid (x,y)
  const obstaclePoints = gridData.filter((gridPoint) =>
    obstacles.some((obs) => obs.r === gridPoint.r && obs.c === gridPoint.c)
  );

  // When image loads, get its actual rendered pixel dimensions
  const handleImageLoad = () => {
    if (imgRef.current) {
      const { naturalWidth, naturalHeight } = imgRef.current;
      setImgDimensions({ width: naturalWidth, height: naturalHeight });
      console.log("Image dimensions:", { width: naturalWidth, height: naturalHeight });
    }
  };

  return (
    <div
      style={{
        position: "relative",
        display: "inline-block",
        width: "100%",
        maxWidth: "1049px", // keep proportions similar to your example
      }}
    >
      {/* Background image */}
      {image && (
        <img
          ref={imgRef}
          src={image}
          alt="Football Field"
          onLoad={handleImageLoad}
          style={{
            width: "100%",
            height: "auto",
            display: "block",
          }}
        />
      )}

      {/* Overlay grid points */}
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${imgDimensions.width || 1049} ${imgDimensions.height || 488}`}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          pointerEvents: "none", // user can’t interact yet
        }}
      >
        {gridData.map((point, index) => (
          <circle
            key={index}
            cx={point.x}
            cy={point.y}
            r="3"
            fill="red"
            opacity="0.8"
          />
        ))}
        {/* Highlight obstacle points */}
        {obstaclePoints.map((point, index) => (
          <circle
            key={`obstacle-${index}`}
            cx={point.x}
            cy={point.y}
            r="6"
            fill="#009dffff" // bright yellow
            stroke="black"
            strokeWidth="2"
            opacity="0.95"
          />
        ))}
      </svg>
    </div>
  );
};

export default GridMapTest;
