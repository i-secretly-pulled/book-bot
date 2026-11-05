# -*- coding: utf-8 -*-
# ============================================================
#  БОТ «КНИЖНЫЙ ЧЕРВЬ» — учёт чтения книг с кнопками
#  1) Вставь свой токен от @BotFather в строку TOKEN ниже
#  2) Запусти: py book_bot.py
# ============================================================

import json, os, html, random
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = ""

try:
    with open("token.txt", "r", encoding="utf-8") as f:
        TOKEN = f.read().strip()
except FileNotFoundError:
    print("Ошибка: файл token.txt не найден! Создай его и вставь туда токен.")
    exit()

DB_FILE = "books.json"

# ---------------- хранилище ----------------

def load():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load()

def user_data(uid):
    if str(uid) not in db:
        db[str(uid)] = {"books": {}, "pages": {}, "finished": []}
    return db[str(uid)]

# ---------------- клавиатура (кнопки внизу экрана) ----------------

main_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📚 Моя полка"),      KeyboardButton("📊 Статистика")],
        [KeyboardButton("➕ Добавить книгу"), KeyboardButton("📖 Отметить прогресс")],
        [KeyboardButton("🏁 Завершить книгу"), KeyboardButton("🗑 Убрать книгу")],
        [KeyboardButton("ℹ️ Как пользоваться")],
    ],
    resize_keyboard=True,
)

# ---------------- маленькие помощники ----------------

PRAISE = [
    "Кофе, плед и книга — идеальный вечер ☕",
    "Ты читаешь, а мир подождёт 🌿",
    "Ещё немного — и полка пополнится! 🌟",
    "С каждой страницей ты становишься мудрее 🦉",
    "Темп отличный, не сбавляй! 🔥",
]

