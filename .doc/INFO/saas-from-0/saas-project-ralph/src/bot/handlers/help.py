"""Handler for /help command — bot usage instructions."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.domain.entities.user import User

logger = logging.getLogger(__name__)

router = Router(name="help")

HELP_TEXT = (
    "<b>Как пользоваться ботом</b>\n"
    "\n"
    "Я помогу тебе подготовиться к техническому собеседованию. "
    "Генерирую вопросы по твоему профилю и оцениваю ответы с помощью ИИ.\n"
    "\n"
    "<b>Команды:</b>\n"
    "/start — начать работу / пройти онбординг\n"
    "/practice — получить вопрос для практики\n"
    "/stats — посмотреть статистику и прогресс\n"
    "/settings — изменить профиль и настройки\n"
    "/subscribe — управление подпиской\n"
    "/help — эта справка\n"
    "\n"
    "<b>Как это работает:</b>\n"
    "1. Пройди онбординг — выбери специальность, грейд и технологии\n"
    "2. Отправь /practice — получи вопрос\n"
    "3. Ответь текстом или голосовым сообщением\n"
    "4. Получи оценку и рекомендации от ИИ\n"
    "\n"
    "Бесплатно доступно 5 вопросов в день. "
    "Для безлимитного доступа оформи подписку — /subscribe."
)


@router.message(Command("help"))
async def cmd_help(message: Message, user: User | None = None) -> None:
    """Handle /help command — display bot usage instructions.

    Args:
        message: The incoming Telegram message.
        user: User domain object injected by AuthMiddleware.
    """
    if message.from_user is None:
        return

    logger.info("Help requested by telegram_id=%d", message.from_user.id)
    await message.answer(HELP_TEXT)
