# app/services/telegram_bot.py
import csv, io
import pandas as pd
import logging
from typing import Dict
from dotenv import dotenv_values

import httpx

from aiogram.types import ContentType
from aiogram.types import BufferedInputFile
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from src.app.core.logging import get_logs_writer_logger

logger = get_logs_writer_logger()
config = dotenv_values(".env")


class UserStates(StatesGroup):
    waiting_for_fio = State()
    waiting_for_department = State()
    waiting_for_hr_key = State()
    waiting_for_participants_file = State()
    waiting_for_report_file = State()
    editing_fio = State()
    editing_department = State()


class TelegramBotService:
    """
    Telegram bot service that handles:
    - /start: регистрация по ФИО
    - Кнопки: создать ревью, список ревью, главное меню
    - Создание ревью (только для админов)
    - Просмотр списка ревью (только для админов)
    - /cancel: отмена текущего действия
    """

    CB_CREATE_REVIEW = "create_review"
    CB_LIST_REVIEWS = "list_reviews"
    CB_BACK_TO_MAIN = "back_to_main"
    CB_VIEW_REPORT = "view_report"
    CB_EDIT_REPORT = "edit_report"
    CB_LIST_REVIEW_SURVEYS = "list_review_surveys"

    BTN_CREATE_REVIEW = "📝 Создать ревью"
    BTN_LIST_REVIEWS = "📝 Посмотреть список ревью"
    BTN_BACK_TO_MAIN = "🔙 Главное меню"
    BTN_EDIT_REVIEW = "✏️ Изменить ревью"
    BTN_VIEW_REPORT = "📄 Просмотреть отчёт"
    BTN_EDIT_REPORT = "📝 Изменить отчёт"
    BTN_VIEW_SURVEYS = "🧩 Посмотреть опросы участников"

    ASK_FIO_MESSAGE = "Введите ваше имя (в формате ФИО): "
    ASK_DEPARTMENT_MESSAGE = "Укажите отдел, в котором вы работаете:"
    ASK_HR_KEY_MESSAGE = "Введите HR ключ для получения прав на создание форм:"
    WELCOME_TEMPLATE = "👋 Привет, {first_name}!\n✅ Вы успешно зарегистрированы!"
    ADMIN_PANEL_MESSAGE = "👑 Вам доступна панель администратора"
    HR_KEY = "HR2025"

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
        kb.button(text="➕ Добавить участников", callback_data="upload_participants")
        kb.button(text="✏️ Редактировать профиль", callback_data="edit_profile")
        kb.adjust(2)
        return kb.as_markup()

    def _user_keyboard(self):
        kb = InlineKeyboardBuilder()
        kb.button(text="✏️ Редактировать профиль", callback_data="edit_profile")
        kb.button(text="🔑 HR ключ", callback_data="hr_key")
        return kb.as_markup()

    def _reviews_list_keyboard(self, reviews):
        """Создает клавиатуру со списком ревью"""
        kb = InlineKeyboardBuilder()
        for review in reviews:
            title = review['title'][:30] + "..." if len(review['title']) > 30 else review['title']
            kb.button(text=f"📝 {title}", callback_data=f"review_{review['review_id']}")
        
        kb.button(text=self.BTN_BACK_TO_MAIN, callback_data=self.CB_BACK_TO_MAIN)
        kb.adjust(1)
        return kb.as_markup()

    async def _review_actions_keyboard(self, review_id, review_link):
        """Создает клавиатуру с действиями для конкретного ревью."""
        kb = InlineKeyboardBuilder()
        kb.button(text=self.BTN_EDIT_REVIEW, url=self._url(review_link))
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                rep = await client.get(self._url(f"/api/reviews/{review_id}/report"))
                if rep.status_code == 200 and rep.json().get('file_path'):
                    kb.button(text=self.BTN_VIEW_REPORT, callback_data=f"{self.CB_VIEW_REPORT}_{review_id}")
                    print(f'{self.CB_EDIT_REPORT}_{review_id}')
                    kb.button(text=self.BTN_EDIT_REPORT, callback_data=f"{self.CB_EDIT_REPORT}_{review_id}")
        except Exception:
            pass
        kb.button(text=self.BTN_VIEW_SURVEYS, callback_data=f"{self.CB_LIST_REVIEW_SURVEYS}_{review_id}")

        kb.button(text=self.BTN_BACK_TO_MAIN, callback_data=self.CB_BACK_TO_MAIN)
        kb.adjust(1)
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

    def _register_handlers(self):
        self.dp.message.register(self.start_command, Command("start"))
        self.dp.message.register(self.cancel_command, Command("cancel"))
        self.dp.message.register(self.menu_command, Command("menu"))

        self.dp.callback_query.register(self.create_review_callback, F.data == self.CB_CREATE_REVIEW)
        self.dp.callback_query.register(self.list_reviews_callback, F.data == self.CB_LIST_REVIEWS)
        self.dp.callback_query.register(self.back_to_main_callback, F.data == self.CB_BACK_TO_MAIN)
        self.dp.callback_query.register(self.hr_key_callback, F.data == "hr_key")
        self.dp.callback_query.register(self.edit_profile_callback, F.data == "edit_profile")
        self.dp.callback_query.register(self.upload_participants_callback, F.data == "upload_participants")

        self.dp.callback_query.register(self.edit_fio_callback, F.data == "edit_fio")
        self.dp.callback_query.register(self.edit_department_callback, F.data == "edit_department")
        
        self.dp.callback_query.register(self.review_selected_callback, F.data.startswith("review_"))
        self.dp.callback_query.register(self.view_report_callback, F.data.startswith(self.CB_VIEW_REPORT))
        self.dp.callback_query.register(self.edit_report_callback, F.data.startswith(self.CB_EDIT_REPORT))
        self.dp.callback_query.register(self.list_review_surveys_callback, F.data.startswith(self.CB_LIST_REVIEW_SURVEYS))

        self.dp.message.register(self.handle_fio_input, UserStates.waiting_for_fio)
        self.dp.message.register(self.handle_department_input, UserStates.waiting_for_department)
        self.dp.message.register(self.handle_hr_key_input, UserStates.waiting_for_hr_key)
        self.dp.message.register(self.handle_participants_file, UserStates.waiting_for_participants_file)
        self.dp.message.register(self.handle_report_upload, UserStates.waiting_for_report_file)

        self.dp.message.register(self.handle_edit_fio_input, UserStates.editing_fio)
        self.dp.message.register(self.handle_edit_department_input, UserStates.editing_department)

    async def start_polling(self):
        await self.dp.start_polling(self.bot)

    async def start_command(self, message: Message, state: FSMContext):
        user_id = message.from_user.id if message.from_user else None
        if not user_id:
            return
        username = message.from_user.username if message.from_user else None
        if username:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(self._url(f"/api/user/username/{username}"))
                    if resp.status_code == 200:
                        user_info = resp.json()
                        self.user_db_ids[user_id] = user_info["user_id"]
                        if str(user_info.get("telegram_chat_id")) != str(user_id):
                            await client.put(self._url(f"/api/user/{user_info['user_id']}"), json={"telegram_chat_id": str(user_id)})
                        is_admin = await self._is_admin(user_info["user_id"])
                        if is_admin:
                            await message.answer(
                                f"👋 Добро пожаловать, {user_info['first_name']}!\n\n{TelegramBotService.ADMIN_PANEL_MESSAGE}",
                                reply_markup=self._admin_keyboard()
                            )
                        else:
                            await message.answer(
                                f"👋 Добро пожаловать, {user_info['first_name']}!",
                                reply_markup=self._user_keyboard()
                            )
                        await state.clear()
                        return
            except Exception:
                pass
        
        await state.set_state(UserStates.waiting_for_fio)
        await message.answer(self.ASK_FIO_MESSAGE)

    async def cancel_command(self, message: Message, state: FSMContext):
        await state.clear()

    async def handle_report_upload(self, message: Message, state: FSMContext):
        data = await state.get_data()
        review_id = data.get('waiting_report_upload_for')
        logger.info(f"handle_report_upload: review_id={review_id}, data={data}")
        if not review_id or not message.document:
            return
        try:
            file = await self.bot.get_file(message.document.file_id)
            file_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file.file_path}"
            async with httpx.AsyncClient(timeout=120.0) as client:
                file_bytes = (await client.get(file_url)).content
                files = {
                    'file': (message.document.file_name or 'report.pdf', file_bytes, message.document.mime_type or 'application/pdf')
                }
                upload_url = self._url(f"/api/reviews/{review_id}/report/upload")
                logger.info(f"Uploading to URL: {upload_url}")
                res = await client.post(upload_url, files=files)
                if res.status_code in (200, 201):
                    await message.answer("✅ Отчёт обновлён.", reply_markup=self._admin_keyboard())
                else:
                    await message.answer("❌ Не удалось сохранить отчёт.")
        except Exception as e:
            logger.error(f"Ошибка загрузки отчёта: {e}")
            await message.answer("❌ Ошибка загрузки отчёта.")
        finally:
            await state.clear()

    async def menu_command(self, message: Message, state: FSMContext):
        user_id = message.from_user.id if message.from_user else None
        if not user_id:
            return
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
                search_resp = await client.get(self._url(f"/api/user/telegram/{user_id}"))
                
                if search_resp.status_code == 200:
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
            data = await state.get_data()
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            middle_name = data.get('middle_name')

            if not all([first_name, last_name]):
                await message.answer("❌ Ошибка: данные ФИО не найдены. Начните регистрацию заново командой /start")
                await state.clear()
                return

            async with httpx.AsyncClient(timeout=15.0) as client:
                user_data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "middle_name": middle_name,
                    "department": department,
                    "telegram_chat_id": str(user_id),
                    "telegram_username": (message.from_user.username or None),
                    "can_create_review": False
                }
                
                resp = await client.post(self._url("/api/user"), json=user_data)
                
                if resp.status_code in [200, 201]:
                    user_info = resp.json()
                    self.user_db_ids[user_id] = user_info["user_id"]
                    
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
                    await message.answer("❌ Пользователь уже существует (telegram ID/username).")
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

    async def upload_participants_callback(self, callback: CallbackQuery, state: FSMContext):
        """Начало загрузки участников HR-ом"""
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return
        is_admin = await self._is_admin(self.user_db_ids[user_id])
        if not is_admin:
            await callback.answer("⛔ Доступно только HR", show_alert=True)
            return
        await state.set_state(UserStates.waiting_for_participants_file)
        await callback.message.edit_text(
            "📎 Отправьте CSV или XLSX файл со столбцами: last_name, first_name, middle_name (опц.), job_title (опц.), department (опц.), telegram_username (без @), can_create_review (boolean)")
        await callback.answer()

    async def view_report_callback(self, callback: CallbackQuery, state: FSMContext):
        """Отправка файла отчёта с кнопкой Главное меню"""
        review_id = callback.data.replace(f"{self.CB_VIEW_REPORT}_", "")
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                rep = await client.get(self._url(f"/api/reviews/{review_id}/report"))
                if rep.status_code != 200 or not rep.json().get('file_path'):
                    await client.post(self._url("/api/review/get_report"), data={"review_id": review_id})
                    rep = await client.get(self._url(f"/api/reviews/{review_id}/report"))
                if rep.status_code == 200 and rep.json().get('file_path'):
                    dl = await client.get(self._url(f"/api/reviews/{review_id}/report/download"))
                    if dl.status_code == 200:
                        content = dl.content
                        file_obj = BufferedInputFile(content, 'report.pdf')
                        await callback.message.answer_document(document=file_obj)
                        kb = InlineKeyboardBuilder()
                        kb.button(text=self.BTN_BACK_TO_MAIN, callback_data=self.CB_BACK_TO_MAIN)
                        await callback.message.answer("Ваш отчет", reply_markup=kb.as_markup())
                    else:
                        await callback.message.answer("❌ Не удалось скачать отчёт.")
                else:
                    await callback.message.answer("❌ Отчёт не найден и не удалось сгенерировать.")
        except Exception as e:
            logger.error(f"Ошибка при отправке отчёта: {e}")
            await callback.message.answer("❌ Произошла ошибка при получении отчёта.")
        await callback.answer()

    async def edit_report_callback(self, callback: CallbackQuery, state: FSMContext):
        """Запрос на загрузку отредактированного отчёта"""
        review_id = callback.data.replace(f"{self.CB_EDIT_REPORT}_", "")
        await state.update_data(waiting_report_upload_for=review_id)
        await state.set_state(UserStates.waiting_for_report_file)
        kb = InlineKeyboardBuilder()
        kb.button(text=self.BTN_BACK_TO_MAIN, callback_data=self.CB_BACK_TO_MAIN)
        await callback.message.edit_text("📝 Загрузите отредактированный файл отчёта (PDF).", reply_markup=kb.as_markup())
        await callback.answer()

    async def handle_participants_file(self, message: Message, state: FSMContext):
        """Обработка полученного файла с участниками"""
        
        if not message.document:
            await message.answer("❌ Пришлите файл как документ (CSV/XLSX).")
            return
        doc = message.document
        file_name = doc.file_name or "participants"
        try:
            file = await self.bot.get_file(doc.file_id)
            file_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file.file_path}"
            async with httpx.AsyncClient(timeout=60.0) as client:
                file_bytes = (await client.get(file_url)).content
            rows: list[dict] = []
            if file_name.lower().endswith('.csv'):
                text = file_bytes.decode('utf-8', errors='ignore')
                reader = csv.DictReader(io.StringIO(text))
                rows = [r for r in reader]
            elif file_name.lower().endswith('.xlsx'):
                try:
                    df = pd.read_excel(io.BytesIO(file_bytes))
                    rows = df.to_dict(orient='records')
                except Exception:
                    await message.answer("❌ Не удалось прочитать XLSX. Отправьте CSV.")
                    await state.clear()
                    return
            else:
                await message.answer("❌ Неподдерживаемый формат. Пришлите .csv или .xlsx")
                return
            created, skipped = 0, 0
            async with httpx.AsyncClient(timeout=15.0) as client:
                for r in rows:
                    ln = (r.get('last_name') or r.get('surname') or '').strip()
                    fn = (r.get('first_name') or r.get('name') or '').strip()
                    mn = (r.get('middle_name') or r.get('patronymic') or '').strip() or None
                    jt = (r.get('job_title') or r.get('position') or '').strip() or None
                    dp = (r.get('department') or '').strip() or None
                    un = (r.get('telegram_username') or r.get('username') or '').strip().lstrip('@') or None
                    cr = (r.get('can_create_review') or False)
                    if not ln or not fn or not un:
                        skipped += 1
                        continue
                    payload = {
                        "first_name": fn,
                        "last_name": ln,
                        "middle_name": mn,
                        "job_title": jt,
                        "department": dp,
                        "telegram_username": un,
                        "can_create_review": cr,
                    }
                    resp = await client.post(self._url("/api/user"), json=payload)
                    if resp.status_code in (200, 201):
                        created += 1
                    else:
                        skipped += 1
            await message.answer(f"✅ Готово. Создано: {created}. Пропущено: {skipped}.")
        except Exception as e:
            logger.error(f"Ошибка обработки файла участников: {e}")
            await message.answer("❌ Произошла ошибка при обработке файла.")
        finally:
            await state.clear()

    async def create_review_callback(self, callback: CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return

        try:
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
                        reply_markup=await self._review_actions_keyboard(review_info['review_id'], review_info['review_link'])
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

        review_id = callback.data.replace("review_", "")
        
        try:
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
                        reply_markup=await self._review_actions_keyboard(review_id, review.get('review_link'))
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
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self._url(f"/api/user/{self.user_db_ids[user_id]}"))
                
                if resp.status_code == 200:
                    user_info = resp.json()
                    
                    kb = InlineKeyboardBuilder()
                    kb.button(text="✏️ Изменить ФИО", callback_data="edit_fio")
                    kb.button(text="🏢 Изменить отдел", callback_data="edit_department")
                    if not user_info.get('can_create_review', False):
                        kb.button(text="🔑 Ввести HR ключ", callback_data="hr_key")
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

    async def edit_fio_callback(self, callback: CallbackQuery, state: FSMContext):
        """Начать изменение ФИО"""
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return
        await state.set_state(UserStates.editing_fio)
        await callback.message.edit_text("✏️ Введите новое ФИО в формате 'Фамилия Имя Отчество' (отчество опционально).\nИспользуйте /cancel для отмены.")
        await callback.answer()

    async def edit_department_callback(self, callback: CallbackQuery, state: FSMContext):
        """Начать изменение отдела"""
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return
        await state.set_state(UserStates.editing_department)
        await callback.message.edit_text("🏢 Введите новый отдел.\nИспользуйте /cancel для отмены.")
        await callback.answer()

    async def handle_edit_fio_input(self, message: Message, state: FSMContext):
        """Обновление ФИО существующего пользователя"""
        user_id = message.from_user.id if message.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await message.answer("❌ Сначала зарегистрируйтесь командой /start")
            await state.clear()
            return
        fio_text = (message.text or "").strip()
        parts = fio_text.split()
        if len(parts) < 2:
            await message.answer("❌ Пожалуйста, введите как минимум Фамилию и Имя.")
            return
        last_name = parts[0]
        first_name = parts[1]
        middle_name = parts[2] if len(parts) >= 3 else None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                update = {"first_name": first_name, "last_name": last_name, "middle_name": middle_name}
                resp = await client.put(self._url(f"/api/user/{self.user_db_ids[user_id]}"), json=update)
                if resp.status_code == 200:
                    await message.answer("✅ ФИО обновлено.", reply_markup=self._user_keyboard())
                else:
                    await message.answer("❌ Не удалось обновить ФИО. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка обновления ФИО: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        finally:
            await state.clear()

    async def handle_edit_department_input(self, message: Message, state: FSMContext):
        """Обновление отдела существующего пользователя"""
        user_id = message.from_user.id if message.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await message.answer("❌ Сначала зарегистрируйтесь командой /start")
            await state.clear()
            return
        department = (message.text or "").strip()
        if not department:
            await message.answer("❌ Пожалуйста, укажите отдел.")
            return
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                update = {"department": department}
                resp = await client.put(self._url(f"/api/user/{self.user_db_ids[user_id]}"), json=update)
                if resp.status_code == 200:
                    await message.answer("✅ Отдел обновлён.", reply_markup=self._user_keyboard())
                else:
                    await message.answer("❌ Не удалось обновить отдел. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка обновления отдела: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        finally:
            await state.clear()

    async def list_review_surveys_callback(self, callback: CallbackQuery, state: FSMContext):
        """Показать список опросов для ревью с ссылками на просмотр."""
        user_id = callback.from_user.id if callback.from_user else None
        if not user_id or user_id not in self.user_db_ids:
            await callback.answer("❌ Сначала зарегистрируйтесь командой /start", show_alert=True)
            return

        is_admin = await self._is_admin(self.user_db_ids[user_id])
        if not is_admin:
            await callback.answer("⛔ Доступно только HR", show_alert=True)
            return

        review_id = callback.data.replace(f"{self.CB_LIST_REVIEW_SURVEYS}_", "")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self._url(f"/api/reviews/{review_id}/surveys"))
                if resp.status_code != 200:
                    await callback.message.edit_text("❌ Не удалось получить список опросов.")
                    await callback.answer()
                    return
                surveys = resp.json()

                kb = InlineKeyboardBuilder()
                if not surveys:
                    kb.button(text=self.BTN_BACK_TO_MAIN, callback_data=self.CB_BACK_TO_MAIN)
                    await callback.message.edit_text("Опросы отсутствуют.", reply_markup=kb.as_markup())
                    await callback.answer()
                    return

                for idx, s in enumerate(surveys, start=1):
                    surv_id = s.get('survey_id')
                    status = s.get('status')
                    link_resp = await client.get(self._url(f"/api/surveys/{surv_id}/admin_link"))
                    url = None
                    if link_resp.status_code == 200:
                        url = self._url(link_resp.json().get('url', ''))
                    btn_text = f"Опрос {idx}"
                    if url:
                        kb.button(text=btn_text, url=url)
                    else:
                        kb.button(text=f"{btn_text} (без ссылки)", callback_data=self.CB_BACK_TO_MAIN)

                kb.button(text="↩️ Назад к ревью", callback_data=f"review_{review_id}")
                kb.button(text=self.BTN_BACK_TO_MAIN, callback_data=self.CB_BACK_TO_MAIN)
                kb.adjust(1)
                await callback.message.edit_text("Выберите опрос для просмотра:", reply_markup=kb.as_markup())
        except Exception as e:
            logger.error(f"Ошибка при получении опросов ревью: {e}")
            await callback.message.edit_text("❌ Произошла ошибка при получении списка опросов.")
        await callback.answer()


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
