const BASE_URL = "http://127.0.0.1:8000";

export async function generateTaskPlan(instruction) {
  const response = await fetch(`${BASE_URL}/generate_task`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instruction }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function executeTask(taskName) {
  const response = await fetch(`${BASE_URL}/execute_task`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task: taskName }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}
