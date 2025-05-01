from bot.tasks import create_request_task

async def handle_request(update, context):
    text = update.message.text or ""
    if not text.startswith("/request"):
     return

    doi = text.split(" ", 1)[1].strip()
    user = update.effective_user

    create_request_task.delay(
         doi,
         update.effective_chat.id,
         update.message.message_id,
         user.id,
         user.username or user.full_name
     )