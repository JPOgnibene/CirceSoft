import React from "react";

const Progress = ({ distanceTraveled = 0, pathLength = { feet: 0 } }) => {
  const progressPercentage = pathLength.feet > 0 
    ? Math.min(Math.round((distanceTraveled / pathLength.feet) * 100), 100)
    : 0;
  
  const safeValue = Math.min(Math.max(progressPercentage, 0), 100);
  
  // Determine text color based on progress
  // If progress is > 50%, the green fill covers the center, so use black text
  const textColor = safeValue > 50 ? '#000000' : '#ffffff';
  
  return (
    <div style={styles.progressWrapper}>
      <div style={styles.progressBar}>
        <div
          style={{
            ...styles.progressFill,
            width: `${safeValue}%`
          }}
        ></div>
        <span style={{
          ...styles.progressText,
          color: textColor,
          textShadow: safeValue > 50 ? 'none' : '0 0 6px rgba(0, 255, 159, 0.6)'
        }}>
          {safeValue}%
        </span>
      </div>
    </div>
  );
};

const styles = {
  progressWrapper: {
    width: '100%',
    background: 'rgba(15, 20, 30, 0.9)',
    borderRadius: '10px',
    border: '1px solid rgba(0, 255, 159, 0.25)',
    padding: '6px 8px',
    boxSizing: 'border-box'
  },
  progressBar: {
    position: 'relative',
    width: '100%',
    height: '19px',
    background: 'rgba(255, 255, 255, 0)',
    border: '1px solid rgba(0, 255, 159, 0.2)',
    borderRadius: '8px',
    overflow: 'hidden'
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, rgba(0, 255, 157, 0.52), rgba(0, 255, 157, 0.94), rgba(0, 255, 157, 0.52))',
    boxShadow: '0 0 10px rgba(0, 255, 159, 0.4)',
    transition: 'width 0.3s ease-in-out'
  },
  progressText: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    fontSize: '0.85rem',
    fontFamily: '"Courier New", monospace',
    fontWeight: '900',
    pointerEvents: 'none',
    transition: 'color 0.3s ease-in-out, text-shadow 0.3s ease-in-out'
  }
};

export default Progress;