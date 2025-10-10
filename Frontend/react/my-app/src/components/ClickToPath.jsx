import React, { useState, useRef, useEffect } from "react";
import { useTransformContext } from "react-zoom-pan-pinch";
import GridMap from "./GridMap";

const ClickToPath = ({
  xMin = 0,
  xMax = 10,
  yMin = 0,
  yMax = 10,
  pathProgress,
  path,
  setPath,
  FIELD_HEIGHT,
  FIELD_WIDTH,
}) => {
  const [pixels, setPixels] = useState([]);
  const [mode, setMode] = useState("path"); // NEW: current mode
  const containerRef = useRef(null);
  const [size, setSize] = useState({ width: 800, height: 600 });

  //watch dimensions for changes from GridMap
  useEffect(() => {
    console.log("Dimensions state updated:", dimensions);
  }, [dimensions]);

  // grab zoom state
  const transformContext = useTransformContext();
  const scale = transformContext?.state?.scale ?? 1;

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

  // Only handle clicks when in "path" mode
  const handleClick = (e) => {
    if (mode !== "path") return; // prevent path editing in obstacle mode

    const rect = containerRef.current.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const py = e.clientY - rect.top;

    const xCoord = xMin + (px / rect.width) * (xMax - xMin);
    const yCoord = yMax - (py / rect.height) * (yMax - yMin);

    setPath((p) => [...p, { x: xCoord, y: yCoord }]);
  };

  // Map graph coords to pixels
  const graphToPixel = (dot) => {
    const { width, height } = dimensions;
    const px = ((dot.x - xMin) / (xMax - xMin)) * width;
    const py = ((yMax - dot.y) / (yMax - yMin)) * height;
    return { px, py };
  };

  // Handle slider progress for robot motion
  const getPosition = () => {
    if (path.length === 0) return { x: 0, y: 0, index: 0 };
    if (path.length === 1) return { ...path[0], index: 0 };

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

  // Split path
  let completed = [];
  let remaining = [];
  if (path.length > 1) {
    completed = path.slice(0, currentDot.index + 1);
    completed.push({ x: currentDot.x, y: currentDot.y });
    remaining = [{ x: currentDot.x, y: currentDot.y }, ...path.slice(currentDot.index + 1)];
  }

  return (
    <>
      {/* === MODE TOGGLE === */}
      <div style={{ marginBottom: "8px" }}>
        <button
          onClick={() => setMode("path")}
          style={{
            marginRight: "10px",
            backgroundColor: mode === "path" ? "#4CAF50" : "#ccc",
            color: "white",
            padding: "6px 12px",
            border: "none",
            borderRadius: "6px",
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
          }}
        >
          Obstacle Mode
        </button>
      </div>

      <div
        style={{
          position: "relative",
          width: `${FIELD_WIDTH}px`,
          height: `${FIELD_HEIGHT}px`,
        }}
      >
        <div
          style={{
            width: "100%",
            height: "95%",
          }}
          onClick={handleClick}
          ref={containerRef}
        >
          {/* Pass mode down to GridMap */}
          <GridMap points={path} mode={mode} />

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
          </svg>

          {/* Draw clicked path dots */}
          {path.map((dot, index) => {
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
                  backgroundColor: "white",
                  pointerEvents: "none",
                }}
              />
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
            }}
          />
        </div>
      </div>
    </>
  );
};

export default ClickToPath;
