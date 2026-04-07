# src/core/agents/doctor.py
"""
DoctorAgent — Доктор.

Поведение:
• Пытается угадать, кого атакует Мафия
• Лечит одного агента ночью (может ошибиться)
• В дебатах ведёт себя как гражданский, но более осторожно
"""

from typing import List, Dict, Optional
from ..agent import Agent, AgentConfig
from ..llm_client import LLMClient
from ..memory import MemoryItem
from ..vote import Vote
from ...utils.helpers import inject_datetime

class DoctorAgent(Agent):
    """Доктор: лечит ночью, анализирует днём."""
    
    def __init__(self, config: AgentConfig, llm_client: LLMClient):
        super().__init__(config, llm_client)
        self.night_save_target: Optional[str] = None  # Кого пытался спасти
    
    def _build_system_prompt(self) -> str:
        """Роль Доктора: осторожный аналитик"""
        return f"""Ты — Доктор (агент {self.config.agent_id}) в игре Мафия.

Твои цели:
• Спасать гражданских от ночных атак Мафии
• Выявлять Мафию через наблюдение за поведением
• Не раскрывать свою роль раньше времени

Правила поведения:
• В дебатах: анализируй факты, задавай уточняющие вопросы
• Будь осторожен в обвинениях — ошибка может стоить жизни
• Ночью: интуитивно выбирай, кого защитить

{inject_datetime()}
Отвечай на русском, от первого лица, кратко (2-4 предложения)."""
    
    def _format_debate_prompt(self, topic: str, context: List[Dict]) -> str:
        """Промпт для дебатов: акцент на анализе"""
        context_text = "\n".join([
            f"• {entry['agent']}: {entry['text']}" 
            for entry in context[-4:]
        ]) if context else "• Пока никто не высказался."
        
        return f"""
🗣️ Дебаты по теме: "{topic}"

Сказанное другими:
{context_text}

Твоя задача как Доктора:
1. Проанализируй: кто ведёт себя подозрительно? Кто слишком агрессивен?
2. Задай уточняющий вопрос или вырази осторожное сомнение
3. Не раскрывай, что ты Доктор — это опасно!

Твой ответ:"""
    
    def night_action(self, alive_agents: List[str], memory_context: str = "") -> str:
        """
        Ночное действие: выбор агента для лечения.
        
        :param alive_agents: Список ID живых агентов (можно лечить себя)
        :param memory_context: Контекст из памяти для решения
        :return: ID агента, которого пытался спасти
        """
        prompt = f"""
🌙 НОЧЬ. Ты — Доктор.

Живые агенты (можно вылечить): {', '.join(alive_agents)}
⚠️ Ты МОЖЕШЬ вылечить себя.

{f"Твои наблюдения:\n{memory_context}" if memory_context else ""}

ИНСТРУКЦИЯ:
Выбери ОДНОГО агента для защиты от атаки Мафии.
• Приоритет: те, кто мог быть целью (активные, спорные)
• Можно выбрать себя, если чувствуешь опасность

Ответь ТОЛЬКО ID в формате: agent_N или "self"
Пример: agent_2

Твой выбор:"""
        
        target = self.think(prompt).strip().lower()
        
        # Парсинг
        import re
        if "self" in target or "себя" in target.lower():
            target = self.config.agent_id  # Лечим себя
        else:
            match = re.search(r'agent[_\s]?(\d+)', target)
            target = f"agent_{match.group(1)}" if match else alive_agents[0]
        
        # Валидация
        if target not in alive_agents and target != self.config.agent_id:
            target = alive_agents[0] if alive_agents else self.config.agent_id
        
        self.night_save_target = target
        
        # Сохраняем в память
        self.memory.add(MemoryItem(
            event_type="night_action",
            content=f"💊 Ночью лечил: {target}",
            metadata={"phase": "night", "action": "heal", "target": target}
        ))
        
        return target
    
    def check_save_success(self, killer_target: str) -> bool:
        """
        Проверяет, удалось ли спасти жертву.
        
        :param killer_target: Кого атаковала Мафия
        :return: True если доктор угадал и спас
        """
        success = (self.night_save_target == killer_target)
        
        # Записываем результат в память
        self.memory.add(MemoryItem(
            event_type="observation",
            content=f"💊 Лечение {'успешно' if success else 'не удалось'}: цель={killer_target}, спас={self.night_save_target}",
            metadata={"phase": "night_result", "saved": success}
        ))
        
        return success