"""Practice keyboards for interview sessions."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class NextQuestionCallback(CallbackData, prefix="practice"):
    """Callback data for next question button."""

    action: str


def get_next_question_keyboard() -> InlineKeyboardMarkup:
    """Get inline keyboard with 'Next Question' button.

    Returns:
        InlineKeyboardMarkup with a single button.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="➡️ Следующий вопрос",
        callback_data=NextQuestionCallback(action="next"),
    )
    return builder.as_markup()
