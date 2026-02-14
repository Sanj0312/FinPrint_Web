import React from "react";

function ExpenseList({ expenses }) {
  return (
    <div>
      <h2>Expense List</h2>
      {expenses.length === 0 ? (
        <p className="meta">No expenses found.</p>
      ) : (
        <div className="list">
          {expenses.map((expense) => (
            <div className="expense-row" key={expense.id}>
              <div>
                <strong>{expense.name}</strong>
                <div className="meta">{new Date(expense.timestamp).toLocaleString()}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div>${Number(expense.amount).toFixed(2)}</div>
                <span className="badge">{expense.category}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ExpenseList;
