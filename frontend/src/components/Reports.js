import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  LineChart,
  Line,
  Legend,
} from "recharts";

const CHART_COLORS = ["#2ad1a3", "#2cb5f8", "#ffd166", "#ff8a5b", "#8ec5ff", "#7c91ff", "#6fd4ff", "#63e6be"];

function Reports({ apiBaseUrl, authHeaders }) {
  const [report, setReport] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [budgetAmount, setBudgetAmount] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const loadReports = async () => {
    setLoading(true);
    setMessage("");
    try {
      const [reportRes, datasetRes] = await Promise.all([
        axios.get(`${apiBaseUrl}/reports`, { headers: authHeaders }),
        axios.get(`${apiBaseUrl}/dataset_analytics`, { headers: authHeaders }),
      ]);
      setReport(reportRes.data);
      setDataset(datasetRes.data);
      if (reportRes.data?.budget) {
        setBudgetAmount(String(reportRes.data.budget));
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

      {dataset ? (
        <div className="dataset-analytics">
          <h3>Dataset Analytics</h3>
          <p className="meta">
            Source: <strong>us_expense_dataset_large.csv</strong> | Records: {dataset.rows}
          </p>

          <div className="kpi-grid">
            <div className="kpi-card income">
              <span>Total Income</span>
              <strong>
                ${Number(dataset.total_income || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </strong>
            </div>
            <div className="kpi-card expense">
              <span>Total Expense</span>
              <strong>
                ${Number(dataset.total_expense || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </strong>
            </div>
            <div className="kpi-card net">
              <span>Net Balance</span>
              <strong>
                ${Number(dataset.net_balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </strong>
            </div>
          </div>

          <div className="chart-grid">
            <div className="chart-card">
              <h4>Category Split</h4>
              <div className="chart-box">
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={dataset.top_categories || []}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      label
                    >
                      {(dataset.top_categories || []).map((entry, index) => (
                        <Cell key={`cat-${entry.name}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => `$${Number(value).toFixed(2)}`} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="chart-card">
              <h4>Top Subcategories</h4>
              <div className="chart-box">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={dataset.top_subcategories || []} layout="vertical" margin={{ left: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(147,168,208,0.2)" />
                    <XAxis type="number" stroke="#9fb0cf" />
                    <YAxis dataKey="name" type="category" stroke="#9fb0cf" width={110} />
                    <Tooltip formatter={(value) => `$${Number(value).toFixed(2)}`} />
                    <Bar dataKey="value" fill="#2cb5f8" radius={[0, 8, 8, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="chart-card chart-card-wide">
              <h4>Monthly Income vs Expense</h4>
              <div className="chart-box">
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={dataset.monthly_trend || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(147,168,208,0.2)" />
                    <XAxis dataKey="month" stroke="#9fb0cf" />
                    <YAxis stroke="#9fb0cf" />
                    <Tooltip formatter={(value) => `$${Number(value).toFixed(2)}`} />
                    <Legend />
                    <Line type="monotone" dataKey="income" stroke="#2ad1a3" strokeWidth={3} dot={false} />
                    <Line type="monotone" dataKey="expense" stroke="#ff8a5b" strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <h4>Top Accounts by Spend</h4>
          <div className="list">
            {(dataset.top_accounts || []).map((item) => (
              <div className="expense-row" key={item.name}>
                <span>{item.name}</span>
                <strong>${Number(item.value).toFixed(2)}</strong>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default Reports;
