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
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]

# ─────────────────────────────────────────────
#  FIREBASE INIT + STARTUP CHECK
# ─────────────────────────────────────────────
FIREBASE_ON = False
firebase_key_raw = os.getenv("FIREBASE_KEY")

if firebase_key_raw:
    try:
        firebase_key = json.loads(firebase_key_raw)
        cred = credentials.Certificate(firebase_key)
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://seatswap-a96ec-default-rtdb.firebaseio.com/"
        })
        # ── STARTUP TEST ──
        test_ref = db.reference("bot_status")
        test_ref.set({
            "status":    "online",
            "last_boot": datetime.now().strftime("%d %b %Y %I:%M %p"),
        })
        result = test_ref.get()
        if result and result.get("status") == "online":
            FIREBASE_ON = True
            print("✅ Firebase connected and verified!")
        else:
            print("⚠️  Firebase write/read test failed.")
    except Exception as e:
        print(f"❌ Firebase error: {e}")
else:
    print("⚠️  FIREBASE_KEY not set. Running without database.")

# ─────────────────────────────────────────────
#  CONVERSATION STATES
# ─────────────────────────────────────────────
TRAIN, COACH, CURRENT_SEAT, WANTED_SEAT = range(4)
SEARCH_TRAIN                             = 4
BROADCAST_MSG                            = 5

# ─────────────────────────────────────────────
#  BADGE SYSTEM  (improved)
# ─────────────────────────────────────────────
BADGE_LEVELS = [
    (0,  "🌱",  "Newcomer",         "#"),
    (3,  "🎫",  "Regular Traveler", "🌱 Newcomer"),
    (10, "⭐",  "Trusted Member",   "🎫 Regular"),
    (25, "🔰",  "Expert Swapper",   "⭐ Trusted"),
    (50, "👑",  "Seat Master",      "🔰 Expert"),
]

def get_badge(swaps):
    badge = BADGE_LEVELS[0]
    for level in BADGE_LEVELS:
        if swaps >= level[0]:
            badge = level
    return f"{badge[0]} {badge[2]}"

def badge_progress_bar(swaps):
    current_level = BADGE_LEVELS[0]
    next_level    = None
    for i, level in enumerate(BADGE_LEVELS):
        if swaps >= level[0]:
            current_level = level
            if i + 1 < len(BADGE_LEVELS):
                next_level = BADGE_LEVELS[i + 1]
    if not next_level:
        return "👑 *Maximum badge reached!* You are a Seat Master.", 100

    done    = swaps - current_level[0]
    needed  = next_level[0] - current_level[0]
    pct     = int((done / needed) * 10)
    bar     = "█" * pct + "░" * (10 - pct)
    left    = next_level[0] - swaps
    info    = (
        f"[{bar}] {done}/{needed}\n"
        f"_{left} more swap(s) to {next_level[0]} {next_level[2]}_"
    )
    return info, int(pct * 10)

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
    if fb_get(f"users/{user.id}"):
        return
    fb_set(f"users/{user.id}", {
        "name":       user.first_name,
        "username":   user.username or "",
        "points":     0,
        "swaps_done": 0,
        "badge":      get_badge(0),
        "premium":    False,
        "banned":     False,
        "reports":    0,
        "joined":     datetime.now().strftime("%d %b %Y"),
    })

def get_user(user_id):
    return fb_get(f"users/{user_id}") or {
        "name": "User", "username": "", "points": 0,
        "swaps_done": 0, "badge": get_badge(0),
        "premium": False, "banned": False, "reports": 0,
    }

def is_banned(user_id):
    return get_user(user_id).get("banned", False)

def get_contact_text(req):
    if req.get("username"):
        return f"@{req['username']}"
    return f"[{req['name']}](tg://user?id={req['user_id']})"

def time_ago(timestamp_str):
    try:
        then  = datetime.strptime(timestamp_str, "%d %b %Y %I:%M %p")
        diff  = datetime.now() - then
        mins  = int(diff.total_seconds() / 60)
        if mins < 1:    return "just now"
        if mins < 60:   return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:  return f"{hours}h ago"
        return f"{diff.days}d ago"
    except Exception:
        return timestamp_str

