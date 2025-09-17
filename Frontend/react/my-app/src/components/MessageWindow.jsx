import React, { useState, useEffect, useRef, useImperativeHandle, forwardRef } from 'react';

const MessageWindow = forwardRef((props, ref) => {
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);

  // Expose addMessage function to parent components
  useImperativeHandle(ref, () => ({
    addMessage: (type, content) => {
      const newMessage = {
        id: Date.now() + Math.random(),
        type: type,
        content: content,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, newMessage]);
    },
    clearMessages: () => {
      setMessages([]);
    }
  }));

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const formatTimestamp = (timestamp) => {
    return timestamp.toLocaleTimeString();
  };

  return (
    <div className="message_window">      
      <div className="messages">
        {messages.length === 0 ? (
          <div className="hazard info">
            Message window connected...
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={`hazard ${message.type}`}>
              <strong>[{formatTimestamp(message.timestamp)}]</strong> {message.content}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
});

MessageWindow.displayName = 'MessageWindow';

export default MessageWindow;