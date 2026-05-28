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

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS  = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]

firebase_key_raw = os.getenv("FIREBASE_KEY")
FIREBASE_ON = False
if firebase_key_raw:
    try:
        firebase_key = json.loads(firebase_key_raw)
        cred = credentials.Certificate(firebase_key)
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://seatswap-a96ec-default-rtdb.firebaseio.com/"
        })
        FIREBASE_ON = True
        print("Firebase connected ✅")
    except Exception as e:
        print(f"Firebase error: {e}")
else:
    print("WARNING: FIREBASE_KEY not set. Running without database.")

# ─────────────────────────────────────────────
#  CONVERSATION STATES
# ─────────────────────────────────────────────
TRAIN, COACH, CURRENT_SEAT, WANTED_SEAT = range(4)
SEARCH_TRAIN, SEARCH_COACH              = range(4, 6)
CONFIRM_A, CONFIRM_B                    = range(6, 8)
BROADCAST_MSG                           = range(8, 9)

# ─────────────────────────────────────────────
#  BADGE SYSTEM
# ─────────────────────────────────────────────
def get_badge(swaps_done):
    if swaps_done >= 25:  return "🚆 Seat Master"
    if swaps_done >= 10:  return "🛡 Verified Swapper"
    if swaps_done >= 3:   return "⭐ Trusted Traveler"
    return "🟢 New Traveler"

def next_badge_info(swaps_done):
    if swaps_done < 3:    return f"{3  - swaps_done} more swaps → ⭐ Trusted Traveler"
    if swaps_done < 10:   return f"{10 - swaps_done} more swaps → 🛡 Verified Swapper"
    if swaps_done < 25:   return f"{25 - swaps_done} more swaps → 🚆 Seat Master"
    return "🏆 Maximum badge reached!"

# ─────────────────────────────────────────────
#  FIREBASE HELPERS
# ─────────────────────────────────────────────
def fb_get(path):
    if not FIREBASE_ON: return None
    try:    return db.reference(path).get()
    except: return None

def fb_set(path, data):
    if not FIREBASE_ON: return
    try:    db.reference(path).set(data)
    except: pass

def fb_update(path, data):
    if not FIREBASE_ON: return
    try:    db.reference(path).update(data)
    except: pass

def fb_delete(path):
    if not FIREBASE_ON: return
    try:    db.reference(path).delete()
    except: pass

def save_user(user):
    existing = fb_get(f"users/{user.id}")
    if not existing:
        fb_set(f"users/{user.id}", {
            "name":       user.first_name,
            "username":   user.username or "",
            "points":     0,
            "swaps_done": 0,
            "badge":      get_badge(0),
            "premium":    False,
            "banned":     False,
            "reports":    0,
        })

def get_user(user_id):
    data = fb_get(f"users/{user_id}")
    return data or {
        "name": "User", "username": "", "points": 0,
        "swaps_done": 0, "badge": get_badge(0),
        "premium": False, "banned": False, "reports": 0,
    }

def is_banned(user_id):
    u = get_user(user_id)
    return u.get("banned", False)

def save_swap(user, train, coach, current, wanted):
    swap_id = str(uuid.uuid4())[:8]
    # Remove old request from this user
    all_swaps = fb_get("swaps") or {}
    for sid, s in all_swaps.items():
        if s.get("user_id") == user.id:
            fb_delete(f"swaps/{sid}")
    swap = {
        "swap_id":   swap_id,
        "user_id":   user.id,
        "name":      user.first_name,
        "username":  user.username or "",
        "train":     train.strip().upper(),
        "coach":     coach.strip().upper(),
        "current":   current.strip(),
        "wanted":    wanted.strip(),
        "timestamp": datetime.now().strftime("%d %b %Y %I:%M %p"),
        "status":    "active",
    }
    fb_set(f"swaps/{swap_id}", swap)
    return swap

def get_all_swaps():
    return fb_get("swaps") or {}

def delete_user_swap(user_id):
    all_swaps = get_all_swaps()
    deleted = False
    for sid, s in all_swaps.items():
        if s.get("user_id") == user_id:
            fb_delete(f"swaps/{sid}")
            deleted = True
    return deleted

