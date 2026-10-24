import os
import uuid
from urllib.parse import urlencode, urlparse, parse_qs, unquote

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


# ==========================================
# WELCOME MESSAGE
# ==========================================

WELCOME_MESSAGE = (
    "✨ **WELCOME TO MOBILE PAY** ✨\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "💙 Your smarter digital payment companion starts here.\n\n"
    "🚀 **SMART • SIMPLE • USER-FRIENDLY**\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "💳 Manage your account in one place\n"
    "📱 Register with your mobile number\n"
    "🔐 Set your personal 4-digit M-PIN\n"
    "📷 Generate and scan UPI QR codes\n"
    "💰 Submit deposit requests and view wallet records\n"
    "📜 Review your transaction history\n"
    "🛠️ Get help whenever you need it\n\n"
    "🌟 **YOUR PAYMENTS. YOUR CONTROL.**\n"
    "Built to make your payment experience simple, clear, "
    "and convenient.\n\n"
    "🔒 Always verify the recipient and amount in your UPI app "
    "before authorizing a payment.\n\n"
    "👇 Tap below to explore Mobile Pay."
)

SUPPORT_URL = (
    "https://t.me/" + str(SUPPORT_USERNAME).lstrip("@")
)


# ==========================================
# HELPERS
# ==========================================

def money(value):
    return float(value or 0)


def valid_amount(value):
    try:
        amount = float(value)
        if amount <= 0 or amount > 10000000:
            return None
        return round(amount, 2)
    except (ValueError, TypeError):
        return None


def valid_upi(upi):
    if not upi:
        return False

    upi = upi.strip()

    if len(upi) > 100 or " " in upi:
        return False

    if upi.count("@") != 1:
        return False

    handle, provider = upi.split("@", 1)

    return bool(handle and provider)


def make_upi_uri(upi, name="Mobile Pay", amount=None, note=None):
    """
    Standard UPI payment intent.
    Recipient must be a real, active UPI ID.
    Generating this URI does not verify or send payment.
    """
    if not valid_upi(upi):
        raise ValueError(
            "Configured recipient is not a valid-looking UPI ID."
        )

    params = {
        "pa": upi.strip(),
        "pn": name[:80],
        "cu": "INR",
    }

    if amount is not None:
        amount = valid_amount(amount)
        if amount is None:
            raise ValueError("Invalid payment amount.")

        params["am"] = f"{amount:.2f}"

    if note:
        params["tn"] = note[:80]

    return "upi://pay?" + urlencode(params)


def make_qr_file(data, filename):
    img = qrcode.make(data)
    img.save(filename)
    return filename


def main_menu_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👤 My Account", callback_data="my_account"
            ),
            InlineKeyboardButton(
                "💰 My Balance", callback_data="my_balance"
            ),
        ],
        [
            InlineKeyboardButton(
                "💵 Deposit Money", callback_data="deposit_money"
            ),
            InlineKeyboardButton(
                "🪪 My UPI / QR", callback_data="my_qr"
            ),
        ],
        [
            InlineKeyboardButton(
                "🆔 Create New UPI ID", callback_data="create_upi"
            ),
            InlineKeyboardButton(
                "💸 Pay Any UPI", callback_data="pay_upi"
            ),
        ],
        [
            InlineKeyboardButton(
                "📷 Scan QR Code", callback_data="scan_qr"
            ),
            InlineKeyboardButton(
                "📜 My Transactions", callback_data="my_transactions"
            ),
        ],
        [
            InlineKeyboardButton(
                "⚠️ Terms & Charges", callback_data="notice"
            ),
            InlineKeyboardButton(
                "🛠️ Support Admin", url=SUPPORT_URL
            ),
        ],
    ])


def admin_menu_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📊 Bot Statistics", callback_data="admin_stats"
            ),
            InlineKeyboardButton(
                "📢 Broadcast", callback_data="admin_broadcast"
            ),
        ],
        [
            InlineKeyboardButton(
                "➕ Add Balance", callback_data="admin_add_balance"
            ),
            InlineKeyboardButton(
                "➖ Deduct Balance", callback_data="admin_sub_balance"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 Exit Admin Panel", callback_data="back_menu"
            ),
        ],
    ])


