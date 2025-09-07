import asyncio
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from datetime import datetime
from typing import List, Optional
import json
import httpx

from dotenv import dotenv_values

import logging
import sys
sys.path.append("..")
# from db import Base 
# from db.session import engine, LocalSession 
# from db.models.broadcast import Broadcast 

config = dotenv_values("../../.env")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = config.get("BOT_TOKEN")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

async def get_db_id(user_id: int) -> Optional[int]:
    async with httpx.AsyncClient() as client:
        users = await client.get(url="http://localhost:8000/api/user")
    for user in users.json():
        if user['telegram_chat_id'] == str(user_id):
            return user['user_id']
    return None

# Сохранение рассылки в БД
# ПОКА НЕ РАБОТАЕТ, НУЖНА ТАБЛИЦА BROADCAST В БД
# def save_broadcast(message_text: str, scheduled_time: datetime) -> Optional[int]:
#     try:
#         with LocalSession() as session:
#             new_broadcast = Broadcast(
#                 message_text=message_text,
#                 scheduled_time=scheduled_time
#             )
#             session.add(new_broadcast)
#             session.commit()
#             return new_broadcast.id
#     except Exception as e:
#         logger.error(f"Error saving broadcast: {e}")
#         return None

# Получение активных рассылок
# ПОКА НЕ РАБОТАЕТ, НУЖНА ТАБЛИЦА BROADCAST В БД
# def get_scheduled_broadcasts() -> List[Broadcast]:
#     try:
#         with LocalSession() as session:
#             broadcasts = session.query(Broadcast).filter(
#                 Broadcast.status == 'scheduled',
#                 Broadcast.scheduled_time > datetime.utcnow()
#             ).order_by(Broadcast.scheduled_time).all()
#             return broadcasts
#     except Exception as e:
#         logger.error(f"Error getting broadcasts: {e}")
#         return []

# Обновление статуса рассылки
# ПОКА НЕ РАБОТАЕТ, НУЖНА ТАБЛИЦА BROADCAST В БД
# def update_broadcast_status(broadcast_id: int, status: str, 
#                             sent_count: int = 0, failed_count: int = 0) -> bool:
#     try:
#         with LocalSession() as session:
#             broadcast = session.query(Broadcast).filter(Broadcast.id == broadcast_id).one_or_none()
            
#             if broadcast:
#                 broadcast.status = status
#                 broadcast.sent_count = sent_count
#                 broadcast.failed_count = failed_count
#                 session.commit()
#                 return True
#             return False
#     except Exception as e:
#         logger.error(f"Error updating broadcast status: {e}")
#         return False

# Создание основной клавиатуры
def create_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📝 Создать форму"))
    builder.row(KeyboardButton(text="📝 Посмотреть список созданных форм"))
    builder.row(KeyboardButton(text="Назначить review_id"))
    builder.row(KeyboardButton(text="⬅️ Главное меню"))
    return builder.as_markup(resize_keyboard=True)

# Состояния для FSM
user_states = {}

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_states[message.from_user.id] = 'waiting_for_name'
    await message.answer('Введите ваше имя (в формате ФИО): ')

# Проверка прав администратора
def is_admin(user_id: int) -> bool:
    with httpx.Client() as client:
        is_admin = client.post(url=f"http://localhost:8000/api/user/{user_id}/is_admin")
    return is_admin

