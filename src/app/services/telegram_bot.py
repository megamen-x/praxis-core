# app/services/telegram_bot.py
import os
import logging
from typing import Dict
from dotenv import dotenv_values

import httpx

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logger = logging.getLogger(__name__)
config = dotenv_values(".env")


class UserStates(StatesGroup):
    waiting_for_fio = State()
    waiting_for_department = State()
    waiting_for_hr_key = State()


class TelegramBotService:
    """
    Telegram bot service that handles:
    - /start: регистрация по ФИО
    - Кнопки: создать ревью, список ревью, главное меню
    - Создание ревью (только для админов)
    - Просмотр списка ревью (только для админов)
    - /cancel: отмена текущего действия
    """

    # Callback данные для кнопок
    CB_CREATE_REVIEW = "create_review"
    CB_LIST_REVIEWS = "list_reviews"
    CB_BACK_TO_MAIN = "back_to_main"
    CB_EDIT_REVIEW = "edit_review"
    
    # Тексты кнопок
    BTN_CREATE_REVIEW = "📝 Создать ревью"
    BTN_LIST_REVIEWS = "📝 Посмотреть список ревью"
    BTN_BACK_TO_MAIN = "🔙 Главное меню"
    BTN_EDIT_REVIEW = "✏️ Изменить Review"

    # Тексты
    ASK_FIO_MESSAGE = "Введите ваше имя (в формате ФИО): "
    ASK_DEPARTMENT_MESSAGE = "Укажите отдел, в котором вы работаете:"
    ASK_HR_KEY_MESSAGE = "Введите HR ключ для получения прав на создание форм:"
    WELCOME_TEMPLATE = "👋 Привет, {first_name}!\n✅ Вы успешно зарегистрированы!"
    ADMIN_PANEL_MESSAGE = "👑 Вам доступна панель администратора"
    HR_KEY = "HR2024"  # Простой HR ключ

    def __init__(self, bot_token: str, backend_url: str):
        self.bot = Bot(token=bot_token)
        storage = MemoryStorage()
        self.dp = Dispatcher(storage=storage)

        self.backend_url = backend_url

        self.user_states: Dict[int, str] = {}
        self.user_db_ids: Dict[int, str] = {}

        self._register_handlers()

    def _url(self, path: str) -> str:
        return self.backend_url.rstrip("/") + "/" + path.lstrip("/")

    def _admin_keyboard(self):
        kb = InlineKeyboardBuilder()
        kb.button(text=self.BTN_CREATE_REVIEW, callback_data=self.CB_CREATE_REVIEW)
        kb.button(text=self.BTN_LIST_REVIEWS, callback_data=self.CB_LIST_REVIEWS)
        kb.button(text="✏️ Редактировать профиль", callback_data="edit_profile")
        return kb.as_markup()

    def _user_keyboard(self):
        kb = InlineKeyboardBuilder()
        kb.button(text="✏️ Редактировать профиль", callback_data="edit_profile")
        return kb.as_markup()

    def _reviews_list_keyboard(self, reviews):
        """Создает клавиатуру со списком ревью"""
        kb = InlineKeyboardBuilder()
        for review in reviews:
            # Ограничиваем длину заголовка для кнопки
            title = review['title'][:30] + "..." if len(review['title']) > 30 else review['title']
            kb.button(text=f"📝 {title}", callback_data=f"review_{review['review_id']}")
        
        kb.button(text=self.BTN_BACK_TO_MAIN, callback_data=self.CB_BACK_TO_MAIN)
        kb.adjust(1)  # По одной кнопке в ряд
        return kb.as_markup()

    def _review_actions_keyboard(self, review_id):
        """Создает клавиатуру с действиями для конкретного ревью"""
        kb = InlineKeyboardBuilder()
        kb.button(text=self.BTN_EDIT_REVIEW, callback_data=f"edit_{review_id}")
        kb.button(text=self.BTN_BACK_TO_MAIN, callback_data=self.CB_BACK_TO_MAIN)
        kb.adjust(1)  # По одной кнопке в ряд
        return kb.as_markup()

    async def _is_admin(self, db_user_id: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self._url(f"/api/user/{db_user_id}/is_admin"))
                if resp.status_code >= 400:
                    return False
                try:
                    data = resp.json()
                    if isinstance(data, dict) and "is_admin" in data:
                        return bool(data["is_admin"])
                    if isinstance(data, bool):
                        return data
                except Exception:
                    pass
                return False
        except Exception as e:
            logger.error(f"Ошибка при проверке прав админа: {e}")
            return False

    # ----------------------------- Регистрация хендлеров ----------------------------- #
    def _register_handlers(self):
        self.dp.message.register(self.start_command, Command("start"))
        self.dp.message.register(self.cancel_command, Command("cancel"))
        self.dp.message.register(self.menu_command, Command("menu"))

        # Callback хендлеры для кнопок
        self.dp.callback_query.register(self.create_review_callback, F.data == self.CB_CREATE_REVIEW)
        self.dp.callback_query.register(self.list_reviews_callback, F.data == self.CB_LIST_REVIEWS)
        self.dp.callback_query.register(self.back_to_main_callback, F.data == self.CB_BACK_TO_MAIN)
        self.dp.callback_query.register(self.hr_key_callback, F.data == "hr_key")
        self.dp.callback_query.register(self.edit_profile_callback, F.data == "edit_profile")
        
        # Обработчики для конкретных ревью
        self.dp.callback_query.register(self.review_selected_callback, F.data.startswith("review_"))
        self.dp.callback_query.register(self.edit_review_callback, F.data.startswith("edit_"))

        # Обработчики состояний FSM
        self.dp.message.register(self.handle_fio_input, UserStates.waiting_for_fio)
        self.dp.message.register(self.handle_department_input, UserStates.waiting_for_department)
        self.dp.message.register(self.handle_hr_key_input, UserStates.waiting_for_hr_key)

    async def start_polling(self):
        await self.dp.start_polling(self.bot)

    # -------------------------------- Команды -------------------------------- #
    async def start_command(self, message: Message, state: FSMContext):
        user_id = message.from_user.id if message.from_user else None
        if not user_id:
            return
        
        await state.set_state(UserStates.waiting_for_fio)
        await message.answer(self.ASK_FIO_MESSAGE)

    async def cancel_command(self, message: Message, state: FSMContext):
        await state.clear()
        await message.answer("❌ Операция отменена. Используйте /start для начала работы.")

    async def menu_command(self, message: Message, state: FSMContext):
        user_id = message.from_user.id if message.from_user else None
        if not user_id:
            return
        # Обеспечим наличие db id пользователя в кэше
        if user_id not in self.user_db_ids:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    search_resp = await client.get(self._url(f"/api/user/telegram/{user_id}"))
                    if search_resp.status_code == 200:
                        user_info = search_resp.json()
                        self.user_db_ids[user_id] = user_info["user_id"]
                    else:
                        await message.answer("❌ Сначала зарегистрируйтесь командой /start")
                        return
            except Exception:
                await message.answer("❌ Произошла ошибка. Попробуйте позже.")
                return

        is_admin = await self._is_admin(self.user_db_ids[user_id])
        if is_admin:
            await message.answer(
                "🏠 Главное меню",
                reply_markup=self._admin_keyboard()
            )
        else:
            await message.answer(
                "🏠 Главное меню",
                reply_markup=self._user_keyboard()
            )

    # ------------------------------- Обработчики состояний ------------------------------- #
    async def handle_fio_input(self, message: Message, state: FSMContext):
        user_id = message.from_user.id if message.from_user else None
        if not user_id:
            return

        fio_text = message.text.strip()
        
        parts = fio_text.split()
        if len(parts) < 3:
            await message.answer("❌ Пожалуйста, введите ФИО в формате 'Фамилия Имя Отчество'")
            return

        last_name = parts[0]
        first_name = parts[1]
        middle_name = parts[2]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Сначала проверяем, не зарегистрирован ли пользователь уже
                search_resp = await client.get(self._url(f"/api/user/telegram/{user_id}"))
                
                if search_resp.status_code == 200:
                    # Пользователь уже зарегистрирован
                    user_info = search_resp.json()
                    self.user_db_ids[user_id] = user_info["user_id"]
                    
                    if user_info.get("can_create_review", False):
                        await message.answer(
                            f"👋 Добро пожаловать обратно, {user_info['first_name']}!\n\n{TelegramBotService.ADMIN_PANEL_MESSAGE}",
                            reply_markup=self._admin_keyboard()
                        )
                    else:
                        await message.answer(
                            f"👋 Добро пожаловать обратно, {user_info['first_name']}!"
                        )
                    
                    await state.clear()
                    return
                
                # Если пользователь не найден, сохраняем ФИО и переходим к вводу отдела
                await state.update_data(
                    first_name=first_name,
                    last_name=last_name,
                    middle_name=middle_name
                )
                await state.set_state(UserStates.waiting_for_department)
                await message.answer(self.ASK_DEPARTMENT_MESSAGE)
                    
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_department_input(self, message: Message, state: FSMContext):
        user_id = message.from_user.id if message.from_user else None
        if not user_id:
            return

        department = message.text.strip()
        if not department:
            await message.answer("❌ Пожалуйста, укажите отдел.")
            return

        try:
            # Получаем сохраненные данные ФИО
            data = await state.get_data()
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            middle_name = data.get('middle_name')

            if not all([first_name, last_name]):
                await message.answer("❌ Ошибка: данные ФИО не найдены. Начните регистрацию заново командой /start")
                await state.clear()
                return

            # Создаем пользователя с отделом
            async with httpx.AsyncClient(timeout=15.0) as client:
                user_data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "middle_name": middle_name,
                    "department": department,
                    "telegram_chat_id": str(user_id),
                    "can_create_review": False  # По умолчанию не может создавать формы
                }
                
                resp = await client.post(self._url("/api/user"), json=user_data)
                
                if resp.status_code in [200, 201]:
                    user_info = resp.json()
                    self.user_db_ids[user_id] = user_info["user_id"]
                    
                    # Создаем клавиатуру с кнопкой HR ключа
                    kb = InlineKeyboardBuilder()
                    kb.button(text="🔑 HR ключ", callback_data="hr_key")
                    kb.button(text="🔙 Главное меню", callback_data=self.CB_BACK_TO_MAIN)
                    kb.adjust(1)
                    
                    await message.answer(
                        text=f"{TelegramBotService.WELCOME_TEMPLATE.format(first_name=first_name)}\n"
                             f"🏢 Отдел: {department}\n\n"
                             f"Для создания форм введите HR ключ или перейдите в главное меню:",
                        reply_markup=kb.as_markup()
                    )
                    
                    await state.clear()
                elif resp.status_code == 400:
                    await message.answer("❌ Пользователь с таким Telegram ID уже зарегистрирован.")
                else:
                    await message.answer("❌ Ошибка при регистрации. Попробуйте еще раз.")
                    
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_hr_key_input(self, message: Message, state: FSMContext):
        user_id = message.from_user.id if message.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await message.answer("❌ Сначала зарегистрируйтесь командой /start")
            await state.clear()
            return

        hr_key = message.text.strip()
        
        if hr_key == self.HR_KEY:
            try:
                # Обновляем права пользователя
                async with httpx.AsyncClient(timeout=15.0) as client:
                    update_data = {"can_create_review": True}
                    resp = await client.put(
                        self._url(f"/api/user/{self.user_db_ids[user_id]}"), 
                        json=update_data
                    )
                    
                    if resp.status_code == 200:
                        await message.answer(
                            "✅ HR ключ принят! Теперь вы можете создавать формы.\n\n"
                            "🏠 Главное меню:",
                            reply_markup=self._admin_keyboard()
                        )
                    else:
                        await message.answer("❌ Ошибка при обновлении прав. Попробуйте позже.")
            except Exception as e:
                logger.error(f"Ошибка при обновлении прав пользователя: {e}")
                await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        else:
            await message.answer("❌ Неверный HR ключ. Попробуйте еще раз или перейдите в главное меню.")
        
        await state.clear()


    # ------------------------------- Callback обработчики ------------------------------- #
    async def create_review_callback(self, callback: CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return

        try:
            # Создаем ревью без subject_user_id (будет заполнен позже в админке)
            async with httpx.AsyncClient(timeout=15.0) as client:
                review_data = {
                    "created_by_user_id": self.user_db_ids[user_id],
                    "title": "Новое ревью",
                    "description": "Описание будет добавлено в админке"
                }
                
                review_resp = await client.post(self._url("/api/review/create"), json=review_data)
                
                if review_resp.status_code == 200:
                    review_info = review_resp.json()
                    await callback.message.edit_text(
                        f"✅ Ревью успешно создано!\n"
                        f"📝 ID ревью: {review_info['review_id']}\n\n"
                        f"Для настройки субъекта оценки и оценщиков перейдите в админку:",
                        reply_markup=self._review_actions_keyboard(review_info['review_id'])
                    )
                else:
                    await callback.message.edit_text("❌ Ошибка при создании ревью.")
        except Exception as e:
            logger.error(f"Ошибка при создании ревью: {e}")
            await callback.message.edit_text("❌ Произошла ошибка. Попробуйте позже.")
        
        await callback.answer()

    async def list_reviews_callback(self, callback: CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self._url(f"/api/user/{self.user_db_ids[user_id]}/reviews"))
                
                if resp.status_code == 200:
                    reviews = resp.json()
                    if reviews:
                        await callback.message.edit_text(
                            "📝 Выберите ревью для работы:",
                            reply_markup=self._reviews_list_keyboard(reviews)
                        )
                    else:
                        # Создаем клавиатуру с кнопкой главного меню
                        kb = InlineKeyboardBuilder()
                        kb.button(text=self.BTN_BACK_TO_MAIN, callback_data=self.CB_BACK_TO_MAIN)
                        await callback.message.edit_text(
                            "📝 У вас пока нет созданных ревью.",
                            reply_markup=kb.as_markup()
                        )
                else:
                    await callback.message.edit_text("❌ Ошибка при получении списка ревью.")
                    
        except Exception as e:
            logger.error(f"Ошибка при получении списка ревью: {e}")
            await callback.message.edit_text("❌ Произошла ошибка. Попробуйте позже.")
        
        await callback.answer()

    async def back_to_main_callback(self, callback: CallbackQuery, state: FSMContext):
        """Возврат в главное меню"""
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return

        await callback.message.edit_text(
            "🏠 Главное меню",
            reply_markup=self._admin_keyboard()
        )
        await callback.answer()

    async def review_selected_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора конкретного ревью"""
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return

        # Извлекаем review_id из callback_data
        review_id = callback.data.replace("review_", "")
        
        try:
            # Получаем информацию о ревью
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self._url(f"/api/review/{review_id}"))
                
                if resp.status_code == 200:
                    review = resp.json()
                    await callback.message.edit_text(
                        f"📝 **{review['title']}**\n\n"
                        f"📄 Описание: {review.get('description', 'Не указано')}\n"
                        f"🔒 Анонимность: {'Да' if review.get('anonymity', True) else 'Нет'}\n"
                        f"📊 Статус: {review.get('status', 'Неизвестно')}\n\n"
                        f"Выберите действие:",
                        reply_markup=self._review_actions_keyboard(review_id)
                    )
                else:
                    await callback.message.edit_text("❌ Ревью не найдено.")
                    
        except Exception as e:
            logger.error(f"Ошибка при получении ревью: {e}")
            await callback.message.edit_text("❌ Произошла ошибка. Попробуйте позже.")
        
        await callback.answer()


    async def edit_review_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка редактирования ревью - переход на сайт"""
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return

        # Извлекаем review_id из callback_data
        review_id = callback.data.replace("edit_", "")
        
        try:
            # Получаем информацию о ревью для получения ссылки
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self._url(f"/api/review/{review_id}"))
                
                if resp.status_code == 200:
                    review = resp.json()
                    review_link = review.get('review_link')
                    
                    if review_link:
                        # Создаем клавиатуру с кнопкой-ссылкой
                        kb = InlineKeyboardBuilder()
                        kb.button(text="🌐 Открыть в браузере", url=self._url(review_link))
                        kb.button(text=self.BTN_BACK_TO_MAIN, callback_data=self.CB_BACK_TO_MAIN)
                        kb.adjust(1)
                        
                        await callback.message.edit_text(
                            f"✏️ **Редактирование ревью**\n\n"
                            f"📝 {review['title']}\n\n"
                            f"Нажмите кнопку ниже, чтобы открыть страницу редактирования:",
                            reply_markup=kb.as_markup()
                        )
                    else:
                        await callback.message.edit_text(
                            f"✏️ Редактирование ревью {review_id}\n\n"
                            f"❌ Ссылка для редактирования не найдена.\n"
                            f"Обратитесь к администратору.",
                            reply_markup=self._review_actions_keyboard(review_id)
                        )
                else:
                    await callback.message.edit_text("❌ Ревью не найдено.")
                    
        except Exception as e:
            logger.error(f"Ошибка при получении ревью: {e}")
            await callback.message.edit_text("❌ Произошла ошибка. Попробуйте позже.")
        
        await callback.answer()

    async def hr_key_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка нажатия кнопки HR ключа"""
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return

        await state.set_state(UserStates.waiting_for_hr_key)
        await callback.message.edit_text(
            f"🔑 **HR ключ**\n\n{self.ASK_HR_KEY_MESSAGE}\n\n"
            f"Используйте /cancel для отмены."
        )
        await callback.answer()

    async def edit_profile_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка редактирования профиля"""
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return

        try:
            # Получаем информацию о пользователе
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self._url(f"/api/user/{self.user_db_ids[user_id]}"))
                
                if resp.status_code == 200:
                    user_info = resp.json()
                    
                    # Создаем клавиатуру для редактирования
                    kb = InlineKeyboardBuilder()
                    kb.button(text="✏️ Изменить ФИО", callback_data="edit_fio")
                    kb.button(text="🏢 Изменить отдел", callback_data="edit_department")
                    kb.button(text="🔙 Главное меню", callback_data=self.CB_BACK_TO_MAIN)
                    kb.adjust(1)
                    
                    await callback.message.edit_text(
                        f"👤 **Ваш профиль**\n\n"
                        f"📝 ФИО: {user_info['last_name']} {user_info['first_name']} {user_info.get('middle_name', '')}\n"
                        f"🏢 Отдел: {user_info.get('department', 'Не указан')}\n"
                        f"🔑 Права на создание форм: {'Да' if user_info.get('can_create_review', False) else 'Нет'}\n\n"
                        f"Выберите, что хотите изменить:",
                        reply_markup=kb.as_markup()
                    )
                else:
                    await callback.message.edit_text("❌ Ошибка при получении данных профиля.")
                    
        except Exception as e:
            logger.error(f"Ошибка при получении профиля: {e}")
            await callback.message.edit_text("❌ Произошла ошибка. Попробуйте позже.")
        
        await callback.answer()


# Глобальная переменная для хранения экземпляра бота
telegram_bot_service = None


async def start_telegram_bot():
    """Запуск телеграм-бота"""
    global telegram_bot_service
    
    bot_token = config.get("BOT_TOKEN")
    backend_url = config.get("BACKEND_URL", "http://127.0.0.1:8000")
    
    if not bot_token:
        logger.warning("BOT_TOKEN не установлен. Телеграм-бот не будет запущен.")
        return
    
    try:
        telegram_bot_service = TelegramBotService(bot_token, backend_url)
        logger.info("Запуск телеграм-бота...")
        await telegram_bot_service.start_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске телеграм-бота: {e}")


def get_telegram_bot_service():
    """Получить экземпляр телеграм-бота"""
    return telegram_bot_service
