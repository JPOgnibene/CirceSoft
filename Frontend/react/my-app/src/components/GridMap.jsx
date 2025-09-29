import React from "react";

const GridMap = ({ points = [] }) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        backgroundImage: "url('/contents/images/footballfield.jpg')",
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      {/* SVG lines overlay */}
      <svg
        width="100%"
        height="100%"
        style={{ position: "absolute", top: 0, left: 0 }}
      >
        {points.length > 1 &&
          points.slice(1).map((p, i) => {
            const prev = points[i];
            return (
              <line
                key={i}
                x1={prev.x}
                y1={prev.y}
                x2={p.x}
                y2={p.y}
                stroke="blue"
                strokeWidth="2"
              />
            );
          })}
      </svg>

      {/* Dots overlay */}
      {points.map((p, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: p.x - 5,
            top: p.y - 5,
            width: 10,
            height: 10,
            borderRadius: "50%",
            backgroundColor: "green",
          }}
        />
      ))}
    </div>
  );
};

export default GridMap;
