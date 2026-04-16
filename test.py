# test_roles.py
"""Тест трёх ролей агентов: Civilian, Killer, Doctor"""

from datetime import datetime
from src.core.llm_client import LLMClient, LLMConfig
from src.core.agents.civilian import CivilianAgent
from src.core.agents.killer import KillerAgent
from src.core.agents.doctor import DoctorAgent
from src.core.agent import AgentConfig

# === Настройка ===
config = LLMConfig(
    model_name="liquid/lfm2.5-1.2b",
    base_url="http://127.0.0.1:1234/v1",
    temperature=0.7,
    max_tokens=400
)
client = LLMClient(config)

# === Тестовая тема ===
TOPIC = "Агент_3 утверждает, что видел Мафию ночью. Стоит ли ему доверять?"

# === Контекст дебатов (симуляция) ===
DEBATE_CONTEXT = [
    {"agent": "agent_1", "text": "Я не верю агент_3, он слишком эмоционален."},
    {"agent": "agent_2", "text": "А почему бы и не выслушать его версию?"},
    {"agent": "agent_3", "text": "Я видел тень у дома агента_4, это была Мафия!"},
    {"agent": "agent_4", "text": "Это клевета! Я спал всю ночь."},
]

def test_role(agent_class, role_name: str, agent_id: str):
    """Универсальный тест для любой роли"""
    print(f"\n{'='*60}")
    print(f"🎭 Тест: {role_name} ({agent_id})")
    print(f"{'='*60}")
    
    # Создаём конфиг и агента
    agent_config = AgentConfig(
        agent_id=agent_id,
        role_type=role_name.lower(),
        system_prompt_template=f"Ты {role_name}"
    )
    agent = agent_class(agent_config, client)
    
    # 1. Дебаты
    print(f"\n💬 Дебаты:")
    argument = agent.debate(TOPIC, DEBATE_CONTEXT)
    print(f"   {agent_id}: {argument}")
    
    # 2. Голосование
    print(f"\n🗳️  Голосование:")
    vote = agent.vote(TOPIC, DEBATE_CONTEXT)
    print(f"   Выбор: {vote['choice']}")
    print(f"   Причина: {vote['reason']}")
    
    # 3. Ночное действие (только для Killer/Doctor)
    if hasattr(agent, 'night_action'):
        print(f"\n🌙 Ночное действие:")
        alive = ["agent_1", "agent_2", "agent_3", "agent_4", agent_id]
        target = agent.night_action(alive)
        action_name = "устранение" if role_name == "Killer" else "лечение"
        print(f"   {agent_id} выбрал {action_name}: {target}")
    
    return agent

# === Запуск тестов ===
if __name__ == "__main__":
    print("🎭 Тест ролей агентов для игры Мафия")
    print(f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"🤖 Модель: {config.model_name}")
    
    # Тестируем три роли
    civilian = test_role(CivilianAgent, "Civilian", "agent_1")
    killer = test_role(KillerAgent, "Killer", "agent_2")
    doctor = test_role(DoctorAgent, "Doctor", "agent_3")
    
    # Бонус: проверка спасения (если доктор угадал цель мафии)
    print(f"\n{'='*60}")
    print("🔍 Проверка ночного исхода:")
    killer_target = killer.night_target
    doctor_saved = doctor.night_save_target
    saved = (killer_target == doctor_saved)
    
    print(f"   Мафия атаковала: {killer_target}")
    print(f"   Доктор лечил: {doctor_saved}")
    print(f"   ✅ Жертва спасена!" if saved else f"   ❌ Жертва устранена...")
    
    print(f"\n🎉 Тест ролей завершён!")