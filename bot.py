from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from fastapi import FastAPI, Request
import uvicorn
from rembg import remove
from PIL import Image, ImageEnhance
import os
import asyncio

TOKEN = os.getenv("TOKEN", "8022914630:AAHnT4QEeHZaeClvbJOm5F8vZGmoovJpXM8")

# Telegram application setup (global for FastAPI handler)
application = ApplicationBuilder().token(TOKEN).build()

# ... (Paste all handler functions from your existing code: start, templates, button, handle_image, etc.) ...

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... as before ...

async def templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... as before ...

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... as before ...

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... as before ...

async def dimension_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... as before ...

async def process_and_send_all(update, context):
    # ... as before ...

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... as before ...

# Add handlers to application
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("templates", templates))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.PHOTO, handle_image))
application.add_handler(CommandHandler("done", done))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), dimension_response))

# ==== FastAPI Integration ====
app_fastapi = FastAPI()

@app_fastapi.post("/webhook")
async def telegram_webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, application.bot)
    # Put the update in the handling queue
    await application.update_queue.put(update)
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("bot:app_fastapi", host="0.0.0.0", port=port)
