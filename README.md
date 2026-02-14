# SpendSense AI

SpendSense AI is a production-quality, hackathon-ready AI-powered expense tracker built with React, Flask, SQLite, Google Gemini API, and Backboard API.

## Features
- Add and store expenses in SQLite
- Auto-categorize expenses with Gemini AI
- Dashboard analytics with totals and category breakdown
- AI-generated financial insights from expense history
- Backboard user profile integration via backend endpoint

## Project Structure
- `backend/app.py`
- `backend/models.py`
- `backend/database.py`
- `backend/gemini_service.py`
- `backend/blackboard_service.py`
- `frontend/src/App.js`
- `frontend/src/components/AddExpense.js`
- `frontend/src/components/ExpenseList.js`
- `frontend/src/components/Dashboard.js`
- `frontend/src/components/UserProfile.js`

## Environment Variables
Create `.env` in project root:

```env
GEMINI_API_KEY=your_gemini_api_key
BLACKBOARD_API_KEY=your_backboard_api_key
BACKBOARD_API_BASE_URL=https://app.backboard.io/api
```

## Backend Run

```bash
cd backend
pip install flask flask-cors python-dotenv requests google-generativeai
python app.py
```

Server runs at `http://localhost:5000`.

## Frontend Run

```bash
cd frontend
npm install
npm start
```

Frontend runs at `http://localhost:3000` and calls backend at `http://localhost:5000` by default.

## API Endpoints
- `POST /add_expense`
  - body: `{ "name": "Coffee", "amount": 5.75 }`
- `GET /expenses`
- `GET /summary`
- `GET /user_profile`

## Notes
- SQLite database file is auto-created at `backend/database.db`.
- If Gemini or Backboard keys are missing/invalid, endpoints return clear errors.
- Override frontend backend URL with `REACT_APP_API_BASE_URL` if needed.
