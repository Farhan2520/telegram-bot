from telegram.ext import Updater, CommandHandler

BOT_TOKEN = "8816672349:AAHy2N7ZNqJEvw3AnY8beVB8aiN3GxeaWnI"

def start(update, context):
update.message.reply_text("Hello Farhan 🔥 SeatSwap Bot Working!")

updater = Updater(BOT_TOKEN, use_context=True)

dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))

print("Bot is running...")

updater.start_polling()
updater.idle()
