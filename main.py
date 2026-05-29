import os, json, uuid, re
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, BotCommand,
    MenuButtonCommands, ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    ContextTypes, MessageHandler,
    CallbackQueryHandler, filters,
)
import firebase_admin
from firebase_admin import credentials, db

# ═══════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════
BOT_TOKEN  = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_IDS  = [int(x) for x in os.getenv("ADMIN_IDS","0").split(",") if x.strip().isdigit()]
ADMIN_UNAMES = [x.strip().lower().lstrip("@") for x in os.getenv("ADMIN_USERNAMES","").split(",") if x.strip()]

# ═══════════════════════════════════════════
#  FIREBASE
# ═══════════════════════════════════════════
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
            "boot":   datetime.now().strftime("%d %b %Y %I:%M %p"),
        })
        FIREBASE_ON = True
        print("✅ Firebase OK")
    else:
        print("⚠️  No FIREBASE_KEY")
except Exception as e:
    print(f"❌ Firebase: {e}")

# ═══════════════════════════════════════════
#  TRAIN DATABASE  (300+ trains)
# ═══════════════════════════════════════════
TRAINS = {
    # ── Rajdhani ──
    "12301":"Howrah Rajdhani Express","12302":"New Delhi Rajdhani Express",
    "12305":"Howrah Rajdhani (via Patna)","12306":"Howrah Rajdhani (via Patna)",
    "12309":"Rajendra Nagar Rajdhani","12310":"Rajendra Nagar Rajdhani",
    "12313":"Sealdah Rajdhani Express","12314":"Sealdah Rajdhani Express",
    "12423":"Dibrugarh Rajdhani","12424":"Dibrugarh Rajdhani",
    "12431":"Trivandrum Rajdhani","12432":"Trivandrum Rajdhani",
    "12433":"NZM Rajdhani Express","12434":"NZM Rajdhani Express",
    "12951":"Mumbai Rajdhani Express","12952":"New Delhi Rajdhani Express",
    "12953":"August Kranti Rajdhani","12954":"August Kranti Rajdhani",
    "22691":"Rajdhani Express","22692":"Rajdhani Express",
    "20503":"Agartala Rajdhani","20504":"Agartala Rajdhani",
    # ── Shatabdi ──
    "12001":"Bhopal Shatabdi Express","12002":"Bhopal Shatabdi Express",
    "12003":"Lucknow Shatabdi Express","12004":"Lucknow Shatabdi Express",
    "12009":"Mumbai Shatabdi Express","12010":"Mumbai Shatabdi Express",
    "12011":"Kalka Shatabdi Express","12012":"Kalka Shatabdi Express",
    "12013":"Amritsar Shatabdi","12014":"Amritsar Shatabdi",
    "12015":"Ajmer Shatabdi Express","12016":"Ajmer Shatabdi Express",
    "12017":"Howrah Shatabdi Express","12018":"Howrah Shatabdi Express",
    "12019":"Howrah Shatabdi Express","12020":"Howrah Shatabdi Express",
    "12025":"Pune Shatabdi Express","12026":"Pune Shatabdi Express",
    "12031":"Amritsar Shatabdi","12032":"Amritsar Shatabdi",
    "12033":"Kanpur Shatabdi","12034":"Kanpur Shatabdi",
    "12035":"Mysore Shatabdi","12036":"Mysore Shatabdi",
    "12037":"NZM Shatabdi","12038":"NZM Shatabdi",
    "12041":"NJP Shatabdi","12042":"NJP Shatabdi",
    # ── Duronto ──
    "12213":"Yesvantpur Duronto","12214":"Yesvantpur Duronto",
    "12219":"Secunderabad Duronto","12220":"Secunderabad Duronto",
    "12221":"Pune Duronto","12222":"Pune Duronto",
    "12225":"NZM Duronto Express","12226":"NZM Duronto Express",
    "12227":"Indore Duronto","12228":"Indore Duronto",
    "12229":"Lucknow Duronto","12230":"Lucknow Duronto",
    "12259":"Sealdah Duronto Express","12260":"Sealdah Duronto Express",
    "12269":"Chennai Duronto","12270":"Chennai Duronto",
    # ── Vande Bharat ──
    "22435":"Varanasi Vande Bharat","22436":"Varanasi Vande Bharat",
    "22439":"Amb Andaura Vande Bharat","22440":"Amb Andaura Vande Bharat",
    "20901":"Mumbai Ahmedabad Vande Bharat","20902":"Ahmedabad Mumbai Vande Bharat",
    "20903":"Gandhinagar Vande Bharat","20904":"Gandhinagar Vande Bharat",
    "06001":"Chennai Coimbatore Vande Bharat","06002":"Coimbatore Chennai Vande Bharat",
    "20951":"Kasaragod Vande Bharat","20952":"Kasaragod Vande Bharat",
    # ── Garib Rath ──
    "12203":"Garib Rath Express","12204":"Garib Rath Express",
    "12209":"Mumbai Garib Rath","12210":"Mumbai Garib Rath",
    "12215":"Garib Rath Express","12216":"Garib Rath Express",
    # ── Humsafar ──
    "12501":"Porbandar Humsafar","12502":"Porbandar Humsafar",
    "22501":"Northeast Express Humsafar","22502":"Northeast Express Humsafar",
    "20903":"Humsafar Express","20904":"Humsafar Express",
    # ── Tejas ──
    "82501":"Lucknow Tejas Express","82502":"Lucknow Tejas Express",
    "82901":"Mumbai Tejas Express","82902":"Mumbai Tejas Express",
    # ── Kolkata / Howrah ──
    "12303":"Poorva Express","12304":"Poorva Express",
    "12307":"Jodhpur Express","12308":"Jodhpur Express",
    "12311":"Howrah Kalka Mail","12312":"Kalka Howrah Mail",
    "12315":"Annanya Express","12316":"Annanya Express",
    "12321":"Howrah Mumbai Express","12322":"Mumbai Howrah Express",
    "12335":"Bhagalpur Express","12336":"Bhagalpur Express",
    "12337":"Shantiniketan Express","12338":"Shantiniketan Express",
    "12339":"Howrah Patna Express","12340":"Patna Howrah Express",
    "12343":"Darjeeling Mail","12344":"Darjeeling Mail",
    "12345":"Saraighat Express","12346":"Saraighat Express",
    "12349":"Rajendra Nagar Express","12350":"Rajendra Nagar Express",
    "12381":"Poorabh Express","12382":"Poorabh Express",
    "13005":"Howrah Amritsar Express","13006":"Amritsar Howrah Express",
    "13007":"Udyan Abha Toofan Express","13008":"Udyan Abha Toofan Express",
    "13009":"Doon Express","13010":"Doon Express",
    "13011":"Mldt Express","13012":"Mldt Express",
    "13019":"Bagh Express","13020":"Bagh Express",
    "13025":"Howrah Bandra Express","13026":"Bandra Howrah Express",
    "13027":"Howrah Azimabad Express","13028":"Azimabad Howrah Express",
    "13029":"Patna Express","13030":"Patna Express",
    "13049":"Amritsar Express","13050":"Amritsar Express",
    "13151":"Kolkata Jammu Tawi Express","13152":"Jammu Kolkata Express",
    # ── Mumbai / Western ──
    "12101":"Jnaneshwari Super Deluxe","12102":"Jnaneshwari Super Deluxe",
    "12123":"Deccan Queen Express","12124":"Deccan Queen Express",
    "12125":"Pragati Express","12126":"Pragati Express",
    "12127":"Intercity Express","12128":"Intercity Express",
    "12129":"Azad Hind Express","12130":"Azad Hind Express",
    "12137":"Punjab Mail","12138":"Punjab Mail",
    "12139":"Sewagram Express","12140":"Sewagram Express",
    "12141":"LTT Patliputra Express","12142":"Patliputra LTT Express",
    "12145":"Pawan Express","12146":"Pawan Express",
    "12147":"Konkan Kanya Express","12148":"Konkan Kanya Express",
    "12149":"Pune Danapur Express","12150":"Danapur Pune Express",
    # ── Delhi / Northern ──
    "12001":"Bhopal Shatabdi","12002":"Bhopal Shatabdi",
    "12231":"Lucknow Rajdhani","12232":"Lucknow Rajdhani",
    "12461":"Mandore Express","12462":"Mandore Express",
    "12471":"Swaraj Express","12472":"Swaraj Express",
    "12473":"Sarvodaya Express","12474":"Sarvodaya Express",
    "14001":"Sadbhavana Express","14002":"Sadbhavana Express",
    "14003":"Lichchhivi Express","14004":"Lichchhivi Express",
    "14033":"Jammu Mail","14034":"Jammu Mail",
    "14035":"Daulatpur Chowk Express","14036":"Daulatpur Chowk Express",
    "14055":"Brahmaputra Mail","14056":"Brahmaputra Mail",
    "14715":"Tiruchirappalli Express","14716":"Tiruchirappalli Express",
    # ── South India ──
    "12601":"Mangalore Express","12602":"Mangalore Express",
    "12603":"Hyderabad Express","12604":"Hyderabad Express",
    "12605":"Pallavan Express","12606":"Pallavan Express",
    "12615":"Grand Trunk Express","12616":"Grand Trunk Express",
    "12617":"Mangala Lakshadweep Express","12618":"Mangala Lakshadweep Express",
    "12621":"Tamil Nadu Express","12622":"Tamil Nadu Express",
    "12627":"Karnataka Express","12628":"Karnataka Express",
    "12631":"Nellai Express","12632":"Nellai Express",
    "12633":"Kanyakumari Express","12634":"Kanyakumari Express",
    "12639":"Brindavan Express","12640":"Brindavan Express",
    "12641":"Thirukkural Express","12642":"Thirukkural Express",
    "12657":"Chennai Mail","12658":"Chennai Mail",
    "16001":"Mettupalayam Express","16002":"Mettupalayam Express",
    "16003":"Rameswaram Express","16004":"Rameswaram Express",
    "16031":"Andaman Express","16032":"Andaman Express",
    "16317":"Himsagar Express","16318":"Himsagar Express",
    "12163":"Chennai Express","12164":"Chennai Express",
    # ── East / Northeast ──
    "12505":"Northeast Express","12506":"Northeast Express",
    "12507":"Trivandrum Express","12508":"Trivandrum Express",
    "12509":"Guwahati Express","12510":"Guwahati Express",
    "12515":"Guwahati Express","12516":"Guwahati Express",
    "12517":"Garib Rath Express","12518":"Garib Rath Express",
    "15631":"Barmer Guwahati Express","15632":"Guwahati Barmer Express",
    "15633":"Guwahati Express","15634":"Guwahati Express",
    "15647":"Guwahati Express","15648":"Guwahati Express",
    # ── Sampark Kranti ──
    "12239":"Begampura Sampark Kranti","12240":"Begampura Sampark Kranti",
    "12241":"Muzaffarpur Sampark Kranti","12242":"Muzaffarpur Sampark Kranti",
    "12243":"Coimbatore Sampark Kranti","12244":"Coimbatore Sampark Kranti",
    "12245":"Howrah Yuva Express","12246":"Howrah Yuva Express",
    # ── Special / Popular ──
    "12557":"Sapt Kranti Express","12558":"Sapt Kranti Express",
    "12559":"Shiv Ganga Express","12560":"Shiv Ganga Express",
    "12561":"Swatantrata Senani SF","12562":"Swatantrata Senani SF",
    "12569":"Jaynagar Express","12570":"Jaynagar Express",
    "12581":"Manduadih Express","12582":"Manduadih Express",
    "12801":"Purushottam Express","12802":"Purushottam Express",
    "12875":"Neelachal Express","12876":"Neelachal Express",
    "12879":"Howrah Pondicherry Express","12880":"Pondicherry Howrah Express",
    "12881":"Garib Rath Express","12882":"Garib Rath Express",
    "22823":"Bhubaneswar Rajdhani","22824":"Bhubaneswar Rajdhani",
    "22825":"Shalimar Rajdhani","22826":"Shalimar Rajdhani",
    "12969":"Porbandar Express","12970":"Porbandar Express",
    "11059":"Chhattisgarh Express","11060":"Chhattisgarh Express",
    "11061":"LTT Jabalpur Express","11062":"Jabalpur LTT Express",
    "11071":"Kamayani Express","11072":"Kamayani Express",
    "11077":"Jhelum Express","11078":"Jhelum Express",
    "11079":"Maurya Express","11080":"Maurya Express",
    "11081":"LTT Gwalior Express","11082":"Gwalior LTT Express",
    "12187":"Garib Nawaz Express","12188":"Garib Nawaz Express",
    "12191":"Shridham Express","12192":"Shridham Express",
    "12193":"Yelahanka Express","12194":"Yelahanka Express",
}

