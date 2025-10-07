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
    };
    fetchImage();
  }, []);

  // --- Fetch grid coordinates ---
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

  // --- Fetch obstacles ---
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

  // --- Get image dimensions ---
  const handleImageLoad = () => {
    if (imgRef.current) {
      const { naturalWidth, naturalHeight } = imgRef.current;
      setImgDimensions({ width: naturalWidth, height: naturalHeight });
    }
  };

  // --- Determine if cell is an obstacle ---
  const isObstacle = (r, c) => obstacles.some((obs) => obs.r === r && obs.c === c);

  // --- Handle user click ---
  const handlePointClick = async (point) => {
    // 🚫 Prevent editing unless in obstacle mode
    if (mode !== "obstacle") return;

    const { r, c } = point;
    let updatedObstacles;

    if (isObstacle(r, c)) {
      updatedObstacles = obstacles.filter((obs) => !(obs.r === r && obs.c === c));
      console.log(`Removing obstacle at (r=${r}, c=${c})`);
    } else {
      updatedObstacles = [...obstacles, { r, c }];
      console.log(`Adding obstacle at (r=${r}, c=${c})`);
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
    } catch (error) {
      console.error("Error updating obstacles:", error);
    }
  };

  // --- Match obstacles to grid points ---
  const obstaclePoints = gridData.filter((gridPoint) =>
    obstacles.some((obs) => obs.r === gridPoint.r && obs.c === gridPoint.c)
  );

  // --- Render ---
  return (
    <div
      style={{
        position: "relative",
        display: "inline-block",
        width: "100%",
        maxWidth: "1049px",
      }}
    >
    </div>
  );
};

export default GridMap;
