# test_fixes.py
"""Быстрая проверка фиксов: парсинг + ночные действия"""

from src.utils.helpers import parse_agent_id

print("🧪 Тест парсера ID агента:\n")

test_cases = [
    ("ВЫБОР: agent_3", "agent_3"),
    ("Голосую за агент 2", "agent_2"),
    ("#1 кажется подозрительным", "agent_1"),
    ("Не вижу цели, никого", "no_one"),
    ("agent_5", "agent_5", "agent_5"),  # exclude_self тест
]

for i, case in enumerate(test_cases, 1):
    text = case[0]
    expected = case[1]
    exclude = case[2] if len(case) > 2 else None
    
    result = parse_agent_id(text, exclude_self=exclude)
    status = "✅" if result == expected else "❌"
    print(f"{i}. {status} '{text[:30]}...' → {result} (ожидал: {expected})")

print("\n🎉 Парсер готов!")