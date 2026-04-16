# src/core/memory.py
"""
MemoryBank — система памяти для агента.

Хранит:
• Личные события (что агент сам делал/говорил)
• Социальные события (что агент знает о других)

Поддерживает:
• Ограничение по количеству записей (чтобы не раздувать контекст)
• Фильтрацию по типу события
• Экспорт в промпт-формат
"""

import logging
from typing import Optional, List, Dict, Literal
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# Типы событий в памяти
EventType = Literal["debate", "vote", "night_action", "observation", "system"]

@dataclass
class MemoryItem:
    """
    Одна запись в памяти агента.
    """
    event_type: EventType
    content: str  # Текст события (реплика, решение, наблюдение)
    timestamp: datetime = field(default_factory=datetime.now)
    target_agent: Optional[str] = None  # Если событие касается другого агента
    metadata: Dict = field(default_factory=dict)  # Доп. данные (тема, результат и т.д.)
    
    def to_prompt_format(self) -> str:
        """
        Преобразует запись в строку для вставки в промпт.
        Пример: "[2026-04-04 14:30] [debate] Маг: 'Я считаю, что...'"
        """
        time_str = self.timestamp.strftime("%H:%M")
        target = f" → {self.target_agent}" if self.target_agent else ""
        return f"[{time_str}] [{self.event_type}{target}] {self.content}"


class MemoryBank:
    """
    Хранилище памяти для одного агента.
    
    Разделяет память на:
    • personal: собственные действия агента
    • social: наблюдения за другими агентами
    """
    
    def __init__(self, max_personal: int = 30, max_social_per_agent: int = 10):
        """
        :param max_personal: Макс. записей личной памяти (deque автоматически удалит старые)
        :param max_social_per_agent: Макс. записей о каждом другом агенте
        """
        self.max_personal = max_personal
        self.max_social_per_agent = max_social_per_agent
        
        # Личная память: очередь с ограничением
        self.personal: deque[MemoryItem] = deque(maxlen=max_personal)
        
        # Социальная память: словарь агент → очередь событий
        self.social: Dict[str, deque[MemoryItem]] = defaultdict(
            lambda: deque(maxlen=max_social_per_agent)
        )
        
        logger.info(f"🧠 MemoryBank создан (личная: {max_personal}, социальная: {max_social_per_agent}/агент)")
    
    def add(self, event: MemoryItem, about_agent: Optional[str] = None):
        """
        Добавляет событие в память.
        
        :param event: Объект MemoryItem
        :param about_agent: Если событие о другом агенте — укажи его ID
        """
        if about_agent:
            # Социальная память: что агент знает о других
            self.social[about_agent].append(event)
            logger.debug(f"📝 Соц. память (+{about_agent}): {event.content[:50]}...")
        else:
            # Личная память: собственные действия
            self.personal.append(event)
            logger.debug(f"📝 Личная память: {event.content[:50]}...")
    
    def get_recent(
        self, 
        limit: int = 10, 
        event_type: Optional[EventType] = None,
        about_agent: Optional[str] = None
    ) -> List[MemoryItem]:
        """
        Получает последние события из памяти.
        
        :param limit: Макс. количество записей
        :param event_type: Фильтр по типу (None = все типы)
        :param about_agent: Если указан — возвращает только события об этом агенте
        :return: Список MemoryItem (от старых к новым)
        """
        if about_agent:
            # Берём из социальной памяти
            source = self.social.get(about_agent, deque())
        else:
            # Берём из личной памяти
            source = self.personal
        
        # Фильтруем по типу события, если нужно
        filtered = [e for e in source if event_type is None or e.event_type == event_type]
        
        # Возвращаем последние `limit` записей (от старых к новым для контекста)
        return list(filtered)[-limit:]
    
    def to_prompt_context(
        self, 
        limit: int = 10,
        include_social: bool = True,
        about_agents: Optional[List[str]] = None
    ) -> str:
        """
        Формирует текстовый контекст из памяти для вставки в промпт.
        
        :param limit: Общее ограничение записей
        :param include_social: Включать ли наблюдения за другими
        :param about_agents: Если указано — включить память только об этих агентах
        :return: Строка для вставки в промпт
        """
        lines = []
        
        # 1. Личная память
        personal = self.get_recent(limit // 2)
        for item in personal:
            lines.append(f"• {item.to_prompt_format()}")
        
        # 2. Социальная память (если включено)
        if include_social:
            agents_to_check = about_agents or list(self.social.keys())
            for agent_id in agents_to_check:
                social_events = self.get_recent(limit // len(agents_to_check) if agents_to_check else limit, about_agent=agent_id)
                for item in social_events:
                    lines.append(f"• {item.to_prompt_format()}")
        
        if not lines:
            return "📭 Память пуста (это первое действие)."
        
        # Собираем в блок
        return "🧭 Контекст из памяти:\n" + "\n".join(lines)
    
    def export(self) -> Dict:
        """Экспорт памяти в словарь (для сохранения в JSON)."""
        return {
            "personal": [asdict(e) for e in self.personal],
            "social": {k: [asdict(e) for e in v] for k, v in self.social.items()}
        }
    
    def import_data(self, data: Dict):
        """Импорт памяти из словаря (при загрузке сохранения)."""
        # Очистка
        self.personal.clear()
        self.social.clear()
        
        # Восстановление личной памяти
        for item in data.get("personal", []):
            self.personal.append(MemoryItem(**item))
        
        # Восстановление социальной памяти
        for agent_id, events in data.get("social", {}).items():
            for item in events:
                self.social[agent_id].append(MemoryItem(**item))
        
        logger.info(f"💾 Память загружена: {len(self.personal)} личных, {sum(len(v) for v in self.social.values())} социальных записей")