@router.message(F.text == "📝 Создать форму")
async def create_form(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав на создание формы")
        return
    
    try: 
        
        db_id = user_states.get(str(message.from_user.id))
        if not db_id:
            user_states[str(message.from_user.id)+'_db_id'] = await get_db_id(message.from_user.id)
        
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
        
        db_id = user_states.get(str(message.from_user.id))
        if not db_id:
            user_states[str(message.from_user.id)+'_db_id'] = await get_db_id(message.from_user.id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=f"http://localhost:8000/api/user/{user_states[str(message.from_user.id)+'_db_id']}/reviews"
            )
            forms = response.json()
            print(forms)
        
        if not forms:
            await message.answer("📭 Нет созданных форм")
            return
        
        response_text = "📋 Список созданных форм:\n\n"
        for form in forms:
            response_text += f"ID: {form['review_id']}\n"
            # response_text += f"Тег пользователя: {form['subject_user_id']}\n"
            response_text += f"status: {form['status']}\n"
        
        await message.answer(response_text)
        
    except Exception as e:
        logger.error(f"Error getting forms: {e}")
        await message.answer("❌ Ошибка при получении списка форм")

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
# НЕ РАБОТАЕТ, НУЖНА ТАБЛИЦА BROADCAST В БД
# @router.message(F.text == "📋 Активные рассылки")
# async def show_active_broadcasts(message: types.Message):
#     if not is_admin(message.from_user.id):
#         await message.answer("❌ У вас нет прав для просмотра рассылок")
#         return
    
#     broadcasts = get_scheduled_broadcasts()
    
#     if not broadcasts:
#         await message.answer("📭 Нет активных рассылок", reply_markup=create_main_keyboard())
#         return
    
#     response = "📋 Активные рассылки:\n\n"
#     for broadcast in broadcasts:
#         # Обрезаем длинный текст
#         preview = broadcast.message_text[:50] + "..." if len(broadcast.message_text) > 50 else broadcast.message_text
#         response += f"ID: {broadcast.id}\n"
#         response += f"Время: {broadcast.scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"
#         response += f"Текст: {preview}\n"
#         response += "─" * 20 + "\n"
    
#     await message.answer(response, reply_markup=create_main_keyboard())

@router.message(F.text == "Назначить review_id")
async def assign_survey_id(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этого действия")
        return
    
    user_states[message.from_user.id] = 'awaiting_review_id'
    await message.answer("Выберите review_id для назначения:")
    

# Обработчик текстовых сообщений для создания рассылки
@router.message(F.text)
async def handle_text_response(message: types.Message):
    cur_user = message.from_user
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
            # ПОКА НЕ РАБОТАЕТ, НУЖНА ТАБЛИЦА BROADCAST В БД
            broadcast_id = None # broadcast_id = save_broadcast(message_text, scheduled_time)
            
            if broadcast_id:
                # Планируем рассылку
                schedule_broadcast(broadcast_id, message_text, scheduled_time)
                
                await message.answer(
                    f"✅ Рассылка запланирована!\n"
                    f"ID: {broadcast_id}\n"
                    f"Время: {scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"
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
            
            async with httpx.AsyncClient() as client:
                data = {
                    "created_by_user_id": user_states[str(message.from_user.id)+'_db_id'], 
                    "subject_user_id": message.text.strip(), 
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
                
    elif user_id in user_states and user_states[user_id] == 'waiting_for_name':
        
        last_name, first_name, middle_name = message.text.strip().split()
        
        async with httpx.AsyncClient() as client:
            users = await client.get(url="http://localhost:8000/api/all_user")
            print(users)
            is_registered = False
            for user in users.json():
                print(user)
                if user['telegram_chat_id'] == str(cur_user.id):
                    is_registered = True
                    db_id = user['user_id']
                    break
            if not is_registered:
                data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "middle_name": middle_name,
                    "telegram_chat_id": str(cur_user.id),
                    "can_create_review": True
                }
                headers = {
                    "Content-type": "application/json", 
                }
                response = await client.post(url=f"http://localhost:8000/api/user", 
                                            data=json.dumps(data), headers=headers)
                db_id = response.json()['user_id']

        welcome_text = f"👋 Привет, {cur_user.first_name}!\n✅ Вы успешно зарегистрированы!"

        keyboard = create_main_keyboard()
        
        user_states[str(message.from_user.id)+'_db_id'] = db_id
        
        if is_admin(user_states[str(message.from_user.id)+'_db_id']):
            await message.answer("👑 Вам доступна панель администратора", reply_markup=keyboard)
        else:
            await message.answer(welcome_text, reply_markup=keyboard)
            
        del user_states[user_id]
        
    elif user_id in user_states and user_states[user_id] == 'awaiting_review_id':
        try:
            review_id = message.text.strip()
            user_states[user_id] = 'awaiting_evaluator_id'
            user_states[str(user_id)+'_review_id'] = review_id
            
            await message.answer(f"Введите evaluator_id для назначения review_id: {review_id}")
            
        except Exception as e:
            logger.error(f"Error in review_id input: {e}")
            await message.answer("❌ Ошибка при вводе review_id")
            if user_id in user_states:
                del user_states[user_id]
                
    elif user_id in user_states and user_states[user_id] == 'awaiting_evaluator_id':
        try:
            evaluator_id = message.text.strip()
            review_id = user_states.get(str(user_id)+'_review_id')            
            
            async with httpx.AsyncClient() as client:
                data = {
                    "evaluator_user_ids": [evaluator_id],
                }
                headers = {
                    "Content-type": "application/json", 
                }
                url = f"http://localhost:8000/api/tg/reviews/{review_id}/surveys"
                response = await client.post(url, data=json.dumps(data), headers=headers)
            
            builder = InlineKeyboardBuilder()
            target_url = "http://127.0.0.1:8000" + response.json()[0]['form_link']
            builder.button(
                text="Перейти к форме",
                url=target_url
            )

            await message.answer(
                "Уникальная ссылка создана, жми на кнопку ниже:",
                reply_markup=builder.as_markup()
            )
            
            if response.status_code == 200:
                await message.answer(f"✅ Успешно назначен evaluator_id: {evaluator_id} для review_id: {review_id}")
            else:
                await message.answer(f"❌ Ошибка при назначении evaluator_id: {evaluator_id} для review_id: {review_id}")
                
            del user_states[user_id]
            del user_states[str(user_id)+'_review_id']
            
        except Exception as e:
            logger.error(f"Error in evaluator_id input: {e}")
            await message.answer("❌ Ошибка при вводе evaluator_id")
            if user_id in user_states:
                del user_states[user_id]
                if str(user_id)+'_review_id' in user_states:
                    del user_states[str(user_id)+'_review_id']

# Функция для отправки рассылки
async def send_broadcast(broadcast_id: int, message_text: str):
    try:
        async with httpx.AsyncClient() as client:
            users = await client.get(url="http://localhost:8000/api/user")
            users = [int(user['telegram_chat_id']) for user in users.json()]
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
        # ПОКА НЕ РАБОТАЕТ, НУЖНА ТАБЛИЦА BROADCAST В БД
        # update_broadcast_status(broadcast_id, 'completed', success_count, fail_count)
        
        # Отправляем отчет админу
        report = (
            f"📊 Отчет по рассылке ID: {broadcast_id}\n"
            f"✅ Успешно: {success_count}\n"
            f"❌ Неудачно: {fail_count}\n"
            f"📝 Текст: {message_text[:100]}..."
        )
        
        for user_id in users:
            try:
                await bot.send_message(user_id, report)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error in broadcast {broadcast_id}: {e}")
        # ПОКА НЕ РАБОТАЕТ, НУЖНА ТАБЛИЦА BROADCAST В БД
        # update_broadcast_status(broadcast_id, 'failed')

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
# ПОКА НЕ РАБОТАЕТ, НУЖНА ТАБЛИЦА BROADCAST В БД
# async def load_scheduled_broadcasts():
#     broadcasts = get_scheduled_broadcasts()
#     for broadcast in broadcasts:
#         if broadcast.scheduled_time > datetime.now():
#             schedule_broadcast(broadcast.id, broadcast.message_text, broadcast.scheduled_time)
#             logger.info(f"Запланирована рассылка ID: {broadcast.id} на {broadcast.scheduled_time}")

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
    # await init_db()
    
    # Загружаем запланированные рассылки
    # await load_scheduled_broadcasts()
    
    logger.info("Бот запущен!")
    
    # Запускаем бота
    await dp.start_polling(bot)

# Обработка graceful shutdown
async def shutdown():
    # await engine.dispose()
    logger.info("Бот остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
        asyncio.run(shutdown())