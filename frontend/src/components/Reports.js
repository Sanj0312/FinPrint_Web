import React, { useEffect, useState } from "react";
import axios from "axios";
import jsPDF from "jspdf";
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

const money = (value) => `$${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function Reports({ apiBaseUrl, authHeaders, compact = false }) {
  const [report, setReport] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [showDataset, setShowDataset] = useState(!compact);
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

  const downloadPdfReport = () => {
    if (!report && !dataset) {
      setMessage("No report data available for PDF download.");
      return;
    }

    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 48;
    const contentWidth = pageWidth - margin * 2;
    let y = margin;

    const ensureSpace = (needed = 24) => {
      if (y + needed > pageHeight - margin) {
        doc.addPage();
        y = margin;
      }
    };

    const addHeading = (text) => {
      ensureSpace(30);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(15);
      doc.text(text, margin, y);
      y += 22;
    };

    const addLine = (text, size = 11, bold = false) => {
      doc.setFont("helvetica", bold ? "bold" : "normal");
      doc.setFontSize(size);
      const lines = doc.splitTextToSize(String(text), contentWidth);
      const lineHeight = size + 5;
      ensureSpace(lines.length * lineHeight + 8);
      doc.text(lines, margin, y);
      y += lines.length * lineHeight + 4;
    };

    const addSectionGap = () => {
      y += 8;
    };

    doc.setFillColor(18, 30, 60);
    doc.rect(0, 0, pageWidth, 84, "F");
    doc.setTextColor(238, 245, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(24);
    doc.text("FinPrint by Fynx", margin, 42);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(11);
    doc.text("Expense, Budget & Profit Opportunity Report", margin, 62);

    y = 110;
    doc.setTextColor(32, 42, 67);

    addHeading("1) Monthly Snapshot");
    if (report) {
      addLine(`Month: ${report.month || "N/A"}`);
      addLine(`Total Spending: ${money(report.total_spending)}`);
      addLine(`Daily Average: ${money(report.daily_average)}`);
      addLine(
        `Budget Remaining: ${
          report.budget_remaining === null || report.budget_remaining === undefined
            ? "No budget set"
            : money(report.budget_remaining)
        }`
      );
    } else {
      addLine("Monthly report data is not available.");
    }

    addSectionGap();
    addHeading("2) Category Breakdown");
    const categoryEntries = Object.entries(report?.spending_per_category || {});
    if (categoryEntries.length === 0) {
      addLine("No category spending data available.");
    } else {
      categoryEntries
        .sort((a, b) => Number(b[1]) - Number(a[1]))
        .forEach(([category, amount], index) => {
          addLine(`${index + 1}. ${category}: ${money(amount)}`);
        });
    }

    addSectionGap();
    addHeading("3) Dataset Analytics");
    if (dataset) {
      addLine(`Records: ${dataset.rows || 0}`);
      addLine(`Total Income: ${money(dataset.total_income)}`);
      addLine(`Total Expense: ${money(dataset.total_expense)}`);
      addLine(`Net Balance: ${money(dataset.net_balance)}`);

      const topCategories = (dataset.top_categories || []).slice(0, 5);
      if (topCategories.length > 0) {
        addLine("Top Expense Categories:", 11, true);
        topCategories.forEach((item, index) => addLine(`- ${index + 1}. ${item.name}: ${money(item.value)}`));
      }
    } else {
      addLine("Dataset analytics are not available.");
    }

    addSectionGap();
    addHeading("4) Profit Opportunity (Savings Plan)");
    const sortedForSavings = categoryEntries
      .map(([name, value]) => ({ name, value: Number(value) || 0 }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 3);
    const savingsPotential = sortedForSavings.reduce((sum, item) => sum + item.value * 0.1, 0);

    if (sortedForSavings.length === 0) {
      addLine("Not enough spending data to estimate savings opportunities.");
    } else {
      addLine("If you reduce the top 3 spending categories by 10%, estimated monthly savings could be:", 11);
      addLine(`${money(savingsPotential)}`, 14, true);
      addLine("Focus Categories:", 11, true);
      sortedForSavings.forEach((item, index) => addLine(`- ${index + 1}. ${item.name}: ${money(item.value)}`));
    }

    ensureSpace(40);
    doc.setTextColor(110, 120, 145);
    doc.setFont("helvetica", "italic");
    doc.setFontSize(10);
    doc.text(`Generated on ${new Date().toLocaleString()}`, margin, pageHeight - 30);

    const fileMonth = report?.month || "report";
    doc.save(`FinPrint_Report_${fileMonth}.pdf`);
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
              <strong>{money(report.total_spending)}</strong>
            </div>
          </div>

          <div className="expense-row">
            <div>
              <div className="meta">Daily Average</div>
              <strong>{money(report.daily_average)}</strong>
            </div>
          </div>

          <div className="expense-row">
            <div>
              <div className="meta">Budget Remaining</div>
              <strong>
                {report.budget_remaining === null
                  ? "No budget set"
                  : money(report.budget_remaining)}
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
                <strong>{money(amount)}</strong>
              </div>
            ))}
          </div>
        </>
      ) : null}

      {dataset ? (
        <div className="dataset-analytics">
          <div className="drawer-header" style={{ marginBottom: 8 }}>
            <h3>Dataset Analytics</h3>
            {compact ? (
              <button className="secondary-btn" type="button" onClick={() => setShowDataset((prev) => !prev)}>
                {showDataset ? "Hide" : "Show"}
              </button>
            ) : null}
          </div>
          {!showDataset ? (
            <p className="meta">Dataset analytics hidden to keep this dashboard compact.</p>
          ) : null}
          {showDataset ? (
            <>
              <p className="meta">
                Source: <strong>us_expense_dataset_large.csv</strong> | Records: {dataset.rows}
              </p>

              <div className="kpi-grid">
                <div className="kpi-card income">
                  <span>Total Income</span>
                  <strong>{money(dataset.total_income)}</strong>
                </div>
                <div className="kpi-card expense">
                  <span>Total Expense</span>
                  <strong>{money(dataset.total_expense)}</strong>
                </div>
                <div className="kpi-card net">
                  <span>Net Balance</span>
                  <strong>{money(dataset.net_balance)}</strong>
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
                        <Tooltip formatter={(value) => money(value)} />
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
                        <Tooltip formatter={(value) => money(value)} />
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
                        <Tooltip formatter={(value) => money(value)} />
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
                    <strong>{money(item.value)}</strong>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </div>
      ) : null}

      <div className="row-actions" style={{ justifyContent: "flex-start", marginTop: 14 }}>
        <button type="button" className="secondary-btn" onClick={downloadPdfReport}>
          Download PDF Report
        </button>
      </div>
    </div>
  );
}

export default Reports;
