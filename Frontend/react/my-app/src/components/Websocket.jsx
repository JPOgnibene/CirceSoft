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
  const wsClientRef = useRef(null);

  // Handler for incoming WebSocket messages
  const handleServerUpdates = (message) => {
    console.log('Received Update:', message);
    
    // Log to message box if available
    if (messageBoxRef?.current) {
      messageBoxRef.current.addMessage('ws', `WS Update: ${message.type || 'unknown'}`);
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
  }, []);

  const value = {
    isConnected,
    wsClient: wsClientRef.current,
    connect: () => wsClientRef.current?.connect(),
    disconnect: () => wsClientRef.current?.disconnect(),
    send: (payload) => wsClientRef.current?.send(payload),
    updateWaypoints: (waypoints) => wsClientRef.current?.updateWaypoints(waypoints),
    updateObstacles: (obstacles) => wsClientRef.current?.updateObstacles(obstacles),
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

// WebSocket Status Icon Component
export const WebsocketStatusIcon = ({ messageBoxRef }) => {
  const ws = useWebSocket();
  const [isConnected, setIsConnected] = useState(false);

  // Update local state when WebSocket connection changes
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
    <img
      id="toggleImage"
      src={
        isConnected
          ? '/contents/images/websocket_connection_on.png'
          : '/contents/images/websocket_connection_off.png'
      }
      alt="Websocket Status"
      onClick={handleClick}
      style={{ cursor: 'pointer' }}
      title={isConnected ? 'Connected - Click to disconnect' : 'Disconnected - Click to connect'}
    />
  );
};