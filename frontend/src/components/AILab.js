import React, { useEffect, useState } from "react";
import axios from "axios";

function AILab({ apiBaseUrl, authHeaders }) {
  const [models, setModels] = useState([]);
  const [modelA, setModelA] = useState("");
  const [modelB, setModelB] = useState("");
  const [prompt, setPrompt] = useState(
    "Give me a weekly plan to reduce food and subscriptions spend while keeping quality of life high."
  );
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const loadModels = async () => {
    try {
      const response = await axios.get(`${apiBaseUrl}/blackboard/models`, { headers: authHeaders });
      const next = response.data?.models || [];
      setModels(next);
      if (next.length >= 1 && !modelA) {
        setModelA(next[0].id);
      }
      if (next.length >= 2 && !modelB) {
        setModelB(next[1].id);
      } else if (next.length === 1 && !modelB) {
        setModelB(next[0].id);
      }
    } catch (error) {
      setMessage(error?.response?.data?.error || "Failed to load models.");
    }
  };

  useEffect(() => {
    loadModels();
  }, [apiBaseUrl, authHeaders]);

  const runExperiment = async (event) => {
    event.preventDefault();
    if (!prompt.trim()) {
      setMessage("Prompt is required.");
      return;
    }
    if (!modelA || !modelB) {
      setMessage("Select both models.");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const response = await axios.post(
        `${apiBaseUrl}/ai/experiments`,
        { prompt: prompt.trim(), model_a: modelA, model_b: modelB },
        { headers: authHeaders }
      );
      setResult(response.data);
    } catch (error) {
      setMessage(error?.response?.data?.error || "Experiment failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>AI Lab</h2>
      <p className="meta">Run prompt A/B tests across two Blackboard models and compare outputs.</p>

      <form onSubmit={runExperiment}>
        <div className="summary-grid">
          <div>
            <div className="meta">Model A</div>
            <select value={modelA} onChange={(e) => setModelA(e.target.value)}>
              {models.map((item) => (
                <option key={`a-${item.id}`} value={item.id}>
                  {item.id}
                </option>
              ))}
            </select>
          </div>
          <div>
            <div className="meta">Model B</div>
            <select value={modelB} onChange={(e) => setModelB(e.target.value)}>
              {models.map((item) => (
                <option key={`b-${item.id}`} value={item.id}>
                  {item.id}
                </option>
              ))}
            </select>
          </div>
        </div>

        <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <button type="submit" disabled={loading}>
          {loading ? "Running..." : "Run Experiment"}
        </button>
      </form>

      {message ? <p className="meta">{message}</p> : null}

      {result ? (
        <>
          <h3>Result</h3>
          <p className="meta">Winner: {result.winner || "n/a"}</p>

          <div className="list">
            {(result.outputs || []).map((item) => (
              <div className="expense-row" key={item.model}>
                <div>
                  <strong>{item.model}</strong>
                  <div className="meta">Length: {item.length}</div>
                  <div>{item.output}</div>
                </div>
              </div>
            ))}
          </div>

          {(result.errors || []).length ? (
            <>
              <h3>Errors</h3>
              <div className="list">
                {result.errors.map((item) => (
                  <div className="expense-row" key={`err-${item.model}`}>
                    <span>
                      {item.model}: {item.error}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

export default AILab;