def save_swap(user, train, coach, current, wanted):
    swap_id   = str(uuid.uuid4())[:8]
    all_swaps = fb_get("swaps") or {}
    for sid, s in all_swaps.items():
        if s.get("user_id") == user.id:
            fb_delete(f"swaps/{sid}")
    u = get_user(user.id)
    swap = {
        "swap_id":   swap_id,
        "user_id":   user.id,
        "name":      user.first_name,
        "username":  user.username or "",
        "badge":     u.get("badge", get_badge(0)),
        "premium":   u.get("premium", False),
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
    deleted   = False
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
        if s.get("train")   != new_swap["train"]:   continue
        tw = s.get("wanted", "").lower()
        tc = s.get("current","").lower()
        if (tw == nc or tw in opposites.get(nc, []) or
                nw == tc or nw in opposites.get(tc, [])):
            return s
    return None

def award_points(user_id):
    u     = get_user(user_id)
    swaps = u.get("swaps_done", 0) + 1
    pts   = u.get("points", 0) + 10
    fb_update(f"users/{user_id}", {
        "swaps_done": swaps,
        "points":     pts,
        "badge":      get_badge(swaps),
    })
    return swaps, pts

# ─────────────────────────────────────────────
#  KEYBOARDS
# ─────────────────────────────────────────────
def main_menu_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Post Swap",  callback_data="menu_postseat"),
            InlineKeyboardButton("🔍 Find Swap",  callback_data="menu_search"),
        ],
        [
            InlineKeyboardButton("📋 My Request", callback_data="menu_myrequest"),
            InlineKeyboardButton("👤 My Profile", callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton("💎 Premium",    callback_data="menu_premium"),
            InlineKeyboardButton("❓ Help",        callback_data="menu_help"),
        ],
    ])

def back_home_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
    ])

def seat_type_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬇️ Lower",      callback_data="want_Lower"),
            InlineKeyboardButton("⬆️ Upper",      callback_data="want_Upper"),
        ],
        [
            InlineKeyboardButton("➡️ Middle",     callback_data="want_Middle"),
            InlineKeyboardButton("↘️ Side Lower", callback_data="want_Side Lower"),
        ],
        [
            InlineKeyboardButton("↗️ Side Upper", callback_data="want_Side Upper"),
            InlineKeyboardButton("🪑 Any",        callback_data="want_Any Lower"),
        ],
    ])

# ─────────────────────────────────────────────
#  REPLY HELPER
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
        await reply(update, "🚫 Your account has been suspended.")
        return
    db_status = "✅ Connected" if FIREBASE_ON else "⚠️ Offline (no database)"
    await reply(update,
        f"🚆 *Welcome to SeatSwap!*\n\n"
        f"Hey *{user.first_name}*, exchange your Indian train seat with fellow passengers — instantly!\n\n"
        f"🔄 Post your seat swap request\n"
        f"🔍 Find swaps by train & coach\n"
        f"🤝 Get matched automatically\n"
        f"🏅 Earn badges with every swap\n\n"
        f"_{db_status}_",
        main_menu_kb()
    )

# ─────────────────────────────────────────────
#  POST SWAP FLOW
# ─────────────────────────────────────────────
async def postseat_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        await reply(update, "🚫 You are banned.")
        return ConversationHandler.END
    # Free user limit
    u         = get_user(user.id)
    my_swaps  = [s for s in get_all_swaps().values() if s.get("user_id") == user.id]
    if not u.get("premium") and len(my_swaps) >= 1:
        await reply(update,
            "⚠️ *Free users can have 1 active request.*\n\n"
            "Cancel your existing request first:\n/cancel\n\n"
            "Or upgrade to 💎 *Premium* for unlimited requests.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 See Premium",    callback_data="menu_premium")],
                [InlineKeyboardButton("❌ Cancel Request", callback_data="cancel_request")],
                [InlineKeyboardButton("🏠 Main Menu",      callback_data="menu_home")],
            ])
        )
        return ConversationHandler.END
    await reply(update,
        "📝 *Post Seat Swap*\n\n"
        "Step *1/4* — Enter your *Train Number* 🚆\n\n"
        "_(Example: 12345, Rajdhani, Duronto)_"
    )
    return TRAIN

async def ps_train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ps_train"] = update.message.text.strip().upper()
    await update.message.reply_text(
        "Step *2/4* — Enter your *Coach* 🚉\n\n_(Example: S1, B2, A1, H1)_",
        parse_mode="Markdown"
    )
    return COACH

