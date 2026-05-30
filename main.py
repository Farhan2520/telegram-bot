import os, json, uuid, re
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, BotCommand, MenuButtonCommands,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, CallbackQueryHandler, filters,
)
import firebase_admin
from firebase_admin import credentials, db

# ═══════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════
BOT_TOKEN     = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_IDS     = [int(x) for x in os.getenv("ADMIN_IDS","0").split(",") if x.strip().isdigit()]
ADMIN_UNAMES  = [x.strip().lower().lstrip("@") for x in os.getenv("ADMIN_USERNAMES","").split(",") if x.strip()]

# ═══════════════════════════════════════════════════════
#  FIREBASE
# ═══════════════════════════════════════════════════════
FIREBASE_ON = False
try:
    raw = os.getenv("FIREBASE_KEY")
    if raw:
        cred = credentials.Certificate(json.loads(raw))
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://seatswap-a96ec-default-rtdb.firebaseio.com/"
        })
        db.reference("bot_status").set({
            "online": True,
            "boot": datetime.now().strftime("%d %b %Y %I:%M %p"),
        })
        FIREBASE_ON = True
        print("✅ Firebase connected!")
    else:
        print("⚠️  FIREBASE_KEY missing")
except Exception as e:
    print(f"❌ Firebase error: {e}")

# ═══════════════════════════════════════════════════════
#  TRAIN DATABASE
# ═══════════════════════════════════════════════════════
TRAINS = {
    "12301":"Howrah Rajdhani Express","12302":"New Delhi Rajdhani Express",
    "12303":"Poorva Express","12304":"Poorva Express",
    "12305":"Howrah Rajdhani (via Patna)","12306":"Howrah Rajdhani (via Patna)",
    "12309":"Rajendra Nagar Rajdhani","12310":"Rajendra Nagar Rajdhani",
    "12313":"Sealdah Rajdhani Express","12314":"Sealdah Rajdhani Express",
    "12315":"Annanya Express","12316":"Annanya Express",
    "12321":"Howrah Mumbai Mail","12322":"Mumbai Howrah Mail",
    "12339":"Howrah Patna Express","12340":"Patna Howrah Express",
    "12343":"Darjeeling Mail","12344":"Darjeeling Mail",
    "12345":"Saraighat Express","12346":"Saraighat Express",
    "12381":"Poorabh Express","12382":"Poorabh Express",
    "12423":"Dibrugarh Rajdhani","12424":"Dibrugarh Rajdhani",
    "12431":"Trivandrum Rajdhani","12432":"Trivandrum Rajdhani",
    "12433":"NZM Rajdhani Express","12434":"NZM Rajdhani Express",
    "12505":"Northeast Express","12506":"Northeast Express",
    "12507":"Trivandrum Express","12508":"Trivandrum Express",
    "12557":"Sapt Kranti Express","12558":"Sapt Kranti Express",
    "12559":"Shiv Ganga Express","12560":"Shiv Ganga Express",
    "12601":"Mangalore Express","12602":"Mangalore Express",
    "12615":"Grand Trunk Express","12616":"Grand Trunk Express",
    "12621":"Tamil Nadu Express","12622":"Tamil Nadu Express",
    "12627":"Karnataka Express","12628":"Karnataka Express",
    "12657":"Chennai Mail","12658":"Chennai Mail",
    "12801":"Purushottam Express","12802":"Purushottam Express",
    "12875":"Neelachal Express","12876":"Neelachal Express",
    "12951":"Mumbai Rajdhani Express","12952":"New Delhi Rajdhani Express",
    "12953":"August Kranti Rajdhani","12954":"August Kranti Rajdhani",
    "13005":"Howrah Amritsar Express","13006":"Amritsar Howrah Express",
    "13009":"Doon Express","13010":"Doon Express",
    "13025":"Howrah Bandra Express","13026":"Bandra Howrah Express",
    "13049":"Amritsar Express","13050":"Amritsar Express",
    "13065":"Howrah Anand Vihar Amrit Bharat","13066":"Howrah Anand Vihar Amrit Bharat",
    "13151":"Kolkata Jammu Tawi Express","13152":"Jammu Kolkata Express",
    "14021":"Anand Vihar Purulia Express","14022":"Purulia Anand Vihar Express",
    "14033":"Jammu Mail","14034":"Jammu Mail",
    "14055":"Brahmaputra Mail","14056":"Brahmaputra Mail",
    "15631":"Barmer Guwahati Express","15632":"Guwahati Barmer Express",
    "15671":"Kamakhya Rohtak Amrit Bharat","15672":"Kamakhya Rohtak Amrit Bharat",
    "15949":"Dibrugarh Gomtinagar Amrit Bharat","15950":"Dibrugarh Gomtinagar Amrit Bharat",
    "16107":"Tambaram Santragachi Amrit Bharat","16108":"Tambaram Santragachi Amrit Bharat",
    "16121":"Tambaram Trivandrum Amrit Bharat","16122":"Tambaram Trivandrum Amrit Bharat",
    "16315":"Kochuveli Amrit Bharat","16316":"Kochuveli Amrit Bharat",
    "16329":"Nagercoil Mangaluru Amrit Bharat","16330":"Nagercoil Mangaluru Amrit Bharat",
    "16357":"Nagercoil Charlapalli Amrit Bharat","16358":"Nagercoil Charlapalli Amrit Bharat",
    "17041":"Charlapalli Trivandrum Amrit Bharat","17042":"Charlapalli Trivandrum Amrit Bharat",
    "18063":"Santragachi Yelahanka Express","18064":"Santragachi Yelahanka Express",
    "18261":"Bilaspur Yelahanka Express","18262":"Bilaspur Yelahanka Express",
    "20503":"Agartala Rajdhani","20504":"Agartala Rajdhani",
    "20609":"NJP Tiruchchirappalli Amrit Bharat","20610":"NJP Tiruchchirappalli Amrit Bharat",
    "20901":"Mumbai Ahmedabad Vande Bharat","20902":"Ahmedabad Mumbai Vande Bharat",
    "22691":"Rajdhani Express","22692":"Rajdhani Express",
    "22691":"Rajdhani Express","22692":"Rajdhani Express",
    "22823":"Bhubaneswar Rajdhani","22824":"Bhubaneswar Rajdhani",
    "22347":"Howrah Patna Vande Bharat","22348":"Howrah Patna Vande Bharat",
    "22435":"Varanasi Vande Bharat","22436":"Varanasi Vande Bharat",
    "22589":"Banaras Hadapsar Amrit Bharat","22590":"Banaras Hadapsar Amrit Bharat",
    "12001":"Bhopal Shatabdi","12002":"Bhopal Shatabdi",
    "12017":"Howrah Shatabdi","12018":"Howrah Shatabdi",
    "12041":"NJP Shatabdi","12042":"NJP Shatabdi",
    "12259":"Sealdah Duronto","12260":"Sealdah Duronto",
    "12213":"Yesvantpur Duronto","12214":"Yesvantpur Duronto",
    "11061":"LTT Jabalpur Express","11062":"Jabalpur LTT Express",
    "11071":"Kamayani Express","11072":"Kamayani Express",
    "11077":"Jhelum Express","11078":"Jhelum Express",
}

# ═══════════════════════════════════════════════════════
#  COACH & SEAT SYSTEM
# ═══════════════════════════════════════════════════════
COACH_TYPES = {
    "SL": {"label":"🛏 Sleeper (S1–S12)",    "max_seat":72,  "coaches":[f"S{i}" for i in range(1,13)]},
    "3A": {"label":"❄️ AC 3 Tier (B1–B6)",   "max_seat":64,  "coaches":[f"B{i}" for i in range(1,7)]},
    "2A": {"label":"❄️ AC 2 Tier (A1–A4)",   "max_seat":46,  "coaches":[f"A{i}" for i in range(1,5)]},
    "1A": {"label":"❄️ First Class (H1–H2)", "max_seat":24,  "coaches":["H1","H2"]},
    "CC": {"label":"💺 Chair Car (C1–C8)",    "max_seat":78,  "coaches":[f"C{i}" for i in range(1,9)]},
    "EC": {"label":"💺 Exec Chair (EC1–EC3)","max_seat":56,  "coaches":["EC1","EC2","EC3"]},
    "GN": {"label":"🚃 General (GS)",         "max_seat":200, "coaches":["GS1","GS2","GS3"]},
}

BERTHS_BY_CT = {
    "SL": ["Lower","Middle","Upper","Side Lower","Side Upper"],
    "3A": ["Lower","Middle","Upper","Side Lower","Side Upper"],
    "2A": ["Lower","Upper"],
    "1A": ["Lower","Upper"],
    "CC": ["Window","Middle","Aisle"],
    "EC": ["Window","Middle","Aisle"],
    "GN": ["Any"],
}
BERTH_EMOJI = {
    "Lower":"⬇️","Middle":"➡️","Upper":"⬆️",
    "Side Lower":"↘️","Side Upper":"↗️",
    "Window":"🪟","Aisle":"🚶","Any":"🔀",
}

def auto_berth(seat_num, ct):
    try:
        s = int(seat_num)
    except:
        return "Any"
    if ct in ["SL","3A"]:
        pos = (s - 1) % 8
        return ["Lower","Middle","Upper","Lower","Middle","Upper","Side Lower","Side Upper"][pos]
    elif ct == "2A":
        return "Lower" if (s - 1) % 4 in [0,2] else "Upper"
    elif ct in ["1A"]:
        return "Lower" if s % 2 == 1 else "Upper"
    elif ct in ["CC","EC"]:
        return ["Window","Middle","Aisle"][(s - 1) % 3]
    return "Any"

# ═══════════════════════════════════════════════════════
#  BADGE SYSTEM
# ═══════════════════════════════════════════════════════
BADGES = [
    (0,  "🌱", "Newcomer"),
    (3,  "🎫", "Regular Traveler"),
    (10, "⭐", "Trusted Member"),
    (25, "🔰", "Expert Swapper"),
    (50, "👑", "Seat Master"),
]
SPECIAL_BADGES = {
    "Master":  "👑 Master",
    "VIP":     "⭐ VIP",
    "Trusted": "🛡 Trusted",
    "Premium": "💎 Premium",
    "Family":  "👨‍👩‍👧‍👦 Family",
    "Official":"✅ Official",
}

