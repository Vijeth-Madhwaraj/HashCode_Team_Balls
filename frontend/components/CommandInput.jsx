import React, { useState } from 'react';

function CommandInput({ onSubmit, disabled }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onSubmit(input.trim());
      setInput('');
    }
  };

  return (
    <div className="command-input-container">
      <h2>💬 What do you want to automate?</h2>
      <form onSubmit={handleSubmit}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your command here... e.g., 'Go to Wikipedia and search Jane Austen'"
          rows="4"
          disabled={disabled}
        />
        <button type="submit" disabled={disabled || !input.trim()}>
          {disabled ? 'Generating...' : 'Generate Task Plan'}
        </button>
      </form>
      
      <div className="example-commands">
        <p><strong>Examples (click to use):</strong></p>
        <ul>
          <li onClick={() => setInput("Go to Wikipedia and search Jane Austen")}>
            Go to Wikipedia and search Jane Austen
          </li>
          <li onClick={() => setInput("Go to YouTube and search for the latest Sidemen video")}>
            Go to YouTube and search for the latest Sidemen video
          </li>
        </ul>
      </div>
    </div>
  );
}

export default CommandInput;
