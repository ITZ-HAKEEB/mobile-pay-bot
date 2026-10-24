import motor.motor_asyncio
from config import MONGO_URI, DB_NAME

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

users_collection = db["users"]
transactions_collection = db["transactions"]

async def register_user(user_id: int, full_name: str, mobile: str):
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        default_upi = f"{full_name.lower().replace(' ', '')}{user_id}@mbp"
        user_data = {
            "user_id": user_id,
            "full_name": full_name,
            "mobile": mobile,
            "balance": 0.0,
            "mpin": None,
            "custom_upi": default_upi,
            "kyc_verified": True
        }
        await users_collection.insert_one(user_data)
        return default_upi
    return user.get("custom_upi")

async def get_user(user_id: int):
    return await users_collection.find_one({"user_id": user_id})

async def set_mpin(user_id: int, mpin: str):
    await users_collection.update_one({"user_id": user_id}, {"$set": {"mpin": mpin}})

async def update_balance(user_id: int, amount: float):
    await users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})

async def update_custom_upi(user_id: int, new_upi: str):
    await users_collection.update_one({"user_id": user_id}, {"$set": {"custom_upi": new_upi}})

async def log_transaction(user_id: int, tx_type: str, amount: float, recipient: str, status: str):
    tx_data = {
        "user_id": user_id,
        "type": tx_type,
        "amount": amount,
        "recipient": recipient,
        "status": status,
        "timestamp": motor.motor_asyncio.AsyncIOMotorClient.datetime.datetime.utcnow()
    }
    await transactions_collection.insert_one(tx_data)

async def get_user_transactions(user_id: int):
    cursor = transactions_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(10)
    return await cursor.to_list(length=10)
  