def get_badge(uid=None, swaps=0):
    if uid:
        u = fb_get(f"users/{uid}") or {}
        if u.get("special_badge"):
            return u["special_badge"]
        if u.get("special_user"):
            return "🌟 Official SeatSwap Family"
        swaps = u.get("swaps_done", 0)
    b = BADGES[0]
    for lvl in BADGES:
        if swaps >= lvl[0]: b = lvl
    return f"{b[0]} {b[2]}"

def progress_bar(swaps):
    cur = BADGES[0]; nxt = None
    for i, lvl in enumerate(BADGES):
        if swaps >= lvl[0]:
            cur = lvl
            nxt = BADGES[i+1] if i+1 < len(BADGES) else None
    if not nxt:
        return "👑 *Maximum badge reached!*"
    done = swaps - cur[0]; need = nxt[0] - cur[0]
    f = int((done / need) * 10)
    return f"`[{'█'*f}{'░'*(10-f)}]` {done}/{need}  _{nxt[0]-swaps} more → {nxt[0]} {nxt[2]}_"

# ═══════════════════════════════════════════════════════
#  TRANSLATIONS
# ═══════════════════════════════════════════════════════
LANG_MENU = {
    "en": {
        "change_seat":"🔄 Change Seat", "find_seat":"🔍 Find Seat",
        "my_req":"📋 My Request",       "profile":"👤 Profile",
        "language":"🌐 Language",       "help":"❓ Help",
        "feedback":"💬 Feedback",
    },
    "hi": {
        "change_seat":"🔄 सीट बदलें", "find_seat":"🔍 सीट खोजें",
        "my_req":"📋 मेरा अनुरोध",    "profile":"👤 प्रोफ़ाइल",
        "language":"🌐 भाषा",          "help":"❓ मदद",
        "feedback":"💬 फ़ीडबैक",
    },
    "bn": {
        "change_seat":"🔄 সিট বদলান", "find_seat":"🔍 সিট খুঁজুন",
        "my_req":"📋 আমার অনুরোধ",   "profile":"👤 প্রোফাইল",
        "language":"🌐 ভাষা",          "help":"❓ সাহায্য",
        "feedback":"💬 ফিডব্যাক",
    },
    "ur": {
        "change_seat":"🔄 سیٹ بدلیں", "find_seat":"🔍 سیٹ تلاش کریں",
        "my_req":"📋 میری درخواست",   "profile":"👤 پروفائل",
        "language":"🌐 زبان",          "help":"❓ مدد",
        "feedback":"💬 فیڈبیک",
    },
}