async def ps_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ps_coach"] = update.message.text.strip().upper()
    await update.message.reply_text(
        "Step *3/4* — Enter your *Current Seat* 💺\n\n_(Example: 45 Lower, 12 Upper)_",
        parse_mode="Markdown"
    )
    return CURRENT_SEAT

async def ps_current(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ps_current"] = update.message.text.strip()
    await update.message.reply_text(
        "Step *4/4* — Which seat do you *want*? 🔄\n\nTap a button below:",
        reply_markup=seat_type_kb(),
        parse_mode="Markdown"
    )
    return WANTED_SEAT

async def ps_wanted_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ps_wanted"] = update.callback_query.data.replace("want_", "")
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
        u_match  = get_user(match["user_id"])
        contact  = get_contact_text(match)
        text += (
            f"🎉 *INSTANT MATCH FOUND!*\n\n"
            f"👤 *{match['name']}* {u_match.get('badge','')}\n"
            premium_text = "💎 Premium User\n" if u_match.get("premium") else ""
            f"💺 Has: `{match['current']}`\n"
            f"🔄 Wants: `{match['wanted']}`\n\n"
            f"📩 Contact: {contact}\n\n"
            f"_After swapping tap ✅ Confirm below to earn +10 points!_"
        )
        # Notify matched user
        try:
            my_u      = get_user(user.id)
            my_badge  = my_u.get("badge", "")
            my_contact= get_contact_text({"username": user.username, "name": user.first_name, "user_id": user.id})
            await context.bot.send_message(
                chat_id=match["user_id"],
                text=(
                    f"🎉 *MATCH FOUND!*\n\n"
                    f"Train `{train}` — Someone wants to swap with you!\n\n"
                    f"👤 *{user.first_name}* {my_badge}\n"
                    f"💺 Has: `{current}`\n"
                    f"🔄 Wants: `{wanted}`\n\n"
                    f"📩 Contact: {my_contact}\n\n"
                    f"_After swapping tap ✅ Confirm to earn +10 points!_"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Confirm Swap Done", callback_data=f"confirm_{match['swap_id']}")],
                    [InlineKeyboardButton("🏠 Main Menu",         callback_data="menu_home")],
                ]),
                parse_mode="Markdown"
            )
        except Exception:
            pass
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm Swap Done", callback_data=f"confirm_{swap['swap_id']}")],
            [InlineKeyboardButton("🏠 Main Menu",         callback_data="menu_home")],
        ])
    else:
        text += "Your request is *live*! 🔔\nWe'll notify you instantly when a match is found."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Browse Swaps", callback_data="menu_search")],
            [InlineKeyboardButton("🏠 Main Menu",    callback_data="menu_home")],
        ])

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")
    return ConversationHandler.END

# ─────────────────────────────────────────────
#  FIND / SEARCH FLOW  (train → coach filter)
# ─────────────────────────────────────────────
async def search_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update,
        "🔍 *Find Seat Swaps*\n\n"
        "Enter *Train Number* to search:\n_(Example: 12345)_"
    )
    return SEARCH_TRAIN

async def search_by_train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    train     = update.message.text.strip().upper()
    all_swaps = get_all_swaps()
    results   = {k: v for k, v in all_swaps.items()
                 if v.get("train") == train and v.get("status") == "active"}

    if not results:
        await update.message.reply_text(
            f"😔 No active swaps for *Train {train}* right now.\n\n"
            f"Be the first to post one!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Post Swap", callback_data="menu_postseat")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
            ]),
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    # Group by coach, premium first
    coaches = {}
    for sid, s in results.items():
        c = s.get("coach", "?")
        coaches.setdefault(c, []).append(s)

    total = len(results)
    text  = (
        f"🚆 *Train {train}*\n"
        f"Found *{total} swap request(s)*\n\n"
        f"Select a coach to see details 👇"
    )
    coach_btns = [
        InlineKeyboardButton(
            f"🚉 Coach {c}  ({len(v)})",
            callback_data=f"coach_{train}_{c}"
        )
        for c, v in sorted(coaches.items())
    ]
    rows = [coach_btns[i:i+2] for i in range(0, len(coach_btns), 2)]
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")
    return ConversationHandler.END

