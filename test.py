# test_agent.py
"""Тест базового агента и памяти"""

from src.core.llm_client import LLMClient, LLMConfig
from src.core.agent import Agent, AgentConfig
from src.core.memory import MemoryItem

# === Настройка ===
config = LLMConfig(
    model_name="liquid/lfm2.5-1.2b",  # Твоя лёгкая модель
    base_url="http://127.0.0.1:1234/v1"
)
client = LLMClient(config)

# === Простой тестовый агент (без абстракции) ===
class TestAgent(Agent):
    def _build_system_prompt(self) -> str:
        return f"""Ты — тестовый агент {self.config.agent_id}.
Отвечай кратко, по делу, на русском."""

# === Запуск теста ===
if __name__ == "__main__":
    print("🧪 Тест Agent + MemoryBank\n")
    
    # 1. Создаём агента
    agent_config = AgentConfig(
        agent_id="test_0",
        role_type="civilian",
        system_prompt_template="Ты {agent_id}"
    )
    agent = TestAgent(agent_config, client)
    
    # 2. Тест памяти
    print("1️⃣  Тест памяти:")
    agent.memory.add(MemoryItem("debate", "Я считаю, что агент_2 подозрителен"))
    agent.observe("killer_0", "ночью ходил к дому агента_3")
    print(f"   Контекст для промпта:\n{agent.memory.to_prompt_context()}\n")
    
    # 3. Тест think()
    print("2️⃣  Тест think():")
    answer = agent.think("Какой сегодня день?")
    print(f"   Ответ: {answer}\n")
    
    # 4. Тест debate()
    print("3️⃣  Тест debate():")
    argument = agent.debate(
        topic="Стоит ли доверять агенту_2?",
        context=[
            {"agent": "agent_1", "text": "Он вёл себя странно"},
            {"agent": "agent_3", "text": "Я не согласен, у него алиби"}
        ]
    )
    print(f"   Аргумент: {argument}\n")
    
    # 5. Тест vote()
    print("4️⃣  Тест vote():")
    vote = agent.vote(
        topic="Кого устранить?",
        debate_log=[
            {"agent": "agent_1", "text": "Голосую за agent_2"},
            {"agent": "agent_2", "text": "Это клевета!"}
        ]
    )
    print(f"   Голос: {vote}\n")
    
    print("✅ Все тесты пройдены!")