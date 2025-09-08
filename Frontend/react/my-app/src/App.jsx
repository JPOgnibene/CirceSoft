import "./App.css"; // or your old style.css

function App() {
  return (
    <div>
      <header className="header">
        <div className="icons">
          <div className="icon">
            <img
              id="toggleImage"
              src="/contents/images/websocket_connection_off.png"
              alt="Websocket Status"
            />
          </div>
          <div className="clickIcon">
            <img src="/contents/images/importpathicon.png" alt="Import path" />
          </div>
          <div className="clickIcon">
            <img src="/contents/images/playbutton.png" alt="Start/resume path" />
          </div>
          <div className="clickIcon">
            <img src="/contents/images/pausebutton.png" alt="Stop path" />
          </div>
          <div className="clickIcon">
            <img src="/contents/images/waypointicon.png" alt="Add a waypoint" />
          </div>
          <div className="clickIcon">
            <img src="/contents/images/imagestargeticon.png" alt="Select target location" />
          </div>
        </div>

        <div className="progress-container">
          <input type="range" min="0" max="100" defaultValue="0" id="progressSlider" className="slider" />
          <div className="progress-bar">
            <div id="progressFill" className="progress-fill"></div>
            <span id="progressValue">0%</span>
          </div>
        </div>

        <div className="spacer"></div>

        <label className="switch">
          <input type="checkbox" id="websocket_on" />
        </label>

        <label className="switch">
          <input type="checkbox" id="offpath" />
        </label>

        <div className="icon">
          <img id="togglePathDeviation" src="/contents/images/onpath.png" alt="Bot is on path" />
        </div>
      </header>

      {/* Main Content Area */}
      <div className="content">
        <div className="message_window">
          <h1>Message Box</h1>
          <div id="messages" className="messages"></div>
        </div>

        <div className="map_feed">
          <h1>Map Feed</h1>
        </div>
      </div>
    </div>
  );
}

export default App;