def welcome_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🚀 OPEN MOBILE PAY", callback_data="open_dashboard"
            ),
        ],
        [
            InlineKeyboardButton(
                "🛠️ Contact Support", url=SUPPORT_URL
            ),
        ],
    ])


def back_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Back to Main Menu", callback_data="back_menu"
            ),
        ],
    ])


def contact_markup():
    return ReplyKeyboardMarkup(
        [[
            KeyboardButton(
                "📱 Share Mobile Number",
                request_contact=True,
            )
        ]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def send_welcome(client, chat_id):
    if START_IMAGE_URL:
        await client.send_photo(
            chat_id=chat_id,
            photo=START_IMAGE_URL,
            caption=WELCOME_MESSAGE,
            reply_markup=welcome_markup(),
        )
    else:
        await client.send_message(
            chat_id=chat_id,
            text=WELCOME_MESSAGE,
            reply_markup=welcome_markup(),
        )


async def send_registration_prompt(message):
    if START_IMAGE_URL:
        await message.reply_photo(
            photo=START_IMAGE_URL,
            caption=(
                WELCOME_MESSAGE
                + "\n\n📲 **First Step:** To register, "
                "share your mobile number below."
            ),
        )

    await message.reply_text(
        "📱 **Share Mobile Number**\n\n"
        "To continue registration, use the button below to "
        "share your Telegram contact.",
        reply_markup=contact_markup(),
    )


async def send_main_menu(client, chat_id):
    await client.send_message(
        chat_id,
        START_MESSAGE or WELCOME_MESSAGE,
        reply_markup=main_menu_markup(),
    )


# ==========================================
# START / FORCE JOIN
# ==========================================

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id

    try:
        member = await client.get_chat_member(FORCE_CHANNEL, user_id)
        status = getattr(member.status, "value", member.status)

        if str(status).lower() in ("left", "kicked", "banned"):
            raise ValueError("Channel membership required")

    except Exception:
        channel = str(FORCE_CHANNEL).lstrip("@")

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📢 Join Official Channel",
                    url=f"https://t.me/{channel}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "✅ Verify Join", callback_data="verify_join"
                ),
            ],
        ])

        text = (
            "⚠️ **CHANNEL JOIN REQUIRED**\n\n"
            "Before using Mobile Pay, please join our "
            "official channel."
        )

        if START_IMAGE_URL:
            await message.reply_photo(
                photo=START_IMAGE_URL,
                caption=text,
                reply_markup=keyboard,
            )
        else:
            await message.reply_text(
                text,
                reply_markup=keyboard,
            )

        return

    user = await get_user(user_id)

    if not user:
        USER_STATES[user_id] = {"step": "awaiting_mobile"}
        await send_registration_prompt(message)
    else:
        await send_welcome(client, user_id)


@app.on_message(filters.command("admin") & filters.private)
async def admin_panel_command(client, message: Message):
    if not message.from_user:
        return

    if message.from_user.id != OWNER_ID:
        await message.reply_text("❌ Access Denied.")
        return

    await message.reply_text(
        "👑 **MOBILE PAY ADMIN PANEL**\n"
        "Choose an action below:",
        reply_markup=admin_menu_markup(),
    )


@app.on_callback_query(filters.regex("^verify_join$"))
async def verify_join_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id

    try:
        member = await client.get_chat_member(FORCE_CHANNEL, user_id)
        status = getattr(member.status, "value", member.status)

        if str(status).lower() in ("left", "kicked", "banned"):
            await callback.answer(
                "Please join the channel first.",
                show_alert=True,
            )
            return

    except Exception:
        await callback.answer(
            "Please join the channel first.",
            show_alert=True,
        )
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    user = await get_user(user_id)

    if not user:
        USER_STATES[user_id] = {"step": "awaiting_mobile"}
        await callback.message.reply_text(
            "✅ Channel verification successful."
        )
        await callback.message.reply_text(
            "to register, share your mobile number:",
            reply_markup=contact_markup(),
        )
    else:
        await send_welcome(client, user_id)

    await callback.answer()


