# src/core/agents/killer.py
"""
KillerAgent — Мафия.

Поведение:
• Лжёт и запутывает в дебатах
• Голосует против тех, кто его подозревает
• Ночью выбирает жертву для устранения
"""

from typing import List, Dict, Optional
from ..agent import Agent, AgentConfig
from ..llm_client import LLMClient
from ..memory import MemoryItem
from ..vote import Vote
from ...utils.helpers import inject_datetime

class KillerAgent(Agent):
    """Мафия: манипулирует, лжёт, устраняет ночью."""
    
    def __init__(self, config: AgentConfig, llm_client: LLMClient):
        super().__init__(config, llm_client)
        self.night_target: Optional[str] = None  # Кого устранил этой ночью
    
    def _build_system_prompt(self) -> str:
        """Роль Мафии: скрытная и манипулятивная"""
        return f"""Ты — Мафия (агент {self.config.agent_id}) в игре Мафия.

Твои цели:
• Оставаться незамеченным среди гражданских
• Устранять подозрительных игроков ночью
• Манипулировать голосованием в свою пользу

Правила поведения:
• В дебатах: лги, запутывай, перекладывай подозрения на других
• Никогда не признавайся, что ты Мафия
• Голосуй против тех, кто задаёт неудобные вопросы
• Если тебя прямо обвиняют — защищайся эмоционально, но правдоподобно

{inject_datetime()}
Отвечай на русском, от первого лица, кратко (2-4 предложения)."""
    
    def _format_debate_prompt(self, topic: str, context: List[Dict]) -> str:
        """Промпт для дебатов: акцент на манипуляции"""
        context_text = "\n".join([
            f"• {entry['agent']}: {entry['text']}" 
            for entry in context[-4:]
        ]) if context else "• Пока никто не высказался."
        
        # Анализируем: кто нас подозревает?
        suspicious = [
            entry['agent'] for entry in context 
            if any(word in entry['text'].lower() for word in ["подозреваю", "мафия", "странно", "ложь"])
        ]
        
        return f"""
🗣️ Дебаты по теме: "{topic}"

Сказанное другими:
{context_text}

⚠️ Внимание: тебя могут подозревать! {f"Подозрительные: {', '.join(suspicious)}" if suspicious else "Пока все спокойны."}

Твоя задача как Мафии:
1. Отвлеки внимание: переведи тему или обвини другого
2. Если тебя обвиняют — защищайся, но не агрессивно
3. Создай впечатление, что ты «просто гражданский»

Твой ответ (будь хитрым, но правдоподобным):"""
    
    def night_action(self, alive_agents: List[str], memory_context: str = "") -> str:
        """
        Ночное действие: выбор жертвы.
        
        :param alive_agents: Список ID живых агентов (кроме себя)
        :param memory_context: Контекст из памяти для принятия решения
        :return: ID агента для устранения
        """
        # Формируем промпт с контекстом
        prompt = f"""
🌙 НОЧЬ. Ты — Мафия.

Живые агенты (можно устранить): {', '.join(alive_agents)}

{f"Твои наблюдения из памяти:\n{memory_context}" if memory_context else ""}

ИНСТРУКЦИЯ:
Выбери ОДНУ жертву для устранения.
• Приоритет: те, кто тебя подозревал в дебатах
• Избегай: тех, кто тебя защищал (возможные союзники)

Ответь ТОЛЬКО ID агента в формате: agent_N
Пример: agent_3

Твой выбор:"""
        
        # Запрос к модели
        target = self.think(prompt).strip().lower()
        
        # Парсинг: извлекаем agent_N
        import re
        match = re.search(r'agent[_\s]?(\d+)', target)
        if match:
            target = f"agent_{match.group(1)}"
        else:
            # Fallback: первый из списка
            target = alive_agents[0] if alive_agents else "unknown"
        
        # Проверяем, что цель жива и не мы сами
        if target not in alive_agents:
            target = alive_agents[0] if alive_agents else "unknown"
        
        self.night_target = target
        
        # Сохраняем в память
        self.memory.add(MemoryItem(
            event_type="night_action",
            content=f"🔪 Ночью устранил: {target}",
            metadata={"phase": "night", "action": "eliminate", "target": target}
        ))
        
        return target