import React, { useState } from "react";
import axios from "axios";

function AuthPage({ apiBaseUrl, onAuthSuccess }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setMessage("");

    if (!email.trim() || !password) {
      setMessage("Email and password are required.");
      return;
    }

    if (mode === "register" && !name.trim()) {
      setMessage("Name is required for registration.");
      return;
    }

    setLoading(true);
    try {
      const url = `${apiBaseUrl}/auth/${mode}`;
      const payload =
        mode === "register"
          ? { name: name.trim(), email: email.trim(), password }
          : { email: email.trim(), password };

      const response = await axios.post(url, payload);
      onAuthSuccess(response.data);
    } catch (error) {
      setMessage(error?.response?.data?.error || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-layout">
        <div className="auth-visual">
          <p className="eyebrow">SPENDSENSE AI</p>
          <h2>Turn every swipe into a strategy.</h2>
          <p>
            A premium control center for budgeting, monthly debits, and AI-powered expense insights designed for
            modern financial clarity.
          </p>
          <img
            src="https://images.unsplash.com/photo-1579621970795-87facc2f976d?auto=format&fit=crop&w=1200&q=80"
            alt="Luxury finance setup"
          />
        </div>
        <div className="auth-card">
          <h1>{mode === "login" ? "Welcome Back" : "Create Your Account"}</h1>
          <p className="meta">Track expenses, budgets, and smart reports.</p>

          <div className="auth-tabs">
            <button
              className={mode === "login" ? "tab-btn active" : "tab-btn"}
              onClick={() => setMode("login")}
              type="button"
            >
              Login
            </button>
            <button
              className={mode === "register" ? "tab-btn active" : "tab-btn"}
              onClick={() => setMode("register")}
              type="button"
            >
              Register
            </button>
          </div>

          <form onSubmit={submit}>
            {mode === "register" ? (
              <input
                type="text"
                placeholder="Full name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            ) : null}

            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />

            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <button type="submit" disabled={loading}>
              {loading ? "Please wait..." : mode === "login" ? "Login" : "Create Account"}
            </button>
          </form>

          {message ? <p className="meta">{message}</p> : null}
        </div>
      </div>
    </div>
  );
}

export default AuthPage;
