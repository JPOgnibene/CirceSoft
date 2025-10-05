import React, { useState, useRef, useEffect } from "react";
import {useTransformContext} from "react-zoom-pan-pinch";
//(deprecated) import Graph from "./Graph";
import GridMap from "./GridMap";

const ClickToPath = ({ xMin = 0, xMax = 10, yMin = 0, yMax = 10, pathProgress, path, setPath, FIELD_HEIGHT, FIELD_WIDTH}) => {

  const [pixels, setPixels] = useState([]); //store pixel points of dots on screen
  const containerRef = useRef(null);
  const [size, setSize] = useState({ width: 800, height: 600 });

  // grab zoom state
  const transformContext = useTransformContext();
  const scale = transformContext?.state?.scale ?? 1;
  const positionX = transformContext?.state?.positionX ?? 1;
  const positionY = transformContext?.state?.positionY ?? 1;
  console.log(path?.length)
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

  // Click to add a dot
  const handleClick = (e) => {
    const rect = containerRef.current.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const py = e.clientY - rect.top;

    // Map pixel to graph coordinates
    const xCoord = xMin + (px / rect.width) * (xMax - xMin);
    const yCoord = yMax - (py / rect.height) * (yMax - yMin);

    console.log("Click raw:", e.clientX, e.clientY);
    console.log("Converted coords:", xCoord, yCoord);
    setPath((p) => {
      console.log("Previous path:", p);
      return [...p, { x: xCoord, y: yCoord }];
    });
  };

  // Map graph coordinates to pixels
  const graphToPixel = (dot) => {
    const { width, height } = size;
    const px = ((dot.x - xMin) / (xMax - xMin)) * width;
    const py = ((yMax - dot.y) / (yMax - yMin)) * height;
    console.log("Pixels are", px, "and", py)
    return { px, py };
  };

  // Get smooth interpolated position along the path
  const getPosition = () => {
    if (path.length === 0) return { x: 0, y: 0, index: 0 };
    if (path.length === 1) return { ...path[0], index: 0 };
    console.log("Slider value is ", pathProgress)

    const totalSegments = path.length - 1;
    const pos = (pathProgress / 100) * totalSegments;
    const index = Math.floor(pos);
    const t = pos - index;

    const start = path[index];
    const end = path[Math.min(index + 1, path.length - 1)];

    return {
      x: start.x + (end.x - start.x) * t,
      y: start.y + (end.y - start.y) * t,
      index,
    };
  };

  const currentDot = getPosition();
  const { px, py } = graphToPixel(currentDot);

  // Split path into completed and remaining
  let completed = [];
  let remaining = [];
  if (path.length > 1) {
    completed = path.slice(0, currentDot.index + 1);
    completed.push({ x: currentDot.x, y: currentDot.y });

    remaining = [{ x: currentDot.x, y: currentDot.y }, ...path.slice(currentDot.index + 1)];
  }

  return (
    <>
    <div
      style={{
        position: "relative",
        width: `${FIELD_WIDTH}px`,
        height: `${FIELD_HEIGHT}px`
      }}
    >
      <div
        style={{
            width: "100%",
            height: "95%"
            
        }}
        onClick={handleClick}
        ref={containerRef}
      >
        <GridMap points={path} />

        {/* Draw completed and remaining paths */}
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
          {completed.length > 1 && (
            <polyline
              points={completed.map((dot) => {
                const p = graphToPixel(dot);
                return `${p.px},${p.py}`;
              }).join(" ")}
              fill="none"
              stroke="green"
              strokeWidth="3"
            />
          )}

          {remaining.length > 1 && (
            <polyline
              points={remaining.map((dot) => {
                const p = graphToPixel(dot);
                return `${p.px},${p.py}`;
              }).join(" ")}
              fill="none"
              stroke="blue"
              strokeWidth="2"
            />
          )}
        </svg>

        {/* Dots you click */}
        {path.map((dot, index) => {
          console.log(`Dot #${index}:`, dot);
          const { px, py } = graphToPixel(dot);
          return (
            <div
              key={index}
              style={{
                position: "absolute",
                left: px - 5,
                top: py - 5,
                width: 10,
                height: 10,
                borderRadius: "50%",
                backgroundColor: "green",
                pointerEvents: "none",
              }}
            />
          );
        })}

        {/* Image moving along path */}
        <img
          src="/contents/images/circe.png"
          alt="moving"
          style={{
            position: "absolute",
            left: px - (16 * scale),
            top: py - (16 * scale),
            width: 32 * scale,
            height: 32 * scale,
            pointerEvents: "none",
          }}
        />
      </div>
      </div>
  </>
  );
  
};

export default ClickToPath;
