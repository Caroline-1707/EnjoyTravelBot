from loader import bot
from telebot.custom_filters import StateFilter
from utils.set_bot_commands import set_default_commands
from database.write_db import create_tables, clear_database

if __name__ == '__main__':
    create_tables()
    clear_database()
    bot.add_custom_filter(StateFilter(bot))
    set_default_commands(bot)
    bot.infinity_polling()