# ═══════════════════════════════════════════
#  COACH & SEAT SYSTEM
# ═══════════════════════════════════════════
COACH_TYPES = {
    "SL": {"label":"🛏 Sleeper (S1–S12)",    "max_seat":72,  "coaches":[f"S{i}" for i in range(1,13)]},
    "3A": {"label":"❄️ AC 3 Tier (B1–B6)",   "max_seat":64,  "coaches":[f"B{i}" for i in range(1,7)]},
    "2A": {"label":"❄️ AC 2 Tier (A1–A4)",   "max_seat":46,  "coaches":[f"A{i}" for i in range(1,5)]},
    "1A": {"label":"❄️ AC 1st Class (H1–H2)","max_seat":24,  "coaches":["H1","H2"]},
    "CC": {"label":"💺 Chair Car (C1–C8)",    "max_seat":78,  "coaches":[f"C{i}" for i in range(1,9)]},
    "EC": {"label":"💺 Exec Chair (EC1–EC3)", "max_seat":56,  "coaches":["EC1","EC2","EC3"]},
    "GN": {"label":"🚃 General (GS)",         "max_seat":200, "coaches":["GS1","GS2","GS3"]},
}

def seat_to_berth(seat, coach_type):
    try:
        s = int(seat)
    except:
        return "Unknown"
    if coach_type in ["SL","3A"]:
        pos = (s - 1) % 8
        return ["Lower","Middle","Upper","Lower","Middle","Upper","Side Lower","Side Upper"][pos]
    elif coach_type == "2A":
        pos = (s - 1) % 4
        return ["Lower","Upper","Lower","Upper"][pos]
    elif coach_type in ["1A","H"]:
        return "Lower" if s % 2 == 1 else "Upper"
    elif coach_type in ["CC","EC"]:
        pos = (s - 1) % 3
        return ["Window","Middle","Aisle"][pos]
    return "Seat " + str(seat)

BERTH_EMOJI = {
    "Lower":"⬇️","Middle":"➡️","Upper":"⬆️",
    "Side Lower":"↘️","Side Upper":"↗️",
    "Window":"🪟","Aisle":"🚶","Any":"🔀",
}

# ═══════════════════════════════════════════
#  BADGE SYSTEM
# ═══════════════════════════════════════════
BADGES = [(0,"🌱","Newcomer"),(3,"🎫","Regular Traveler"),
          (10,"⭐","Trusted Member"),(25,"🔰","Expert Swapper"),(50,"👑","Seat Master")]

def get_badge(n):
    b = BADGES[0]
    for lvl in BADGES:
        if n >= lvl[0]: b = lvl
    return f"{b[0]} {b[2]}"

def progress_bar(n):
    cur = BADGES[0]; nxt = None
    for i,lvl in enumerate(BADGES):
        if n >= lvl[0]: cur=lvl; nxt=BADGES[i+1] if i+1<len(BADGES) else None
    if not nxt: return "👑 *Maximum badge reached!*"
    done=n-cur[0]; need=nxt[0]-cur[0]; f=int((done/need)*10)
    return f"`[{'█'*f}{'░'*(10-f)}]` {done}/{need}  _{nxt[0]-n} more → {nxt[0]} {nxt[2]}_"

