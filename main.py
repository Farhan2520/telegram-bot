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
    await update.message.reply_text(
        "Welcome to SeatSwap 🚆\n\n"
        "Commands:\n"
        "/postseat - Post your seat swap request\n"
        "/help - How to use"
    )


async def postseat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter your Train Number 🚆\n(Example: 12345)")
    return TRAIN


async def get_train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["train"] = update.message.text
    await update.message.reply_text("Enter your Coach 🚉\n(Example: S1, B2, A1)")
    return COACH


async def get_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["coach"] = update.message.text
    await update.message.reply_text("Enter your Current Seat Number 💺\n(Example: 45)")
    return CURRENT_SEAT


async def get_current_seat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["current"] = update.message.text
    await update.message.reply_text(
        "What type of seat do you want? 🔄\n(Example: Lower, Upper, Middle, Side Lower)"
    )
    return WANTED_SEAT


async def get_wanted_seat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wanted"] = update.message.text

    train = context.user_data["train"]
    coach = context.user_data["coach"]
    current = context.user_data["current"]
    wanted = context.user_data["wanted"]

    await update.message.reply_text(
        f"✅ Seat Swap Request Posted!\n\n"
        f"🚆 Train: {train}\n"
        f"🚉 Coach: {coach}\n"
        f"💺 Current Seat: {current}\n"
        f"🔄 Wanted: {wanted}\n\n"
        f"We will notify you when a match is found!"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Request cancelled. Type /postseat to start again.")
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "How to use SeatSwap 🚆\n\n"
        "1. Type /postseat\n"
        "2. Enter train number\n"
        "3. Enter coach\n"
        "4. Enter your current seat\n"
        "5. Enter what seat you want\n\n"
        "We will find a match for you automatically!"
    )


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("postseat", postseat)],
    states={
        TRAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_train)],
        COACH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_coach)],
        CURRENT_SEAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_current_seat)],
        WANTED_SEAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_wanted_seat)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(conv_handler)

print("SeatSwap Bot is running...")

app.run_polling()
