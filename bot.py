import os
import uuid
import cv2
import qrcode

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    Message,
    CallbackQuery,
)

from config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    OWNER_ID,
    FORCE_CHANNEL,
    START_MESSAGE,
    START_IMAGE_URL,
    INITIAL_NOTICE_TEXT,
    SUPPORT_USERNAME,
    MONTHLY_FEE,
    COMPANY_UPI,
)

from database import (
    register_user,
    get_user,
    get_all_users,
    set_mpin,
    update_balance,
    update_custom_upi,
    log_transaction,
    get_user_transactions,
    create_deposit_request,
    get_deposit_request,
    update_deposit_status,
)


app = Client(
    "mobile_pay_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

USER_STATES = {}


# =========================
# KEYBOARDS
# =========================

def mobile_share_markup():
    # Contact request button must be a ReplyKeyboard button.
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    "📱 Share Mobile Number",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👤 My Account",
                callback_data="my_account",
            ),
            InlineKeyboardButton(
                "💰 My Balance",
                callback_data="my_balance",
            ),
        ],
        [
            InlineKeyboardButton(
                "💵 Deposit Money",
                callback_data="deposit_money",
            ),
            InlineKeyboardButton(
                "🪪 My UPI / QR",
                callback_data="my_qr",
            ),
        ],
        [
            InlineKeyboardButton(
                "🆔 Create New UPI ID",
                callback_data="create_upi",
            ),
            InlineKeyboardButton(
                "💸 Pay Any UPI",
                callback_data="pay_upi",
            ),
        ],
        [
            InlineKeyboardButton(
                "📷 Scan QR Code",
                callback_data="scan_qr",
            ),
            InlineKeyboardButton(
                "📜 My Transactions",
                callback_data="my_transactions",
            ),
        ],
        [
            InlineKeyboardButton(
                "⚠️ Terms & Charges",
                callback_data="notice",
            ),
            InlineKeyboardButton(
                "🛠️ Support Admin",
                url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}",
            ),
        ],
    ])


def admin_menu_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📊 Bot Statistics",
                callback_data="admin_stats",
            ),
            InlineKeyboardButton(
                "📢 Broadcast Message",
                callback_data="admin_broadcast",
            ),
        ],
        [
            InlineKeyboardButton(
                "➕ Add Balance",
                callback_data="admin_add_balance",
            ),
            InlineKeyboardButton(
                "➖ Deduct Balance",
                callback_data="admin_sub_balance",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 Exit Admin Panel",
                callback_data="back_menu",
            ),
        ],
    ])


def notice_keyboard_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🚀 Start Engine",
                callback_data="open_dashboard",
            ),
        ],
        [
            InlineKeyboardButton(
                "🛠️ Contact Admin Support",
                url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}",
            ),
        ],
    ])


def back_menu_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Back to Main Menu",
                callback_data="back_menu",
            )
        ]
    ])


# =========================
# START COMMAND
# =========================

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id

    try:
        member = await client.get_chat_member(
            FORCE_CHANNEL,
            user_id,
        )

        status = getattr(member.status, "value", member.status)

        if str(status).lower() in ("left", "kicked", "banned"):
            raise ValueError("User has not joined the channel.")

    except Exception:
        channel = str(FORCE_CHANNEL).replace("@", "")

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📢 Join Channel",
                    url=f"https://t.me/{channel}",
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ Verify Join",
                    callback_data="verify_join",
                )
            ],
        ])

        join_text = (
            "⚠️ **Force Join Required!**\n"
            "Please join our official channel first "
            "to use Mobile Pay bot."
        )

        if START_IMAGE_URL:
            await message.reply_photo(
                photo=START_IMAGE_URL,
                caption=join_text,
                reply_markup=keyboard,
            )
        else:
            await message.reply_text(
                join_text,
                reply_markup=keyboard,
            )

        return

    user = await get_user(user_id)

    if not user:
        USER_STATES[user_id] = {
            "step": "awaiting_mobile",
        }

        await message.reply_text(
            "👋 Welcome to **Mobile Pay**!\n"
            "Please share your mobile number for registration:",
            reply_markup=mobile_share_markup(),
        )

    else:
        if START_IMAGE_URL:
            await message.reply_photo(
                photo=START_IMAGE_URL,
                caption=INITIAL_NOTICE_TEXT,
                reply_markup=notice_keyboard_markup(),
            )
        else:
            await message.reply_text(
                INITIAL_NOTICE_TEXT,
                reply_markup=notice_keyboard_markup(),
            )


