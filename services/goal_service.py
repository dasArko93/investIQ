from engines.goal_engine import (
    GoalEngine
)


class GoalService:

    @staticmethod
    def progress(

        current,

        target

    ):

        return (

            GoalEngine

            .progress(

                current,

                target

            )

        )