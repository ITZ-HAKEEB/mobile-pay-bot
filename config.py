import os

# Telegram Bot Credentials
API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

# Database Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "mobile_pay_db"

# Force Join Channel
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "@YourChannelUsername")

# Start Image URL (Change this link anytime)
START_IMAGE_URL = os.getenv("START_IMAGE_URL", "https://telegra.ph/file/0c324976c7c251bb425c7.jpg")

# Configurable Start Message
START_MESSAGE = (
    "👋 Welcome to **Mobile Pay**!\n\n"
    "Your secure digital wallet and instant UPI payment bot.\n"
    "Please select an option from the menu below to get started:"
)

# Mandatory Initial Notice Text
INITIAL_NOTICE_TEXT = (
    "⚠️ **IMPORTANT NOTICE & SAFETY ASSURANCE**\n\n"
    "Welcome to **Mobile Pay** Bot!\n"
    "• Our bot is 100% secure, safe, and reliable for all your financial interactions.\n"
    "• You can generate your custom QR code and UPI ID to send or receive REAL payments seamlessly.\n"
    "• This platform contains zero fraudulent intent—you can use it with complete peace of mind.\n"
    "• In case you encounter any issue or suspect any unauthorized activity, you can contact our Admin Support directly anytime. We will assist and protect you to the best of our ability.\n\n"
    "Click the **Start Engine** button below to open your Mobile Pay dashboard!"
)

# Support Username (without @)
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "llMR_BADALll")

# Company & Business Configuration
COMPANY_UPI = os.getenv("COMPANY_UPI", "company@mbp")
MONTHLY_FEE = 49.0
