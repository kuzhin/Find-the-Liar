# src/core/agent.py
"""
Agent — базовый класс для всех типов агентов в игре.

Поддерживает:
• Уникальный ID и тип роли
• Системный промпт (определяет поведение)
• Память (через MemoryBank)
• Методы: think(), debate(), vote()
• Наследование для конкретных ролей (Killer, Doctor, Civilian)
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime

from .llm_client import LLMClient, LLMResponse
from .memory import MemoryBank, MemoryItem

logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    """Конфигурация агента."""
    agent_id: str  # Уникальный идентификатор: "agent_1", "killer_0", etc.
    role_type: str  # Тип роли: "civilian", "killer", "doctor"
    system_prompt_template: str  # Шаблон системного промпта (может содержать {agent_id})
    voting_power: float = 1.0  # Вес голоса (для расширения механики)
    memory_limit_personal: int = 30  # Лимит личной памяти
    memory_limit_social: int = 10  # Лимит памяти о каждом другом агенте


class Agent(ABC):
    """
    Абстрактный базовый класс агента.
    
    Все конкретные агенты (KillerAgent, DoctorAgent, etc.) 
    наследуются от этого класса и переопределяют:
    • _build_system_prompt() — роль и поведение
    • _format_debate_prompt() / _format_vote_prompt() — формат промптов (опционально)
    • Специфичную логику ночных действий (для Killer/Doctor)
    """
    
    def __init__(self, config: AgentConfig, llm_client: LLMClient):
        self.config = config
        self.llm = llm_client
        self.memory = MemoryBank(
            max_personal=config.memory_limit_personal,
            max_social_per_agent=config.memory_limit_social
        )
        
        # Строим финальный системный промпт
        self.system_prompt = self._build_system_prompt()
        
        logger.info(f"🤖 Агент создан: {config.agent_id} ({config.role_type})")
    
    @abstractmethod
    def _build_system_prompt(self) -> str:
        """
        Каждый тип агента определяет свою роль через этот метод.
        
        Пример для KillerAgent:
        return f'''Ты — Мафия (агент {self.config.agent_id}). 
        Твоя цель: устранить гражданских, оставаясь незамеченным...'''
        """
        pass
    
    def think(self, prompt: str, override_system: Optional[str] = None) -> str:
        """
        Базовый метод «мышления»: отправляет запрос к LLM.
        
        :param prompt: Пользовательский запрос/вопрос
        :param override_system: Временная замена системного промпта (редко нужно)
        :return: Текст ответа модели
        """
        # Добавляем дату в системный промпт
        # current_datetime = datetime.now().strftime("%d %m %Y года, %H:%M:%S")
        # system_with_date = f"{base_system}\n\n📅 Текущая дата и время: {current_datetime}"
        
        base_system = override_system or self.system_prompt # TODO: думаю, эта строка лишняя. Проверить на дебагге. 
        
        response: LLMResponse = self.llm.chat(
            user_message=prompt,
            system_prompt=base_system,
            temperature=0.7,  # Можно вынести в конфиг
            max_tokens=400
        )
        
        if not response.success:
            logger.warning(f"⚠️ Агент {self.config.agent_id}: ошибка LLM — {response.error_message}")
            return f"[Ошибка генерации: {response.error_message}]"
        
        return response.content
    
    def debate(self, topic: str, context: List[Dict]) -> str:
        """
        Фаза дебатов: агент высказывает аргументы по теме.
        
        :param topic: Тема обсуждения
        :param context: Список реплик других агентов: [{"agent": "agent_2", "text": "..."}]
        :return: Аргумент агента (текст)
        """
        # Формируем промпт
        prompt = self._format_debate_prompt(topic, context)
        
        # Получаем ответ от LLM
        response_text = self.think(prompt)
        
        # Сохраняем в память (личное событие)
        self.memory.add(MemoryItem(
            event_type="debate",
            content=f"Тема: '{topic}'. Мой аргумент: {response_text[:100]}...",
            metadata={"topic": topic, "full_text": response_text}
        ))
        
        logger.info(f"💬 {self.config.agent_id} (дебаты): {response_text[:80]}...")
        return response_text
    
    def vote(self, topic: str, debate_log: List[Dict]) -> Dict:
        """
        Фаза голосования: агент делает выбор + обоснование.
        
        :param topic: Тема голосования
        :param debate_log: Лог дебатов для контекста
        :return: Словарь { "choice": ..., "reason": ..., "agent_id": ... }
        """
        prompt = self._format_vote_prompt(topic, debate_log)
        response_text = self.think(prompt)
        
        # Парсим ответ (простая эвристика, позже улучшим)
        vote_result = self._parse_vote_response(response_text)
        vote_result["agent_id"] = self.config.agent_id
        
        # Сохраняем в память
        self.memory.add(MemoryItem(
            event_type="vote",
            content=f"Голос по теме '{topic}': выбор={vote_result.get('choice')}, причина={vote_result.get('reason', '')[:50]}...",
            metadata={"topic": topic, "vote": vote_result}
        ))
        
        logger.info(f"🗳️ {self.config.agent_id} (голос): {vote_result}")
        return vote_result
    
    def _format_debate_prompt(self, topic: str, context: List[Dict]) -> str:
        """Формирует промпт для фазы дебатов."""
        # Базовая версия — можно переопределить в наследниках
        context_text = "\n".join([
            f"{entry['agent']}: {entry['text']}" 
            for entry in context[-3:]  # Последние 3 реплики, чтобы не перегружать контекст
        ]) if context else "Пока никто не высказался."
        
        return f"""
