import ollama
import time

# --- КОНФИГУРАЦИЯ ---
# Имя модели должно точно совпадать с тем, что ты скачал в консоли
MODEL_NAME = "qwen2.5:7b" 

# Системный промпт — это "душа" твоего агента
# Здесь мы задаём роль, которую модель будет играть
SYSTEM_PROMPT = """
Ты — участник совета древней гильдии магов. 
Твои черты: мудрый, немного ворчливый, ценишь знания выше золота.
Отвечай кратко (2-3 предложения).
"""

def run_agent(user_message: str):
    """
    Функция отправки запроса к локальной модели.
    """
    print(f"🤖 Агент думает...")
    
    try:
        # Отправляем запрос через локальный сервер Ollama
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': user_message}
            ],
            options={
                'temperature': 0.7,  # Креативность (0.2 - точно, 0.8 - безумно)
                'num_predict': 256,  # Максимум токенов в ответе (экономит память)
            }
        )
        
        # Извлекаем текст ответа
        answer = response['message']['content']
        return answer
        
    except Exception as e:
        return f"❌ Ошибка соединения с Ollama: {e}"

# --- ЗАПУСК ---
if __name__ == "__main__":
    print(f"🚀 Запуск агента на модели: {MODEL_NAME}")
    print(f"💡 Убедись, что приложение Ollama запущено в трее!\n")
    
    # Пример диалога
    question = "Стоит ли нам принять предложение торговцев зельями?"
    
    # Замер времени (для понимания скорости на GTX 1060)
    start_time = time.time()
    result = run_agent(question)
    end_time = time.time()
    
    print(f"🧙‍♂️ Маг говорит: {result}")
    print(f"⏱️ Время ответа: {end_time - start_time:.2f} сек.")