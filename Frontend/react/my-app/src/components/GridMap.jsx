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

    </div>
  );
};

export default GridMap;
