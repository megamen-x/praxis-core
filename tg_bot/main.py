import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from datetime import datetime, timedelta
import aioschedule
from typing import List, Optional
import pytz
import json
import httpx

# SQLAlchemy imports
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

import logging

from models.user import User
from models.broadcast import Broadcast
from models.review import Review
from db.session import Base, engine

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8096053221:AAFtVtvlGyiHJOtRQWbCbd1_C2LqTVzGM9Y"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# # Создание асинхронного движка
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Инициализация базы данных
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Регистрация пользователя в БД
async def register_user(user_id: int, username: str, first_name: str, last_name: str) -> bool:
    try:
        async with async_session() as session:
            # Проверяем, существует ли пользователь
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                new_user = User(
                    user_id=user_id,
                    first_name=first_name,
                    last_name=last_name,
                    can_create_review=True,
                    created_at=datetime.utcnow(),
                )
                session.add(new_user)
            
            await session.commit()
            return True
            
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        return False

# Получение всех активных пользователей
async def get_all_users() -> List[int]:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(User.user_id).where(User.is_active == True)
            )
            users = [row[0] for row in result.all()]
            return users
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return []

# Получение количества пользователей
async def get_reviews_by_user(user_id: str) -> int:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Review).where(Review.created_by_user_id == user_id)
            )
            return result.scalars().all()
    except Exception as e:
        logger.error(f"Error getting users count: {e}")
        return 0

async def get_users_count() -> int:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(User)
            )
            return len(result.scalars().all())
    except Exception as e:
        logger.error(f"Error getting users count: {e}")
        return 0

# Сохранение рассылки в БД
async def save_broadcast(message_text: str, scheduled_time: datetime) -> Optional[int]:
    try:
        async with async_session() as session:
            new_broadcast = Broadcast(
                message_text=message_text,
                scheduled_time=scheduled_time
            )
            session.add(new_broadcast)
            await session.commit()
            return new_broadcast.id
    except Exception as e:
        logger.error(f"Error saving broadcast: {e}")
        return None

# Получение активных рассылок
async def get_scheduled_broadcasts() -> List[Broadcast]:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Broadcast).where(
                    Broadcast.status == 'scheduled',
                    Broadcast.scheduled_time > datetime.utcnow()
                ).order_by(Broadcast.scheduled_time)
            )
            return result.scalars().all()
    except Exception as e:
        logger.error(f"Error getting broadcasts: {e}")
        return []

# Обновление статуса рассылки
async def update_broadcast_status(broadcast_id: int, status: str, 
                                 sent_count: int = 0, failed_count: int = 0) -> bool:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()
            
            if broadcast:
                broadcast.status = status
                broadcast.sent_count = sent_count
                broadcast.failed_count = failed_count
                await session.commit()
                return True
            return False
    except Exception as e:
        logger.error(f"Error updating broadcast status: {e}")
        return False

# Создание основной клавиатуры
def create_main_keyboard():
    builder = ReplyKeyboardBuilder()
    
    # Кнопка для админа
    builder.row(KeyboardButton(text="📝 Создать форму"))
    builder.row(KeyboardButton(text="📝 Посмотреть список созданных форм"))
    builder.row(KeyboardButton(text="⬅️ Главное меню"))
    return builder.as_markup(resize_keyboard=True)

# Создание клавиатуры админа
def create_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📝 Создать форму"))
    builder.row(KeyboardButton(text="⬅️ Главное меню"))
    return builder.as_markup(resize_keyboard=True)

ADMIN_IDS = [12345678]  # Ваш Telegram ID

# Проверка прав администратора
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    success = await register_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name or ""
    )
    
    if success:
        welcome_text = f"👋 Привет, {user.first_name}!\n✅ Вы успешно зарегистрированы!"
    else:
        welcome_text = f"👋 Привет, {user.first_name}!\nПроизошла ошибка при регистрации."
    
    keyboard = create_main_keyboard()
    await message.answer(welcome_text, reply_markup=keyboard)
    
    # Если пользователь админ - показываем админ-панель
    if is_admin(user.id):
        admin_keyboard = create_admin_keyboard()
        await message.answer("👑 Вам доступна панель администратора", reply_markup=admin_keyboard)

# Состояния для FSM
user_states = {}

