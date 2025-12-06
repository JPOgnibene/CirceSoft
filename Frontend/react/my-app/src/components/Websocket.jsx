import React, { useState, useEffect, useRef, createContext, useContext } from 'react';

const WS_PATH = '/ws'; // Define your WebSocket path here

// WebSocket Context for sharing connection across components
const WebSocketContext = createContext(null);

// Hook to use WebSocket in any component
export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    console.warn('useWebSocket must be used within WebSocketProvider');
  }
  return context;
};

// WebSocket class to manage connection, updates, and sending commands
class GridClientWS {
  /**
   * @param {function} onMessage - Callback function to handle incoming JSON updates.
   * @param {function} onConnectionChange - Callback for connection status changes.
   */
  constructor(onMessage, onConnectionChange) {
    this.url = `ws://localhost:8765${WS_PATH}`;
    this.socket = null;
    this.onMessage = onMessage;
    this.onConnectionChange = onConnectionChange;
    this.reconnectTimeout = null;
    this.manualDisconnect = false;
  }

  connect() {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected.');
      return;
    }

    this.manualDisconnect = false;
    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      console.log('WebSocket Connected.');
      this.onConnectionChange?.(true);
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.onMessage(message);
      } catch (e) {
        console.error('Failed to parse WebSocket message as JSON:', event.data);
      }
    };

    this.socket.onclose = (event) => {
      console.log('WebSocket Disconnected.', event.reason);
      this.onConnectionChange?.(false);
      
      if (!this.manualDisconnect) {
        console.log('Reconnecting in 5 seconds...');
        this.reconnectTimeout = setTimeout(() => this.connect(), 5000);
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket Error:', error);
      this.socket.close();
    };
  }

  disconnect() {
    this.manualDisconnect = true;
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.onConnectionChange?.(false);
  }

  isConnected() {
    return this.socket && this.socket.readyState === WebSocket.OPEN;
  }

  /**
   * Sends a command to the server via WebSocket.
   * @param {Object} payload - The JSON payload to send.
   */
  send(payload) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    } else {
      console.error('WebSocket not open. Cannot send payload.');
    }
  }

  /**
   * Update Waypoints (via WebSocket)
   * @param {Array<Object>} waypoints - List of {'r': int, 'c': int}
   */
  updateWaypoints(waypoints) {
    console.log('Sending Waypoints Update via WS...');
    this.send({ waypoints: waypoints });
  }

  /**
   * Update Obstacles (via WebSocket)
   * @param {Array<Object>} obstacles - List of {'r': int, 'c': int}
   */
  updateObstacles(obstacles) {
    console.log('Sending Obstacles Update via WS...');
    this.send({ obstacles: obstacles });
  }
}

