import os, random, requests, logging
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("waifu")

BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 10000))

SFW = ["waifu", "neko", "shinobu", "megumin", "maid", "uniform", "selfies"]
NSFW_CATS = ["waifu", "neko", "trap"]

def fetch(cat, nsfw=False):
    base = "https://api.waifu.pics/nsfw/" if nsfw else "https://api.waifu.pics/sfw/"
    try:
        r = requests.get(base + cat, timeout=8)
        if r.ok: return r.json().get("url")
    except: return None

def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌸 Random Waifu", callback_data="waifu")],
        [InlineKeyboardButton("😺 Neko", callback_data="neko"),
         InlineKeyboardButton("🟣 Shinobu", callback_data="shinobu")],
        [InlineKeyboardButton("💥 Megumin", callback_data="megumin"),
         InlineKeyboardButton("👗 Maid", callback_data="maid")],
        [InlineKeyboardButton("🔞 NSFW", callback_data="nsfw_menu")],
    ])

async def send_img(target, ctx, cat, nsfw):
    chat_id = target.message.chat_id
    reply_to = target.message.message_id
    msg = await ctx.bot.send_message(chat_id, "✨ Summoning waifu...")
    url = fetch(cat, nsfw)
    if not url: return await msg.edit_text("❌ Failed. Try again.")
    try:
        await ctx.bot.send_photo(chat_id=chat_id, photo=url,
            caption=f"🌸 {cat.capitalize()}\n💖 /waifu for more",
            reply_to_message_id=reply_to,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Another", callback_data=cat),
                InlineKeyboardButton("🏠 Menu", callback_data="home")
            ]]))
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

async def start(u, c): await u.message.reply_text(
    f"🌸 Hey {u.effective_user.first_name}!\nPick a category:", reply_markup=kb_home())

async def help_cmd(u, c): await u.message.reply_text(
    "/waifu /neko /shinobu /megumin /maid /random\nInline: @yourbotname waifu",
    reply_markup=kb_home())

async def waifu(u, c): await send_img(u.message, c, "waifu", False)
async def neko(u, c): await send_img(u.message, c, "neko", False)
async def shinobu(u, c): await send_img(u.message, c, "shinobu", False)
async def megumin(u, c): await send_img(u.message, c, "megumin", False)
async def maid(u, c): await send_img(u.message, c, "maid", False)
async def random_cmd(u, c): await send_img(u.message, c, random.choice(SFW), False)

async def nsfw_cmd(u, c):
    if u.effective_chat.type != "private":
        return await u.message.reply_text("🔞 NSFW only in private chat.")
    btns = [[InlineKeyboardButton(f"🔞 {x}", callback_data=f"nsfw_{x}")] for x in NSFW_CATS]
    btns.append([InlineKeyboardButton("« Back", callback_data="home")])
    await u.message.reply_text("🔞 NSFW Categories:", reply_markup=InlineKeyboardMarkup(btns))

async def button(u, c):
    q = u.callback_query; await q.answer(); d = q.data
    if d == "home":
        await q.edit_message_text("🌸 Waifu Grabber", reply_markup=kb_home())
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
        await send_img(q, c, d, False)

# Health server in background thread
def run_health():
    async def health(req): return web.Response(text="ok")
    app = web.Application()
    app.router.add_get("/", health)
    web.run_app(app, host="0.0.0.0", port=PORT)

def main():
    Thread(target=run_health, daemon=True).start()
    log.info(f"Health server on port {PORT}")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    for cmd, fn in [("waifu",waifu),("neko",neko),("shinobu",shinobu),
                     ("megumin",megumin),("maid",maid),("random",random_cmd),
                     ("nsfw",nsfw_cmd)]:
        app.add_handler(CommandHandler(cmd, fn))
    app.add_handler(CallbackQueryHandler(button))
    log.info("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()