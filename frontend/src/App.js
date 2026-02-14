import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";
import AddExpense from "./components/AddExpense";
import ExpenseList from "./components/ExpenseList";
import Dashboard from "./components/Dashboard";
import UserProfile from "./components/UserProfile";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:5000";

function App() {
  const [expenses, setExpenses] = useState([]);
  const [summary, setSummary] = useState({
    total_spending: 0,
    spending_per_category: {},
    ai_insight: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchExpenses = useCallback(async () => {
    const response = await axios.get(`${API_BASE_URL}/expenses`);
    setExpenses(response.data || []);
  }, []);

  const fetchSummary = useCallback(async () => {
    const response = await axios.get(`${API_BASE_URL}/summary`);
    setSummary(response.data);
  }, []);

  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      await Promise.all([fetchExpenses(), fetchSummary()]);
    } catch (err) {
      setError(err?.response?.data?.error || "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, [fetchExpenses, fetchSummary]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const handleExpenseAdded = async () => {
    await bootstrap();
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>SpendSense AI</h1>
        <p>AI-powered expense intelligence for smarter decisions.</p>
      </header>

      {error ? <div className="alert alert-error">{error}</div> : null}
      {loading ? <div className="alert">Loading...</div> : null}

      <div className="grid-layout">
        <section className="card">
          <UserProfile apiBaseUrl={API_BASE_URL} />
        </section>

        <section className="card">
          <AddExpense apiBaseUrl={API_BASE_URL} onExpenseAdded={handleExpenseAdded} />
        </section>

        <section className="card wide">
          <Dashboard summary={summary} />
        </section>

        <section className="card wide">
          <ExpenseList expenses={expenses} />
        </section>
      </div>
    </div>
  );
}

export default App;
