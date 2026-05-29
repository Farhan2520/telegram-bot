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

# ══════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════
BOT_TOKEN   = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_IDS   = [int(x) for x in os.getenv("ADMIN_IDS","0").split(",") if x.strip().isdigit()]
ADMIN_UNAMES= [x.strip().lower().lstrip("@") for x in os.getenv("ADMIN_USERNAMES","").split(",") if x.strip()]

# ══════════════════════════════════════════════════════
#  FIREBASE
# ══════════════════════════════════════════════════════
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
    print("❌ Firebase:", e)

# ══════════════════════════════════════════════════════
#  TRAIN DATABASE
# ══════════════════════════════════════════════════════
TRAINS = {
    "12301":"Howrah Rajdhani Express","12302":"New Delhi Rajdhani Express",
    "12303":"Poorva Express","12304":"Poorva Express",
    "12305":"Howrah Rajdhani (via Patna)","12306":"Howrah Rajdhani (via Patna)",
    "12309":"Rajendra Nagar Rajdhani","12310":"Rajendra Nagar Rajdhani",
    "12311":"Howrah Kalka Mail","12312":"Kalka Howrah Mail",
    "12313":"Sealdah Rajdhani Express","12314":"Sealdah Rajdhani Express",
    "12343":"Darjeeling Mail","12344":"Darjeeling Mail",
    "12345":"Saraighat Express","12346":"Saraighat Express",
    "12381":"Poorabh Express","12382":"Poorabh Express",
    "12423":"Dibrugarh Rajdhani","12424":"Dibrugarh Rajdhani",
    "12431":"Trivandrum Rajdhani","12432":"Trivandrum Rajdhani",
    "12433":"NZM Rajdhani Express","12434":"NZM Rajdhani Express",
    "12951":"Mumbai Rajdhani Express","12952":"New Delhi Rajdhani Express",
    "12953":"August Kranti Rajdhani","12954":"August Kranti Rajdhani",
    "22691":"Rajdhani Express","22692":"Rajdhani Express",
    "20503":"Agartala Rajdhani","20504":"Agartala Rajdhani",
    "12001":"Bhopal Shatabdi Express","12002":"Bhopal Shatabdi Express",
    "12003":"Lucknow Shatabdi Express","12004":"Lucknow Shatabdi Express",
    "12017":"Howrah Shatabdi Express","12018":"Howrah Shatabdi Express",
    "12019":"Howrah Shatabdi Express","12020":"Howrah Shatabdi Express",
    "12025":"Pune Shatabdi Express","12026":"Pune Shatabdi Express",
    "12031":"Amritsar Shatabdi","12032":"Amritsar Shatabdi",
    "12041":"NJP Shatabdi","12042":"NJP Shatabdi",
    "12213":"Yesvantpur Duronto","12214":"Yesvantpur Duronto",
    "12219":"Secunderabad Duronto","12220":"Secunderabad Duronto",
    "12221":"Pune Duronto","12222":"Pune Duronto",
    "12225":"NZM Duronto Express","12226":"NZM Duronto Express",
    "12259":"Sealdah Duronto Express","12260":"Sealdah Duronto Express",
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
    "13005":"Howrah Amritsar Express","13006":"Amritsar Howrah Express",
    "13007":"Udyan Abha Toofan Express","13008":"Udyan Abha Toofan Express",
    "13065":"Howrah Anand Vihar Amrit Bharat","13066":"Howrah Anand Vihar Amrit Bharat",
    "14021":"Anand Vihar Purulia Express","14022":"Anand Vihar Purulia Express",
    "14033":"Jammu Mail","14034":"Jammu Mail",
    "14055":"Brahmaputra Mail","14056":"Brahmaputra Mail",
    "15309":"Ramnagar Dehradun Express","15310":"Dehradun Ramnagar Express",
    "15675":"New Jalpaiguri Guwahati Express","15676":"New Jalpaiguri Guwahati Express",
    "15673":"Kamakhya Charlapalli Amrit Bharat","15674":"Kamakhya Charlapalli Amrit Bharat",
    "15671":"Kamakhya Rohtak Amrit Bharat","15672":"Kamakhya Rohtak Amrit Bharat",
    "16001":"Mettupalayam Express","16002":"Mettupalayam Express",
    "16107":"Tambaram Thiruvananthapuram Amrit Bharat","16108":"Tambaram Thiruvananthapuram Amrit Bharat",
    "16121":"Tambaram Thiruvananthapuram Central Amrit Bharat","16122":"Tambaram Thiruvananthapuram Central Amrit Bharat",
    "16317":"Himsagar Express","16318":"Himsagar Express",
    "16329":"Nagercoil Mangaluru Amrit Bharat","16330":"Nagercoil Mangaluru Amrit Bharat",
    "16357":"Nagercoil Charlapalli Amrit Bharat","16358":"Nagercoil Charlapalli Amrit Bharat",
    "17041":"Charlapalli Thiruvananthapuram Amrit Bharat","17042":"Charlapalli Thiruvananthapuram Amrit Bharat",
    "18061":"Santragachi Khatipura Express","18062":"Santragachi Khatipura Express",
    "20609":"NJP Tiruchchirappalli Amrit Bharat","20610":"NJP Tiruchchirappalli Amrit Bharat",
    "20603":"NJP Nagercoil Amrit Bharat","20604":"NJP Nagercoil Amrit Bharat",
    "22435":"Varanasi Vande Bharat","22436":"Varanasi Vande Bharat",
    "22347":"Howrah Patna Vande Bharat","22348":"Howrah Patna Vande Bharat",
    "20887":"Ranchi Varanasi Vande Bharat","20888":"Ranchi Varanasi Vande Bharat",
    "26401":"Jammu Tawi Srinagar Vande Bharat","26402":"Jammu Tawi Srinagar Vande Bharat",
    "22589":"Banaras Hadapsar Amrit Bharat","22590":"Banaras Hadapsar Amrit Bharat",
    "22588":"Banaras Sealdah Amrit Bharat","22587":"Sealdah Banaras Amrit Bharat",
    "14045":"Gorakhpur Delhi Amrit Bharat","14046":"Gorakhpur Delhi Amrit Bharat",
    "11061":"LTT Jabalpur Express","11062":"Jabalpur LTT Express",
    "11071":"Kamayani Express","11072":"Kamayani Express",
    "11077":"Jhelum Express","11078":"Jhelum Express",
    "12101":"Jnaneshwari Super Deluxe","12102":"Jnaneshwari Super Deluxe",
    "12137":"Punjab Mail","12138":"Punjab Mail",
    "12453":"Ranchi New Delhi Rajdhani","12454":"Ranchi New Delhi Rajdhani",
    "13379":"Dhanbad Lokmanya Tilak Express","13380":"Dhanbad Lokmanya Tilak Express",
    "15949":"Dibrugarh Gomtinagar Amrit Bharat","15950":"Dibrugarh Gomtinagar Amrit Bharat",
    "18061":"Santragachi Khatipura Express","18062":"Santragachi Khatipura Express",
    "19403":"Bhuj Delhi Express","19404":"Bhuj Delhi Express",
    "20111":"LTT Balharshah Express","20112":"LTT Balharshah Express",
    "20120":"LTT Ayodhya Amrit Bharat","20121":"LTT Ayodhya Amrit Bharat",
    "16619":"Podanur Dhanbad Amrit Bharat","16620":"Podanur Dhanbad Amrit Bharat",
    "16707":"Mangaluru Tirunelveli Express","16708":"Mangaluru Tirunelveli Express",
    "22823":"Bhubaneswar Rajdhani","22824":"Bhubaneswar Rajdhani",
    "22825":"Shalimar Rajdhani","22826":"Shalimar Rajdhani",
}

