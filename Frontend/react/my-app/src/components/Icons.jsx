// src/components/Icons.jsx
import React from "react";

export const WebsocketStatusIcon = ({ messageBoxRef }) => {
  const handleClick = () => {
    messageBoxRef.current?.addMessage('info', 'Websocket Status Icon was clicked');
  };

  return (
    <img
      id="toggleImage"
      src="/contents/images/websocket_connection_off2.png"
      alt="Websocket Status"
      onClick={handleClick}
      style={{ cursor: 'pointer' }}
    />
  );
};

export const ImportPathIcon = ({ messageBoxRef }) => {
  const handleClick = () => {
    messageBoxRef.current?.addMessage('info', 'Import Path Icon was clicked');
  };

  return (
    <img 
      src="/contents/images/importpathicon2.png" 
      alt="Import path" 
      onClick={handleClick}
      style={{ cursor: 'pointer' }}
    />
  );
};

export const PlayButtonIcon = ({ messageBoxRef }) => {
  const handleClick = () => {
    messageBoxRef.current?.addMessage('success', 'Play button clicked - Starting path');
  };

  return (
    <img 
      src="/contents/images/playbutton2.png" 
      alt="Start/resume path" 
      onClick={handleClick}
      style={{ cursor: 'pointer' }}
    />
  );
};

export const PauseButtonIcon = ({ messageBoxRef }) => {
  const handleClick = () => {
    messageBoxRef.current?.addMessage('warning', 'Pause button clicked - Stopping path');
  };

  return (
    <img 
      src="/contents/images/pausebutton2.png" 
      alt="Stop path" 
      onClick={handleClick}
      style={{ cursor: 'pointer' }}
    />
  );
};

export const WaypointIcon = ({ messageBoxRef }) => {
  const handleClick = () => {
    messageBoxRef.current?.addMessage('info', 'Waypoint icon clicked - Ready to add waypoint');
  };

  return (
    <img 
      src="/contents/images/waypointicon2.png" 
      alt="Add a waypoint" 
      onClick={handleClick}
      style={{ cursor: 'pointer' }}
    />
  );
};

export const TargetIcon = ({ messageBoxRef }) => {
  const handleClick = () => {
    messageBoxRef.current?.addMessage('info', 'Target icon clicked - Select target location');
  };

  return (
    <img 
      src="/contents/images/targeticon2.png" 
      alt="Select target location" 
      onClick={handleClick}
      style={{ cursor: 'pointer' }}
    />
  );
};

export const OnPathIcon = ({ messageBoxRef }) => {
  const handleClick = () => {
    messageBoxRef.current?.addMessage('success', 'Bot is currently on path');
  };

  return (
    <img 
      id="togglePathDeviation" 
      src="/contents/images/onpath.png" 
      alt="Bot is on path" 
      onClick={handleClick}
      style={{ cursor: 'pointer' }}
    />
  );
};