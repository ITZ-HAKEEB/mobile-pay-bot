import os
import uuid
import cv2
import qrcode
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from config import (
    API_ID, API_HASH, BOT_TOKEN, OWNER_ID, FORCE_CHANNEL, START_MESSAGE, 
    START_IMAGE_URL, INITIAL_NOTICE_TEXT, SUPPORT_USERNAME, MONTHLY_FEE, COMPANY_UPI
)
from database import (
    register_user, get_user, get_all_users, set_mpin, update_balance, 
    update_custom_upi, log_transaction, get_user_transactions,
    create_deposit_request, get_deposit_request, update_deposit_status
)

app = Client("mobile_pay_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

USER_STATES = {}

def main_menu_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 My Account", callback_data="my_account"), InlineKeyboardButton("💰 My Balance", callback_data="my_balance")],
        [InlineKeyboardButton("💵 Deposit Money", callback_data="deposit_money"), InlineKeyboardButton("🪪 My UPI / QR", callback_data="my_qr")],
        [InlineKeyboardButton("🆔 Create New UPI ID", callback_data="create_upi"), InlineKeyboardButton("💸 Pay Any UPI", callback_data="pay_upi")],
        [InlineKeyboardButton("📷 Scan QR Code", callback_data="scan_qr"), InlineKeyboardButton("📜 My Transactions", callback_data="my_transactions")],
        [InlineKeyboardButton("⚠️ Terms & Charges", callback_data="notice"), InlineKeyboardButton("🛠️ Support Admin", url=f"https://t.me/{SUPPORT_USERNAME}")]
    ])

def admin_menu_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Bot Statistics", callback_data="admin_stats"), InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("➕ Add Balance", callback_data="admin_add_balance"), InlineKeyboardButton("➖ Deduct Balance", callback_data="admin_sub_balance")],
        [InlineKeyboardButton("🔙 Exit Admin Panel", callback_data="back_menu")]
    ])

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    user_id = message.from_user.id
    
    try:
        member = await client.get_chat_member(FORCE_CHANNEL, user_id)
        if member.status in ["left", "kicked"]:
            raise Exception()
    except Exception:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_CHANNEL.replace('@', '')}")],
            [InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")]
        ])
        if START_IMAGE_URL:
            await message.reply_photo(
                photo=START_IMAGE_URL,
                caption="⚠️ **Force Join Required!**\nPlease join our official channel first to use Mobile Pay bot.",
                reply_markup=keyboard
            )
        else:
            await message.reply_text(
                "⚠️ **Force Join Required!**\nPlease join our official channel first to use Mobile Pay bot.",
                reply_markup=keyboard
            )
        return

    user = await get_user(user_id)
    if not user:
        USER_STATES[user_id] = {"step": "awaiting_mobile"}
        await message.reply_text(
            "👋 Welcome to **Mobile Pay**!\nPlease share your mobile number for registration:", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📱 Share Mobile Number", request_contact=True)]])
        )
    else:
        notice_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Engine", callback_data="open_dashboard")],
            [InlineKeyboardButton("🛠️ Contact Admin Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
        ])
        if START_IMAGE_URL:
            await message.reply_photo(photo=START_IMAGE_URL, caption=INITIAL_NOTICE_TEXT, reply_markup=notice_keyboard)
        else:
            await message.reply_text(INITIAL_NOTICE_TEXT, reply_markup=notice_keyboard)

@app.on_message(filters.command("admin"))
async def admin_panel_command(client, message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        await message.reply_text("❌ Access Denied! This command is only for the Bot Admin.")
        return
    await message.reply_text("👑 **Admin Control Panel**\nSelect an operation below:", reply_markup=admin_menu_markup())

@app.on_callback_query(filters.regex("verify_join"))
async def verify_join_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        member = await client.get_chat_member(FORCE_CHANNEL, user_id)
        if member.status in ["left", "kicked"]:
            await callback.answer("❌ You haven't joined the channel yet!", show_alert=True)
            return
    except Exception:
        await callback.answer("❌ Please join the channel first!", show_alert=True)
        return
    
    await callback.message.delete()
    user = await get_user(user_id)
    if not user:
        USER_STATES[user_id] = {"step": "awaiting_mobile"}
        await callback.message.reply_text("✅ Verification Successful!\nPlease share your mobile number to proceed:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📱 Share Mobile Number", request_contact=True)]]))
    else:
        notice_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Engine", callback_data="open_dashboard")],
            [InlineKeyboardButton("🛠️ Contact Admin Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
        ])
        if START_IMAGE_URL:
            await callback.message.reply_photo(photo=START_IMAGE_URL, caption=INITIAL_NOTICE_TEXT, reply_markup=notice_keyboard)
        else:
            await callback.message.reply_text(INITIAL_NOTICE_TEXT, reply_markup=notice_keyboard)

