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
    
    # Создаём запрос
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    # Отправляем
    with urllib.request.urlopen(req, context=context, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))
        
        print("✅ УСПЕХ! Ответ получен:")
        print("-" * 50)
        content = result['choices'][0]['message']['content']
        print(content)
        print("-" * 50)
        print(f"\n🎉 LM Studio работает! Проблема была в библиотеке openai.")
        
except urllib.error.HTTPError as e:
    print(f"❌ HTTP Ошибка {e.code}: {e.reason}")
    print(f"📄 Ответ сервера: {e.read().decode()[:200]}")
    
except urllib.error.URLError as e:
    print(f"❌ URL Ошибка: {e.reason}")
    print("💡 Попробуй заменить 'localhost' на '127.0.0.1' в URL")
    
except Exception as e:
    print(f"❌ Неизвестная ошибка: {type(e).__name__}: {e}")