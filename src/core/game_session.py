class GameSession:
    def run_round(self, topic: str) -> RoundResult:
        # 🌞 ДЕНЬ
        debate_log = self._run_debate_phase(topic)
        votes = self._run_vote_phase(topic, debate_log)
        eliminated = self._calculate_elimination(votes)
        
        # 🌙 НОЧЬ (только если игра не закончилась)
        night_result = None
        if eliminated is None:  # Никого не устранили днём
            night_result = self._run_night_phase()
        
        # 📊 ИТОГИ
        result = RoundResult(
            topic=topic,
            debate_log=debate_log,
            votes=votes,
            eliminated=eliminated,
            night_result=night_result
        )
        
        # 💾 Авто-сохранение
        self.save_state()
        return result