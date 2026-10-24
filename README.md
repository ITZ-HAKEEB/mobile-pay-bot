# 📱 Mobile Pay - Telegram Wallet & UPI Payment Bot

![Mobile Pay Banner](https://telegra.ph/file/0c324976c7c251bb425c7.jpg)

**Mobile Pay** is a powerful, secure, and modern Telegram Wallet and UPI Payment Bot built using **Python**, **Pyrogram**, and **MongoDB (Motor)**. It enables users to create custom `@mbp` UPI handles, generate dynamic QR codes, process real payments, scan QR codes using OCR/Computer Vision, and manage their wallet balance smoothly.

---

## ✨ Features & Highlights

- 📢 **Force Join Verification:** Ensures users join your official Telegram channel before accessing the bot.
- 🔐 **Secure Registration & M-PIN:** Step-by-step mobile verification, profile creation, and 4-digit M-PIN security for all financial actions.
- 🪪 **Custom `@mbp` UPI Handles:** Users can generate custom UPI IDs (e.g., `hakeeb07@mbp`).
- 📷 **Instant QR Code Scanner:** Built-in QR scanner powered by `OpenCV` and `pyzbar` to extract UPI IDs directly from uploaded photos/screenshots.
- 💵 **Deposit & Wallet System:** Users can request wallet deposits, generate QR codes, and upload payment proofs.
- 👑 **Admin Control Panel (`/admin`):**
  - **Broadcast System:** Send announcements to all registered users in real-time.
  - **Approve/Decline Payments:** Receive instant alert notifications for deposit requests with one-click `Approve` or `Decline` buttons.
  - **Manual Balance Adjustments:** Add or deduct balance from any user's wallet manually.
  - **Bot Analytics:** View live total users and total system wallet balance.
- ⚠️ **Configurable Safety Notice & Banners:** Easily update start images, support usernames, and start messages from `config.py`.

---

## 🛠️ Tech Stack & Requirements

- **Language:** Python 3.10+
- **Framework:** Pyrogram (v2.0+)
- **Database:** MongoDB Atlas (Async Motor Driver)
- **Computer Vision:** `opencv-python-headless`, `pyzbar`, `qrcode`

---

## 🚀 One-Click Deployment on Heroku

Click the button below to deploy your **Mobile Pay** bot directly to Heroku:

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ITZ-HAKEEB/mobile-pay-bot)

---

## ⚙️ Environment Variables Setup

Configure the following environment variables during Heroku deployment or in your local `.env` file:

| Variable | Description | Required | Example |
| :--- | :--- | :---: | :--- |
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) | Yes | `123456` |
| `API_HASH` | Telegram API Hash | Yes | `abc123xyz...` |
| `BOT_TOKEN` | Bot Token from [@BotFather](https://t.me/BotFather) | Yes | `123456:ABC-DEF...` |
| `MONGO_URI` | MongoDB Connection String | Yes | `mongodb+srv://...` |
| `OWNER_ID` | Your Numeric Telegram User ID | Yes | `123456789` |
| `FORCE_CHANNEL` | Telegram Channel Username for Force Join | Yes | `@THE_LINK_PALACE` |
| `SUPPORT_USERNAME` | Support Admin Telegram Username (without `@`) | Yes | `llMR_BADALll` |
| `START_IMAGE_URL` | Direct URL for Start Banner Image | Yes | `https://telegra.ph/...` |
| `COMPANY_UPI` | Master UPI ID for receiving deposits | Yes | `company@mbp` |

---

