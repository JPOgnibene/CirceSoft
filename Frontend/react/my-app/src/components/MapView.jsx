import React from "react";
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import ClickToPath from "./ClickToPath";

// Set these to your original image's width and height
const FIELD_WIDTH = 1049;
const FIELD_HEIGHT = 488;

export default function MapView({ sliderValue, path, setPath }) {
  return (
    <div
      style={{
        width: `${FIELD_WIDTH}px`,
        height: `${FIELD_HEIGHT}px`,
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
                width: `${FIELD_WIDTH}px`,
                height: `${FIELD_HEIGHT}px`,
                position: "relative"
              }}
            >
              {/*<img
                src="/imagefrombackend/aerialview.png"
                alt="Aerial Map"
                width={FIELD_WIDTH}
                height={FIELD_HEIGHT}
                style={{
                  width: `${FIELD_WIDTH}px`,
                  height: `${FIELD_HEIGHT}px`,
                  display: "block",
                  objectFit: "cover"
                }}
              /> */}
              <ClickToPath pathProgress={sliderValue} path={path} setPath={setPath} />
            </div>
          </TransformComponent>
        )}
      </TransformWrapper>
    </div>
  );
}
