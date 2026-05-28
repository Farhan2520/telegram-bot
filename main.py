from telegram import Update
from telegram.ext import (
ApplicationBuilder,
CommandHandler,
ContextTypes,
ConversationHandler,
MessageHandler,
filters,
)

BOT_TOKEN = "8816672349:AAG41gLQ4DJEz4rwBV-onPJPgQgncRpQqfk"

TRAIN, COACH, CURRENT_SEAT, WANTED_SEAT = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("SeatSwap Bot Working 🔥")

async def postseat(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text("Enter Train Number 🚆")
return TRAIN

async def train(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data["train"] = update.message.text
await update.message.reply_text("Enter Coach 🚉")
return COACH

async def coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data["coach"] = update.message.text
await update.message.reply_text("Enter Current Seat 💺")
return CURRENT_SEAT

async def current_seat(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data["current"] = update.message.text
await update.message.reply_text("Wanted Seat? 🔄")
return WANTED_SEAT

async def wanted_seat(update: Update, context: ContextTypes.DEFAULT_TYPE):

```
context.user_data["wanted"] = update.message.text

await update.message.reply_text(
    f"Seat Posted 🚀\n\n"
    f"Train: {context.user_data['train']}\n"
    f"Coach: {context.user_data['coach']}\n"
    f"Current Seat: {context.user_data['current']}\n"
    f"Wanted Seat: {context.user_data['wanted']}"
)

return ConversationHandler.END
```

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))

conv_handler = ConversationHandler(
entry_points=[CommandHandler("postseat", postseat)],
states={
TRAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, train)],
COACH: [MessageHandler(filters.TEXT & ~filters.COMMAND, coach)],
CURRENT_SEAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, current_seat)],
WANTED_SEAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wanted_seat)],
},
fallbacks=[],
)

app.add_handler(conv_handler)

print("Bot is running...")

app.run_polling()
