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
    filters,
    ContextTypes,
)
from rembg import remove
from PIL import Image, ImageEnhance
import os

TOKEN = "8022914630:AAHnT4QEeHZaeClvbJOm5F8vZGmoovJpXM8"  # Put your Bot Token here

# -------- 1. Start & Help Command --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome!\n\n1. /templates — Choose template\n2. Send image/photo\n3. Set width/height when prompted\n4. Get background-removed, perfectly centered image!"
    )

# -------- 2. Template List & Select --------
async def templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    templates_dir = "templates/"
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    templates_list = os.listdir(templates_dir)
    if not templates_list:
        await update.message.reply_text("No templates found in templates folder!")
        return
    buttons = [
        [InlineKeyboardButton(t, callback_data=f"template_{t}")] for t in templates_list
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Choose your template:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith("template_"):
        template_name = query.data.replace("template_", "")
        context.user_data["selected_template"] = template_name
        await query.answer()
        await query.edit_message_text(f"Selected template: {template_name}")

# -------- 3. Handle Images / Multi-Image Logic --------
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        if update.message:
            await update.message.reply_text("Please send an image/photo.")
        return
    photo_file = await update.message.photo[-1].get_file()
    file_path = f"images/input_{update.message.message_id}.png"
    await photo_file.download_to_drive(file_path)
    if "images_queue" not in context.user_data:
        context.user_data["images_queue"] = []
    context.user_data["images_queue"].append(file_path)
    context.user_data["awaiting_dimension"] = True
    await update.message.reply_text(
        f"Image received! Ab width ya height set karein —\n"
        f"`width 1000` ya `height 800` type karein.\n"
        f"Aap aur images bhi bhej sakte hain. Sab ho jaaye toh `/done` likhe.",
        parse_mode="Markdown",
    )

# -------- 4. Handle Dimension Input --------
async def dimension_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_dimension"):
        return
    msg = update.message.text.lower()
    try:
        width = height = None
        if "width" in msg:
            width = int(msg.split()[-1])
        elif "height" in msg:
            height = int(msg.split()[-1])
        else:
            raise ValueError
        context.user_data["size"] = (width, height)
        context.user_data["awaiting_dimension"] = False
        await process_and_send_all(update, context)
    except Exception:
        await update.message.reply_text(
            "Please enter in format: `width 1000` ya `height 800`",
            parse_mode="Markdown",
        )

# -------- 5. Enhance, Send, and Delete Images --------
async def process_and_send_all(update, context):
    images_queue = context.user_data.get("images_queue", [])
    size = context.user_data.get("size", (None, None))
    selected_template = context.user_data.get("selected_template", None)
    templates_dir = "templates/"
    template_path = (
        os.path.join(templates_dir, selected_template)
        if selected_template
        else os.path.join(templates_dir, "template1.png")
    )

    if not os.path.exists(template_path):
        await update.message.reply_text(
            "Template image not found. Use /templates to select again."
        )
        return

    for idx, file_path in enumerate(images_queue, 1):
        try:
            output_file = f"images/result_{update.message.message_id}_{idx}.png"
            # Remove BG
            with open(file_path, "rb") as inp:
                out_data = remove(inp.read())
            with open("no_bg.png", "wb") as out:
                out.write(out_data)
            template = Image.open(template_path).convert("RGBA")
            img = Image.open("no_bg.png").convert("RGBA")
            ow, oh = img.size
            tw, th = template.size
            if size[0]:
                w = size[0]
                h = round(oh * (w / ow))
            elif size[1]:
                h = size[1]
                w = round(ow * (h / oh))
            else:
                w, h = 200, 200  # fallback
            img = img.resize((w, h))
            center_x = (tw - w) // 2
            center_y = (th - h) // 2
            template.paste(img, (center_x, center_y), img)
            template.save(output_file)

            # --- Enhance quality before sending ---
            img_enh = Image.open(output_file)
            sharp_enhancer = ImageEnhance.Sharpness(img_enh)
            img_enh = sharp_enhancer.enhance(2.0)
            color_enhancer = ImageEnhance.Color(img_enh)
            img_enh = color_enhancer.enhance(1.2)
            img_enh.save(output_file)

            # --- Send to telegram user ---
            with open(output_file, "rb") as final:
                await update.message.reply_photo(final)

            # --- Cleanup: remove all temp files ---
            if os.path.exists(output_file):
                os.remove(output_file)
            if os.path.exists("no_bg.png"):
                os.remove("no_bg.png")
            if os.path.exists(file_path):
                os.remove(file_path)
        except FileNotFoundError:
            await update.message.reply_text(
                "Template image not found. Please use /templates to select."
            )
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
    context.user_data["images_queue"] = []

# -------- 6. Done Command --------
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("images_queue"):
        await update.message.reply_text("No images in queue! Pehle photo bhejein.")
        return
    if not context.user_data.get("size"):
        await update.message.reply_text(
            "Pehle width ya height set karein (e.g. width 1000)."
        )
        context.user_data["awaiting_dimension"] = True
        return
    await process_and_send_all(update, context)

# -------- 7. Main App Entry --------
if __name__ == "__main__":
    if not os.path.exists("images/"):
        os.makedirs("images/")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("templates", templates))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), dimension_response)
    )
    app.run_polling()
