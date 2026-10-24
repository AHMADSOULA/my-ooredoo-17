import os
import telebot
import httpx
import time
import json
import asyncio
from telebot.types import Message

# ============================================================
# 1. الإعدادات (يُفضل وضع التوكن في Environment Variables)
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ضع_التوكن_هنا_إذا_لم_تستخدم_المتغيرات")
ADMIN_ID = 123456789  # ضع آيدي تيليجرام الخاص بك هنا (رقم)

bot = telebot.TeleBot(BOT_TOKEN)

# ============================================================
# 2. ثوابت API الخاصة بأوريدو (من سجلك)
# ============================================================
BASE_URL = "https://apis.ooredoo.dz"
X_SIGNATURE = "f320f896f3da2a5a0284f9af316efb4ab0432b26406413568db116fa9dc60feb"
X_INSTANCE_ID = "1992a870-b975-11f1-9fa4-c120a3d6d3ec1790404801655"
X_PLATFORM_INFO = "eyJwbGF0Zm9ybSI6ImFuZHJvaWQiLCJpcy1waHlzaWNhbC1kZXZpY2UiOnRydWUsImRldmljZS1pZCI6IjE5OTJhODcwLWI5NzUtMTFmMS05ZmE0LWMxMjBhM2Q2ZDNlYzE3OTA0MDQ4MDE2NTUifQ=="
X_NATIVE_INTEGRITY_TOKEN = "JWBTpxXcH7Ks6mr0fJZ81uKPBTi/jHvP2KXOol9Ooj5r9c41WapD5UeV+zSVHSTeI6a80widPAncpeyus/9qjQ1xMbytlWLq7bQ3Ky8xW9XDvaiuNC4iJ/wE5WopTbqP/f70edwIJIH374PWWUvtvpvAiJVL04t/uJpfWx7IOWjlxD4M+UskIYLo7SD0NSaEvu6Abd54keq9Uo8HNbNSf6Qndmw8+RFXHB/uiFC01E7z2Kavy6RYE1i7x/zuo/OpmTMCJUjlMj++f0FrVU0AwfDYXsua+uB0JeuBidCRNx0cjbNf+yqW+iDGGLiMhA4KTLxpGWoUqTyXnNuRrVhP/JiUcT92C+DRKD3eFrhZwwa22zvQrn21RETZ4iMvfdr4I7g2rBXf+Z1HB8nh7mu5QlFhcZVJyzAMB03ZMO37vzEjoEC2x0laQeN6sT9Vcn2BO+Frx8hdHb2ZK0cZHWsEmH3gKzavPlRWnqlOegboLrQrtF04CzDUfeCRblHlRr/Q9+ngSyf7Cv4wiBwfAu+74tFbV2anrMj/V2q4AiiIfHEPtg6Shf/W35PoSu7oIwXklFn4Bu2vRRMYJJ3LMVtQCSv9BjO1AA1WvSWhqgCe5qTbFM2jCLzG9CH/boGIqyu3CHqFSxabsSdCAbYrZ0qMYKa474Djh0UxxyaOalBB5ABS/EjQuLjLIgIg8A26STCsxBUBEEbSZwLvnxtS8GBGfvgPsKtxiuMtS4OVJzGghySD9f4verJiyTlfiR0M"

DEVICE_FP = "d4d827cf8063ee5084e5e87be4a16f2b27ca4a7eee499fc2de8d55455f14fa97"