# =========================
# ADMIN COMMAND
# =========================

@app.on_message(filters.command("admin"))
async def admin_panel_command(client, message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id

    if user_id != OWNER_ID:
        await message.reply_text(
            "❌ Access Denied! "
            "This command is only for the Bot Admin."
        )
        return

    await message.reply_text(
        "👑 **Admin Control Panel**\n"
        "Select an operation below:",
        reply_markup=admin_menu_markup(),
    )


# =========================
# VERIFY FORCE JOIN
# =========================

@app.on_callback_query(filters.regex("^verify_join$"))
async def verify_join_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id

    try:
        member = await client.get_chat_member(
            FORCE_CHANNEL,
            user_id,
        )

        status = getattr(member.status, "value", member.status)

        if str(status).lower() in ("left", "kicked", "banned"):
            await callback.answer(
                "❌ You haven't joined the channel yet!",
                show_alert=True,
            )
            return

    except Exception:
        await callback.answer(
            "❌ Please join the channel first!",
            show_alert=True,
        )
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    user = await get_user(user_id)

    if not user:
        USER_STATES[user_id] = {
            "step": "awaiting_mobile",
        }

        await callback.message.reply_text(
            "✅ Verification Successful!\n"
            "Please share your mobile number to proceed:",
            reply_markup=mobile_share_markup(),
        )

    else:
        if START_IMAGE_URL:
            await callback.message.reply_photo(
                photo=START_IMAGE_URL,
                caption=INITIAL_NOTICE_TEXT,
                reply_markup=notice_keyboard_markup(),
            )
        else:
            await callback.message.reply_text(
                INITIAL_NOTICE_TEXT,
                reply_markup=notice_keyboard_markup(),
            )

    await callback.answer()


# =========================
# CONTACT / MOBILE HANDLER
# =========================

@app.on_message(filters.contact & filters.private)
async def contact_handler(client, message: Message):
    if not message.from_user or not message.contact:
        return

    user_id = message.from_user.id

    if (
        user_id not in USER_STATES
        or USER_STATES[user_id].get("step") != "awaiting_mobile"
    ):
        return

    # Accept only the user's own contact.
    if (
        message.contact.user_id is not None
        and message.contact.user_id != user_id
    ):
        await message.reply_text(
            "❌ कृपया अपना ही मोबाइल नंबर शेयर करें।",
            reply_markup=mobile_share_markup(),
        )
        return

    USER_STATES[user_id]["mobile"] = message.contact.phone_number
    USER_STATES[user_id]["step"] = "awaiting_name"

    await message.reply_text(
        "✅ Mobile number received.\n"
        "Now, please send your full name for your account profile:",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================
# TEXT HANDLER
# =========================

@app.on_message(
    filters.text
    & filters.private
    & ~filters.command(["start", "admin"])
)
async def text_handler(client, message: Message):
    if not message.from_user or not message.text:
        return

    user_id = message.from_user.id
    text = message.text.strip()

    if user_id not in USER_STATES:
        return

    state = USER_STATES[user_id]
    step = state.get("step")

    # -------------------------
    # REGISTER NAME
    # -------------------------

    if step == "awaiting_name":
        if not text:
            await message.reply_text(
                "❌ Please enter your full name."
            )
            return

        full_name = text
        mobile = state.get("mobile")

        if not mobile:
            USER_STATES[user_id] = {
                "step": "awaiting_mobile",
            }
            await message.reply_text(
                "📱 Please share your mobile number first.",
                reply_markup=mobile_share_markup(),
            )
            return

        custom_upi = await register_user(
            user_id,
            full_name,
            mobile,
        )

        USER_STATES[user_id] = {
            "step": "setting_mpin",
        }

        await message.reply_text(
            f"🎉 Account Created Successfully!\n"
            f"Your UPI ID: `{custom_upi}`\n\n"
            "Now, please set a secure **4-digit M-PIN** "
            "(e.g. `1234`) for transactions:"
        )

    # -------------------------
    # SET M-PIN
    # -------------------------

    elif step == "setting_mpin":
        if not text.isdigit() or len(text) != 4:
            await message.reply_text(
                "❌ Invalid M-PIN format. "
                "Please enter exactly **4 digits** (e.g. `1234`):"
            )
            return

        await set_mpin(user_id, text)
        USER_STATES.pop(user_id, None)

        await message.reply_text(
            "✅ M-PIN set successfully!\n\n"
            + INITIAL_NOTICE_TEXT,
            reply_markup=notice_keyboard_markup(),
        )

    # -------------------------
    # CREATE CUSTOM UPI ID
    # -------------------------

    elif step == "creating_upi":
        clean_name = "".join(
            char for char in text.lower()
            if char.isalnum() or char in "._-"
        )

        if not clean_name:
            await message.reply_text(
                "❌ Invalid UPI name. Please try again."
            )
            return

        new_upi = f"{clean_name}@mbp"

        await update_custom_upi(user_id, new_upi)
        USER_STATES.pop(user_id, None)

        await message.reply_text(
            "✅ New UPI ID Created Successfully!\n"
            f"📍 `{new_upi}`",
            reply_markup=back_menu_markup(),
        )

    # -------------------------
    # DEPOSIT AMOUNT
    # -------------------------

    elif step == "awaiting_deposit_amount":
        try:
            amount = float(text)

            if amount <= 0:
                raise ValueError

        except ValueError:
            await message.reply_text(
                "❌ Invalid amount. Enter a valid number:"
            )
            return

        deposit_id = str(uuid.uuid4())[:8]

        await create_deposit_request(
            deposit_id,
            user_id,
            amount,
        )

        USER_STATES[user_id] = {
            "step": "awaiting_deposit_proof",
            "deposit_id": deposit_id,
            "amount": amount,
        }

        qr_path = f"deposit_{deposit_id}.png"

        try:
            qr_data = (
                f"upi://pay?pa={COMPANY_UPI}"
                f"&am={amount:.2f}&pn=MobilePay"
            )

            img = qrcode.make(qr_data)
            img.save(qr_path)

            await message.reply_photo(
                photo=qr_path,
                caption=(
                    "💵 **Deposit Request Generated**\n"
                    f"Amount: ₹{amount:.2f}\n"
                    f"UPI ID: `{COMPANY_UPI}`\n\n"
                    "Scan the QR code and pay. Once paid, "
                    "send the payment screenshot/receipt here:"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🔙 Cancel",
                            callback_data="back_menu",
                        )
                    ]
                ]),
            )

        finally:
            if os.path.exists(qr_path):
                os.remove(qr_path)

    # -------------------------
    # ENTER RECIPIENT UPI
    # -------------------------

    elif step == "pay_upi_id":
        if "@" not in text or " " in text:
            await message.reply_text(
                "❌ Please enter a valid-looking UPI ID, "
                "for example `merchant@bank`."
            )
            return

        USER_STATES[user_id]["recipient_upi"] = text
        USER_STATES[user_id]["step"] = "pay_amount"

        await message.reply_text(
            "💵 Please enter the amount (INR) you wish to send:"
        )

    # -------------------------
    # ENTER PAYMENT AMOUNT
    # -------------------------

    elif step == "pay_amount":
        try:
            amount = float(text)

            if amount <= 0:
                raise ValueError

        except ValueError:
            await message.reply_text(
                "❌ Invalid amount. Please enter a valid number:"
            )
            return

        USER_STATES[user_id]["amount"] = amount
        USER_STATES[user_id]["step"] = "pay_mpin"

        await message.reply_text(
            "🔐 Please enter your **4-digit M-PIN** "
            "to authorize this wallet operation:"
        )

    # -------------------------
    # CHECK M-PIN
    # -------------------------

    elif step == "pay_mpin":
        user = await get_user(user_id)

        if not user:
            USER_STATES.pop(user_id, None)
            await message.reply_text(
                "❌ आपका अकाउंट नहीं मिला। कृपया /start करें।"
            )
            return

        if user.get("mpin") != text:
            USER_STATES.pop(user_id, None)

            await message.reply_text(
                "❌ Incorrect M-PIN. Operation cancelled.",
                reply_markup=main_menu_markup(),
            )
            return

        amount = state.get("amount")
        recipient = (
            state.get("recipient_upi")
            or state.get("scanned_upi")
        )

        if amount is None or not recipient:
            USER_STATES.pop(user_id, None)
            await message.reply_text(
                "❌ Payment details missing. Please try again.",
                reply_markup=main_menu_markup(),
            )
            return

        balance = float(user.get("balance", 0) or 0)

        if balance < amount:
            USER_STATES.pop(user_id, None)

            await message.reply_text(
                "❌ Insufficient balance in your wallet!",
                reply_markup=main_menu_markup(),
            )
            return

        # This updates the internal wallet balance only.
        # It does not perform an actual UPI bank transfer.
        await update_balance(user_id, -amount)

        await log_transaction(
            user_id,
            "DEBIT",
            amount,
            recipient,
            "SUCCESS",
        )

        USER_STATES.pop(user_id, None)

        receipt = (
            "✅ **Wallet Operation Recorded**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **To:** `{recipient}`\n"
            f"💰 **Amount:** ₹{amount:.2f}\n"
            "🏢 **Company Fee:** ₹0.00\n"
            "🕒 **Status:** RECORDED IN INTERNAL WALLET\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ This bot has not sent an actual UPI transfer."
        )

        await message.reply_text(
            receipt,
            reply_markup=main_menu_markup(),
        )

    # -------------------------
    # ADMIN BROADCAST
    # -------------------------

    elif step == "admin_awaiting_broadcast":
        if user_id != OWNER_ID:
            USER_STATES.pop(user_id, None)
            return

        all_users = await get_all_users()
        sent = 0
        failed = 0

        status_msg = await message.reply_text(
            "⏳ Broadcasting message to all users..."
        )

        for user_data in all_users:
            try:
                await app.send_message(
                    user_data["user_id"],
                    f"📢 **ADMIN ANNOUNCEMENT**\n\n{text}",
                )
                sent += 1

            except Exception:
                failed += 1

        USER_STATES.pop(user_id, None)

        await status_msg.edit_text(
            "✅ **Broadcast Completed!**\n"
            f"• Total Sent: {sent}\n"
            f"• Failed: {failed}",
            reply_markup=admin_menu_markup(),
        )

    # -------------------------
    # ADMIN ADD BALANCE
    # -------------------------

    elif step == "admin_awaiting_add_bal":
        if user_id != OWNER_ID:
            USER_STATES.pop(user_id, None)
            return

        try:
            parts = text.split()

            if len(parts) != 2:
                raise ValueError(
                    "Use format: USER_ID AMOUNT"
                )

            target_id = int(parts[0])
            amount = float(parts[1])

            if amount <= 0:
                raise ValueError(
                    "Amount must be greater than zero."
                )

            target_user = await get_user(target_id)

            if not target_user:
                raise ValueError("User not found.")

            await update_balance(target_id, amount)

            await log_transaction(
                target_id,
                "CREDIT_ADMIN",
                amount,
                "ADMIN",
                "SUCCESS",
            )

            await message.reply_text(
                f"✅ Added ₹{amount:.2f} "
                f"to User ID: `{target_id}`",
                reply_markup=admin_menu_markup(),
            )

            try:
                await app.send_message(
                    target_id,
                    "🎉 **Wallet Credited!**\n"
                    f"Admin added ₹{amount:.2f} "
                    "to your Mobile Pay wallet.",
                )
            except Exception:
                pass

            USER_STATES.pop(user_id, None)

        except Exception as e:
            await message.reply_text(
                "❌ Error! Use format: `USER_ID AMOUNT`\n"
                f"Details: {e}"
            )

    # -------------------------
    # ADMIN DEDUCT BALANCE
    # -------------------------

    elif step == "admin_awaiting_sub_bal":
        if user_id != OWNER_ID:
            USER_STATES.pop(user_id, None)
            return

        try:
            parts = text.split()

            if len(parts) != 2:
                raise ValueError(
                    "Use format: USER_ID AMOUNT"
                )

            target_id = int(parts[0])
            amount = float(parts[1])

            if amount <= 0:
                raise ValueError(
                    "Amount must be greater than zero."
                )

            target_user = await get_user(target_id)

            if not target_user:
                raise ValueError("User not found.")

            current_balance = float(
                target_user.get("balance", 0) or 0
            )

            if amount > current_balance:
                raise ValueError(
                    "Amount is greater than the user's current balance."
                )

            await update_balance(target_id, -amount)

            await log_transaction(
                target_id,
                "DEBIT_ADMIN",
                amount,
                "ADMIN",
                "SUCCESS",
            )

            await message.reply_text(
                f"✅ Deducted ₹{amount:.2f} "
                f"from User ID: `{target_id}`",
                reply_markup=admin_menu_markup(),
            )

            try:
                await app.send_message(
                    target_id,
                    "⚠️ **Wallet Debited**\n"
                    f"Admin deducted ₹{amount:.2f} "
                    "from your Mobile Pay wallet.",
                )
            except Exception:
                pass

            USER_STATES.pop(user_id, None)

        except Exception as e:
            await message.reply_text(
                "❌ Error! Use format: `USER_ID AMOUNT`\n"
                f"Details: {e}"
            )


