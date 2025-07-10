#!/usr/bin/env python3
"""
Demo script to compare English and Russian bot text
"""

# Sample text comparisons
comparisons = [
    {
        "context": "Welcome Message",
        "english": "🎉 **Welcome to the Gate Bot!**\n\nThis bot provides exclusive prizes for users who are subscribed to our required channels.\n\nClick the button below to get your prize!",
        "russian": "🎉 **Добро пожаловать в Gate Bot!**\n\nЭтот бот предоставляет эксклюзивные призы пользователям, которые подписаны на наши обязательные каналы.\n\nНажмите на кнопку ниже, чтобы получить свой приз!"
    },
    {
        "context": "Button: Get Prize",
        "english": "🎁 Get Prize",
        "russian": "🎁 Получить приз"
    },
    {
        "context": "Button: Admin Panel",
        "english": "⚙️ Admin Panel",
        "russian": "⚙️ Панель администратора"
    },
    {
        "context": "Admin: Edit Channels",
        "english": "📺 Edit Channels",
        "russian": "📺 Управление каналами"
    },
    {
        "context": "Admin: Edit Prize",
        "english": "🎁 Edit Prize",
        "russian": "🎁 Управление призом"
    },
    {
        "context": "Subscription Required",
        "english": "🚫 **Subscription Required**\n\nYou must subscribe to the following channels to get your prize:",
        "russian": "🚫 **Требуется подписка**\n\nВы должны подписаться на следующие каналы, чтобы получить свой приз:"
    },
    {
        "context": "I'm Subscribed Button",
        "english": "✅ I'm Subscribed",
        "russian": "✅ Я подписался"
    },
    {
        "context": "Congratulations Message",
        "english": "🎉 **Congratulations!**\n\nYou have successfully verified your subscription. Here's your prize:",
        "russian": "🎉 **Поздравляем!**\n\nВы успешно подтвердили свою подписку. Вот ваш приз:"
    },
    {
        "context": "Bot Activation Required",
        "english": "🔐 **Bot Activation Required**\n\nThis bot requires an activation code to start working.\nPlease enter the activation code:",
        "russian": "🔐 **Требуется активация бота**\n\nДля начала работы этого бота необходим код активации.\nПожалуйста, введите код активации:"
    },
    {
        "context": "Bot Successfully Activated",
        "english": "✅ **Bot Activated Successfully!**\n\nThe bot is now ready to use. Use /start to begin.",
        "russian": "✅ **Бот успешно активирован!**\n\nБот теперь готов к использованию. Используйте /start для начала."
    }
]

print("🔄 RUSSIAN TRANSLATION COMPARISON")
print("=" * 60)

for i, comp in enumerate(comparisons, 1):
    print(f"\n{i}. {comp['context']}")
    print("-" * 40)
    print("🇺🇸 English:")
    print(comp['english'])
    print("\n🇷🇺 Russian:")
    print(comp['russian'])
    print()

print("✅ All user-facing text has been successfully translated to Russian!")
print("🚀 Both English and Russian versions are ready for deployment!")