@app.on_message(filters.contact)
async def contact_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id in USER_STATES and USER_STATES[user_id].get("step") == "awaiting_mobile":
        mobile = message.contact.phone_number
        USER_STATES[user_id]["mobile"] = mobile
        USER_STATES[user_id]["step"] = "awaiting_name"
        await message.reply_text("✅ Mobile verified.\nNow, please send your full name for your account profile:")

@app.on_message(filters.text & ~filters.command(["start", "admin"]))
async def text_handler(client, message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if user_id not in USER_STATES:
        return

    state = USER_STATES[user_id]
    step = state.get("step")

    if step == "awaiting_name":
        full_name = text
        mobile = state.get("mobile", "9999999999")
        custom_upi = await register_user(user_id, full_name, mobile)
        USER_STATES[user_id] = {"step": "setting_mpin"}
        await message.reply_text(f"🎉 Account Created Successfully!\nYour UPI ID: `{custom_upi}`\n\nNow, please set a secure **4-digit M-PIN** (e.g., `1234`) for transactions:")

    elif step == "setting_mpin":
        if not text.isdigit() or len(text) != 4:
            await message.reply_text("❌ Invalid M-PIN format. Please enter exactly **4 digits** (e.g. `1234`):")
            return
        await set_mpin(user_id, text)
        del USER_STATES[user_id]
        notice_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Engine", callback_data="open_dashboard")],
            [InlineKeyboardButton("🛠️ Contact Admin Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
        ])
        await message.reply_text("✅ M-PIN set successfully!\n\n" + INITIAL_NOTICE_TEXT, reply_markup=notice_keyboard)

    elif step == "creating_upi":
        clean_name = text.lower().replace(" ", "")
        new_upi = f"{clean_name}@mbp"
        await update_custom_upi(user_id, new_upi)
        del USER_STATES[user_id]
        await message.reply_text(f"✅ New UPI ID Created Successfully!\n📍 `{new_upi}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_menu")]]))

    elif step == "awaiting_deposit_amount":
        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            await message.reply_text("❌ Invalid amount. Enter a valid number:")
            return
        
        deposit_id = str(uuid.uuid4())[:8]
        await create_deposit_request(deposit_id, user_id, amount)
        USER_STATES[user_id] = {"step": "awaiting_deposit_proof", "deposit_id": deposit_id, "amount": amount}
        
        qr_path = f"deposit_{deposit_id}.png"
        img = qrcode.make(f"upi://pay?pa={COMPANY_UPI}&am={amount}&pn=MobilePay")
        img.save(qr_path)
        
        await message.reply_photo(
            photo=qr_path,
            caption=f"💵 **Deposit Request Generated**\nAmount: ₹{amount:.2f}\nUPI ID: `{COMPANY_UPI}`\n\nScan the QR code and pay. Once paid, send the payment screenshot/receipt here:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="back_menu")]])
        )
        if os.path.exists(qr_path):
            os.remove(qr_path)

    elif step == "pay_upi_id":
        USER_STATES[user_id]["recipient_upi"] = text
        USER_STATES[user_id]["step"] = "pay_amount"
        await message.reply_text("💵 Please enter the amount (INR) you wish to send:")

    elif step == "pay_amount":
        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            await message.reply_text("❌ Invalid amount. Please enter a valid number:")
            return
        USER_STATES[user_id]["amount"] = amount
        USER_STATES[user_id]["step"] = "pay_mpin"
        await message.reply_text("🔐 Please enter your **4-digit M-PIN** to authorize this payment:")

    elif step == "pay_mpin":
        user = await get_user(user_id)
        if user.get("mpin") != text:
            await message.reply_text("❌ Incorrect M-PIN. Payment cancelled.", reply_markup=main_menu_markup())
            del USER_STATES[user_id]
            return
        
        amount = state.get("amount")
        recipient = state.get("recipient_upi") or state.get("scanned_upi")
        
        if user.get("balance") < amount:
            await message.reply_text("❌ Insufficient balance in your wallet!", reply_markup=main_menu_markup())
            del USER_STATES[user_id]
            return

        await update_balance(user_id, -amount)
        await log_transaction(user_id, "DEBIT", amount, recipient, "SUCCESS")
        del USER_STATES[user_id]
        
        receipt = (
            f"✅ **Payment Successful!**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **To:** `{recipient}`\n"
            f"💰 **Amount:** ₹{amount:.2f}\n"
            f"🏢 **Company Fee:** ₹0.00\n"
            f"🕒 **Status:** SUCCESS\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📱 Powered by **Mobile Pay**"
        )
        await message.reply_text(receipt, reply_markup=main_menu_markup())

    elif step == "admin_awaiting_broadcast":
        all_users = await get_all_users()
        sent, failed = 0, 0
        status_msg = await message.reply_text("⏳ Broadcasting message to all users...")
        for u in all_users:
            try:
                await app.send_message(u["user_id"], f"📢 **ADMIN ANNOUNCEMENT**\n\n{text}")
                sent += 1
            except Exception:
                failed += 1
        del USER_STATES[user_id]
        await status_msg.edit_text(f"✅ **Broadcast Completed!**\n• Total Sent: {sent}\n• Failed: {failed}", reply_markup=admin_menu_markup())

    elif step == "admin_awaiting_add_bal":
        try:
            target_id, amt = text.split()
            await update_balance(int(target_id), float(amt))
            await log_transaction(int(target_id), "CREDIT_ADMIN", float(amt), "ADMIN", "SUCCESS")
            await message.reply_text(f"✅ Added ₹{amt} to User ID: `{target_id}`", reply_markup=admin_menu_markup())
            await app.send_message(int(target_id), f"🎉 **Wallet Credited!**\nAdmin added ₹{amt} to your Mobile Pay wallet.")
        except Exception as e:
            await message.reply_text(f"❌ Error! Use format: `USER_ID AMOUNT`\nDetails: {e}")
        del USER_STATES[user_id]

