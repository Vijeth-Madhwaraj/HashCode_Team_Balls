import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000';

export const generateTaskPlan = async (instruction) => {
  const response = await axios.post(`${API_BASE_URL}/generate-task`, {
    instruction: instruction
  });
  return response.data;
};

export const executeTask = async (taskName) => {
  const response = await axios.post(`${API_BASE_URL}/execute-task`, {
    task_name: taskName
  });
  return response.data;
};

export const getTasks = async () => {
  const response = await axios.get(`${API_BASE_URL}/tasks`);
  return response.data;
};
