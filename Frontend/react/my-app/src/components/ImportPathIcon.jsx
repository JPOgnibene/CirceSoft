import React from 'react';

const ImportPathIcon = ({ messageBoxRef, onPathImported }) => {
  const PATH_JSON_ENDPOINT = "http://localhost:8765/grid/path/json";

  const handleImportPath = async () => {
    try {
      const response = await fetch(PATH_JSON_ENDPOINT);
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      const json = await response.json();
      const pathData = json.data || [];
      
      if (pathData.length === 0) {
        if (messageBoxRef?.current) {
          messageBoxRef.current.addMessage('info', 'No path data found to import');
        }
        console.log('No path data to import');
        return;
      }

      // Convert from {r, c} format to {x, y} format
      const convertedPath = pathData.map(point => ({
        x: point.c || 0,
        y: point.r || 0
      }));

      // Call the callback to update the path in parent component
      if (onPathImported) {
        onPathImported(convertedPath);
      }

      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('success', `Path imported: ${convertedPath.length} waypoints`);
      }
      console.log('Path imported:', convertedPath);
      
    } catch (error) {
      console.error("Failed to import path:", error);
      if (messageBoxRef?.current) {
        messageBoxRef.current.addMessage('error', 'Failed to import path');
      }
    }
  };

  return (
    <img
      src="/contents/images/importpathicon.png"
      alt="Import path"
      onClick={handleImportPath}
      style={{ cursor: 'pointer' }}
    />
  );
};

export default ImportPathIcon;