async def show_coach_swaps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    _, train, coach = update.callback_query.data.split("_", 2)
    all_swaps = get_all_swaps()
    results   = sorted(
        [v for v in all_swaps.values()
         if v.get("train") == train and v.get("coach") == coach and v.get("status") == "active"],
        key=lambda x: (not x.get("premium", False))   # premium first
    )

    if not results:
        await update.callback_query.edit_message_text("No swaps found for this coach.", reply_markup=back_home_kb())
        return

    text = f"🚉 *Train {train} — Coach {coach}*\n{len(results)} swap(s)\n\n"
    rows = []
    for i, req in enumerate(results, 1):
        prem    = "💎 " if req.get("premium") else ""
        badge   = req.get("badge", "🌱 Newcomer")
        ago     = time_ago(req.get("timestamp", ""))
        contact = get_contact_text(req)
        text += (
            f"*#{i}* {prem}*{req['name']}*  {badge}\n"
            f"💺 Has: `{req['current']}`  →  🔄 Wants: `{req['wanted']}`\n"
            f"📩 {contact}  ·  🕐 {ago}\n"
            f"─────────────────\n"
        )
        rows.append([
            InlineKeyboardButton(f"📩 Contact #{i}", url=f"tg://user?id={req['user_id']}"),
            InlineKeyboardButton(f"🚩 Report #{i}",  callback_data=f"report_{req['user_id']}"),
        ])
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")])
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")

# ─────────────────────────────────────────────
#  CONFIRM SWAP
# ─────────────────────────────────────────────
async def confirm_swap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id  = update.effective_user.id
    swap_id  = update.callback_query.data.replace("confirm_", "")
    conf_key = f"confirmed/{user_id}_{swap_id}"

    if fb_get(conf_key):
        await update.callback_query.edit_message_text(
            "✅ You already confirmed this swap!",
            reply_markup=back_home_kb()
        )
        return

    fb_set(conf_key, True)
    swaps_done, total_pts = award_points(user_id)
    u    = get_user(user_id)
    bar, _ = badge_progress_bar(swaps_done)
    new_badge = get_badge(swaps_done)

    await update.callback_query.edit_message_text(
        f"🎉 *Swap Confirmed!*\n\n"
        f"✅ +10 points earned!\n"
        f"⭐ Total points: *{total_pts}*\n"
        f"🏅 Badge: *{new_badge}*\n\n"
        f"📈 Progress:\n{bar}",
        reply_markup=back_home_kb(),
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
#  REPORT
# ─────────────────────────────────────────────
async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reporter = update.effective_user.id
    reported = int(update.callback_query.data.replace("report_", ""))

    if reporter == reported:
        await update.callback_query.answer("You can't report yourself!", show_alert=True)
        return

    key = f"reports/{reporter}_{reported}"
    if fb_get(key):
        await update.callback_query.answer("You already reported this user.", show_alert=True)
        return

    fb_set(key, True)
    u     = get_user(reported)
    count = u.get("reports", 0) + 1
    fb_update(f"users/{reported}", {"reports": count})

    if count >= 3:
        fb_update(f"users/{reported}", {"banned": True})
        delete_user_swap(reported)
        try:
            await context.bot.send_message(
                chat_id=reported,
                text="🚫 Your account has been suspended due to multiple reports.\n\nContact support if you think this is a mistake."
            )
        except Exception:
            pass
        await update.callback_query.answer("⚠️ User has been banned after 3 reports.", show_alert=True)
    else:
        await update.callback_query.answer(f"User reported. ({count}/3 reports before ban)", show_alert=True)

# ─────────────────────────────────────────────
#  MY REQUEST
# ─────────────────────────────────────────────
async def myrequest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    all_swaps = get_all_swaps()
    req       = next((v for v in all_swaps.values() if v.get("user_id") == user_id), None)

    if not req:
        await reply(update,
            "📋 You have no active swap request.\n\nPost one using the button below!",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Post Swap", callback_data="menu_postseat")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")],
            ])
        )
        return

    ago = time_ago(req.get("timestamp", ""))
    await reply(update,
        f"📋 *Your Active Request*\n\n"
        f"🚆 Train: `{req['train']}`\n"
        f"🚉 Coach: `{req['coach']}`\n"
        f"💺 Has: `{req['current']}`\n"
        f"🔄 Wants: `{req['wanted']}`\n"
        f"🕐 Posted: {ago}",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel Request", callback_data="cancel_request")],
            [InlineKeyboardButton("🏠 Main Menu",      callback_data="menu_home")],
        ])
    )

