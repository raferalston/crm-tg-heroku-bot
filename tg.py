import os
import logging

from telegram.ext import Updater, CommandHandler

#NOTE: crm class already initialized
from crm import crm_dispatcher


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

#IMPORTANT: place your heroku link here
HEROKU_LINK = '...'

class TelegramBot:
    def __init__(self, TOKEN, use_context=True):
        self.updater = Updater(TOKEN, use_context=use_context)
        self.dp = self.updater.dispatcher
        #TODO: refactor this. Adding a error handler
        # self.dp.add_error_handler(self.error_handler)

    def handler_addition(self, command_name: str, func):
        """input: command_name -> str, func -> function"""
        self.dp.add_handler(CommandHandler(command_name, func))

    def error_handler(self, update, context):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)

    def start_as_webhook_on_heroku(self, 
                                HEROKU_TOKEN, 
                                ip='0.0.0.0', 
                                heroku_address=address):
        """Start bot as webhook on heroku"""
        PORT = int(os.environ.get('PORT', 5000))
        self.updater.start_webhook(listen=ip,
                                port=int(PORT),
                                url_path=HEROKU_TOKEN)
        self.updater.bot.setWebhook(f'https://{heroku_address}.herokuapp.com/' + HEROKU_TOKEN)

    def start_as_polling(self):
        """
        Run the bot until you press Ctrl-C or the process receives SIGINT,
        SIGTERM or SIGABRT. This should be used most of the time, since
        start_polling() is non-blocking and will stop the bot gracefully."""
        self.updater.start_polling()
        self.updater.idle()

class TgMessenger(TelegramBot):
    def __init__(self, TOKEN, crm_dispatch, use_context=True):
        super().__init__(TOKEN, use_context)
        #NOTE: added handlers for commands used in tg bot:
        #NOTE: /tomorrow: - Расписание занятий на следующий день
        #NOTE: /tomorrow: - Расписание занятий через день
        #NOTE: /today: - Расписание занятий на текущий день
        #NOTE: /chat_id: - Номер чата
        self.handler_addition('tomorrow', self.send_tomorrow_schedule)
        self.handler_addition('aftertomorrow', self.send__aftertomorrow_schedule)
        self.handler_addition('today', self.send_today_schedule)
        self.handler_addition('chat_id', self.send_chat_id)
        self._crm_dispatch = crm_dispatch

    def send__aftertomorrow_schedule(self, update, context):
        #TODO: build this method, he took schedule from crm class
        _chat_id = update.message.chat.id
        _schedule = self._crm_dispatch.build_schedule_aftertomorrow(teacher=_chat_id)
        update.message.reply_markdown(_schedule)

    def send_tomorrow_schedule(self, update, context):
        #TODO: build this method, he took schedule from crm class
        _chat_id = update.message.chat.id
        _schedule = self._crm_dispatch.build_schedule_tomorrow(teacher=_chat_id)
        update.message.reply_markdown(_schedule)

    def send_today_schedule(self, update, context):
        _chat_id = update.message.chat.id
        _schedule = self._crm_dispatch.build_schedule_today(teacher=_chat_id)
        update.message.reply_markdown(_schedule)

    def send_chat_id(self, update, context):
        _chat_id = update.message.chat.id
        update.message.reply_text(f'Ваш номер чата: {_chat_id}')

    #TODO:(Mike) create command for adding teachers to managers.json (test_), return message success denied


DEBUG = True
if __name__ == '__main__':
    #TODO:(Mike) move API keys to the os environment 
    if not DEBUG:
        with open('TG_KEY') as f:
            TOKEN = f.read()
    else:
        with open('TG_KEY DEBUG') as f:
            TOKEN = f.read()
    bot = TgMessenger(TOKEN=TOKEN, crm_dispatch=crm_dispatcher)
    if not DEBUG:
        bot.start_as_webhook_on_heroku(TOKEN, heroku_address=HEROKU_LINK)
    else:
        bot.start_as_polling()