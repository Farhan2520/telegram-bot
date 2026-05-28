import os, json, uuid, re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    ContextTypes, MessageHandler,
    CallbackQueryHandler, filters,
)
import firebase_admin
from firebase_admin import credentials, db

# ═══════════════════════════════════════════════
#   CONFIG
# ═══════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS","0").split(",") if x.strip().isdigit()]

# ═══════════════════════════════════════════════
#   FIREBASE
# ═══════════════════════════════════════════════
FIREBASE_ON = False
try:
    raw = os.getenv("FIREBASE_KEY")
    if raw:
        key  = json.loads(raw)
        cred = credentials.Certificate(key)
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://seatswap-a96ec-default-rtdb.firebaseio.com/"
        })
        db.reference("bot_status").set({
            "status":    "online",
            "boot_time": datetime.now().strftime("%d %b %Y %I:%M %p"),
        })
        FIREBASE_ON = True
        print("✅ Firebase connected!")
    else:
        print("⚠️  FIREBASE_KEY missing — running offline")
except Exception as e:
    print(f"❌ Firebase error: {e}")

# ═══════════════════════════════════════════════
#   TRAIN + COACH DATABASE
# ═══════════════════════════════════════════════
POPULAR_TRAINS = {
    "12301": "Howrah Rajdhani Express",
    "12302": "New Delhi Rajdhani Express",
    "12303": "Poorva Express",
    "12304": "Poorva Express",
    "12305": "Howrah Rajdhani Express",
    "12306": "Howrah Rajdhani Express",
    "12309": "Rajendra Nagar Patna Rajdhani",
    "12313": "Sealdah Rajdhani Express",
    "12314": "Sealdah Rajdhani Express",
    "12311": "Howrah Kalka Mail",
    "12312": "Kalka Howrah Mail",
    "12343": "Darjeeling Mail",
    "12344": "Darjeeling Mail",
    "12381": "Poorabh Express",
    "12382": "Poorabh Express",
    "12259": "Sealdah Duronto Express",
    "12260": "Sealdah Duronto Express",
    "13005": "Howrah Amritsar Express",
    "13006": "Amritsar Howrah Express",
    "12017": "Howrah Shatabdi Express",
    "12018": "Howrah Shatabdi Express",
    "12951": "Mumbai Rajdhani Express",
    "12952": "Mumbai Rajdhani Express",
    "12621": "Tamil Nadu Express",
    "12622": "Tamil Nadu Express",
    "12001": "Bhopal Shatabdi Express",
    "12002": "Bhopal Shatabdi Express",
    "11061": "LTT Jabalpur Express",
    "11062": "Jabalpur LTT Express",
    "22691": "Rajdhani Express",
    "22692": "Rajdhani Express",
    "12101": "Jnaneshwari Super Deluxe",
    "12102": "Jnaneshwari Super Deluxe",
    "12041": "New Jalpaiguri Shatabdi",
    "12042": "New Jalpaiguri Shatabdi",
    "12423": "Dibrugarh Rajdhani",
    "12424": "Dibrugarh Rajdhani",
}

COACH_TYPES = {
    "SL": {"label": "🛏  Sleeper  (S1–S12)",  "coaches": [f"S{i}" for i in range(1,13)]},
    "3A": {"label": "❄️  AC 3 Tier (B1–B6)",  "coaches": [f"B{i}" for i in range(1,7)]},
    "2A": {"label": "❄️  AC 2 Tier (A1–A4)",  "coaches": [f"A{i}" for i in range(1,5)]},
    "1A": {"label": "❄️  AC 1st  (H1–H2)",    "coaches": ["H1","H2"]},
    "CC": {"label": "💺  Chair Car (C1–C8)",   "coaches": [f"C{i}" for i in range(1,9)]},
    "EC": {"label": "💺  Exec Chair (EC1–EC3)","coaches": ["EC1","EC2","EC3"]},
    "GN": {"label": "🚃  General  (GS)",       "coaches": ["GS1","GS2","GS3"]},
}

BERTHS = ["Lower","Middle","Upper","Side Lower","Side Upper"]
BERTH_EMOJI = {
    "Lower":      "⬇️",
    "Middle":     "➡️",
    "Upper":      "⬆️",
    "Side Lower": "↘️",
    "Side Upper": "↗️",
}