# ═══════════════════════════════════════════
#  TRANSLATIONS  (EN / HI / BN / UR)
# ═══════════════════════════════════════════
T = {
"welcome":{
    "en":"🚆 *SeatSwap*\n\nHey *{name}*! 👋\nExchange your train berth instantly.\n\n🔄 Post swap  |  🔍 Find swap\n🤝 Get matched  |  🏅 Earn badges",
    "hi":"🚆 *SeatSwap*\n\nनमस्ते *{name}*! 👋\nट्रेन की सीट तुरंत बदलें।\n\n🔄 स्वैप पोस्ट करें  |  🔍 खोजें\n🤝 मैच पाएं  |  🏅 बैज कमाएं",
    "bn":"🚆 *SeatSwap*\n\nনমস্কার *{name}*! 👋\nট্রেনের বার্থ এখনই বদলান।\n\n🔄 স্বাপ পোস্ট  |  🔍 খুঁজুন\n🤝 ম্যাচ পান  |  🏅 ব্যাজ অর্জন",
    "ur":"🚆 *SeatSwap*\n\nہیلو *{name}*! 👋\nٹرین کی سیٹ فوری بدلیں۔\n\n🔄 سویپ پوسٹ  |  🔍 تلاش کریں\n🤝 میچ پائیں  |  🏅 بیج کمائیں",
},
"choose_lang":{
    "en":"🌐 *Choose your language:*",
    "hi":"🌐 *अपनी भाषा चुनें:*",
    "bn":"🌐 *আপনার ভাষা বেছে নিন:*",
    "ur":"🌐 *اپنی زبان چنیں:*",
},
"enter_train":{
    "en":"📝 *Step 1/5 — Train Number*\n\nEnter your *train number*:\n_(Example: `12345`, `12301`)_",
    "hi":"📝 *चरण 1/5 — ट्रेन नंबर*\n\nअपना *ट्रेन नंबर* दर्ज करें:\n_(उदाहरण: `12345`, `12301`)_",
    "bn":"📝 *ধাপ 1/5 — ট্রেন নম্বর*\n\nআপনার *ট্রেন নম্বর* লিখুন:\n_(উদাহরণ: `12345`, `12301`)_",
    "ur":"📝 *مرحلہ 1/5 — ٹرین نمبر*\n\nاپنا *ٹرین نمبر* درج کریں:\n_(مثال: `12345`, `12301`)_",
},
"train_found":{
    "en":"✅ Train *{num}*\n🔖 _{name}_\n\nSelect *Coach Type*:",
    "hi":"✅ ट्रेन *{num}*\n🔖 _{name}_\n\n*बोगी प्रकार* चुनें:",
    "bn":"✅ ট্রেন *{num}*\n🔖 _{name}_\n\n*কোচের ধরন* বেছে নিন:",
    "ur":"✅ ٹرین *{num}*\n🔖 _{name}_\n\n*بوگی کی قسم* منتخب کریں:",
},
"train_unknown":{
    "en":"⚠️ Train *{num}* not in our database.\nVerify the number and proceed?",
    "hi":"⚠️ ट्रेन *{num}* हमारे डेटाबेस में नहीं है।\nनंबर जांचें और आगे बढ़ें?",
    "bn":"⚠️ ট্রেন *{num}* আমাদের ডেটাবেসে নেই।\nনম্বর যাচাই করে এগিয়ে যাবেন?",
    "ur":"⚠️ ٹرین *{num}* ہمارے ڈیٹابیس میں نہیں ہے۔\nنمبر چیک کریں اور آگے بڑھیں؟",
},
"select_coach":{
    "en":"Select your *Coach* 🚉",
    "hi":"अपनी *बोगी* चुनें 🚉",
    "bn":"আপনার *কোচ* বেছে নিন 🚉",
    "ur":"اپنی *بوگی* چنیں 🚉",
},
"enter_seat":{
    "en":"📝 *Step 3/5 — Seat Number*\n\nEnter your *seat number*:\n_(For {ct}: 1–{max})_\n\n_Tip: Berth type auto-detected!_",
    "hi":"📝 *चरण 3/5 — सीट नंबर*\n\nअपना *सीट नंबर* दर्ज करें:\n_({ct} के लिए: 1–{max})_\n\n_टिप: बर्थ प्रकार अपने आप पता चलेगा!_",
    "bn":"📝 *ধাপ 3/5 — সিট নম্বর*\n\nআপনার *সিট নম্বর* লিখুন:\n_({ct} এর জন্য: 1–{max})_",
    "ur":"📝 *مرحلہ 3/5 — سیٹ نمبر*\n\nاپنا *سیٹ نمبر* درج کریں:\n_({ct} کیلیے: 1–{max})_",
},
"seat_detected":{
    "en":"✅ Seat *{seat}* → Berth: *{berth}*\n\nIs this correct?",
    "hi":"✅ सीट *{seat}* → बर्थ: *{berth}*\n\nक्या यह सही है?",
    "bn":"✅ সিট *{seat}* → বার্থ: *{berth}*\n\nএটা কি ঠিক আছে?",
    "ur":"✅ سیٹ *{seat}* → بارتھ: *{berth}*\n\nکیا یہ درست ہے؟",
},
"seat_invalid":{
    "en":"❌ Invalid seat. For {ct}: enter 1–{max}",
    "hi":"❌ गलत सीट नंबर। {ct} के लिए: 1–{max} दर्ज करें",
    "bn":"❌ ভুল সিট নম্বর। {ct} এর জন্য: 1–{max} লিখুন",
    "ur":"❌ غلط سیٹ نمبر۔ {ct} کیلیے: 1–{max} درج کریں",
},
"select_wanted":{
    "en":"📝 *Step 4/5 — Wanted Berth*\n\nWhich berth do you *want*? 🔄",
    "hi":"📝 *चरण 4/5 — चाहिए बर्थ*\n\nआप कौनसी बर्थ *चाहते हैं*? 🔄",
    "bn":"📝 *ধাপ 4/5 — পছন্দের বার্থ*\n\nআপনি কোন বার্থ *চান*? 🔄",
    "ur":"📝 *مرحلہ 4/5 — مطلوبہ بارتھ*\n\nآپ کون سی بارتھ *چاہتے ہیں*؟ 🔄",
},
"enter_pnr":{
    "en":"📝 *Step 5/5 — PNR (Optional)*\n\nEnter your *10-digit PNR* for trust verification,\nor tap *Skip*:",
    "hi":"📝 *चरण 5/5 — PNR (वैकल्पिक)*\n\nविश्वास के लिए *10-अंकीय PNR* दर्ज करें,\nया *छोड़ें* दबाएं:",
    "bn":"📝 *ধাপ 5/5 — PNR (ঐচ্ছিক)*\n\nবিশ্বাসের জন্য *10-সংখ্যার PNR* লিখুন,\nঅথবা *এড়িয়ে যান* চাপুন:",
    "ur":"📝 *مرحلہ 5/5 — PNR (اختیاری)*\n\nاعتماد کیلیے *10 ہندسی PNR* درج کریں,\nیا *چھوڑیں* دبائیں:",
},
"pnr_invalid":{
    "en":"❌ PNR must be 10 digits. Try again or tap Skip:",
    "hi":"❌ PNR 10 अंकों का होना चाहिए। फिर दर्ज करें या छोड़ें:",
    "bn":"❌ PNR 10 সংখ্যার হতে হবে। আবার চেষ্টা করুন বা এড়িয়ে যান:",
    "ur":"❌ PNR 10 ہندسی ہونا چاہیے۔ دوبارہ کوشش کریں یا چھوڑیں:",
},
"swap_posted":{
    "en":"✅ *Swap Posted!*\n\n🚆 Train: *{train}* _{tname}_\n🚉 Coach: *{coach}*  Seat: *{seat}*\n💺 Has: *{cur}*  →  🔄 Wants: *{want}*\n{pnr_line}\n🔔 You'll be notified when a match is found!",
    "hi":"✅ *स्वैप पोस्ट हो गया!*\n\n🚆 ट्रेन: *{train}* _{tname}_\n🚉 बोगी: *{coach}*  सीट: *{seat}*\n💺 है: *{cur}*  →  🔄 चाहिए: *{want}*\n{pnr_line}\n🔔 मैच मिलने पर सूचना मिलेगी!",
    "bn":"✅ *স্বাপ পোস্ট হয়েছে!*\n\n🚆 ট্রেন: *{train}* _{tname}_\n🚉 কোচ: *{coach}*  সিট: *{seat}*\n💺 আছে: *{cur}*  →  🔄 চাই: *{want}*\n{pnr_line}\n🔔 ম্যাচ পেলে জানানো হবে!",
    "ur":"✅ *سویپ پوسٹ ہو گئی!*\n\n🚆 ٹرین: *{train}* _{tname}_\n🚉 بوگی: *{coach}*  سیٹ: *{seat}*\n💺 ہے: *{cur}*  →  🔄 چاہیے: *{want}*\n{pnr_line}\n🔔 میچ ملنے پر اطلاع ملے گی!",
},
"match_found":{
    "en":"🎉 *INSTANT MATCH FOUND!*\n\n👤 *{name}* {badge}\n🚉 Coach: *{coach}*  Seat: *{seat}*\n💺 Has: *{cur}*  →  🔄 Wants: *{want}*\n📩 Contact: {contact}\n\n_After swap, tap ✅ Confirm to earn +10 pts!_",
    "hi":"🎉 *तुरंत मैच मिला!*\n\n👤 *{name}* {badge}\n🚉 बोगी: *{coach}*  सीट: *{seat}*\n💺 है: *{cur}*  →  🔄 चाहिए: *{want}*\n📩 संपर्क: {contact}\n\n_स्वैप के बाद ✅ Confirm दबाएं → +10 pts!_",
    "bn":"🎉 *তাৎক্ষণিক ম্যাচ পাওয়া গেছে!*\n\n👤 *{name}* {badge}\n🚉 কোচ: *{coach}*  সিট: *{seat}*\n💺 আছে: *{cur}*  →  🔄 চাই: *{want}*\n📩 যোগাযোগ: {contact}\n\n_বদলের পর ✅ Confirm চাপুন → +10 pts!_",
    "ur":"🎉 *فوری میچ مل گیا!*\n\n👤 *{name}* {badge}\n🚉 بوگی: *{coach}*  سیٹ: *{seat}*\n💺 ہے: *{cur}*  →  🔄 چاہیے: *{want}*\n📩 رابطہ: {contact}\n\n_تبادلے کے بعد ✅ Confirm دبائیں → +10 pts!_",
},
"no_match":{
    "en":"🔔 Request is *live*! We'll notify you when a match is found.",
    "hi":"🔔 आपका अनुरोध *लाइव* है! मैच मिलने पर सूचना मिलेगी।",
    "bn":"🔔 অনুরোধ *লাইভ*! ম্যাচ পেলে জানানো হবে।",
    "ur":"🔔 درخواست *لائیو* ہے! میچ ملنے پر اطلاع ملے گی۔",
},
"search_enter_train":{
    "en":"🔍 *Find Swap*\n\nEnter *train number* to search:",
    "hi":"🔍 *स्वैप खोजें*\n\n*ट्रेन नंबर* दर्ज करें:",
    "bn":"🔍 *স্বাপ খুঁজুন*\n\n*ট্রেন নম্বর* লিখুন:",
    "ur":"🔍 *سویپ تلاش کریں*\n\n*ٹرین نمبر* درج کریں:",
},
"no_swaps":{
    "en":"😔 No active swaps for *Train {train}*.\nPost yours first!",
    "hi":"😔 ट्रेन *{train}* के लिए कोई स्वैप नहीं।\nपहले अपना पोस्ट करें!",
    "bn":"😔 ট্রেন *{train}* এর জন্য কোনো স্বাপ নেই।\nআগে আপনারটা পোস্ট করুন!",
    "ur":"😔 ٹرین *{train}* کیلیے کوئی سویپ نہیں۔\nپہلے اپنا پوسٹ کریں!",
},
"no_request":{
    "en":"📋 You have no active request.",
    "hi":"📋 आपका कोई सक्रिय अनुरोध नहीं है।",
    "bn":"📋 আপনার কোনো সক্রিয় অনুরোধ নেই।",
    "ur":"📋 آپ کی کوئی فعال درخواست نہیں ہے۔",
},
"request_cancelled":{
    "en":"✅ Your swap request has been removed.",
    "hi":"✅ आपका स्वैप अनुरोध हटा दिया गया।",
    "bn":"✅ আপনার স্বাপ অনুরোধ সরানো হয়েছে।",
    "ur":"✅ آپ کی سویپ درخواست ہٹا دی گئی۔",
},
"confirmed":{
    "en":"🎉 *Swap Confirmed!*\n\n+10 pts  |  Total: *{pts}* pts\nBadge: *{badge}*\n\n{bar}",
    "hi":"🎉 *स्वैप पुष्टि हो गया!*\n\n+10 pts  |  कुल: *{pts}* pts\nबैज: *{badge}*\n\n{bar}",
    "bn":"🎉 *সওয়াপ নিশ্চিত!*\n\n+10 pts  |  মোট: *{pts}* pts\nব্যাজ: *{badge}*\n\n{bar}",
    "ur":"🎉 *سویپ کنفرم!*\n\n+10 pts  |  کل: *{pts}* pts\nبیج: *{badge}*\n\n{bar}",
},
"help":{
    "en":(
        "❓ *How to use SeatSwap*\n\n"
        "1️⃣ Tap *🔄 Post Swap* → enter train no → pick coach → enter seat no → pick wanted berth → PNR (optional)\n\n"
        "2️⃣ Tap *🔍 Find Swap* → enter train no → pick coach → see all swaps + contact button\n\n"
        "3️⃣ After swap → tap *✅ Confirm* → earn +10 points!\n\n"
        "🚩 Report fake users → 3 reports = auto ban\n\n"
        "🏅 *Badges:*\n"
        "🌱 Newcomer (0)  🎫 Regular (3+)\n"
        "⭐ Trusted (10+)  🔰 Expert (25+)  👑 Master (50+)"
    ),
    "hi":(
        "❓ *SeatSwap का उपयोग कैसे करें*\n\n"
        "1️⃣ *🔄 Post Swap* दबाएं → ट्रेन नंबर → बोगी → सीट नंबर → चाहिए बर्थ → PNR (वैकल्पिक)\n\n"
        "2️⃣ *🔍 Find Swap* दबाएं → ट्रेन नंबर → बोगी → सभी स्वैप देखें\n\n"
        "3️⃣ स्वैप के बाद *✅ Confirm* दबाएं → +10 पॉइंट!\n\n"
        "🚩 फर्जी यूजर को रिपोर्ट करें → 3 रिपोर्ट = ऑटो बैन\n\n"
        "🏅 *बैज:* 🌱 नया (0)  🎫 नियमित (3+)\n"
        "⭐ विश्वसनीय (10+)  🔰 विशेषज्ञ (25+)  👑 मास्टर (50+)"
    ),
    "bn":(
        "❓ *SeatSwap কিভাবে ব্যবহার করবেন*\n\n"
        "1️⃣ *🔄 Post Swap* → ট্রেন নম্বর → কোচ → সিট নম্বর → পছন্দের বার্থ → PNR (ঐচ্ছিক)\n\n"
        "2️⃣ *🔍 Find Swap* → ট্রেন নম্বর → কোচ → সব স্বাপ দেখুন\n\n"
        "3️⃣ বদলের পর *✅ Confirm* → +10 পয়েন্ট!\n\n"
        "🏅 *ব্যাজ:* 🌱 নতুন  🎫 নিয়মিত (3+)\n"
        "⭐ বিশ্বস্ত (10+)  🔰 বিশেষজ্ঞ (25+)  👑 মাস্টার (50+)"
    ),
    "ur":(
        "❓ *SeatSwap استعمال کا طریقہ*\n\n"
        "1️⃣ *🔄 Post Swap* → ٹرین نمبر → بوگی → سیٹ نمبر → مطلوبہ بارتھ → PNR (اختیاری)\n\n"
        "2️⃣ *🔍 Find Swap* → ٹرین نمبر → بوگی → تمام سویپ دیکھیں\n\n"
        "3️⃣ تبادلے کے بعد *✅ Confirm* → +10 پوائنٹ!\n\n"
        "🏅 *بیج:* 🌱 نیا  🎫 باقاعدہ (3+)\n"
        "⭐ قابل اعتماد (10+)  🔰 ماہر (25+)  👑 ماسٹر (50+)"
    ),
},
}

