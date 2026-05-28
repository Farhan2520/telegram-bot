import os
import json
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import firebase_admin
from firebase_admin import credentials, db

# ── CONFIG ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8816672349:AAG41gLQ4DJEz4rwBV-onPJPgQgncRpQqfk")

# Firebase init
firebase_key_raw = os.getenv("FIREBASE_KEY")
if firebase_key_raw:
    firebase_key = json.loads(firebase_key_raw)
    cred = credentials.Certificate(firebase_key)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://seatswap-a96ec-default-rtdb.firebaseio.com/"
    })
    FIREBASE_ON = True
else:
    FIREBASE_ON = False
    print("WARNING: FIREBASE_KEY not set. Running without database.")

# Conversation states
TRAIN, COACH, CURRENT_SEAT, WANTED_SEAT = range(4)

# ── BADGE SYSTEM ─────────────────────────────────────────────────────────────
def get_badge(swaps_done):
    if swaps_done >= 25:
        return "🚆 Seat Master"
    elif swaps_done >= 10:
        return "🛡 Verified Swapper"
    elif swaps_done >= 3:
        return "⭐ Trusted Traveler"
    else:
        return "🟢 New Traveler"

# ── FIREBASE HELPERS ─────────────────────────────────────────────────────────
def save_user(user):
    if not FIREBASE_ON:
        return
    ref = db.reference(f"users/{user.id}")
    existing = ref.get()
    if not existing:
        ref.set({
            "name": user.first_name,
            "username": user.username or "",
            "points": 0,
            "swaps_done": 0,
            "badge": get_badge(0),
        })

def get_user_data(user_id):
    if not FIREBASE_ON:
        return {"name": "User", "username": "", "points": 0, "swaps_done": 0, "badge": get_badge(0)}
    data = db.reference(f"users/{user_id}").get()
    return data or {"name": "User", "username": "", "points": 0, "swaps_done": 0, "badge": get_badge(0)}

def save_swap(user, train, coach, current, wanted):
    swap_id = str(uuid.uuid4())[:8]
    swap = {
        "swap_id": swap_id,
        "user_id": user.id,
        "name": user.first_name,
        "username": user.username or "",
        "train": train.strip().upper(),
        "coach": coach.strip().upper(),
        "current": current.strip(),
        "wanted": wanted.strip(),
        "timestamp": datetime.now().strftime("%d %b %Y %I:%M %p"),
        "status": "active",
    }
    if FIREBASE_ON:
        # Remove old request from this user first
        all_swaps = db.reference("swaps").get() or {}
        for sid, sdata in all_swaps.items():
            if sdata.get("user_id") == user.id:
                db.reference(f"swaps/{sid}").delete()
        db.reference(f"swaps/{swap_id}").set(swap)
    return swap

def get_all_swaps():
    if not FIREBASE_ON:
        return {}
    return db.reference("swaps").get() or {}

def delete_swap_by_user(user_id):
    if not FIREBASE_ON:
        return False
    all_swaps = db.reference("swaps").get() or {}
    deleted = False
    for sid, sdata in all_swaps.items():
        if sdata.get("user_id") == user_id:
            db.reference(f"swaps/{sid}").delete()
            deleted = True
    return deleted

def find_match(new_swap):
    all_swaps = get_all_swaps()
    seat_opposites = {
        "lower": ["upper", "middle"],
        "upper": ["lower", "middle"],
        "middle": ["lower", "upper"],
        "side lower": ["side upper"],
        "side upper": ["side lower"],
    }
    new_wanted = new_swap["wanted"].lower()
    new_current = new_swap["current"].lower()
    for sid, s in all_swaps.items():
        if s.get("user_id") == new_swap["user_id"]:
            continue
        if s.get("train") != new_swap["train"]:
            continue
        their_wanted = s.get("wanted", "").lower()
        their_current = s.get("current", "").lower()
        # Check if they want what we have and we want what they have
        wanted_match = (
            their_wanted == new_current or
            their_wanted in seat_opposites.get(new_current, []) or
            new_wanted == their_current or
            new_wanted in seat_opposites.get(their_current, [])
        )
        if wanted_match:
            return s
    return None

def update_swap_points(user_id):
    if not FIREBASE_ON:
        return
    ref = db.reference(f"users/{user_id}")
    data = ref.get() or {}
    swaps_done = data.get("swaps_done", 0) + 1
    points = data.get("points", 0) + 10
    ref.update({
        "swaps_done": swaps_done,
        "points": points,
        "badge": get_badge(swaps_done),
    })

# ── KEYBOARDS ────────────────────────────────────────────────────────────────
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Post Swap", callback_data="menu_postseat"),
            InlineKeyboardButton("👀 View Swaps", callback_data="menu_viewswaps"),
        ],
        [
            InlineKeyboardButton("📋 My Request", callback_data="menu_myrequest"),
            InlineKeyboardButton("👤 My Profile", callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="menu_help"),
        ],
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
    ])

