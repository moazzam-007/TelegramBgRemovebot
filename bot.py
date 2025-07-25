from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from fastapi import FastAPI, Request
from PIL import Image, ImageEnhance
from rembg import remove
from dotenv import load_dotenv
import os
import io
import asyncio

# Load .env variables
load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("TOKEN not found in .env file!")

# --- FASTAPI ---
app_fastapi = FastAPI()

@app_fastapi.get("/")
def root():
    return {"status": "Bot is running fine ✅"}

@app_fastapi.post("/webhook")
async def telegram_webhook(update: dict):
    await application.update_queue.put(Update.de_json(update, application.bot))
    return {"ok": True}

# --- TELEGRAM BOT LOGIC ---
application = ApplicationBuilder().token(TOKEN).build()

# Templates
TEMPLATES = {
    "1": "templates/1.png",
    "2": "templates/2.png",
    "3": "templates/3.png",
}

# Button Interface
def get_template_buttons():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Template 1", callback_data="1"),
        InlineKeyboardButton("Template 2", callback_data="2"),
        InlineKeyboardButton("Template 3", callback_data="3"),
    ]])

# Store user preferences
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"template": "1", "mode": "width"}
    await update.message.reply_text(
        "👋 Send me an image and I'll remove background and paste it on your template.\n\n"
        "Choose a template:", reply_markup=get_template_buttons()
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    template_id = query.data
    user_id = query.from_user.id
    user_data.setdefault(user_id, {})
    user_data[user_id]["template"] = template_id
    await query.edit_message_text(f"✅ Template {template_id} selected.\nNow send an image.")

async def process_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_prefs = user_data.get(user_id, {"template": "1", "mode": "width"})
    template_path = TEMPLATES.get(user_prefs["template"], "templates/1.png")
    resize_mode = user_prefs.get("mode", "width")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    
    try:
        # Process image
        input_image = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        no_bg = remove(input_image)

        template = Image.open(template_path).convert("RGBA")
        template_width, template_height = template.size

        # Resize
        if resize_mode == "width":
            base_width = int(template_width * 0.8)
            w_percent = base_width / float(no_bg.width)
            h_size = int((float(no_bg.height) * w_percent))
            no_bg = no_bg.resize((base_width, h_size), Image.Resampling.LANCZOS)
        else:  # height
            base_height = int(template_height * 0.8)
            h_percent = base_height / float(no_bg.height)
            w_size = int((float(no_bg.width) * h_percent))
            no_bg = no_bg.resize((w_size, base_height), Image.Resampling.LANCZOS)

        # Center paste
        paste_x = (template_width - no_bg.width) // 2
        paste_y = (template_height - no_bg.height) // 2
        template.paste(no_bg, (paste_x, paste_y), no_bg)

        # Save and send
        output_buffer = io.BytesIO()
        template.save(output_buffer, format='PNG')
        output_buffer.seek(0)

        await update.message.reply_photo(photo=output_buffer)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# --- HANDLERS ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_button))
application.add_handler(MessageHandler(filters.PHOTO, process_image))

# --- RUN WITH Uvicorn in Render ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot:app_fastapi", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
