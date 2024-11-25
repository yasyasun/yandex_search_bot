import csv
import io

import telebot
from telebot.types import BotCommand

from utils import process_queries, write_results_to_file, calculate_shares

YANDEX_API_KEY = 'YANDEX_API_KEY'  # Заменить 'YANDEX_API_KEY' на ваш ключ API
BOT_TOKEN = 'BOT_TOKEN'  # Заменить 'BOT_TOKEN' на токен вашего бота
COMMANDS = (
    ('start', 'Запустить бота'),
    ('yandex_search', 'Поиск позиции домена по запросу'),
)

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def start_command(message):
    """Функция, реагирующая на команду '/start'. Выводит приветственное сообщение."""
    bot.send_message(message.from_user.id, f'👋 Привет, {message.from_user.username}!\n'
                                           f'Нажми /yandex_search для поиска позиции домена по запросу.')


@bot.message_handler(commands=['yandex_search'])
def yandex_search_command(message):
    """Функция, реагирующая на команду '/yandex_search'."""
    bot.send_message(message.from_user.id, f'Отправь мне файл с запросами в формате '
                                           f'<b>CSV</b> или <b>TXT</b>.', parse_mode='html')
    bot.register_next_step_handler(message, file_handler)


@bot.message_handler(content_types=['document'])
def file_handler(message):
    """Продолжение команды '/yandex_search'. На вход принимает файл и обрабатывает его."""
    try:
        if not message.document:
            bot.reply_to(message,
                         f'Это не то, что нужно 😎 Пожалуйста, загрузи файл в формате <b>CSV</b> или <b>TXT</b>.',
                         parse_mode='html')
            return

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path).decode('utf-8')
        mime_type = message.document.mime_type

        if mime_type == 'text/csv':
            csv_reader = csv.reader(io.StringIO(downloaded_file))
            queries_data = [row[0] for row in csv_reader if row]  # 1-ый столбец - запрос/запросы
            if not queries_data:
                bot.reply_to(message, 'Файл CSV пустой или некорректный.')
                return

        elif mime_type == 'text/plain':
            queries_data = downloaded_file.splitlines()  # каждый запрос на новой строке
            if not queries_data:
                bot.reply_to(message, 'Файл TXT пустой или некорректный.')
                return

        else:
            bot.reply_to(message, 'Пожалуйста, загрузи файл в формате CSV или TXT.')
            return

    except Exception as e:
        bot.reply_to(message, f'⚠️ Ошибка! Попробуй ещё раз.')
        print(f"Ошибка: {e}")
        return
    bot.send_message(message.from_user.id, 'Введи домен/домены через пробел для поиска позиций по запросу.')
    bot.register_next_step_handler(message, file_handler_with_domains, queries_data)


def file_handler_with_domains(message, queries_data):
    """
    Продолжение команды '/yandex_search'.
    На вход принимает домен/домены и выводит результаты поиска.
    """
    msg = bot.send_message(message.chat.id, 'Запрос обрабатывается...')
    try:
        domains = [domain.strip() for domain in message.text.split(' ')]

        results = process_queries(queries_data, domains, YANDEX_API_KEY)
        if not results:
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                  text='Результаты поиска пустые. Проверь корректность ввода. '
                                       'Для повторного поиска отправь файл или нажми /yandex_search')
            return

        results_file = 'results.csv'
        write_results_to_file(results_file, results)
        share_domains = calculate_shares(results_file)

        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                              text=f'Доля доменов:\n```{share_domains}```', parse_mode='Markdown')
        with open(results_file, 'r', encoding='utf-8') as file_to_send:
            bot.send_document(message.chat.id, file_to_send, caption='Твой файл с результатами')
    except Exception as e:
        bot.reply_to(message, f'⚠️ Произошла ошибка! Попробуй ещё раз.')
        print(f"Ошибка: {e}")
        return


@bot.message_handler(state=None)
def bot_echo(message):
    """
    Эхо хендлер, куда летят текстовые сообщения без указанного состояния.
    Также функция реагирует на ввод пользователем сообщения 'привет'.
    """
    if message.text.lower() == 'привет':
        bot.send_message(message, f'👋 Привет, {message.from_user.username}!\n'
                                  f'Нажми /yandex_search для поиска позиции домена по запросу.')
    else:
        bot.reply_to(message, 'Нет такой команды.\n'
                              'Нажми /start')


if __name__ == "__main__":
    bot.set_my_commands([BotCommand(*i) for i in COMMANDS])
    bot.polling()
