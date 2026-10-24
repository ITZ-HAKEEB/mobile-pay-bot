import os

# Telegram Bot Credentials
API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

# Database Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "mobile_pay_db"

# Owner & Admin Configuration
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))  # Replace with your Telegram Numeric ID
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "llMR_BADALll")  # Support username without @

# Force Join Channel
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "@YourChannelUsername")

# Start Image URL
START_IMAGE_URL = os.getenv("START_IMAGE_URL", "https://telegra.ph/file/0c324976c7c251bb425c7.jpg")

# Configurable Messages
START_MESSAGE = (
    "👋 Welcome to **Mobile Pay**!\n\n"
    "Your secure digital wallet and instant UPI payment bot.\n"
    "Please select an option from the menu below to get started:"
)

INITIAL_NOTICE_TEXT = (
    "⚠️ **IMPORTANT NOTICE & SAFETY ASSURANCE**\n\n"
    "Welcome to **Mobile Pay** Bot!\n"
    "• Our bot is 100% secure, safe, and reliable for all your financial interactions.\n"
    "• You can generate your custom QR code and UPI ID to send or receive REAL payments seamlessly.\n"
    "• This platform contains zero fraudulent intent—you can use it with complete peace of mind.\n"
    "• In case you encounter any issue or suspect any unauthorized activity, you can contact our Admin Support directly anytime.\n\n"
    "Click the **Start Engine** button below to open your Mobile Pay dashboard!"
)

# Company Configuration
COMPANY_UPI = os.getenv("COMPANY_UPI", "company@mbp")
MONTHLY_FEE = 49.0
