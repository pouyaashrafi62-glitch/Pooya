import os
import subprocess
import ipaddress
import threading
import concurrent.futures

from flask import Flask
import telebot
from telebot import types

# ========== تنظیمات ==========
BOT_TOKEN = "9047217839:AAGzRR55WUWjks1C19ZJvP0syiKpxPpLTCw" # توکن خودت را اینجا بگذار
BOT_USERNAME = "@Pooyhhf64if_bot" # یوزرنیم ربات خودت
# ============================

# --- وب‌سرور ساده برای پارس‌پک ---
web_app = Flask(__name__)

@web_app.route("/")
def health():
    return "Bot is running", 200

def run_web_server():
    port = int(os.environ.get("PORT", 5000))
    web_app.run(host="0.0.0.0", port=port)

# --- ربات تلگرام ---
bot = telebot.TeleBot(BOT_TOKEN)

# ذخیره IP های کاربر: chat_id -> {step, ip1, ip2}
user_data = {}

FOOTER = "➖➖➖➖➖➖➖➖\n👨‍💻 پویا اشرفی | پروژه تحلیل و پینگ IP"

def get_class(ip_obj):
    first_octet = int(str(ip_obj).split('.')[0])
    if 1 <= first_octet <= 126:
        return "A"
    elif 128 <= first_octet <= 191:
        return "B"
    elif 192 <= first_octet <= 223:
        return "C"
    elif 224 <= first_octet <= 239:
        return "D (Multicast)"
    else:
        return "E (Reserved)"

def analyze_ip(ip_str):
    """تحلیل IP و برگرداندن دیکشنری مشخصات"""
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError:
        return None

    # برای کلاس‌های A, B, C از subnet mask پیش‌فرض استفاده می‌کنیم
    cls = get_class(ip_obj)
    if cls == "A":
        mask = "255.0.0.0"
        prefix = 8
    elif cls == "B":
        mask = "255.255.0.0"
        prefix = 16
    elif cls == "C":
        mask = "255.255.255.0"
        prefix = 24
    else:
        return {"error": "کلاس D و E برای تحلیل شبکه پشتیبانی نمی‌شوند."}

    network = ipaddress.IPv4Network(f"{ip_str}/{mask}", strict=False)

    # شناسه شبکه و میزبان
    ip_int = int(ip_obj)
    mask_int = int(ipaddress.IPv4Address(mask))
    network_id = ip_int & mask_int
    host_id = ip_int & (~mask_int & 0xFFFFFFFF)

    return {
        "address": str(ip_obj),
        "class": cls,
        "network_id": str(ipaddress.IPv4Address(network_id)),
        "host_id": str(ipaddress.IPv4Address(host_id)),
        "network_address": str(network.network_address),
        "broadcast": str(network.broadcast_address),
        "subnet_mask": mask,
        "subnet_value": f"/{prefix}",
    }

def format_analysis(ip_str):
    info = analyze_ip(ip_str)
    if info is None:
        return f"❌ IP وارد شده معتبر نیست: `{ip_str}`"
    if "error" in info:
        return f"⚠️ {info['error']}"

    return (
        f"🔍 **تحلیل IP:** `{info['address']}`\n"
        f"• کلاس IP: **{info['class']}**\n"
        f"• شناسه شبکه: `{info['network_id']}`\n"
        f"• شناسه میزبان: `{info['host_id']}`\n"
        f"• آدرس شبکه: `{info['network_address']}`\n"
        f"• آدرس Broadcast: `{info['broadcast']}`\n"
        f"• Subnet Mask: `{info['subnet_mask']}`\n"
        f"• Subnet Value: `{info['subnet_value']}`"
    )