# ==========================================
# CONTACT REGISTRATION
# ==========================================

@app.on_message(filters.contact & filters.private)
async def contact_handler(client, message: Message):
    if not message.from_user or not message.contact:
        return

    user_id = message.from_user.id
    state = USER_STATES.get(user_id, {})

    if state.get("step") != "awaiting_mobile":
        return

    contact_user_id = message.contact.user_id

    if contact_user_id and contact_user_id != user_id:
        await message.reply_text(
            "❌ Please share your own mobile number.",
            reply_markup=contact_markup(),
        )
        return

    state["mobile"] = message.contact.phone_number
    state["step"] = "awaiting_name"

    await message.reply_text(
        "✅ Mobile number received.\n\n"
        "Now send your full name:",
        reply_markup=ReplyKeyboardRemove(),
    )


# ==========================================
# TEXT / REGISTRATION / PAYMENT FLOW
# ==========================================

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
    state = USER_STATES.get(user_id)

    if not state:
        return

    step = state.get("step")

    # New account: full name
    if step == "awaiting_name":
        mobile = state.get("mobile")

        if not mobile:
            USER_STATES[user_id] = {"step": "awaiting_mobile"}
            await message.reply_text(
                "Please share your mobile number first.",
                reply_markup=contact_markup(),
            )
            return

        custom_upi = await register_user(user_id, text, mobile)

        USER_STATES[user_id] = {"step": "setting_mpin"}

        await message.reply_text(
            "🎉 **ACCOUNT CREATED!**\n\n"
            f"Account ID: `{user_id}`\n"
            f"Database UPI field: `{custom_upi}`\n\n"
            "⚠️ Do not treat the custom UPI ID stored in the database as a "
            "real bank UPI ID unless a bank/UPI provider "
            "has verified it.\n\n"
            "Now set your 4-digit M-PIN:"
        )
        return

    # Set M-PIN
    if step == "setting_mpin":
        if not text.isdigit() or len(text) != 4:
            await message.reply_text(
                "❌ The M-PIN must contain exactly 4 digits."
            )
            return

        await set_mpin(user_id, text)
        USER_STATES.pop(user_id, None)

        await message.reply_text(
            "✅ Your M-PIN has been set.\n\n"
            + INITIAL_NOTICE_TEXT,
            reply_markup=welcome_markup(),
        )
        return

    # Create custom database UPI label
    if step == "creating_upi":
        clean_name = "".join(
            c for c in text.lower()
            if c.isalnum() or c in "._-"
        )

        if not clean_name:
            await message.reply_text(
                "❌ Please send a valid name or number."
            )
            return

        new_upi = f"{clean_name}@mbp"
        await update_custom_upi(user_id, new_upi)
        USER_STATES.pop(user_id, None)

        await message.reply_text(
            f"✅ Database ID updated: `{new_upi}`\n\n"
            "⚠️ This is only a custom app ID. It does not automatically create a "
            "real UPI ID or bank account.",
            reply_markup=back_markup(),
        )
        return

    # Deposit amount
    if step == "awaiting_deposit_amount":
        amount = valid_amount(text)

        if amount is None:
            await message.reply_text(
                "❌ Enter a valid amount, such as 100 or 250.50."
            )
            return

        if not valid_upi(COMPANY_UPI):
            await message.reply_text(
                "❌ COMPANY_UPI is not configured correctly. "
                "Set your bank-linked UPI ID in Heroku Config Vars."
            )
            return

        deposit_id = str(uuid.uuid4())[:8]
        await create_deposit_request(deposit_id, user_id, amount)

        USER_STATES[user_id] = {
            "step": "awaiting_deposit_proof",
            "deposit_id": deposit_id,
            "amount": amount,
        }

        qr_path = f"deposit_{deposit_id}.png"

        try:
            uri = make_upi_uri(
                COMPANY_UPI,
                name="Mobile Pay",
                amount=amount,
                note=f"Deposit {deposit_id}",
            )
            make_qr_file(uri, qr_path)

            await message.reply_photo(
                photo=qr_path,
                caption=(
                    "💵 **DEPOSIT PAYMENT QR**\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"💰 Amount: ₹{amount:.2f}\n"
                    f"🏦 UPI ID: `{COMPANY_UPI}`\n"
                    f"🆔 Request ID: `{deposit_id}`\n\n"
                    "1. Scan the QR code using your UPI app.\n"
                    "2. Verify the UPI ID and amount in the app.\n"
                    "3. After completing payment, send the receipt/screenshot.\n\n"
                    "⚠️ The admin must verify the payment. Generating a QR code is "
                    "not proof of a successful payment."
                ),
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🔙 Cancel", callback_data="back_menu"
                        )
                    ]
                ]),
            )

        finally:
            if os.path.exists(qr_path):
                os.remove(qr_path)

        return

    # Recipient UPI ID
    if step == "pay_upi_id":
        if not valid_upi(text):
            await message.reply_text(
                "❌ Enter a valid UPI ID, such as `name@bank`."
            )
            return

        state["recipient_upi"] = text
        state["step"] = "pay_amount"

        await message.reply_text(
            "💵 Now send the payment amount in INR:"
        )
        return

    # Payment amount
    if step == "pay_amount":
        amount = valid_amount(text)

        if amount is None:
            await message.reply_text(
                "❌ Enter a valid amount, such as 100 or 250.50."
            )
            return

        state["amount"] = amount
        state["step"] = "pay_mpin"

        await message.reply_text(
            "🔐 Enter your 4-digit M-PIN to continue:"
        )
        return

    # M-PIN verification, then generate a real UPI intent QR
    if step == "pay_mpin":
        user = await get_user(user_id)

        if not user:
            USER_STATES.pop(user_id, None)
            await message.reply_text(
                "❌ Account not found. Please use /start."
            )
            return

        if str(user.get("mpin", "")) != text:
            USER_STATES.pop(user_id, None)
            await message.reply_text(
                "❌ Incorrect M-PIN. The operation has been cancelled.",
                reply_markup=main_menu_markup(),
            )
            return

        amount = state.get("amount")
        recipient = state.get("recipient_upi") or state.get("scanned_upi")

        if not amount or not valid_upi(recipient):
            USER_STATES.pop(user_id, None)
            await message.reply_text(
                "❌ The payment details are invalid. Please try again.",
                reply_markup=main_menu_markup(),
            )
            return

        # No wallet debit here: without a payment API this bot
        # cannot send money or confirm an external UPI transaction.
        qr_path = f"pay_{uuid.uuid4().hex[:8]}.png"

        try:
            uri = make_upi_uri(
                recipient,
                name="UPI Payment",
                amount=amount,
                note="Payment via Mobile Pay",
            )
            make_qr_file(uri, qr_path)

            await message.reply_photo(
                photo=qr_path,
                caption=(
                    "💸 **UPI PAYMENT QR READY**\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 Recipient: `{recipient}`\n"
                    f"💰 Amount: ₹{amount:.2f}\n\n"
                    "1. Scan the QR code using your bank/UPI app.\n"
                    "2. Carefully verify the recipient and amount.\n"
                    "3. Authorize the payment yourself in your UPI app.\n\n"
                    "⚠️ Mobile Pay has not sent any money, and this bot "
                    "does not have a payment API. Without payment verification, "
                    "the payment cannot be marked as SUCCESS."
                ),
                reply_markup=main_menu_markup(),
            )

            await log_transaction(
                user_id,
                "UPI_QR_GENERATED",
                amount,
                recipient,
                "PENDING_EXTERNAL_PAYMENT",
            )

        finally:
            if os.path.exists(qr_path):
                os.remove(qr_path)

        USER_STATES.pop(user_id, None)
        return

    # Admin broadcast
    if step == "admin_awaiting_broadcast":
        if user_id != OWNER_ID:
            USER_STATES.pop(user_id, None)
            return

        users = await get_all_users()
        sent = 0
        failed = 0

        status_message = await message.reply_text(
            "⏳ Sending broadcast..."
        )

        for item in users:
            try:
                await app.send_message(
                    item["user_id"],
                    f"📢 **ADMIN ANNOUNCEMENT**\n\n{text}",
                )
                sent += 1
            except Exception:
                failed += 1

        USER_STATES.pop(user_id, None)

        await status_message.edit_text(
            "✅ **Broadcast Complete**\n"
            f"• Sent: {sent}\n"
            f"• Failed: {failed}",
            reply_markup=admin_menu_markup(),
        )
        return

    # Admin add balance
    if step == "admin_awaiting_add_bal":
        if user_id != OWNER_ID:
            USER_STATES.pop(user_id, None)
            return

        try:
            parts = text.split()
            if len(parts) != 2:
                raise ValueError("Please enter USER_ID AMOUNT.")

            target_id = int(parts[0])
            amount = valid_amount(parts[1])

            if amount is None:
                raise ValueError("Invalid amount.")

            if not await get_user(target_id):
                raise ValueError("User not found.")

            await update_balance(target_id, amount)
            await log_transaction(
                target_id, "CREDIT_ADMIN", amount, "ADMIN", "SUCCESS"
            )

            await message.reply_text(
                f"✅ ₹{amount:.2f} to the internal wallet. User ID: `{target_id}`",
                reply_markup=admin_menu_markup(),
            )

            try:
                await app.send_message(
                    target_id,
                    f"🎉 The admin added ₹{amount:.2f} to your internal wallet.",
                )
            except Exception:
                pass

            USER_STATES.pop(user_id, None)

        except Exception as error:
            await message.reply_text(
                f"❌ Error: {error}\nFormat: `USER_ID AMOUNT`"
            )
        return

    # Admin deduct balance
    if step == "admin_awaiting_sub_bal":
        if user_id != OWNER_ID:
            USER_STATES.pop(user_id, None)
            return

        try:
            parts = text.split()
            if len(parts) != 2:
                raise ValueError("Please enter USER_ID AMOUNT.")

            target_id = int(parts[0])
            amount = valid_amount(parts[1])

            if amount is None:
                raise ValueError("Invalid amount.")

            target_user = await get_user(target_id)

            if not target_user:
                raise ValueError("User not found.")

            balance = money(target_user.get("balance", 0))

            if amount > balance:
                raise ValueError("The user's balance is insufficient.")

            await update_balance(target_id, -amount)
            await log_transaction(
                target_id, "DEBIT_ADMIN", amount, "ADMIN", "SUCCESS"
            )

            await message.reply_text(
                f"✅ ₹{amount:.2f} deducted. User ID: `{target_id}`",
                reply_markup=admin_menu_markup(),
            )

            try:
                await app.send_message(
                    target_id,
                    f"⚠️ The admin deducted ₹{amount:.2f} from your internal wallet.",
                )
            except Exception:
                pass

            USER_STATES.pop(user_id, None)

        except Exception as error:
            await message.reply_text(
                f"❌ Error: {error}\nFormat: `USER_ID AMOUNT`"
            )
        return


