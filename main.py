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

# In-memory storage for swap requests
swap_requests = []


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚆 Welcome to SeatSwap Bot!\n\n"
        "Commands:\n"
        "/postseat - Post your seat swap request\n"
        "/viewswaps - See all available swaps\n"
        "/myrequest - See your active request\n"
        "/cancel - Cancel your request\n"
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

    user = update.effective_user
    train = context.user_data["train"]
    coach = context.user_data["coach"]
    current = context.user_data["current"]
    wanted = context.user_data["wanted"]

    # Remove any previous request from this user
    global swap_requests
    swap_requests = [r for r in swap_requests if r["user_id"] != user.id]

    # Add new request
    swap_requests.append({
        "user_id": user.id,
        "name": user.first_name,
        "train": train,
        "coach": coach,
        "current": current,
        "wanted": wanted,
    })

    await update.message.reply_text(
        f"✅ Seat Swap Request Posted!\n\n"
        f"🚆 Train: {train}\n"
        f"🚉 Coach: {coach}\n"
        f"💺 Current Seat: {current}\n"
        f"🔄 Wanted: {wanted}\n\n"
        f"Others can now see your request via /viewswaps\n"
        f"Use /cancel to remove your request."
    )
    return ConversationHandler.END


async def viewswaps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not swap_requests:
        await update.message.reply_text(
            "No active swap requests right now 😔\n\n"
            "Be the first! Use /postseat to post yours."
        )
        return

    msg = f"🚆 Active Seat Swap Requests ({len(swap_requests)} total)\n"
    msg += "━━━━━━━━━━━━━━━━━━━\n\n"

    for i, req in enumerate(swap_requests, 1):
        msg += (
            f"#{i} — {req['name']}\n"
            f"🚆 Train: {req['train']}\n"
            f"🚉 Coach: {req['coach']}\n"
            f"💺 Has: {req['current']}\n"
            f"🔄 Wants: {req['wanted']}\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
        )

    msg += "Interested in a swap? Contact the person directly on Telegram."
    await update.message.reply_text(msg)


async def myrequest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    req = next((r for r in swap_requests if r["user_id"] == user_id), None)

    if not req:
        await update.message.reply_text(
            "You have no active request.\n\nUse /postseat to post one!"
        )
        return

    await update.message.reply_text(
        f"📋 Your Active Request:\n\n"
        f"🚆 Train: {req['train']}\n"
        f"🚉 Coach: {req['coach']}\n"
        f"💺 Current Seat: {req['current']}\n"
        f"🔄 Wanted: {req['wanted']}\n\n"
        f"Use /cancel to remove this request."
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    global swap_requests
    before = len(swap_requests)
    swap_requests = [r for r in swap_requests if r["user_id"] != user_id]
    after = len(swap_requests)

    if before != after:
        await update.message.reply_text("✅ Your swap request has been removed.")
    else:
        await update.message.reply_text(
            "No active request found.\n\nUse /postseat to post one!"
        )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "How to use SeatSwap 🚆\n\n"
        "1. /postseat — post your swap request\n"
        "2. /viewswaps — see all requests\n"
        "3. /myrequest — check your request\n"
        "4. /cancel — remove your request\n\n"
        "Steps to post:\n"
        "Enter train number → coach → current seat → wanted seat\n\n"
        "Others will see your request and can contact you!"
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
app.add_handler(CommandHandler("viewswaps", viewswaps))
app.add_handler(CommandHandler("myrequest", myrequest))
app.add_handler(conv_handler)

print("SeatSwap Bot is running...")

app.run_polling()