def find_match(new_swap):
    opposites = {
        "lower":      ["upper", "middle"],
        "upper":      ["lower", "middle"],
        "middle":     ["lower", "upper"],
        "side lower": ["side upper"],
        "side upper": ["side lower"],
    }
    nw = new_swap["wanted"].lower()
    nc = new_swap["current"].lower()
    for sid, s in get_all_swaps().items():
        if s.get("user_id") == new_swap["user_id"]: continue
        if s.get("train") != new_swap["train"]:     continue
        tw = s.get("wanted", "").lower()
        tc = s.get("current", "").lower()
        if (tw == nc or tw in opposites.get(nc, []) or
                nw == tc or nw in opposites.get(tc, [])):
            return s
    return None

def award_points(user_id):
    u = get_user(user_id)
    swaps = u.get("swaps_done", 0) + 1
    pts   = u.get("points", 0) + 10
    fb_update(f"users/{user_id}", {
        "swaps_done": swaps,
        "points":     pts,
        "badge":      get_badge(swaps),
    })

def get_contact_text(req):
    if req.get("username"):
        return f"@{req['username']}"
    return f"[{req['name']}](tg://user?id={req['user_id']})"

# ─────────────────────────────────────────────
#  KEYBOARDS
# ─────────────────────────────────────────────
def main_menu_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Post Swap",   callback_data="menu_postseat"),
            InlineKeyboardButton("🔍 Find Swap",   callback_data="menu_search"),
        ],
        [
            InlineKeyboardButton("📋 My Request",  callback_data="menu_myrequest"),
            InlineKeyboardButton("👤 My Profile",  callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton("❓ Help",         callback_data="menu_help"),
        ],
    ])

def back_home_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
    ])

def seat_type_kb(prefix="want"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬇️ Lower",      callback_data=f"{prefix}_lower"),
            InlineKeyboardButton("⬆️ Upper",      callback_data=f"{prefix}_upper"),
        ],
        [
            InlineKeyboardButton("➡️ Middle",     callback_data=f"{prefix}_middle"),
            InlineKeyboardButton("↘️ Side Lower", callback_data=f"{prefix}_side lower"),
        ],
        [InlineKeyboardButton("↗️ Side Upper",    callback_data=f"{prefix}_side upper")],
    ])

def swap_result_kb(swap_id, show_confirm=False):
    rows = []
    if show_confirm:
        rows.append([InlineKeyboardButton("✅ Confirm Swap Done", callback_data=f"confirm_{swap_id}")])
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")])
    return InlineKeyboardMarkup(rows)

# ─────────────────────────────────────────────
#  HELPERS — send / edit message
# ─────────────────────────────────────────────
async def reply(update: Update, text: str, kb=None, md=True):
    mode = "Markdown" if md else None
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode=mode)
        except Exception:
            await update.callback_query.message.reply_text(text, reply_markup=kb, parse_mode=mode)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode=mode)

# ─────────────────────────────────────────────
#  /START
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    if is_banned(user.id):
        await reply(update, "🚫 You have been banned from SeatSwap.")
        return
    text = (
        f"🚆 Welcome to *SeatSwap*, {user.first_name}!\n\n"
        "Exchange your train seat with fellow passengers easily.\n\n"
        "Choose an option below 👇"
    )
    await reply(update, text, main_menu_kb())

# ─────────────────────────────────────────────
#  POST SWAP FLOW
# ─────────────────────────────────────────────
async def postseat_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        await reply(update, "🚫 You are banned.")
        return ConversationHandler.END
    u = get_user(user.id)
    if not u.get("premium") and len([
        s for s in get_all_swaps().values() if s.get("user_id") == user.id
    ]) >= 1:
        await reply(update,
            "⚠️ *Free users can have 1 active request.*\n\n"
            "Cancel your existing request first with /cancel\n"
            "or upgrade to 💎 Premium for unlimited requests.\n\n"
            "Use /premium to know more.",
            back_home_kb()
        )
        return ConversationHandler.END
    await reply(update,
        "📝 *Post Seat Swap — Step 1/4*\n\n"
        "Enter your *Train Number* 🚆\n_(Example: 12345 or Rajdhani Express)_"
    )
    return TRAIN