# =========================
# CALLBACK HANDLER
# =========================

@app.on_callback_query()
async def callback_handler(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data or ""

    # Restrict admin callbacks to the owner.
    admin_callbacks = {
        "admin_stats",
        "admin_broadcast",
        "admin_add_balance",
        "admin_sub_balance",
    }

    if data in admin_callbacks and user_id != OWNER_ID:
        await callback.answer(
            "❌ Access denied.",
            show_alert=True,
        )
        return

    user = await get_user(user_id)

    if data == "open_dashboard":
        await callback.answer()

        try:
            await callback.message.delete()
        except Exception:
            pass

        await client.send_message(
            user_id,
            START_MESSAGE,
            reply_markup=main_menu_markup(),
        )

    elif data == "my_account":
        if not user:
            await callback.answer(
                "❌ Account not found. Please use /start.",
                show_alert=True,
            )
            return

        await callback.message.edit_text(
            "👤 **Account Details**\n\n"
            f"• Name: {user.get('full_name', 'N/A')}\n"
            f"• Mobile: {user.get('mobile', 'N/A')}\n"
            f"• Primary UPI: `{user.get('custom_upi', 'N/A')}`\n"
            "• KYC Status: Not verified by this bot",
            reply_markup=back_menu_markup(),
        )

    elif data == "my_balance":
        if not user:
            await callback.answer(
                "❌ Account not found.",
                show_alert=True,
            )
            return

        balance = float(user.get("balance", 0) or 0)

        await callback.message.edit_text(
            "💰 **Wallet Balance**\n\n"
            f"Available Balance: **₹{balance:.2f}**",
            reply_markup=back_menu_markup(),
        )

    elif data == "deposit_money":
        if not user:
            await callback.answer(
                "❌ Account not found. Please use /start.",
                show_alert=True,
            )
            return

        USER_STATES[user_id] = {
            "step": "awaiting_deposit_amount",
        }

        await callback.message.edit_text(
            "💵 Enter the amount (INR) you wish to add to your wallet:"
        )

    elif data == "my_qr":
        if not user:
            await callback.answer(
                "❌ Account not found.",
                show_alert=True,
            )
            return

        upi = user.get("custom_upi")

        if not upi:
            await callback.answer(
                "❌ UPI ID not found.",
                show_alert=True,
            )
            return

        qr_img_path = f"qr_{user_id}.png"

        try:
            qr_data = (
                f"upi://pay?pa={upi}"
                f"&pn={user.get('full_name', 'MobilePay')}"
            )

            img = qrcode.make(qr_data)
            img.save(qr_img_path)

            try:
                await callback.message.delete()
            except Exception:
                pass

            await client.send_photo(
                chat_id=user_id,
                photo=qr_img_path,
                caption=(
                    "🪪 **Your Mobile Pay QR & UPI**\n"
                    f"UPI ID: `{upi}`\n"
                    "यह QR कोड UPI ID दिखाता है। "
                    "वास्तविक भुगतान आपके बैंक/UPI प्रदाता पर निर्भर है।"
                ),
                reply_markup=back_menu_markup(),
            )

        finally:
            if os.path.exists(qr_img_path):
                os.remove(qr_img_path)

    elif data == "create_upi":
        if not user:
            await callback.answer(
                "❌ Account not found.",
                show_alert=True,
            )
            return

        USER_STATES[user_id] = {
            "step": "creating_upi",
        }

        await callback.message.edit_text(
            "🆔 Send your desired custom ID name/number "
            "(e.g. `hakeeb07`) to generate your new `@mbp` ID:",
            reply_markup=back_menu_markup(),
        )

    elif data == "pay_upi":
        if not user:
            await callback.answer(
                "❌ Account not found.",
                show_alert=True,
            )
            return

        USER_STATES[user_id] = {
            "step": "pay_upi_id",
        }

        await callback.message.edit_text(
            "💸 Send the recipient UPI ID "
            "(e.g. `merchant@paytm`):",
            reply_markup=back_menu_markup(),
        )

    elif data == "scan_qr":
        if not user:
            await callback.answer(
                "❌ Account not found.",
                show_alert=True,
            )
            return

        USER_STATES[user_id] = {
            "step": "awaiting_qr_photo",
        }

        await callback.message.edit_text(
            "📷 Please send the QR code photo/screenshot to scan:",
            reply_markup=back_menu_markup(),
        )

    elif data == "my_transactions":
        if not user:
            await callback.answer(
                "❌ Account not found.",
                show_alert=True,
            )
            return

        txs = await get_user_transactions(user_id)

        tx_text = (
            "📜 **Recent Transactions**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
        )

        if not txs:
            tx_text += "No transactions found."
        else:
            for tx in txs:
                tx_text += (
                    f"• {tx.get('type', 'N/A')} | "
                    f"₹{tx.get('amount', 0)} | "
                    f"To: {tx.get('recipient', 'N/A')} | "
                    f"{tx.get('status', 'N/A')}\n"
                )

        await callback.message.edit_text(
            tx_text,
            reply_markup=back_menu_markup(),
        )

    elif data == "notice":
        notice_text = (
            "⚠️ **Terms & Subscription Notice**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"• Monthly subscription fee: ₹{MONTHLY_FEE}.\n"
            "• This bot's wallet records do not themselves "
            "perform real-time bank transfers.\n"
            "• Keep your M-PIN secure and confidential."
        )

        await callback.message.edit_text(
            notice_text,
            reply_markup=back_menu_markup(),
        )

    elif data == "admin_stats":
        all_users = await get_all_users()

        total_balance = sum(
            float(u.get("balance", 0) or 0)
            for u in all_users
        )

        await callback.message.edit_text(
            "📊 **Bot Statistics**\n\n"
            f"• Total Users: {len(all_users)}\n"
            f"• Total System Balance: ₹{total_balance:.2f}",
            reply_markup=admin_menu_markup(),
        )

    elif data == "admin_broadcast":
        USER_STATES[user_id] = {
            "step": "admin_awaiting_broadcast",
        }

        await callback.message.edit_text(
            "📢 Send the broadcast message text you wish to send "
            "to all registered users:"
        )

    elif data == "admin_add_balance":
        USER_STATES[user_id] = {
            "step": "admin_awaiting_add_bal",
        }

        await callback.message.edit_text(
            "➕ Send `USER_ID AMOUNT` (e.g. `123456789 500`):"
        )

    elif data == "admin_sub_balance":
        USER_STATES[user_id] = {
            "step": "admin_awaiting_sub_bal",
        }

        await callback.message.edit_text(
            "➖ Send `USER_ID AMOUNT` to deduct balance "
            "(e.g. `123456789 100`):"
        )

    elif data.startswith("approve_"):
        if user_id != OWNER_ID:
            await callback.answer(
                "❌ Access denied.",
                show_alert=True,
            )
            return

        dep_id = data[len("approve_"):]
        dep_req = await get_deposit_request(dep_id)

        if dep_req and dep_req.get("status") == "PENDING":
            await update_deposit_status(dep_id, "APPROVED")

            await update_balance(
                dep_req["user_id"],
                dep_req["amount"],
            )

            await log_transaction(
                dep_req["user_id"],
                "CREDIT_DEPOSIT",
                dep_req["amount"],
                "DEPOSIT",
                "SUCCESS",
            )

            try:
                await callback.message.edit_caption(
                    caption=(
                        (callback.message.caption or "")
                        + "\n\n✅ **STATUS: APPROVED**"
                    )
                )
            except Exception:
                pass

            await app.send_message(
                dep_req["user_id"],
                "✅ **Deposit Approved!**\n"
                f"₹{dep_req['amount']:.2f} has been added "
                "to your internal wallet balance.",
            )

            await callback.answer("Deposit approved.")

        else:
            await callback.answer(
                "❌ Request already processed or not found!",
                show_alert=True,
            )

    elif data.startswith("decline_"):
        if user_id != OWNER_ID:
            await callback.answer(
                "❌ Access denied.",
                show_alert=True,
            )
            return

        dep_id = data[len("decline_"):]
        dep_req = await get_deposit_request(dep_id)

        if dep_req and dep_req.get("status") == "PENDING":
            await update_deposit_status(dep_id, "DECLINED")

            try:
                await callback.message.edit_caption(
                    caption=(
                        (callback.message.caption or "")
                        + "\n\n❌ **STATUS: DECLINED**"
                    )
                )
            except Exception:
                pass

            await app.send_message(
                dep_req["user_id"],
                "❌ **Deposit Declined!**\n"
                f"Your deposit request for ₹{dep_req['amount']:.2f} "
                "was declined by Admin.",
            )

            await callback.answer("Deposit declined.")

        else:
            await callback.answer(
                "❌ Request already processed or not found!",
                show_alert=True,
            )

    elif data == "back_menu":
        USER_STATES.pop(user_id, None)

        try:
            if callback.message.photo:
                await callback.message.edit_caption(
                    START_MESSAGE,
                    reply_markup=main_menu_markup(),
                )
            else:
                await callback.message.edit_text(
                    START_MESSAGE,
                    reply_markup=main_menu_markup(),
                )

        except Exception:
            await client.send_message(
                user_id,
                START_MESSAGE,
                reply_markup=main_menu_markup(),
            )

        await callback.answer()

    else:
        await callback.answer()


# =========================
# PHOTO HANDLER
# =========================

@app.on_message(filters.photo & filters.private)
async def photo_handler(client, message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id

    if user_id not in USER_STATES:
        return

    step = USER_STATES[user_id].get("step")

    # -------------------------
    # DEPOSIT PAYMENT PROOF
    # -------------------------

    if step == "awaiting_deposit_proof":
        dep_id = USER_STATES[user_id].get("deposit_id")
        amount = USER_STATES[user_id].get("amount")

        user = await get_user(user_id)

        if not dep_id or amount is None:
            USER_STATES.pop(user_id, None)
            await message.reply_text(
                "❌ Deposit request not found. Please try again."
            )
            return

        USER_STATES.pop(user_id, None)

        await message.reply_text(
            "⏳ Your payment proof has been submitted to Admin "
            "for verification. You will be notified once reviewed."
        )

        admin_caption = (
            "🔔 **NEW DEPOSIT REQUEST!**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** {user.get('full_name', 'N/A') if user else 'N/A'}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📱 **Mobile:** `{user.get('mobile', 'N/A') if user else 'N/A'}`\n"
            f"💵 **Amount:** ₹{amount:.2f}\n"
            f"🔑 **Deposit ID:** `{dep_id}`"
        )

        admin_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Approve",
                    callback_data=f"approve_{dep_id}",
                ),
                InlineKeyboardButton(
                    "❌ Decline",
                    callback_data=f"decline_{dep_id}",
                ),
            ]
        ])

        await client.send_photo(
            chat_id=OWNER_ID,
            photo=message.photo.file_id,
            caption=admin_caption,
            reply_markup=admin_keyboard,
        )

    # -------------------------
    # SCAN UPI QR CODE
    # -------------------------

    elif step == "awaiting_qr_photo":
        file_path = await message.download()
        scanned_data = None

        try:
            img = cv2.imread(file_path)

            if img is not None:
                detector = cv2.QRCodeDetector()
                scanned_data, points, _ = detector.detectAndDecode(img)

        except Exception as e:
            print(f"QR scan error: {e}")

        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

        if scanned_data and "pa=" in scanned_data:
            try:
                upi_id = (
                    scanned_data.split("pa=", 1)[1]
                    .split("&", 1)[0]
                )
            except Exception:
                upi_id = scanned_data

            USER_STATES[user_id]["scanned_upi"] = upi_id
            USER_STATES[user_id]["step"] = "pay_amount"

            await message.reply_text(
                "✅ QR Code Scanned Successfully!\n"
                f"📍 UPI ID: `{upi_id}`\n\n"
                "💵 Please enter the amount (INR):"
            )

        else:
            await message.reply_text(
                "❌ No valid UPI QR code detected in the image. "
                "Please try again or click menu.",
                reply_markup=main_menu_markup(),
            )

            USER_STATES.pop(user_id, None)


# =========================
# RUN BOT
# =========================

if __name__ == "__main__":
    app.run()