STRINGS = {
    "welcome": {
        "en": "🚆 *SeatSwap*\n\nHey *{name}*! 👋\nExchange your train berth with fellow passengers — instantly!\n\n✅ Post your swap • 🔍 Find swaps\n🤝 Get matched • 🏅 Earn badges",
        "hi": "🚆 *SeatSwap*\n\nनमस्ते *{name}*! 👋\nट्रेन की सीट तुरंत बदलें!\n\n✅ सीट पोस्ट करें • 🔍 खोजें\n🤝 मैच पाएं • 🏅 बैज कमाएं",
        "bn": "🚆 *SeatSwap*\n\nনমস্কার *{name}*! 👋\nট্রেনের বার্থ এখনই বদলান!\n\n✅ পোস্ট করুন • 🔍 খুঁজুন\n🤝 ম্যাচ পান • 🏅 ব্যাজ অর্জন",
        "ur": "🚆 *SeatSwap*\n\nہیلو *{name}*! 👋\nٹرین کی سیٹ فوری بدلیں!\n\n✅ پوسٹ کریں • 🔍 تلاش کریں\n🤝 میچ پائیں • 🏅 بیج کمائیں",
    },
    "step_train": {
        "en": "📝 *Step 1/5 — Train Number*\n\nEnter your train number:\n_(e.g. `12301`, `12951`)_",
        "hi": "📝 *चरण 1/5 — ट्रेन नंबर*\n\nट्रेन नंबर डालें:\n_(जैसे: `12301`, `12951`)_",
        "bn": "📝 *ধাপ 1/5 — ট্রেন নম্বর*\n\nট্রেন নম্বর লিখুন:\n_(যেমন: `12301`, `12951`)_",
        "ur": "📝 *مرحلہ 1/5 — ٹرین نمبر*\n\nاپنا ٹرین نمبر درج کریں:\n_(مثال: `12301`, `12951`)_",
    },
    "step_coach_type": {
        "en": "✅ Train: *{num}* — _{name}_\n\n📝 *Step 2/5*\nSelect your *Coach Type*:",
        "hi": "✅ ट्रेन: *{num}* — _{name}_\n\n📝 *चरण 2/5*\n*बोगी प्रकार* चुनें:",
        "bn": "✅ ট্রেন: *{num}* — _{name}_\n\n📝 *ধাপ 2/5*\n*কোচের ধরন* বেছে নিন:",
        "ur": "✅ ٹرین: *{num}* — _{name}_\n\n📝 *مرحلہ 2/5*\nاپنی *بوگی کی قسم* منتخب کریں:",
    },
    "step_coach": {
        "en": "📝 *Step 2/5 (cont.)* — Select *Coach*:",
        "hi": "📝 *चरण 2/5 (जारी)* — *बोगी* चुनें:",
        "bn": "📝 *ধাপ 2/5 (চলমান)* — *কোচ* বেছে নিন:",
        "ur": "📝 *مرحلہ 2/5 (جاری)* — *بوگی* منتخب کریں:",
    },
    "step_cur_seat": {
        "en": "📝 *Step 3/5 — Your Current Seat*\n\nEnter your *seat number*:\n_(For {ct}: 1 to {max})_\n\n_Berth type will be detected automatically!_",
        "hi": "📝 *चरण 3/5 — आपकी वर्तमान सीट*\n\n*सीट नंबर* डालें:\n_({ct} के लिए: 1 से {max})_\n\n_बर्थ प्रकार अपने आप पता चलेगा!_",
        "bn": "📝 *ধাপ 3/5 — আপনার বর্তমান সিট*\n\n*সিট নম্বর* লিখুন:\n_({ct} এর জন্য: 1 থেকে {max})_\n\n_বার্থ স্বয়ংক্রিয়ভাবে শনাক্ত হবে!_",
        "ur": "📝 *مرحلہ 3/5 — آپ کی موجودہ سیٹ*\n\n*سیٹ نمبر* درج کریں:\n_({ct} کیلیے: 1 سے {max})_\n\n_بارتھ خودبخود شناخت ہوگا!_",
    },
    "seat_detected": {
        "en": "✅ Seat *{seat}* → Berth: *{berth}*\n\nIs this correct?",
        "hi": "✅ सीट *{seat}* → बर्थ: *{berth}*\n\nक्या यह सही है?",
        "bn": "✅ সিট *{seat}* → বার্থ: *{berth}*\n\nএটা কি ঠিক আছে?",
        "ur": "✅ سیٹ *{seat}* → بارتھ: *{berth}*\n\nکیا یہ درست ہے؟",
    },
    "step_want_seat": {
        "en": "📝 *Step 4/5 — Wanted Seat*\n\nEnter the *exact seat number* you want:\n_(e.g. `41`, `26`)_\n\nOr tap *Any* to accept any seat of the berth type:",
        "hi": "📝 *चरण 4/5 — चाहिए सीट नंबर*\n\nजो *सीट नंबर* चाहिए दर्ज करें:\n_(जैसे: `41`, `26`)_\n\nया *Any* दबाएं अगर कोई भी चलेगा:",
        "bn": "📝 *ধাপ 4/5 — পছন্দের সিট নম্বর*\n\nআপনি যে *সিট নম্বর* চান লিখুন:\n_(যেমন: `41`, `26`)_\n\nবা *Any* চাপুন যেকোনো সিটের জন্য:",
        "ur": "📝 *مرحلہ 4/5 — مطلوبہ سیٹ نمبر*\n\nجو *سیٹ نمبر* چاہیے درج کریں:\n_(مثال: `41`, `26`)_\n\nیا *Any* دبائیں کسی بھی سیٹ کیلیے:",
    },
    "step_want_berth": {
        "en": "📝 *Step 4/5 (cont.)* — Which *berth type* do you want?",
        "hi": "📝 *चरण 4/5 (जारी)* — कौनसी *बर्थ* चाहिए?",
        "bn": "📝 *ধাপ 4/5 (চলমান)* — কোন *বার্থ* চান?",
        "ur": "📝 *مرحلہ 4/5 (جاری)* — کون سی *بارتھ* چاہیے؟",
    },
    "step_pnr": {
        "en": "📝 *Step 5/5 — PNR (Optional)*\n\nEnter your *10-digit PNR* for trust verification,\nor tap *Skip*:",
        "hi": "📝 *चरण 5/5 — PNR (वैकल्पिक)*\n\nविश्वास के लिए *10 अंकीय PNR* डालें,\nया *छोड़ें* दबाएं:",
        "bn": "📝 *ধাপ 5/5 — PNR (ঐচ্ছিক)*\n\nবিশ্বাসের জন্য *10 সংখ্যার PNR* লিখুন,\nঅথবা *এড়িয়ে যান* চাপুন:",
        "ur": "📝 *مرحلہ 5/5 — PNR (اختیاری)*\n\nاعتماد کیلیے *10 ہندسی PNR* درج کریں,\nیا *چھوڑیں* دبائیں:",
    },
    "invalid_train": {
        "en": "⚠️ Train *{num}* not found in our database.\n\nPlease check the number. Proceed anyway?",
        "hi": "⚠️ ट्रेन *{num}* हमारे डेटाबेस में नहीं है।\n\nनंबर जांचें। फिर भी जारी रखें?",
        "bn": "⚠️ ট্রেন *{num}* আমাদের ডেটাবেসে নেই।\n\nনম্বর যাচাই করুন। তবু এগিয়ে যাবেন?",
        "ur": "⚠️ ٹرین *{num}* ہمارے ڈیٹابیس میں نہیں ہے۔\n\nنمبر چیک کریں۔ پھر بھی جاری رکھیں؟",
    },
    "invalid_seat": {
        "en": "❌ Invalid. For {ct} enter seat 1–{max}.",
        "hi": "❌ गलत। {ct} के लिए 1–{max} दर्ज करें।",
        "bn": "❌ ভুল। {ct} এর জন্য 1–{max} লিখুন।",
        "ur": "❌ غلط۔ {ct} کیلیے 1–{max} درج کریں۔",
    },
    "invalid_pnr": {
        "en": "❌ PNR must be 10 digits. Try again or Skip:",
        "hi": "❌ PNR 10 अंकों का होना चाहिए। फिर डालें या छोड़ें:",
        "bn": "❌ PNR 10 সংখ্যার হতে হবে। আবার চেষ্টা করুন বা এড়িয়ে যান:",
        "ur": "❌ PNR 10 ہندسی ہونا چاہیے۔ دوبارہ کوشش کریں یا چھوڑیں:",
    },
    "posted": {
        "en": "✅ *Seat Change Request Posted!*\n\n🚆 Train: *{train}* — _{tname}_\n🚉 Coach: *{coach}* ({ct})\n💺 Has: Seat *{cseat}* (*{cberth}*)\n🔄 Wants: Seat *{wseat}* (*{wberth}*)\n{pnr}\n\n🔔 You'll be notified when a match is found!",
        "hi": "✅ *सीट बदलाव अनुरोध पोस्ट हुआ!*\n\n🚆 ट्रेन: *{train}* — _{tname}_\n🚉 बोगी: *{coach}* ({ct})\n💺 है: सीट *{cseat}* (*{cberth}*)\n🔄 चाहिए: सीट *{wseat}* (*{wberth}*)\n{pnr}\n\n🔔 मैच मिलने पर सूचना मिलेगी!",
        "bn": "✅ *সিট পরিবর্তনের অনুরোধ পোস্ট হয়েছে!*\n\n🚆 ট্রেন: *{train}* — _{tname}_\n🚉 কোচ: *{coach}* ({ct})\n💺 আছে: সিট *{cseat}* (*{cberth}*)\n🔄 চাই: সিট *{wseat}* (*{wberth}*)\n{pnr}\n\n🔔 ম্যাচ পেলে জানানো হবে!",
        "ur": "✅ *سیٹ تبدیلی کی درخواست پوسٹ ہوئی!*\n\n🚆 ٹرین: *{train}* — _{tname}_\n🚉 بوگی: *{coach}* ({ct})\n💺 ہے: سیٹ *{cseat}* (*{cberth}*)\n🔄 چاہیے: سیٹ *{wseat}* (*{wberth}*)\n{pnr}\n\n🔔 میچ ملنے پر اطلاع ملے گی!",
    },
    "match_found": {
        "en": "🎉 *INSTANT MATCH FOUND!*\n\n👤 *{name}* {badge}\n🚉 Coach: *{coach}*\n💺 Has: Seat *{cseat}* (*{cberth}*)\n🔄 Wants: Seat *{wseat}* (*{wberth}*)\n\n📩 Contact: {contact}\n\n_After swap, tap ✅ Confirm to earn +10 pts!_",
        "hi": "🎉 *तुरंत मैच मिला!*\n\n👤 *{name}* {badge}\n🚉 बोगी: *{coach}*\n💺 है: सीट *{cseat}* (*{cberth}*)\n🔄 चाहिए: सीट *{wseat}* (*{wberth}*)\n\n📩 संपर्क: {contact}\n\n_स्वैप के बाद ✅ Confirm दबाएं → +10 pts!_",
        "bn": "🎉 *তাৎক্ষণিক ম্যাচ!*\n\n👤 *{name}* {badge}\n🚉 কোচ: *{coach}*\n💺 আছে: সিট *{cseat}* (*{cberth}*)\n🔄 চাই: সিট *{wseat}* (*{wberth}*)\n\n📩 যোগাযোগ: {contact}\n\n_বদলের পর ✅ Confirm → +10 pts!_",
        "ur": "🎉 *فوری میچ ملا!*\n\n👤 *{name}* {badge}\n🚉 بوگی: *{coach}*\n💺 ہے: سیٹ *{cseat}* (*{cberth}*)\n🔄 چاہیے: سیٹ *{wseat}* (*{wberth}*)\n\n📩 رابطہ: {contact}\n\n_تبادلے کے بعد ✅ Confirm → +10 pts!_",
    },
    "confirmed_1": {
        "en": "⏳ *Your confirmation saved!*\n\nWaiting for the other person to also confirm.\nPoints will be awarded to *both* once they confirm!",
        "hi": "⏳ *पुष्टि सेव हो गई!*\n\nदूसरे व्यक्ति की पुष्टि का इंतजार है।\nदोनों की पुष्टि होने पर +10 pts मिलेंगे!",
        "bn": "⏳ *নিশ্চিতকরণ সেভ হয়েছে!*\n\nঅন্য ব্যক্তির নিশ্চিতকরণের অপেক্ষায়।\nদুজন নিশ্চিত করলেই পয়েন্ট মিলবে!",
        "ur": "⏳ *تصدیق محفوظ!*\n\nدوسرے شخص کی تصدیق کا انتظار ہے۔\nدونوں کی تصدیق پر +10 pts ملیں گے!",
    },
    "confirmed_both": {
        "en": "🎉 *Swap Confirmed!*\n\n+10 points earned!\nTotal: *{pts}* pts | Badge: *{badge}*\n\n{bar}",
        "hi": "🎉 *स्वैप पुष्टि!*\n\n+10 pts मिले!\nकुल: *{pts}* pts | बैज: *{badge}*\n\n{bar}",
        "bn": "🎉 *সওয়াপ নিশ্চিত!*\n\n+10 pts পেয়েছেন!\nমোট: *{pts}* pts | ব্যাজ: *{badge}*\n\n{bar}",
        "ur": "🎉 *سویپ تصدیق!*\n\n+10 pts ملے!\nکل: *{pts}* pts | بیج: *{badge}*\n\n{bar}",
    },
    "feedback_ask": {
        "en": "💬 *Send Feedback*\n\nWrite your message, suggestion or problem.\nIt goes directly to admin:",
        "hi": "💬 *फ़ीडबैक भेजें*\n\nअपना संदेश, सुझाव या समस्या लिखें।\nसीधे एडमिन को जाएगा:",
        "bn": "💬 *ফিডব্যাক পাঠান*\n\nআপনার বার্তা, পরামর্শ বা সমস্যা লিখুন।\nসরাসরি অ্যাডমিনের কাছে যাবে:",
        "ur": "💬 *فیڈبیک بھیجیں*\n\nاپنا پیغام، مشورہ یا مسئلہ لکھیں۔\nبراہ راست ایڈمن کو جائے گا:",
    },
    "feedback_done": {
        "en": "✅ *Feedback sent!* Thank you. Admin will review it soon.",
        "hi": "✅ *फ़ीडबैक भेजा गया!* शुक्रिया। एडमिन जल्द देखेंगे।",
        "bn": "✅ *ফিডব্যাক পাঠানো হয়েছে!* ধন্যবাদ।",
        "ur": "✅ *فیڈبیک بھیج دیا!* شکریہ۔ ایڈمن جلد دیکھیں گے۔",
    },
    "search_enter": {
        "en": "🔍 *Find Seat*\n\nEnter *train number* to search:",
        "hi": "🔍 *सीट खोजें*\n\n*ट्रेन नंबर* दर्ज करें:",
        "bn": "🔍 *সিট খুঁজুন*\n\n*ট্রেন নম্বর* লিখুন:",
        "ur": "🔍 *سیٹ تلاش کریں*\n\n*ٹرین نمبر* درج کریں:",
    },
    "no_swaps": {
        "en": "😔 No active requests for *Train {train}*.\nBe the first to post yours!",
        "hi": "😔 ट्रेन *{train}* के लिए कोई अनुरोध नहीं।\nपहले अपना पोस्ट करें!",
        "bn": "😔 ট্রেন *{train}* এর জন্য কোনো অনুরোধ নেই।",
        "ur": "😔 ٹرین *{train}* کیلیے کوئی درخواست نہیں۔\nپہلے اپنا پوسٹ کریں!",
    },
    "no_request": {
        "en": "📋 You have no active seat change request.",
        "hi": "📋 आपका कोई सक्रिय अनुरोध नहीं है।",
        "bn": "📋 আপনার কোনো সক্রিয় অনুরোধ নেই।",
        "ur": "📋 آپ کی کوئی فعال درخواست نہیں ہے۔",
    },
    "cancelled": {
        "en": "✅ Your request has been removed.",
        "hi": "✅ आपका अनुरोध हटा दिया गया।",
        "bn": "✅ আপনার অনুরোধ সরানো হয়েছে।",
        "ur": "✅ آپ کی درخواست ہٹا دی گئی۔",
    },
    "help_text": {
        "en": (
            "❓ *How to use SeatSwap*\n\n"
            "1️⃣ Tap *🔄 Change Seat*\n"
            "   → Train no → Coach → Your seat no → Wanted seat no → PNR (optional)\n\n"
            "2️⃣ Tap *🔍 Find Seat*\n"
            "   → Train no → Pick coach → See all requests\n\n"
            "3️⃣ Contact person via 📩 button\n\n"
            "4️⃣ After swap → Tap *✅ Confirm Swap Done*\n"
            "   → Both confirm → Both get +10 pts!\n\n"
            "🚩 Report fake users (3 reports = auto ban)\n\n"
            "🏅 *Badges:*\n"
            "🌱 Newcomer • 🎫 Regular (3+)\n"
            "⭐ Trusted (10+) • 🔰 Expert (25+) • 👑 Master (50+)"
        ),
        "hi": (
            "❓ *SeatSwap का उपयोग*\n\n"
            "1️⃣ *🔄 सीट बदलें* दबाएं\n"
            "   → ट्रेन → बोगी → आपकी सीट → चाहिए सीट → PNR\n\n"
            "2️⃣ *🔍 सीट खोजें* दबाएं\n"
            "   → ट्रेन नंबर → बोगी चुनें → सभी अनुरोध देखें\n\n"
            "3️⃣ 📩 बटन से सीधे संपर्क करें\n\n"
            "4️⃣ स्वैप के बाद *✅ Confirm* दबाएं → दोनों को +10 pts!\n\n"
            "🏅 *बैज:* 🌱 नया • 🎫 नियमित (3+)\n"
            "⭐ विश्वसनीय (10+) • 🔰 विशेषज्ञ (25+) • 👑 मास्टर (50+)"
        ),
        "bn": (
            "❓ *SeatSwap ব্যবহার পদ্ধতি*\n\n"
            "1️⃣ *🔄 সিট বদলান* চাপুন\n"
            "   → ট্রেন → কোচ → আপনার সিট → পছন্দের সিট → PNR\n\n"
            "2️⃣ *🔍 সিট খুঁজুন* চাপুন\n"
            "   → ট্রেন নম্বর → কোচ → সব অনুরোধ দেখুন\n\n"
            "3️⃣ 📩 বোতাম দিয়ে যোগাযোগ করুন\n\n"
            "4️⃣ বদলের পর *✅ Confirm* → দুজনই +10 pts পাবেন!\n\n"
            "🏅 *ব্যাজ:* 🌱 নতুন • 🎫 নিয়মিত (3+)\n"
            "⭐ বিশ্বস্ত (10+) • 🔰 বিশেষজ্ঞ (25+) • 👑 মাস্টার (50+)"
        ),
        "ur": (
            "❓ *SeatSwap استعمال کا طریقہ*\n\n"
            "1️⃣ *🔄 سیٹ بدلیں* دبائیں\n"
            "   → ٹرین → بوگی → آپ کی سیٹ → مطلوبہ سیٹ → PNR\n\n"
            "2️⃣ *🔍 سیٹ تلاش کریں* دبائیں\n"
            "   → ٹرین نمبر → بوگی → تمام درخواستیں دیکھیں\n\n"
            "3️⃣ 📩 بٹن سے رابطہ کریں\n\n"
            "4️⃣ تبادلے کے بعد *✅ Confirm* → دونوں کو +10 pts!\n\n"
            "🏅 *بیج:* 🌱 نیا • 🎫 باقاعدہ (3+)\n"
            "⭐ قابل اعتماد (10+) • 🔰 ماہر (25+) • 👑 ماسٹر (50+)"
        ),
    },
}

