import { createContext, useContext, useState } from 'react';

const ArrayContext = createContext();

// Custom hook for easier access
export function useArray() {
  const context = useContext(ArrayContext);
  if (!context) {
    throw new Error('useArray must be used within ArrayProvider');
  }
  return context;
}

// Provider component
export function ArrayProvider({ children }) {
  const [myArray, setMyArray] = useState([]);
  
  // You can add helper functions here
  const addItem = (item) => {
    setMyArray(prev => [...prev, item]);
  };
  
  const removeItem = (index) => {
    setMyArray(prev => prev.filter((_, i) => i !== index));
  };
  
  return (
    <ArrayContext.Provider value={{ myArray, setMyArray, addItem, removeItem 