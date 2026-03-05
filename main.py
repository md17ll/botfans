import os
import json
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ======================
# Environment Variables (Railway Variables)
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip() or "0")
CONTACT_USERNAME = os.getenv("CONTACT_USERNAME", "").strip().lstrip("@")

# ملف إعدادات بسيط لتخزين رسالة البدء
SETTINGS_PATH = Path(os.getenv("SETTINGS_PATH", "settings.json"))

DEFAULT_START_TEXT = (
    "👋 أهلاً بك!\n\n"
    "لاستخدام البوت تواصل معنا عبر الزر 👇"
)

# لتخزين حالة تعديل الرسالة (للمستخدم الأدمن فقط)
AWAITING_NEW_START_TEXT_KEY = "awaiting_new_start_text"


# ======================
# Helpers: settings load/save
# ======================
def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_settings(data: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_start_text() -> str:
    s = load_settings()
    return (s.get("start_text") or DEFAULT_START_TEXT).strip()

def set_start_text(new_text: str) -> None:
    s = load_settings()
    s["start_text"] = new_text.strip()
    save_settings(s)

def is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID

def contact_url() -> str:
    if not CONTACT_USERNAME:
        # إذا ما حطيت يوزر تواصل، خليه يفتح قائمة share بدال رابط
        return "https://t.me/"
    return f"https://t.me/{CONTACT_USERNAME}"


# ======================
# UI
# ======================
def start_keyboard(user_is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("💬 تواصل", url=contact_url())]
    ]
    if user_is_admin:
        rows.append([InlineKeyboardButton("⚙ تعديل رسالة البدء", callback_data="admin_edit_start")])
    return InlineKeyboardMarkup(rows)


# ======================
# Handlers
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = get_start_text()
    await update.message.reply_text(
        text,
        reply_markup=start_keyboard(is_admin(user.id))
    )

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()

    user = update.effective_user
    if q.data == "admin_edit_start":
        if not is_admin(user.id):
            await q.message.reply_text("غير مصرح.")
            return

        context.user_data[AWAITING_NEW_START_TEXT_KEY] = True
        await q.message.reply_text("✏️ أرسل الآن رسالة البدء الجديدة (نص فقط).")
        return

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    # فقط الأدمن يقدر يغير رسالة البدء
    if not is_admin(user.id):
        return

    if context.user_data.get(AWAITING_NEW_START_TEXT_KEY):
        new_text = (update.message.text or "").strip()
        if not new_text:
            await update.message.reply_text("أرسل نص صحيح.")
            return

        set_start_text(new_text)
        context.user_data[AWAITING_NEW_START_TEXT_KEY] = False
        await update.message.reply_text("✅ تم تعديل رسالة البدء.\nجرّب /start لتشوفها.")
        return


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Missing BOT_TOKEN. Set it in Railway Variables.")

    if ADMIN_ID == 0:
        print("⚠️ ADMIN_ID غير مضبوط. زر الأدمن لن يظهر لأي شخص.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    # Polling مناسب لـ Railway إذا شغّلت Worker
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