def ping_ip(target):
    """پینگ یک IP و برگرداندن نتیجه"""
    try:
        # در لینوکس (پارس‌پک) از -c 4 استفاده می‌کنیم
        result = subprocess.run(
            ["ping", "-c", "4", "-W", "2", target],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            # خلاصه‌ای از خروجی پینگ
            lines = result.stdout.strip().split("\n")
            summary = lines[-2] if len(lines) >= 2 else "پینگ موفق"
            return f"✅ `{target}` → {summary}"
        else:
            return f"❌ `{target}` → پاسخی دریافت نشد (Timeout)"
    except subprocess.TimeoutExpired:
        return f"⏱ `{target}` → زمان پینگ به پایان رسید"
    except Exception as e:
        return f"⚠️ `{target}` → خطا: {str(e)}"

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    # ریست کردن اطلاعات کاربر برای شروع مجدد
    user_data[chat_id] = {"step": "ip1"}

    welcome_text = (
        f"👋 **خوش آمدید!**\n"
        f"به پروژه **پویا اشرفی - دوازدهم شبکه** خوش آمدید.\n\n"
        f"این ربات برای **تحلیل و پینگ IP** طراحی شده است.\n"
        f"در ادامه نحوه کارکرد ربات را مشاهده می‌کنید:\n\n"
        f"1️⃣ **تحلیل IP:** در هر مرحله یک IP از شما دریافت می‌شود و مشخصات آن (کلاس، شناسه شبکه، آدرس شبکه، Broadcast، Subnet Mask و...) به صورت خودکار نمایش داده می‌شود.\n\n"
        f"2️⃣ **پینگ دو IP:** پس از وارد کردن دو IP، دکمه پینگ ظاهر می‌شود و نتیجه پینگ هر دو آدرس به شما نمایش داده می‌شود.\n\n"
        f"{FOOTER}\n\n"
        f"👇 **برای شروع، لطفاً IP اول خود را وارد کنید:**\n"
        f"(مثال: `192.168.1.1`)\n"
    )
    
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if chat_id not in user_data:
        bot.send_message(chat_id, "برای شروع لطفاً دستور /start را بزنید.")
        return

    state = user_data[chat_id]

    # مرحله اول: دریافت IP اول
    if state["step"] == "ip1":
        try:
            ipaddress.ip_address(text)
        except ValueError:
            bot.send_message(chat_id, "❌ IP معتبر نیست. دوباره وارد کنید (مثال: `192.168.1.1`):", parse_mode="Markdown")
            return

        state["ip1"] = text
        state["step"] = "ip2"

        analysis = format_analysis(text)
        bot.send_message(chat_id, analysis, parse_mode="Markdown")
        bot.send_message(
            chat_id,
            "✅ IP اول ثبت شد.\n\nحالا **IP دوم** را وارد کنید:\n(مثال: `8.8.8.8`)",
            parse_mode="Markdown"
        )

    # مرحله دوم: دریافت IP دوم
    elif state["step"] == "ip2":
        try:
            ipaddress.ip_address(text)
        except ValueError:
            bot.send_message(chat_id, "❌ IP معتبر نیست. دوباره وارد کنید (مثال: `8.8.8.8`):", parse_mode="Markdown")
            return

        state["ip2"] = text
        state["step"] = "done"

        analysis = format_analysis(text)
        bot.send_message(chat_id, analysis, parse_mode="Markdown")

        # دکمه پینگ
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton(
            "🏓 پینگ دو IP",
            callback_data="do_ping"
        )
        markup.add(btn)

        bot.send_message(
            chat_id,
            f"✅ IP دوم ثبت شد.\n\nIP1: `{state['ip1']}`\nIP2: `{state['ip2']}`\n\nبرای پینگ کلیک کنید:",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    else:
        # بعد از اتمام، اگر دوباره پیام داد، ریست کن
        bot.send_message(chat_id, "برای شروع مجدد لطفاً دستور /start را بزنید.")

@bot.callback_query_handler(func=lambda call: call.data == "do_ping")
def callback_ping(call):
    chat_id = call.message.chat.id
    state = user_data.get(chat_id)

    if not state or state.get("step") != "done":
        bot.answer_callback_query(call.id, "ابتدا دو IP وارد کنید.")
        return

    ip1 = state["ip1"]
    ip2 = state["ip2"]

    bot.answer_callback_query(call.id, "در حال پینگ...")
    bot.send_message(chat_id, "⏳ در حال پینگ هر دو IP...")

    # پینگ به صورت موازی برای سرعت بیشتر
    with concurrent.futures.ThreadPoolExecutor() as executor:
        f1 = executor.submit(ping_ip, ip1)
        f2 = executor.submit(ping_ip, ip2)
        result1 = f1.result()
        result2 = f2.result()

    result_text = (
        f"📡 **نتیجه پینگ:**\n\n"
        f"IP اول: {result1}\n"
        f"IP دوم: {result2}\n\n"
        f"{FOOTER}"
    )
    bot.send_message(chat_id, result_text, parse_mode="Markdown")

    # ریست برای درخواست بعدی
    user_data[chat_id] = {"step": "ip1"}
    bot.send_message(chat_id, "برای تحلیل جدید، **IP اول** را وارد کنید:")


if __name__ == "__main__":
    # وب‌سرور رو در ترد جداگانه اجرا کن تا پارس‌پک ارور Healthy نده
    t = threading.Thread(target=run_web_server, daemon=True)
    t.start()
    print("Web server started on port", os.environ.get("PORT", 5000))

    # ربات رو اجرا کن (Polling)
    print("Bot polling started...")
    bot.infinity_polling()