def post_swap_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
    ])

# ── COMMANDS ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    text = (
        f"🚆 Welcome to *SeatSwap*, {user.first_name}!\n\n"
        "Easily exchange your train seat with fellow passengers.\n\n"
        "What would you like to do?"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# ── POSTSEAT FLOW ────────────────────────────────────────────────────────────
async def postseat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📝 *Post Seat Swap*\n\nEnter your *Train Number* 🚆\n_(Example: 12345 or Rajdhani)_"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")
    return TRAIN

async def get_train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["train"] = update.message.text
    await update.message.reply_text(
        "Enter your *Coach* 🚉\n_(Example: S1, B2, A1, H1)_",
        parse_mode="Markdown"
    )
    return COACH

async def get_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["coach"] = update.message.text
    await update.message.reply_text(
        "Enter your *Current Seat* 💺\n_(Example: 45 Lower, 12 Upper)_",
        parse_mode="Markdown"
    )
    return CURRENT_SEAT

async def get_current_seat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["current"] = update.message.text
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬇️ Lower", callback_data="want_lower"),
            InlineKeyboardButton("⬆️ Upper", callback_data="want_upper"),
        ],
        [
            InlineKeyboardButton("➡️ Middle", callback_data="want_middle"),
            InlineKeyboardButton("↘️ Side Lower", callback_data="want_side lower"),
        ],
        [InlineKeyboardButton("↗️ Side Upper", callback_data="want_side upper")],
    ])
    await update.message.reply_text(
        "Which seat type do you *want*? 🔄",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return WANTED_SEAT

async def get_wanted_seat_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wanted = query.data.replace("want_", "").title()
    context.user_data["wanted"] = wanted
    return await finish_postseat(update, context)

async def get_wanted_seat_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wanted"] = update.message.text
    return await finish_postseat(update, context)

async def finish_postseat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    train = context.user_data["train"]
    coach = context.user_data["coach"]
    current = context.user_data["current"]
    wanted = context.user_data["wanted"]

    swap = save_swap(user, train, coach, current, wanted)

    # Check for instant match
    match = find_match(swap)

    text = (
        f"✅ *Swap Request Posted!*\n\n"
        f"🚆 Train: `{train}`\n"
        f"🚉 Coach: `{coach}`\n"
        f"💺 Has: `{current}`\n"
        f"🔄 Wants: `{wanted}`\n\n"
    )

    if match:
        contact = f"@{match['username']}" if match.get("username") else f"[{match['name']}](tg://user?id={match['user_id']})"
        text += (
            f"🎉 *INSTANT MATCH FOUND!*\n\n"
            f"👤 Name: {match['name']} {match.get('badge','')}\n"
            f"💺 Has: `{match['current']}`\n"
            f"🔄 Wants: `{match['wanted']}`\n\n"
            f"📩 Contact: {contact}\n\n"
            f"_Message them to confirm the swap!_"
        )
        # Notify the matched user
        try:
            my_contact = f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={user.id})"
            match_text = (
                f"🎉 *MATCH FOUND for your swap!*\n\n"
                f"Someone wants to swap with you on Train `{train}`\n\n"
                f"👤 Name: {user.first_name}\n"
                f"💺 Has: `{current}`\n"
                f"🔄 Wants: `{wanted}`\n\n"
                f"📩 Contact: {my_contact}\n\n"
                f"_Message them to confirm!_"
            )
            bot = update.get_bot() if hasattr(update, "get_bot") else context.bot
            await bot.send_message(
                chat_id=match["user_id"],
                text=match_text,
                parse_mode="Markdown"
            )
        except Exception:
            pass
    else:
        text += "Your request is now *live*! We'll notify you when a match is found. 🔔"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👀 View All Swaps", callback_data="menu_viewswaps"),
            InlineKeyboardButton("🏠 Menu", callback_data="menu_home"),
        ]
    ])

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    return ConversationHandler.END

