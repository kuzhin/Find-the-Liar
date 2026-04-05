# src/core/agents/killer.py
from ..agent import Agent, AgentConfig
from ..llm_client import LLMClient

class KillerAgent(Agent):
    def __init__(self, config: AgentConfig, llm_client: LLMClient):
        super().__init__(config, llm_client)
        self.target: Optional[str] = None  # Кого устранил ночью
    
    def _build_system_prompt(self) -> str:
        return f"""Ты — Мафия (агент {self.config.agent_id}).
                    Твоя цель: устранить гражданских, оставаясь незамеченным.

                    Правила:
                    • В дебатах: лги, запутывай, обвиняй других
                    • В голосовании: голосуй против тех, кто тебя подозревает
                    • Ночью: выбирай одну жертву для устранения

                    📅 Текущая дата: {{datetime}}
                    Отвечай кратко, на русском, от первого лица.
                """
                    
    def night_action(self, alive_agents: list[str]) -> str:
        """
        Ночное действие: выбор жертвы.
        Возвращает ID агента для устранения.
        """
        prompt = f"""
                    Ночь. Ты — Мафия. Живые агенты: {', '.join(alive_agents)}.

                    Выбери ОДНУ жертву для устранения.
                    Ответь ТОЛЬКО ID агента (например, "civilian_2").

                    Твой выбор:
                """
        
        target = self.think(prompt).strip().lower()
        self.target = target
        
        # Сохраняем в память
        self.memory.add(MemoryItem(
            event_type="night_action",
            content=f"Eliminated in night time: {target}",
            metadata={"phase": "night", "action": "eliminate"}
        ))
        
        return target