import os
import telebot
from telebot import types
import requests
from dotenv import load_dotenv
from download_service import get_movie_versions


load_dotenv()

TMDB_TOKEN = os.getenv("TMDB_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TMDB_TOKEN:
    raise ValueError("TMDB_TOKEN is not set")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
user_sessions = {}
processed_download_messages = set()


def search_movie(movie_name):
    url = 'https://api.themoviedb.org/3/search/movie'
    headers = {
        'Authorization': f'Bearer {TMDB_TOKEN}',
        'accept': 'application/json'
    }
    params = {
        'query': movie_name,
        'language': 'fa-IR'
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        print("TMDB request time out")
        return None
    except requests.exceptions.RequestException as error:
        print(f"TMDB request error: {error}")
        return None
    except ValueError:
        print("Invalid JSON response from TMDB")
        return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "🎬 سلام، به دنیای فیلم‌ها خوش اومدی!\n\nبرای شروع، لطفاً نوع عضویت خودت رو انتخاب کن.")
    send_membership_plans(message)

@bot.message_handler(commands=['help'])
def send_help(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton('درباره ما')
    item2 = types.KeyboardButton('تماس با ما')
    item3 = types.KeyboardButton('⬅️')
    markup.add(item1, item2, item3)
    bot.send_message(message.chat.id, "یکی از موارد زیر را انتخاب کنید:", reply_markup=markup)

@bot.message_handler(commands=['membership'])
def send_membership_plans(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton('یک ماهه')
    item2 = types.KeyboardButton('سه ماهه')
    item3 = types.KeyboardButton('⬅️')
    markup.add(item1, item2, item3)
    bot.send_message(message.chat.id, "نوع عضویت خود را تعیین کنید:", reply_markup=markup)

def send_options(chat_id, title, options, prefix, back_data=None):
    markup = types.InlineKeyboardMarkup()
    for index, option in enumerate(options):
        markup.add(types.InlineKeyboardButton(option, callback_data=f"{prefix}|{index}"))
    if back_data:
        markup.add(types.InlineKeyboardButton('⬅️ بازگشت', callback_data=back_data))
    bot.send_message(chat_id, title, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('download_'))
def download_movie(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    request_key = (chat_id, message_id)
    if request_key in processed_download_messages:
        bot.answer_callback_query(call.id, "این درخواست قبلاً ثبت شده است.")
        return
    processed_download_messages.add(request_key)
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
    except telebot.apihelper.ApiTelegramException as error:
        print(f"Button removal error: {error}")
    status_message = bot.send_message(chat_id, "⏳ در حال بررسی نسخه‌های فیلم...")
    versions = get_movie_versions(call.data.removeprefix('download_'))
    if not versions:
        bot.edit_message_text("❌ نسخه‌ای از این فیلم در منبع فعلی پیدا نشد.", chat_id, status_message.message_id)
        return
    print("VERSIONS:", [ (v['filename'], v['language'], v['quality']) for v in versions])
    user_sessions[chat_id] = {'versions': versions}
    try:
        bot.delete_message(chat_id, status_message.message_id)
    except telebot.apihelper.ApiTelegramException as error:
        print(f"Status message deletion error: {error}")
    send_options(
        chat_id,
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        ['دوبله', 'زبان اصلی (زیرنویس فارسی)'],
        "type",
        back_data="back|cancel"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('type|'))
def select_type(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    session = user_sessions.get(chat_id)
    if not session:
        return
    index = int(call.data.split('|')[1])
    versions = session['versions']
    if index == 0:
        filtered_versions = [v for v in versions if v['language'] == 'دوبله فارسی']
    else:
        filtered_versions = []
        for version in versions:
            if version['language'] == 'دوبله فارسی':
                continue
            persian_subtitle = next((s for s in version['subtitles'] if s['language'] == 'زیرنویس فارسی'), None)
            filtered_versions.append({**version, 'selected_subtitle': persian_subtitle})
    if not filtered_versions:
        bot.send_message(chat_id, "❌ نسخه‌ای با این مشخصات پیدا نشد.")
        return
    session['filtered_versions'] = filtered_versions
    qualities = list(dict.fromkeys(version['quality'] for version in filtered_versions))
    if not qualities:
        bot.send_message(chat_id, "❌ کیفیت قابل انتخابی برای این نسخه پیدا نشد.")
        return
    session['qualities'] = qualities
    send_options(chat_id, "📺 کیفیت موردنظر را انتخاب کنید:", qualities, "quality", back_data="back|type")

@bot.callback_query_handler(func=lambda call: call.data.startswith('quality|'))
def select_quality(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    session = user_sessions.get(chat_id)
    if not session:
        return
    index = int(call.data.split('|')[1])
    if index >= len(session['qualities']):
        return
    quality = session['qualities'][index]
    versions = [
        v for v in session['filtered_versions']
        if v['quality'] == quality
    ]
    if not versions:
        bot.send_message(chat_id, "❌ نسخه موردنظر پیدا نشد.")
        return
    session['selected_quality'] = quality
    version = versions[0]
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton('▶️ تماشای آنلاین', url=version['stream_url']),
        types.InlineKeyboardButton('⬇️ دانلود', url=version['download_url'])
    )
    subtitle = version.get('selected_subtitle')
    if subtitle:
        markup.add(
            types.InlineKeyboardButton('📝 دانلود زیرنویس فارسی', url=subtitle['url'])
        )
    markup.add(
        types.InlineKeyboardButton('⬅️ بازگشت', callback_data='back|quality')
    )
    bot.send_message(
        chat_id,
        "🎬 روش دریافت فیلم را انتخاب کنید:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('back|'))
def handle_back(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    session = user_sessions.get(chat_id)
    if call.data == 'back|cancel':
        user_sessions.pop(chat_id, None)
        bot.send_message(chat_id, "انتخاب لغو شد. می‌توانید نام فیلم دیگری را جست‌وجو کنید.")
        return
    if not session:
        return
    if call.data == 'back|type':
        send_options(
            chat_id,
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            ['دوبله', 'زبان اصلی (زیرنویس فارسی)'],
            "type",
            back_data="back|cancel"
        )
    elif call.data == 'back|quality':
        send_options(
            chat_id,
            "📺 کیفیت موردنظر را انتخاب کنید:",
            session['qualities'],
            "quality",
            back_data="back|type"
        )

@bot.message_handler(func=lambda message: True)
def handle_other_message(message):
    if message.text == 'درباره ما':
        bot.send_message(message.chat.id, 'این ربات توسط حسین توسعه داده شده است')
    elif message.text == 'تماس با ما':
        email = 'hoseynosooli@gmail.com'
        contact_info = f"اطلاعات تماس \nایمیل: {email}"
        bot.send_message(message.chat.id, contact_info)
    elif message.text in ['یک ماهه', 'سه ماهه']:
        markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, f"✅ شما عضویت {message.text} را انتخاب کردید.\n\n🍿 حالا اسم فیلم مورد نظرت رو برام بفرست تا جست‌وجوش کنم.", reply_markup=markup)
    elif message.text == '⬅️':
        markup = types.ReplyKeyboardRemove(selective=False)
        bot.send_message(message.chat.id, 'به منوی اصلی بازگشتید', reply_markup=markup)
    else:
        movie_name = message.text
        result = search_movie(movie_name)
        if result is None:
            bot.send_message(message.chat.id, '⚠️ ارتباط با سرویس جستجوی فیلم برقرار نشد. لطفاً کمی بعد دوباره تلاش کنید.')
            return
        if result['total_results'] == 0:
            bot.send_message(
                message.chat.id,
                '❌ متاسفانه فیلمی با این نام پیدا نکردم\n'
                'لطفاً نام فیلم را دوباره بررسی کنید.'
            )
            return
        else:
            movie = result['results'][0]
            title = movie.get('title') or 'عنوان نامشخص'
            release_date = movie.get('release_date') or 'نامشخص'
            vote_average = movie.get('vote_average', 0)
            overview = movie.get('overview') or 'خلاصه‌ای برای این فیلم ثبت نشده است.'
            poster_path = movie.get('poster_path')
            poster_url = (f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None)
            markup = types.InlineKeyboardMarkup()
            download_button = types.InlineKeyboardButton('دانلود فیلم', callback_data=f"download_{movie['id']}")
            markup.add(download_button)
            caption = (
                f"🎬 فیلم پیدا شد:\n{title}\n"
                f"📅 تاریخ انتشار: {release_date}\n"
                f"⭐ امتیاز: {vote_average}\n"
                f"📝 خلاصه فیلم:\n{overview}"
            )
            if poster_url:
                bot.send_photo(
                    message.chat.id,
                    poster_url,
                    caption=caption,
                    reply_markup=markup
                )
            else:
                bot.send_message(
                    message.chat.id,
                    caption,
                    reply_markup=markup
                )

if __name__ == '__main__':
    print("🤖 Bot is running...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
