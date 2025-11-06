import os
import random
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- Cấu hình token ---
TOKEN = os.getenv("TOKEN") or "8426687666:AAHc8IRdvsaztY4UWsrmb1CP1HGUrAsUj0A"

# --- Biến toàn cục ---
games = {}  # group_id -> game state


# --- Kiểm tra từ có nghĩa hay không ---
def is_valid_word(word: str) -> bool:
    try:
        res = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower()}")
        return res.status_code == 200
    except:
        return False


# --- Lệnh /batdau ---
async def batdau(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in games:
        await update.message.reply_text("❗ Trò chơi đã bắt đầu rồi!")
        return

    games[chat_id] = {
        "players": set(),
        "started": False,
        "current_word": None,
        "player_turn": None,
        "player_map": {}
    }
    await update.message.reply_text("🎮 Trò chơi nối từ bắt đầu! Mọi người gõ /thamgia trong 30 giây để tham gia.")

    # đếm ngược 30s
    await context.job_queue.run_once(start_game, 30, chat_id=chat_id, name=str(chat_id))


# --- Lệnh /thamgia ---
async def thamgia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    if chat_id not in games:
        await update.message.reply_text("❌ Chưa có trò chơi nào. Gõ /batdau để bắt đầu!")
        return

    g = games[chat_id]
    if g["started"]:
        await update.message.reply_text("⏳ Trò chơi đã bắt đầu rồi!")
        return

    g["players"].add(user.id)
    g["player_map"][user.id] = user.first_name
    await update.message.reply_text(f"✅ {user.first_name} đã tham gia!")


# --- Khi hết 30s sẽ chạy ---
async def start_game(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = int(job.chat_id)
    g = games.get(chat_id)
    if not g or len(g["players"]) < 2:
        games.pop(chat_id, None)
        await context.bot.send_message(chat_id, "😢 Không đủ người chơi, hủy trò chơi.")
        return

    g["started"] = True
    g["current_word"] = random.choice(["mèo", "chó", "bàn", "cây", "hoa"])
    g["player_turn"] = random.choice(list(g["players"]))
    await context.bot.send_message(
        chat_id,
        f"🎯 Trò chơi bắt đầu!\nTừ đầu tiên là: *{g['current_word']}*\n👉 Lượt của {g['player_map'][g['player_turn']]}",
        parse_mode="Markdown"
    )


# --- Lệnh /ketthuc ---
async def ketthuc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games:
        await update.message.reply_text("❌ Không có trò chơi nào đang diễn ra.")
        return

    g = games.pop(chat_id)
    names = [g["player_map"].get(uid, str(uid)) for uid in g["players"]]
    await update.message.reply_text("🏁 Trò chơi kết thúc!\nNgười chơi: " + ", ".join(names))


# --- Lệnh /reset ---
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    games.pop(chat_id, None)
    await update.message.reply_text("♻️ Trò chơi đã được đặt lại.")


# --- Xử lý nối từ ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    text = update.message.text.strip().lower()

    if chat_id not in games or not games[chat_id]["started"]:
        return

    g = games[chat_id]

    # Nếu chưa đến lượt người này
    if user.id != g["player_turn"]:
        return

    if not is_valid_word(text):
        await update.message.reply_text(f"❌ '{text}' không có nghĩa, {user.first_name} bị loại!")
        g["players"].discard(user.id)
        if len(g["players"]) == 1:
            winner = list(g["players"])[0]
            await update.message.reply_text(f"🏆 {g['player_map'][winner]} là người chiến thắng!")
            games.pop(chat_id, None)
            return
        else:
            g["player_turn"] = random.choice(list(g["players"]))
            await update.message.reply_text(f"➡️ Lượt tiếp theo: {g['player_map'][g['player_turn']]}")
            return

    g["current_word"] = text
    # Chọn người kế tiếp
    next_players = [p for p in g["players"] if p != user.id]
    if not next_players:
        await update.message.reply_text(f"🏆 {user.first_name} là người chiến thắng!")
        games.pop(chat_id, None)
        return

    g["player_turn"] = random.choice(next_players)
    await update.message.reply_text(
        f"✅ '{text}' hợp lệ!\n🎯 Lượt tiếp theo: {g['player_map'][g['player_turn']]}."
    )


# --- Main ---
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("batdau", batdau))
    app.add_handler(CommandHandler("thamgia", thamgia))
    app.add_handler(CommandHandler("ketthuc", ketthuc))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