async def ps_train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ps_train"] = update.message.text.strip().upper()
    await update.message.reply_text(
        "📝 *Step 2/4*\n\nEnter your *Coach* 🚉\n_(Example: S1, B2, A1, H1)_",
        parse_mode="Markdown"
    )
    return COACH

async def ps_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ps_coach"] = update.message.text.strip().upper()
    await update.message.reply_text(
        "📝 *Step 3/4*\n\nEnter your *Current Seat* 💺\n_(Example: 45 Lower, 12 Upper)_",
        parse_mode="Markdown"
    )
    return CURRENT_SEAT

async def ps_current(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ps_current"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 *Step 4/4*\n\nWhich seat do you *want*? 🔄\nTap a button or type it:",
        reply_markup=seat_type_kb("want"),
        parse_mode="Markdown"
    )
    return WANTED_SEAT

async def ps_wanted_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ps_wanted"] = update.callback_query.data.replace("want_", "").title()
    await update.callback_query.answer()
    return await ps_finish(update, context)

async def ps_wanted_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ps_wanted"] = update.message.text.strip()
    return await ps_finish(update, context)

async def ps_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    train   = context.user_data["ps_train"]
    coach   = context.user_data["ps_coach"]
    current = context.user_data["ps_current"]
    wanted  = context.user_data["ps_wanted"]

    swap  = save_swap(user, train, coach, current, wanted)
    match = find_match(swap)

    text = (
        f"✅ *Swap Request Posted!*\n\n"
        f"🚆 Train: `{train}`\n"
        f"🚉 Coach: `{coach}`\n"
        f"💺 Has: `{current}`\n"
        f"🔄 Wants: `{wanted}`\n\n"
    )

    if match:
        contact = get_contact_text(match)
        u_data  = get_user(match["user_id"])
        text += (
            f"🎉 *INSTANT MATCH FOUND!*\n\n"
            f"👤 {match['name']} {u_data.get('badge','')}\n"
            f"💺 Has: `{match['current']}`\n"
            f"🔄 Wants: `{match['wanted']}`\n\n"
            f"📩 Contact: {contact}\n\n"
            f"_After swapping, tap Confirm below to earn points!_"
        )
        # Notify matched user
        try:
            my_contact = get_contact_text({"username": user.username, "name": user.first_name, "user_id": user.id})
            my_data    = get_user(user.id)
            match_msg  = (
                f"🎉 *MATCH FOUND for your swap!*\n\n"
                f"Train `{train}` — someone wants to swap with you!\n\n"
                f"👤 {user.first_name} {my_data.get('badge','')}\n"
                f"💺 Has: `{current}`\n"
                f"🔄 Wants: `{wanted}`\n\n"
                f"📩 Contact: {my_contact}\n\n"
                f"_After swapping, tap Confirm below to earn points!_"
            )
            await context.bot.send_message(
                chat_id=match["user_id"],
                text=match_msg,
                reply_markup=swap_result_kb(match["swap_id"], show_confirm=True),
                parse_mode="Markdown"
            )
        except Exception:
            pass
        kb = swap_result_kb(swap["swap_id"], show_confirm=True)
    else:
        text += "Your request is now *live*! 🔔 We'll notify you when a match is found."
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 Browse Swaps", callback_data="menu_search"),
                InlineKeyboardButton("🏠 Menu",          callback_data="menu_home"),
            ]
        ])

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")
    return ConversationHandler.END

# ─────────────────────────────────────────────
#  SEARCH / VIEW SWAPS FLOW  (train filter first)
# ─────────────────────────────────────────────
async def search_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update,
        "🔍 *Find Seat Swaps*\n\n"
        "Enter your *Train Number* to search:\n_(Example: 12345)_"
    )
    return SEARCH_TRAIN

