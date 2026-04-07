# src/core/agents/civilian.py
"""
CivilianAgent — мирный житель.

Поведение:
• Ищет противоречия в словах других
• Голосует на основе логики и наблюдений
• Не имеет специальных ночных действий
"""

from typing import List, Dict, Optional
from ..agent import Agent, AgentConfig
from ..llm_client import LLMClient
from ..memory import MemoryItem
from ..vote import Vote
from ...utils.helpers import inject_datetime

class CivilianAgent(Agent):
    """Мирный житель: анализирует, аргументирует, голосует."""
    
    def __init__(self, config: AgentConfig, llm_client: LLMClient):
        super().__init__(config, llm_client)
    
    def _build_system_prompt(self) -> str:
        """Роль мирного жителя"""
        base_prompt = f"""Ты — Мирный Житель (агент {self.config.agent_id}) в игре Мафия.

Твои цели:
• Выявить Мафию через анализ противоречий
• Голосовать обоснованно, на основе фактов
• Не поддаваться эмоциям и манипуляциям

Правила общения:
• Отвечай кратко (2-4 предложения)
• Ссылайся на конкретные слова других агентов
• Если не уверен — говори об этом

{inject_datetime()}
Отвечай на русском, от первого лица."""
        return base_prompt
    
    def _format_debate_prompt(self, topic: str, context: List[Dict]) -> str:
        """Промпт для дебатов: акцент на поиск лжи"""
        context_text = "\n".join([
            f"• {entry['agent']}: {entry['text']}" 
            for entry in context[-4:]  # Последние 4 реплики
        ]) if context else "• Пока никто не высказался."
        
        return f"""
🗣️ Дебаты по теме: "{topic}"

Сказанное другими:
{context_text}

Твоя задача как Мирного Жителя:
1. Проанализируй реплики: есть ли противоречия, подозрительные утверждения?
2. Выскажи свою позицию: кого подозреваешь и почему?
3. Будь краток, но конкретен.

Твой ответ:"""
    
    def _format_vote_prompt(self, topic: str, debate_log: List[Dict]) -> str:
        """Промпт для голосования: чёткий формат вывода"""
        debate_text = "\n".join([
            f"{entry['agent']}: {entry['text']}" 
            for entry in debate_log
        ])
        
        return f"""
🗳️ ГОЛОСОВАНИЕ: "{topic}"

Ход дебатов:
{debate_text}

ИНСТРУКЦИЯ:
Проголосуй за устранение ОДНОГО агента ИЛИ выбери "no_one", если не уверен.

Формат ответа СТРОГО:
ВЫБОР: <agent_1|agent_2|...|no_one>
ПРИЧИНА: <1-2 предложения обоснования>

Пример:
ВЫБОР: agent_3
ПРИЧИНА: Он противоречил себе в дебатах и избегал прямых ответов.

Твой ответ:"""
    
    def _parse_vote_response(self, raw_text: str) -> Dict:
        """Улучшенный парсер для гражданских: ищет ключевые слова"""
        result = {"choice": "parse_error", "reason": "", "raw": raw_text}
        
        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        
        for line in lines:
            upper = line.upper()
            if upper.startswith(("ВЫБОР:", "CHOICE:", "ГОЛОС:")):
                choice = line.split(":", 1)[1].strip().lower()
                # Нормализация: убираем лишние слова
                for word in ["агент", "agent", "за", "против"]:
                    choice = choice.replace(word, "").strip()
                result["choice"] = choice if choice else "parse_error"
            elif upper.startswith(("ПРИЧИНА:", "РЕЗОН:", "ПОЧЕМУ:", "REASON:")):
                result["reason"] = line.split(":", 1)[1].strip()
        
        # Fallback: если не нашли ВЫБОР, берём первое упоминание agent_N
        if result["choice"] == "parse_error":
            import re
            match = re.search(r'agent[_\s]?(\d+)', raw_text.lower())
            if match:
                result["choice"] = f"agent_{match.group(1)}"
            elif "не уверен" in raw_text.lower() or "no one" in raw_text.lower():
                result["choice"] = "no_one"
        
        return result