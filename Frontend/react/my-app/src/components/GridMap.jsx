import React, { useRef, useState, useEffect } from "react";

const GridMap = ({ points = [] }) => {
  console.log("GridMap component rendered")
  const [image, setBackgroundImg] = useState(null);

  useEffect(() => {
    //To test API: curl -o current_image.jpg http://localhost:8765/grid/image
    const fetchImage = async () => {
        console.log("Fetching image...")
        try {
          console.log("Trying to fetch from API...")
          const response = await fetch('http://localhost:8765/grid/image'); //get image
          const blob = await response.blob(); //convert response to a blob
          const imageUrl = URL.createObjectURL(blob); //create url from the blob
          setBackgroundImg(imageUrl) //update image var with blob
        } catch (error) {
          console.log("Failed to fetch map background from API endpoint:", error)
          console.log("Defaulting to debug football field.")
          
          setBackgroundImg('/imagefrombackend/aerialview.png')
        }
      }

    fetchImage();
  }, []);

  console.log("Current image value:", image);
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        backgroundImage: `url(${image})`,
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