def s(key, lang="en", **kw):
    text = STRINGS.get(key, {}).get(lang) or STRINGS.get(key, {}).get("en", "")
    return text.format(**kw) if kw else text

# ═══════════════════════════════════════════════════════
#  FIREBASE HELPERS
# ═══════════════════════════════════════════════════════
def fb_get(p):
    if not FIREBASE_ON: return None
    try: return db.reference(p).get()
    except: return None

def fb_set(p, d):
    if not FIREBASE_ON: return
    try: db.reference(p).set(d)
    except Exception as e: print(f"fb_set {p}: {e}")

def fb_upd(p, d):
    if not FIREBASE_ON: return
    try: db.reference(p).update(d)
    except Exception as e: print(f"fb_upd {p}: {e}")

def fb_del(p):
    if not FIREBASE_ON: return
    try: db.reference(p).delete()
    except: pass

def ensure_user(user):
    if fb_get(f"users/{user.id}"): return
    fb_set(f"users/{user.id}", {
        "name": user.first_name, "username": user.username or "",
        "lang": "en", "points": 0, "swaps_done": 0,
        "badge": get_badge(swaps=0), "banned": False, "reports": 0,
        "special_user": False, "special_badge": "",
        "joined": datetime.now().strftime("%d %b %Y"),
    })

def get_user(uid):
    return fb_get(f"users/{uid}") or {
        "name":"User","username":"","lang":"en","points":0,
        "swaps_done":0,"badge":"🌱 Newcomer","banned":False,"reports":0,
        "special_user":False,"special_badge":"",
    }

def ulang(uid):
    return get_user(uid).get("lang", "en")

def is_banned(uid): return get_user(uid).get("banned", False)

def is_admin(uid):
    if uid in ADMIN_IDS: return True
    u = get_user(uid)
    un = u.get("username","").lower().lstrip("@")
    return un in ADMIN_UNAMES if un else False

def all_swaps(): return fb_get("swaps") or {}

def my_swap(uid):
    return next((v for v in all_swaps().values() if v.get("user_id") == uid), None)

def clink(req):
    return f"@{req['username']}" if req.get("username") else f"[{req['name']}](tg://user?id={req['user_id']})"

def time_ago(ts):
    try:
        d = datetime.strptime(ts, "%d %b %Y %I:%M %p")
        m = int((datetime.now()-d).total_seconds()/60)
        if m < 1: return "just now"
        if m < 60: return f"{m}m ago"
        h = m // 60
        return f"{h}h ago" if h < 24 else f"{(datetime.now()-d).days}d ago"
    except: return ts

def clean_old_swaps():
    swaps = all_swaps()
    now = datetime.now()
    for k, v in swaps.items():
        try:
            ts = datetime.strptime(v.get("ts",""), "%d %b %Y %I:%M %p")
            if (now - ts).total_seconds() > 86400:
                fb_del(f"swaps/{k}")
                print(f"🗑 Auto-deleted old swap {k}")
        except: pass

def save_swap(user, d):
    clean_old_swaps()
    sid = str(uuid.uuid4())[:8]
    for k, v in all_swaps().items():
        if v.get("user_id") == user.id: fb_del(f"swaps/{k}")
    u = get_user(user.id)
    sw = {
        "swap_id":  sid,       "user_id": user.id,
        "name":     user.first_name, "username": user.username or "",
        "badge":    get_badge(user.id),
        "train":    d["train"],   "train_name": d.get("train_name", d["train"]),
        "coach_type": d["ct"],    "coach": d["coach"],
        "cur_seat": d["cseat"],   "cur_berth": d["cberth"],
        "want_seat": d["wseat"],  "want_berth": d["wberth"],
        "pnr":      d.get("pnr",""), "status": "active",
        "ts":       datetime.now().strftime("%d %b %Y %I:%M %p"),
    }
    fb_set(f"swaps/{sid}", sw)
    return sw

def find_match(sw):
    opp = {
        "lower":      ["upper","middle","any"],
        "upper":      ["lower","middle","any"],
        "middle":     ["lower","upper","any"],
        "side lower": ["side upper","any"],
        "side upper": ["side lower","any"],
        "window":     ["aisle","middle","any"],
        "aisle":      ["window","middle","any"],
        "any":        ["lower","upper","middle","side lower","side upper","window","aisle","any"],
    }
    nw = sw["want_berth"].lower(); nc = sw["cur_berth"].lower()
    nws = str(sw.get("want_seat",""))
    ncs = str(sw.get("cur_seat",""))
    best = None; best_score = 0
    for k, s in all_swaps().items():
        if s.get("user_id") == sw["user_id"]: continue
        if s.get("train") != sw["train"]:     continue
        if s.get("coach_type") != sw["coach_type"]: continue
        tw = s.get("want_berth","").lower(); tc = s.get("cur_berth","").lower()
        tws = str(s.get("want_seat",""))
        tcs = str(s.get("cur_seat",""))
        berth_ok = (tw==nc or tw in opp.get(nc,[]) or nw==tc or nw in opp.get(tc,[]))
        if not berth_ok: continue
        score = 1
        if nws and nws == tcs: score += 10
        if tws and tws == ncs: score += 10
        if score > best_score: best_score = score; best = s
    return best

def del_my_swap(uid):
    deleted = False
    for k, v in all_swaps().items():
        if v.get("user_id") == uid: fb_del(f"swaps/{k}"); deleted = True
    return deleted

def award(uid):
    u = get_user(uid); sd = u.get("swaps_done",0)+1; pt = u.get("points",0)+10
    fb_upd(f"users/{uid}", {"swaps_done": sd, "points": pt, "badge": get_badge(swaps=sd)})
    return sd, pt

# ═══════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════
def kb_menu(lang="en"):
    m = LANG_MENU.get(lang, LANG_MENU["en"])
    return ReplyKeyboardMarkup([
        [m["change_seat"], m["find_seat"]],
        [m["my_req"],      m["profile"]],
        [m["language"],    m["help"]],
        [m["feedback"]],
    ], resize_keyboard=True)

def kb_home():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="home")]])

def kb_cancel():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="home")]])

def kb_ct():
    rows = []
    items = list(COACH_TYPES.items())
    for i in range(0, len(items), 2):
        rows.append([InlineKeyboardButton(v["label"], callback_data=f"ct_{k}") for k,v in items[i:i+2]])
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def kb_coaches(lst):
    rows = [InlineKeyboardButton(c, callback_data=f"cn_{c}") for c in lst]
    grid = [rows[i:i+4] for i in range(0, len(rows), 4)]
    grid.append([InlineKeyboardButton("⬅️ Back", callback_data="back_ct")])
    return InlineKeyboardMarkup(grid)

def kb_berths(ct, prefix):
    bl = BERTHS_BY_CT.get(ct, ["Lower","Upper"])
    rows = [[InlineKeyboardButton(f"{BERTH_EMOJI.get(b,'🔄')} {b}", callback_data=f"{prefix}_{b}")] for b in bl]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=f"{prefix}_back")])
    return InlineKeyboardMarkup(rows)