// WebSocket Provider Component
export const WebSocketProvider = ({ children, messageBoxRef }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [distanceTraveled, setDistanceTraveled] = useState(0);
  const [isMoving, setIsMoving] = useState(false);
  const wsClientRef = useRef(null);

  // Helper function to format changes for display
  const formatChanges = (type, data) => {
    if (!data) return 'No data';

    switch (type) {
      case 'current_values_update': {
        const {
          distanceTraveled = 0,
          distanceRemaining = 0,
          cableRemaining = 0,
          percentBatteryRemaining = 0,
          errorCode = 0,
          cableDispenseStatus = false,
          debug_note = ""
        } = data;

        const shortNote =
          debug_note.length > 20 ? debug_note.slice(0, 20) + "..." : debug_note;

        return (
          `dist ${distanceTraveled.toFixed(1)}ft / ${distanceRemaining.toFixed(1)}ft, ` +
          `cable ${cableRemaining.toFixed(0)}ft, ` +
          `batt ${percentBatteryRemaining}%, ` +
          `err ${errorCode}, ` +
          `disp ${cableDispenseStatus ? "ON" : "OFF"}` +
          (shortNote ? `, note: "${shortNote}"` : "")
        );
      }

      case 'path_update':
        // Display number of path points
        if (Array.isArray(data)) {
          return `${data.length} points: ${data.slice(0, 3).map(p => `(${p.r},${p.c})`).join(', ')}${data.length > 3 ? '...' : ''}`;
        }
        return JSON.stringify(data);

      case 'directions_update':
        // Display directions array
        if (Array.isArray(data)) {
          return `${data.length} steps: ${data.slice(0, 5).join(', ')}${data.length > 5 ? '...' : ''}`;
        }
        return JSON.stringify(data);

      case 'obstacles_update':
        // Display number of obstacles
        if (Array.isArray(data)) {
          return `${data.length} obstacles: ${data.slice(0, 3).map(o => `(${o.r},${o.c})`).join(', ')}${data.length > 3 ? '...' : ''}`;
        }
        return JSON.stringify(data);

      case 'waypoints_update':
        // Display number of waypoints
        if (Array.isArray(data)) {
          return `${data.length} waypoints: ${data.slice(0, 3).map(w => `(${w.r},${w.c})`).join(', ')}${data.length > 3 ? '...' : ''}`;
        }
        return JSON.stringify(data);

      default:
        return JSON.stringify(data);
    }
  };

  // Handler for incoming WebSocket messages
  const handleServerUpdates = (message) => {
    console.log('Received Update:', message);
    
    // Handle distance traveled and movement status updates
    // Check both top-level and nested in data object
    const distanceTraveled = message.distanceTraveled ?? message.data?.distanceTraveled;
    const isMoving = message.isMoving ?? message.data?.isMoving;
    
    if (distanceTraveled !== undefined) {
      console.log('Setting distanceTraveled to:', distanceTraveled);
      setDistanceTraveled(distanceTraveled);
    }
    
    if (isMoving !== undefined) {
      console.log('Setting isMoving to:', isMoving);
      setIsMoving(isMoving);
    }
    
    // Log to message box if available with detailed changes
    if (messageBoxRef?.current) {
      const messageType = message.type || 'unknown';
      const changes = formatChanges(messageType, message.data);
      //messageBoxRef.current.addMessage('ws', `${messageType}: ${changes}`);
    }

    // Handle different message types
    if (message.type === 'current_values_update') {
      // Update robot status UI
      console.log('Current values:', message.data);
    } else if (message.type === 'path_update') {
      // Re-render path on the grid
      console.log('Path update:', message.data);
    } else if (message.type === 'directions_update') {
      console.log('Directions update:', message.data);
    } else if (message.type === 'obstacles_update') {
      console.log('Obstacles update:', message.data);
    } else if (message.type === 'waypoints_update') {
      console.log('Waypoints update:', message.data);
    }
  };

  // Handler for connection status changes
  const handleConnectionChange = (connected) => {
    setIsConnected(connected);
    if (messageBoxRef?.current) {
      messageBoxRef.current.addMessage(
        connected ? 'success' : 'warning',
        `WebSocket ${connected ? 'Connected' : 'Disconnected'}`
      );
    }
  };

  // Initialize WebSocket client
  useEffect(() => {
    wsClientRef.current = new GridClientWS(handleServerUpdates, handleConnectionChange);
    wsClientRef.current.connect();

    // Cleanup on unmount
    return () => {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
      }
    };
  }, []); // Empty dependency array - only run once

  // Create the context value object - this will update when state changes
  const contextValue = {
    isConnected,
    distanceTraveled,
    isMoving,
    wsClient: wsClientRef.current,
    connect: () => wsClientRef.current?.connect(),
    disconnect: () => wsClientRef.current?.disconnect(),
    send: (payload) => wsClientRef.current?.send(payload),
    updateWaypoints: (waypoints) => wsClientRef.current?.updateWaypoints(waypoints),
    updateObstacles: (obstacles) => wsClientRef.current?.updateObstacles(obstacles),
  };

  // Add debug logging when state changes
  useEffect(() => {
    console.log('WebSocket Context State Updated:', {
      isConnected,
      distanceTraveled,
      isMoving
    });
  }, [isConnected, distanceTraveled, isMoving]);

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