def t(key, lang="en", **kw):
    text = T.get(key,{}).get(lang) or T.get(key,{}).get("en","")
    return text.format(**kw) if kw else text

# ═══════════════════════════════════════════
#  FIREBASE HELPERS
# ═══════════════════════════════════════════
def fb_get(p):
    if not FIREBASE_ON: return None
    try: return db.reference(p).get()
    except: return None

def fb_set(p,d):
    if not FIREBASE_ON: return
    try: db.reference(p).set(d)
    except Exception as e: print(f"fb_set {p}: {e}")

def fb_upd(p,d):
    if not FIREBASE_ON: return
    try: db.reference(p).update(d)
    except Exception as e: print(f"fb_upd {p}: {e}")

def fb_del(p):
    if not FIREBASE_ON: return
    try: db.reference(p).delete()
    except: pass

def ensure_user(user):
    if fb_get(f"users/{user.id}"): return
    fb_set(f"users/{user.id}",{
        "name":user.first_name,"username":user.username or "",
        "lang":"en","points":0,"swaps_done":0,"badge":get_badge(0),
        "banned":False,"reports":0,"joined":datetime.now().strftime("%d %b %Y"),
    })

def get_user(uid):
    return fb_get(f"users/{uid}") or {
        "name":"User","username":"","lang":"en","points":0,
        "swaps_done":0,"badge":get_badge(0),"banned":False,"reports":0,
    }

def user_lang(uid):
    return get_user(uid).get("lang","en")

def is_banned(uid): return get_user(uid).get("banned",False)

def all_swaps(): return fb_get("swaps") or {}

def my_swap(uid):
    return next((v for v in all_swaps().values() if v.get("user_id")==uid),None)

def save_swap(user,train,tname,ct,coach,seat,cur,want,pnr):
    sid=str(uuid.uuid4())[:8]
    for k,v in all_swaps().items():
        if v.get("user_id")==user.id: fb_del(f"swaps/{k}")
    u=get_user(user.id)
    sw={
        "swap_id":sid,"user_id":user.id,
        "name":user.first_name,"username":user.username or "",
        "badge":u.get("badge",get_badge(0)),
        "train":train,"train_name":tname,"coach_type":ct,
        "coach":coach,"seat":seat,"current":cur,"wanted":want,
        "pnr":pnr or "","status":"active",
        "ts":datetime.now().strftime("%d %b %Y %I:%M %p"),
    }
    fb_set(f"swaps/{sid}",sw)
    return sw

def del_my_swap(uid):
    deleted=False
    for k,v in all_swaps().items():
        if v.get("user_id")==uid: fb_del(f"swaps/{k}"); deleted=True
    return deleted

def find_match(sw):
    opp={"lower":["upper","middle"],"upper":["lower","middle"],"middle":["lower","upper"],
         "side lower":["side upper"],"side upper":["side lower"]}
    nw=sw["wanted"].lower(); nc=sw["current"].lower()
    for k,s in all_swaps().items():
        if s.get("user_id")==sw["user_id"]: continue
        if s.get("train")  !=sw["train"]:   continue
        tw=s.get("wanted","").lower(); tc=s.get("current","").lower()
        if tw==nc or tw in opp.get(nc,[]) or nw==tc or nw in opp.get(tc,[]): return s
    return None

def award(uid):
    u=get_user(uid); sd=u.get("swaps_done",0)+1; pt=u.get("points",0)+10
    fb_upd(f"users/{uid}",{"swaps_done":sd,"points":pt,"badge":get_badge(sd)})
    return sd,pt

def contact_link(req):
    return f"@{req['username']}" if req.get("username") else f"[{req['name']}](tg://user?id={req['user_id']})"

def time_ago(ts):
    try:
        d=datetime.strptime(ts,"%d %b %Y %I:%M %p")
        m=int((datetime.now()-d).total_seconds()/60)
        if m<1: return "just now"
        if m<60: return f"{m}m ago"
        h=m//60
        if h<24: return f"{h}h ago"
        return f"{(datetime.now()-d).days}d ago"
    except: return ts

