class MissingSectorEngine:
    @staticmethod
    def identify(current_sectors, universe_sectors):
        return [
            s
            for s
            in universe_sectors
            if s not in current_sectors
        ]