class GoalEngine:
    @staticmethod
    def progress(current, target):
        if not target:
            return 0
        return round(min((current / target) * 100, 100), 2)
