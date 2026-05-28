from telegram.ext import (
ApplicationBuilder,
CommandHandler,
ContextTypes,
MessageHandler,
filters,
)

BOT_TOKEN = "8816672349:AAG41gLQ4DJEz4rwBV-onPJPgQgncRpQqfk"

async def postseat(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text("Enter Train Number 🚆")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("SeatSwap Bot Working 🔥")
async def postseat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter Train Number 🚆")

async def postseat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter Train Number 🚆")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("postseat", postseat))
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_message = update.message.text

```
    await update.message.reply_text(
    f"Train Number Saved 🚆\n\nYour Train: {user_message}"
)
```

app.add_handler(MessageHandler(filters.TEXT, handle_message))


print("Bot is running...")

app.run_polling()