# ═══════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════
def kb_main_reply(lang="en"):
    lbl = {
        "en":["🔄 Post Swap","🔍 Find Swap","📋 My Request","👤 Profile","🌐 Language","❓ Help"],
        "hi":["🔄 स्वैप करें","🔍 खोजें","📋 मेरा अनुरोध","👤 प्रोफ़ाइल","🌐 भाषा","❓ मदद"],
        "bn":["🔄 পোস্ট করুন","🔍 খুঁজুন","📋 আমার অনুরোধ","👤 প্রোফাইল","🌐 ভাষা","❓ সাহায্য"],
        "ur":["🔄 پوسٹ کریں","🔍 تلاش","📋 میری درخواست","👤 پروفائل","🌐 زبان","❓ مدد"],
    }.get(lang,["🔄 Post Swap","🔍 Find Swap","📋 My Request","👤 Profile","🌐 Language","❓ Help"])
    return ReplyKeyboardMarkup([
        [lbl[0],lbl[1]],
        [lbl[2],lbl[3]],
        [lbl[4],lbl[5]],
    ], resize_keyboard=True)

def kb_back_home():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu",callback_data="flow_home")]])

def kb_coach_types():
    rows=[]
    items=list(COACH_TYPES.items())
    for i in range(0,len(items),2):
        row=[InlineKeyboardButton(v["label"],callback_data=f"ct_{k}") for k,v in items[i:i+2]]
        rows.append(row)
    rows.append([InlineKeyboardButton("🏠 Cancel",callback_data="flow_home")])
    return InlineKeyboardMarkup(rows)

def kb_coaches(coach_list):
    rows=[InlineKeyboardButton(c,callback_data=f"cn_{c}") for c in coach_list]
    grid=[rows[i:i+4] for i in range(0,len(rows),4)]
    grid.append([InlineKeyboardButton("⬅️ Back",callback_data="ps_back_ct")])
    return InlineKeyboardMarkup(grid)

def kb_berths(prefix,coach_type):
    berths=["Lower","Middle","Upper","Side Lower","Side Upper"] if coach_type in ["SL","3A"] else \
           ["Lower","Upper"] if coach_type in ["2A","1A"] else \
           ["Window","Middle","Aisle"]
    rows=[[InlineKeyboardButton(f"{BERTH_EMOJI.get(b,'🔄')} {b}",callback_data=f"{prefix}_{b}")] for b in berths]
    rows.append([InlineKeyboardButton("⬅️ Back",callback_data=f"{prefix}_back")])
    return InlineKeyboardMarkup(rows)

def kb_yes_no(yes_cb,no_cb,lang="en"):
    yes={"en":"✅ Yes","hi":"✅ हाँ","bn":"✅ হ্যাঁ","ur":"✅ ہاں"}.get(lang,"✅ Yes")
    no ={"en":"❌ No, re-enter","hi":"❌ नहीं, फिर डालें","bn":"❌ না, আবার","ur":"❌ نہیں، دوبارہ"}.get(lang,"❌ No")
    return InlineKeyboardMarkup([[InlineKeyboardButton(yes,callback_data=yes_cb),InlineKeyboardButton(no,callback_data=no_cb)]])

def kb_skip(lang="en"):
    s={"en":"⏭️ Skip","hi":"⏭️ छोड़ें","bn":"⏭️ এড়িয়ে যান","ur":"⏭️ چھوڑیں"}.get(lang,"⏭️ Skip")
    return InlineKeyboardMarkup([[InlineKeyboardButton(s,callback_data="pnr_skip")],
                                  [InlineKeyboardButton("🏠 Cancel",callback_data="flow_home")]])

def kb_confirm_swap(sid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Swap Done",callback_data=f"confirm_{sid}")],
        [InlineKeyboardButton("🏠 Main Menu",callback_data="flow_home")],
    ])

def kb_lang():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇬🇧 English",callback_data="lang_en"),
         InlineKeyboardButton("🇮🇳 हिन्दी",callback_data="lang_hi")],
        [InlineKeyboardButton("🇧🇩 বাংলা",callback_data="lang_bn"),
         InlineKeyboardButton("🇵🇰 اردو",callback_data="lang_ur")],
    ])

# ═══════════════════════════════════════════
#  REPLY HELPER
# ═══════════════════════════════════════════
async def rply(update:Update, text:str, kb=None, rm=False):
    kw=dict(text=text,parse_mode="Markdown")
    if rm: kw["reply_markup"]=ReplyKeyboardRemove()
    elif kb: kw["reply_markup"]=kb
    if update.callback_query:
        try: await update.callback_query.edit_message_text(**kw)
        except: await update.callback_query.message.reply_text(**kw)
    else:
        await update.message.reply_text(**kw)

# ═══════════════════════════════════════════
#  /START
# ═══════════════════════════════════════════
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    user=update.effective_user
    ensure_user(user)
    context.user_data.clear()
    if is_banned(user.id):
        await rply(update,"🚫 Your account has been suspended."); return
    lang=user_lang(user.id)
    db_icon="🟢" if FIREBASE_ON else "🔴"
    # Send ReplyKeyboard first (persistent menu)
    await update.effective_message.reply_text(
        t("welcome",lang,name=user.first_name)+f"\n\n_{db_icon} DB {'Online' if FIREBASE_ON else 'Offline'}_",
        reply_markup=kb_main_reply(lang), parse_mode="Markdown"
    )

# ═══════════════════════════════════════════
#  LANGUAGE FLOW
# ═══════════════════════════════════════════
async def choose_lang(update:Update,context:ContextTypes.DEFAULT_TYPE):
    lang=user_lang(update.effective_user.id)
    await rply(update,t("choose_lang",lang),kb_lang())

async def set_lang(update:Update,context:ContextTypes.DEFAULT_TYPE):
    lang=update.callback_query.data.replace("lang_","")
    uid=update.effective_user.id
    fb_upd(f"users/{uid}",{"lang":lang})
    await update.callback_query.answer()
    name_map={"en":"English 🇬🇧","hi":"हिन्दी 🇮🇳","bn":"বাংলা 🇧🇩","ur":"اردو 🇵🇰"}
    await update.callback_query.edit_message_text(
        f"✅ Language set to *{name_map.get(lang,lang)}*",
        parse_mode="Markdown",reply_markup=kb_back_home()
    )
    # Update persistent keyboard
    await update.callback_query.message.reply_text(
        "👇",reply_markup=kb_main_reply(lang)
    )

# ═══════════════════════════════════════════
#  POST SWAP FLOW  (state machine)
# ═══════════════════════════════════════════
async def ps_start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    if is_banned(uid): await rply(update,"🚫 Banned."); return
    lang=user_lang(uid)
    context.user_data.update({"flow":"ps_train","ps":{}})
    await rply(update,t("enter_train",lang),
        InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Cancel",callback_data="flow_home")]]))

async def ps_got_train(update:Update,context:ContextTypes.DEFAULT_TYPE):
    raw=update.message.text.strip()
    uid=update.effective_user.id; lang=user_lang(uid)
    if not re.match(r"^\d{4,6}$",raw):
        await update.message.reply_text(
            "❌ Train number should be 4–6 digits.\n_(Example: `12301`)_",
            parse_mode="Markdown"
        ); return
    tname=TRAINS.get(raw,"")
    context.user_data["ps"]["train"]=raw.upper()
    context.user_data["ps"]["train_name"]=tname or raw.upper()
    if tname:
        context.user_data["flow"]="ps_ct"
        await update.message.reply_text(
            t("train_found",lang,num=raw,name=tname),
            reply_markup=kb_coach_types(),parse_mode="Markdown"
        )
    else:
        context.user_data["flow"]="ps_train_confirm"
        await update.message.reply_text(
            t("train_unknown",lang,num=raw),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Proceed",callback_data="ps_train_ok"),
                 InlineKeyboardButton("❌ Re-enter",callback_data="ps_renter_train")],
            ]),parse_mode="Markdown"
        )

async def ps_ct(update:Update,context:ContextTypes.DEFAULT_TYPE):
    code=update.callback_query.data.replace("ct_","")
    await update.callback_query.answer()
    lang=user_lang(update.effective_user.id)
    context.user_data["ps"]["coach_type"]=code
    context.user_data["ps"]["ct_label"]=COACH_TYPES[code]["label"]
    context.user_data["flow"]="ps_coach"
    await update.callback_query.edit_message_text(
        f"✅ {COACH_TYPES[code]['label']}\n\n{t('select_coach',lang)} 🚉",
        reply_markup=kb_coaches(COACH_TYPES[code]["coaches"]),parse_mode="Markdown"
    )