async def search_by_train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    train = update.message.text.strip().upper()
    context.user_data["search_train"] = train
    all_swaps = get_all_swaps()
    results   = {k: v for k, v in all_swaps.items()
                 if v.get("train") == train and v.get("status") == "active"}

    if not results:
        await update.message.reply_text(
            f"😔 No active swaps for Train *{train}* right now.\n\n"
            f"Be the first! Use /postseat to post yours.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Post Swap", callback_data="menu_postseat")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
            ]),
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    # Group by coach
    coaches = {}
    for sid, s in results.items():
        c = s.get("coach", "?")
        coaches.setdefault(c, []).append(s)

    text  = f"🚆 *Train {train}* — {len(results)} swap(s) found\n\n"
    text += "_Tap a coach to see details or type coach name:_\n\n"
    text += "Coaches with swaps: " + ", ".join(f"`{c}`" for c in sorted(coaches.keys()))

    coach_btns = [
        InlineKeyboardButton(f"🚉 {c} ({len(v)})", callback_data=f"coach_{train}_{c}")
        for c, v in sorted(coaches.items())
    ]
    rows = [coach_btns[i:i+3] for i in range(0, len(coach_btns), 3)]
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")
    return ConversationHandler.END

async def show_coach_swaps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, train, coach = query.data.split("_", 2)
    all_swaps = get_all_swaps()
    results   = [v for v in all_swaps.values()
                 if v.get("train") == train and v.get("coach") == coach
                 and v.get("status") == "active"]

    if not results:
        await query.edit_message_text("No swaps found for this coach.", reply_markup=back_home_kb())
        return

    text = f"🚉 *Train {train} — Coach {coach}*\n{len(results)} swap(s)\n\n"
    rows = []
    for i, req in enumerate(results, 1):
        u    = get_user(req["user_id"])
        prem = "💎 " if u.get("premium") else ""
        text += (
            f"*#{i} — {prem}{req['name']}* {u.get('badge','')}\n"
            f"💺 Has: `{req['current']}`  →  🔄 Wants: `{req['wanted']}`\n"
            f"📩 {get_contact_text(req)}\n"
            f"🕐 {req.get('timestamp','')}\n"
            f"─────────────────\n"
        )
        rows.append([
            InlineKeyboardButton(f"📩 Contact #{i}", url=f"tg://user?id={req['user_id']}"),
            InlineKeyboardButton(f"🚩 Report #{i}", callback_data=f"report_{req['user_id']}"),
        ])
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")

# ─────────────────────────────────────────────
#  CONFIRM SWAP
# ─────────────────────────────────────────────
async def confirm_swap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    swap_id = query.data.replace("confirm_", "")

    confirmed_key = f"confirmed/{user_id}_{swap_id}"
    already = fb_get(confirmed_key)
    if already:
        await query.edit_message_text("✅ You already confirmed this swap!", reply_markup=back_home_kb())
        return

    fb_set(confirmed_key, True)
    award_points(user_id)
    u = get_user(user_id)

    await query.edit_message_text(
        f"🎉 *Swap Confirmed!*\n\n"
        f"✅ +10 points awarded\n"
        f"⭐ Total points: {u.get('points', 0)}\n"
        f"🏅 Badge: {u.get('badge', '')}\n\n"
        f"_{next_badge_info(u.get('swaps_done', 0))}_",
        reply_markup=back_home_kb(),
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
#  REPORT USER
# ─────────────────────────────────────────────
async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await query.answer()
    reporter   = update.effective_user.id
    reported   = int(query.data.replace("report_", ""))

    if reporter == reported:
        await query.answer("You can't report yourself!", show_alert=True)
        return

    key = f"reports/{reporter}_{reported}"
    if fb_get(key):
        await query.answer("You already reported this user.", show_alert=True)
        return

    fb_set(key, True)
    u      = get_user(reported)
    count  = u.get("reports", 0) + 1
    fb_update(f"users/{reported}", {"reports": count})

    if count >= 3:
        fb_update(f"users/{reported}", {"banned": True})
        delete_user_swap(reported)
        await context.bot.send_message(
            chat_id=reported,
            text="🚫 Your account has been suspended due to multiple reports."
        )
        await query.answer("User reported and banned.", show_alert=True)
    else:
        await query.answer(f"User reported. ({count}/3 reports)", show_alert=True)

# ─────────────────────────────────────────────
#  MY REQUEST
# ─────────────────────────────────────────────
async def myrequest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    all_swaps = get_all_swaps()
    req       = next((v for v in all_swaps.values() if v.get("user_id") == user_id), None)

    if not req:
        await reply(update,
            "📋 You have no active swap request.\n\nUse /postseat to post one!",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Post Swap", callback_data="menu_postseat")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
            ])
        )
        return

    await reply(update,
        f"📋 *Your Active Request*\n\n"
        f"🚆 Train: `{req['train']}`\n"
        f"🚉 Coach: `{req['coach']}`\n"
        f"💺 Has: `{req['current']}`\n"
        f"🔄 Wants: `{req['wanted']}`\n"
        f"🕐 Posted: {req.get('timestamp','')}",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel Request", callback_data="cancel_request")],
            [InlineKeyboardButton("🏠 Main Menu",      callback_data="menu_home")],
        ])
    )

