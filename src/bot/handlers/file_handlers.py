from bot.models import Request
from bot.tasks import handle_pdf_upload_task


async def handle_pdf_upload(update, context):
    msg = update.message
    if not msg.reply_to_message:
     return
    f = await context.bot.get_file(msg.document.file_id)
    tmp_path = f"/tmp/{msg.document.file_id}"
    await f.download_to_drive(tmp_path)
    req_msg_id = msg.reply_to_message.message_id
    req = Request.objects.get(request_message_id=req_msg_id)
    handle_pdf_upload_task.delay(
        req_msg_id,
        req.id,
        msg.document.file_id,
        msg.document.file_name,
        msg.from_user.id,
        msg.from_user.username or msg.from_user.full_name
    )