async def ps_coach(update:Update,context:ContextTypes.DEFAULT_TYPE):
    coach=update.callback_query.data.replace("cn_","")
    await update.callback_query.answer()
    uid=update.effective_user.id; lang=user_lang(uid)
    context.user_data["ps"]["coach"]=coach
    context.user_data["flow"]="ps_seat"
    ct=context.user_data["ps"]["coach_type"]
    mx=COACH_TYPES[ct]["max_seat"]
    await update.callback_query.edit_message_text(
        f"✅ Coach: *{coach}*\n\n{t('enter_seat',lang,ct=ct,max=mx)}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="ps_back_ct")]]))

async def ps_got_seat(update:Update,context:ContextTypes.DEFAULT_TYPE):
    raw=update.message.text.strip()
    uid=update.effective_user.id; lang=user_lang(uid)
    ps=context.user_data.get("ps",{}); ct=ps.get("coach_type","SL")
    mx=COACH_TYPES.get(ct,{}).get("max_seat",72)
    if not raw.isdigit() or not (1<=int(raw)<=mx):
        await update.message.reply_text(t("seat_invalid",lang,ct=ct,max=mx),parse_mode="Markdown"); return
    berth=seat_to_berth(raw,ct)
    ps["seat"]=raw; ps["current"]=berth
    context.user_data["flow"]="ps_seat_confirm"
    await update.message.reply_text(
        t("seat_detected",lang,seat=raw,berth=berth),
        reply_markup=kb_yes_no("ps_seat_ok","ps_renter_seat",lang),parse_mode="Markdown"
    )

async def ps_wanted(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    uid=update.effective_user.id; lang=user_lang(uid)
    ct=context.user_data.get("ps",{}).get("coach_type","SL")
    context.user_data["flow"]="ps_wanted"
    await update.callback_query.edit_message_text(
        t("select_wanted",lang),
        reply_markup=kb_berths("want",ct),parse_mode="Markdown"
    )

async def ps_got_wanted(update:Update,context:ContextTypes.DEFAULT_TYPE):
    berth=update.callback_query.data.replace("want_","")
    await update.callback_query.answer()
    uid=update.effective_user.id; lang=user_lang(uid)
    context.user_data["ps"]["wanted"]=berth
    context.user_data["flow"]="ps_pnr"
    await update.callback_query.edit_message_text(
        t("enter_pnr",lang),
        reply_markup=kb_skip(lang),parse_mode="Markdown"
    )

async def ps_got_pnr(update:Update,context:ContextTypes.DEFAULT_TYPE):
    raw=update.message.text.strip()
    uid=update.effective_user.id; lang=user_lang(uid)
    if not re.match(r"^\d{10}$",raw):
        await update.message.reply_text(t("pnr_invalid",lang),
            reply_markup=kb_skip(lang),parse_mode="Markdown"); return
    context.user_data["ps"]["pnr"]=raw
    context.user_data["flow"]=""
    await finish_post(update,context,uid,lang)

async def ps_skip_pnr(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    uid=update.effective_user.id; lang=user_lang(uid)
    context.user_data["ps"]["pnr"]=""
    context.user_data["flow"]=""
    await finish_post(update,context,uid,lang)

async def finish_post(update:Update,context:ContextTypes.DEFAULT_TYPE,uid,lang):
    user=update.effective_user; ps=context.user_data.get("ps",{})
    pnr=ps.get("pnr","")
    pnr_line=f"🎫 PNR: `{pnr}`" if pnr else ""
    sw=save_swap(user,ps["train"],ps["train_name"],ps["coach_type"],
                 ps["coach"],ps["seat"],ps["current"],ps["wanted"],pnr)
    text=t("swap_posted",lang,
           train=ps["train"],tname=ps["train_name"],coach=ps["coach"],
           seat=ps["seat"],cur=ps["current"],want=ps["wanted"],pnr_line=pnr_line)
    match=find_match(sw)
    if match:
        um=get_user(match["user_id"]); cl=contact_link(match)
        text+="\n\n"+t("match_found",lang,
            name=match["name"],badge=um.get("badge",""),
            coach=match["coach"],seat=match.get("seat","?"),
            cur=match["current"],want=match["wanted"],contact=cl)
        try:
            ul=user_lang(match["user_id"]); ume=get_user(uid)
            mc=contact_link({"username":user.username,"name":user.first_name,"user_id":uid})
            await context.bot.send_message(
                chat_id=match["user_id"],parse_mode="Markdown",
                text=t("match_found",ul,
                    name=user.first_name,badge=ume.get("badge",""),
                    coach=ps["coach"],seat=ps["seat"],
                    cur=ps["current"],want=ps["wanted"],contact=mc),
                reply_markup=kb_confirm_swap(match["swap_id"])
            )
        except: pass
        kb=kb_confirm_swap(sw["swap_id"])
    else:
        text+="\n\n"+t("no_match",lang)
        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Browse Swaps",callback_data="flow_search"),
             InlineKeyboardButton("🏠 Menu",callback_data="flow_home")],
        ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text,reply_markup=kb,parse_mode="Markdown")
    else:
        await update.message.reply_text(text,reply_markup=kb,parse_mode="Markdown")

# ═══════════════════════════════════════════
#  SEARCH FLOW
# ═══════════════════════════════════════════
async def search_start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; lang=user_lang(uid)
    context.user_data.update({"flow":"search_train"})
    await rply(update,t("search_enter_train",lang),
        InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Cancel",callback_data="flow_home")]]))

async def search_got_train(update:Update,context:ContextTypes.DEFAULT_TYPE):
    raw=update.message.text.strip().upper()
    uid=update.effective_user.id; lang=user_lang(uid)
    context.user_data["flow"]=""
    swaps=all_swaps()
    results={k:v for k,v in swaps.items() if v.get("train")==raw and v.get("status")=="active"}
    tname=TRAINS.get(raw,"")
    if not results:
        await update.message.reply_text(
            t("no_swaps",lang,train=raw)+(f"\n🔖 _{tname}_" if tname else ""),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Post Swap",callback_data="flow_postseat")],
                [InlineKeyboardButton("🏠 Main Menu",callback_data="flow_home")],
            ]),parse_mode="Markdown"); return
    coaches={}
    for v in results.values():
        c=v.get("coach","?"); coaches.setdefault(c,[]).append(v)
    text=(f"🚆 *Train {raw}*"+(f"\n🔖 _{tname}_" if tname else "")+
          f"\nFound *{len(results)} swap(s)* in *{len(coaches)} coach(es)*\n\nSelect a coach 👇")
    rows=[[InlineKeyboardButton(f"🚉 {c}  —  {len(vs)} swap(s)",
           callback_data=f"vc_{raw}_{c}")] for c,vs in sorted(coaches.items())]
    rows.append([InlineKeyboardButton("🏠 Main Menu",callback_data="flow_home")])
    await update.message.reply_text(text,reply_markup=InlineKeyboardMarkup(rows),parse_mode="Markdown")

