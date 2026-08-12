"""FSM states for practice session flow."""

from aiogram.fsm.state import State, StatesGroup


class PracticeStates(StatesGroup):
    """States for the practice conversation flow.

    The practice flow consists of the following steps:
    1. waiting_answer - Bot sent a question, waiting for user's answer (text or voice)
    2. processing_answer - User submitted an answer, AI is evaluating it

    After evaluation is complete, feedback is sent and FSM is cleared.
    The user can then request another question via /practice or "Next question" button.
    """

    waiting_answer = State()
    processing_answer = State()
