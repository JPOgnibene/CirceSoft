import React, { useState } from "react";

const Progress = ({ onChange }) => {
  const [value, setValue] = useState(0);

  return (
    <div className="progress-container">
      <div className="progress-bar">
        <span className="progress-value">{value}%</span>
        <div
          className="progress-fill"
          style={{ width: `${value}%` }}
        ></div>
      </div>
    </div>
  );
};

export default Progress;