# ── VIEW SWAPS ────────────────────────────────────────────────────────────────
async def viewswaps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_swaps = get_all_swaps()
    active = {k: v for k, v in all_swaps.items() if v.get("status") == "active"}

    if update.callback_query:
        await update.callback_query.answer()

    if not active:
        text = "😔 No active swap requests right now.\n\nBe the first! Use /postseat"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Post Your Swap", callback_data="menu_postseat")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
        ])
    else:
        text = f"🚆 *Active Swap Requests* ({len(active)} total)\n\n"
        for i, (sid, req) in enumerate(active.items(), 1):
            badge = req.get("badge", "🟢 New Traveler")
            contact = f"@{req['username']}" if req.get("username") else f"ID: {req['user_id']}"
            text += (
                f"*#{i} — {req['name']}* {badge}\n"
                f"🚆 Train: `{req['train']}` | 🚉 Coach: `{req['coach']}`\n"
                f"💺 Has: `{req['current']}`  →  🔄 Wants: `{req['wanted']}`\n"
                f"📩 {contact}\n"
                f"🕐 {req.get('timestamp','')}\n"
                f"─────────────────\n"
            )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Post My Swap", callback_data="menu_postseat")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
        ])

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ── MY REQUEST ────────────────────────────────────────────────────────────────
async def myrequest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.callback_query:
        await update.callback_query.answer()

    all_swaps = get_all_swaps()
    req = next((v for v in all_swaps.values() if v.get("user_id") == user_id), None)

    if not req:
        text = "📋 You have no active swap request.\n\nUse /postseat to post one!"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Post Swap", callback_data="menu_postseat")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
        ])
    else:
        text = (
            f"📋 *Your Active Request*\n\n"
            f"🚆 Train: `{req['train']}`\n"
            f"🚉 Coach: `{req['coach']}`\n"
            f"💺 Has: `{req['current']}`\n"
            f"🔄 Wants: `{req['wanted']}`\n"
            f"🕐 Posted: {req.get('timestamp','')}\n\n"
            f"_Use /cancel to remove this request._"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel Request", callback_data="cancel_request")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
        ])

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ── PROFILE ──────────────────────────────────────────────────────────────────
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.callback_query:
        await update.callback_query.answer()
    data = get_user_data(user.id)
    swaps = data.get("swaps_done", 0)
    points = data.get("points", 0)
    badge = get_badge(swaps)

    # Next badge progress
    if swaps < 3:
        nxt = f"{3 - swaps} more swaps to ⭐ Trusted Traveler"
    elif swaps < 10:
        nxt = f"{10 - swaps} more swaps to 🛡 Verified Swapper"
    elif swaps < 25:
        nxt = f"{25 - swaps} more swaps to 🚆 Seat Master"
    else:
        nxt = "You've reached the highest badge! 🏆"

    text = (
        f"👤 *Your Profile*\n\n"
        f"Name: *{user.first_name}*\n"
        f"Badge: {badge}\n"
        f"✅ Swaps Done: {swaps}\n"
        f"⭐ Points: {points}\n\n"
        f"📈 Next: {nxt}"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ── HELP ─────────────────────────────────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    text = (
        "❓ *How to use SeatSwap*\n\n"
        "1️⃣ Tap *Post Swap* and fill in details\n"
        "2️⃣ Others can see your request in *View Swaps*\n"
        "3️⃣ If a match is found, you both get notified instantly\n"
        "4️⃣ Contact each other via Telegram to confirm\n"
        "5️⃣ After successful swap, you earn *+10 points* 🎉\n\n"
        "🏅 *Badge Levels:*\n"
        "🟢 New Traveler — Starting out\n"
        "⭐ Trusted Traveler — 3+ swaps\n"
        "🛡 Verified Swapper — 10+ swaps\n"
        "🚆 Seat Master — 25+ swaps\n\n"
        "More swaps = higher trust = more people will swap with you!"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ── CANCEL ────────────────────────────────────────────────────────────────────
async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.callback_query:
        await update.callback_query.answer()
    deleted = delete_swap_by_user(user_id)
    text = "✅ Your swap request has been removed." if deleted else "You have no active request to cancel."
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    return ConversationHandler.END

# ── CALLBACK ROUTER ───────────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "menu_home":
        await start(update, context)
    elif data == "menu_postseat":
        await postseat_start(update, context)
    elif data == "menu_viewswaps":
        await viewswaps(update, context)
    elif data == "menu_myrequest":
        await myrequest(update, context)
    elif data == "menu_profile":
        await profile(update, context)
    elif data == "menu_help":
        await help_cmd(update, context)
    elif data == "cancel_request":
        await cancel_cmd(update, context)
    elif data.startswith("want_"):
        await get_wanted_seat_button(update, context)

# ── CONV HANDLER ──────────────────────────────────────────────────────────────
conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("postseat", postseat_start),
        CallbackQueryHandler(postseat_start, pattern="^menu_postseat$"),
    ],
    states={
        TRAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_train)],
        COACH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_coach)],
        CURRENT_SEAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_current_seat)],
        WANTED_SEAT: [
            CallbackQueryHandler(get_wanted_seat_button, pattern="^want_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_wanted_seat_text),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_cmd),
        CallbackQueryHandler(cancel_cmd, pattern="^cancel_request$"),
    ],
    per_message=False,
)

# ── APP SETUP ─────────────────────────────────────────────────────────────────
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(conv_handler)
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("viewswaps", viewswaps))
app.add_handler(CommandHandler("myrequest", myrequest))
app.add_handler(CommandHandler("profile", profile))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("cancel", cancel_cmd))
app.add_handler(CallbackQueryHandler(button_handler))

print("SeatSwap Bot is running...")
app.run_polling()
