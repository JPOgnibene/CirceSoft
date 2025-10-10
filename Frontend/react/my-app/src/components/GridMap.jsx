import React, { useRef, useState, useEffect } from "react";

const GridMap = ({ points = [] , dimensions, setDimensions}) => {
  console.log("GridMap component rendered")
  const [image, setBackgroundImg] = useState(null);

  const getImageDimensions = (imagePath) => {
    const img = new Image();
    
    img.onload = () => {
      setDimensions({
        height: img.naturalHeight,
        width: img.naturalWidth
      });
      console.log("Image loaded: ", img.naturalHeight, img.naturalWidth)
    };

    console.log("setting image:", dimensions);
    img.src = imagePath;
    console.log("set image:", dimensions)
  };

  useEffect(() => {
    //To test API: curl -o current_image.jpg http://localhost:8765/grid/image
    const fetchImage = async () => {
        console.log("Fetching image...")
        try {
          console.log("Trying to fetch from API...")
          const response = await fetch('http://localhost:8765/grid/image'); //get image
          if (!response.ok) {
            if(response.status === 404) {
              throw new Error('Resource not found (404)')
            }
            throw new Error(`HTTP error: status ${response.status}`);
          }

          
          const blob = await response.blob(); //convert response to a blob
          const imageUrl = URL.createObjectURL(blob); //create url from the blob

          //render the image from the blob in order to get the dimensions
          img = new Image();
          img.onload = () => {
            setDimensions({
            height: img.naturalHeight,
            width: img.naturalWidth
          });
            URL.revokeObjectURL(imageUrl);
          };
          img.src = imageUrl;
        
      
          setBackgroundImg(imageUrl) //update image var with blob

        } catch (error) {
          console.log("Failed to fetch map background from API endpoint:", error)
          console.log("Defaulting to debug football field.")
          
          setBackgroundImg('/imagefrombackend/aerialview.png') //display default background img
          getImageDimensions('/imagefrombackend/aerialview.png')    //grab dimensions of default background img
        }
      }

    console.log("Dimensions: ", dimensions)
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
