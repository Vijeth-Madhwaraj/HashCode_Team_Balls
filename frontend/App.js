import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [instruction, setInstruction] = useState("");
  const [modification, setModification] = useState("");
  const [tasks, setTasks] = useState([]);
  const [currentTask, setCurrentTask] = useState(null);
  const [status, setStatus] = useState("idle"); // will control the sphere
  const [developerText, setDeveloperText] = useState("");
  const [showJSONEditor, setShowJSONEditor] = useState(false);
  const [editableJSON, setEditableJSON] = useState("");

  // ---------- Helper to format steps ----------
  const formatSteps = (steps) => {
    if (!steps || !Array.isArray(steps)) return "";
    return steps.map((step, i) => {
      const val = step.value 
        ? (step.target.toLowerCase().includes("password") ? "********" : step.value) 
        : "";
      return `Step ${i + 1}: ${step.action} -> ${step.target}${val ? ` | Value: ${val}` : ""}`;
    }).join("\n");
  };

  // ---------- Fetch tasks ----------
  const refreshTasks = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/list-tasks");
      const data = await res.json();
      setTasks(data.tasks || []);
    } catch(err){ console.error(err); }
  };

  useEffect(() => { refreshTasks(); }, []);

  // ---------- Add new task ----------
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
      setDeveloperText(formatSteps(plan.steps));
      setStatus("idle");
      setInstruction("");
      refreshTasks();
    } catch(err){ console.error(err); setStatus("error"); }
  };

  // ---------- Modify existing task ----------
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
      setDeveloperText(formatSteps(updated.steps));
      setStatus("idle");
      setModification("");
      refreshTasks();
    } catch(err){ console.error(err); setStatus("error"); }
  };

  // ---------- Execute task ----------
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

  // ---------- Developer view (read JSON) ----------
  const handleDeveloperView = async (taskName) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/developer-task/${taskName}`);
      const data = await res.json();
      setCurrentTask(data.plan);
      setDeveloperText(formatSteps(data.plan.steps));
      setEditableJSON(JSON.stringify(data.plan, null, 2));
      setShowJSONEditor(false);
    } catch(err){ console.error(err); }
  };

  // ---------- Execute edited JSON ----------
  const executeEditedJSON = async () => {
    if (!editableJSON) return;
    let parsed;
    try { parsed = JSON.parse(editableJSON); } 
    catch(err){ alert("Invalid JSON"); return; }

    setStatus("executing");
    try {
      const res = await fetch("http://127.0.0.1:8000/execute-json", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify(parsed)
      });
      const result = await res.json();
      alert(JSON.stringify(result, null, 2));
      setCurrentTask(parsed); // overwrite current task
      setDeveloperText(formatSteps(parsed.steps));
      setStatus("idle");
      refreshTasks();
    } catch(err){ console.error(err); setStatus("error"); }
  };

  // ---------- Choose a task ----------
  const chooseTask = () => {
    if (tasks.length === 0) return null;
    return tasks[0]; // optional: default selection, can adjust
  };

  return (
    <div className="app-container">
      {/* Status Sphere */}
      <span className={`status-indicator ${status}`}></span>

      {/* Left Sidebar */}
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

      {/* Right Main Panel */}
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
      </main>
    </div>
  );
}

export default App;
