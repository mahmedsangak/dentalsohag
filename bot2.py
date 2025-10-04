import os
import json
import hashlib
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ------------------ الإعدادات ------------------
TOKEN = "7655758995:AAEhrYOTdyE4zAYQv9oAQq4QV85sOcBcPbc"
CODES_FILE = "codes.json"
LOGGED_FILE = "logged_users.txt"
LECTURES_DIR = "lectures"

# أنواع الملفات
PDF_EXTENSIONS = [".pdf", ".ppt", ".pptx"]
AUDIO_EXTENSIONS = [".mp3", ".wav", ".ogg", ".m4a"]

FILES_MAP = {}

# ------------------ دوال مساعدة ------------------
def normalize_code(code: str) -> str:
    arabic_to_english = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    normalized = code.translate(arabic_to_english)
    normalized = "".join(filter(str.isdigit, normalized))
    return normalized

def check_code(student_code):
    if not os.path.exists(CODES_FILE):
        return None
    with open(CODES_FILE, "r", encoding="utf-8") as f:
        codes_list = json.load(f)
    user_code = normalize_code(student_code)
    for student in codes_list:
        code_in_file = normalize_code(student["code"])
        if user_code == code_in_file:
            return student
    return None

def is_logged_in(user_id):
    if not os.path.exists(LOGGED_FILE):
        return False
    with open(LOGGED_FILE, "r", encoding="utf-8") as f:
        ids = [line.strip().split("|")[0] for line in f]
    return str(user_id) in ids

