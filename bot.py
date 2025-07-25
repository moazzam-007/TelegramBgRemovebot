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
from fastapi import FastAPI
import uvicorn
from rembg import remove
from PIL import Image
import os
import io
from dotenv import load_dotenv
import asyncio
from datetime import datetime

# Load environment variables
load_dotenv()

# Bot token from environment
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("❌ Bot token not found! Please set TOKEN in your .env file.")

# === FastAPI App (for Render keep-alive) ===
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot is running!"}

# === Telegram Bot App ===
application = ApplicationBuilder().token(TOKEN).build()

# --- Template Options ---
template_options = {
    "1": "template1.png",
    "2": "template2.png",
    # Add more if needed
}

# --- Image Processing Function ---
def process_and_send_all(images, template_path, scale_by="width", size=1200):
    processed = []

    if not os.path.exists("images"):
        os.makedirs("images")

    template = Image.open(template_path).convert("RGBA")

    for i, image_bytes in enumerate(images):
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        removed = remove(image)

        if scale_by == "width":
            new_height = int((size / removed.width) * removed.height)
            removed = removed.resize((size, new_height), Image.LANCZOS)
        else:
            new_width = int((size / removed.height) * removed.width)
            removed = removed.resize((new_width, size), Image.LANCZOS)

        # Center the image
        x = (template.width - removed.width) // 2
        y = (template.height - removed.height) // 2
        template_copy = template.copy()
        template_copy.paste(removed, (x, y), removed)

        output = io.BytesIO()
        output.name = f"result_{i+1}.png"
        template_copy.save(output, format="PNG")
        output.seek(0)
        processed.append(output)

    return processed

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me one or more images.\n\nUse /template to choose a template first."
    )

async def template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("Template 1", callback_data="template_1")],
        [InlineKeyboardButton("Template 2", callback_data="template_2")],
    ]
    await update.message.reply_text(
        "📌 Choose a template:", reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- Image Handling ---
user_state = {}

async def handle_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    photos = update.message.photo or []

    # Get highest resolution image
    images = []
    for photo in photos:
        file = await context.bot.get_file(photo.file_id)
        byte_data = await file.download_as_bytearray()
        images.append(byte_data)

    # Get user state
    template_id = user_state.get(chat_id, {}).get("template", "1")
    scale_by = user_state.get(chat_id, {}).get("scale_by", "width")

    template_path = template_options.get(template_id)
    if not template_path or not os.path.exists(template_path):
        await update.message.reply_text("❌ Template not found.")
        return

    processed = process_and_send_all(images, template_path, scale_by=scale_by)

    for img_io in processed:
        await update.message.reply_photo(photo=img_io)

# --- Callback for Template Buttons ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if data.startswith("template_"):
        template_id = data.split("_")[1]
        user_state.setdefault(chat_id, {})["template"] = template_id
        await query.edit_message_text(f"✅ Template {template_id} selected.")

# --- Scale Mode Commands ---
async def width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_state.setdefault(chat_id, {})["scale_by"] = "width"
    await update.message.reply_text("📏 Scaling mode set to: Width (1200px)")

async def height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_state.setdefault(chat_id, {})["scale_by"] = "height"
    await update.message.reply_text("📏 Scaling mode set to: Height (1200px)")

# === Register All Handlers ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("template", template))
application.add_handler(CommandHandler("width", width))
application.add_handler(CommandHandler("height", height))
application.add_handler(CallbackQueryHandler(handle_buttons))
application.add_handler(MessageHandler(filters.PHOTO, handle_images))

# === Run both FastAPI and Bot ===
async def run():
    loop = asyncio.get_event_loop()
    await application.initialize()
    await application.start()
    print("✅ Bot started.")
    await application.updater.start_polling()
    await application.updater.idle()

def start_all():
    loop = asyncio.get_event_loop()
    loop.create_task(run())

start_all()
