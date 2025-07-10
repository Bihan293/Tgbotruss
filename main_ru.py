"""
Telegram Gate Bot - Secure Channel Subscription Verification Bot
Created for resale as a lightweight, production-ready solution.

Features:
- Encrypted activation code protection
- Channel subscription verification
- Admin panel with full management
- File-based storage system
- Prize management (text, photo, video, link)
- Optimized for 100+ concurrent users
- Self-destruct mechanism against tampering
- Russian interface throughout

Author: Senior Telegram Bot Developer
License: Commercial Resale License
"""

import asyncio
import json
import os
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiofiles
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, 
    Message, CallbackQuery, ContentType
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
import sys
import traceback

# ==================== CONFIGURATION ====================

# IMPORTANT: Replace these placeholders with your actual values
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Get from @BotFather
ADMIN_USER_ID = 123456789  # Replace with your Telegram User ID

# Encrypted activation code (DO NOT MODIFY OR REMOVE)
# Original code: G7m$K2zQ
ENCRYPTED_ACTIVATION_CODE = "fe4cad7e1e8bd0d34c33ba3f88ffa43f97272e3974ffacf6b918aadf81ab2e18"  # SHA256 hash

# File paths for data storage
CHANNELS_FILE = "channels.json"
PRIZE_FILE = "prize.dat"
ACTIVATION_FILE = "activation.dat"
LOG_FILE = "bot.log"

# Bot configuration
MAX_USERS_PER_SECOND = 30  # Rate limiting
ADMIN_PANEL_TIMEOUT = 300  # 5 minutes timeout for admin operations

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== FSM STATES ====================

class AdminStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_prize = State()
    waiting_for_prize_confirmation = State()
    waiting_for_activation_code = State()

# ==================== SECURITY SYSTEM ====================

class SecuritySystem:
    """Enhanced security system with self-destruct mechanism"""
    
    @staticmethod
    def encrypt_code(code: str) -> str:
        """Encrypt activation code using SHA256"""
        return hashlib.sha256(code.encode()).hexdigest()
    
    @staticmethod
    def verify_activation_code(input_code: str) -> bool:
        """Verify if input code matches encrypted activation code"""
        return SecuritySystem.encrypt_code(input_code) == ENCRYPTED_ACTIVATION_CODE
    
    @staticmethod
    def check_code_integrity():
        """Check if activation code section has been tampered with"""
        # This function checks if the encrypted code is still present
        current_code = globals().get('ENCRYPTED_ACTIVATION_CODE', '')
        if not current_code or current_code != "fe4cad7e1e8bd0d34c33ba3f88ffa43f97272e3974ffacf6b918aadf81ab2e18":
            SecuritySystem.trigger_self_destruct()
    
    @staticmethod
    def trigger_self_destruct():
        """Self-destruct mechanism if tampering is detected"""
        logger.critical("SECURITY BREACH DETECTED - ACTIVATING SELF-DESTRUCT")
        
        # Create self-destruct marker
        with open("SELF_DESTRUCT_ACTIVATED.txt", "w") as f:
            f.write(f"Bot self-destructed due to tampering at {datetime.now()}")
        
        # Clear all data files
        for file_path in [CHANNELS_FILE, PRIZE_FILE, ACTIVATION_FILE]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        
        # Exit the application
        logger.critical("Bot has been permanently disabled due to security breach")
        sys.exit(1)

# ==================== DATA STORAGE SYSTEM ====================