# ═══════════════════════════════════════════════
#   BADGE SYSTEM
# ═══════════════════════════════════════════════
BADGE_LEVELS = [
    (0,  "🌱", "Newcomer"),
    (3,  "🎫", "Regular Traveler"),
    (10, "⭐", "Trusted Member"),
    (25, "🔰", "Expert Swapper"),
    (50, "👑", "Seat Master"),
]

def get_badge(n):
    b = BADGE_LEVELS[0]
    for lvl in BADGE_LEVELS:
        if n >= lvl[0]: b = lvl
    return f"{b[0]} {b[2]}"

def progress_bar(n):
    cur = BADGE_LEVELS[0]; nxt = None
    for i, lvl in enumerate(BADGE_LEVELS):
        if n >= lvl[0]:
            cur = lvl
            nxt = BADGE_LEVELS[i+1] if i+1 < len(BADGE_LEVELS) else None
    if not nxt:
        return "👑 *Maximum badge reached!*", 100
    done   = n - cur[0]
    needed = nxt[0] - cur[0]
    filled = int((done/needed)*10)
    bar    = "█"*filled + "░"*(10-filled)
    left   = nxt[0] - n
    return f"`[{bar}]` {done}/{needed}\n_{left} more → {nxt[0]} {nxt[2]}_", int(filled*10)

# ═══════════════════════════════════════════════
#   FIREBASE HELPERS
# ═══════════════════════════════════════════════
def fb_get(path):
    if not FIREBASE_ON: return None
    try: return db.reference(path).get()
    except: return None

def fb_set(path, data):
    if not FIREBASE_ON: return
    try: db.reference(path).set(data)
    except Exception as e: print(f"fb_set error {path}: {e}")

def fb_upd(path, data):
    if not FIREBASE_ON: return
    try: db.reference(path).update(data)
    except Exception as e: print(f"fb_upd error {path}: {e}")

def fb_del(path):
    if not FIREBASE_ON: return
    try: db.reference(path).delete()
    except: pass

def ensure_user(user):
    if fb_get(f"users/{user.id}"): return
    fb_set(f"users/{user.id}", {
        "name": user.first_name, "username": user.username or "",
        "points": 0, "swaps_done": 0, "badge": get_badge(0),
        "banned": False, "reports": 0,
        "joined": datetime.now().strftime("%d %b %Y"),
    })

def get_user(uid):
    return fb_get(f"users/{uid}") or {
        "name":"User","username":"","points":0,
        "swaps_done":0,"badge":get_badge(0),"banned":False,"reports":0,
    }

def is_banned(uid):
    return get_user(uid).get("banned", False)

def get_all_swaps():
    return fb_get("swaps") or {}

def user_swap(uid):
    return next((v for v in get_all_swaps().values() if v.get("user_id")==uid), None)

def save_swap(user, train, train_name, coach_type, coach, current, wanted):
    sid = str(uuid.uuid4())[:8]
    # remove old request
    for k,v in get_all_swaps().items():
        if v.get("user_id") == user.id: fb_del(f"swaps/{k}")
    u = get_user(user.id)
    swap = {
        "swap_id": sid, "user_id": user.id,
        "name": user.first_name, "username": user.username or "",
        "badge": u.get("badge", get_badge(0)),
        "train": train, "train_name": train_name,
        "coach_type": coach_type, "coach": coach,
        "current": current, "wanted": wanted,
        "status": "active",
        "timestamp": datetime.now().strftime("%d %b %Y %I:%M %p"),
    }
    fb_set(f"swaps/{sid}", swap)
    return swap

def delete_my_swap(uid):
    deleted = False
    for k,v in get_all_swaps().items():
        if v.get("user_id") == uid:
            fb_del(f"swaps/{k}"); deleted = True
    return deleted

def find_match(sw):
    opp = {
        "lower":      ["upper","middle"],
        "upper":      ["lower","middle"],
        "middle":     ["lower","upper"],
        "side lower": ["side upper"],
        "side upper": ["side lower"],
    }
    nw = sw["wanted"].lower(); nc = sw["current"].lower()
    for k,s in get_all_swaps().items():
        if s.get("user_id") == sw["user_id"]: continue
        if s.get("train")   != sw["train"]:   continue
        tw = s.get("wanted","").lower(); tc = s.get("current","").lower()
        if tw==nc or tw in opp.get(nc,[]) or nw==tc or nw in opp.get(tc,[]):
            return s
    return None

