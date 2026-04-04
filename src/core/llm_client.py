# src/core/llm_client.py
"""
LLMClient — обёртка для работы с LM Studio через прямые HTTP-запросы.
Почему не openai-библиотека: твоя версия LM Studio не поддерживает все эндпоинты openai SDK.
"""

import logging
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Конфигурация подключения к LM Studio."""
    # 👇 ВАЖНО: укажи точное имя модели из http://127.0.0.1:1234/v1/models

    model_name: str = "liquid/lfm2.5-1.2b" #qwen2.5-coder-7b-instruct
    # 👇 Используем 127.0.0.1 вместо localhost (надёжнее на Windows)
    base_url: str = "http://127.0.0.1:1234/v1"
    api_key: str = "lm-studio"  # Любой, LM Studio не проверяет
    temperature: float = 0.7
    max_tokens: int = 500
    timeout: int = 180  # 3 минуты — твой лимит
    retry_count: int = 2


@dataclass
class LLMResponse:
    """Структурированный ответ от модели."""
    content: str
    success: bool
    error_message: Optional[str] = None
    model: str = ""
    tokens_used: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        if self.success:
            preview = self.content[:100].replace('\n', ' ')
            return f"✅ [{self.model}] {preview}..."
        else:
            return f"❌ [{self.error_message}]"


class LLMClient:
    """Клиент для работы с LM Studio через requests."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LMStudio-Client"
        })
        logger.info(f"🔌 LLMClient инициализирован: {self.config.base_url}")
        logger.info(f"📦 Используемая модель: {self.config.model_name}")
    
    def is_available(self) -> bool:
        """Проверка доступности сервера."""
        try:
            url = self.config.base_url.rstrip("/") + "/models"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"✅ LM Studio сервер доступен, найдено моделей: {len(data.get('data', []))}")
            return True
        except Exception as e:
            logger.error(f"❌ LM Studio сервер недоступен: {e}")
            return False
    
    def chat(
        self,
        user_message: str,
        system_prompt: str = "Ты полезный ассистент.",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> LLMResponse:
        """Синхронный запрос к модели."""
        
        use_model = model or self.config.model_name
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        
        payload = {
            "model": use_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": False  # Важно: отключаем стриминг для простоты
        }
        
        for attempt in range(self.config.retry_count + 1):
            try:
                logger.info(f"📤 Запрос к '{use_model}' (попытка {attempt + 1})")
                
                resp = self.session.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout
                )
                resp.raise_for_status()
                
                result = resp.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # Считаем токены, если есть
                tokens = 0
                if 'usage' in result and result['usage']:
                    tokens = result['usage'].get('total_tokens', 0)
                
                logger.info(f"✅ Ответ получен ({tokens} токенов)")
                
                return LLMResponse(
                    content=content,
                    success=True,
                    model=use_model,
                    tokens_used=tokens
                )
                
            except requests.exceptions.Timeout:
                error_msg = f"Таймаут ответа ({self.config.timeout} сек)"
                logger.warning(f"⚠️ {error_msg}")
                if attempt == self.config.retry_count:
                    return LLMResponse(content="", success=False, error_message=error_msg, model=use_model)
                    
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                logger.error(f"❌ {error_msg}")
                if attempt == self.config.retry_count:
                    return LLMResponse(content="", success=False, error_message=error_msg, model=use_model)
                    
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Не удалось подключиться: {e}"
                logger.error(f"❌ {error_msg}")
                if attempt == self.config.retry_count:
                    return LLMResponse(content="", success=False, error_message=error_msg, model=use_model)
                    
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                if attempt == self.config.retry_count:
                    return LLMResponse(content="", success=False, error_message=error_msg, model=use_model)
        
        return LLMResponse(content="", success=False, error_message="Неизвестная ошибка", model=use_model)
    
    def chat_batch(
        self,
        prompts: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> List[LLMResponse]:
        """Пакетный запрос (последовательно)."""
        logger.info(f"📤 Пакетный запрос: {len(prompts)} агентов")
        results = []
        for i, prompt in enumerate(prompts):
            logger.info(f"  Агент {i+1}/{len(prompts)}")
            response = self.chat(
                user_message=prompt.get("user", ""),
                system_prompt=prompt.get("system", "Ты полезный ассистент."),
                temperature=temperature,
                max_tokens=max_tokens
            )
            results.append(response)
        logger.info("✅ Пакетный запрос завершён")
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Информация о доступных моделях."""
        try:
            url = self.config.base_url.rstrip("/") + "/models"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = [m["id"] for m in data.get("data", []) if "embedding" not in m.get("id", "").lower()]
            return {
                "available": True,
                "models": models if models else ["local-model"],
                "base_url": self.config.base_url
            }
        except Exception as e:
            return {"available": False, "error": str(e), "base_url": self.config.base_url}


# ================= ТЕСТ =================
if __name__ == "__main__":
    print("🧪 Тест LLMClient для LM Studio\n")
    
    # 👇 ВАЖНО: укажи свою модель здесь или в config
    config = LLMConfig(
        model_name="liquid/lfm2.5-1.2b", #qwen2.5-coder-7b-instruct,  # ← Твоя модель из /v1/models
        base_url="http://127.0.0.1:1234/v1"
    )
    
    client = LLMClient(config)
    
    print("1️⃣ Проверка подключения...")
    if not client.is_available():
        print("❌ LM Studio не отвечает")
        print("💡 Убедись: сервер запущен, модель загружена, порт 1234")
        exit(1)
    
    print("✅ Сервер доступен\n")
    
    print("2️⃣ Доступные модели:")
    info = client.get_model_info()
    for m in info.get('models', []):
        print(f"   • {m}")
    print()
    
    print("3️⃣ Тестовый запрос:")
    response = client.chat(
        user_message="Назови своё имя и кратко опиши, что ты умеешь.",
        system_prompt="Ты полезный ассистент для текстовой игры. Отвечай кратко."
    )
    
    if response.success:
        print(f"✅ Ответ:\n   {response.content}\n")
        print(f"   Модель: {response.model}")
        print(f"   Токенов: {response.tokens_used}")
    else:
        print(f"❌ Ошибка: {response.error_message}")
    
    print("\n🎉 Тест завершён!")