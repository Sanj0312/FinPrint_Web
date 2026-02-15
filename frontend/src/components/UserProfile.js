import React, { useEffect, useState } from "react";
import axios from "axios";

function UserProfile({ apiBaseUrl, authHeaders, onProfileUpdated }) {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${apiBaseUrl}/user_profile`, { headers: authHeaders });
      const data = response.data;
      setProfile(data);
      setName(data?.name || "");
      setEmail(data?.email || "");
      setError("");
    } catch (err) {
      setError(err?.response?.data?.error || "Unable to fetch user profile.");
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const saveProfile = async (event) => {
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
        `${apiBaseUrl}/user_profile`,
        {
          name: name.trim(),
          email: email.trim(),
        },
        { headers: authHeaders }
      );
      setProfile((previous) => ({ ...(previous || {}), ...response.data }));
      onProfileUpdated((prev) => ({ ...(prev || {}), ...response.data }));
      setMessage("Profile updated.");
    } catch (err) {
      setError(err?.response?.data?.error || "Unable to update profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h2>User Profile</h2>
      {error ? <p className="meta">{error}</p> : null}
      {!error && !profile ? <p className="meta">Loading profile...</p> : null}
      <form onSubmit={saveProfile}>
        <input
          type="text"
          placeholder="Full name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save Profile"}
        </button>
      </form>
      {message ? <p className="meta">{message}</p> : null}
    </div>
  );
}

export default UserProfile;
