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
import os
from rembg import remove
from PIL import Image, ImageEnhance
from dotenv import load_dotenv
import asyncio
from io import BytesIO

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Bot token not found in environment!")

# ========== FastAPI App ==========
app = FastAPI()

@app.get("/")
async def home():
    return {"message": "Bot is running!"}

@app.post("/")
async def handle(request: Request):
    return await application.update_queue.put(await request.json())

# ========== Bot Setup ==========
application = ApplicationBuilder().token(TOKEN).build()

# In-memory storage for user choices
user_preferences = {}

# ========== Helper Functions ==========
def process_image(image_data, method, template_path):
    image = Image.open(BytesIO(image_data)).convert("RGBA")
    no_bg = remove(image)

    # Resize logic
    template = Image.open(template_path).convert("RGBA")
    temp_w, temp_h = template.size
    img_w, img_h = no_bg.size

    if method == "scale_height":
        new_h = int(temp_h * 0.9)
        scale = new_h / img_h
        new_w = int(img_w * scale)
    else:  # scale_width
        new_w = int(temp_w * 0.9)
        scale = new_w / img_w
        new_h = int(img_h * scale)

    resized = no_bg.resize((new_w, new_h))
    offset = ((temp_w - new_w) // 2, (temp_h - new_h) // 2)
    template.paste(resized, offset, resized)

    result = BytesIO()
    result.name = "final.png"
    template.save(result, "PNG")
    result.seek(0)
    return result

# ========== Bot Handlers ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Template 1", callback_data="template_1"),
         InlineKeyboardButton("Template 2", callback_data="template_2")],
        [InlineKeyboardButton("Scale by Height", callback_data="scale_height"),
         InlineKeyboardButton("Scale by Width", callback_data="scale_width")]
    ]
    user_preferences[update.effective_user.id] = {"template": "template_1", "scale": "scale_height"}
    await update.message.reply_text("Send me an image.", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_data = await file.download_as_bytearray()

    user_id = update.effective_user.id
    prefs = user_preferences.get(user_id, {"template": "template_1", "scale": "scale_height"})

    template_file = "template1.png" if prefs["template"] == "template_1" else "template2.png"
    result = process_image(image_data, prefs["scale"], template_file)

    await update.message.reply_photo(result, caption="Here is your final image.")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    prefs = user_preferences.setdefault(user_id, {})

    if query.data.startswith("template_"):
        prefs["template"] = query.data
        await query.answer("Template selected.")
    elif query.data.startswith("scale_"):
        prefs["scale"] = query.data
        await query.answer("Scaling method selected.")

    await query.edit_message_text("Send your image now or select more options.", reply_markup=query.message.reply_markup)

# ========== Register Handlers ==========
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.PHOTO, handle_image))
application.add_handler(CallbackQueryHandler(button))

# ========== Run Server ==========
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Use Render-provided port
    uvicorn.run("bot:app", host="0.0.0.0", port=port)
