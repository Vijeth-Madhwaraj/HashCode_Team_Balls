# HashCode_Team_Balls
This is a repository for the 24hackathon HashCode for team Balls 

# AI Web Automation with React & Python

A modern web application that allows users to create automated web browsing tasks by typing plain English instructions. The frontend is built with React and styled for a clean, elegant interface. The backend is a Python Flask API that generates task plans and executes automation scripts using LLMs and Playwright.

## Features

- **Plain English Instructions**: Users input natural language commands describing the automation task.
- **Task Plan Generation**: Backend parses instructions and creates step-by-step action plans.
- **Task Execution**: Automation scripts are generated and run to perform requested tasks.
- **Elegant UI**: Clean, minimal grey-themed React frontend with Lato font and interactive buttons.
- **Background Image**: Full-screen background image with translucent overlay for readability.
- **Responsive Design**: Layout adapts seamlessly to different screen sizes.
- **Smooth Interactions**: Button hover and click effects, subtle step highlight animation.

## Tech Stack

- **Frontend**: React, Axios, CSS (Lato font, greyish elegant theme)
- **Backend**: Python, FastAPI, Playwright, LLM integration (custom scripts)
- **Other Tools**: Node.js, npm/yarn for frontend packages

### Prerequisites

- Node.js (v16 or higher)
- Python (v3.8 or higher)
- pip package manager

### Frontend Setup

1. Clone the repository
2. Navigate to the frontend directory:
```
cd web-automation-frontend
```
3. Install dependencies:
```
npm install
```
4. Start the development server:
```
npm start
```
5. Open your browser at `http://localhost:3000` to see the frontend UI.

### Backend Setup

1. Navigate to the backend folder (where your Python files are located):
```
cd backend # or appropriate folder
```
2. Install Python dependencies:
```
pip install -r requirements.txt
```
(Make sure your `requirements.txt` includes Flask, flask-cors, playwright, etc.)
3. Run the backend API:
```
python backend_api.py
```
4. Ensure the backend runs on `http://localhost:5000`


## Project Structure
├── backend/ # Python backend code and API
│ ├── backend_api.py # Flask API server
│ ├── llm.py # Custom scripts for LLM integration
│ ├── llama_action_planner.py# Task planning logic
│ └── requirements.txt # Python dependencies
│
├── web-automation-frontend/ # React frontend
│ ├── public/
│ │ └── background.jpg # Background image file
│ ├── src/
│ │ ├── components/ # React components (CommandInput, TaskSteps, StatusDisplay)
│ │ ├── services/ # API communication logic
│ │ ├── App.js # Main React app component
│ │ └── App.css # CSS styling (Lato font, grey elegance theme)
│ └── package.json # Frontend dependencies
│
└── README.md # This file

## Usage

1. Type your plain English automation command in the text box (e.g., "Go to Wikipedia and search Jane Austen").
2. Click the **Generate Task Plan** button.
3. View the generated stepwise task plan.
4. Click **Execute** to run the automation via the backend.
5. Watch the status messages update live.


## Troubleshooting

- Ensure backend API is running at port 5000 before using frontend features.
- Check console for errors and verify correct Python and Node.js versions.
- Install missing dependencies using pip/npm as needed.


## Contributing

Feel free to fork and submit pull requests!
Please follow standard commit message conventions and include descriptive pull request notes.


