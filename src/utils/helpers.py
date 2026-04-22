from typing import Optional


def parse_agent_id(text: str, exclude_self: Optional[str] = None) -> str:
    """
    Извлекает и валидирует ID агента из текста.
    
    :param text: Произвольный текст ответа модели
    :param exclude_self: Если указан — не возвращать этот ID (для Killer)
    :return: Нормализованный ID вида "agent_N" или "no_one"/"unknown"
    """
    import re
    text_lower = text.lower().strip()
    
    # 1. Проверка на "никого"
    if any(phrase in text_lower for phrase in ["no_one", "никого", "не голосую", "отказываюсь", "нет цели"]):
        return "no_one"
    
    # 2. Поиск паттерна: agent_1, агент2, agent 3, #1, etc.
    patterns = [
        r'agent[_\s]?(\d+)',      # agent_1, agent 2
        r'агент[_\s]?(\d+)',       # агент_1, агент 2
        r'#(\d+)',                 # #1, #2
        r'номер[_\s]?(\d+)',       # номер 1
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            candidate = f"agent_{match.group(1)}"
            # Исключаем себя, если нужно (для Killer)
            if exclude_self and candidate == exclude_self:
                continue
            return candidate
    
    # 3. Fallback: ищем любое упоминание agent в контексте
    if "agent" in text_lower or "агент" in text_lower:
        # Возвращаем неизвестный, но валидный формат
        return "unknown_agent"
    
    return "parse_error"
