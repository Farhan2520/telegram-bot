from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "8816672349:AAG41gLQ4DJEz4rwBV-onPJPgQgncRpQqfk"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("SeatSwap Bot Working 🔥")

async def postseat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter Train Number 🚆")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("postseat", postseat))

print("Bot is running...")

app.run_polling()