# ══════════════════════════════════════════════════════
#  COACH + SEAT SYSTEM
# ══════════════════════════════════════════════════════
COACH_TYPES = {
    "SL": {"label":"🛏 Sleeper (S1-S12)",    "max":72,  "coaches":[f"S{i}" for i in range(1,13)]},
    "3A": {"label":"❄️ AC 3 Tier (B1-B6)",   "max":64,  "coaches":[f"B{i}" for i in range(1,7)]},
    "2A": {"label":"❄️ AC 2 Tier (A1-A4)",   "max":46,  "coaches":[f"A{i}" for i in range(1,5)]},
    "1A": {"label":"❄️ AC 1st (H1-H2)",      "max":24,  "coaches":["H1","H2"]},
    "CC": {"label":"💺 Chair Car (C1-C8)",    "max":78,  "coaches":[f"C{i}" for i in range(1,9)]},
    "EC": {"label":"💺 Exec Chair (EC1-EC3)", "max":56,  "coaches":["EC1","EC2","EC3"]},
    "GN": {"label":"🚃 General (GS1-GS3)",    "max":200, "coaches":["GS1","GS2","GS3"]},
}

BERTH_EMOJI = {
    "Lower":"⬇️","Middle":"➡️","Upper":"⬆️",
    "Side Lower":"↘️","Side Upper":"↗️",
    "Window":"🪟","Aisle":"🚶","Any":"🔀",
}

def seat_to_berth(seat_num, coach_type):
    try:
        s = int(seat_num)
    except:
        return "?"
    if coach_type in ["SL","3A"]:
        return ["Lower","Middle","Upper","Lower","Middle","Upper","Side Lower","Side Upper"][(s-1)%8]
    if coach_type == "2A":
        return ["Lower","Upper","Lower","Upper","Side Lower","Side Upper"][(s-1)%6]
    if coach_type == "1A":
        return "Lower" if s % 2 == 1 else "Upper"
    if coach_type in ["CC","EC"]:
        return ["Window","Middle","Aisle"][(s-1)%3]
    return "Seat " + str(s)

def berths_for_coach(ct):
    if ct in ["SL","3A"]:
        return ["Lower","Middle","Upper","Side Lower","Side Upper"]
    if ct in ["2A","1A"]:
        return ["Lower","Upper","Side Lower","Side Upper"]
    return ["Window","Middle","Aisle"]
