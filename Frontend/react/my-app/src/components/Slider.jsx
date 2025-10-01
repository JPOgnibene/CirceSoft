import React, { useState } from "react";

const Slider = ({ onChange }) => {
  const [value, setValue] = useState(0);

  const handleSliderChange = (e) => {
    const newValue = Number(e.target.value);
    setValue(newValue);
    if (onChange) {
      onChange(newValue);
      console.log("Value updated to", newValue);
    }
  };

  return (
    <div className="progress-container">
      <input
        type="range"
        min="0"
        max="100"
        value={value}
        onChange={handleSliderChange}
        className="slider"
      />
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

export default Slider;