def kb_any_seat(lang):
    txt = {"en":"✅ Any Seat","hi":"✅ कोई भी सीट","bn":"✅ যেকোনো সিট","ur":"✅ کوئی بھی سیٹ"}.get(lang,"✅ Any Seat")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(txt, callback_data="wseat_any")],
        [InlineKeyboardButton("❌ Cancel", callback_data="home")],
    ])

def kb_yesno(yes_cb, no_cb, lang):
    yes = {"en":"✅ Yes","hi":"✅ हाँ","bn":"✅ হ্যাঁ","ur":"✅ ہاں"}.get(lang,"✅ Yes")
    no  = {"en":"❌ Re-enter","hi":"❌ दोबारा","bn":"❌ আবার","ur":"❌ دوبارہ"}.get(lang,"❌ Re-enter")
    return InlineKeyboardMarkup([[InlineKeyboardButton(yes,callback_data=yes_cb), InlineKeyboardButton(no,callback_data=no_cb)]])

def kb_skip(lang):
    txt = {"en":"⏭️ Skip","hi":"⏭️ छोड़ें","bn":"⏭️ এড়িয়ে","ur":"⏭️ چھوڑیں"}.get(lang,"⏭️ Skip")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(txt, callback_data="pnr_skip")],
        [InlineKeyboardButton("❌ Cancel", callback_data="home")],
    ])

def kb_confirm(sid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Swap Done", callback_data=f"confirm_{sid}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="home")],
    ])

def kb_lang():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇬🇧 English",  callback_data="lang_en"),
         InlineKeyboardButton("🇮🇳 हिन्दी",  callback_data="lang_hi")],
        [InlineKeyboardButton("🇧🇩 বাংলা",   callback_data="lang_bn"),
         InlineKeyboardButton("🇵🇰 اردو",    callback_data="lang_ur")],
    ])

# ═══════════════════════════════════════════════════════
#  REPLY HELPER
# ═══════════════════════════════════════════════════════
async def rply(update: Update, text: str, kb=None):
    kw = dict(text=text, parse_mode="Markdown", reply_markup=kb)
    if update.callback_query:
        try: await update.callback_query.edit_message_text(**kw)
        except: await update.callback_query.message.reply_text(**kw)
    else:
        await update.message.reply_text(**kw)

# ═══════════════════════════════════════════════════════
#  /START
# ═══════════════════════════════════════════════════════
keyboard = [
    [
        InlineKeyboardButton(
            "📱 Open App",
            web_app=WebAppInfo(
                url="https://farhan2520.github.io/telegram-bot/"
            )
        )
    ]
]

reply_markup = InlineKeyboardMarkup(keyboard)
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)
    ctx.user_data.clear()
    if is_banned(user.id):
        await rply(update, "🚫 Your account has been suspended."); return
    lang = ulang(user.id)
    db_ico = "🟢" if FIREBASE_ON else "🔴"
    await update.effective_message.reply_text(
        s("welcome", lang, name=user.first_name) + f"\n\n_{db_ico} DB {'Online' if FIREBASE_ON else 'Offline'}_",
        reply_markup=kb_menu(lang), parse_mode="Markdown"
    )
from telegram import WebAppInfo
# Start message mein keyboard add karo:
InlineKeyboardButton("📱 Open App", web_app=WebAppInfo(url="https://yourusername.github.io/seatswap-miniapp"))
# ═══════════════════════════════════════════════════════
#  CHANGE SEAT (POST SWAP) FLOW
# ═══════════════════════════════════════════════════════
async def cs_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): await rply(update, "🚫 Banned."); return
    lang = ulang(uid)
    ctx.user_data.update({"flow": "cs_train", "cs": {}})
    await rply(update, s("step_train", lang), kb_cancel())

async def cs_got_train(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    uid = update.effective_user.id; lang = ulang(uid)
    if not re.match(r"^\d{4,6}$", raw):
        await update.message.reply_text("❌ Train number should be 4–6 digits. Try again:", parse_mode="Markdown"); return
    tname = TRAINS.get(raw, "")
    ctx.user_data["cs"]["train"] = raw.upper()
    ctx.user_data["cs"]["train_name"] = tname or raw.upper()
    ctx.user_data["flow"] = "cs_ct"
    if tname:
        await update.message.reply_text(s("step_coach_type",lang,num=raw,name=tname), reply_markup=kb_ct(), parse_mode="Markdown")
    else:
        await update.message.reply_text(
            s("invalid_train", lang, num=raw),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Proceed", callback_data="cs_train_ok"),
                 InlineKeyboardButton("❌ Re-enter", callback_data="cs_train_retry")],
            ]), parse_mode="Markdown"
        )

async def cs_got_ct(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    code = update.callback_query.data.replace("ct_","")
    await update.callback_query.answer()
    lang = ulang(update.effective_user.id)
    ctx.user_data["cs"]["ct"] = code
    ctx.user_data["flow"] = "cs_coach"
    await update.callback_query.edit_message_text(
        s("step_coach", lang) + f"\n\n_Type: {COACH_TYPES[code]['label']}_",
        reply_markup=kb_coaches(COACH_TYPES[code]["coaches"]), parse_mode="Markdown"
    )

async def cs_got_coach(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    coach = update.callback_query.data.replace("cn_","")
    await update.callback_query.answer()
    uid = update.effective_user.id; lang = ulang(uid)
    ctx.user_data["cs"]["coach"] = coach
    ctx.user_data["flow"] = "cs_cseat"
    ct = ctx.user_data["cs"]["ct"]
    mx = COACH_TYPES[ct]["max_seat"]
    await update.callback_query.edit_message_text(
        f"✅ Coach: *{coach}*\n\n{s('step_cur_seat',lang,ct=ct,max=mx)}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back_ct")]]),
        parse_mode="Markdown"
    )

async def cs_got_cseat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    uid = update.effective_user.id; lang = ulang(uid)
    ct = ctx.user_data["cs"]["ct"]
    mx = COACH_TYPES.get(ct,{}).get("max_seat",72)
    if not raw.isdigit() or not (1 <= int(raw) <= mx):
        await update.message.reply_text(s("invalid_seat",lang,ct=ct,max=mx), parse_mode="Markdown"); return
    berth = auto_berth(raw, ct)
    ctx.user_data["cs"]["cseat"]  = raw
    ctx.user_data["cs"]["cberth"] = berth
    ctx.user_data["flow"] = "cs_cseat_confirm"
    await update.message.reply_text(
        s("seat_detected", lang, seat=raw, berth=berth),
        reply_markup=kb_yesno("cs_cseat_ok","cs_cseat_retry",lang),
        parse_mode="Markdown"
    )

