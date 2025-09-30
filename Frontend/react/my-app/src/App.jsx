import React, { useRef } from 'react';
import './App.css';
import MessageWindow from './components/MessageWindow';
import WebsocketTester from "./components/WebsocketTester";
import MapView from "./components/MapView";
import Slider from "./components/Slider";

import {
  WebsocketStatusIcon,
  ImportPathIcon,
  PlayButtonIcon,
  PauseButtonIcon,
  WaypointIcon,
  TargetIcon,
  OnPathIcon,
} from "./components/Icons";
import { useReducer } from 'react';
import ClickToPath from './components/ClickToPath';

function App() {
  const messageBoxRef = useRef();
  
  return (
    <div>
      <header className="header">
        <div className="icons">
          <div className="icon">
            <WebsocketStatusIcon messageBoxRef={messageBoxRef }/>
          </div>
          <div className="clickIcon">
            <ImportPathIcon messageBoxRef={messageBoxRef} />
          </div>
          <div className="clickIcon">
            <PlayButtonIcon messageBoxRef={messageBoxRef} />
          </div>
          <div className="clickIcon">
            <PauseButtonIcon messageBoxRef={messageBoxRef} />
          </div>
          <div className="clickIcon">
            <WaypointIcon messageBoxRef={messageBoxRef} />
          </div>
          <div className="clickIcon">
            <TargetIcon messageBoxRef={messageBoxRef} />
          </div>
        </div>
        <div className="progress-container">
          <Slider />
        </div>
        <div className="spacer"></div>
        <label className="switch">
          <input type="checkbox" id="websocket_on" />
        </label>
        <label className="switch">
          <input type="checkbox" id="offpath" />
        </label>
        <div className="icon">
          {/*FIXME: Add functionality to replace ClickToPath slider*/}
          <OnPathIcon messageBoxRef={messageBoxRef} />
        </div>
      </header>

      {/* Main Content Area */}
      <div className="content">
        <MessageWindow ref={ messageBoxRef } />
        <WebsocketTester />
        <div className="map_feed">
         {/*<ClickToPath /> */}
        <MapView />
        </div>
      </div>
    </div>
  );
}

export default App;