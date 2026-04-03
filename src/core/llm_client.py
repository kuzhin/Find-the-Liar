# src/core/llm_client.py
"""
LLMClient — обёртка для работы с LM Studio (локальный сервер).

Поддерживает:
• Синхронные запросы (для дебатов — последовательно)
• Асинхронные запросы (для голосования — параллельно)
• Таймаут 3 минуты (по требованию пользователя)
• Обработку ошибок (сеть, таймаут, пустой ответ)
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

# OpenAI-совместимый клиент (LM Studio использует тот же API)
from openai import OpenAI, APIError, APITimeoutError

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """
    Конфигурация подключения к LLM.
    Выносится в отдельный класс для гибкости (смена модели, URL и т.д.).
    """
    model_name: str = "local-model"  # Имя модели (в LM Studio не важно)
    base_url: str = "http://localhost:1234/v1"  # LM Studio сервер /v1
    api_key: str = "lm-studio"  # Любой ключ, LM Studio не проверяет
    temperature: float = 0.7  # Креативность (0.0-1.0)
    max_tokens: int = 500  # Макс. длина ответа
    timeout: int = 180  # 3 минуты — твой лимит
    retry_count: int = 2  # Сколько раз повторять при ошибке


@dataclass
class LLMResponse:
    """
    Структурированный ответ от модели.
    Удобно для логирования и отладки.
    """
    content: str  # Текст ответа
    success: bool  # Успешно ли выполнился запрос
    error_message: Optional[str] = None  # Текст ошибки (если была)
    model: str = ""  # Какая модель ответила
    tokens_used: int = 0  # Сколько токенов потрачено (если доступно)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        """Для удобного вывода в консоль/лог"""
        if self.success:
            return f"✅ [{self.model}] {self.content[:100]}..."
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
        self.client = OpenAI(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            timeout=self.config.timeout  # Важно: 3 минуты на ответ
        )
        logger.info(f"LLMClient инициализирован: {self.config.base_url}")
    
    def is_available(self) -> bool:
        """
        Проверка доступности сервера LM Studio.
        
        :return: True если сервер отвечает, False иначе
        """
        try:
            # Простой запрос для проверки соединения
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
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Синхронный запрос к модели (один агент).
        
        :param user_message: Вопрос/запрос от пользователя
        :param system_prompt: Системный промпт (роль агента)
        :param temperature: Переопределение креативности (опционально)
        :param max_tokens: Переопределение длины ответа (опционально)
        :return: LLMResponse с ответом модели
        """
        for attempt in range(self.config.retry_count + 1):
            try:
                logger.info(f"📤 Запрос к модели (попытка {attempt + 1})")
                
                response = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=temperature or self.config.temperature,
                    max_tokens=max_tokens or self.config.max_tokens,
                    timeout=self.config.timeout
                )
                
                # Извлекаем текст ответа
                content = response.choices[0].message.content.strip()
                
                # Считаем токены (если доступно)
                tokens = 0
                if hasattr(response, 'usage') and response.usage:
                    tokens = response.usage.total_tokens or 0
                
                logger.info(f"✅ Получен ответ ({tokens} токенов)")
                
                return LLMResponse(
                    content=content,
                    success=True,
                    model=self.config.model_name,
                    tokens_used=tokens
                )
                
            except APITimeoutError:
                error_msg = f"Таймаут ответа ({self.config.timeout} сек)"
                logger.warning(f"⚠️ {error_msg}")
                if attempt == self.config.retry_count:
                    return LLMResponse(
                        content="",
                        success=False,
                        error_message=error_msg,
                        model=self.config.model_name
                    )
                    
            except APIError as e:
                error_msg = f"API ошибка: {str(e)}"
                logger.error(f"❌ {error_msg}")
                if attempt == self.config.retry_count:
                    return LLMResponse(
                        content="",
                        success=False,
                        error_message=error_msg,
                        model=self.config.model_name
                    )
                    
            except Exception as e:
                error_msg = f"Неизвестная ошибка: {str(e)}"
                logger.error(f"❌ {error_msg}")
                if attempt == self.config.retry_count:
                    return LLMResponse(
                        content="",
                        success=False,
                        error_message=error_msg,
                        model=self.config.model_name
                    )
        
        # Должны вернуться из цикла выше, но на всякий случай:
        return LLMResponse(
            content="",
            success=False,
            error_message="Неизвестная ошибка после всех попыток",
            model=self.config.model_name
        )
    
    def chat_batch(
        self,
        prompts: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> List[LLMResponse]:
        """
        Пакетный запрос к модели (несколько агентов параллельно).
        
        :param prompts: Список промптов вида:
            [
                {"system": "Ты маг", "user": "Голосуй!"},
                {"system": "Ты воин", "user": "Голосуй!"},
                ...
            ]
        :param temperature: Переопределение креативности
        :param max_tokens: Переопределение длины ответа
        :return: Список LLMResponse в том же порядке
        """
        logger.info(f"📤 Пакетный запрос: {len(prompts)} агентов")
        
        results = []
        
        # ⚠️ Примечание: LM Studio не поддерживает настоящий async
        # Поэтому делаем последовательно, но в одном методе для удобства
        # Если нужен настоящий параллелизм — потребуется несколько экземпляров клиента
        
        for i, prompt in enumerate(prompts):
            logger.info(f"  Агент {i+1}/{len(prompts)}")
            response = self.chat(
                user_message=prompt.get("user", ""),
                system_prompt=prompt.get("system", "Ты полезный ассистент."),
                temperature=temperature,
                max_tokens=max_tokens
            )
            results.append(response)
        
        logger.info(f"✅ Пакетный запрос завершён")
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Получение информации о подключённой модели.
        
        :return: Словарь с информацией (имя, контекст и т.д.)
        """
        try:
            models = self.client.models.list()
            return {
                "available": True,
                "models": [m.id for m in models.data] if models.data else ["local-model"],
                "base_url": self.config.base_url
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "base_url": self.config.base_url
            }


# ================= ТЕСТОВЫЙ ЗАПУСК =================
if __name__ == "__main__":
    print("🧪 Тест LLMClient для LM Studio\n")
    
    # 1. Создаём клиент
    client = LLMClient()
    
    # 2. Проверяем доступность сервера
    print("1️⃣ Проверка подключения к LM Studio...")
    if not client.is_available():
        print("❌ ОШИБКА: LM Studio сервер не отвечает!")
        print("   → Убедись, что LM Studio запущен")
        print("   → Убедись, что сервер включён (кнопка 'Start Server')")
        print("   → Убедись, что модель загружена в LM Studio")
        exit(1)
    
    print("✅ LM Studio сервер доступен\n")
    
    # 3. Информация о модели
    print("2️⃣ Информация о модели:")
    info = client.get_model_info()
    print(f"   URL: {info['base_url']}")
    print(f"   Модели: {info.get('models', ['неизвестно'])}\n")
    
    # 4. Тестовый запрос
    print("3️⃣ Тестовый запрос:")
    response = client.chat(
        user_message="Назови своё имя и кратко опиши, что ты умеешь.",
        system_prompt="Ты полезный ассистент для текстовой игры. Отвечай кратко."
    )
    
    if response.success:
        print(f"✅ Ответ получен:\n   {response.content}\n")
        print(f"   Токенов использовано: {response.tokens_used}")
    else:
        print(f"❌ Ошибка: {response.error_message}\n")
    
    print("🎉 Тест завершён!")