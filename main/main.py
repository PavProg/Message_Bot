import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from config.config import API_TOKEN, GROUP_ID


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

user_pending_messages = {}
# Хранилище тикетов: ticket_id -> {user_id, user_msg_id, group_msg_id}
ticket_map = {}
ticket_counter = 1

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать! Опишите вашу проблему одним сообщением, иначе бот перенаправит специалисту только последнее сообщение, затем нажмите кнопку 'Отправить обращение'.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✉️ Отправить обращение", callback_data="send_ticket")]
            ]
        )
    )

# Обработка нажатия кнопки и отправка обращения в группу + выдача номера тикета
@dp.callback_query(F.data == "send_ticket")
async def send_ticket_to_group(callback: types.CallbackQuery):
    global ticket_counter
    user_id = callback.from_user.id
    comment = user_pending_messages.get(user_id)
    if not comment:
        await callback.answer("Опишите проблему одним сообщением перед отправкой обращения!", show_alert=True)
        return
    ticket_id = ticket_counter
    ticket_counter += 1
    # Сохраняем тикет
    ticket_map[ticket_id] = user_id
    # Пересылаем в группу обращение и номер тикета
    await bot.send_message(
        chat_id=GROUP_ID,
        text=f"Заявка #{ticket_id} от @{callback.from_user.username or user_id}:\n{comment}"
    )
    user_pending_messages.pop(user_id, None)
    await callback.message.answer(f"Ваше обращение #{ticket_id} успешно отправлено специалистам. Постараемся ответить как можно скорее!")
    await callback.answer()

# Отправка специалистом ответа с указанием номера тикета (в тексте)
@dp.message(lambda msg: msg.chat.type in ("group", "supergroup"))
async def reply_from_group(message: Message):
    print('Хендлер сработал!')
    print('f"chat.id={message.chat.id}, GROUP_ID={GROUP_ID}"')
    import re
    # Ищем "#номер" тикета в сообщении
    match = re.search(r"#(\d+)", message.text)
    if match:
        ticket_id = int(match.group(1))
        if ticket_id in ticket_map:
            client_id = ticket_map[ticket_id]
            try:
                await bot.send_message(
                    chat_id=client_id,
                    text=f"Ответ специалиста по вашей заявке #{ticket_id}:\n{message.text}"
                )
            except Exception as e:
                logging.error(f"Ошибка пересылки ответа клиенту: {e}")

# Сохраняем последнее сообщение пользователя для пересылки
@dp.message()
async def store_user_message(message: Message):
    if message.text and not message.text.startswith("/"):
        user_pending_messages[message.from_user.id] = message.text

if __name__ == "__main__":
    dp.run_polling(bot)
