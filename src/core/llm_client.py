# src/core/llm_client.py
"""
LLMClient — обёртка для работы с LM Studio (локальный сервер).
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI, APIError, APITimeoutError

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Конфигурация подключения к LLM."""
    model_name: str = "auto"  # "auto" = взять первую доступную модель из LM Studio
    base_url: str = "http://localhost:1234/v1"  # 
    api_key: str = "lm-studio"
    temperature: float = 0.7
    max_tokens: int = 500
    timeout: int = 180  # 3 минуты
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
    """
    Основной клиент для работы с LM Studio.
    
    Пример использования:
        client = LLMClient()
        response = client.chat("Привет!", "Ты полезный ассистент.")
        print(response.content)
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Инициализация клиента.
        
        :param config: Конфигурация (если None — используются значения по умолчанию)
        """
        self.config = config or LLMConfig()
        
        # Если model_name = "auto", узнаем реальную модель из LM Studio
        if self.config.model_name == "auto":
            self.config.model_name = self._detect_model()
            logger.info(f"🔍 Авто-обнаружена модель: {self.config.model_name}")
        
        self.client = OpenAI(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            timeout=self.config.timeout
        )
        logger.info(f"🔌 LLMClient инициализирован: {self.config.base_url}")
    
    def _detect_model(self) -> str:
        """Получает первую доступную модель из LM Studio."""
        try:
            import urllib.request
            import json
            url = self.config.base_url.rstrip("/v1") + "/v1/models"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                models = data.get("data", [])
                # Ищем первую НЕ-эмбеддинг модель
                for m in models:
                    if "embedding" not in m.get("id", "").lower():
                        return m["id"]
                return models[0]["id"] if models else "local-model"
        except Exception as e:
            logger.warning(f"⚠️ Не удалось авто-определить модель: {e}")
            return "local-model"
    
    def is_available(self) -> bool:
        """Проверка доступности сервера."""
        try:
            self.client.models.list()
            logger.info("✅ LM Studio сервер доступен")
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
        
        for attempt in range(self.config.retry_count + 1):
            try:
                logger.info(f"📤 Запрос к модели '{use_model}' (попытка {attempt + 1})")
                
                response = self.client.chat.completions.create(
                    model=use_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=temperature or self.config.temperature,
                    max_tokens=max_tokens or self.config.max_tokens,
                    timeout=self.config.timeout
                )
                
                content = response.choices[0].message.content.strip()
                
                tokens = 0
                if hasattr(response, 'usage') and response.usage:
                    tokens = response.usage.total_tokens or 0
                
                logger.info(f"✅ Получен ответ ({tokens} токенов)")
                
                return LLMResponse(
                    content=content,
                    success=True,
                    model=use_model,
                    tokens_used=tokens
                )
                
            except APITimeoutError:
                error_msg = f"Таймаут ответа ({self.config.timeout} сек)"
                logger.warning(f"⚠️ {error_msg}")
                if attempt == self.config.retry_count:
                    return LLMResponse(content="", success=False, error_message=error_msg, model=use_model)
                    
            except APIError as e:
                error_msg = f"API ошибка: {str(e)}"
                logger.error(f"❌ {error_msg}")
                if attempt == self.config.retry_count:
                    return LLMResponse(content="", success=False, error_message=error_msg, model=use_model)
                    
            except Exception as e:
                error_msg = f"Неизвестная ошибка: {type(e).__name__}: {str(e)}"
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
        """Пакетный запрос (последовательно, но в одном вызове)."""
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
        """Информация о подключённой модели."""
        try:
            models = self.client.models.list()
            return {
                "available": True,
                "models": [m.id for m in models.data] if models.data else ["local-model"],
                "base_url": self.config.base_url
            }
        except Exception as e:
            return {"available": False, "error": str(e), "base_url": self.config.base_url}


# ================= ТЕСТ =================
if __name__ == "__main__":
    print("🧪 Тест LLMClient для LM Studio\n")
    
    client = LLMClient()  # auto-определит модель
    
    print("1️⃣ Проверка подключения...")
    if not client.is_available():
        print("❌ LM Studio не отвечает")
        exit(1)
    
    print("✅ Сервер доступен\n")
    
    print("2️⃣ Информация о модели:")
    info = client.get_model_info()
    print(f"   URL: {info['base_url']}")
    print(f"   Доступные модели: {info.get('models')}\n")
    
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


