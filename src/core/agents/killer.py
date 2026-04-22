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
# from ...utils.helpers import inject_datetime

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
    # 🔧 ФИКС: убираем себя из списка возможных жертв
    valid_targets = [a for a in alive_agents if a != self.config.agent_id]
    
    if not valid_targets:
        return "no_one"  # Нечего устранять
    
    prompt = f"""
🌙 НОЧЬ. Ты — Мафия.

Живые агенты (можно устранить): {', '.join(valid_targets)}
⚠️ Ты НЕ можешь устранить себя.

{f"Твои наблюдения:\n{memory_context}" if memory_context else ""}

ИНСТРУКЦИЯ:
Выбери ОДНУ жертву для устранения.
• Приоритет: те, кто тебя подозревал в дебатах

Ответь ТОЛЬКО ID в формате: agent_N
Пример: agent_3

Твой выбор:"""
    
    target_raw = self.think(prompt).strip()
    
    # 🔧 ФИКС: передаём exclude_self в парсер
    target = parse_agent_id(target_raw, exclude_self=self.config.agent_id)
    
    # Валидация: если парсер вернул invalid — берём первого из списка
    if target in ["parse_error", "unknown_agent", "no_one", None]:
        target = valid_targets[0]
    
    self.night_target = target
        # Запрос к модели
    self.night_target = target
    
    # Сохраняем в память
    self.memory.add(MemoryItem(
        event_type="night_action",
        content=f"🔪 Ночью устранил: {target}",
        metadata={"phase": "night", "action": "eliminate", "target": target}
    ))
    
    return target