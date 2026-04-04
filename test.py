# test_direct.py
# Тест подключения к LM Studio БЕЗ библиотеки openai
import urllib.request
import json
import ssl

print("🔍 Прямой тест подключения к LM Studio\n")

# Отключаем проверку SSL (для localhost не критично)
context = ssl._create_unverified_context()

url = "http://localhost:1234/v1/chat/completions"

# Заголовки, как у браузера (чтобы LM Studio не блокировал)
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer lm-studio",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Тело запроса в формате OpenAI API
payload = {
    "model": "liquid/lfm2.5-1.2b",
    # "model": "qwen2.5-coder-7b-instruct",  # ← Твоя модель из списка!
    "messages": [
        {"role": "system", "content": "Отвечай кратко."},
        {"role": "user", "content": "Привет! Как тебя зовут?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
}

try:
    print(f"📤 Отправка запроса к {url}")
    print(f"📦 Модель: {payload['model']}\n")
    
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