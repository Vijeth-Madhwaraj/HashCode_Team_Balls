import React from 'react';

function TaskSteps({ task, onExecute, executing }) {
  if (!task || !task.steps) return null;

  return (
    <div className="task-steps-container">
      <h2>📋 Task Plan: {task.task}</h2>
      
      <div className="steps-list">
        {task.steps.map((step, index) => (
          <div key={index} className="step-item">
            <span className="step-number">{index + 1}</span>
            <div className="step-details">
              <strong>{step.action.toUpperCase()}</strong>
              <span className="step-target">→ {step.target}</span>
              {step.value && !step.value.includes('PASSWORD') && (
                <span className="step-value">Value: {step.value}</span>
              )}
              {step.value && step.value.includes('PASSWORD') && (
                <span className="step-value">Value: ********</span>
              )}
            </div>
          </div>
        ))}
      </div>

      <button 
        className="execute-button" 
        onClick={onExecute}
        disabled={executing}
      >
        {executing ? '⏳ Executing...' : '▶️ Execute Automation'}
      </button>
    </div>
  );
}

export default TaskSteps;