# ============================================================
# 3. دالة جلب الرصيد
# ============================================================
async def login_and_get_balance(msisdn_int: str, password: str) -> dict:
    async with httpx.AsyncClient(http2=False, verify=True, timeout=30.0) as client:
        try:
            login_path = "/api/auth/realms/myooredoo/protocol/openid-connect/token"
            ts = str(int(time.time() * 1000))
            
            # Header for login
            ck_headers = {
                "user-agent": "Dart/3.11 (dart:io)",
                "x-msisdn": msisdn_int,
                "x-device-fingerprint": DEVICE_FP,
                "x-platform-origin": "mobile-android",
                "platform": "android",
                "x-version": "1.5.15",
                "x-signature": X_SIGNATURE,
                "accept": "*/*",
                "host": "apis.ooredoo.dz",
                "x-timestamp": ts,
                "x-instance-id": X_INSTANCE_ID,
                "x-platform-data-signature": X_PLATFORM_INFO,
                "accept-encoding": "gzip",
                "x-path": login_path,
                "x-method": "POST",
                "x-native-integrity-token": X_NATIVE_INTEGRITY_TOKEN,
                "content-type": "application/json; charset=utf-8",
                "content-length": "2"
            }
            
            ck_res = await client.post(f"{BASE_URL}/api/ooredoo-bff/checkpoint/token", headers=ck_headers, content="{}")
            nonce = ck_res.headers.get("X-Nonce-Id", "")
            chronos = ck_res.headers.get("X-Chronos-Id", "")
            
            if not nonce:
                return {"success": False, "error": "فشل جلب التوكنات من السيرفر"}

            # Login
            login_headers = ck_headers.copy()
            login_headers.update({
                "x-nonce-id": nonce,
                "x-chronos-id": chronos,
                "x-force-update": "true",
                "content-type": "application/x-www-form-urlencoded; charset=utf-8",
            })
            del login_headers["x-path"]
            del login_headers["x-method"]
            del login_headers["x-native-integrity-token"]
            del login_headers["content-length"]

            data = {"client_id": "myooredoo-app", "grant_type": "password", "username": msisdn_int, "password": password}
            res = await client.post(f"{BASE_URL}{login_path}", headers=login_headers, data=data)
            
            if res.status_code != 200:
                return {"success": False, "error": f"بيانات الدخول خاطئة (كود {res.status_code})"}
                
            token = res.json().get("access_token")

            # Balance
            bal_path = "/api/ooredoo-bff/subscriptions/getAccountInfo"
            ts = str(int(time.time() * 1000))
            bal_headers = login_headers.copy()
            bal_headers.update({
                "authorization": f"Bearer {token}",
                "x-nonce-id": nonce,
                "x-chronos-id": chronos,
                "accept": "application/json",
                "x-timestamp": ts,
            })
            
            bal_res = await client.get(f"{BASE_URL}{bal_path}?msisdn={msisdn_int}", headers=bal_headers)
            
            if bal_res.status_code == 200:
                data = bal_res.json()
                return {"success": True, "balance": str(data.get("accountBalance", "0.00"))}
            else:
                return {"success": False, "error": f"فشل جلب الرصيد (كود {bal_res.status_code})"}

        except Exception as e:
            return {"success": False, "error": str(e)}

# ============================================================
# 4. البوت (Telebot)
# ============================================================
@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ هذا البوت مخصص للاستخدام الشخصي فقط.")
        return
    msg = bot.reply_to(message, "👋 أهلاً بك.\nأرسل رقم الهاتف (مثال: 0554924120).")
    bot.register_next_step_handler(msg, process_username)

def process_username(message: Message):
    if message.chat.id != ADMIN_ID: return
    raw_input = message.text.strip().replace("+", "").replace(" ", "")
    
    if raw_input.startswith("05") and len(raw_input) == 10:
        username_int = "213" + raw_input[1:]
    elif len(raw_input) == 9 and raw_input.startswith("5"):
        username_int = "213" + raw_input
    elif raw_input.startswith("213"):
        username_int = raw_input
    else:
        msg = bot.reply_to(message, "⚠️ الرقم غير صالح. أعد المحاولة.")
        bot.register_next_step_handler(msg, process_username)
        return
        
    display_num = "0" + username_int[3:] if username_int.startswith("213") else username_int
    msg = bot.reply_to(message, f"✅ الرقم: {display_num}\n🔑 أرسل كلمة المرور.")
    bot.register_next_step_handler(msg, process_password, username_int, display_num)

def process_password(message: Message, username_int, display_num):
    if message.chat.id != ADMIN_ID: return
    password = message.text.strip()
    
    if not password: 
        bot.reply_to(message, "⚠️ كلمة المرور فارغة.")
        return

    try:
        bot.delete_message(message.chat.id, message.message_id) # حذف كلمة المرور للأمان
    except: pass
    
    msg = bot.reply_to(message, "⏳ جاري الفحص...")
    
    # تشغيل دالة الـ API في حلقة أحداث جديدة
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(login_and_get_balance(username_int, password))
    
    if result["success"]:
        bot.edit_message_text(
            f"✅ تم الفحص بنجاح!\n\n"
            f"📱 الرقم: {display_num}\n"
            f"💰 الرصيد: {result['balance']} دج",
            chat_id=msg.chat.id, 
            message_id=msg.message_id
        )
    else:
        bot.edit_message_text(
            f"❌ فشل الفحص\n"
            f"⚠️ السبب: {result.get('error')}",
            chat_id=msg.chat.id, 
            message_id=msg.message_id
        )

# ============================================================
# 5. التشغيل
# ============================================================
if __name__ == "__main__":
    print("🤖 البوت يعمل...")
    bot.infinity_polling()
