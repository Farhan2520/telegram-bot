from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "8816672349:AAG41gLQ4DJEz4rwBV-onPJPgQgncRpQqfk"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("SeatSwap Bot Working 🔥")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))

print("Bot is running...")

app.run_polling()