# ─────────────────────────────────────────────
#  PROFILE
# ─────────────────────────────────────────────
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user      = update.effective_user
    u         = get_user(user.id)
    swaps     = u.get("swaps_done", 0)
    points    = u.get("points", 0)
    badge     = get_badge(swaps)
    bar, pct  = badge_progress_bar(swaps)
    prem_line = "💎 *PREMIUM MEMBER*\n\n" if u.get("premium") else ""

    await reply(update,
        f"👤 *Your Profile*\n\n"
        f"{prem_line}"
        f"Name:  *{user.first_name}*\n"
        f"Badge: {badge}\n"
        f"✅ Swaps Done: *{swaps}*\n"
        f"⭐ Points: *{points}*\n\n"
        f"📈 *Next Badge:*\n{bar}",
        back_home_kb()
    )

# ─────────────────────────────────────────────
#  PREMIUM
# ─────────────────────────────────────────────
async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update,
        "💎 *SeatSwap Premium*\n\n"
        "*Free Plan:*\n"
        "• 1 active swap request\n"
        "• Standard matching\n"
        "• Basic badges\n\n"
        "*Premium Plan:*\n"
        "• ✅ Unlimited swap requests\n"
        "• ✅ Listed *first* in search results\n"
        "• ✅ 💎 Premium badge on profile\n"
        "• ✅ Instant match notifications\n"
        "• ✅ Priority support\n\n"
        "📩 To upgrade, contact: @YourAdminUsername\n"
        "_Coming soon: UPI payment integration!_",
        back_home_kb()
    )

# ─────────────────────────────────────────────
#  HELP
# ─────────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update,
        "❓ *How to use SeatSwap*\n\n"
        "1️⃣ Tap *Post Swap* → fill train, coach, seat details\n"
        "2️⃣ Tap *Find Swap* → enter train number → pick coach\n"
        "3️⃣ Contact the person directly via Telegram\n"
        "4️⃣ After swapping → tap *Confirm Swap Done* → earn +10 pts!\n\n"
        "🚩 *Report* fake/ghost users — 3 reports = auto ban\n\n"
        "🏅 *Badge Levels:*\n"
        "🌱 Newcomer       — Starting out\n"
        "🎫 Regular          — 3+ swaps\n"
        "⭐ Trusted Member — 10+ swaps\n"
        "🔰 Expert Swapper — 25+ swaps\n"
        "👑 Seat Master      — 50+ swaps\n\n"
        "Higher badge = more people trust you = more swaps! 🚆",
        back_home_kb()
    )

# ─────────────────────────────────────────────
#  CANCEL
# ─────────────────────────────────────────────
async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deleted = delete_user_swap(update.effective_user.id)
    text    = "✅ Your swap request has been removed." if deleted else "You have no active request to cancel."
    await reply(update, text, back_home_kb())
    return ConversationHandler.END

# ─────────────────────────────────────────────
#  ADMIN COMMANDS
# ─────────────────────────────────────────────
def is_admin(uid): return uid in ADMIN_IDS

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized.")
        return
    users    = fb_get("users") or {}
    swaps    = get_all_swaps()
    active   = sum(1 for s in swaps.values() if s.get("status") == "active")
    premiums = sum(1 for u in users.values() if u.get("premium"))
    banned   = sum(1 for u in users.values() if u.get("banned"))
    db_ok    = "✅ Connected" if FIREBASE_ON else "❌ Offline"
    await update.message.reply_text(
        f"📊 *SeatSwap Stats*\n\n"
        f"🗄 Database: {db_ok}\n"
        f"👥 Total Users: {len(users)}\n"
        f"🔄 Active Swaps: {active}\n"
        f"💎 Premium Users: {premiums}\n"
        f"🚫 Banned Users: {banned}",
        parse_mode="Markdown"
    )

