import os
import random
import requests
import logging
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger("waifu")

BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 10000))

SFW = ["waifu", "neko", "shinobu", "megumin", "maid", "uniform"]
NSFW_CATS = ["waifu", "neko", "trap"]

def fetch(cat, nsfw=False):
    base = "https://api.waifu.pics/nsfw/" if nsfw else "https://api.waifu.pics/sfw/"
    try:
        r = requests.get(base + cat, timeout=10)
        if r.status_code == 200:
            return r.json().get("url")
    except Exception as e:
        log.error(f"Fetch error: {e}")
    return None

def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌸 Random Waifu", callback_data="waifu")],
        [InlineKeyboardButton("😺 Neko", callback_data="neko"),
         InlineKeyboardButton("🟣 Shinobu", callback_data="shinobu")],
        [InlineKeyboardButton("💥 Megumin", callback_data="megumin"),
         InlineKeyboardButton("👗 Maid", callback_data="maid")],
        [InlineKeyboardButton("🔞 NSFW", callback_data="nsfw_menu")],
    ])

async def send_img(update, ctx, cat, nsfw):
    msg = await update.message.reply_text("✨ Summoning waifu...")
    url = fetch(cat, nsfw)
    if not url:
        return await msg.edit_text("❌ Failed to fetch. Try again.")
    try:
        await ctx.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=url,
            caption=f"🌸 {cat.capitalize()}\n💖 /waifu for more",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Another", callback_data=cat),
                 InlineKeyboardButton("🏠 Menu", callback_data="home")]
            ])
        )
        await msg.delete()
    except Exception as e:
        log.error(f"Send error: {e}")
        await msg.edit_text(f"❌ Error: {str(e)[:50]}")

async def start(u, c):
    await u.message.reply_text(
        f"🌸 Hey {u.effective_user.first_name}!\n\nPick a category:",
        reply_markup=kb_home()
    )

async def help_cmd(u, c):
    await u.message.reply_text(
        "Commands:\n/waifu /neko /shinobu /megumin /maid /random\n\nInline: @yourbotname waifu",
        reply_markup=kb_home()
    )

async def waifu(u, c): await send_img(u, c, "waifu", False)
async def neko(u, c): await send_img(u, c, "neko", False)
async def shinobu(u, c): await send_img(u, c, "shinobu", False)
async def megumin(u, c): await send_img(u, c, "megumin", False)
async def maid(u, c): await send_img(u, c, "maid", False)
async def random_cmd(u, c): await send_img(u, c, random.choice(SFW), False)

async def nsfw_cmd(u, c):
    if u.effective_chat.type != "private":
        return await u.message.reply_text("🔞 NSFW only in private chat with bot.")
    btns = [[InlineKeyboardButton(f"🔞 {x}", callback_data=f"nsfw_{x}")] for x in NSFW_CATS]
    btns.append([InlineKeyboardButton("« Back", callback_data="home")])
    await u.message.reply_text("🔞 NSFW Categories:", reply_markup=InlineKeyboardMarkup(btns))

async def button(u, c):
    q = u.callback_query
    await q.answer()
    d = q.data
    if d == "home":
        await q.edit_message_text("🌸 Waifu Grabber\n\nPick a category:", reply_markup=kb_home())
    elif d == "nsfw_menu":
        btns = [[InlineKeyboardButton(f"🔞 {x}", callback_data=f"nsfw_{x}")] for x in NSFW_CATS]
        btns.append([InlineKeyboardButton("« Back", callback_data="home")])
        await q.edit_message_text("🔞 NSFW:", reply_markup=InlineKeyboardMarkup(btns))
    elif d.startswith("nsfw_"):
        cat = d.split("_")[1]
        url = fetch(cat, True)
        if url:
            await q.message.reply_photo(url, caption=f"🔞 {cat}", reply_markup=kb_home())
        else:
            await q.answer("❌ Failed", show_alert=True)
    else:
        msg = await q.message.reply_text("✨ Summoning waifu...")
        url = fetch(d, False)
        if url:
            try:
                await q.message.reply_photo(
                    photo=url,
                    caption=f"🌸 {d.capitalize()}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Another", callback_data=d),
                         InlineKeyboardButton("🏠 Menu", callback_data="home")]
                    ])
                )
                await msg.delete()
            except Exception as e:
                await msg.edit_text(f"❌ {str(e)[:50]}")
        else:
            await msg.edit_text("❌ Failed to fetch.")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, format, *args):
        pass

def run_health():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    log.info(f"Health server on port {PORT}")
    server.serve_forever()

def main():
    Thread(target=run_health, daemon=True).start()
    log.info("Starting bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    
    for cmd, fn in [("waifu", waifu), ("neko", neko), ("shinobu", shinobu),
                     ("megumin", megumin), ("maid", maid), ("random", random_cmd),
                     ("nsfw", nsfw_cmd)]:
        app.add_handler(CommandHandler(cmd, fn))
    
    app.add_handler(CallbackQueryHandler(button))
    
    log.info("Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()