import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [instruction, setInstruction] = useState("");
  const [modification, setModification] = useState("");
  const [tasks, setTasks] = useState([]);
  const [currentTask, setCurrentTask] = useState(null);
  const [status, setStatus] = useState("idle");
  const [developerText, setDeveloperText] = useState("");
  const [showJSONEditor, setShowJSONEditor] = useState(false);
  const [editableJSON, setEditableJSON] = useState("");

  const refreshTasks = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/list-tasks");
      const data = await res.json();
      setTasks(data.tasks || []);
    } catch(err){ console.error(err); }
  };

  useEffect(() => { refreshTasks(); }, []);

  const handleAddTask = async () => {
    if (!instruction) return;
    setStatus("generating");
    try {
      const res = await fetch("http://127.0.0.1:8000/generate-task", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({instruction})
      });
      const plan = await res.json();
      setCurrentTask(plan);
      setStatus("idle");
      setInstruction("");
      refreshTasks();
    } catch(err){ console.error(err); setStatus("error"); }
  };

  const handleModifyTask = async () => {
    if (!currentTask || !modification) return;
    setStatus("modifying");
    try {
      const res = await fetch("http://127.0.0.1:8000/modify-task", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ task: currentTask.task, modification })
      });
      const updated = await res.json();
      setCurrentTask(updated);
      setStatus("idle");
      setModification("");
      refreshTasks();
    } catch(err){ console.error(err); setStatus("error"); }
  };

  const handleExecuteTask = async () => {
    if (!currentTask) return;
    setStatus("executing");
    try {
      const res = await fetch("http://127.0.0.1:8000/execute-task", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ task: currentTask.task })
      });
      const result = await res.json();
      alert(JSON.stringify(result, null, 2));
      setStatus("idle");
    } catch(err){ console.error(err); setStatus("error"); }
  };

  const handleDeveloperView = async (taskName) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/developer-task/${taskName}`);
      const data = await res.json();
      setDeveloperText(data.readable_text || "");
      setCurrentTask(data.plan);
      setEditableJSON(JSON.stringify(data.plan, null, 2));
      setShowJSONEditor(false);
    } catch(err){ console.error(err); }
  };

  const executeEditedJSON = async () => {
    if (!editableJSON) return;
    let parsed;
    try { parsed = JSON.parse(editableJSON); } 
    catch(err){ alert("❌ Invalid JSON"); return; }
    setStatus("executing");
    try {
      const res = await fetch("http://127.0.0.1:8000/execute-json", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify(parsed)
      });
      const result = await res.json();
      alert(JSON.stringify(result, null, 2));
      setStatus("idle");
      refreshTasks();
      handleDeveloperView(parsed.task);
    } catch(err){ console.error(err); setStatus("error"); }
  };

  return (
    <div className="app-container">
      <span className={`status-indicator ${status}`}></span>

      {/* Sidebar */}
      <aside className="sidebar">
        <h2>Tasks</h2>
        <ul className="task-list">
          {tasks.map(t => (
            <li 
              key={t} 
              className={`task-item ${currentTask?.task===t?'active':''}`}
              onClick={()=>handleDeveloperView(t)}
            >
              {t}
            </li>
          ))}
        </ul>

        <div className="add-task">
          <h3>Add Task</h3>
          <input 
            type="text" 
            placeholder="Instruction" 
            value={instruction} 
            onChange={e=>setInstruction(e.target.value)}
          />
          <button onClick={handleAddTask}>Add</button>
        </div>
      </aside>

      {/* Main Panel */}
      <main className="main-panel">
        {currentTask ? (
          <>
            <h2 className="task-title">{currentTask.task}</h2>

            <h3>Steps</h3>
            <pre className="developer-text">{developerText}</pre>

            <h3>Modify Task</h3>
            <input 
              type="text" 
              placeholder="Modification instruction" 
              value={modification} 
              onChange={e=>setModification(e.target.value)}
            />
            <div className="button-group">
              <button onClick={handleModifyTask}>Modify</button>
              <button className="execute" onClick={handleExecuteTask}>Execute</button>
            </div>

            <h3>Developer JSON</h3>
            {!showJSONEditor ? (
              <button onClick={()=>setShowJSONEditor(true)}>Edit JSON</button>
            ) : (
              <div className="json-editor">
                <textarea 
                  value={editableJSON} 
                  onChange={e=>setEditableJSON(e.target.value)}
                />
                <div className="button-group">
                  <button onClick={executeEditedJSON}>Run JSON</button>
                  <button onClick={()=>setShowJSONEditor(false)}>Close</button>
                </div>
              </div>
            )}
          </>
        ) : (
          <p className="placeholder">Select a task to view details</p>
        )}

        <footer className="footer">
          Status: <span className={`status ${status}`}>{status}</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
