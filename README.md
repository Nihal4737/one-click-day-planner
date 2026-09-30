# One-Click Day Planner

AI-Powered Daily Planning and Schedule Management with Seamless Calendar & Notion Integration

## Project Overview

One-Click Day Planner is an AI-powered web application that helps users organize their daily tasks and create a structured schedule based on priorities, deadlines, working hours, breaks, and fixed commitments.

Instead of manually deciding when each task should be completed, users provide their requirements and the application uses Google Gemini AI to generate a practical daily plan. The generated schedule is displayed as organized time blocks and can be exported to Google Calendar or Notion.

## Key Features

- Add and manage daily tasks
- Set task priorities and deadlines
- Define working hours
- Add fixed commitments
- Generate AI-based daily schedules using Google Gemini
- Avoid conflicts with fixed commitments
- Display schedules in organized time blocks
- Export schedules to Google Calendar
- Export schedules to Notion
- Handle API errors and invalid inputs
- Secure API credentials using environment variables

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React.js + Vite |
| Backend | Python + Flask |
| AI | Google Gemini API |
| API Communication | Axios |
| Calendar Integration | Google Calendar API |
| Productivity Integration | Notion API |
| Version Control | Git + GitHub |
| Development Environment | Antigravity / VS Code |

## System Workflow

```text
User
  ↓
React + Vite Frontend
  ↓
Axios API Request
  ↓
Flask Backend
  ↓
Google Gemini AI
  ↓
Generated Schedule
  ↓
React Frontend
  ↙                 ↘
Google Calendar      Notion
```

## Project Structure

```text
one-click-day-planner/
│
├── backend/
│   ├── app.py
│   ├── planner.py
│   ├── calendar_service.py
│   ├── notion_service.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
│
├── run_public.py
├── README.md
└── .gitignore
```

## Setup and Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Nihal4737/one-click-day-planner.git
cd one-click-day-planner
```

### 2. Set Up the Backend

```bash
cd backend
py -3.13 -m venv venv
```

Activate the virtual environment on Windows:

```powershell
.\venv\Scripts\activate
```

Install the required packages:

```powershell
pip install -r requirements.txt
```

Create a `.env` file inside the `backend` folder and add the required API configuration.

Do not upload `.env`, API keys, OAuth credentials, or `token.json` to GitHub.

### 3. Start the Backend

From the project root:

```powershell
.\backend\venv\Scripts\python.exe backend\app.py
```

The Flask backend runs locally on:

```text
http://127.0.0.1:5000
```

### 4. Start the Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server runs on:

```text
http://localhost:5173
```

## Integrations

### Google Gemini

Gemini AI processes the user's planning information and generates a structured daily schedule while considering priorities, deadlines, working hours, and fixed commitments.

### Google Calendar

The application can export generated schedule items to Google Calendar after the required authorization is completed.

### Notion

The application can export generated schedule information to the configured Notion database.

## Security

API keys and other sensitive credentials are stored using environment variables and are excluded from version control through `.gitignore`.

Sensitive files such as `.env` and `token.json` should never be committed to the repository.

## Testing

The application was tested across its main workflow, including:

- Task input
- Priority and deadline handling
- Working hours
- Fixed commitments
- AI schedule generation
- Frontend-backend communication
- Google Calendar export
- Notion export
- API error handling

## Deployment

The project can be demonstrated publicly using Ngrok to expose the local Flask server through an HTTPS endpoint.

## Documentation

The complete project documentation contains the project description, scenarios, technical architecture, prerequisites, development milestones, testing, validation, and conclusion.

## Demo

Demo video: Add your demo video link here.

## Repository

GitHub Repository: https://github.com/Nihal4737/one-click-day-planner

## Project Status

Completed. The major planned features were implemented, integrated, tested, and uploaded to the GitHub repository.