# ─────────────────────────────────────────────
#  MY PROFILE
# ─────────────────────────────────────────────
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u    = get_user(user.id)
    prem = "💎 *PREMIUM*\n" if u.get("premium") else ""
    await reply(update,
        f"👤 *Your Profile*\n\n"
        f"{prem}"
        f"Name: *{user.first_name}*\n"
        f"Badge: {u.get('badge', get_badge(0))}\n"
        f"✅ Swaps Done: {u.get('swaps_done', 0)}\n"
        f"⭐ Points: {u.get('points', 0)}\n\n"
        f"📈 Next: _{next_badge_info(u.get('swaps_done', 0))}_",
        back_home_kb()
    )

# ─────────────────────────────────────────────
#  PREMIUM INFO
# ─────────────────────────────────────────────
async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update,
        "💎 *SeatSwap Premium*\n\n"
        "Free Plan:\n"
        "• 1 active swap request\n"
        "• Normal matching\n\n"
        "Premium Plan:\n"
        "• ✅ Unlimited swap requests\n"
        "• ✅ Priority listing (shown first)\n"
        "• ✅ 💎 Premium badge\n"
        "• ✅ Faster match notifications\n\n"
        "To upgrade, contact admin: @YourAdminUsername",
        back_home_kb()
    )

# ─────────────────────────────────────────────
#  CANCEL REQUEST
# ─────────────────────────────────────────────
async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    deleted = delete_user_swap(user_id)
    text    = "✅ Your swap request has been removed." if deleted else "You have no active request."
    await reply(update, text, back_home_kb())
    return ConversationHandler.END

# ─────────────────────────────────────────────
#  HELP
# ─────────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update,
        "❓ *How to use SeatSwap*\n\n"
        "1️⃣ Tap *Post Swap* → fill your details\n"
        "2️⃣ Tap *Find Swap* → enter train number\n"
        "3️⃣ Browse swaps coach-wise\n"
        "4️⃣ Contact the person via Telegram\n"
        "5️⃣ After swap, tap *Confirm Swap Done* → earn +10 points! 🎉\n\n"
        "🚩 *Report* fake/ghost users — 3 reports = auto ban\n\n"
        "🏅 *Badges:*\n"
        "🟢 New Traveler — Starting out\n"
        "⭐ Trusted Traveler — 3+ swaps\n"
        "🛡 Verified Swapper — 10+ swaps\n"
        "🚆 Seat Master — 25+ swaps\n\n"
        "💎 /premium — Upgrade for unlimited requests",
        back_home_kb()
    )

# ─────────────────────────────────────────────
#  ADMIN COMMANDS
# ─────────────────────────────────────────────
def is_admin(user_id):
    return user_id in ADMIN_IDS

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized.")
        return
    users     = fb_get("users") or {}
    swaps     = get_all_swaps()
    active    = sum(1 for s in swaps.values() if s.get("status") == "active")
    premiums  = sum(1 for u in users.values() if u.get("premium"))
    banned    = sum(1 for u in users.values() if u.get("banned"))
    await update.message.reply_text(
        f"📊 *SeatSwap Stats*\n\n"
        f"👥 Total Users: {len(users)}\n"
        f"🔄 Active Swaps: {active}\n"
        f"💎 Premium Users: {premiums}\n"
        f"🚫 Banned Users: {banned}",
        parse_mode="Markdown"
    )

