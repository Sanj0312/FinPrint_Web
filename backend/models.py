from dataclasses import dataclass


@dataclass
class Expense:
    id: int
    name: str
    amount: float
    category: str
    timestamp: str

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "amount": self.amount,
            "category": self.category,
            "timestamp": self.timestamp,
        }
