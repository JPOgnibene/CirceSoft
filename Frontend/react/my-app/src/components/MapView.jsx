  import React, { useState, useEffect } from "react";
  import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
  import ClickToPath from "./ClickToPath";

  // Set these to your original image's width and height

  export default function MapView({ sliderValue, path, setPath, messageBoxRef }) {
    const [imgDimensions, setImgDimensions] = useState({ width: 0, height: 0 });
    const [image, setBackgroundImg] = useState(null);
    
    const IMAGE_ENDPOINT = "http://localhost:8765/grid/image";

    useEffect(() => {
      const fetchImage = async () => {
        try {
          const response = await fetch(IMAGE_ENDPOINT);
          if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
          const blob = await response.blob();
          const imageUrl = URL.createObjectURL(blob);
          setBackgroundImg(imageUrl);

          const img = new Image();
            img.onload = () => {
            setImgDimensions({ width: img.naturalWidth, height: img.naturalHeight });
          };
          img.src = imageUrl;

        } catch (error) {
          console.error("Failed to fetch map background:", error);
          setBackgroundImg("/imagefrombackend/aerialview.png");
        }
      };
      fetchImage();
    }, []);


    if (!imgDimensions.width || !imgDimensions.height) {
      return <div>Loading map...</div>;
    }

    const fieldWidth = imgDimensions.width;
    const fieldHeight = imgDimensions.height;

    return (
      <div
        style={{
          width: `${fieldWidth}px`,
          height: `${fieldHeight}px`,
          overflow: "hidden",
          border: "none",
          margin: 0,
          padding: 0,
          background: "#000",
          position: "relative"
        }}
      >
        <TransformWrapper
          initialScale={1}
          minScale={0.5}
          maxScale={5}
          wheel={{ step: 0.1 }}
          doubleClick={{ disabled: true }}
        >
          {({ state }) => (
            <TransformComponent>
              <div
                style={{
                  width: `${fieldWidth}px`,
                  height: `${fieldHeight}px`,
                  position: "relative"
                }}
              >
                <ClickToPath 
                  pathProgress={sliderValue} 
                  path={path} setPath={setPath} 
                  imgDimensions={imgDimensions}
                  setImgDimensions={setImgDimensions}
                  image={image}
                  messageBoxRef={messageBoxRef}
                />
              </div>
            </TransformComponent>
          )}
        </TransformWrapper>
      </div>
    );
  }