def award(uid):
    u  = get_user(uid)
    sd = u.get("swaps_done",0)+1
    pt = u.get("points",0)+10
    fb_upd(f"users/{uid}", {"swaps_done":sd,"points":pt,"badge":get_badge(sd)})
    return sd, pt

def contact_link(req):
    if req.get("username"): return f"@{req['username']}"
    return f"[{req['name']}](tg://user?id={req['user_id']})"

def time_ago(ts):
    try:
        d = datetime.strptime(ts, "%d %b %Y %I:%M %p")
        m = int((datetime.now()-d).total_seconds()/60)
        if m<1:  return "just now"
        if m<60: return f"{m}m ago"
        h = m//60
        if h<24: return f"{h}h ago"
        return f"{(datetime.now()-d).days}d ago"
    except: return ts

# ═══════════════════════════════════════════════
#   KEYBOARD BUILDERS
# ═══════════════════════════════════════════════
def kb_main():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄  Post Swap",    callback_data="flow_postseat"),
            InlineKeyboardButton("🔍  Find Swap",    callback_data="flow_search"),
        ],
        [
            InlineKeyboardButton("📋  My Request",   callback_data="flow_myrequest"),
            InlineKeyboardButton("👤  My Profile",   callback_data="flow_profile"),
        ],
        [
            InlineKeyboardButton("❓  Help",          callback_data="flow_help"),
            InlineKeyboardButton("📊  Stats",         callback_data="flow_stats"),
        ],
    ])

def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠  Main Menu", callback_data="flow_home")],
    ])