async def cs_got_wseat_num(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    uid = update.effective_user.id; lang = ulang(uid)
    ct = ctx.user_data["cs"]["ct"]
    mx = COACH_TYPES.get(ct,{}).get("max_seat",72)
    if not raw.isdigit() or not (1 <= int(raw) <= mx):
        await update.message.reply_text(s("invalid_seat",lang,ct=ct,max=mx), reply_markup=kb_any_seat(lang), parse_mode="Markdown"); return
    ctx.user_data["cs"]["wseat"] = raw
    ctx.user_data["flow"] = "cs_wberth"
    await update.message.reply_text(
        s("step_want_berth", lang),
        reply_markup=kb_berths(ct, "wb"), parse_mode="Markdown"
    )

async def cs_got_wberth(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    berth = update.callback_query.data.replace("wb_","")
    await update.callback_query.answer()
    ctx.user_data["cs"]["wberth"] = berth
    ctx.user_data["flow"] = "cs_pnr"
    lang = ulang(update.effective_user.id)
    await update.callback_query.edit_message_text(s("step_pnr",lang), reply_markup=kb_skip(lang), parse_mode="Markdown")

async def cs_wseat_any(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    lang = ulang(update.effective_user.id)
    ctx.user_data["cs"]["wseat"] = "Any"
    ctx.user_data["flow"] = "cs_wberth"
    ct = ctx.user_data["cs"]["ct"]
    await update.callback_query.edit_message_text(
        s("step_want_berth", lang),
        reply_markup=kb_berths(ct, "wb"), parse_mode="Markdown"
    )

async def cs_got_pnr(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    uid = update.effective_user.id; lang = ulang(uid)
    if not re.match(r"^\d{10}$", raw):
        await update.message.reply_text(s("invalid_pnr",lang), reply_markup=kb_skip(lang), parse_mode="Markdown"); return
    ctx.user_data["cs"]["pnr"] = raw
    ctx.user_data["flow"] = ""
    await cs_finish(update, ctx)

async def cs_pnr_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ctx.user_data["cs"]["pnr"] = ""
    ctx.user_data["flow"] = ""
    await cs_finish(update, ctx)

async def cs_finish(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; d = ctx.user_data.get("cs",{}); lang = ulang(user.id)
    pnr_line = f"🎫 PNR: `{d['pnr']}`" if d.get("pnr") else ""
    sw = save_swap(user, d)
    text = s("posted", lang,
        train=d["train"], tname=d["train_name"], coach=d["coach"], ct=d["ct"],
        cseat=d["cseat"], cberth=d["cberth"],
        wseat=d.get("wseat","Any"), wberth=d.get("wberth","Any"),
        pnr=pnr_line
    )
    match = find_match(sw)
    if match:
        um = get_user(match["user_id"]); cl = clink(match)
        text += "\n\n" + s("match_found", lang,
            name=match["name"], badge=um.get("badge",""), coach=match["coach"],
            cseat=match.get("cur_seat","?"), cberth=match.get("cur_berth","?"),
            wseat=match.get("want_seat","?"), wberth=match.get("want_berth","?"),
            contact=cl
        )
        try:
            ul2 = ulang(match["user_id"]); ume = get_user(user.id)
            mc = clink({"username":user.username,"name":user.first_name,"user_id":user.id})
            await ctx.bot.send_message(
                chat_id=match["user_id"], parse_mode="Markdown",
                text=s("match_found", ul2,
                    name=user.first_name, badge=ume.get("badge",""),
                    coach=d["coach"],
                    cseat=d["cseat"], cberth=d["cberth"],
                    wseat=d.get("wseat","Any"), wberth=d.get("wberth","Any"),
                    contact=mc
                ),
                reply_markup=kb_confirm(match["swap_id"])
            )
        except: pass
        kb = kb_confirm(sw["swap_id"])
    else:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Find Seats", callback_data="find_seat"),
             InlineKeyboardButton("🏠 Menu",       callback_data="home")],
        ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

# ═══════════════════════════════════════════════════════
#  FIND SEAT FLOW
# ═══════════════════════════════════════════════════════
async def find_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ulang(update.effective_user.id)
    ctx.user_data["flow"] = "find_train"
    await rply(update, s("search_enter",lang), kb_cancel())

async def find_got_train(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip().upper()
    uid = update.effective_user.id; lang = ulang(uid)
    ctx.user_data["flow"] = ""
    swaps = all_swaps()
    results = {k:v for k,v in swaps.items() if v.get("train")==raw and v.get("status")=="active"}
    tname = TRAINS.get(raw,"")
    if not results:
        await update.message.reply_text(
            s("no_swaps",lang,train=raw) + (f"\n🔖 _{tname}_" if tname else ""),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Change Seat",callback_data="change_seat")],
                [InlineKeyboardButton("🏠 Main Menu",  callback_data="home")],
            ]), parse_mode="Markdown"
        ); return
    coaches = {}
    for v in results.values():
        coaches.setdefault(v.get("coach","?"),[]).append(v)
    tline = f"\n🔖 _{tname}_" if tname else ""
    text = f"🚆 *Train {raw}*{tline}\nFound *{len(results)}* request(s) in *{len(coaches)}* coach(es)\n\nSelect a coach 👇"
    rows = [[InlineKeyboardButton(f"🚉 {c}  —  {len(vs)} request(s)", callback_data=f"vc_{raw}_{c}")] for c,vs in sorted(coaches.items())]
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="home")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")

async def show_coach(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    _, train, coach = update.callback_query.data.split("_", 2)
    lang = ulang(update.effective_user.id)
    swaps = all_swaps()
    results = sorted(
        [v for v in swaps.values() if v.get("train")==train and v.get("coach")==coach and v.get("status")=="active"],
        key=lambda x: -get_user(x["user_id"]).get("swaps_done",0)
    )
    if not results:
        await update.callback_query.edit_message_text("No requests for this coach.", reply_markup=kb_home()); return
    text = f"🚉 *Train {train} — Coach {coach}*\n{len(results)} request(s)\n\n"
    rows = []
    for i, req in enumerate(results, 1):
        pnr = f"\n🎫 PNR: `{req['pnr']}`" if req.get("pnr") else ""
        wseat_line = f" (prefers seat *{req['want_seat']}*)" if req.get("want_seat") and req["want_seat"] != "Any" else ""
        text += (
            f"*#{i}  {req['name']}*  {req.get('badge','🌱 Newcomer')}\n"
            f"💺 Seat *{req.get('cur_seat','?')}* ({req.get('cur_berth','?')})  →  🔄 *{req.get('want_berth','Any')}*{wseat_line}{pnr}\n"
            f"✅ {get_user(req['user_id']).get('swaps_done',0)} swaps  ·  🕐 {time_ago(req.get('ts',''))}\n"
            f"──────────────────\n"
        )
        rows.append([
            InlineKeyboardButton(f"📩 Contact #{i}", url=f"tg://user?id={req['user_id']}"),
            InlineKeyboardButton(f"🚩 Report #{i}",  callback_data=f"report_{req['user_id']}"),
        ])
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="home")])
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")

# ═══════════════════════════════════════════════════════
#  CONFIRM SWAP  (dual confirm system)
# ═══════════════════════════════════════════════════════
async def confirm_swap(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    uid = update.effective_user.id; lang = ulang(uid)
    sid = update.callback_query.data.replace("confirm_","")
    key = f"confirmed/{uid}_{sid}"
    if fb_get(key):
        await update.callback_query.edit_message_text("✅ Already confirmed!", reply_markup=kb_home()); return
    fb_set(key, True)
    all_conf = fb_get("confirmed") or {}
    parties = [k for k in all_conf if k.endswith(f"_{sid}")]
    if len(parties) >= 2:
        sd, pts = award(uid)
        for ck in parties:
            try:
                o_uid = int(ck.replace(f"_{sid}",""))
                if o_uid != uid:
                    o_sd, o_pts = award(o_uid)
                    try:
                        await ctx.bot.send_message(
                            chat_id=o_uid, parse_mode="Markdown",
                            text=s("confirmed_both", ulang(o_uid), pts=o_pts, badge=get_badge(swaps=o_sd), bar=progress_bar(o_sd))
                        )
                    except: pass
            except: pass
        fb_set(f"matches/{sid}", {"completed": datetime.now().strftime("%d %b %Y %I:%M %p")})
        await update.callback_query.edit_message_text(
            s("confirmed_both", lang, pts=pts, badge=get_badge(swaps=sd), bar=progress_bar(sd)),
            reply_markup=kb_home(), parse_mode="Markdown"
        )
    else:
        await update.callback_query.edit_message_text(
            s("confirmed_1", lang), reply_markup=kb_home(), parse_mode="Markdown"
        )

# ═══════════════════════════════════════════════════════
#  REPORT SYSTEM
# ═══════════════════════════════════════════════════════
async def report_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    reporter = update.effective_user.id
    reported = int(update.callback_query.data.replace("report_",""))
    if reporter == reported:
        await update.callback_query.answer("❌ Can't report yourself!", show_alert=True); return
    key = f"reports/{reporter}_{reported}"
    if fb_get(key):
        await update.callback_query.answer("Already reported.", show_alert=True); return
    rid = str(uuid.uuid4())[:8]
    fb_set(key, True)
    fb_set(f"reports/{rid}", {
        "reporter": reporter, "reported": reported,
        "ts": datetime.now().strftime("%d %b %Y %I:%M %p"),
    })
    u = get_user(reported); count = u.get("reports",0)+1
    fb_upd(f"users/{reported}", {"reports": count})
    for aid in ADMIN_IDS:
        try:
            ru = get_user(reporter)
            await ctx.bot.send_message(
                chat_id=aid,
                text=f"🚩 *New Report*\n\nReporter: {ru.get('name','')} (ID:{reporter})\nReported: {u.get('name','')} (ID:{reported})\nTotal reports on reported: {count}",
                parse_mode="Markdown"
            )
        except: pass
    if count >= 3:
        fb_upd(f"users/{reported}", {"banned": True}); del_my_swap(reported)
        try: await ctx.bot.send_message(chat_id=reported, text="🚫 Your SeatSwap account has been suspended.")
        except: pass
        await update.callback_query.answer("⚠️ User banned after 3 reports.", show_alert=True)
    else:
        await update.callback_query.answer(f"Reported ({count}/3 before ban).", show_alert=True)

# ═══════════════════════════════════════════════════════
#  MY REQUEST
# ═══════════════════════════════════════════════════════
async def my_request(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; lang = ulang(uid)
    req = my_swap(uid)
    if not req:
        await rply(update, s("no_request",lang), InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Change Seat", callback_data="change_seat")],
            [InlineKeyboardButton("🏠 Main Menu",   callback_data="home")],
        ])); return
    pnr = f"\n🎫 PNR: `{req['pnr']}`" if req.get("pnr") else ""
    wseat = f" (prefers *{req['want_seat']}*)" if req.get("want_seat") and req["want_seat"]!="Any" else ""
    await rply(update,
        f"📋 *Your Active Request*\n\n"
        f"🚆 Train: *{req['train']}* — _{req.get('train_name','')}_\n"
        f"🚉 Coach: *{req['coach']}* ({req.get('coach_type','')})\n"
        f"💺 Has: Seat *{req.get('cur_seat','?')}* (*{req.get('cur_berth','?')}*)\n"
        f"🔄 Wants: *{req.get('want_berth','?')}*{wseat}{pnr}\n"
        f"🕐 Posted: {time_ago(req.get('ts',''))}",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Delete Request", callback_data="cancel_req")],
            [InlineKeyboardButton("🏠 Main Menu",      callback_data="home")],
        ])
    )

# ═══════════════════════════════════════════════════════
#  PROFILE
# ═══════════════════════════════════════════════════════
async def profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; u = get_user(user.id); lang = ulang(user.id)
    sd = u.get("swaps_done",0); pts = u.get("points",0)
    badge = get_badge(user.id)
    special = ""
    if u.get("special_user"): special = "\n🌟 *Official SeatSwap Family*"
    pnr_verified = "✅ Yes" if u.get("pnr_verified") else "❌ No"
    await rply(update,
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Profile*{special}\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Name:     *{user.first_name}*\n"
        f"Username: @{user.username or 'not set'}\n"
        f"Badge:    {badge}\n\n"
        f"✅ Swaps Done: *{sd}*\n"
        f"⭐ Points:     *{pts}*\n\n"
        f"📈 *Progress:*\n{progress_bar(sd)}",
        kb_home()
    )

# ═══════════════════════════════════════════════════════
#  FEEDBACK
# ═══════════════════════════════════════════════════════
async def feedback_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ulang(update.effective_user.id)
    ctx.user_data["flow"] = "feedback"
    await rply(update, s("feedback_ask",lang), kb_cancel())

async def feedback_got_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; lang = ulang(uid)
    msg = update.message.text; u = get_user(uid)
    ctx.user_data["flow"] = ""
    fid = f"{uid}_{int(datetime.now().timestamp())}"
    fb_set(f"feedbacks/{fid}", {
        "user_id": uid, "name": u.get("name",""), "username": u.get("username",""),
        "message": msg, "ts": datetime.now().strftime("%d %b %Y %I:%M %p"),
    })
    for aid in ADMIN_IDS:
        try:
            uname = f"@{u.get('username','')}" if u.get("username") else f"ID:{uid}"
            await ctx.bot.send_message(
                chat_id=aid,
                text=f"📩 *New Feedback*\n\n👤 {u.get('name','')} ({uname})\n\n💬 {msg}",
                parse_mode="Markdown"
            )
        except: pass
    await update.message.reply_text(s("feedback_done",lang), reply_markup=kb_home(), parse_mode="Markdown")