async def checkdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized.")
        return
    if not FIREBASE_ON:
        await update.message.reply_text("❌ Firebase is NOT connected.\n\nCheck FIREBASE_KEY variable in Railway.")
        return
    try:
        db.reference("bot_status").update({"ping": datetime.now().strftime("%d %b %Y %I:%M %p")})
        result = db.reference("bot_status").get()
        await update.message.reply_text(
            f"✅ *Firebase is working!*\n\n"
            f"Last ping: `{result.get('ping','?')}`\n"
            f"Last boot: `{result.get('last_boot','?')}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Firebase error:\n`{e}`", parse_mode="Markdown")

async def admin_set_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("Usage: /setpremium <user_id>")
        return
    uid = int(context.args[0])
    fb_update(f"users/{uid}", {"premium": True})
    await update.message.reply_text(f"✅ User {uid} upgraded to 💎 Premium.")
    try:
        await context.bot.send_message(
            chat_id=uid,
            text="🎉 You've been upgraded to *SeatSwap Premium*! 💎\n\nEnjoy unlimited swap requests and priority listing!",
            parse_mode="Markdown"
        )
    except Exception: pass

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    uid = int(context.args[0])
    fb_update(f"users/{uid}", {"banned": True})
    delete_user_swap(uid)
    await update.message.reply_text(f"🚫 User {uid} banned.")

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    uid = int(context.args[0])
    fb_update(f"users/{uid}", {"banned": False, "reports": 0})
    await update.message.reply_text(f"✅ User {uid} unbanned.")

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    await update.message.reply_text("📢 Enter your broadcast message:")
    return BROADCAST_MSG

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg   = update.message.text
    users = fb_get("users") or {}
    sent  = 0
    for uid in users:
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"📢 *Announcement from SeatSwap*\n\n{msg}",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception: pass
    await update.message.reply_text(f"✅ Sent to {sent}/{len(users)} users.")
    return ConversationHandler.END

# ─────────────────────────────────────────────
#  CALLBACK ROUTER
# ─────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if   data == "menu_home":        await start(update, context)
    elif data == "menu_postseat":    await postseat_entry(update, context)
    elif data == "menu_search":      await search_entry(update, context)
    elif data == "menu_myrequest":   await myrequest(update, context)
    elif data == "menu_profile":     await profile(update, context)
    elif data == "menu_premium":     await premium_info(update, context)
    elif data == "menu_help":        await help_cmd(update, context)
    elif data == "cancel_request":   await cancel_cmd(update, context)
    elif data.startswith("coach_"):  await show_coach_swaps(update, context)
    elif data.startswith("confirm_"):await confirm_swap(update, context)
    elif data.startswith("report_"): await report_user(update, context)

# ─────────────────────────────────────────────
#  CONVERSATION HANDLERS
# ─────────────────────────────────────────────
postseat_conv = ConversationHandler(
    entry_points=[CommandHandler("postseat", postseat_entry)],
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
    entry_points=[CommandHandler("viewswaps", search_entry)],
    states={
        SEARCH_TRAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_by_train)],
    },
    fallbacks=[CommandHandler("cancel", cancel_cmd)],
    per_message=False,
)

broadcast_conv = ConversationHandler(
    entry_points=[CommandHandler("broadcast", broadcast_start)],
    states={
        BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)],
    },
    fallbacks=[],
    per_message=False,
)

# ─────────────────────────────────────────────
#  APP SETUP
# ─────────────────────────────────────────────
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(postseat_conv)
app.add_handler(search_conv)
app.add_handler(broadcast_conv)

app.add_handler(CommandHandler("start",      start))
app.add_handler(CommandHandler("myrequest",  myrequest))
app.add_handler(CommandHandler("profile",    profile))
app.add_handler(CommandHandler("premium",    premium_info))
app.add_handler(CommandHandler("help",       help_cmd))
app.add_handler(CommandHandler("cancel",     cancel_cmd))
app.add_handler(CommandHandler("stats",      admin_stats))
app.add_handler(CommandHandler("checkdb",    checkdb))
app.add_handler(CommandHandler("setpremium", admin_set_premium))
app.add_handler(CommandHandler("ban",        admin_ban))
app.add_handler(CommandHandler("unban",      admin_unban))

app.add_handler(CallbackQueryHandler(button_handler))

print("🚆 SeatSwap Bot is running...")
app.run_polling()
