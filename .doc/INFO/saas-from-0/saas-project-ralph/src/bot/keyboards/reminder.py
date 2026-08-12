"""Reminder keyboards for practice nudges."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.practice import NextQuestionCallback


def get_reminder_practice_keyboard() -> InlineKeyboardMarkup:
    """Get inline keyboard with 'Continue practice' button for reminders.

    Reuses the NextQuestionCallback so that pressing the button triggers
    the same flow as the 'Next Question' button after feedback.

    Returns:
        InlineKeyboardMarkup with a single practice button.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="\U0001f4aa \u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c \u043f\u0440\u0430\u043a\u0442\u0438\u043a\u0443",
        callback_data=NextQuestionCallback(action="next"),
    )
    return builder.as_markup()