def log_user(user_id, student_name):
    with open(LOGGED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{user_id}|{student_name}\n")

def logout_user(user_id):
    if not os.path.exists(LOGGED_FILE):
        return
    with open(LOGGED_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]
    lines = [line for line in lines if not line.startswith(str(user_id) + "|")]
    with open(LOGGED_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def get_logged_name(user_id):
    if not os.path.exists(LOGGED_FILE):
        return None
    with open(LOGGED_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]
    for line in lines:
        if line.startswith(str(user_id) + "|"):
            return line.split("|")[1]
    return None

# ------------------ الأوامر ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "👋 أهلاً بك في بوت الجامعة!\n\n"
        "من فضلك أدخل كود الطالب الخاص بك:\n\n"
        "البوت مطور بواسطة محمد: https://facebook.com/MSANGAK27"
    )
    # زر توضيحي للطالب
    keyboard = [[KeyboardButton("برجاء إدخال كود الطالب")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    user_data = context.user_data

    # تسجيل دخول
    if not is_logged_in(user_id):
        student = check_code(text)
        if student:
            log_user(user_id, student["name"])
            await update.message.reply_text(f"✅ تم التحقق من الكود بنجاح! مرحباً {student['name']} 🌟")
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("❌ كود غير صحيح. حاول مرة أخرى:")
        return

    # التعامل مع الأزرار
    if text == "🚪 تسجيل الخروج":
        logout_user(user_id)
        user_data.clear()
        await update.message.reply_text(
            "🚪 تم تسجيل الخروج بنجاح.\nأدخل كود الطالب لتسجيل الدخول من جديد:",
            reply_markup=ReplyKeyboardRemove()  # هذا يخفي القائمة
        )
        return

    # بياناتي
    if text == "👤 بياناتي":
        student_name = get_logged_name(user_id)
        keyboard = [
            [KeyboardButton(f"📝 الاسم: {student_name}")],
            [KeyboardButton("📆 الجدول الدراسي")],
            [KeyboardButton("🕒 الغياب والحضور")],
            [KeyboardButton("⬅️ رجوع للقائمة الرئيسية")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text("👤 بياناتي:", reply_markup=reply_markup)
        user_data["current_menu"] = "my_data"
        return

    if user_data.get("current_menu") == "my_data":
        if text != "⬅️ رجوع للقائمة الرئيسية":
            await update.message.reply_text("❗ لم يتم إضافة هذه الميزة بعد")
            return

    # المحاضرات
    if text == "📚 المحاضرات":
        subjects = sorted([name for name in os.listdir(LECTURES_DIR) if os.path.isdir(os.path.join(LECTURES_DIR, name))])
        user_data["subjects_map"] = {s: s for s in subjects}
        keyboard = [[KeyboardButton(s)] for s in subjects]
        keyboard.append([KeyboardButton("⬅️ رجوع للقائمة الرئيسية")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text("اختر المادة:", reply_markup=reply_markup)
        user_data["current_menu"] = "subjects"
        return

    # اختيار مادة
    subjects_map = user_data.get("subjects_map", {})
    if text in subjects_map:
        subject_name = subjects_map[text]
        subject_path = os.path.join(LECTURES_DIR, subject_name)
        lecture_dirs = sorted([d for d in os.listdir(subject_path) if os.path.isdir(os.path.join(subject_path, d))])
        user_data["lectures_map"] = {d: d for d in lecture_dirs}
        keyboard = [[KeyboardButton(d.capitalize())] for d in lecture_dirs]
        keyboard.append([KeyboardButton("⬅️ رجوع خطوة للخلف")])
        keyboard.append([KeyboardButton("⬅️ رجوع للقائمة الرئيسية")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(f"📘 {subject_name}\nاختر المحاضرة:", reply_markup=reply_markup)
        user_data["current_subject"] = subject_name
        user_data["current_menu"] = "lectures"
        return

    # اختيار محاضرة
    lectures_map = user_data.get("lectures_map", {})
    if text in lectures_map:
        lecture_name = lectures_map[text]
        subject_name = user_data.get("current_subject")
        lecture_path = os.path.join(LECTURES_DIR, subject_name, lecture_name)
        buttons = []
        if os.path.exists(lecture_path):
            for f in os.listdir(lecture_path):
                ext = os.path.splitext(f)[1].lower()
                file_id = hashlib.md5(f.encode()).hexdigest()[:8]
                FILES_MAP[file_id] = os.path.join(lecture_path, f)
                if ext in PDF_EXTENSIONS:
                    buttons.append([KeyboardButton(f"📄 {f}")])
                elif ext in AUDIO_EXTENSIONS:
                    buttons.append([KeyboardButton(f"🎧 {f}")])
        buttons.append([KeyboardButton("⬅️ رجوع خطوة للخلف")])
        buttons.append([KeyboardButton("⬅️ رجوع للقائمة الرئيسية")])
        reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(f"🎓 {subject_name} - {lecture_name}", reply_markup=reply_markup)
        user_data["current_menu"] = "lecture_files"
        user_data["current_lecture"] = lecture_name
        return

    # زر الرجوع خطوة للخلف
    if text == "⬅️ رجوع خطوة للخلف":
        current_menu = user_data.get("current_menu")
        if current_menu == "lectures":
            await handle_message(Update(update.update_id, message=update.message), context)
        elif current_menu == "lecture_files":
            subject_name = user_data.get("current_subject")
            subject_path = os.path.join(LECTURES_DIR, subject_name)
            lecture_dirs = sorted([d for d in os.listdir(subject_path) if os.path.isdir(os.path.join(subject_path, d))])
            user_data["lectures_map"] = {d: d for d in lecture_dirs}
            keyboard = [[KeyboardButton(d.capitalize())] for d in lecture_dirs]
            keyboard.append([KeyboardButton("⬅️ رجوع خطوة للخلف")])
            keyboard.append([KeyboardButton("⬅️ رجوع للقائمة الرئيسية")])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            await update.message.reply_text(f"📘 {subject_name}\nاختر المحاضرة:", reply_markup=reply_markup)
            user_data["current_menu"] = "lectures"
        return

    # زر الرجوع للقائمة الرئيسية
    if text == "⬅️ رجوع للقائمة الرئيسية":
        await show_main_menu(update, context)
        return

    # إرسال الملفات
    for file_id, path in FILES_MAP.items():
        if text.endswith(os.path.basename(path)):
            try:
                msg = await update.message.reply_text("⏳ جاري تحميل الملف، يرجى الانتظار...")
                ext = os.path.splitext(path)[1].lower()
                if ext in PDF_EXTENSIONS:
                    with open(path, "rb") as f:
                        await update.message.reply_document(f)
                elif ext in AUDIO_EXTENSIONS:
                    with open(path, "rb") as f:
                        await update.message.reply_audio(f)
                await msg.delete()
            except Exception as e:
                await update.message.reply_text(f"❌ حدث خطأ أثناء إرسال الملف:\n{str(e)}")
            return

# ------------------ القائمة الرئيسية ------------------
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📚 المحاضرات")],
        [KeyboardButton("👤 بياناتي")],
        [KeyboardButton("🚪 تسجيل الخروج")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text("اختر من القائمة:", reply_markup=reply_markup)
    context.user_data["current_menu"] = "main"

# ------------------ تشغيل البوت ------------------
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

print("🤖 البوت يعمل الآن ...")
app.run_polling()
