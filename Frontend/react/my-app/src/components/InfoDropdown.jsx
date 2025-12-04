import React, { useState } from 'react';

const InfoDropdown = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  const openDropdown = () => {
    setIsVisible(true);
    setTimeout(() => setIsAnimating(true), 10);
    setIsOpen(true);
  };

  const closeDropdown = () => {
    setIsAnimating(false);
    setIsOpen(false);
    setTimeout(() => setIsVisible(false), 300);
  };

  const toggleDropdown = () => {
    if (isOpen) {
      closeDropdown();
    } else {
      openDropdown();
    }
  };

  return (
    <>
      {/* Info Icon Button */}
      <div
        onClick={toggleDropdown}
        style={{
          width: 40,
          height: 40,
          borderRadius: '50%',
          backgroundColor: isOpen ? 'rgba(0, 255, 159, 0.3)' : 'rgba(255, 255, 255, 0.1)',
          border: `2px solid ${isOpen ? '#00ff9f' : '#666'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          if (!isOpen) {
            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
            e.currentTarget.style.borderColor = '#00ff9f';
          }
        }}
        onMouseLeave={(e) => {
          if (!isOpen) {
            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
            e.currentTarget.style.borderColor = '#666';
          }
        }}
        title="Project Information"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke={isOpen ? '#00ff9f' : '#cccccc'}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
      </div>

      {/* Overlay Background */}
      {isVisible && (
        <div
          onClick={closeDropdown}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            zIndex: 999,
            opacity: isAnimating ? 1 : 0,
            transition: 'opacity 0.3s ease',
          }}
        />
      )}

      {/* Dropdown Panel */}
      {isVisible && (
        <div
          style={{
            position: 'fixed',
            top: 80,
            left: '50%',
            transform: `translateX(-50%) scale(${isAnimating ? 1 : 0.95})`,
            width: '90%',
            maxWidth: 1200,
            maxHeight: 'calc(100% - 120px)',
            background: 'rgba(166, 166, 166, .15)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(0, 255, 159, 0.3)',
            borderRadius: 8,
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5), 0 0 20px rgba(0, 255, 159, 0.1)',
            zIndex: 1000,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            fontFamily: "'Courier New', monospace",
            opacity: isAnimating ? 1 : 0,
            transition: 'opacity 0.3s ease, transform 0.3s ease',
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '16px 20px',
              borderBottom: '1px solid rgba(0, 255, 159, 0.2)',
              background: 'rgba(0, 0, 0, .25)',
              backdropFilter: 'blur(20px)',
            }}
          >
            <h2
              style={{
                margin: 0,
                color: '#00ff9f',
                fontSize: '1.4rem',
                fontWeight: 600,
                letterSpacing: 1,
              }}
            >
              Project Information
            </h2>
            <button
              onClick={closeDropdown}
              style={{
                background: 'none',
                border: 'none',
                color: '#888',
                fontSize: '1.5rem',
                cursor: 'pointer',
                padding: '4px 8px',
                lineHeight: 1,
                transition: 'color 0.2s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ff6b6b')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#888')}
            >
              ×
            </button>
          </div>

          {/* Content Area */}
          <div
            style={{
              padding: 24,
              overflowY: 'auto',
              color: '#e0e0e0',
              lineHeight: 1.7,
            }}
          >
            {/* Project Title Section */}
            <section style={{ marginBottom: 24 }}>
              <h3
                style={{
                  color: '#00ff9f',
                  fontSize: '1.1rem',
                  marginBottom: 12,
                  borderBottom: '1px solid rgba(0, 255, 159, 0.2)',
                  paddingBottom: 8,
                }}
              >
                About CirceSoft
              </h3>
              <p style={{ margin: 0, color: '#e0e0e0ca' }}>
                CirceSoft is a robotic control interface designed for real-time path planning
                and obstacle management. This application provides operators with an intuitive
                way to plot navigation paths, define obstacles, and monitor robot movement
                in real-time.
              </p>
            </section>

            {/* Features Section */}
            <section style={{ marginBottom: 24 }}>
              <h3
                style={{
                  color: '#00ff9f',
                  fontSize: '1.1rem',
                  marginBottom: 12,
                  borderBottom: '1px solid rgba(0, 255, 159, 0.2)',
                  paddingBottom: 8,
                }}
              >
                Key Features
              </h3>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: 20,
                  color: '#e0e0e0ca',
                }}
              >
                <li style={{ marginBottom: 8 }}>
                  <strong style={{ color: '#e0e0e0' }}>Path Planning:</strong> Click-to-plot
                  waypoint system with drag-and-drop repositioning
                </li>
                <li style={{ marginBottom: 8 }}>
                  <strong style={{ color: '#e0e0e0' }}>Obstacle Management:</strong> Define
                  and manage obstacle zones on the navigation grid
                </li>
                <li style={{ marginBottom: 8 }}>
                  <strong style={{ color: '#e0e0e0' }}>Real-Time Monitoring:</strong> WebSocket
                  integration for live robot position and status updates
                </li>
                <li style={{ marginBottom: 8 }}>
                  <strong style={{ color: '#e0e0e0' }}>Path Validation:</strong> Automatic
                  path length limits and obstacle collision prevention
                </li>
              </ul>
            </section>

            {/* Usage Section */}
            <section style={{ marginBottom: 24 }}>
              <h3
                style={{
                  color: '#00ff9f',
                  fontSize: '1.1rem',
                  marginBottom: 12,
                  borderBottom: '1px solid rgba(0, 255, 159, 0.2)',
                  paddingBottom: 8,
                }}
              >
                How to Use
              </h3>
              <ol
                style={{
                  margin: 0,
                  paddingLeft: 20,
                  color: '#e0e0e0ca',
                }}
              >
                <li style={{ marginBottom: 8 }}>
                  Select <strong style={{ color: '#e0e0e0' }}>Path Mode</strong> to plot
                  navigation waypoints on the grid
                </li>
                <li style={{ marginBottom: 8 }}>
                  Switch to <strong style={{ color: '#e0e0e0' }}>Obstacle Mode</strong> to
                  mark areas the robot should avoid
                </li>
                <li style={{ marginBottom: 8 }}>
                  Use the <strong style={{ color: '#e0e0e0' }}>Calculate Path</strong> button to
                    validate the plotted path against obstacles and length limits
                </li>
                <li style={{ marginBottom: 8 }}>
                  Press <strong style={{ color: '#e0e0e0' }}>Start</strong> to begin robot
                  navigation along the plotted path
                </li>
              </ol>
            </section>

            {/* Version/Credits Section */}
            <section>
              <h3
                style={{
                  color: '#00ff9f',
                  fontSize: '1.1rem',
                  marginBottom: 12,
                  borderBottom: '1px solid rgba(0, 255, 159, 0.2)',
                  paddingBottom: 8,
                }}
              >
                Version Info
              </h3>
              <p style={{ margin: 0, color: '#888', fontSize: '0.9rem' }}>
                DEVCOM CirceSoft v1.0.0<br />
                Developed by Gabriel Adams, Celia Hough, Ryan Naleway, JP Ognibene, 
                Harrison Simpson, Graham Wheeler<br />
                
              </p>
            </section>
          </div>
        </div>
      )}
    </>
  );
};

export default InfoDropdown;