def kb_coach_types():
    rows = []
    items = list(COACH_TYPES.items())
    for i in range(0, len(items), 2):
        row = []
        for code, info in items[i:i+2]:
            row.append(InlineKeyboardButton(info["label"], callback_data=f"ct_{code}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("🏠  Main Menu", callback_data="flow_home")])
    return InlineKeyboardMarkup(rows)

def kb_coaches(coach_list):
    rows = []
    for i in range(0, len(coach_list), 4):
        rows.append([
            InlineKeyboardButton(c, callback_data=f"cn_{c}")
            for c in coach_list[i:i+4]
        ])
    rows.append([InlineKeyboardButton("⬅️  Back", callback_data="ps_back_coachtype")])
    return InlineKeyboardMarkup(rows)

def kb_berths(prefix):
    rows = [[
        InlineKeyboardButton(f"{BERTH_EMOJI[b]}  {b}", callback_data=f"{prefix}_{b}")
    ] for b in BERTHS]
    rows.append([InlineKeyboardButton("⬅️  Back", callback_data=f"{prefix}_back")])
    return InlineKeyboardMarkup(rows)

def kb_confirm(swap_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  Confirm Swap Done", callback_data=f"confirm_{swap_id}")],
        [InlineKeyboardButton("🏠  Main Menu",          callback_data="flow_home")],
    ])

# ═══════════════════════════════════════════════
#   STATE MACHINE — user_data keys:
#   "flow"  : current flow name
#   "ps"    : postseat collected data dict
# ═══════════════════════════════════════════════
def set_flow(ctx, name, extra=None):
    ctx.user_data["flow"] = name
    if extra: ctx.user_data.update(extra)

def clear_flow(ctx):
    ctx.user_data.pop("flow", None)
    ctx.user_data.pop("ps", None)
    ctx.user_data.pop("search_train", None)

# ═══════════════════════════════════════════════
#   REPLY HELPER  (works for both msg & callback)
# ═══════════════════════════════════════════════
async def rply(update: Update, text: str, kb=None):
    kw = dict(text=text, reply_markup=kb, parse_mode="Markdown")
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(**kw)
        except Exception:
            await update.callback_query.message.reply_text(**kw)
    else:
        await update.message.reply_text(**kw)

# ═══════════════════════════════════════════════
#   /START  — MAIN MENU
# ═══════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)
    clear_flow(context)
    if is_banned(user.id):
        await rply(update, "🚫 Your account has been suspended. Contact support.")
        return
    db_icon = "🟢" if FIREBASE_ON else "🔴"
    await rply(update,
        f"🚆 *SeatSwap*\n\n"
        f"Hey *{user.first_name}!* 👋\n"
        f"Exchange your train berth with fellow passengers — instantly.\n\n"
        f"🔄 Post your swap request\n"
        f"🔍 Find swaps by train & coach\n"
        f"🤝 Get auto-matched & earn badges\n\n"
        f"_{db_icon} Database {'Online' if FIREBASE_ON else 'Offline'}_",
        kb_main()
    )

# ═══════════════════════════════════════════════
#   POST SWAP FLOW
# ═══════════════════════════════════════════════
async def ps_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        await rply(update, "🚫 You are banned."); return
    set_flow(context, "ps_train", {"ps": {}})
    await rply(update,
        "📝 *Post Seat Swap*\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Step 1️⃣ of 4️⃣\n\n"
        "Enter your *Train Number* 🚆\n\n"
        "_(Example: `12301`, `12951`)_\n\n"
        "_Tip: You can search by name too — just type it!_",
        InlineKeyboardMarkup([[InlineKeyboardButton("🏠  Cancel", callback_data="flow_home")]])
    )

async def ps_got_train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw   = update.message.text.strip()
    # look up in popular trains
    train_name = POPULAR_TRAINS.get(raw, "")
    if not train_name:
        # try partial name match
        raw_up = raw.upper()
        for num, name in POPULAR_TRAINS.items():
            if raw_up in name.upper() or raw_up in num:
                train_name = name; raw = num; break
    context.user_data["ps"]["train"]      = raw.upper()
    context.user_data["ps"]["train_name"] = train_name or raw.upper()
    set_flow(context, "ps_coach_type")

    name_line = f"\n🔖 _{train_name}_" if train_name else ""
    await update.message.reply_text(
        f"✅ Train: *{raw.upper()}*{name_line}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Step 2️⃣ of 4️⃣\n\n"
        f"Select your *Coach Type* 🚉",
        reply_markup=kb_coach_types(),
        parse_mode="Markdown"
    )

async def ps_got_coach_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.callback_query.data.replace("ct_","")
    await update.callback_query.answer()
    if code not in COACH_TYPES:
        await update.callback_query.answer("Invalid selection", show_alert=True); return
    info = COACH_TYPES[code]
    context.user_data["ps"]["coach_type"]       = code
    context.user_data["ps"]["coach_type_label"] = info["label"]
    set_flow(context, "ps_coach")
    await update.callback_query.edit_message_text(
        f"✅ Coach Type: *{info['label']}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Step 2️⃣ of 4️⃣ (cont.)\n\n"
        f"Select your *Coach* 🚉",
        reply_markup=kb_coaches(info["coaches"]),
        parse_mode="Markdown"
    )

async def ps_got_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coach = update.callback_query.data.replace("cn_","")
    await update.callback_query.answer()
    context.user_data["ps"]["coach"] = coach
    set_flow(context, "ps_current")
    await update.callback_query.edit_message_text(
        f"✅ Coach: *{coach}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Step 3️⃣ of 4️⃣\n\n"
        f"Select your *Current Berth* 💺",
        reply_markup=kb_berths("cur"),
        parse_mode="Markdown"
    )

async def ps_got_current(update: Update, context: ContextTypes.DEFAULT_TYPE):
    berth = update.callback_query.data.replace("cur_","")
    await update.callback_query.answer()
    context.user_data["ps"]["current"] = berth
    set_flow(context, "ps_wanted")
    await update.callback_query.edit_message_text(
        f"✅ Current Berth: *{berth}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Step 4️⃣ of 4️⃣\n\n"
        f"Which berth do you *want*? 🔄",
        reply_markup=kb_berths("want"),
        parse_mode="Markdown"
    )

async def ps_got_wanted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    berth = update.callback_query.data.replace("want_","")
    await update.callback_query.answer()
    user  = update.effective_user
    ps    = context.user_data.get("ps",{})
    ps["wanted"] = berth

    swap  = save_swap(
        user,
        ps["train"], ps["train_name"],
        ps["coach_type"], ps["coach"],
        ps["current"], ps["wanted"],
    )
    clear_flow(context)

    # summary card
    name_line = f"\n🔖 _{ps['train_name']}_" if ps.get("train_name") and ps["train_name"] != ps["train"] else ""
    summary = (
        f"✅ *Swap Posted Successfully!*\n\n"
        f"🚆 Train: *{ps['train']}*{name_line}\n"
        f"🚉 Coach: *{ps['coach']}*  ({ps['coach_type_label']})\n"
        f"💺 Has:   *{ps['current']}*\n"
        f"🔄 Wants: *{ps['wanted']}*\n\n"
    )

    match = find_match(swap)
    if match:
        u_m     = get_user(match["user_id"])
        contact = contact_link(match)
        summary += (
            f"🎉 *INSTANT MATCH FOUND!*\n\n"
            f"👤 *{match['name']}*  {u_m.get('badge','')}\n"
            f"🚉 Coach: *{match['coach']}*\n"
            f"💺 Has:   *{match['current']}*\n"
            f"🔄 Wants: *{match['wanted']}*\n\n"
            f"📩 Contact: {contact}\n\n"
            f"_Message them to confirm the swap!_\n"
            f"_Tap ✅ Confirm after swap to earn +10 pts!_"
        )
        try:
            u_me = get_user(user.id)
            await context.bot.send_message(
                chat_id=match["user_id"],
                text=(
                    f"🎉 *MATCH FOUND!*\n\n"
                    f"Train *{ps['train']}* — Someone wants to swap!\n\n"
                    f"👤 *{user.first_name}*  {u_me.get('badge','')}\n"
                    f"🚉 Coach: *{ps['coach']}*\n"
                    f"💺 Has:   *{ps['current']}*\n"
                    f"🔄 Wants: *{ps['wanted']}*\n\n"
                    f"📩 Contact: {contact_link({'username':user.username,'name':user.first_name,'user_id':user.id})}\n\n"
                    f"_Tap ✅ Confirm after swap to earn +10 pts!_"
                ),
                reply_markup=kb_confirm(match["swap_id"]),
                parse_mode="Markdown"
            )
        except Exception: pass
        kb = kb_confirm(swap["swap_id"])
    else:
        summary += "🔔 Your request is *live*!\nWe'll notify you instantly when a match is found."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍  Browse Swaps", callback_data="flow_search")],
            [InlineKeyboardButton("🏠  Main Menu",    callback_data="flow_home")],
        ])

    await update.callback_query.edit_message_text(summary, reply_markup=kb, parse_mode="Markdown")