def bar(percent):
    filled = max(0, min(10, percent // 10))
    return "▓" * filled + "░" * (10 - filled)

def esc(text):
    return html.escape(str(text))

HELP_TEXT = (
    "📖 <b>Как пользоваться ботом</b>\n\n"
    "Все действия — через кнопки внизу экрана, команды не обязательны 🙂\n\n"
    "➕ <b>Добавить книгу</b> — бот попросит написать:\n"
    "   <code>Автор, Название, страниц</code>\n"
    "   Например: <code>Достоевский, Преступление и наказание, 671</code>\n\n"
    "📖 <b>Отметить прогресс</b> — напиши:\n"
    "   <code>Название, сколько страниц прочитал</code>\n"
    "   Например: <code>Преступление и наказание, 50</code>\n\n"
    "🏁 <b>Завершить книгу</b> — просто напиши название.\n\n"
    "🗑 <b>Убрать книгу</b> — напиши название, и она покинет полку.\n\n"
    "📚 <b>Моя полка</b> — список книг с прогрессом.\n\n"
    "А ещё всё это работает командами: /add /read /finish /list /stats /drop"
)

# ---------------- действия (общие для команд и кнопок) ----------------

async def do_add(update: Update, text: str):
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 3 or not parts[-1].isdigit():
        context_set = "add"
        update.effective_user  # noop
        await update.message.reply_text(
            "✍️ Напиши в формате:\n<code>Автор, Название, страниц</code>\n\n"
            "Например: <code>Достоевский, Преступление и наказание, 671</code>",
            parse_mode="HTML",
        )
        return False  # ждём правильный ввод дальше
    author = parts[0]
    pages = int(parts[-1])
    title = ", ".join(parts[1:-1]).strip()
    if not title:
        await update.message.reply_text("✍️ Название книги не должно быть пустым 🙂")
        return False
    u = user_data(update.effective_user.id)
    key = title.lower()
    if key in u["books"]:
        await update.message.reply_text("Эта книга уже стоит на полке 😉")
        return True
    u["books"][key] = {
        "title": title,
        "author": author,
        "pages": pages,
        "start": datetime.now().strftime("%d.%m.%Y"),
    }
    save()
    await update.message.reply_text(
        f"📚 <b>Книга встала на полку!</b>\n\n"
        f"📕 <i>{esc(title)}</i>\n"
        f"👤 {esc(author)} · {pages} стр.\n"
        f"🗓 Начало: {u['books'][key]['start']}\n\n"
        "Как прочитаешь кусочек — жми «📖 Отметить прогресс» ☕",
        parse_mode="HTML",
    )
    return True

async def do_read(update: Update, title: str, pages: int):
    u = user_data(update.effective_user.id)
    key = title.strip().lower()
    if key not in u["books"]:
        await update.message.reply_text(
            "🔍 Не нашёл такую книгу на полке.\nГлянь точные названия: «📚 Моя полка»"
        )
        return False
    u["pages"][key] = u["pages"].get(key, 0) + pages
    b = u["books"][key]
    if u["pages"][key] >= b["pages"]:
        u["pages"][key] = b["pages"]
        save()
        await update.message.reply_text(
            f"🏁 <i>{esc(b['title'])}</i> дочитана до последней страницы!\n"
            "Осталось закрыть её кнопкой «🏁 Завершить книгу» 🎉",
            parse_mode="HTML",
        )
        return True
    save()
    total = u["pages"][key]
    percent = int(total / b["pages"] * 100)
    await update.message.reply_text(
        f"✅ <b>+{pages} стр.</b> — «{esc(b['title'])}»\n\n"
        f"{bar(percent)} <b>{percent}%</b>\n"
        f"Прочитано {total} из {b['pages']} стр.\n\n"
        f"{random.choice(PRAISE)}",
        parse_mode="HTML",
    )
    return True

async def do_finish(update: Update, title: str):
    u = user_data(update.effective_user.id)
    key = title.strip().lower()
    if key not in u["books"]:
        await update.message.reply_text(
            "🔍 Не нашёл такую книгу. Глянь точные названия: «📚 Моя полка»"
        )
        return False
    book = u["books"].pop(key)
    u["pages"].pop(key, None)
    u["finished"].append({"title": book["title"], "date": datetime.now().strftime("%d.%m.%Y")})
    save()
    left = len(u["books"])
    await update.message.reply_text(
        f"🏆 <b>Поздравляю!</b>\n\n"
        f"«{esc(book['title'])}» — прочитана от корки до корки!\n"
        f"🗓 Читал с {book['start']} по {datetime.now().strftime('%d.%m.%Y')}\n\n"
        f"Книг на полке осталось: {left}\n"
        "Ставь следующую — полка ждёт ✨",
        parse_mode="HTML",
    )
    return True

async def do_drop(update: Update, title: str):
    u = user_data(update.effective_user.id)
    key = title.strip().lower()
    if key not in u["books"]:
        await update.message.reply_text(
            "🔍 Не нашёл такую книгу. Глянь точные названия: «📚 Моя полка»"
        )
        return False
    book = u["books"].pop(key)
    u["pages"].pop(key, None)
    save()
    await update.message.reply_text(
        f"🗑 «{esc(book['title'])}» покинула полку.\nЧто-нибудь ещё уберём или добавим? 🙂",
        parse_mode="HTML",
    )
    return True

async def show_shelf(update: Update):
    u = user_data(update.effective_user.id)
    if not u["books"]:
        await update.message.reply_text(
            "📚 <b>На полке пока пусто…</b> 😔\n"
            "Пора добавить что-то новенькое!\n\n"
            "Жми «➕ Добавить книгу» — и полка оживёт ✨",
            parse_mode="HTML",
        )
        return
    lines = ["📖 <b>Твоя книжная полка:</b>\n"]
    for i, b in enumerate(u["books"].values(), 1):
        read = u["pages"].get(b["title"].lower(), 0)
        percent = int(read / b["pages"] * 100) if b["pages"] else 0
        lines.append(
            f"{i}. 📕 <b>{esc(b['title'])}</b> — {esc(b['author'])}\n"
            f"   {bar(percent)} {percent}% ({read}/{b['pages']} стр.)\n"
        )
    lines.append("🗃 Что-то убрать? Жми «🗑 Убрать книгу». Приятного чтения! ☕")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def show_stats(update: Update):
    u = user_data(update.effective_user.id)
    pages_total = sum(u["pages"].values())
    done = len(u["finished"])
    reading = len(u["books"])
    lines = [
        "📊 <b>Твоя статистика</b>\n",
        f"📚 Сейчас читаешь: <b>{reading}</b>",
        f"🏆 Прочитано целиком: <b>{done}</b>",
        f"📄 Страниц в активных книгах: <b>{pages_total}</b>",
    ]
    if u["finished"]:
        lines.append("\n🏁 <b>Завершённые книги:</b>")
        for f in u["finished"]:
            lines.append(f"• «{esc(f['title'])}» — {f['date']}")
    else:
        lines.append("\nЗавершённых книг пока нет — всё впереди! ✨")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

# ---------------- команды (для тех, кто любит слэши) ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Привет, {esc(name)}!\n\n"
        "Я — твой уютный помощник для учёта чтения 📖☕\n"
        "Мне можно писать текстом, но проще — жать кнопки внизу 👇\n\n"
        "Начни с «➕ Добавить книгу» — и вперёд!",
        parse_mode="HTML",
        reply_markup=main_menu,
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_shelf(update)

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_stats(update)

async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/add", "").strip()
    if not text:
        context.user_data["awaiting"] = "add"
        await update.message.reply_text(
            "✍️ Напиши в формате:\n<code>Автор, Название, страниц</code>",
            parse_mode="HTML",
        )
        return
    if not await do_add(update, text):
        context.user_data["awaiting"] = "add"

async def read_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/read", "").strip()
    if not text:
        context.user_data["awaiting"] = "read"
        await update.message.reply_text(
            "✍️ Напиши:\n<code>Название, сколько страниц прочитал</code>",
            parse_mode="HTML",
        )
        return
    await handle_read_text(update, context, text)

async def finish_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/finish", "").strip()
    if not text:
        context.user_data["awaiting"] = "finish"
        await update.message.reply_text("✍️ Напиши название книги, которую закончил.")
        return
    if not await do_finish(update, text):
        context.user_data["awaiting"] = "finish"

async def drop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/drop", "").strip()
    if not text:
        context.user_data["awaiting"] = "drop"
        await update.message.reply_text("✍️ Напиши название книги, которую убрать с полки.")
        return
    if not await do_drop(update, text):
        context.user_data["awaiting"] = "drop"

async def handle_read_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 2 or not parts[-1].isdigit():
        context.user_data["awaiting"] = "read"
        await update.message.reply_text(
            "✍️ Напиши:\n<code>Название, сколько страниц прочитал</code>\n"
            "Например: <code>Преступление и наказание, 50</code>",
            parse_mode="HTML",
        )
        return
    pages = int(parts[-1])
    title = ", ".join(parts[:-1])
    if await do_read(update, title, pages):
        context.user_data.pop("awaiting", None)

# ---------------- кнопки и свободный текст ----------------

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    awaiting = context.user_data.get("awaiting")

    # 1) Нажатия на кнопки меню
    if text == "📚 Моя полка":
        await show_shelf(update)
        return
    if text == "📊 Статистика":
        await show_stats(update)
        return
    if text == "ℹ️ Как пользоваться":
        await update.message.reply_text(HELP_TEXT, parse_mode="HTML")
        return
    if text == "➕ Добавить книгу":
        context.user_data["awaiting"] = "add"
        await update.message.reply_text(
            "✍️ Отлично! Напиши в следующем сообщении:\n"
            "<code>Автор, Название, страниц</code>\n\n"
            "Например: <code>Оруэлл, 1984, 328</code>",
            parse_mode="HTML",
        )
        return
    if text == "📖 Отметить прогресс":
        context.user_data["awaiting"] = "read"
        await update.message.reply_text(
            "✍️ Напиши:\n<code>Название, сколько страниц прочитал</code>\n\n"
            "Например: <code>1984, 40</code>",
            parse_mode="HTML",
        )
        return
    if text == "🏁 Завершить книгу":
        context.user_data["awaiting"] = "finish"
        await update.message.reply_text(
            "✍️ Напиши название книги, которую дочитал 🏁"
        )
        return
    if text == "🗑 Убрать книгу":
        context.user_data["awaiting"] = "drop"
        await update.message.reply_text(
            "✍️ Напиши название книги, которую убрать с полки 🗑"
        )
        return

    # 2) Бот ждёт ввод после нажатия кнопки — принимаем данные
    if awaiting == "add":
        if await do_add(update, text):
            context.user_data.pop("awaiting", None)
        return
    if awaiting == "read":
        await handle_read_text(update, context, text)
        return
    if awaiting == "finish":
        if await do_finish(update, text):
            context.user_data.pop("awaiting", None)
        return
    if awaiting == "drop":
        if await do_drop(update, text):
            context.user_data.pop("awaiting", None)
        return

    # 3) Непонятный текст — мягко возвращаем к кнопкам
    await update.message.reply_text(
        "🤔 Хм, это я не совсем поняла.\n"
        "Попробуй кнопки внизу — с ними всё точно сработает 👇",
        reply_markup=main_menu,
    )

# ---------------- запуск ----------------

def main():
    app = Application.builder().token(TOKEN).build()

    # хендлеры команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("add", add_cmd))
    app.add_handler(CommandHandler("read", read_cmd))
    app.add_handler(CommandHandler("finish", finish_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("drop", drop_cmd))

    # хендлер кнопок и любых обычных сообщений — ВСЕГДА последним
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    print("Бот запущен! Не закрывай это окно.")
    app.run_polling()

if __name__ == "__main__":
    main()