# ═══════════════════════════════════════════════════════
#  LANGUAGE
# ═══════════════════════════════════════════════════════
async def choose_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await rply(update, "🌐 *Choose your language:*", kb_lang())

async def set_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.data.replace("lang_","")
    uid = update.effective_user.id
    fb_upd(f"users/{uid}", {"lang": lang})
    await update.callback_query.answer()
    names = {"en":"English 🇬🇧","hi":"हिन्दी 🇮🇳","bn":"বাংলা 🇧🇩","ur":"اردو 🇵🇰"}
    await update.callback_query.edit_message_text(
        f"✅ Language set to *{names.get(lang,lang)}*",
        parse_mode="Markdown", reply_markup=kb_home()
    )
    await update.callback_query.message.reply_text("👇", reply_markup=kb_menu(lang))

# ═══════════════════════════════════════════════════════
#  HELP
# ═══════════════════════════════════════════════════════
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ulang(update.effective_user.id)
    await rply(update, s("help_text",lang), kb_home())

# ═══════════════════════════════════════════════════════
#  CANCEL
# ═══════════════════════════════════════════════════════
async def cancel_req(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; lang = ulang(uid)
    ctx.user_data.clear()
    deleted = del_my_swap(uid)
    await rply(update, s("cancelled" if deleted else "no_request", lang), kb_home())

# ═══════════════════════════════════════════════════════
#  /MYID
# ═══════════════════════════════════════════════════════
async def my_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.message.reply_text(
        f"🔑 *Your Telegram ID:*\n`{u.id}`\n\nUsername: @{u.username or 'not set'}\n\n_Share with admin if needed._",
        parse_mode="Markdown"
    )

# ═══════════════════════════════════════════════════════
#  ADMIN COMMANDS
# ═══════════════════════════════════════════════════════
async def admin_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    users = fb_get("users") or {}; swaps = all_swaps()
    active = sum(1 for s in swaps.values() if s.get("status")=="active")
    banned = sum(1 for u in users.values() if u.get("banned"))
    total_sd = sum(u.get("swaps_done",0) for u in users.values())
    reports = fb_get("reports") or {}
    feedbacks = fb_get("feedbacks") or {}
    await update.message.reply_text(
        f"📊 *Admin Stats*\n\n"
        f"🗄 Firebase: {'✅ Online' if FIREBASE_ON else '❌ Offline'}\n"
        f"👥 Total Users: *{len(users)}*\n"
        f"🔄 Active Swaps: *{active}*\n"
        f"✅ Total Swaps Done: *{total_sd}*\n"
        f"🚫 Banned: *{banned}*\n"
        f"🚩 Total Reports: *{len(reports)}*\n"
        f"💬 Feedbacks: *{len(feedbacks)}*",
        parse_mode="Markdown"
    )

async def admin_allusers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    users = fb_get("users") or {}
    text = f"👥 *All Users* ({len(users)} total)\n\n"
    for uid, u in list(users.items())[:20]:
        text += f"• {u.get('name','')} (@{u.get('username','?')}) — {u.get('badge','')} — {u.get('swaps_done',0)} swaps\n"
    if len(users) > 20: text += f"\n_...and {len(users)-20} more_"
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_activeusers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    swaps = all_swaps()
    uids = list(set(v.get("user_id") for v in swaps.values()))
    text = f"🟢 *Active Users* ({len(uids)} with live requests)\n\n"
    for uid in uids[:20]:
        u = get_user(uid)
        sw = my_swap(uid)
        if sw: text += f"• {u.get('name','')} — Train {sw.get('train','')} Coach {sw.get('coach','')}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_totalswaps(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    users = fb_get("users") or {}
    total = sum(u.get("swaps_done",0) for u in users.values())
    active = len([s for s in all_swaps().values() if s.get("status")=="active"])
    matches = fb_get("matches") or {}
    await update.message.reply_text(
        f"📈 *Swap Statistics*\n\n"
        f"✅ Total Completed Swaps: *{total}*\n"
        f"🔄 Currently Active Requests: *{active}*\n"
        f"🤝 Confirmed Matches: *{len(matches)}*",
        parse_mode="Markdown"
    )

async def admin_feedbacks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    feedbacks = fb_get("feedbacks") or {}
    if not feedbacks:
        await update.message.reply_text("📭 No feedbacks yet."); return
    items = sorted(feedbacks.items(), key=lambda x: x[1].get("ts",""), reverse=True)[:10]
    text = f"📩 *Recent Feedbacks* ({len(feedbacks)} total)\n\n"
    for k, v in items:
        uname = f"@{v.get('username','')}" if v.get("username") else f"ID:{v.get('user_id','')}"
        text += f"👤 *{v.get('name','')}* ({uname})\n💬 {v.get('message','')}\n🕐 {v.get('ts','')}\n\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_checkdb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not FIREBASE_ON:
        await update.message.reply_text(
            "❌ *Firebase NOT connected!*\n\nFix:\n1. Railway → Variables\n2. Add `FIREBASE_KEY` with JSON\n3. Redeploy",
            parse_mode="Markdown"); return
    try:
        db.reference("bot_status").update({"ping": datetime.now().strftime("%d %b %Y %I:%M %p")})
        r = db.reference("bot_status").get()
        await update.message.reply_text(
            f"✅ *Firebase Working!*\n\nPing: `{r.get('ping')}`\nBoot: `{r.get('boot')}`",
            parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error:\n`{e}`", parse_mode="Markdown")

async def admin_givebadge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if len(ctx.args) < 2:
        opts = ", ".join(SPECIAL_BADGES.keys())
        await update.message.reply_text(f"Usage: /givebadge <user_id> <badge>\nOptions: {opts}\nExample: /givebadge 123456 Master"); return
    uid = int(ctx.args[0]); badge_key = ctx.args[1].capitalize()
    if badge_key not in SPECIAL_BADGES:
        await update.message.reply_text(f"❌ Unknown badge. Options: {', '.join(SPECIAL_BADGES.keys())}"); return
    badge_val = SPECIAL_BADGES[badge_key]
    fb_upd(f"users/{uid}", {"special_badge": badge_val, "badge": badge_val})
    u = get_user(uid)
    await update.message.reply_text(f"✅ {badge_val} badge given to *{u.get('name',uid)}*.", parse_mode="Markdown")
    try:
        await ctx.bot.send_message(chat_id=uid, text=f"🎉 You've been given a special badge: *{badge_val}*\n\nKeep swapping! 🚆", parse_mode="Markdown")
    except: pass

async def admin_removebadge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not ctx.args:
        await update.message.reply_text("Usage: /removebadge <user_id>"); return
    uid = int(ctx.args[0]); u = get_user(uid)
    sd = u.get("swaps_done",0)
    fb_upd(f"users/{uid}", {"special_badge": "", "badge": get_badge(swaps=sd)})
    await update.message.reply_text(f"✅ Special badge removed from *{u.get('name',uid)}*.", parse_mode="Markdown")

async def admin_viewbadge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not ctx.args:
        await update.message.reply_text("Usage: /viewbadge <user_id>"); return
    uid = int(ctx.args[0]); u = get_user(uid)
    await update.message.reply_text(
        f"👤 *{u.get('name',uid)}* (@{u.get('username','?')})\n"
        f"Current Badge: {u.get('badge','')}\n"
        f"Special Badge: {u.get('special_badge') or 'None'}\n"
        f"Special User: {'Yes 🌟' if u.get('special_user') else 'No'}",
        parse_mode="Markdown"
    )

async def admin_setfamily(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not ctx.args:
        await update.message.reply_text("Usage: /setfamily <user_id>"); return
    uid = int(ctx.args[0])
    fb_upd(f"users/{uid}", {"special_user": True, "badge": "🌟 Official SeatSwap Family"})
    u = get_user(uid)
    await update.message.reply_text(f"✅ *{u.get('name',uid)}* is now Official SeatSwap Family 🌟", parse_mode="Markdown")
    try:
        await ctx.bot.send_message(chat_id=uid, text="🌟 You are now an *Official SeatSwap Family* member!\n\nSpecial badge added to your profile.", parse_mode="Markdown")
    except: pass

async def admin_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not ctx.args:
        await update.message.reply_text("Usage: /ban <user_id>"); return
    uid = int(ctx.args[0]); fb_upd(f"users/{uid}", {"banned": True}); del_my_swap(uid)
    await update.message.reply_text(f"🚫 User `{uid}` banned.", parse_mode="Markdown")
    try: await ctx.bot.send_message(chat_id=uid, text="🚫 Your SeatSwap account has been suspended.")
    except: pass

async def admin_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not ctx.args:
        await update.message.reply_text("Usage: /unban <user_id>"); return
    uid = int(ctx.args[0]); fb_upd(f"users/{uid}", {"banned": False, "reports": 0})
    await update.message.reply_text(f"✅ User `{uid}` unbanned.", parse_mode="Markdown")
    try: await ctx.bot.send_message(chat_id=uid, text="✅ Your SeatSwap account has been restored.")
    except: pass

async def admin_userinfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not ctx.args:
        await update.message.reply_text("Usage: /userinfo <user_id>"); return
    uid = int(ctx.args[0]); u = get_user(uid); sw = my_swap(uid)
    swap_info = f"🔄 Active: Train {sw['train']} Coach {sw['coach']} Seat {sw.get('cur_seat','?')}" if sw else "No active swap"
    await update.message.reply_text(
        f"👤 *User Info*\n\nID: `{uid}`\nName: {u.get('name','')}\nUsername: @{u.get('username','none')}\n"
        f"Lang: {u.get('lang','en')}\nBadge: {u.get('badge','')}\nSpecial: {u.get('special_badge') or 'None'}\n"
        f"Family: {'Yes 🌟' if u.get('special_user') else 'No'}\nSwaps: {u.get('swaps_done',0)}\n"
        f"Points: {u.get('points',0)}\nBanned: {'Yes 🚫' if u.get('banned') else 'No ✅'}\n"
        f"Reports: {u.get('reports',0)}\nJoined: {u.get('joined','?')}\n\n{swap_info}",
        parse_mode="Markdown"
    )

async def admin_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    msg = " ".join(ctx.args) if ctx.args else ""
    if not msg: await update.message.reply_text("Usage: /broadcast <message>"); return
    users = fb_get("users") or {}; sent = 0
    for uid in users:
        try:
            await ctx.bot.send_message(
                chat_id=int(uid),
                text=f"📢 *SeatSwap Announcement*\n\n{msg}",
                parse_mode="Markdown"
            ); sent += 1
        except: pass
    await update.message.reply_text(f"✅ Sent to *{sent}/{len(users)}* users.", parse_mode="Markdown")

async def admin_deleteswap(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not ctx.args:
        await update.message.reply_text("Usage: /deleteswap <user_id>"); return
    uid = int(ctx.args[0]); deleted = del_my_swap(uid)
    await update.message.reply_text(f"{'✅ Deleted' if deleted else '❌ No active swap'} for user `{uid}`.", parse_mode="Markdown")

# ═══════════════════════════════════════════════════════
#  MESSAGE ROUTER  (state machine)
# ═══════════════════════════════════════════════════════
ALL_MENU_LABELS = set()
for lm in LANG_MENU.values():
    ALL_MENU_LABELS.update(lm.values())

async def handle_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text.strip()
    uid = update.effective_user.id
    flow = ctx.user_data.get("flow","")

    # Menu labels detection (all languages)
    if any(k in text for k in ["Change Seat","सीट बदलें","সিট বদলান","سیٹ بدلیں"]): await cs_start(update,ctx); return
    if any(k in text for k in ["Find Seat","सीट खोजें","সিট খুঁজুন","سیٹ تلاش"]): await find_start(update,ctx); return
    if any(k in text for k in ["My Request","मेरा अनुरोध","আমার অনুরোধ","میری درخواست"]): await my_request(update,ctx); return
    if any(k in text for k in ["Profile","प्रोफ़ाइल","প্রোফাইল","پروفائل"]): await profile(update,ctx); return
    if any(k in text for k in ["Language","भाषा","ভাষা","زبان"]): await choose_lang(update,ctx); return
    if any(k in text for k in ["Help","मदद","সাহায্য","مدد"]): await help_cmd(update,ctx); return
    if any(k in text for k in ["Feedback","फ़ीडबैक","ফিডব্যাক","فیڈبیک"]): await feedback_start(update,ctx); return

    # Flow-based routing
    if   flow == "cs_train":      await cs_got_train(update, ctx)
    elif flow == "cs_cseat":      await cs_got_cseat(update, ctx)
    elif flow == "cs_wseat_num":  await cs_got_wseat_num(update, ctx)
    elif flow == "cs_pnr":        await cs_got_pnr(update, ctx)
    elif flow == "find_train":    await find_got_train(update, ctx)
    elif flow == "feedback":      await feedback_got_msg(update, ctx)
    else:
        lang = ulang(uid)
        await update.message.reply_text("👇 Use the menu below:", reply_markup=kb_menu(lang))

# ═══════════════════════════════════════════════════════
#  CALLBACK ROUTER
# ═══════════════════════════════════════════════════════
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = update.callback_query.data
    uid  = update.effective_user.id
    lang = ulang(uid)

    if   data == "home":           await start(update, ctx)
    elif data == "change_seat":    await cs_start(update, ctx)
    elif data == "find_seat":      await find_start(update, ctx)
    elif data == "cancel_req":     await cancel_req(update, ctx)

    # Train confirm
    elif data == "cs_train_ok":
        ps = ctx.user_data["cs"]
        ctx.user_data["flow"] = "cs_ct"
        await update.callback_query.edit_message_text(
            s("step_coach_type",lang,num=ps["train"],name=ps["train_name"]),
            reply_markup=kb_ct(), parse_mode="Markdown")
    elif data == "cs_train_retry":
        ctx.user_data["flow"] = "cs_train"
        await update.callback_query.edit_message_text(s("step_train",lang), reply_markup=kb_cancel(), parse_mode="Markdown")

    # Coach type
    elif data.startswith("ct_"):   await cs_got_ct(update, ctx)
    elif data == "back_ct":
        ctx.user_data["flow"] = "cs_ct"
        ps = ctx.user_data.get("cs",{})
        await update.callback_query.edit_message_text(
            s("step_coach_type",lang,num=ps.get("train",""),name=ps.get("train_name","")),
            reply_markup=kb_ct(), parse_mode="Markdown")
    elif data.startswith("cn_"):   await cs_got_coach(update, ctx)

    # Current seat confirm
    elif data == "cs_cseat_ok":
        ctx.user_data["flow"] = "cs_wseat_num"
        await update.callback_query.edit_message_text(s("step_want_seat",lang), reply_markup=kb_any_seat(lang), parse_mode="Markdown")
    elif data == "cs_cseat_retry":
        ct = ctx.user_data.get("cs",{}).get("ct","SL")
        mx = COACH_TYPES.get(ct,{}).get("max_seat",72)
        ctx.user_data["flow"] = "cs_cseat"
        await update.callback_query.edit_message_text(
            s("step_cur_seat",lang,ct=ct,max=mx),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back_ct")]]),
            parse_mode="Markdown")

    # Wanted seat
    elif data == "wseat_any":      await cs_wseat_any(update, ctx)

    # Wanted berth
    elif data.startswith("wb_") and data != "wb_back":
        await cs_got_wberth(update, ctx)
    elif data == "wb_back":
        ctx.user_data["flow"] = "cs_wseat_num"
        await update.callback_query.edit_message_text(s("step_want_seat",lang), reply_markup=kb_any_seat(lang), parse_mode="Markdown")

    # PNR
    elif data == "pnr_skip":       await cs_pnr_skip(update, ctx)

    # View coach
    elif data.startswith("vc_"):   await show_coach(update, ctx)

    # Confirm / report
    elif data.startswith("confirm_"): await confirm_swap(update, ctx)
    elif data.startswith("report_"):  await report_user(update, ctx)

    # Language
    elif data.startswith("lang_"):    await set_lang(update, ctx)

    else:
        try: await update.callback_query.edit_message_text("⚠️ Error. Returning...", reply_markup=kb_home())
        except: pass

# ═══════════════════════════════════════════════════════
#  ERROR HANDLER
# ═══════════════════════════════════════════════════════
async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    print(f"❌ Error: {ctx.error}")
    try:
        if isinstance(update, Update):
            uid = update.effective_user.id if update.effective_user else 0
            lang = ulang(uid) if uid else "en"
            if update.callback_query:
                try: await update.callback_query.edit_message_text("⚠️ Something went wrong. Returning to menu.", reply_markup=kb_home())
                except: pass
            elif update.message:
                await update.message.reply_text("⚠️ Something went wrong. Use the menu below:", reply_markup=kb_menu(lang))
    except: pass

# ═══════════════════════════════════════════════════════
#  BOT COMMANDS SETUP
# ═══════════════════════════════════════════════════════
async def post_init(app):
    cmds = [
        BotCommand("start",       "🏠 Home / Main Menu"),
        BotCommand("myrequest",   "📋 My active seat request"),
        BotCommand("profile",     "👤 My profile & badges"),
        BotCommand("language",    "🌐 Change language"),
        BotCommand("feedback",    "💬 Send feedback to admin"),
        BotCommand("myid",        "🔑 Get my Telegram ID"),
        BotCommand("cancel",      "❌ Cancel current action"),
        BotCommand("help",        "❓ How to use SeatSwap"),
    ]
    await app.bot.set_my_commands(cmds)
    try: await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except: pass
    print("✅ Bot commands registered")

# ═══════════════════════════════════════════════════════
#  APP SETUP
# ═══════════════════════════════════════════════════════
app = (ApplicationBuilder()
       .token(BOT_TOKEN)
       .post_init(post_init)
       .build())

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
app.add_handler(CallbackQueryHandler(button_handler))

app.add_handler(CommandHandler("start",        start))
app.add_handler(CommandHandler("myrequest",    my_request))
app.add_handler(CommandHandler("profile",      profile))
app.add_handler(CommandHandler("language",     choose_lang))
app.add_handler(CommandHandler("feedback",     feedback_start))
app.add_handler(CommandHandler("myid",         my_id))
app.add_handler(CommandHandler("cancel",       cancel_req))
app.add_handler(CommandHandler("help",         help_cmd))

# Admin
app.add_handler(CommandHandler("stats",        admin_stats))
app.add_handler(CommandHandler("allusers",     admin_allusers))
app.add_handler(CommandHandler("activeusers",  admin_activeusers))
app.add_handler(CommandHandler("totalswaps",   admin_totalswaps))
app.add_handler(CommandHandler("feedbacks",    admin_feedbacks))
app.add_handler(CommandHandler("checkdb",      admin_checkdb))
app.add_handler(CommandHandler("givebadge",    admin_givebadge))
app.add_handler(CommandHandler("removebadge",  admin_removebadge))
app.add_handler(CommandHandler("viewbadge",    admin_viewbadge))
app.add_handler(CommandHandler("setfamily",    admin_setfamily))
app.add_handler(CommandHandler("ban",          admin_ban))
app.add_handler(CommandHandler("unban",        admin_unban))
app.add_handler(CommandHandler("userinfo",     admin_userinfo))
app.add_handler(CommandHandler("broadcast",    admin_broadcast))
app.add_handler(CommandHandler("deleteswap",   admin_deleteswap))

app.add_error_handler(error_handler)

print("🚆 SeatSwap Bot starting...")
app.run_polling(allowed_updates=Update.ALL_TYPES)