# ═══════════════════════════════════════════════
#   FIND SWAP FLOW  (train → coach buttons)
# ═══════════════════════════════════════════════
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_flow(context, "search_train")
    await rply(update,
        "🔍 *Find Seat Swaps*\n\n"
        "Enter *Train Number* to search:\n\n"
        "_(Example: `12301`)_",
        InlineKeyboardMarkup([[InlineKeyboardButton("🏠  Cancel", callback_data="flow_home")]])
    )

async def search_got_train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw   = update.message.text.strip().upper()
    context.user_data["search_train"] = raw
    clear_flow(context)
    all_swaps = get_all_swaps()
    results   = {k:v for k,v in all_swaps.items()
                 if v.get("train") == raw and v.get("status") == "active"}

    if not results:
        train_name = POPULAR_TRAINS.get(raw, "")
        name_line  = f"\n🔖 _{train_name}_" if train_name else ""
        await update.message.reply_text(
            f"😔 No active swaps for *Train {raw}*{name_line}\n\n"
            f"Be the first to post one!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄  Post Swap", callback_data="flow_postseat")],
                [InlineKeyboardButton("🏠  Main Menu", callback_data="flow_home")],
            ]),
            parse_mode="Markdown"
        )
        return

    # group by coach
    coaches = {}
    for k,v in results.items():
        c = v.get("coach","?")
        coaches.setdefault(c, []).append(v)

    train_name = results[list(results.keys())[0]].get("train_name", raw)
    text = (
        f"🚆 *Train {raw}*\n"
        f"🔖 _{train_name}_\n"
        f"Found *{len(results)} swap(s)* in *{len(coaches)} coach(es)*\n\n"
        f"Select a coach 👇"
    )
    rows = []
    for c, vs in sorted(coaches.items()):
        rows.append([InlineKeyboardButton(
            f"🚉  {c}  —  {len(vs)} swap(s)",
            callback_data=f"viewcoach_{raw}_{c}"
        )])
    rows.append([InlineKeyboardButton("🏠  Main Menu", callback_data="flow_home")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")

async def show_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    _, train, coach = update.callback_query.data.split("_", 2)
    all_swaps = get_all_swaps()
    results   = sorted(
        [v for v in all_swaps.values()
         if v.get("train")==train and v.get("coach")==coach and v.get("status")=="active"],
        key=lambda x: -int(get_user(x["user_id"]).get("swaps_done",0))
    )
    if not results:
        await update.callback_query.edit_message_text(
            "No swaps for this coach.", reply_markup=kb_home())
        return

    text = f"🚉 *{train} — Coach {coach}*\n{len(results)} swap(s)\n\n"
    rows = []
    for i, req in enumerate(results, 1):
        u    = get_user(req["user_id"])
        sd   = u.get("swaps_done",0)
        ago  = time_ago(req.get("timestamp",""))
        text += (
            f"*#{i}  {req['name']}*  {req.get('badge','🌱 Newcomer')}\n"
            f"💺 Has: *{req['current']}*  →  🔄 Wants: *{req['wanted']}*\n"
            f"✅ {sd} swaps done  ·  🕐 {ago}\n"
            f"──────────────────\n"
        )
        rows.append([
            InlineKeyboardButton(f"📩  Contact #{i}", url=f"tg://user?id={req['user_id']}"),
            InlineKeyboardButton(f"🚩  Report #{i}",  callback_data=f"report_{req['user_id']}"),
        ])
    rows.append([InlineKeyboardButton("🏠  Main Menu", callback_data="flow_home")])
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")

# ═══════════════════════════════════════════════
#   CONFIRM SWAP
# ═══════════════════════════════════════════════
async def confirm_swap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    uid     = update.effective_user.id
    swap_id = update.callback_query.data.replace("confirm_","")
    key     = f"confirmed/{uid}_{swap_id}"

    if fb_get(key):
        await update.callback_query.edit_message_text(
            "✅ You already confirmed this swap!", reply_markup=kb_home())
        return

    fb_set(key, True)
    sd, pts = award(uid)
    u       = get_user(uid)
    bar, _  = progress_bar(sd)

    await update.callback_query.edit_message_text(
        f"🎉 *Swap Confirmed!*\n\n"
        f"✅ +10 points earned!\n"
        f"⭐ Total points: *{pts}*\n"
        f"🏅 Badge: *{get_badge(sd)}*\n\n"
        f"📈 *Next Badge:*\n{bar}",
        reply_markup=kb_home(), parse_mode="Markdown"
    )

# ═══════════════════════════════════════════════
#   REPORT USER
# ═══════════════════════════════════════════════
async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reporter = update.effective_user.id
    reported = int(update.callback_query.data.replace("report_",""))
    if reporter == reported:
        await update.callback_query.answer("❌ Can't report yourself!", show_alert=True); return
    key = f"reports/{reporter}_{reported}"
    if fb_get(key):
        await update.callback_query.answer("Already reported.", show_alert=True); return
    fb_set(key, True)
    u     = get_user(reported)
    count = u.get("reports",0)+1
    fb_upd(f"users/{reported}", {"reports": count})
    if count >= 3:
        fb_upd(f"users/{reported}", {"banned": True})
        delete_my_swap(reported)
        try:
            await context.bot.send_message(
                chat_id=reported,
                text="🚫 Your SeatSwap account has been suspended due to multiple reports."
            )
        except: pass
        await update.callback_query.answer("⚠️ User banned after 3 reports.", show_alert=True)
    else:
        await update.callback_query.answer(f"Reported ({count}/3)", show_alert=True)

# ═══════════════════════════════════════════════
#   MY REQUEST
# ═══════════════════════════════════════════════
async def my_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    req = user_swap(uid)
    if not req:
        await rply(update,
            "📋 You have no active swap request.\n\nPost one now!",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄  Post Swap", callback_data="flow_postseat")],
                [InlineKeyboardButton("🏠  Main Menu", callback_data="flow_home")],
            ])
        ); return
    name_line = f"\n🔖 _{req.get('train_name','')}_ " if req.get("train_name") and req["train_name"] != req["train"] else ""
    await rply(update,
        f"📋 *Your Active Request*\n\n"
        f"🚆 Train: *{req['train']}*{name_line}\n"
        f"🚉 Coach: *{req['coach']}*\n"
        f"💺 Has:   *{req['current']}*\n"
        f"🔄 Wants: *{req['wanted']}*\n"
        f"🕐 Posted: {time_ago(req.get('timestamp',''))}",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("❌  Delete Request", callback_data="cancelswap")],
            [InlineKeyboardButton("🏠  Main Menu",      callback_data="flow_home")],
        ])
    )