class DataManager:
    """File-based data storage with crash recovery"""
    
    @staticmethod
    async def load_json(file_path: str, default: Any = None) -> Any:
        """Load JSON data from file with error handling"""
        try:
            if os.path.exists(file_path):
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            return default if default is not None else {}
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return default if default is not None else {}
    
    @staticmethod
    async def save_json(file_path: str, data: Any) -> bool:
        """Save JSON data to file with atomic write"""
        try:
            temp_path = f"{file_path}.tmp"
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Atomic rename
            os.replace(temp_path, file_path)
            logger.info(f"Data saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
            return False
    
    @staticmethod
    async def load_prize() -> Dict[str, Any]:
        """Load prize data from file"""
        return await DataManager.load_json(PRIZE_FILE, {
            'type': 'text',
            'content': 'Приз еще не установлен.',
            'created_at': datetime.now().isoformat()
        })
    
    @staticmethod
    async def save_prize(prize_data: Dict[str, Any]) -> bool:
        """Save prize data to file"""
        prize_data['updated_at'] = datetime.now().isoformat()
        return await DataManager.save_json(PRIZE_FILE, prize_data)
    
    @staticmethod
    async def load_channels() -> List[str]:
        """Load channels list from file"""
        data = await DataManager.load_json(CHANNELS_FILE, {'channels': []})
        return data.get('channels', [])
    
    @staticmethod
    async def save_channels(channels: List[str]) -> bool:
        """Save channels list to file"""
        data = {
            'channels': channels,
            'updated_at': datetime.now().isoformat()
        }
        return await DataManager.save_json(CHANNELS_FILE, data)
    
    @staticmethod
    async def is_bot_activated() -> bool:
        """Check if bot is activated"""
        return os.path.exists(ACTIVATION_FILE)
    
    @staticmethod
    async def activate_bot() -> bool:
        """Mark bot as activated"""
        try:
            async with aiofiles.open(ACTIVATION_FILE, 'w') as f:
                await f.write(f"Activated at {datetime.now().isoformat()}")
            return True
        except Exception as e:
            logger.error(f"Error activating bot: {e}")
            return False

# ==================== CHANNEL VERIFICATION ====================

class ChannelVerifier:
    """Channel subscription verification system"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.session = None
    
    async def init_session(self):
        """Initialize aiohttp session for API calls"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
    
    async def is_user_subscribed(self, user_id: int, channel_username: str) -> bool:
        """Check if user is subscribed to a specific channel"""
        try:
            # Remove @ if present
            channel_username = channel_username.replace('@', '')
            
            # Try to get chat member info
            try:
                member = await self.bot.get_chat_member(
                    chat_id=f"@{channel_username}", 
                    user_id=user_id
                )
                
                # Check if user is subscribed (member, administrator, creator)
                return member.status in ['member', 'administrator', 'creator']
            
            except Exception as e:
                logger.warning(f"Error checking subscription for @{channel_username}: {e}")
                return False
        
        except Exception as e:
            logger.error(f"Error in subscription check: {e}")
            return False
    
    async def verify_all_subscriptions(self, user_id: int) -> tuple[bool, List[str]]:
        """Verify user subscription to all required channels"""
        channels = await DataManager.load_channels()
        if not channels:
            return True, []  # No channels required
        
        unsubscribed_channels = []
        
        for channel in channels:
            if not await self.is_user_subscribed(user_id, channel):
                unsubscribed_channels.append(channel)
        
        return len(unsubscribed_channels) == 0, unsubscribed_channels
    
    async def validate_channel_exists(self, channel_username: str) -> bool:
        """Validate if channel exists and bot can access it"""
        try:
            channel_username = channel_username.replace('@', '')
            await self.bot.get_chat(f"@{channel_username}")
            return True
        except Exception as e:
            logger.error(f"Channel validation failed for @{channel_username}: {e}")
            return False

# ==================== KEYBOARD BUILDERS ====================

class KeyboardBuilder:
    """Dynamic keyboard builder for admin panel"""
    
    @staticmethod
    def main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
        """Build main menu keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.add(InlineKeyboardButton(
            text="🎁 Получить приз",
            callback_data="get_prize"
        ))
        
        if is_admin:
            builder.add(InlineKeyboardButton(
                text="⚙️ Панель администратора",
                callback_data="admin_panel"
            ))
        
        builder.adjust(1)
        return builder.as_markup()
    
    @staticmethod
    def admin_panel_keyboard() -> InlineKeyboardMarkup:
        """Build admin panel keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.add(InlineKeyboardButton(
            text="📺 Управление каналами",
            callback_data="edit_channels"
        ))
        
        builder.add(InlineKeyboardButton(
            text="🎁 Управление призом",
            callback_data="edit_prize"
        ))
        
        builder.add(InlineKeyboardButton(
            text="🔙 Назад в главное меню",
            callback_data="main_menu"
        ))
        
        builder.adjust(1)
        return builder.as_markup()
    
    @staticmethod
    def edit_channels_keyboard() -> InlineKeyboardMarkup:
        """Build edit channels keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.add(InlineKeyboardButton(
            text="➕ Добавить канал",
            callback_data="add_channel"
        ))
        
        builder.add(InlineKeyboardButton(
            text="🗑️ Удалить канал",
            callback_data="delete_channel"
        ))
        
        builder.add(InlineKeyboardButton(
            text="📋 Список каналов",
            callback_data="list_channels"
        ))
        
        builder.add(InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="admin_panel"
        ))
        
        builder.adjust(1)
        return builder.as_markup()
    
    @staticmethod
    def edit_prize_keyboard() -> InlineKeyboardMarkup:
        """Build edit prize keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.add(InlineKeyboardButton(
            text="👀 Показать текущий приз",
            callback_data="show_prize"
        ))
        
        builder.add(InlineKeyboardButton(
            text="✏️ Изменить приз",
            callback_data="edit_prize_content"
        ))
        
        builder.add(InlineKeyboardButton(
            text="🗑️ Удалить приз",
            callback_data="delete_prize"
        ))
        
        builder.add(InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="admin_panel"
        ))
        
        builder.adjust(1)
        return builder.as_markup()
    
    @staticmethod
    def channel_delete_keyboard(channels: List[str]) -> InlineKeyboardMarkup:
        """Build channel deletion keyboard"""
        builder = InlineKeyboardBuilder()
        
        for channel in channels:
            builder.add(InlineKeyboardButton(
                text=f"❌ @{channel}",
                callback_data=f"delete_channel_{channel}"
            ))
        
        builder.add(InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="edit_channels"
        ))
        
        builder.adjust(1)
        return builder.as_markup()
    
    @staticmethod
    def confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
        """Build confirmation keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.add(InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"confirm_{action}"
        ))
        
        builder.add(InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_action"
        ))
        
        builder.row()
        return builder.as_markup()
    
    @staticmethod
    def subscription_keyboard(channels: List[str]) -> InlineKeyboardMarkup:
        """Build subscription verification keyboard"""
        builder = InlineKeyboardBuilder()
        
        for channel in channels:
            builder.add(InlineKeyboardButton(
                text=f"📺 @{channel}",
                url=f"https://t.me/{channel}"
            ))
        
        builder.add(InlineKeyboardButton(
            text="✅ Я подписался",
            callback_data="check_subscription"
        ))
        
        builder.adjust(1)
        return builder.as_markup()

# ==================== MAIN BOT CLASS ====================

class TelegramGateBot:
    """Main bot class with all functionality"""
    
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.channel_verifier = ChannelVerifier(self.bot)
        self.rate_limiter = {}
        
        # Security check on initialization
        SecuritySystem.check_code_integrity()
        
        # Register handlers
        self.register_handlers()
    
    def register_handlers(self):
        """Register all bot handlers"""
        
        # Command handlers
        self.dp.message.register(self.start_command, Command("start"))
        self.dp.message.register(self.help_command, Command("help"))
        
        # Activation code handler
        self.dp.message.register(
            self.activation_code_handler,
            StateFilter(AdminStates.waiting_for_activation_code)
        )
        
        # Admin state handlers
        self.dp.message.register(
            self.channel_input_handler,
            StateFilter(AdminStates.waiting_for_channel)
        )
        
        self.dp.message.register(
            self.prize_input_handler,
            StateFilter(AdminStates.waiting_for_prize)
        )
        
        # Callback handlers
        self.dp.callback_query.register(self.callback_handler)
        
        # Text message handler (for activation code)
        self.dp.message.register(self.text_message_handler)
    
    async def start_command(self, message: Message, state: FSMContext):
        """Handle /start command"""
        try:
            # Check if bot is activated
            if not await DataManager.is_bot_activated():
                await message.answer(
                    "🔐 **Требуется активация бота**\n\n"
                    "Для начала работы этого бота необходим код активации.\n"
                    "Пожалуйста, введите код активации:",
                    parse_mode=ParseMode.MARKDOWN
                )
                await state.set_state(AdminStates.waiting_for_activation_code)
                return
            
            # Check rate limiting
            if not await self.check_rate_limit(message.from_user.id):
                await message.answer("⏰ Пожалуйста, подождите немного перед повторным использованием бота.")
                return
            
            is_admin = message.from_user.id == ADMIN_USER_ID
            
            welcome_text = (
                "🎉 **Добро пожаловать в Gate Bot!**\n\n"
                "Этот бот предоставляет эксклюзивные призы пользователям, "
                "которые подписаны на наши обязательные каналы.\n\n"
                "Нажмите на кнопку ниже, чтобы получить свой приз!"
            )
            
            if is_admin:
                welcome_text += "\n\n👑 **Обнаружен доступ администратора**"
            
            await message.answer(
                welcome_text,
                reply_markup=KeyboardBuilder.main_menu_keyboard(is_admin),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.")
    
    async def help_command(self, message: Message):
        """Handle /help command"""
        help_text = (
            "🆘 **Помощь по боту**\n\n"
            "**Доступные команды:**\n"
            "• /start - Запустить бота\n"
            "• /help - Показать это сообщение помощи\n\n"
            "**Как использовать:**\n"
            "1. Нажмите 'Получить приз' для получения вашей награды\n"
            "2. Подпишитесь на все необходимые каналы\n"
            "3. Подтвердите подписку для получения приза\n\n"
            "**Нужна поддержка?** Свяжитесь с администратором бота."
        )
        
        await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def activation_code_handler(self, message: Message, state: FSMContext):
        """Handle activation code input"""
        try:
            input_code = message.text.strip()
            
            if SecuritySystem.verify_activation_code(input_code):
                # Activate the bot
                if await DataManager.activate_bot():
                    await message.answer(
                        "✅ **Бот успешно активирован!**\n\n"
                        "Бот теперь готов к использованию. Используйте /start для начала.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    await state.clear()
                    logger.info(f"Bot activated by user {message.from_user.id}")
                else:
                    await message.answer("❌ Активация не удалась. Пожалуйста, попробуйте еще раз.")
            else:
                await message.answer(
                    "❌ **Неверный код активации**\n\n"
                    "Пожалуйста, введите правильный код активации:"
                )
        
        except Exception as e:
            logger.error(f"Error in activation code handler: {e}")
            await message.answer("❌ Произошла ошибка во время активации.")
    
    async def text_message_handler(self, message: Message, state: FSMContext):
        """Handle text messages (activation code when bot is not activated)"""
        if not await DataManager.is_bot_activated():
            await self.activation_code_handler(message, state)
    
    async def callback_handler(self, callback: CallbackQuery, state: FSMContext):
        """Handle all callback queries"""
        try:
            await callback.answer()
            
            # Check if bot is activated
            if not await DataManager.is_bot_activated():
                await callback.message.answer("🔐 Бот еще не активирован.")
                return
            
            # Check rate limiting
            if not await self.check_rate_limit(callback.from_user.id):
                await callback.message.answer("⏰ Пожалуйста, подождите немного перед повторным использованием бота.")
                return
            
            data = callback.data
            user_id = callback.from_user.id
            is_admin = user_id == ADMIN_USER_ID
            
            # Main menu actions
            if data == "main_menu":
                await self.show_main_menu(callback.message, is_admin)
            
            elif data == "get_prize":
                await self.handle_get_prize(callback.message, user_id)
            
            elif data == "check_subscription":
                await self.handle_check_subscription(callback.message, user_id)
            
            # Admin panel actions
            elif data == "admin_panel" and is_admin:
                await self.show_admin_panel(callback.message)
            
            elif data == "edit_channels" and is_admin:
                await self.show_edit_channels(callback.message)
            
            elif data == "edit_prize" and is_admin:
                await self.show_edit_prize(callback.message)
            
            # Channel management
            elif data == "add_channel" and is_admin:
                await self.start_add_channel(callback.message, state)
            
            elif data == "delete_channel" and is_admin:
                await self.show_delete_channels(callback.message)
            
            elif data == "list_channels" and is_admin:
                await self.show_list_channels(callback.message)
            
            elif data.startswith("delete_channel_") and is_admin:
                channel = data.replace("delete_channel_", "")
                await self.delete_channel(callback.message, channel)
            
            # Prize management
            elif data == "show_prize" and is_admin:
                await self.show_current_prize(callback.message)
            
            elif data == "edit_prize_content" and is_admin:
                await self.start_edit_prize(callback.message, state)
            
            elif data == "delete_prize" and is_admin:
                await self.show_delete_prize_confirmation(callback.message)
            
            elif data == "confirm_delete_prize" and is_admin:
                await self.confirm_delete_prize(callback.message)
            
            # General actions
            elif data == "cancel_action":
                await state.clear()
                await callback.message.answer("❌ Действие отменено.")
            
            else:
                await callback.message.answer("❌ Неизвестное действие.")
        
        except Exception as e:
            logger.error(f"Error in callback handler: {e}")
            await callback.message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.")
    
    async def show_main_menu(self, message: Message, is_admin: bool):
        """Show main menu"""
        welcome_text = (
            "🎉 **Добро пожаловать в Gate Bot!**\n\n"
            "Этот бот предоставляет эксклюзивные призы пользователям, "
            "которые подписаны на наши обязательные каналы.\n\n"
            "Нажмите на кнопку ниже, чтобы получить свой приз!"
        )
        
        if is_admin:
            welcome_text += "\n\n👑 **Обнаружен доступ администратора**"
        
        await message.edit_text(
            welcome_text,
            reply_markup=KeyboardBuilder.main_menu_keyboard(is_admin),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_get_prize(self, message: Message, user_id: int):
        """Handle get prize request"""
        try:
            # Check channel subscriptions
            is_subscribed, unsubscribed_channels = await self.channel_verifier.verify_all_subscriptions(user_id)
            
            if not is_subscribed:
                channels_text = "\n".join([f"• @{channel}" for channel in unsubscribed_channels])
                
                await message.edit_text(
                    "🚫 **Требуется подписка**\n\n"
                    f"Вы должны подписаться на следующие каналы, чтобы получить свой приз:\n\n"
                    f"{channels_text}\n\n"
                    "Нажмите на кнопки каналов ниже для подписки, затем нажмите 'Я подписался' для проверки:",
                    reply_markup=KeyboardBuilder.subscription_keyboard(unsubscribed_channels),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # User is subscribed, give prize
            await self.give_prize(message, user_id)
        
        except Exception as e:
            logger.error(f"Error in handle_get_prize: {e}")
            await message.answer("❌ Произошла ошибка при проверке вашей подписки.")
    
    async def handle_check_subscription(self, message: Message, user_id: int):
        """Handle subscription verification"""
        try:
            is_subscribed, unsubscribed_channels = await self.channel_verifier.verify_all_subscriptions(user_id)
            
            if is_subscribed:
                await self.give_prize(message, user_id)
            else:
                channels_text = "\n".join([f"• @{channel}" for channel in unsubscribed_channels])
                
                await message.edit_text(
                    "❌ **Проверка подписки не удалась**\n\n"
                    f"Вы не подписаны на следующие каналы:\n\n"
                    f"{channels_text}\n\n"
                    "Пожалуйста, подпишитесь на все каналы и попробуйте еще раз:",
                    reply_markup=KeyboardBuilder.subscription_keyboard(unsubscribed_channels),
                    parse_mode=ParseMode.MARKDOWN
                )
        
        except Exception as e:
            logger.error(f"Error in handle_check_subscription: {e}")
            await message.answer("❌ Произошла ошибка при проверке вашей подписки.")
    
    async def give_prize(self, message: Message, user_id: int):
        """Give prize to user"""
        try:
            prize_data = await DataManager.load_prize()
            
            success_text = (
                "🎉 **Поздравляем!**\n\n"
                "Вы успешно подтвердили свою подписку. Вот ваш приз:\n\n"
            )
            
            if prize_data['type'] == 'text':
                await message.edit_text(
                    success_text + prize_data['content'],
                    reply_markup=KeyboardBuilder.main_menu_keyboard(user_id == ADMIN_USER_ID),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            elif prize_data['type'] == 'photo':
                await message.delete()
                await message.answer_photo(
                    photo=prize_data['content'],
                    caption=success_text + prize_data.get('caption', ''),
                    reply_markup=KeyboardBuilder.main_menu_keyboard(user_id == ADMIN_USER_ID),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            elif prize_data['type'] == 'video':
                await message.delete()
                await message.answer_video(
                    video=prize_data['content'],
                    caption=success_text + prize_data.get('caption', ''),
                    reply_markup=KeyboardBuilder.main_menu_keyboard(user_id == ADMIN_USER_ID),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            elif prize_data['type'] == 'document':
                await message.delete()
                await message.answer_document(
                    document=prize_data['content'],
                    caption=success_text + prize_data.get('caption', ''),
                    reply_markup=KeyboardBuilder.main_menu_keyboard(user_id == ADMIN_USER_ID),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            else:
                await message.edit_text(
                    success_text + prize_data['content'],
                    reply_markup=KeyboardBuilder.main_menu_keyboard(user_id == ADMIN_USER_ID),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            logger.info(f"Prize given to user {user_id}")
        
        except Exception as e:
            logger.error(f"Error giving prize: {e}")
            await message.answer("❌ Произошла ошибка при выдаче вашего приза.")
    
    # ==================== ADMIN PANEL METHODS ====================
    
    async def show_admin_panel(self, message: Message):
        """Show admin panel"""
        await message.edit_text(
            "⚙️ **Панель администратора**\n\n"
            "Выберите опцию ниже для управления вашим ботом:",
            reply_markup=KeyboardBuilder.admin_panel_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_edit_channels(self, message: Message):
        """Show edit channels menu"""
        channels = await DataManager.load_channels()
        channels_count = len(channels)
        
        await message.edit_text(
            f"📺 **Управление каналами**\n\n"
            f"Сейчас управляем **{channels_count}** каналами.\n\n"
            f"Выберите действие ниже:",
            reply_markup=KeyboardBuilder.edit_channels_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_edit_prize(self, message: Message):
        """Show edit prize menu"""
        prize_data = await DataManager.load_prize()
        
        await message.edit_text(
            f"🎁 **Управление призом**\n\n"
            f"Текущий тип приза: **{prize_data['type']}**\n\n"
            f"Выберите действие ниже:",
            reply_markup=KeyboardBuilder.edit_prize_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def start_add_channel(self, message: Message, state: FSMContext):
        """Start adding a channel"""
        await message.edit_text(
            "➕ **Добавить канал**\n\n"
            "Пожалуйста, отправьте имя канала (например, @examplechannel):\n\n"
            "⚠️ Убедитесь, что канал существует и является публичным.\n\n"
            "Отправьте /cancel для отмены этой операции.",
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(AdminStates.waiting_for_channel)
    
    async def channel_input_handler(self, message: Message, state: FSMContext):
        """Handle channel input"""
        try:
            if message.text == "/cancel":
                await state.clear()
                await message.answer("❌ Добавление канала отменено.")
                return
            
            channel_username = message.text.strip().replace('@', '')
            
            # Validate channel exists
            if not await self.channel_verifier.validate_channel_exists(channel_username):
                await message.answer(
                    "❌ **Канал не найден**\n\n"
                    "Канал @{} не существует или недоступен.\n\n"
                    "Пожалуйста, проверьте имя и попробуйте еще раз:".format(channel_username)
                )
                return
            
            # Load current channels
            channels = await DataManager.load_channels()
            
            # Check if channel already exists
            if channel_username in channels:
                await message.answer(
                    f"⚠️ **Канал уже существует**\n\n"
                    f"Канал @{channel_username} уже есть в списке.\n\n"
                    f"Пожалуйста, введите другой канал:"
                )
                return
            
            # Add channel
            channels.append(channel_username)
            
            if await DataManager.save_channels(channels):
                await message.answer(
                    f"✅ **Канал успешно добавлен**\n\n"
                    f"Канал @{channel_username} был добавлен в список обязательных каналов.\n\n"
                    f"Всего каналов: {len(channels)}"
                )
                await state.clear()
                logger.info(f"Channel @{channel_username} added by admin")
            else:
                await message.answer("❌ Не удалось сохранить канал. Пожалуйста, попробуйте еще раз.")
        
        except Exception as e:
            logger.error(f"Error in channel input handler: {e}")
            await message.answer("❌ Произошла ошибка при добавлении канала.")
    
    async def show_delete_channels(self, message: Message):
        """Show delete channels menu"""
        channels = await DataManager.load_channels()
        
        if not channels:
            await message.edit_text(
                "📺 **Удалить каналы**\n\n"
                "Каналы в списке не найдены.\n\n"
                "Используйте 'Добавить канал' для добавления каналов сначала.",
                reply_markup=KeyboardBuilder.edit_channels_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await message.edit_text(
            f"🗑️ **Удалить каналы**\n\n"
            f"Выберите канал для удаления:\n\n"
            f"Всего каналов: {len(channels)}",
            reply_markup=KeyboardBuilder.channel_delete_keyboard(channels),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def delete_channel(self, message: Message, channel_username: str):
        """Delete a channel"""
        try:
            channels = await DataManager.load_channels()
            
            if channel_username in channels:
                channels.remove(channel_username)
                
                if await DataManager.save_channels(channels):
                    await message.edit_text(
                        f"✅ **Канал удален**\n\n"
                        f"Канал @{channel_username} был удален из списка.\n\n"
                        f"Осталось каналов: {len(channels)}",
                        reply_markup=KeyboardBuilder.edit_channels_keyboard(),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logger.info(f"Channel @{channel_username} deleted by admin")
                else:
                    await message.answer("❌ Не удалось сохранить изменения. Пожалуйста, попробуйте еще раз.")
            else:
                await message.answer("❌ Канал не найден в списке.")
        
        except Exception as e:
            logger.error(f"Error deleting channel: {e}")
            await message.answer("❌ Произошла ошибка при удалении канала.")
    
    async def show_list_channels(self, message: Message):
        """Show list of channels"""
        channels = await DataManager.load_channels()
        
        if not channels:
            channels_text = "Каналы пока не настроены."
        else:
            channels_text = "\n".join([f"• @{channel}" for channel in channels])
        
        await message.edit_text(
            f"📋 **Список каналов**\n\n"
            f"Обязательные каналы ({len(channels)}):\n\n"
            f"{channels_text}",
            reply_markup=KeyboardBuilder.edit_channels_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_current_prize(self, message: Message):
        """Show current prize"""
        try:
            prize_data = await DataManager.load_prize()
            
            preview_text = (
                f"👀 **Текущий приз**\n\n"
                f"Тип: **{prize_data['type']}**\n"
                f"Создан: {prize_data.get('created_at', 'Неизвестно')}\n\n"
            )
            
            if prize_data['type'] == 'text':
                preview_text += f"Содержание:\n{prize_data['content']}"
                await message.edit_text(
                    preview_text,
                    reply_markup=KeyboardBuilder.edit_prize_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            elif prize_data['type'] in ['photo', 'video', 'document']:
                await message.delete()
                caption = preview_text + prize_data.get('caption', '')
                
                if prize_data['type'] == 'photo':
                    await message.answer_photo(
                        photo=prize_data['content'],
                        caption=caption,
                        reply_markup=KeyboardBuilder.edit_prize_keyboard(),
                        parse_mode=ParseMode.MARKDOWN
                    )
                elif prize_data['type'] == 'video':
                    await message.answer_video(
                        video=prize_data['content'],
                        caption=caption,
                        reply_markup=KeyboardBuilder.edit_prize_keyboard(),
                        parse_mode=ParseMode.MARKDOWN
                    )
                elif prize_data['type'] == 'document':
                    await message.answer_document(
                        document=prize_data['content'],
                        caption=caption,
                        reply_markup=KeyboardBuilder.edit_prize_keyboard(),
                        parse_mode=ParseMode.MARKDOWN
                    )
        
        except Exception as e:
            logger.error(f"Error showing current prize: {e}")
            await message.answer("❌ Произошла ошибка при отображении приза.")
    
    async def start_edit_prize(self, message: Message, state: FSMContext):
        """Start editing prize"""
        await message.edit_text(
            "✏️ **Изменить приз**\n\n"
            "Отправьте новое содержание приза. Вы можете отправить:\n\n"
            "• Текстовое сообщение\n"
            "• Фото с подписью\n"
            "• Видео с подписью\n"
            "• Документ/файл\n"
            "• Ссылку/URL\n\n"
            "Отправьте /cancel для отмены этой операции.",
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(AdminStates.waiting_for_prize)
    
    async def prize_input_handler(self, message: Message, state: FSMContext):
        """Handle prize input"""
        try:
            if message.text == "/cancel":
                await state.clear()
                await message.answer("❌ Изменение приза отменено.")
                return
            
            prize_data = {
                'updated_at': datetime.now().isoformat()
            }
            
            # Handle different message types
            if message.photo:
                prize_data['type'] = 'photo'
                prize_data['content'] = message.photo[-1].file_id
                prize_data['caption'] = message.caption or ''
            
            elif message.video:
                prize_data['type'] = 'video'
                prize_data['content'] = message.video.file_id
                prize_data['caption'] = message.caption or ''
            
            elif message.document:
                prize_data['type'] = 'document'
                prize_data['content'] = message.document.file_id
                prize_data['caption'] = message.caption or ''
            
            elif message.text:
                prize_data['type'] = 'text'
                prize_data['content'] = message.text
            
            else:
                await message.answer(
                    "❌ **Неподдерживаемый формат**\n\n"
                    "Пожалуйста, отправьте поддерживаемый формат (текст, фото, видео или документ)."
                )
                return
            
            # Save to temporary state
            await state.update_data(prize_data=prize_data)
            
            # Show confirmation
            await message.answer(
                "✅ **Предварительный просмотр приза**\n\n"
                f"Тип: **{prize_data['type']}**\n\n"
                "Хотите ли вы сохранить это как новый приз?",
                reply_markup=KeyboardBuilder.confirmation_keyboard("save_prize"),
                parse_mode=ParseMode.MARKDOWN
            )
            
            await state.set_state(AdminStates.waiting_for_prize_confirmation)
        
        except Exception as e:
            logger.error(f"Error in prize input handler: {e}")
            await message.answer("❌ Произошла ошибка при обработке вашего приза.")
    
    async def show_delete_prize_confirmation(self, message: Message):
        """Show delete prize confirmation"""
        await message.edit_text(
            "🗑️ **Удалить приз**\n\n"
            "Вы уверены, что хотите удалить текущий приз?\n\n"
            "⚠️ Это действие нельзя отменить.",
            reply_markup=KeyboardBuilder.confirmation_keyboard("delete_prize"),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def confirm_delete_prize(self, message: Message):
        """Confirm delete prize"""
        try:
            default_prize = {
                'type': 'text',
                'content': 'Приз еще не установлен.',
                'created_at': datetime.now().isoformat()
            }
            
            if await DataManager.save_prize(default_prize):
                await message.edit_text(
                    "✅ **Приз удален**\n\n"
                    "Приз был удален и сброшен на значение по умолчанию.",
                    reply_markup=KeyboardBuilder.edit_prize_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info("Prize deleted by admin")
            else:
                await message.answer("❌ Не удалось удалить приз. Пожалуйста, попробуйте еще раз.")
        
        except Exception as e:
            logger.error(f"Error deleting prize: {e}")
            await message.answer("❌ Произошла ошибка при удалении приза.")
    
    async def check_rate_limit(self, user_id: int) -> bool:
        """Check rate limiting for user"""
        now = datetime.now().timestamp()
        
        if user_id not in self.rate_limiter:
            self.rate_limiter[user_id] = []
        
        # Clean old entries
        self.rate_limiter[user_id] = [
            timestamp for timestamp in self.rate_limiter[user_id] 
            if now - timestamp < 60  # 1 minute window
        ]
        
        # Check if user exceeded rate limit
        if len(self.rate_limiter[user_id]) >= MAX_USERS_PER_SECOND:
            return False
        
        # Add current timestamp
        self.rate_limiter[user_id].append(now)
        return True
    
    async def start_bot(self):
        """Start the bot"""
        try:
            # Initialize channel verifier
            await self.channel_verifier.init_session()
            
            # Log startup
            logger.info("Bot starting up...")
            
            # Start polling
            await self.dp.start_polling(self.bot)
        
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
        
        finally:
            # Cleanup
            await self.channel_verifier.close_session()
    
    async def stop_bot(self):
        """Stop the bot"""
        try:
            await self.channel_verifier.close_session()
            await self.bot.session.close()
            logger.info("Bot stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

# ==================== MAIN EXECUTION ====================

async def main():
    """Main function"""
    try:
        # Security check
        SecuritySystem.check_code_integrity()
        
        # Check for self-destruct marker
        if os.path.exists("SELF_DESTRUCT_ACTIVATED.txt"):
            print("Бот был навсегда отключен из-за нарушения безопасности.")
            return
        
        # Validate bot token
        if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("❌ Пожалуйста, установите токен вашего бота в переменную BOT_TOKEN")
            return
        
        # Validate admin user ID
        if ADMIN_USER_ID == 123456789:
            print("❌ Пожалуйста, установите ID администратора в переменную ADMIN_USER_ID")
            return
        
        # Initialize bot
        bot = TelegramGateBot()
        
        # Start bot
        logger.info("Starting Telegram Gate Bot...")
        await bot.start_bot()
    
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"❌ Не удалось запустить бота: {e}")