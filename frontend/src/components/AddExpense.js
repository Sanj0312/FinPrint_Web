import React, { useState } from "react";
import axios from "axios";

function AddExpense({ apiBaseUrl, onExpenseAdded }) {
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage("");

    if (!name.trim() || !amount) {
      setMessage("Please provide both expense name and amount.");
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`${apiBaseUrl}/add_expense`, {
        name: name.trim(),
        amount: parseFloat(amount),
      });

      setName("");
      setAmount("");
      setMessage("Expense added successfully.");
      await onExpenseAdded();
    } catch (error) {
      setMessage(error?.response?.data?.error || "Failed to add expense.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h2>Add Expense</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Expense name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          type="number"
          placeholder="Amount"
          min="0"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <button type="submit" disabled={submitting}>
          {submitting ? "Adding..." : "Add Expense"}
        </button>
      </form>
      {message ? <p className="meta">{message}</p> : null}
    </div>
  );
}

export default AddExpense;