# ═══════════════════════════════════════════════
#   PROFILE
# ═══════════════════════════════════════════════
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user  = update.effective_user
    u     = get_user(user.id)
    sd    = u.get("swaps_done",0)
    bar,_ = progress_bar(sd)
    await rply(update,
        f"👤 *Your Profile*\n\n"
        f"Name:    *{user.first_name}*\n"
        f"Badge:   {get_badge(sd)}\n"
        f"✅ Swaps Done: *{sd}*\n"
        f"⭐ Points:     *{u.get('points',0)}*\n\n"
        f"📈 *Progress:*\n{bar}",
        kb_home()
    )

# ═══════════════════════════════════════════════
#   STATS  (public — total swaps, users)
# ═══════════════════════════════════════════════
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users  = fb_get("users") or {}
    swaps  = get_all_swaps()
    active = sum(1 for s in swaps.values() if s.get("status")=="active")
    db_ico = "🟢" if FIREBASE_ON else "🔴"
    await rply(update,
        f"📊 *SeatSwap Stats*\n\n"
        f"{db_ico} Database: {'Online' if FIREBASE_ON else 'Offline'}\n"
        f"👥 Total Users:   *{len(users)}*\n"
        f"🔄 Active Swaps:  *{active}*\n"
        f"✅ Total Swapped: *{sum(u.get('swaps_done',0) for u in users.values())}*",
        kb_home()
    )

