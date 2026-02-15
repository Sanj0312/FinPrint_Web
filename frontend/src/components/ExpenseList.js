import React, { useState } from "react";

function ExpenseList({ expenses, onDeleteExpense, onUpdateExpense }) {
  const [editingId, setEditingId] = useState(null);
  const [draftName, setDraftName] = useState("");
  const [draftAmount, setDraftAmount] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [message, setMessage] = useState("");

  const startEdit = (expense) => {
    setEditingId(expense.id);
    setDraftName(expense.name);
    setDraftAmount(String(expense.amount));
    setMessage("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setDraftName("");
    setDraftAmount("");
  };

  const handleSave = async (expenseId) => {
    if (!draftName.trim() || !draftAmount) {
      setMessage("Please provide both expense name and amount.");
      return;
    }

    setBusyId(expenseId);
    setMessage("");
    try {
      await onUpdateExpense(expenseId, {
        name: draftName.trim(),
        amount: parseFloat(draftAmount),
      });
      setMessage("Expense updated.");
      cancelEdit();
    } catch (error) {
      setMessage(error?.response?.data?.error || "Failed to update expense.");
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (expenseId) => {
    setBusyId(expenseId);
    setMessage("");
    try {
      await onDeleteExpense(expenseId);
      setMessage("Expense deleted.");
      if (editingId === expenseId) {
        cancelEdit();
      }
    } catch (error) {
      setMessage(error?.response?.data?.error || "Failed to delete expense.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <h2>Expense List</h2>
      {message ? <p className="meta">{message}</p> : null}
      {expenses.length === 0 ? (
        <p className="meta">No expenses found.</p>
      ) : (
        <div className="list">
          {expenses.map((expense) => (
            <div className="expense-row" key={expense.id}>
              <div className="expense-row-main">
                {editingId === expense.id ? (
                  <div className="expense-edit-fields">
                    <input
                      type="text"
                      value={draftName}
                      onChange={(e) => setDraftName(e.target.value)}
                      placeholder="Expense name"
                    />
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={draftAmount}
                      onChange={(e) => setDraftAmount(e.target.value)}
                      placeholder="Amount"
                    />
                  </div>
                ) : (
                  <strong>{expense.name}</strong>
                )}
                <div className="meta">{new Date(expense.timestamp).toLocaleString()}</div>
              </div>
              <div className="expense-row-side">
                <div>${Number(expense.amount).toFixed(2)}</div>
                <span className="badge">{expense.category}</span>
                {expense.source === "csv" ? <span className="badge badge-muted">CSV</span> : null}
                {expense.can_edit ? (
                  <div className="row-actions">
                    {editingId === expense.id ? (
                      <>
                        <button
                          type="button"
                          className="secondary-btn row-action-btn"
                          onClick={() => cancelEdit()}
                          disabled={busyId === expense.id}
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          className="row-action-btn"
                          onClick={() => handleSave(expense.id)}
                          disabled={busyId === expense.id}
                        >
                          {busyId === expense.id ? "Saving..." : "Save"}
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="secondary-btn row-action-btn"
                          onClick={() => startEdit(expense)}
                          disabled={busyId === expense.id}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="danger-btn row-action-btn"
                          onClick={() => handleDelete(expense.id)}
                          disabled={busyId === expense.id}
                        >
                          {busyId === expense.id ? "Deleting..." : "Delete"}
                        </button>
                      </>
                    )}
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ExpenseList;
