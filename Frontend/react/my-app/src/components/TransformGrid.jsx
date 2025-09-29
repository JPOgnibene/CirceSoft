import React from "react";
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import ClickToPath from "./ClickToPath";

export default function MapView() {
  return (
    <div style={{ width: "800px", height: "600px", border: "1px solid black" }}>
      <TransformWrapper
        initialScale={1}
        minScale={0.5}
        maxScale={5}
        wheel={{ step: 0.1 }}
        doubleClick = {{ disabled: true }}
      >
        {({ state }) => (
        <TransformComponent>
          {/*<img src="/imagefrombackend/aerialview.png" alt="Aerial Map" width="800" />*/}
          <ClickToPath />
        </TransformComponent>
        )}
      </TransformWrapper>
    </div>
  );
}