# ═══════════════════════════════════════════════
#   HELP
# ═══════════════════════════════════════════════
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await rply(update,
        "❓ *How to use SeatSwap*\n\n"
        "1️⃣  Tap *Post Swap*\n"
        "     Enter train no → pick coach type → pick coach → pick your berth → pick wanted berth\n\n"
        "2️⃣  Tap *Find Swap*\n"
        "     Enter train no → pick coach → see swaps\n\n"
        "3️⃣  Contact the person via 📩 button\n\n"
        "4️⃣  After swapping → tap *✅ Confirm Swap Done* → earn *+10 pts!*\n\n"
        "🚩 *Report* fake users — 3 reports = auto ban\n\n"
        "🏅 *Badges:*\n"
        "🌱 Newcomer         (0 swaps)\n"
        "🎫 Regular Traveler  (3+ swaps)\n"
        "⭐ Trusted Member   (10+ swaps)\n"
        "🔰 Expert Swapper   (25+ swaps)\n"
        "👑 Seat Master       (50+ swaps)\n\n"
        "_Higher badge = more people trust you!_",
        kb_home()
    )

# ═══════════════════════════════════════════════
#   CANCEL SWAP
# ═══════════════════════════════════════════════
async def cancel_swap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    clear_flow(context)
    deleted = delete_my_swap(uid)
    text = "✅ Your swap request has been removed." if deleted else "You have no active request."
    await rply(update, text, kb_home())

# ═══════════════════════════════════════════════
#   ADMIN COMMANDS
# ═══════════════════════════════════════════════
def is_admin(uid): return uid in ADMIN_IDS

async def admin_checkdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not FIREBASE_ON:
        await update.message.reply_text(
            "❌ *Firebase NOT connected!*\n\n"
            "Fix:\n1. Go to Railway → Variables\n"
            "2. Add `FIREBASE_KEY` with your Firebase JSON\n"
            "3. Redeploy",
            parse_mode="Markdown"
        ); return
    try:
        db.reference("bot_status").update({"ping": datetime.now().strftime("%d %b %Y %I:%M %p")})
        r = db.reference("bot_status").get()
        await update.message.reply_text(
            f"✅ *Firebase Working!*\n\n"
            f"🕐 Last ping: `{r.get('ping','?')}`\n"
            f"🚀 Boot time: `{r.get('boot_time','?')}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Firebase error:\n`{e}`", parse_mode="Markdown")

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>"); return
    uid = int(context.args[0])
    fb_upd(f"users/{uid}", {"banned": True})
    delete_my_swap(uid)
    await update.message.reply_text(f"🚫 User {uid} banned.")

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>"); return
    uid = int(context.args[0])
    fb_upd(f"users/{uid}", {"banned": False, "reports": 0})
    await update.message.reply_text(f"✅ User {uid} unbanned.")

async def admin_allstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    users  = fb_get("users") or {}
    swaps  = get_all_swaps()
    active = sum(1 for s in swaps.values() if s.get("status")=="active")
    banned = sum(1 for u in users.values() if u.get("banned"))
    await update.message.reply_text(
        f"📊 *Admin Stats*\n\n"
        f"🗄 Firebase: {'✅ On' if FIREBASE_ON else '❌ Off'}\n"
        f"👥 Users: {len(users)}\n"
        f"🔄 Active Swaps: {active}\n"
        f"✅ Total Swaps Done: {sum(u.get('swaps_done',0) for u in users.values())}\n"
        f"🚫 Banned: {banned}",
        parse_mode="Markdown"
    )

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    msg   = " ".join(context.args) if context.args else ""
    if not msg:
        await update.message.reply_text("Usage: /broadcast <message>"); return
    users = fb_get("users") or {}
    sent  = 0
    for uid in users:
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"📢 *SeatSwap Announcement*\n\n{msg}",
                parse_mode="Markdown"
            )
            sent += 1
        except: pass
    await update.message.reply_text(f"✅ Sent to {sent}/{len(users)} users.")