async def show_coach(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    _,train,coach=update.callback_query.data.split("_",2)
    uid=update.effective_user.id; lang=user_lang(uid)
    swaps=all_swaps()
    results=sorted([v for v in swaps.values()
        if v.get("train")==train and v.get("coach")==coach and v.get("status")=="active"],
        key=lambda x:-get_user(x["user_id"]).get("swaps_done",0))
    if not results:
        await update.callback_query.edit_message_text("No swaps for this coach.",reply_markup=kb_back_home()); return
    text=f"🚉 *{train} — Coach {coach}*\n{len(results)} swap(s)\n\n"
    rows=[]
    for i,req in enumerate(results,1):
        pnr_line=f"\n🎫 PNR: `{req['pnr']}`" if req.get("pnr") else ""
        text+=(f"*#{i}  {req['name']}*  {req.get('badge','🌱 Newcomer')}\n"
               f"💺 Seat *{req.get('seat','?')}* → *{req['current']}*  →  🔄 *{req['wanted']}*{pnr_line}\n"
               f"✅ {get_user(req['user_id']).get('swaps_done',0)} swaps  ·  🕐 {time_ago(req.get('ts',''))}\n"
               f"──────────────────\n")
        rows.append([
            InlineKeyboardButton(f"📩 Contact #{i}",url=f"tg://user?id={req['user_id']}"),
            InlineKeyboardButton(f"🚩 Report #{i}",callback_data=f"report_{req['user_id']}"),
        ])
    rows.append([InlineKeyboardButton("🏠 Main Menu",callback_data="flow_home")])
    await update.callback_query.edit_message_text(text,reply_markup=InlineKeyboardMarkup(rows),parse_mode="Markdown")

# ═══════════════════════════════════════════
#  CONFIRM SWAP
# ═══════════════════════════════════════════
async def confirm_swap(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    uid=update.effective_user.id; lang=user_lang(uid)
    sid=update.callback_query.data.replace("confirm_","")
    key=f"confirmed/{uid}_{sid}"

    if fb_get(key):
        await update.callback_query.edit_message_text(
            "✅ You already confirmed this swap!",reply_markup=kb_back_home()); return

    # Mark this user confirmed
    fb_set(key, True)

    # Check how many parties confirmed for this swap_id
    all_confirmed = fb_get("confirmed") or {}
    confirmed_parties = [k for k in all_confirmed if k.endswith(f"_{sid}")]
    count = len(confirmed_parties)

    if count >= 2:
        # BOTH confirmed → award points to both
        sd,pts = award(uid)
        # Find the other party and award them too
        for ck in confirmed_parties:
            other_uid_str = ck.replace(f"_{sid}","")
            try:
                other_uid = int(other_uid_str)
                if other_uid != uid:
                    o_sd, o_pts = award(other_uid)
                    o_lang = user_lang(other_uid)
                    try:
                        await context.bot.send_message(
                            chat_id=other_uid,
                            text=t("confirmed",o_lang,pts=o_pts,badge=get_badge(o_sd),bar=progress_bar(o_sd)),
                            parse_mode="Markdown"
                        )
                    except: pass
            except: pass

        # Mark swap as done in DB
        fb_set(f"swap_done/{sid}", {
            "completed_at": datetime.now().strftime("%d %b %Y %I:%M %p"),
            "parties": confirmed_parties,
        })

        await update.callback_query.edit_message_text(
            t("confirmed",lang,pts=pts,badge=get_badge(sd),bar=progress_bar(sd)),
            reply_markup=kb_back_home(),parse_mode="Markdown"
        )
    else:
        # Only 1 party confirmed so far
        wait_msg = {
            "en": "⏳ *Your confirmation saved!*\n\nWaiting for the other person to also confirm.\nPoints will be awarded to *both* once they confirm too!",
            "hi": "⏳ *आपकी पुष्टि सेव हो गई!*\n\nदूसरे व्यक्ति की पुष्टि का इंतजार है।\nदोनों की पुष्टि होने पर पॉइंट मिलेंगे!",
            "bn": "⏳ *আপনার নিশ্চিতকরণ সেভ হয়েছে!*\n\nঅন্য ব্যক্তির নিশ্চিতকরণের অপেক্ষায়।\nদুজন নিশ্চিত করলেই পয়েন্ট মিলবে!",
            "ur": "⏳ *آپ کی تصدیق محفوظ!*\n\nدوسرے شخص کی تصدیق کا انتظار ہے۔\nدونوں کی تصدیق پر پوائنٹ ملیں گے!",
        }.get(lang, "⏳ *Confirmation saved!*\n\nWaiting for the other person to confirm too.\nPoints awarded to both once they confirm!")

        await update.callback_query.edit_message_text(
            wait_msg,
            reply_markup=kb_back_home(),parse_mode="Markdown"
        )

# ═══════════════════════════════════════════
#  REPORT
# ═══════════════════════════════════════════
async def report_user(update:Update,context:ContextTypes.DEFAULT_TYPE):
    reporter=update.effective_user.id
    reported=int(update.callback_query.data.replace("report_",""))
    if reporter==reported: await update.callback_query.answer("❌ Can't report yourself!",show_alert=True); return
    key=f"reports/{reporter}_{reported}"
    if fb_get(key): await update.callback_query.answer("Already reported.",show_alert=True); return
    fb_set(key,True); u=get_user(reported); count=u.get("reports",0)+1
    fb_upd(f"users/{reported}",{"reports":count})
    if count>=3:
        fb_upd(f"users/{reported}",{"banned":True}); del_my_swap(reported)
        try: await context.bot.send_message(chat_id=reported,text="🚫 Your SeatSwap account has been suspended.")
        except: pass
        await update.callback_query.answer("⚠️ User banned after 3 reports.",show_alert=True)
    else:
        await update.callback_query.answer(f"Reported ({count}/3 reports before ban)",show_alert=True)

# ═══════════════════════════════════════════
#  MY REQUEST
# ═══════════════════════════════════════════
async def my_request(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; lang=user_lang(uid)
    req=my_swap(uid)
    if not req:
        await rply(update,t("no_request",lang),
            InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Post Swap",callback_data="flow_postseat")],
                                   [InlineKeyboardButton("🏠 Main Menu",callback_data="flow_home")]])); return
    pnr_line=f"\n🎫 PNR: `{req['pnr']}`" if req.get("pnr") else ""
    await rply(update,
        f"📋 *Your Active Request*\n\n"
        f"🚆 Train: *{req['train']}* _{req.get('train_name','')}_\n"
        f"🚉 Coach: *{req['coach']}*  Seat: *{req.get('seat','?')}*\n"
        f"💺 Has: *{req['current']}*  →  🔄 Wants: *{req['wanted']}*{pnr_line}\n"
        f"🕐 Posted: {time_ago(req.get('ts',''))}",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Delete Request",callback_data="cancelswap")],
            [InlineKeyboardButton("🏠 Main Menu",callback_data="flow_home")],
        ])
    )

# ═══════════════════════════════════════════
#  PROFILE
# ═══════════════════════════════════════════
async def profile(update:Update,context:ContextTypes.DEFAULT_TYPE):
    user=update.effective_user; u=get_user(user.id); lang=user_lang(user.id)
    sd=u.get("swaps_done",0)
    await rply(update,
        f"👤 *Your Profile*\n\n"
        f"Name:    *{user.first_name}*\n"
        f"Badge:   {get_badge(sd)}\n"
        f"✅ Swaps: *{sd}*\n"
        f"⭐ Points: *{u.get('points',0)}*\n\n"
        f"📈 *Progress:*\n{progress_bar(sd)}",
        kb_back_home()
    )

# ═══════════════════════════════════════════
#  HELP
# ═══════════════════════════════════════════
async def help_cmd(update:Update,context:ContextTypes.DEFAULT_TYPE):
    lang=user_lang(update.effective_user.id)
    await rply(update,t("help",lang),kb_back_home())

