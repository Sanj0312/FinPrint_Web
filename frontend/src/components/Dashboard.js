import React from "react";

function Dashboard({ summary }) {
  const categories = Object.entries(summary.spending_per_category || {}).sort((a, b) => b[1] - a[1]);

  return (
    <div>
      <h2>Dashboard Analytics</h2>
      <div className="summary-grid">
        <div className="expense-row">
          <div>
            <div className="meta">Total Spending</div>
            <strong>${Number(summary.total_spending || 0).toFixed(2)}</strong>
          </div>
        </div>

        <div className="expense-row">
          <div>
            <div className="meta">Categories</div>
            <strong>{categories.length}</strong>
          </div>
        </div>
      </div>

      <h3>Spending by Category</h3>
      {categories.length === 0 ? (
        <p className="meta">No category data available yet.</p>
      ) : (
        <div className="list compact-list">
          {categories.slice(0, 7).map(([category, amount]) => (
            <div className="expense-row" key={category}>
              <span>{category}</span>
              <strong>${Number(amount).toFixed(2)}</strong>
            </div>
          ))}
        </div>
      )}

      <h3>Gemini Insights</h3>
      <div className="insight">{summary.ai_insight || "No insights available."}</div>
    </div>
  );
}

export default Dashboard;