# ═══════════════════════════════════════════════
#   MESSAGE HANDLER  (state machine router)
# ═══════════════════════════════════════════════
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    flow = context.user_data.get("flow","")

    if   flow == "ps_train":      await ps_got_train(update, context)
    elif flow == "search_train":  await search_got_train(update, context)
    else:
        # Unknown input — show helpful menu
        await rply(update,
            "👇 Use the buttons below to navigate SeatSwap:",
            kb_main()
        )

# ═══════════════════════════════════════════════
#   CALLBACK ROUTER
# ═══════════════════════════════════════════════
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = update.callback_query.data
    flow = context.user_data.get("flow","")

    # ── MENU ROUTES ──
    if   data == "flow_home":       await start(update, context)
    elif data == "flow_postseat":   await ps_start(update, context)
    elif data == "flow_search":     await search_start(update, context)
    elif data == "flow_myrequest":  await my_request(update, context)
    elif data == "flow_profile":    await profile(update, context)
    elif data == "flow_help":       await help_cmd(update, context)
    elif data == "flow_stats":      await stats(update, context)
    elif data == "cancelswap":      await cancel_swap(update, context)

    # ── POST SWAP STEPS ──
    elif data.startswith("ct_"):    await ps_got_coach_type(update, context)
    elif data.startswith("cn_"):    await ps_got_coach(update, context)
    elif data.startswith("cur_"):
        if data == "cur_back":
            # go back to coach type
            await ps_start(update, context)
        else:
            await ps_got_current(update, context)
    elif data.startswith("want_"):
        if data == "want_back":
            ps = context.user_data.get("ps",{})
            coach = ps.get("coach","")
            await update.callback_query.edit_message_text(
                f"Select your *Current Berth* 💺",
                reply_markup=kb_berths("cur"), parse_mode="Markdown")
            set_flow(context,"ps_current")
        else:
            await ps_got_wanted(update, context)
    elif data == "ps_back_coachtype":
        await ps_start(update, context)

    # ── VIEW COACH ──
    elif data.startswith("viewcoach_"):  await show_coach(update, context)

    # ── CONFIRM / REPORT ──
    elif data.startswith("confirm_"):    await confirm_swap(update, context)
    elif data.startswith("report_"):     await report_user(update, context)

    else:
        await update.callback_query.edit_message_text(
            "Something went wrong. Please try again.",
            reply_markup=kb_main()
        )

# ═══════════════════════════════════════════════
#   ERROR HANDLER  (self-healing)
# ═══════════════════════════════════════════════
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = str(context.error)
    print(f"❌ Error: {err}")
    try:
        if isinstance(update, Update):
            if update.callback_query:
                await update.callback_query.answer("⚠️ Something went wrong. Returning to menu.", show_alert=True)
                await update.callback_query.edit_message_text(
                    "⚠️ An error occurred. Returning to main menu.",
                    reply_markup=kb_main()
                )
            elif update.message:
                await update.message.reply_text(
                    "⚠️ Something went wrong. Tap below to continue.",
                    reply_markup=kb_main()
                )
    except Exception: pass

# ═══════════════════════════════════════════════
#   APP SETUP
# ═══════════════════════════════════════════════
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Message handler (state machine)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Buttons
app.add_handler(CallbackQueryHandler(button_handler))

# Commands
app.add_handler(CommandHandler("start",     start))
app.add_handler(CommandHandler("cancel",    cancel_swap))
app.add_handler(CommandHandler("checkdb",   admin_checkdb))
app.add_handler(CommandHandler("ban",       admin_ban))
app.add_handler(CommandHandler("unban",     admin_unban))
app.add_handler(CommandHandler("stats",     admin_allstats))
app.add_handler(CommandHandler("broadcast", admin_broadcast))

# Error handler
app.add_error_handler(error_handler)

print("🚆 SeatSwap Bot started!")
app.run_polling(allowed_updates=Update.ALL_TYPES)
