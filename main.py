from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import firebase_admin
from firebase_admin import credentials, db
import json
import os

BOT_TOKEN = "YOUR_BOT_TOKEN"

firebase_key = json.loads(os.getenv("FIREBASE_KEY"))

cred = credentials.Certificate(firebase_key)

firebase_admin.initialize_app(cred, {
'databaseURL': 'https://seatswap-a96ec-default-rtdb.firebaseio.com/'
})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

```
user_id = str(update.effective_user.id)

ref = db.reference(f"users/{user_id}")

ref.set({
    "name": update.effective_user.first_name,
    "points": 0,
    "rating": 5
})

await update.message.reply_text(
    "Welcome to SeatSwap 🚆\nYour profile has been created!"
)
```

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))

print("Bot is running...")

app.run_polling()
