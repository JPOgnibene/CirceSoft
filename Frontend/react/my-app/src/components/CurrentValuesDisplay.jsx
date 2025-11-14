import React, { useEffect, useState } from 'react';
import { useWebSocket } from './Websocket';

const CurrentValuesDisplay = ({ messageBoxRef }) => {
  const [currentValues, setCurrentValues] = useState({
    X_ECI: 0.0,
    Y_ECI: 0.0,
    Z_ECI: 0.0,
    Vx_ECI: 0.0,
    Vy_ECI: 0.0,
    Vz_ECI: 0.0,
    Heading: "",
    cableRemaining: 300.0,
    percentBatteryRemaining: 100,
    errorCode: 0,
    cableDispenseStatus: false,
    cableDispenseCommand: false,
    SequenceNum: "0",
    isMoving: false,
    distanceTraveled: 0.0,
    distanceRemaining: 0.0,
    debug_note: ""
  });

  const ws = useWebSocket();

  // Listen for current_values updates from WebSocket
  useEffect(() => {
    if (!ws?.wsClient) return;

    const originalOnMessage = ws.wsClient.onMessage;

    const handleCurrentValuesUpdate = (message) => {
      originalOnMessage(message);

      if (message.type === 'current_values_update' && message.data) {
        setCurrentValues(prevValues => ({
          ...prevValues,
          ...message.data
        }));
      }
    };

    ws.wsClient.onMessage = handleCurrentValuesUpdate;

    return () => {
      if (ws.wsClient) {
        ws.wsClient.onMessage = originalOnMessage;
      }
    };
  }, [ws]);

  const containerStyle = {
    marginTop: "8px",
    padding: "8px 12px",
    backgroundColor: "rgba(15, 20, 30, 0.9)",
    border: "1px solid rgba(0, 255, 159, 0.2)",
    borderRadius: "2px",
    fontFamily: "'Courier New', monospace",
    fontSize: "0.7rem",
  };

  const gridStyle = {
    display: "grid",
    gridTemplateColumns: "repeat(8, 1fr)",
    gap: "6px 2px",
    alignItems: "center",
  };

  const itemStyle = {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
  };

  const labelStyle = {
    color: "#6b7280",
    fontSize: "0.65rem",
    fontWeight: "600",
    letterSpacing: "0.3px",
    textTransform: "uppercase",
    whiteSpace: "nowrap",
  };

  const valueStyle = {
    color: "#e0e0e0",
    fontSize: "0.75rem",
    fontWeight: "700",
  };

  const statusDotStyle = (value) => ({
    display: "inline-block",
    width: "6px",
    height: "6px",
    borderRadius: "50%",
    backgroundColor: value ? "#00ff9f" : "#ff4757",
    marginLeft: "4px",
    verticalAlign: "middle",
  });

  const getErrorColor = (code) => {
    if (code === 0) return "#00ff9f";
    if (code < 100) return "#ffaa00";
    return "#ff4757";
  };

  const getBatteryColor = (percent) => {
    if (percent > 50) return "#00ff9f";
    if (percent > 20) return "#ffaa00";
    return "#ff4757";
  };

  return (
    <div style={containerStyle}>
      <div style={gridStyle}>
        {/* Position */}
        {/* <div style={itemStyle}>
          <span style={labelStyle}>Pos X</span>
          <span style={valueStyle}>{currentValues.X_ECI.toFixed(1)}</span>
        </div>
        <div style={itemStyle}>
          <span style={labelStyle}>Pos Y</span>
          <span style={valueStyle}>{currentValues.Y_ECI.toFixed(1)}</span>
        </div>
        <div style={itemStyle}>
          <span style={labelStyle}>Pos Z</span>
          <span style={valueStyle}>{currentValues.Z_ECI.toFixed(1)}</span>
        </div>

        {/* Velocity */}
        {/* <div style={itemStyle}>
          <span style={labelStyle}>Vel X</span>
          <span style={valueStyle}>{currentValues.Vx_ECI.toFixed(1)}</span>
        </div>
        <div style={itemStyle}>
          <span style={labelStyle}>Vel Y</span>
          <span style={valueStyle}>{currentValues.Vy_ECI.toFixed(1)}</span>
        </div>
        <div style={itemStyle}>
          <span style={labelStyle}>Vel Z</span>
          <span style={valueStyle}>{currentValues.Vz_ECI.toFixed(1)}</span>
        </div> */}

        {/* Distance */}
        <div style={itemStyle}>
          <span style={labelStyle}>Traveled</span>
          <span style={valueStyle}>{currentValues.distanceTraveled.toFixed(1)} ft</span>
        </div>
        <div style={itemStyle}>
          <span style={labelStyle}>Remaining</span>
          <span style={valueStyle}>{currentValues.distanceRemaining.toFixed(1)} ft</span>
        </div>

        {/* Cable & Battery */}
        <div style={itemStyle}>
          <span style={labelStyle}>Cable</span>
          <span style={valueStyle}>{currentValues.cableRemaining.toFixed(1)} ft</span>
        </div>
        <div style={itemStyle}>
          <span style={labelStyle}>Battery</span>
          <span style={{...valueStyle, color: getBatteryColor(currentValues.percentBatteryRemaining)}}>
            {currentValues.percentBatteryRemaining}%
          </span>
        </div>

        {/* Status */}
        {/* <div style={itemStyle}>
          <span style={labelStyle}>Moving</span>
          <span style={valueStyle}>
            {currentValues.isMoving ? "YES" : "NO"}
            <span style={statusDotStyle(currentValues.isMoving)}></span>
          </span>
        </div> */}
        <div style={itemStyle}>
          <span style={labelStyle}>Dispense</span>
          <span style={valueStyle}>
            {currentValues.cableDispenseStatus ? "ON" : "OFF"}
            <span style={statusDotStyle(currentValues.cableDispenseStatus)}></span>
          </span>
        </div>

        {/* Error & Sequence */}
        <div style={itemStyle}>
          <span style={labelStyle}>Error</span>
          <span style={{...valueStyle, color: getErrorColor(currentValues.errorCode)}}>
            {currentValues.errorCode}
          </span>
        </div>
        {/* <div style={itemStyle}>
          <span style={labelStyle}>Seq #</span>
          <span style={valueStyle}>{currentValues.SequenceNum}</span>
        </div> */}

        {/* Heading */}
        {/* <div style={{...itemStyle, gridColumn: "span 2"}}>
          <span style={labelStyle}>Heading</span>
          <span style={{...valueStyle, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"}}>
            {currentValues.Heading || "N/A"}
          </span>
        </div> */}

        {/* Debug Note */}
        {currentValues.debug_note && (
          <div style={{...itemStyle, gridColumn: "span 2"}}>
            <span style={labelStyle}>Debug</span>
            <span style={{...valueStyle, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"}}>
              {currentValues.debug_note}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default CurrentValuesDisplay;