# ═══════════════════════════════════════════
#  CANCEL SWAP
# ═══════════════════════════════════════════
async def cancel_swap(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; lang=user_lang(uid)
    context.user_data.clear()
    deleted=del_my_swap(uid)
    await rply(update,t("request_cancelled" if deleted else "no_request",lang),kb_back_home())

# ═══════════════════════════════════════════
#  /MYID  — get own Telegram ID
# ═══════════════════════════════════════════
async def my_id(update:Update,context:ContextTypes.DEFAULT_TYPE):
    user=update.effective_user
    await update.message.reply_text(
        f"🔑 *Your Telegram ID:* `{user.id}`\n"
        f"👤 Username: @{user.username or 'not set'}\n\n"
        f"_Share this ID with admin if needed._",
        parse_mode="Markdown"
    )

# ═══════════════════════════════════════════
#  ADMIN COMMANDS
# ═══════════════════════════════════════════
def is_admin(uid):
    if uid in ADMIN_IDS: return True
    u = get_user(uid)
    uname = u.get("username","").lower().lstrip("@")
    return uname in ADMIN_UNAMES if uname else False

async def admin_stats(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    users=fb_get("users") or {}; swaps=all_swaps()
    active=sum(1 for s in swaps.values() if s.get("status")=="active")
    banned=sum(1 for u in users.values() if u.get("banned"))
    total_sd=sum(u.get("swaps_done",0) for u in users.values())
    await update.message.reply_text(
        f"📊 *Admin Stats*\n\n"
        f"🗄 Firebase: {'✅ Online' if FIREBASE_ON else '❌ Offline'}\n"
        f"👥 Users: *{len(users)}*\n"
        f"🔄 Active Swaps: *{active}*\n"
        f"✅ Total Swaps Done: *{total_sd}*\n"
        f"🚫 Banned: *{banned}*",
        parse_mode="Markdown"
    )

async def admin_checkdb(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not FIREBASE_ON:
        await update.message.reply_text(
            "❌ *Firebase NOT connected!*\n\n"
            "Fix:\n1. Railway → Variables\n2. Add `FIREBASE_KEY` with JSON content\n3. Redeploy",
            parse_mode="Markdown"); return
    try:
        db.reference("bot_status").update({"ping":datetime.now().strftime("%d %b %Y %I:%M %p")})
        r=db.reference("bot_status").get()
        await update.message.reply_text(
            f"✅ *Firebase Working!*\n\nPing: `{r.get('ping')}`\nBoot: `{r.get('boot')}`",
            parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error:\n`{e}`",parse_mode="Markdown")

async def admin_ban(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>"); return
    uid=int(context.args[0])
    fb_upd(f"users/{uid}",{"banned":True}); del_my_swap(uid)
    await update.message.reply_text(f"🚫 User `{uid}` banned and swaps removed.",parse_mode="Markdown")
    try: await context.bot.send_message(chat_id=uid,text="🚫 Your SeatSwap account has been suspended.")
    except: pass

async def admin_unban(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>"); return
    uid=int(context.args[0])
    fb_upd(f"users/{uid}",{"banned":False,"reports":0})
    await update.message.reply_text(f"✅ User `{uid}` unbanned.",parse_mode="Markdown")
    try: await context.bot.send_message(chat_id=uid,text="✅ Your SeatSwap account has been restored.")
    except: pass

async def admin_broadcast(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    msg=" ".join(context.args) if context.args else ""
    if not msg: await update.message.reply_text("Usage: /broadcast <message>"); return
    users=fb_get("users") or {}; sent=0
    for uid in users:
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"📢 *SeatSwap Announcement*\n\n{msg}",
                parse_mode="Markdown"); sent+=1
        except: pass
    await update.message.reply_text(f"✅ Sent to *{sent}/{len(users)}* users.",parse_mode="Markdown")

async def admin_userinfo(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not context.args:
        await update.message.reply_text("Usage: /userinfo <user_id>"); return
    uid=int(context.args[0]); u=get_user(uid)
    sw=my_swap(uid)
    swap_info=f"🔄 Active: Train {sw['train']} Coach {sw['coach']} Seat {sw.get('seat','?')}" if sw else "No active swap"
    await update.message.reply_text(
        f"👤 *User Info*\n\n"
        f"ID: `{uid}`\n"
        f"Name: {u.get('name')}\n"
        f"Username: @{u.get('username','none')}\n"
        f"Lang: {u.get('lang','en')}\n"
        f"Badge: {u.get('badge','')}\n"
        f"Swaps: {u.get('swaps_done',0)}\n"
        f"Points: {u.get('points',0)}\n"
        f"Banned: {'Yes 🚫' if u.get('banned') else 'No ✅'}\n"
        f"Reports: {u.get('reports',0)}\n"
        f"Joined: {u.get('joined','?')}\n\n"
        f"{swap_info}",
        parse_mode="Markdown"
    )

async def admin_deleteswap(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    if not context.args:
        await update.message.reply_text("Usage: /deleteswap <user_id>"); return
    uid=int(context.args[0]); deleted=del_my_swap(uid)
    await update.message.reply_text(
        f"✅ Swap deleted for user `{uid}`." if deleted else f"No active swap for `{uid}`.",
        parse_mode="Markdown"
    )

# ═══════════════════════════════════════════
#  MESSAGE ROUTER  (state machine)
# ═══════════════════════════════════════════
MENU_LABELS = {
    "🔄 Post Swap","🔍 Find Swap","📋 My Request","👤 Profile","🌐 Language","❓ Help",
    "🔄 स्वैप करें","🔍 खोजें","📋 मेरा अनुरोध","👤 प्रोफ़ाइल","🌐 भाषा","❓ मदद",
    "🔄 পোস্ট করুন","🔍 খুঁজুন","📋 আমার অনুরোধ","👤 প্রোফাইল","🌐 ভাষা","❓ সাহায্য",
    "🔄 پوسٹ کریں","🔍 تلاش","📋 میری درخواست","👤 پروفائل","🌐 زبان","❓ مدد",
}

async def handle_msg(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text=update.message.text.strip()
    uid=update.effective_user.id
    flow=context.user_data.get("flow","")

    # ReplyKeyboard menu buttons
    if "Post Swap" in text or "स्वैप करें" in text or "পোস্ট করুন" in text or "پوسٹ" in text:
        await ps_start(update,context); return
    if "Find Swap" in text or "खोजें" in text or "খুঁজুন" in text or "تلاش" in text:
        await search_start(update,context); return
    if "My Request" in text or "मेरा अनुरोध" in text or "আমার অনুরোধ" in text or "درخواست" in text:
        await my_request(update,context); return
    if "Profile" in text or "प्रोफ़ाइल" in text or "প্রোফাইল" in text or "پروفائل" in text:
        await profile(update,context); return
    if "Language" in text or "भाषा" in text or "ভাষা" in text or "زبان" in text:
        await choose_lang(update,context); return
    if "Help" in text or "मदद" in text or "সাহায্য" in text or "مدد" in text:
        await help_cmd(update,context); return

    # State machine flows
    if   flow=="ps_train":   await ps_got_train(update,context)
    elif flow=="ps_seat":    await ps_got_seat(update,context)
    elif flow=="ps_pnr":     await ps_got_pnr(update,context)
    elif flow=="search_train": await search_got_train(update,context)
    else:
        lang=user_lang(uid)
        await update.message.reply_text(
            "👇 Use the menu below:",reply_markup=kb_main_reply(lang)
        )

# ═══════════════════════════════════════════
#  CALLBACK ROUTER
# ═══════════════════════════════════════════
async def button_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data=update.callback_query.data

    # Menu
    if   data=="flow_home":      await start(update,context)
    elif data=="flow_postseat":  await ps_start(update,context)
    elif data=="flow_search":    await search_start(update,context)
    elif data=="flow_myrequest": await my_request(update,context)
    elif data=="flow_profile":   await profile(update,context)
    elif data=="flow_help":      await help_cmd(update,context)
    elif data=="cancelswap":     await cancel_swap(update,context)

    # Language
    elif data.startswith("lang_"): await set_lang(update,context)

    # Post swap steps
    elif data=="ps_train_ok":
        context.user_data["flow"]="ps_ct"
        await update.callback_query.edit_message_text(
            f"✅ Train *{context.user_data['ps']['train']}*\n\nSelect *Coach Type*:",
            reply_markup=kb_coach_types(),parse_mode="Markdown")
    elif data=="ps_renter_train":
        context.user_data["flow"]="ps_train"
        lang=user_lang(update.effective_user.id)
        await update.callback_query.edit_message_text(t("enter_train",lang),parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Cancel",callback_data="flow_home")]]))
    elif data.startswith("ct_"):  await ps_ct(update,context)
    elif data=="ps_back_ct":
        context.user_data["flow"]="ps_ct"
        lang=user_lang(update.effective_user.id)
        ps=context.user_data.get("ps",{})
        await update.callback_query.edit_message_text(
            t("train_found",lang,num=ps.get("train",""),name=ps.get("train_name","")),
            reply_markup=kb_coach_types(),parse_mode="Markdown")
    elif data.startswith("cn_"):  await ps_coach(update,context)
    elif data=="ps_seat_ok":      await ps_wanted(update,context)
    elif data=="ps_renter_seat":
        uid=update.effective_user.id; lang=user_lang(uid)
        ct=context.user_data.get("ps",{}).get("coach_type","SL")
        mx=COACH_TYPES.get(ct,{}).get("max_seat",72)
        context.user_data["flow"]="ps_seat"
        await update.callback_query.edit_message_text(
            t("enter_seat",lang,ct=ct,max=mx),parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="ps_back_ct")]]))
    elif data.startswith("want_") and data!="want_back":
        await ps_got_wanted(update,context)
    elif data=="want_back":        await ps_seat_ok_handler(update,context)
    elif data=="pnr_skip":         await ps_skip_pnr(update,context)

    # Search
    elif data.startswith("vc_"):   await show_coach(update,context)

    # Confirm / Report
    elif data.startswith("confirm_"): await confirm_swap(update,context)
    elif data.startswith("report_"):  await report_user(update,context)

    else:
        try: await update.callback_query.edit_message_text("⚠️ Error. Returning...",reply_markup=kb_back_home())
        except: pass

async def ps_seat_ok_handler(update,context):
    uid=update.effective_user.id; lang=user_lang(uid)
    ct=context.user_data.get("ps",{}).get("coach_type","SL")
    mx=COACH_TYPES.get(ct,{}).get("max_seat",72)
    context.user_data["flow"]="ps_seat"
    await update.callback_query.edit_message_text(
        t("enter_seat",lang,ct=ct,max=mx),parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="ps_back_ct")]]))

# ═══════════════════════════════════════════
#  ERROR HANDLER  (self-healing)
# ═══════════════════════════════════════════
async def error_handler(update:object,context:ContextTypes.DEFAULT_TYPE):
    print(f"❌ Error: {context.error}")
    try:
        if isinstance(update,Update):
            lang=user_lang(update.effective_user.id) if update.effective_user else "en"
            if update.callback_query:
                await update.callback_query.answer("⚠️ Error. Returning to menu.",show_alert=True)
                try: await update.callback_query.edit_message_text("⚠️ Something went wrong.",reply_markup=kb_back_home())
                except: pass
            elif update.message:
                await update.message.reply_text("⚠️ Something went wrong. Use the menu:",
                    reply_markup=kb_main_reply(lang))
    except: pass

# ═══════════════════════════════════════════
#  POST INIT  (set bot commands menu)
# ═══════════════════════════════════════════
async def post_init(app):
    cmds=[
        BotCommand("start",     "🏠 Home / Main Menu"),
        BotCommand("myrequest", "📋 My active swap request"),
        BotCommand("profile",   "👤 My profile & badges"),
        BotCommand("language",  "🌐 Change language"),
        BotCommand("myid",      "🔑 Get my Telegram ID"),
        BotCommand("cancel",    "❌ Cancel current action"),
        BotCommand("help",      "❓ How to use SeatSwap"),
    ]
    await app.bot.set_my_commands(cmds)
    try: await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except: pass
    print("✅ Bot commands set")

# ═══════════════════════════════════════════
#  APP SETUP
# ═══════════════════════════════════════════
app=(ApplicationBuilder()
     .token(BOT_TOKEN)
     .post_init(post_init)
     .build())

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(CommandHandler("start",       start))
app.add_handler(CommandHandler("myrequest",   my_request))
app.add_handler(CommandHandler("profile",     profile))
app.add_handler(CommandHandler("language",    choose_lang))
app.add_handler(CommandHandler("myid",        my_id))
app.add_handler(CommandHandler("cancel",      cancel_swap))
app.add_handler(CommandHandler("help",        help_cmd))
app.add_handler(CommandHandler("stats",       admin_stats))
app.add_handler(CommandHandler("checkdb",     admin_checkdb))
app.add_handler(CommandHandler("ban",         admin_ban))
app.add_handler(CommandHandler("unban",       admin_unban))
app.add_handler(CommandHandler("broadcast",   admin_broadcast))
app.add_handler(CommandHandler("userinfo",    admin_userinfo))
app.add_handler(CommandHandler("deleteswap",  admin_deleteswap))
app.add_error_handler(error_handler)

print("🚆 SeatSwap Bot starting...")
app.run_polling(allowed_updates=Update.ALL_TYPES)
