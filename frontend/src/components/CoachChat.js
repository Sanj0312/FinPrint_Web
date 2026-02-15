import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";

function formatCoachText(content = "") {
  return String(content)
    .replace(/\r/g, "")
    .replace(/###\s*/g, "\n")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\s+-\s+/g, "\n- ")
    .replace(/\s+(\d+\.)\s+/g, "\n$1 ")
    .replace(/\s{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function CoachChat({ apiBaseUrl, authHeaders }) {
  const [messages, setMessages] = useState([]);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const modelOptions = useMemo(() => models.map((item) => item.id), [models]);

  const loadData = async () => {
    setLoading(true);
    setMessage("");
    try {
      const [historyRes, modelsRes] = await Promise.all([
        axios.get(`${apiBaseUrl}/coach/messages`, { headers: authHeaders }),
        axios.get(`${apiBaseUrl}/blackboard/models`, { headers: authHeaders }),
      ]);
      setMessages(historyRes.data?.messages || []);
      const nextModels = modelsRes.data?.models || [];
      setModels(nextModels);
      if (!selectedModel && nextModels.length > 0) {
        setSelectedModel(nextModels[0].id);
      }
    } catch (error) {
      setMessage(error?.response?.data?.error || "Failed to load coach data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [apiBaseUrl, authHeaders]);

  const sendMessage = async (event) => {
    event.preventDefault();
    if (!input.trim()) {
      setMessage("Please enter a message.");
      return;
    }

    const userMessage = {
      id: `local-${Date.now()}`,
      role: "user",
      content: input.trim(),
      model: "",
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setMessage("");

    try {
      const response = await axios.post(
        `${apiBaseUrl}/coach/messages`,
        { message: userMessage.content, model: selectedModel || undefined },
        { headers: authHeaders }
      );
      const assistant = response.data?.message;
      if (assistant) {
        setMessages((prev) => [...prev, assistant]);
      }
      if (response.data?.provider_error) {
        setMessage(response.data.provider_error);
      }
    } catch (error) {
      setMessage(error?.response?.data?.error || "Failed to send message.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>AI Financial Coach</h2>
      <p className="meta">Stateful coaching powered by Blackboard with memory across your messages.</p>

      <div className="row-actions" style={{ marginBottom: 10 }}>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          disabled={modelOptions.length === 0}
        >
          {modelOptions.length === 0 ? <option value="">No models</option> : null}
          {modelOptions.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
        <button type="button" className="secondary-btn row-action-btn" onClick={loadData}>
          Refresh
        </button>
      </div>

      {message ? <p className="meta">{message}</p> : null}
      {loading ? <p className="meta">Working...</p> : null}

      <div className="list coach-thread">
        {messages.length === 0 ? (
          <p className="meta">No messages yet.</p>
        ) : (
          messages.map((item) => (
            <div
              className={item.role === "assistant" ? "expense-row coach-row assistant" : "expense-row coach-row user"}
              key={item.id}
            >
              <div className="coach-message-block">
                <strong>{item.role === "assistant" ? "Coach" : "You"}</strong>
                <div className={item.role === "assistant" ? "coach-content assistant" : "coach-content"}>
                  {item.role === "assistant" ? formatCoachText(item.content) : item.content}
                </div>
                {item.model ? <div className="meta">Model: {item.model}</div> : null}
              </div>
            </div>
          ))
        )}
      </div>

      <form onSubmit={sendMessage} style={{ marginTop: 12 }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask for weekly plan, spending advice, or savings strategy..."
        />
        <button type="submit" disabled={loading}>
          {loading ? "Sending..." : "Send to Coach"}
        </button>
      </form>
    </div>
  );
}

export default CoachChat;