// WebSocket Status Icon Component
// WebSocket Status Icon Component
export const WebsocketStatusIcon = ({ messageBoxRef }) => {
  const ws = useWebSocket();
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (ws) {
      setIsConnected(ws.isConnected);
    }
  }, [ws?.isConnected]);

  const handleClick = () => {
    if (!ws) {
      messageBoxRef.current?.addMessage('error', 'WebSocket not initialized');
      return;
    }

    if (isConnected) {
      ws.disconnect();
      messageBoxRef.current?.addMessage('info', 'WebSocket disconnected manually');
    } else {
      ws.connect();
      messageBoxRef.current?.addMessage('info', 'WebSocket connecting...');
    }
  };

  return (
    <div
      onClick={handleClick}
      style={{
        width: 44,
        height: 44,
        borderRadius: '50%',
        // backgroundColor: 'rgba(0, 0, 0, 0.3)',
        // border: `2px solid ${isConnected ? '#00ff9f' : '#ff4757'}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        transition: 'all 0.3s ease',
        position: 'relative',
        boxShadow: isConnected 
          ? '0 0 12px rgba(0, 255, 159, 0.4), inset 0 0 8px rgba(0, 255, 159, 0.1)' 
          : '0 0 12px rgba(255, 71, 87, 0.3), inset 0 0 8px rgba(255, 71, 87, 0.1)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'scale(1.05)';
        e.currentTarget.style.boxShadow = isConnected
          ? '0 0 20px rgba(0, 255, 159, 0.6), inset 0 0 12px rgba(0, 255, 159, 0.2)'
          : '0 0 20px rgba(255, 71, 87, 0.5), inset 0 0 12px rgba(255, 71, 87, 0.2)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'scale(1)';
        e.currentTarget.style.boxShadow = isConnected
          ? '0 0 12px rgba(0, 255, 159, 0.4), inset 0 0 8px rgba(0, 255, 159, 0.1)'
          : '0 0 12px rgba(255, 71, 87, 0.3), inset 0 0 8px rgba(255, 71, 87, 0.1)';
      }}
      title={isConnected ? 'Connected - Click to disconnect' : 'Disconnected - Click to connect'}
    >
      {/* Signal waves */}
      <svg
        width="28"
        height="28"
        viewBox="0 0 24 24"
        fill="none"
        style={{ position: 'relative', zIndex: 1 }}
      >
        {/* Center dot */}
        <circle
          cx="12"
          cy="18"
          r="2.5"
          fill={isConnected ? '#00ff9f' : '#ff4757'}
          style={{
            filter: isConnected 
              ? 'drop-shadow(0 0 4px rgba(0, 255, 159, 0.8))' 
              : 'drop-shadow(0 0 4px rgba(255, 71, 87, 0.8))',
          }}
        />
        
        {/* Inner arc */}
        <path
          d="M8.5 14.5C9.5 13.5 10.7 13 12 13C13.3 13 14.5 13.5 15.5 14.5"
          stroke={isConnected ? '#00ff9f' : '#ff4757'}
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
          style={{
            opacity: isConnected ? 1 : 0.4,
            filter: isConnected ? 'drop-shadow(0 0 3px rgba(0, 255, 159, 0.6))' : 'none',
            transition: 'opacity 0.3s ease',
          }}
        />
        
        {/* Middle arc */}
        <path
          d="M5.5 11C7.3 9.2 9.5 8 12 8C14.5 8 16.7 9.2 18.5 11"
          stroke={isConnected ? '#00ff9f' : '#ff4757'}
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
          style={{
            opacity: isConnected ? 1 : 0.25,
            filter: isConnected ? 'drop-shadow(0 0 3px rgba(0, 255, 159, 0.5))' : 'none',
            transition: 'opacity 0.3s ease',
          }}
        />
        
        {/* Outer arc */}
        <path
          d="M2.5 7.5C5.3 4.7 8.5 3 12 3C15.5 3 18.7 4.7 21.5 7.5"
          stroke={isConnected ? '#00ff9f' : '#ff4757'}
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
          style={{
            opacity: isConnected ? 1 : 0.15,
            filter: isConnected ? 'drop-shadow(0 0 3px rgba(0, 255, 159, 0.4))' : 'none',
            transition: 'opacity 0.3s ease',
          }}
        />
      </svg>

      {/* Pulse animation when connected */}
      {isConnected && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: 40,
            height: 40,
            borderRadius: '50%',
            border: '1px solid rgba(0, 255, 159, 1)',
            animation: 'wsPulse 2s ease-out infinite',
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Keyframes style tag */}
      <style>
        {`
          @keyframes wsPulse {
            0% {
              transform: translate(-50%, -50%) scale(1);
              opacity: 0.6;
            }
            100% {
              transform: translate(-50%, -50%) scale(1.4);
              opacity: 0;
            }
          }
        `}
      </style>
    </div>
  );
};