async def admin_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setpremium <user_id>")
        return
    uid = int(context.args[0])
    fb_update(f"users/{uid}", {"premium": True})
    await update.message.reply_text(f"✅ User {uid} upgraded to Premium.")
    try:
        await context.bot.send_message(
            chat_id=uid,
            text="🎉 You've been upgraded to *SeatSwap Premium*! 💎\n\nEnjoy unlimited swap requests!",
            parse_mode="Markdown"
        )
    except Exception:
        pass

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    uid = int(context.args[0])
    fb_update(f"users/{uid}", {"banned": True})
    delete_user_swap(uid)
    await update.message.reply_text(f"🚫 User {uid} banned and requests removed.")

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    uid = int(context.args[0])
    fb_update(f"users/{uid}", {"banned": False, "reports": 0})
    await update.message.reply_text(f"✅ User {uid} unbanned.")

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    await update.message.reply_text("📢 Enter the broadcast message:")
    return BROADCAST_MSG

async def admin_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg   = update.message.text
    users = fb_get("users") or {}
    sent  = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"📢 *Announcement*\n\n{msg}", parse_mode="Markdown")
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Broadcast sent to {sent}/{len(users)} users.")
    return ConversationHandler.END

# ─────────────────────────────────────────────
#  CALLBACK ROUTER
# ─────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if   data == "menu_home":       await start(update, context)
    elif data == "menu_postseat":   await postseat_entry(update, context)
    elif data == "menu_search":     await search_entry(update, context)
    elif data == "menu_myrequest":  await myrequest(update, context)
    elif data == "menu_profile":    await profile(update, context)
    elif data == "menu_help":       await help_cmd(update, context)
    elif data == "cancel_request":  await cancel_cmd(update, context)
    elif data.startswith("coach_"): await show_coach_swaps(update, context)
    elif data.startswith("confirm_"): await confirm_swap(update, context)
    elif data.startswith("report_"):  await report_user(update, context)

# ─────────────────────────────────────────────
#  CONVERSATION HANDLERS
# ─────────────────────────────────────────────
postseat_conv = ConversationHandler(
    entry_points=[
        CommandHandler("postseat", postseat_entry),
    ],
    states={
        TRAIN:        [MessageHandler(filters.TEXT & ~filters.COMMAND, ps_train)],
        COACH:        [MessageHandler(filters.TEXT & ~filters.COMMAND, ps_coach)],
        CURRENT_SEAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ps_current)],
        WANTED_SEAT:  [
            CallbackQueryHandler(ps_wanted_btn, pattern="^want_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, ps_wanted_txt),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_cmd)],
    per_message=False,
)

search_conv = ConversationHandler(
    entry_points=[
        CommandHandler("viewswaps", search_entry),
    ],
    states={
        SEARCH_TRAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_by_train)],
    },
    fallbacks=[CommandHandler("cancel", cancel_cmd)],
    per_message=False,
)

broadcast_conv = ConversationHandler(
    entry_points=[CommandHandler("broadcast", admin_broadcast_start)],
    states={
        BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_send)],
    },
    fallbacks=[],
    per_message=False,
)

# ─────────────────────────────────────────────
#  APP SETUP
# ─────────────────────────────────────────────
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Conversation handlers first
app.add_handler(postseat_conv)
app.add_handler(search_conv)
app.add_handler(broadcast_conv)

# Commands
app.add_handler(CommandHandler("start",       start))
app.add_handler(CommandHandler("myrequest",   myrequest))
app.add_handler(CommandHandler("profile",     profile))
app.add_handler(CommandHandler("premium",     premium_info))
app.add_handler(CommandHandler("help",        help_cmd))
app.add_handler(CommandHandler("cancel",      cancel_cmd))
app.add_handler(CommandHandler("stats",       admin_stats))
app.add_handler(CommandHandler("setpremium",  admin_premium))
app.add_handler(CommandHandler("ban",         admin_ban))
app.add_handler(CommandHandler("unban",       admin_unban))

# Inline buttons
app.add_handler(CallbackQueryHandler(button_handler))

print("SeatSwap Bot is running... 🚆")
app.run_polling()