# ==========================================
# INLINE CALLBACK HANDLER
# ==========================================

@app.on_callback_query()
async def callback_handler(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data or ""

    admin_actions = {
        "admin_stats",
        "admin_broadcast",
        "admin_add_balance",
        "admin_sub_balance",
    }

    if data in admin_actions and user_id != OWNER_ID:
        await callback.answer("❌ Access denied.", show_alert=True)
        return

    user = await get_user(user_id)

    if data == "open_dashboard":
        await callback.answer()

        try:
            await callback.message.delete()
        except Exception:
            pass

        await send_main_menu(client, user_id)
        return

    if data == "my_account":
        if not user:
            await callback.answer("Please use /start first.", show_alert=True)
            return

        await callback.message.edit_text(
            "👤 **MY ACCOUNT**\n\n"
            f"• Name: {user.get('full_name', 'N/A')}\n"
            f"• Mobile: {user.get('mobile', 'N/A')}\n"
            f"• Database ID: `{user.get('custom_upi', 'N/A')}`\n\n"
            "⚠️ Do not treat this custom ID as a real UPI ID "
            "unless it has been issued by a bank/UPI provider.",
            reply_markup=back_markup(),
        )

    elif data == "my_balance":
        if not user:
            await callback.answer("Please use /start first.", show_alert=True)
            return

        await callback.message.edit_text(
            "💰 **INTERNAL WALLET BALANCE**\n\n"
            f"Available Balance: ₹{money(user.get('balance')):.2f}\n\n"
            "This is an internal app record, not your bank balance.",
            reply_markup=back_markup(),
        )

    elif data == "deposit_money":
        if not user:
            await callback.answer("Please use /start first.", show_alert=True)
            return

        USER_STATES[user_id] = {"step": "awaiting_deposit_amount"}
        await callback.message.edit_text(
            "💵 How much would you like to deposit? Send the amount in INR:",
            reply_markup=back_markup(),
        )

    elif data == "my_qr":
        if not user:
            await callback.answer("Please use /start first.", show_alert=True)
            return

        # This bot has one configured, real receiving UPI ID.
        # Do not present a generated @mbp database ID as bank UPI.
        if not valid_upi(COMPANY_UPI):
            await callback.answer(
                "Set a valid UPI ID in the COMPANY_UPI Config Var.",
                show_alert=True,
            )
            return

        qr_path = f"company_qr_{user_id}.png"

        try:
            uri = make_upi_uri(
                COMPANY_UPI,
                name="Mobile Pay",
                note=f"Mobile Pay user {user_id}",
            )
            make_qr_file(uri, qr_path)

            await callback.answer()

            try:
                await callback.message.delete()
            except Exception:
                pass

            await client.send_photo(
                chat_id=user_id,
                photo=qr_path,
                caption=(
                    "🪪 **MOBILE PAY RECEIVING QR**\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏦 UPI ID: `{COMPANY_UPI}`\n\n"
                    "This QR uses the real UPI ID configured in Config Vars "
                    "Before paying, verify the recipient details in your UPI "
                    "app.\n\n"
                    "⚠️ This is the configured receiving UPI ID for all users, "
                    "not a separate personal bank account for each user."
                ),
                reply_markup=back_markup(),
            )

        finally:
            if os.path.exists(qr_path):
                os.remove(qr_path)

    elif data == "create_upi":
        if not user:
            await callback.answer("Please use /start first.", show_alert=True)
            return

        USER_STATES[user_id] = {"step": "creating_upi"}

        await callback.message.edit_text(
            "🆔 Send a name for your custom database ID:\n"
            "Example: `hakeeb07`\n\n"
            "⚠️ This will not create a real bank UPI ID.",
            reply_markup=back_markup(),
        )

    elif data == "pay_upi":
        if not user:
            await callback.answer("Please use /start first.", show_alert=True)
            return

        USER_STATES[user_id] = {"step": "pay_upi_id"}

        await callback.message.edit_text(
            "💸 Send the recipient's real UPI ID:\n"
            "Example: `name@bank`",
            reply_markup=back_markup(),
        )

    elif data == "scan_qr":
        if not user:
            await callback.answer("Please use /start first.", show_alert=True)
            return

        USER_STATES[user_id] = {"step": "awaiting_qr_photo"}

        await callback.message.edit_text(
            "📷 Send a clear photo of the UPI QR code.",
            reply_markup=back_markup(),
        )

    elif data == "my_transactions":
        if not user:
            await callback.answer("Please use /start first.", show_alert=True)
            return

        transactions = await get_user_transactions(user_id)
        output = "📜 **RECENT TRANSACTIONS**\n━━━━━━━━━━━━━━━━━━━━\n"

        if not transactions:
            output += "No transactions have been recorded yet."
        else:
            for tx in transactions:
                output += (
                    f"• {tx.get('type', 'N/A')} | "
                    f"₹{tx.get('amount', 0)} | "
                    f"{tx.get('recipient', 'N/A')} | "
                    f"{tx.get('status', 'N/A')}\n"
                )

        await callback.message.edit_text(
            output,
            reply_markup=back_markup(),
        )

    elif data == "notice":
        await callback.message.edit_text(
            "⚠️ **TERMS & PAYMENT NOTICE**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"• Monthly fee configuration: ₹{MONTHLY_FEE}\n"
            "• A UPI QR only creates a payment intent.\n"
            "• This code does not include a payment gateway API.\n"
            "• Real payment must be verified using UPI app/bank records "
            "or an authorized provider.\n"
            "• Changing the internal wallet balance through the admin panel "
            "is not a bank transfer.\n"
            "• Never share your M-PIN with anyone.",
            reply_markup=back_markup(),
        )

    elif data == "admin_stats":
        users = await get_all_users()
        total = sum(money(item.get("balance")) for item in users)

        await callback.message.edit_text(
            "📊 **BOT STATISTICS**\n\n"
            f"• Total Users: {len(users)}\n"
            f"• Internal Wallet Total: ₹{total:.2f}",
            reply_markup=admin_menu_markup(),
        )

    elif data == "admin_broadcast":
        USER_STATES[user_id] = {"step": "admin_awaiting_broadcast"}

        await callback.message.edit_text(
            "📢 Send the message you want to broadcast to all users:"
        )

    elif data == "admin_add_balance":
        USER_STATES[user_id] = {"step": "admin_awaiting_add_bal"}

        await callback.message.edit_text(
            "➕ Send in this format:\n`USER_ID AMOUNT`"
        )

    elif data == "admin_sub_balance":
        USER_STATES[user_id] = {"step": "admin_awaiting_sub_bal"}

        await callback.message.edit_text(
            "➖ Send in this format:\n`USER_ID AMOUNT`"
        )

    elif data.startswith("approve_"):
        if user_id != OWNER_ID:
            await callback.answer("Access denied.", show_alert=True)
            return

        deposit_id = data[len("approve_"):]
        request = await get_deposit_request(deposit_id)

        if not request or request.get("status") != "PENDING":
            await callback.answer(
                "This request has already been processed.",
                show_alert=True,
            )
            return

        # Manual approval only. Admin must verify actual receipt/payment.
        await update_deposit_status(deposit_id, "APPROVED")
        await update_balance(request["user_id"], request["amount"])

        await log_transaction(
            request["user_id"],
            "CREDIT_DEPOSIT",
            request["amount"],
            "DEPOSIT",
            "ADMIN_APPROVED",
        )

        try:
            await callback.message.edit_caption(
                caption=(callback.message.caption or "")
                + "\n\n✅ **STATUS: ADMIN APPROVED**"
            )
        except Exception:
            pass

        await app.send_message(
            request["user_id"],
            "✅ **Deposit Request Approved**\n"
            f"₹{request['amount']:.2f} has been added to your internal wallet.",
        )

        await callback.answer("Deposit approved.")

    elif data.startswith("decline_"):
        if user_id != OWNER_ID:
            await callback.answer("Access denied.", show_alert=True)
            return

        deposit_id = data[len("decline_"):]
        request = await get_deposit_request(deposit_id)

        if not request or request.get("status") != "PENDING":
            await callback.answer(
                "This request has already been processed.",
                show_alert=True,
            )
            return

        await update_deposit_status(deposit_id, "DECLINED")

        try:
            await callback.message.edit_caption(
                caption=(callback.message.caption or "")
                + "\n\n❌ **STATUS: DECLINED**"
            )
        except Exception:
            pass

        await app.send_message(
            request["user_id"],
            "❌ Your deposit request was declined by the admin.",
        )

        await callback.answer("Deposit declined.")

    elif data == "back_menu":
        USER_STATES.pop(user_id, None)
        await callback.answer()

        try:
            if callback.message.photo:
                await callback.message.edit_caption(
                    caption=START_MESSAGE or WELCOME_MESSAGE,
                    reply_markup=main_menu_markup(),
                )
            else:
                await callback.message.edit_text(
                    START_MESSAGE or WELCOME_MESSAGE,
                    reply_markup=main_menu_markup(),
                )
        except Exception:
            await send_main_menu(client, user_id)

    else:
        await callback.answer()


# ==========================================
# PHOTO HANDLER: DEPOSIT RECEIPT / QR SCAN
# ==========================================

@app.on_message(filters.photo & filters.private)
async def photo_handler(client, message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    state = USER_STATES.get(user_id, {})
    step = state.get("step")

    # Deposit receipt submission
    if step == "awaiting_deposit_proof":
        deposit_id = state.get("deposit_id")
        amount = state.get("amount")
        user = await get_user(user_id)

        if not deposit_id or amount is None:
            USER_STATES.pop(user_id, None)
            await message.reply_text(
                "❌ Deposit request not found. Please try again."
            )
            return

        USER_STATES.pop(user_id, None)

        await message.reply_text(
            "⏳ Your receipt has been sent to the admin. "
            "You will be notified after the payment is verified."
        )

        admin_caption = (
            "🔔 **NEW DEPOSIT REQUEST**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Name: {user.get('full_name', 'N/A') if user else 'N/A'}\n"
            f"🆔 User ID: `{user_id}`\n"
            f"📱 Mobile: `{user.get('mobile', 'N/A') if user else 'N/A'}`\n"
            f"💰 Amount: ₹{amount:.2f}\n"
            f"🧾 Deposit ID: `{deposit_id}`\n\n"
            "Approve only after checking the receipt and verifying the actual payment."
        )

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Approve",
                    callback_data=f"approve_{deposit_id}",
                ),
                InlineKeyboardButton(
                    "❌ Decline",
                    callback_data=f"decline_{deposit_id}",
                ),
            ]
        ])

        await client.send_photo(
            chat_id=OWNER_ID,
            photo=message.photo.file_id,
            caption=admin_caption,
            reply_markup=buttons,
        )
        return

    # QR scanning
    if step == "awaiting_qr_photo":
        file_path = await message.download()
        scanned_data = None

        try:
            image = cv2.imread(file_path)

            if image is not None:
                detector = cv2.QRCodeDetector()
                scanned_data, points, _ = detector.detectAndDecode(image)

        except Exception as error:
            print(f"QR scan error: {error}")

        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

        if not scanned_data:
            await message.reply_text(
                "❌ Could not read the QR code. Please send a clear, complete QR photo."
            )
            return

        try:
            parsed = urlparse(scanned_data)
            params = parse_qs(parsed.query)

            # Accept standard UPI intent QR only.
            if parsed.scheme.lower() != "upi":
                raise ValueError("Not a UPI intent")

            recipient = unquote(params.get("pa", [""])[0])
            qr_amount = params.get("am", [""])[0]

            if not valid_upi(recipient):
                raise ValueError("Missing/invalid UPI recipient")

        except Exception:
            await message.reply_text(
                "❌ This does not appear to be a valid UPI QR code. "
                "Please send a valid UPI QR code."
            )
            return

        parsed_amount = valid_amount(qr_amount) if qr_amount else None

        if parsed_amount is not None:
            USER_STATES[user_id] = {
                "step": "pay_mpin",
                "recipient_upi": recipient,
                "amount": parsed_amount,
            }
            message_text = (
                "✅ **UPI QR SCANNED**\\n"
                f"📍 Recipient UPI: `{recipient}`\\n"
                f"💰 Amount from QR: ₹{parsed_amount:.2f}\\n\\n"
                "Enter your 4-digit M-PIN to continue. "
                "You must authorize the payment yourself in your UPI app."
            )
        else:
            USER_STATES[user_id] = {
                "step": "pay_amount",
                "recipient_upi": recipient,
            }
            message_text = (
                "✅ **UPI QR SCANNED**\\n"
                f"📍 Recipient UPI: `{recipient}`\\n\\n"
                "This QR has no valid amount. Send the amount in INR to continue."
            )

        await message.reply_text(message_text)
        return


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":
    app.run()