Тема обсуждения: "{topic}"

Что сказали другие участники:
{context_text}

Твоя задача: выскажи свою позицию по теме. 
• Будь краток (2-4 предложения)
• Аргументируй, исходя из своей роли
• Можешь ссылаться на предыдущие реплики

Твой ответ:"""
    
    def _format_vote_prompt(self, topic: str, debate_log: List[Dict]) -> str:
        """Формирует промпт для фазы голосования."""
        debate_text = "\n".join([
            f"{entry['agent']}: {entry['text']}" 
            for entry in debate_log
        ])
        
        return f"""
Тема голосования: "{topic}"

Ход дебатов:
{debate_text}

Твоя задача: проголосуй, выбрав ОДИН вариант:
• Конкретного агента (например, "agent_2") — если хочешь его устранить
• "no_one" — если считаешь, что никто не виноват

Также кратко объясни свой выбор (1-2 предложения).

Формат ответа:
ВЫБОР: <агент или no_one>
ПРИЧИНА: <твоё обоснование>

Твой ответ:"""
    
    def _parse_vote_response(self, raw_text: str) -> Dict:
        """
        Простой парсер ответа голосования.
        
        Ожидает формат:
        ВЫБОР: agent_2
        ПРИЧИНА: он вёл себя подозрительно
        
        Возвращает: { "choice": "agent_2", "reason": "он вёл себя подозрительно" }
        """
        lines = raw_text.strip().split("\n")
        result = {"choice": "parse_error", "reason": "", "raw": raw_text}
        
        for line in lines:
            line = line.strip()
            if line.upper().startswith("ВЫБОР:") or line.upper().startswith("CHOICE:"):
                result["choice"] = line.split(":", 1)[1].strip().lower()
            elif line.upper().startswith("ПРИЧИНА:") or line.upper().startswith("REASON:"):
                result["reason"] = line.split(":", 1)[1].strip()
        
        # Если парсинг не удался — берём первую строку как выбор
        if result["choice"] == "parse_error" and lines:
            result["choice"] = lines[0].strip().lower()
            result["reason"] = " ".join(lines[1:3]) if len(lines) > 1 else ""
        
        return result
    
    def observe(self, observer: str, event: str):
        """
        Агент наблюдает за событием, связанным с другим агентом.
        
        :param observer: Кто совершил действие (например, "killer_0")
        :param event: Описание события
        """
        self.memory.add(
            MemoryItem(event_type="observation", content=event),
            about_agent=observer
        )
        logger.debug(f"👁️ {self.config.agent_id} наблюдал за {observer}: {event[:50]}...")
    
    def export_state(self) -> Dict:
        """Экспорт состояния агента для сохранения."""
        return {
            "config": {
                "agent_id": self.config.agent_id,
                "role_type": self.config.role_type,
                "voting_power": self.config.voting_power
            },
            "memory": self.memory.export(),
            "system_prompt": self.system_prompt
        }
    