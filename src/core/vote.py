# src/core/vote.py
"""
Vote — структурированный результат голосования агента.

Используется для:
• Чёткого парсинга ответов LLM
• Подсчёта итогов (с учётом веса голоса)
• Сохранения истории в JSON/CSV
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Literal

# Типы возможных выборов
VoteChoice = Literal["no_one", "eliminate", "agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]

@dataclass
class Vote:
    """
    Результат голосования одного агента.
    """
    agent_id: str              # Кто голосовал
    choice: str                # За кого/что проголосовал ("agent_2", "no_one", etc.)
    reason: str                # Обоснование выбора
    weight: float = 1.0        # Вес голоса (для расширения механики)
    timestamp: datetime = field(default_factory=datetime.now)
    round_id: int = 0          # Номер раунда (для истории)
    meta : dict = field(default_factory=dict)  # Доп. данные (тема, контекст)
    
    @property
    def is_valid(self) -> bool:
        """Проверка: голос не пустой и не ошибка парсинга"""
        return bool(self.choice and self.choice not in ["parse_error", "", None])
    
    @property
    def effective_weight(self) -> float:
        """Итоговый вес: базовый * множитель агента (если будет)"""
        # Пока просто возвращаем weight, позже можно добавить Agent.voting_power
        return self.weight
    
    def to_dict(self) -> dict:
        """Экспорт в словарь (для JSON/CSV)"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "Vote":
        """Импорт из словаря (при загрузке сохранения)"""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
    
    def __str__(self) -> str:
        """Читаемый вывод для логов/интерфейса"""
        emoji = "✅" if self.choice != "no_one" else "⚪"
        return f"{emoji} {self.agent_id}: {self.choice} — {self.reason[:60]}..."