import React, { useState } from "react";
import axios from "axios";
import SiteFooter from "./SiteFooter";
import BrandLogo from "./BrandLogo";

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

  const withFallback = (event) => {
    event.currentTarget.onerror = null;
    event.currentTarget.src =
      "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?auto=format&fit=crop&w=900&q=80";
  };

  return (
    <div className="auth-shell">
      <div className="auth-layout">
        <div className="auth-visual">
          <div className="brand-row">
            <BrandLogo />
            <h1 className="auth-brand-main">
              FinPrint <span className="brand-sub">by Fynx</span>
            </h1>
          </div>
          <h2>Your money glow-up starts by decoding your Money DNA.</h2>
          <p>
            Bright, bold, and built to vibe with your goals. Track spending, crush budgets, and turn messy money
            habits into clean wins.
          </p>
          <div className="auth-slogan-stack">
            <div className="auth-slogan">Spend smart. Flex harder.</div>
            <div className="auth-slogan">Your wallet, but make it iconic.</div>
            <div className="auth-slogan">Tiny habits. Big balance energy.</div>
          </div>
          <div className="auth-stat-row">
            <div className="auth-stat">
              <span>Budget confidence</span>
              <strong>Always on</strong>
            </div>
            <div className="auth-stat">
              <span>Money mood</span>
              <strong>Up only</strong>
            </div>
            <div className="auth-stat">
              <span>Insights</span>
              <strong>Supercharged</strong>
            </div>
          </div>
          <div className="auth-photo-grid">
            <img
              src="https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?auto=format&fit=crop&w=900&q=80"
              alt="Colorful budgeting workspace"
              onError={withFallback}
            />
            <img
              src="https://images.unsplash.com/photo-1553729459-efe14ef6055d?auto=format&fit=crop&w=900&q=80"
              alt="Modern finance workspace"
              onError={withFallback}
            />
            <img
              src="https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?auto=format&fit=crop&w=900&q=80"
              alt="Money and cards closeup"
              onError={withFallback}
            />
          </div>
          <div className="auth-float auth-float-one">SAVE + SLAY</div>
          <div className="auth-float auth-float-two">BUDGET ERA</div>
        </div>
        <div className="auth-card">
          <p className="auth-kicker">{mode === "login" ? "WELCOME BACK" : "GET STARTED"}</p>
          <h1>{mode === "login" ? "Log in and own your numbers." : "Create your financial command center."}</h1>
          <p className="meta">Powerful expense tracking, smarter budgeting, and beautiful analytics.</p>

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
              {loading ? "Please wait..." : mode === "login" ? "Launch Dashboard" : "Create Account"}
            </button>
          </form>

          {message ? <p className="meta">{message}</p> : null}
        </div>
      </div>
      <SiteFooter />
    </div>
  );
}

export default AuthPage;
