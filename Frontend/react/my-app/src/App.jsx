import React, { useRef, useState } from 'react';
import './App.css';
import MessageWindow from './components/MessageWindow';
import MapView from "./components/MapView";
import Progress from "./components/Progress";
import StartStopButton from './components/StartStop';
import IsMovingStatus from "./components/BotMoving";
import PathControls from './components/PathControls';
import ResetCurrentValues from './components/ResetCurrentValues';
import CurrentValuesDisplay from './components/CurrentValuesDisplay';
import InfoDropdown from './components/InfoDropdown';
import { WebSocketProvider, WebsocketStatusIcon, useWebSocket } from "./components/Websocket";

function AppContent({ messageBoxRef }) {
  const [isBotRunning, setIsBotRunning] = useState(false);
  const [completionProgress, setValue] = useState(0);
  const [path, setPath] = useState([]);
  const [mode, setMode] = useState("path");
  const [obstacleCount, setObstacleCount] = useState(0);
  const [hasUnsavedObstacleChanges, setHasUnsavedObstacleChanges] = useState(false);
  const [hasUnsavedPathChanges, setHasUnsavedPathChanges] = useState(false);
  const [isPathComplete, setIsPathComplete] = useState(false);
  
  // Refs for obstacle functions
  const importObstaclesRef = useRef(null);
  const exportObstaclesRef = useRef(null);
  const clearObstaclesRef = useRef(null);
  const revertObstaclesRef = useRef(null);
  const revertPathRef = useRef(null);
  
  // Refs for path functions
  const exportPathRef = useRef(null);
  const clearPathRef = useRef(null);
  
  // Get WebSocket data
  const ws = useWebSocket();
  const distanceTraveled = ws?.distanceTraveled || 0;
  const isMoving = ws?.isMoving || false;
  
  // Calculate path length (same logic as in ClickToPath)
  const GRID_CELL_SIZE_FEET = 2;
  const calculateDistance = (point1, point2) => {
    const dx = point2.x - point1.x;
    const dy = point2.y - point1.y;
    const dx_feet = dx * 7.5; // CELL_WIDTH_FT
    const dy_feet = dy * 5.16; // CELL_HEIGHT_FT
    console.log("NEW CALCULATIONS: ", dx_feet, dy_feet);
    console.log("REUTURN VAL: ", Math.sqrt(dx_feet * dx_feet + dy_feet * dy_feet));
    return Math.sqrt(dx_feet * dx_feet + dy_feet * dy_feet);
  };
  
  const calculatePathLength = () => {
    if (path.length < 2) {
      return { gridUnits: 0, feet: 0, meters: 0 };
    }
    let totalDistance = 0;
    for (let i = 0; i < path.length - 1; i++) {
      totalDistance += calculateDistance(path[i], path[i + 1]);
    }
    const distanceFeet = totalDistance;
    const distanceMeters = distanceFeet * 0.3048;
    return { gridUnits: totalDistance, feet: distanceFeet, meters: distanceMeters };
  };
  
  const pathLength = calculatePathLength();

  React.useEffect(() => {
  const progressPercentage = pathLength.feet > 0 
    ? Math.min((distanceTraveled / pathLength.feet) * 100, 100)
    : 0;
  
  if (progressPercentage >= 100 && isBotRunning) {
    setIsPathComplete(true);
    setIsBotRunning(false);
  }
}, [distanceTraveled, pathLength.feet, isBotRunning]);

    // Handler for imported path
  const handlePathImported = (importedPath) => {
    setPath(importedPath);
    // Notify ClickToPath to set this as saved state
    if (importPathRef.current) {
      importPathRef.current(importedPath);
    }
  };
  
  // Handlers for PathControls
  const handleExportPath = () => {
    if (exportPathRef.current) {
      exportPathRef.current();
    }
  };
  
  const handleClearPath = () => {
    if (clearPathRef.current) {
      clearPathRef.current();
    }
  };
  
  // ADD THIS HANDLER
  const handleImportObstacles = () => {
    if (importObstaclesRef.current) {
      importObstaclesRef.current();
    }
  };
  
  const handleExportObstacles = () => {
    if (exportObstaclesRef.current) {
      exportObstaclesRef.current();
    }
  };
  
  const handleClearObstacles = () => {
    if (clearObstaclesRef.current) {
      clearObstaclesRef.current();
    }
  };
  
  const handleRevertObstacles = () => {
    if (revertObstaclesRef.current) {
      revertObstaclesRef.current();
    }
  };

  const handleRevertPath = () => {
    if (revertPathRef.current) {
      revertPathRef.current();
    }
  };
  
  return (
    <div className="app-root">
      <header className="header">
        <div className="icons">
          <div className="icon">
            <WebsocketStatusIcon messageBoxRef={messageBoxRef} />
          </div>
          <div className="icon">
            <InfoDropdown />
          </div>
        </div>
        
        <div className="header-title-container">
          <h1 className="header-title">CirceSoft</h1>
        </div>
        
        <div className="spacer"></div>
        <img className="logo2" src="/contents/images/devcomlogo2.png" alt="Devcom" />
        <img className="logo1" src="/contents/images/devcomlogo.png" alt="Devcom" />
      </header>
      
      {/* Main Content Area */}
      <div className="content">
        <div className="message_window">
          <PathControls
            mode={mode}
            setMode={setMode}
            path={path}
            setPath={setPath}
            pathLength={pathLength}
            distanceTraveled={distanceTraveled}
            isMoving={isMoving}
            obstacleCount={obstacleCount}
            hasUnsavedObstacleChanges={hasUnsavedObstacleChanges}
            onExportPath={handleExportPath}
            onClearPath={handleClearPath}
            onImportObstacles={handleImportObstacles}
            onExportObstacles={handleExportObstacles}
            onClearObstacles={handleClearObstacles}
            onRevertObstacles={handleRevertObstacles}
            onRevertPath={handleRevertPath}
            hasUnsavedPathChanges={hasUnsavedPathChanges}
            onPathImported={handlePathImported}
            messageBoxRef={messageBoxRef}
          />
          <MessageWindow ref={messageBoxRef} />
        </div>
        <div className="map_feed">
          <MapView 
            path={path} 
            setPath={setPath} 
            messageBoxRef={messageBoxRef}
            mode={mode}
            setMode={setMode}
            importObstaclesRef={importObstaclesRef}
            exportObstaclesRef={exportObstaclesRef}
            clearObstaclesRef={clearObstaclesRef}
            revertObstaclesRef={revertObstaclesRef}
            setObstacleCount={setObstacleCount}
            setHasUnsavedObstacleChanges={setHasUnsavedObstacleChanges}
            exportPathRef={exportPathRef}
            clearPathRef={clearPathRef}
            revertPathRef={revertPathRef}
            setHasUnsavedPathChanges={setHasUnsavedPathChanges} 
            hasUnsavedPathChanges={hasUnsavedPathChanges}
          />

          <div className="bottom-progress">
            <Progress distanceTraveled={distanceTraveled} pathLength={pathLength} />
          </div>
          
          <div className="bottom-controls-container">
            <div className="start-stop-section">
              <div style={{ flex: 1, transition: "flex 0.3s ease" }}>
                <StartStopButton 
                  messageBoxRef={messageBoxRef} 
                  onRunningChange={setIsBotRunning}
                  isPathComplete={isPathComplete}
                  setIsPathComplete={setIsPathComplete}
                />
              </div>
              <IsMovingStatus 
                messageBoxRef={messageBoxRef} 
                isVisible={isBotRunning}
              />
            </div>
            <div className="reset-button-section">
              <ResetCurrentValues 
                messageBoxRef={messageBoxRef}
                onReset={() => setIsPathComplete(false)}
              />
            </div>
          </div>
          <div>
            <CurrentValuesDisplay messageBoxRef={messageBoxRef} />
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  const messageBoxRef = useRef();

  const baseSize = useRef({
    width: window.innerWidth,
    height: window.innerHeight
  });

  React.useEffect(() => {
    const wrapper = document.querySelector('.app-root');
    if (!wrapper) return;
    
    // Capture initial viewport size ONCE
    const baseWidth = window.innerWidth;
    const baseHeight = window.innerHeight;
    
    // Lock the app to these exact pixel dimensions
    wrapper.style.width = `${baseWidth}px`;
    wrapper.style.height = `${baseHeight}px`;

    function scaleApp() {
      const scaleX = window.innerWidth / baseWidth;
      const scaleY = window.innerHeight / baseHeight;
      wrapper.style.transform = `scaleX(${scaleX}) scaleY(${scaleY})`;
    }

    window.addEventListener('resize', scaleApp);
    scaleApp();

    return () => window.removeEventListener('resize', scaleApp);
  }, []);

  return (
    <WebSocketProvider messageBoxRef={messageBoxRef}>
      <AppContent messageBoxRef={messageBoxRef} />
    </WebSocketProvider>
  );
}

export default App;