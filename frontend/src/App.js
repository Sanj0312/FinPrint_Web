import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import AddExpense from "./components/AddExpense";
import ExpenseList from "./components/ExpenseList";
import Dashboard from "./components/Dashboard";
import UserSettings from "./components/UserSettings";
import Reports from "./components/Reports";
import AuthPage from "./components/AuthPage";
import MoneyDNA from "./components/MoneyDNA";
import CoachChat from "./components/CoachChat";
import SiteFooter from "./components/SiteFooter";
import BrandLogo from "./components/BrandLogo";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:5003";
const TOKEN_KEY = "spendsense_auth_token";

function App() {
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || "");
  const [user, setUser] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [expenses, setExpenses] = useState([]);
  const [summary, setSummary] = useState({
    total_spending: 0,
    spending_per_category: {},
    ai_insight: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("dashboard");

  const authHeaders = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const handleAuthSuccess = ({ token: newToken, user: currentUser }) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
    setUser(currentUser || null);
  };

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken("");
    setUser(null);
    setExpenses([]);
    setSummary({ total_spending: 0, spending_per_category: {}, ai_insight: "" });
    setActiveTab("dashboard");
  };

  const fetchAuthUser = useCallback(async () => {
    const response = await axios.get(`${API_BASE_URL}/auth/me`, { headers: authHeaders });
    setUser(response.data);
  }, [authHeaders]);

  const fetchExpenses = useCallback(async () => {
    const response = await axios.get(`${API_BASE_URL}/expenses`, { headers: authHeaders });
    setExpenses(response.data || []);
  }, [authHeaders]);

  const fetchSummary = useCallback(async () => {
    const response = await axios.get(`${API_BASE_URL}/summary`, { headers: authHeaders });
    setSummary(response.data);
  }, [authHeaders]);

  const bootstrap = useCallback(async () => {
    if (!token) {
      return;
    }

    setLoading(true);
    setError("");
    try {
      await Promise.all([fetchAuthUser(), fetchExpenses(), fetchSummary()]);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        handleLogout();
      }
      setError(err?.response?.data?.error || "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, [token, fetchAuthUser, fetchExpenses, fetchSummary]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    const elements = Array.from(
      document.querySelectorAll(".app-header-row, .top-tabs, .dashboard-hero, .grid-layout .card, .site-footer")
    );

    if (!elements.length) {
      return undefined;
    }

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduceMotion) {
      elements.forEach((el) => el.classList.add("in-view"));
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in-view");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.14, rootMargin: "0px 0px -8% 0px" }
    );

    elements.forEach((el, index) => {
      const delay = index > 4 ? 280 : index * 70;
      el.classList.add("reveal-on-scroll");
      el.style.setProperty("--reveal-delay", String(delay) + "ms");
      observer.observe(el);
    });

    return () => observer.disconnect();
  }, [activeTab, loading, token]);

  const handleExpenseAdded = async (newExpense) => {
    if (newExpense?.id) {
      setExpenses((prev) => {
        const withoutDuplicate = prev.filter((item) => item.id !== newExpense.id);
        return [newExpense, ...withoutDuplicate];
      });
    } else {
      await fetchExpenses();
    }
    await fetchSummary();
  };

  const handleExpenseDeleted = async (expenseId) => {
    await axios.delete(`${API_BASE_URL}/expenses/${expenseId}`, { headers: authHeaders });
    setExpenses((prev) => prev.filter((item) => item.id !== expenseId));
    await fetchSummary();
  };

  const handleExpenseUpdated = async (expenseId, updates) => {
    const response = await axios.put(`${API_BASE_URL}/expenses/${expenseId}`, updates, { headers: authHeaders });
    const updated = response.data;
    setExpenses((prev) => prev.map((item) => (item.id === expenseId ? updated : item)));
    await fetchSummary();
  };

  const handleHeroImageFallback = (event) => {
    event.currentTarget.onerror = null;
    event.currentTarget.src = "https://picsum.photos/id/180/1000/700";
  };

  if (!token) {
    return <AuthPage apiBaseUrl={API_BASE_URL} onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <div className="app-container">
      <header className="app-header app-header-row">
        <div>
          <div className="brand-row">
            <BrandLogo />
            <h1 className="brand-title">
              FinPrint <span className="brand-sub">by Fynx</span>
            </h1>
          </div>
          <p>Decode your Money DNA with AI-powered expense intelligence.</p>
        </div>
        <div className="header-actions">
          <span className="meta">{user?.email || "Signed in"}</span>
          <button
            className="icon-btn"
            type="button"
            title="User Settings"
            onClick={() => setSettingsOpen(true)}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M19.14 12.94a7.55 7.55 0 0 0 .05-.94 7.55 7.55 0 0 0-.05-.94l2.03-1.58a.5.5 0 0 0 .12-.64l-1.92-3.32a.5.5 0 0 0-.6-.22l-2.39.96a7.34 7.34 0 0 0-1.63-.95l-.36-2.54a.5.5 0 0 0-.5-.43h-3.84a.5.5 0 0 0-.5.43l-.36 2.54c-.57.23-1.12.55-1.63.95l-2.39-.96a.5.5 0 0 0-.6.22L2.71 8.84a.5.5 0 0 0 .12.64l2.03 1.58c-.03.31-.05.63-.05.94s.02.63.05.94L2.83 14.52a.5.5 0 0 0-.12.64l1.92 3.32c.13.22.4.31.6.22l2.39-.96c.5.4 1.05.72 1.63.95l.36 2.54c.04.24.25.43.5.43h3.84c.25 0 .46-.19.5-.43l.36-2.54c.58-.23 1.13-.55 1.63-.95l2.39.96c.23.09.48 0 .6-.22l1.92-3.32a.5.5 0 0 0-.12-.64l-2.03-1.58ZM12 15.5A3.5 3.5 0 1 1 12 8.5a3.5 3.5 0 0 1 0 7Z" />
            </svg>
          </button>
          <button className="secondary-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <div className="top-tabs">
        <button
          type="button"
          className={activeTab === "dashboard" ? "top-tab active" : "top-tab"}
          onClick={() => setActiveTab("dashboard")}
        >
          Dashboard
        </button>
        <button
          type="button"
          className={activeTab === "expenses" ? "top-tab active" : "top-tab"}
          onClick={() => setActiveTab("expenses")}
        >
          My Expenses
        </button>
        <button
          type="button"
          className={activeTab === "money-dna" ? "top-tab active" : "top-tab"}
          onClick={() => setActiveTab("money-dna")}
        >
          Money DNA
        </button>
        <button
          type="button"
          className={activeTab === "coach" ? "top-tab active" : "top-tab"}
          onClick={() => setActiveTab("coach")}
        >
          Coach
        </button>
      </div>

      <section className="dashboard-hero card wide">
        <div className="dashboard-hero-copy">
          <p className="eyebrow">SMART MONEY COCKPIT</p>
          <h2>Beautiful spending intelligence, all in one place.</h2>
          <p>
            Track expenses, monitor monthly debits, and keep budget performance visible every day with AI-powered
            context.
          </p>
        </div>
        <div className="dashboard-hero-images">
          <img
            src="https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=800&q=80"
            alt="Financial planning desk"
            onError={handleHeroImageFallback}
          />
          <img
            src="https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=800&q=80"
            alt="Analytics dashboard"
            onError={handleHeroImageFallback}
          />
        </div>
      </section>

      {error ? <div className="alert alert-error">{error}</div> : null}
      {loading ? <div className="alert">Loading...</div> : null}

      <div
        className={settingsOpen ? "settings-overlay open" : "settings-overlay"}
        onClick={() => setSettingsOpen(false)}
      />
      <aside className={settingsOpen ? "settings-drawer open" : "settings-drawer"}>
        <div className="drawer-header">
          <h3>User Settings</h3>
          <button className="secondary-btn" type="button" onClick={() => setSettingsOpen(false)}>
            Close
          </button>
        </div>
        <UserSettings apiBaseUrl={API_BASE_URL} authHeaders={authHeaders} onSettingsUpdated={setUser} />
      </aside>

      {activeTab === "dashboard" ? (
        <div className="grid-layout">
          <section className="card wide">
            <Reports apiBaseUrl={API_BASE_URL} authHeaders={authHeaders} compact />
          </section>

          <section className="card wide">
            <Dashboard summary={summary} />
          </section>
        </div>
      ) : activeTab === "expenses" ? (
        <div className="grid-layout">
          <section className="card">
            <AddExpense apiBaseUrl={API_BASE_URL} authHeaders={authHeaders} onExpenseAdded={handleExpenseAdded} />
          </section>
          <section className="card wide">
            <ExpenseList
              expenses={expenses}
              onDeleteExpense={handleExpenseDeleted}
              onUpdateExpense={handleExpenseUpdated}
            />
          </section>
        </div>
      ) : activeTab === "coach" ? (
        <div className="grid-layout">
          <section className="card wide">
            <CoachChat apiBaseUrl={API_BASE_URL} authHeaders={authHeaders} />
          </section>
        </div>
      ) : (
        <div className="grid-layout">
          <section className="card wide">
            <MoneyDNA apiBaseUrl={API_BASE_URL} authHeaders={authHeaders} />
          </section>
        </div>
      )}

      <SiteFooter />
    </div>
  );
}

export default App;
