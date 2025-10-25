import React from 'react';

function StatusDisplay({ status }) {
  const statusConfig = {
    idle: { emoji: '⚪', text: 'Ready', color: '#gray' },
    generating: { emoji: '🔄', text: 'Generating plan...', color: '#3b82f6' },
    executing: { emoji: '⚡', text: 'Executing automation...', color: '#f59e0b' },
    complete: { emoji: '✅', text: 'Complete!', color: '#10b981' },
    error: { emoji: '❌', text: 'Error occurred', color: '#ef4444' }
  };

  const config = statusConfig[status] || statusConfig.idle;

  return (
    <div className="status-display" style={{ borderColor: config.color }}>
      <span className="status-emoji">{config.emoji}</span>
      <span className="status-text">{config.text}</span>
    </div>
  );
}

export default StatusDisplay;