@app.on_callback_query()
async def callback_handler(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    user = await get_user(user_id)

    if data == "open_dashboard":
        await callback.message.delete()
        await client.send_message(user_id, START_MESSAGE, reply_markup=main_menu_markup())

    elif data == "my_account":
        await callback.message.edit_text(
            f"👤 **Account Details**\n\n"
            f"• Name: {user.get('full_name')}\n"
            f"• Mobile: {user.get('mobile')}\n"
            f"• Primary UPI: `{user.get('custom_upi')}`\n"
            f"• KYC Status: Verified ✅",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_menu")]])
        )

    elif data == "my_balance":
        await callback.message.edit_text(
            f"💰 **Wallet Balance**\n\nAvailable Balance: **₹{user.get('balance', 0.0):.2f}**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_menu")]])
        )

    elif data == "deposit_money":
        USER_STATES[user_id] = {"step": "awaiting_deposit_amount"}
        await callback.message.edit_text("💵 Enter the amount (INR) you wish to add to your wallet:")

    elif data == "my_qr":
        upi = user.get("custom_upi")
        qr_img_path = f"qr_{user_id}.png"
        img = qrcode.make(f"upi://pay?pa={upi}&pn={user.get('full_name')}")
        img.save(qr_img_path)
        
        await callback.message.delete()
        await client.send_photo(
            chat_id=user_id,
            photo=qr_img_path,
            caption=f"🪪 **Your Mobile Pay QR & UPI**\nUPI ID: `{upi}`\nScan this QR code with any UPI app to receive real payments.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_menu")]])
        )
        if os.path.exists(qr_img_path):
            os.remove(qr_img_path)

    elif data == "create_upi":
        USER_STATES[user_id] = {"step": "creating_upi"}
        await callback.message.edit_text("🆔 Send your desired custom ID name/number (e.g., `hakeeb07`) to generate your new `@mbp` UPI ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_menu")]]))

    elif data == "pay_upi":
        USER_STATES[user_id] = {"step": "pay_upi_id"}
        await callback.message.edit_text("💸 Send the recipient UPI ID (e.g., `merchant@paytm`):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_menu")]]))

    elif data == "scan_qr":
        USER_STATES[user_id] = {"step": "awaiting_qr_photo"}
        await callback.message.edit_text("📷 Please send the QR code photo/screenshot to scan and pay:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_menu")]]))

    elif data == "my_transactions":
        txs = await get_user_transactions(user_id)
        text = "📜 **Recent Transactions**\n━━━━━━━━━━━━━━━━━━━\n"
        if not txs:
            text += "No transactions found."
        else:
            for tx in txs:
                text += f"• {tx['type']} | ₹{tx['amount']} | To: {tx['recipient']} | {tx['status']}\n"
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_menu")]]))

    elif data == "notice":
        notice_text = (
            f"⚠️ **Terms & Subscription Notice**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"• A monthly subscription fee of **₹{MONTHLY_FEE}** applies per account for system upkeep.\n"
            f"• All transfers are real-time and backed by user authentication.\n"
            f"• Keep your M-PIN secure and confidential."
        )
        await callback.message.edit_text(notice_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_menu")]]))

    elif data == "admin_stats":
        if user_id != OWNER_ID:
            return
        all_users = await get_all_users()
        total_bal = sum(u.get("balance", 0.0) for u in all_users)
        await callback.message.edit_text(
            f"📊 **Bot Statistics**\n\n"
            f"• Total Users: {len(all_users)}\n"
            f"• Total System Balance: ₹{total_bal:.2f}",
            reply_markup=admin_menu_markup()
        )

    elif data == "admin_broadcast":
        if user_id != OWNER_ID:
            return
        USER_STATES[user_id] = {"step": "admin_awaiting_broadcast"}
        await callback.message.edit_text("📢 Send the broadcast message text you wish to send to all registered users:")

    elif data == "admin_add_balance":
        if user_id != OWNER_ID:
            return
        USER_STATES[user_id] = {"step": "admin_awaiting_add_bal"}
        await callback.message.edit_text("➕ Send `USER_ID AMOUNT` (e.g., `123456789 500`):")

    elif data.startswith("approve_"):
        if user_id != OWNER_ID:
            return
        dep_id = data.split("_")[1]
        dep_req = await get_deposit_request(dep_id)
        if dep_req and dep_req.get("status") == "PENDING":
            await update_deposit_status(dep_id, "APPROVED")
            await update_balance(dep_req["user_id"], dep_req["amount"])
            await log_transaction(dep_req["user_id"], "CREDIT_DEPOSIT", dep_req["amount"], "DEPOSIT", "SUCCESS")
            
            await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ **STATUS: APPROVED**")
            await app.send_message(dep_req["user_id"], f"✅ **Deposit Approved!**\n₹{dep_req['amount']:.2f} has been added to your wallet.")
        else:
            await callback.answer("❌ Request already processed!", show_alert=True)

    elif data.startswith("decline_"):
        if user_id != OWNER_ID:
            return
        dep_id = data.split("_")[1]
        dep_req = await get_deposit_request(dep_id)
        if dep_req and dep_req.get("status") == "PENDING":
            await update_deposit_status(dep_id, "DECLINED")
            await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ **STATUS: DECLINED**")
            await app.send_message(dep_req["user_id"], f"❌ **Deposit Declined!**\nYour deposit request for ₹{dep_req['amount']:.2f} was declined by Admin.")
        else:
            await callback.answer("❌ Request already processed!", show_alert=True)

    elif data == "back_menu":
        await callback.message.edit_text(START_MESSAGE, reply_markup=main_menu_markup())

@app.on_message(filters.photo)
async def photo_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id in USER_STATES:
        step = USER_STATES[user_id].get("step")
        
        if step == "awaiting_deposit_proof":
            dep_id = USER_STATES[user_id].get("deposit_id")
            amount = USER_STATES[user_id].get("amount")
            user = await get_user(user_id)
            
            del USER_STATES[user_id]
            await message.reply_text("⏳ Your payment proof has been submitted to Admin for verification. You will be notified once approved!")
            
            admin_caption = (
                f"🔔 **NEW DEPOSIT REQUEST!**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Name:** {user.get('full_name')}\n"
                f"🆔 **User ID:** `{user_id}`\n"
                f"📱 **Mobile:** `{user.get('mobile')}`\n"
                f"💵 **Amount:** ₹{amount:.2f}\n"
                f"🔑 **Deposit ID:** `{dep_id}`"
            )
            admin_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{dep_id}"), InlineKeyboardButton("❌ Decline", callback_data=f"decline_{dep_id}")]
            ])
            await client.send_photo(chat_id=OWNER_ID, photo=message.photo.file_id, caption=admin_caption, reply_markup=admin_keyboard)

        elif step == "awaiting_qr_photo":
            file_path = await message.download()
            img = cv2.imread(file_path)
            scanned_data = None

            try:
                if img is not None:
                    detector = cv2.QRCodeDetector()
                    scanned_data, points, _ = detector.detectAndDecode(img)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

            if scanned_data and "pa=" in scanned_data:
                try:
                    upi_id = scanned_data.split("pa=")[1].split("&")[0]
                except Exception:
                    upi_id = scanned_data
                
                USER_STATES[user_id]["scanned_upi"] = upi_id
                USER_STATES[user_id]["step"] = "pay_amount"
                await message.reply_text(f"✅ QR Code Scanned Successfully!\n📍 UPI ID: `{upi_id}`\n\n💵 Please enter the amount (INR):")
            else:
                await message.reply_text("❌ No valid UPI QR code detected in the image. Please try again or click menu.", reply_markup=main_menu_markup())
                del USER_STATES[user_id]

if __name__ == "__main__":
    app.run()