@router.message(F.text == "📝 Создать форму")
async def create_form(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав на создание формы")
        return
    
    try: 
        await message.answer('Введите тег пользователя, по которому создана форма')
        user_states[message.from_user.id] = 'form_creating_tag_subject_user_id'
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await message.answer("❌ Ошибка при создании формы")


@router.message(F.text == "📝 Посмотреть список созданных форм")
async def list_forms(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав на просмотр списка форм")
        return
    
    try: 
        
        forms = get_reviews_by_user(user_id='ae15f59e-f572-4d28-9ad5-640014288f7b')
        print(forms)
        if not forms:
            await message.answer("📭 Нет созданных форм")
            return
        
        response_text = "📋 Список созданных форм:\n\n"
        for form in forms:
            response_text += f"ID: {form['id']}\n"
            # response_text += f"Тег пользователя: {form['subject_user_id']}\n"
            response_text += f"Создано: {form['created_at']}\n"
            
        await message.answer(response_text)
        
    except Exception as e:
        logger.error(f"Error getting forms: {e}")
        await message.answer("❌ Ошибка при получении списка форм")

# # Обработчик статистики
# @router.message(F.text == "📊 Статистика")
# async def show_stats(message: types.Message):
#     if not is_admin(message.from_user.id):
#         await message.answer("❌ У вас нет прав для просмотра статистики")
#         return
    
#     try:
#         total_users = await get_users_count()
#         broadcasts = await get_scheduled_broadcasts()
#         active_broadcasts = len(broadcasts)
        
#         stats_text = (
#             "📊 Статистика бота:\n\n"
#             f"👥 Всего пользователей: {total_users}\n"
#             f"📨 Активных рассылок: {active_broadcasts}\n"
#             f"🕒 Время сервера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
#         )
        
#         await message.answer(stats_text)
        
#     except Exception as e:
#         logger.error(f"Error getting stats: {e}")
#         await message.answer("❌ Ошибка при получении статистики")

# Обработчик создания рассылки
@router.message(F.text == "📨 Создать рассылку")
async def create_broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для создания рассылки")
        return
    
    user_states[message.from_user.id] = 'awaiting_broadcast_message'
    await message.answer(
        "📝 Введите текст рассылки:\n\n"
        "Формат даты и времени: ГГГГ-ММ-ДД ЧЧ:ММ\n"
        "Пример: 2024-12-25 15:30\n\n"
        "После текста сообщения на новой строке укажите дату и время"
    )

# Обработчик активных рассылок
@router.message(F.text == "📋 Активные рассылки")
async def show_active_broadcasts(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для просмотра рассылок")
        return
    
    broadcasts = await get_scheduled_broadcasts()
    
    if not broadcasts:
        await message.answer("📭 Нет активных рассылок")
        return
    
    response = "📋 Активные рассылки:\n\n"
    for broadcast in broadcasts:
        # Обрезаем длинный текст
        preview = broadcast.message_text[:50] + "..." if len(broadcast.message_text) > 50 else broadcast.message_text
        response += f"ID: {broadcast.id}\n"
        response += f"Время: {broadcast.scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"
        response += f"Текст: {preview}\n"
        response += "─" * 20 + "\n"
    
    await message.answer(response)
    
@router.message(F.text == "📋 Вывести список")
async def show_active_broadcasts(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для просмотра рассылок")
        return
    
    broadcasts = await get_scheduled_broadcasts()
    
    if not broadcasts:
        await message.answer("📭 Нет активных рассылок")
        return
    
    response = "📋 Активные рассылки:\n\n"
    for broadcast in broadcasts:
        # Обрезаем длинный текст
        preview = broadcast.message_text[:50] + "..." if len(broadcast.message_text) > 50 else broadcast.message_text
        response += f"ID: {broadcast.id}\n"
        response += f"Время: {broadcast.scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"
        response += f"Текст: {preview}\n"
        response += "─" * 20 + "\n"
    
    await message.answer(response)

# Обработчик текстовых сообщений для создания рассылки
@router.message(F.text)
async def handle_broadcast_creation(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in user_states and user_states[user_id] == 'awaiting_broadcast_message':
        try:
            # Парсим сообщение - последняя строка должна быть дата/время
            lines = message.text.strip().split('\n')
            if len(lines) < 2:
                await message.answer("❌ Неверный формат. Нужен текст и дата/время на разных строках")
                return
            
            # Последняя строка - дата/время
            datetime_str = lines[-1].strip()
            message_text = '\n'.join(lines[:-1]).strip()
            
            # Парсим дату/время
            scheduled_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            
            # Проверяем, что время в будущем
            if scheduled_time <= datetime.now():
                await message.answer("❌ Время должно быть в будущем")
                return
            
            # Сохраняем рассылку
            broadcast_id = await save_broadcast(message_text, scheduled_time)
            
            if broadcast_id:
                # Планируем рассылку
                schedule_broadcast(broadcast_id, message_text, scheduled_time)
                
                await message.answer(
                    f"✅ Рассылка запланирована!\n"
                    f"ID: {broadcast_id}\n"
                    f"Время: {scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Получателей: {len(await get_all_users())}"
                )
            else:
                await message.answer("❌ Ошибка при сохранении рассылки")
            
            # Сбрасываем состояние
            del user_states[user_id]
            
        except ValueError:
            await message.answer("❌ Неверный формат даты/времени. Используйте: ГГГГ-ММ-ДД ЧЧ:ММ")
        except Exception as e:
            logger.error(f"Error creating broadcast: {e}")
            await message.answer("❌ Ошибка при создании рассылки")
            if user_id in user_states:
                del user_states[user_id]

    elif user_id in user_states and user_states[user_id] == 'form_creating_tag_subject_user_id':
        try:
            subject_user_id = message.text.strip()
            
            async with httpx.AsyncClient() as client:
                data = {
                    "created_by_user_id": "ae15f59e-f572-4d28-9ad5-640014288f7b", 
                    "subject_user_id": "43e86fc0-ac1f-4b1f-9025-6bb43da68f3e", 
                    "title": "Gospody",
                    "description": "New",
                    "anonymity": False,
                }
                headers = {
                    "Content-type": "application/json", 
                }
                url = "http://localhost:8000/api/tg/reviews/create"
                response = await client.post(url, data=json.dumps(data), headers=headers)
            
            builder = InlineKeyboardBuilder()
            target_url = "http://127.0.0.1:8000" + response.json()['admin_link']
            print(target_url)
            builder.button(
                text="Перейти к форме",
                url=target_url
            )

            await message.answer(
                "Уникальная ссылка создана, жми на кнопку ниже:",
                reply_markup=builder.as_markup()
            )
                
            del user_states[user_id]
        except Exception as e:
            logger.error(f"Error creating form: {e}")
            await message.answer("❌ Ошибка при создании формы")
            if user_id in user_states:
                del user_states[user_id]
        
            

# Функция для отправки рассылки
async def send_broadcast(broadcast_id: int, message_text: str):
    try:
        users = await get_all_users()
        success_count = 0
        fail_count = 0
        
        for user_id in users:
            try:
                await bot.send_message(user_id, f"📨 Рассылка:\n\n{message_text}")
                success_count += 1
                await asyncio.sleep(0.1)  # Задержка чтобы не превысить лимиты
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                fail_count += 1
        
        # Обновляем статус рассылки
        await update_broadcast_status(broadcast_id, 'completed', success_count, fail_count)
        
        # Отправляем отчет админу
        report = (
            f"📊 Отчет по рассылке ID: {broadcast_id}\n"
            f"✅ Успешно: {success_count}\n"
            f"❌ Неудачно: {fail_count}\n"
            f"📝 Текст: {message_text[:100]}..."
        )
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, report)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error in broadcast {broadcast_id}: {e}")
        await update_broadcast_status(broadcast_id, 'failed')

# Планирование рассылки
def schedule_broadcast(broadcast_id: int, message_text: str, scheduled_time: datetime):
    async def scheduled_task():
        await send_broadcast(broadcast_id, message_text)
    
    # Вычисляем разницу во времени
    now = datetime.now()
    delay = (scheduled_time - now).total_seconds()
    
    if delay > 0:
        asyncio.create_task(schedule_delayed(delay, scheduled_task))

async def schedule_delayed(delay: float, task):
    await asyncio.sleep(delay)
    await task()

# Загрузка и планирование существующих рассылок при запуске
async def load_scheduled_broadcasts():
    broadcasts = await get_scheduled_broadcasts()
    for broadcast in broadcasts:
        if broadcast.scheduled_time > datetime.now():
            schedule_broadcast(broadcast.id, broadcast.message_text, broadcast.scheduled_time)
            logger.info(f"Запланирована рассылка ID: {broadcast.id} на {broadcast.scheduled_time}")

# Обработчик возврата в главное меню
@router.message(F.text == "⬅️ Главное меню")
async def back_to_main(message: types.Message):
    keyboard = create_main_keyboard()
    await message.answer("Главное меню", reply_markup=keyboard)
    
    # Если пользователь админ - сбрасываем состояние
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]

# Обработчик команды /cancel для отмены действий
@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
        await message.answer("❌ Действие отменено", reply_markup=create_main_keyboard())
    else:
        await message.answer("Нет активных действий для отмены")

# Основная функция
async def main():
    # Инициализируем БД
    await init_db()
    
    # Загружаем запланированные рассылки
    await load_scheduled_broadcasts()
    
    logger.info("Бот запущен!")
    
    # Запускаем бота
    await dp.start_polling(bot)

# Обработка graceful shutdown
async def shutdown():
    await engine.dispose()
    logger.info("Бот остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
        asyncio.run(shutdown())