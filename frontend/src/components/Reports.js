import React, { useEffect, useState } from "react";
import axios from "axios";

function Reports({ apiBaseUrl, authHeaders }) {
  const [report, setReport] = useState(null);
  const [budgetAmount, setBudgetAmount] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const loadReports = async () => {
    setLoading(true);
    setMessage("");
    try {
      const response = await axios.get(`${apiBaseUrl}/reports`, { headers: authHeaders });
      setReport(response.data);
      if (response.data?.budget) {
        setBudgetAmount(String(response.data.budget));
      }
    } catch (error) {
      setMessage(error?.response?.data?.error || "Unable to load reports.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const saveBudget = async (event) => {
    event.preventDefault();
    setMessage("");

    try {
      await axios.put(
        `${apiBaseUrl}/budget/current`,
        { amount: parseFloat(budgetAmount) },
        { headers: authHeaders }
      );
      setMessage("Budget saved.");
      await loadReports();
    } catch (error) {
      setMessage(error?.response?.data?.error || "Unable to save budget.");
    }
  };

  return (
    <div>
      <h2>Reports & Budgeting</h2>
      {loading ? <p className="meta">Loading report...</p> : null}
      {message ? <p className="meta">{message}</p> : null}

      <form onSubmit={saveBudget}>
        <input
          type="number"
          min="0"
          step="0.01"
          placeholder="Monthly budget"
          value={budgetAmount}
          onChange={(e) => setBudgetAmount(e.target.value)}
        />
        <button type="submit">Save Budget</button>
      </form>

      {report ? (
        <div className="summary-grid" style={{ marginTop: 12 }}>
          <div className="expense-row">
            <div>
              <div className="meta">Month</div>
              <strong>{report.month}</strong>
            </div>
          </div>

          <div className="expense-row">
            <div>
              <div className="meta">Total Spending</div>
              <strong>${Number(report.total_spending || 0).toFixed(2)}</strong>
            </div>
          </div>

          <div className="expense-row">
            <div>
              <div className="meta">Daily Average</div>
              <strong>${Number(report.daily_average || 0).toFixed(2)}</strong>
            </div>
          </div>

          <div className="expense-row">
            <div>
              <div className="meta">Budget Remaining</div>
              <strong>
                {report.budget_remaining === null
                  ? "No budget set"
                  : `$${Number(report.budget_remaining).toFixed(2)}`}
              </strong>
            </div>
          </div>
        </div>
      ) : null}

      {report?.spending_per_category ? (
        <>
          <h3>Category Breakdown</h3>
          <div className="list">
            {Object.entries(report.spending_per_category).map(([category, amount]) => (
              <div className="expense-row" key={category}>
                <span>{category}</span>
                <strong>${Number(amount).toFixed(2)}</strong>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

export default Reports;
