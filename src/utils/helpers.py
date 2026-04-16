# src/utils/helpers.py
"""
Вспомогательные функции для проекта.
"""

from datetime import datetime

def inject_datetime() -> str:
    """
    Возвращает строку с текущей датой/временем для инжекта в промпт.
    
    :return: Строка вида "📅 Текущая дата: 5 апреля 2026 года, 17:45"
    """
    now = datetime.now()
    # Русское название месяца
    months = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    month_ru = months.get(now.month, "месяца")
    return f"📅 Текущая дата и время: {now.day} {month_ru} {now.year} года, {now.hour:02d}:{now.minute:02d}"


def parse_agent_id(text: str) -> str:
    """
    Извлекает ID агента из текста (agent_N, агент_1, etc.)
    
    :param text: Произвольный текст
    :return: Нормализованный ID вида "agent_N" или "unknown"
    """
    import re
    # Ищем pattern: agent_1, агент2, agent 3, etc.
    match = re.search(r'(?:agent|агент)[_\s]?(\d+)', text.lower())
    if match:
        return f"agent_{match.group(1)}"
    
    # Special cases
    if any(word in text.lower() for word in ["no_one", "никого", "не голосую"]):
        return "no_one"
    
    return "unknown"