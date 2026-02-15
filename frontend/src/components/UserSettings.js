import React, { useEffect, useState } from "react";
import axios from "axios";

function UserSettings({ apiBaseUrl, authHeaders, onSettingsUpdated }) {
  const [settings, setSettings] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [accountDetails, setAccountDetails] = useState("");
  const [monthlyBudget, setMonthlyBudget] = useState("");

  const loadSettings = async () => {
    try {
      const response = await axios.get(`${apiBaseUrl}/user_settings`, { headers: authHeaders });
      const data = response.data;
      setSettings(data);
      setName(data?.name || "");
      setEmail(data?.email || "");
      setPhone(data?.phone || "");
      setAccountDetails(data?.account_details || "");
      setMonthlyBudget(data?.monthly_budget != null ? String(data.monthly_budget) : "");
      setError("");
    } catch (err) {
      setError(err?.response?.data?.error || "Unable to load user settings.");
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const saveSettings = async (event) => {
    event.preventDefault();
    setMessage("");
    setError("");

    if (!name.trim() || !email.trim()) {
      setMessage("Name and email are required.");
      return;
    }

    setSaving(true);
    try {
      const response = await axios.put(
        `${apiBaseUrl}/user_settings`,
        {
          name: name.trim(),
          email: email.trim(),
          phone: phone.trim(),
          account_details: accountDetails.trim(),
          monthly_budget: monthlyBudget ? parseFloat(monthlyBudget) : null,
        },
        { headers: authHeaders }
      );

      const data = response.data;
      setSettings(data);
      onSettingsUpdated((prev) => ({ ...(prev || {}), ...data }));
      setMessage("User settings updated.");
    } catch (err) {
      setError(err?.response?.data?.error || "Unable to update user settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h2>User Settings</h2>
      {error ? <p className="meta">{error}</p> : null}
      {!error && !settings ? <p className="meta">Loading user settings...</p> : null}

      <form onSubmit={saveSettings}>
        <input type="text" placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} />
        <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input
          type="text"
          placeholder="Phone number"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <textarea
          className="settings-textarea"
          placeholder="Account details"
          value={accountDetails}
          onChange={(e) => setAccountDetails(e.target.value)}
        />
        <input
          type="number"
          min="0"
          step="0.01"
          placeholder="Budget for this month"
          value={monthlyBudget}
          onChange={(e) => setMonthlyBudget(e.target.value)}
        />

        <button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save Settings"}
        </button>
      </form>

      {settings ? (
        <div className="settings-summary">
          <div className="expense-row">
            <span className="meta">Debits this month ({settings.month})</span>
            <strong>${Number(settings.monthly_debits || 0).toFixed(2)}</strong>
          </div>
        </div>
      ) : null}

      {message ? <p className="meta">{message}</p> : null}
    </div>
  );
}

export default UserSettings;
