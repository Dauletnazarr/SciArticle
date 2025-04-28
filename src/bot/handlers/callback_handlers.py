import datetime

from django.utils import timezone
from telegram import Update
from telegram.ext import ContextTypes

from bot.tasks import schedule_notification_deletion, schedule_pdf_deletion
from bot.models import ChatUser, PDFUpload, Validation, Request, Config


async def handle_vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    try:
        action, pdf_id_str = data.split(":")
        pdf_id = int(pdf_id_str)
    except Exception:
        return


    try:
        pdf_upload = PDFUpload.objects.select_related('request', 'user').get(id=pdf_id)
    except PDFUpload.DoesNotExist:
        return

    req = pdf_upload.request
    uploader = pdf_upload.user
    requester = req.user
    voter_tg_id = query.from_user.id
    voter_name = query.from_user.username or query.from_user.full_name

    if requester and requester.user_id == voter_tg_id:
        await context.bot.answer_callback_query(callback_query_id=query.id, text="Вы не можете голосовать по собственному запросу.", show_alert=True)
        return
    if uploader and uploader.user_id == voter_tg_id:
        await context.bot.answer_callback_query(callback_query_id=query.id, text="Вы не можете голосовать за свой PDF.", show_alert=True)
        return

    voter, _ = ChatUser.objects.get_or_create(user_id=voter_tg_id, defaults={"username": voter_name})
    voter.username = voter_name or voter.username
    voter.save()

    existing_vote = Validation.objects.filter(pdf_upload=pdf_upload, user=voter).first()
    if existing_vote:
        return

    vote_value = True if action == "vote_valid" else False
    Validation.objects.create(pdf_upload=pdf_upload, user=voter, vote=vote_value, voted_at=timezone.now())
    voter.validation_count = (voter.validation_count or 0) + 1
    voter.save()

    config = Config.objects.first()
    if config:
        thank_text = (
            f"Спасибо, что проверили PDF (DOI: {req.doi})! "
            f"Вы помогли проверить {voter.validation_count} раз(а). "
            f"За {config.validations_for_subscription} проверок вы получаете подписку на бота."
        )
    else:
        thank_text = (
            f"Спасибо, что проверили PDF (DOI: {req.doi})! "
            f"Вы помогли проверить {voter.validation_count} раз(а)."
        )
    if not voter.has_bot:
        chat_notify = await context.bot.send_message(chat_id=req.chat_id, text=f"@{voter.username}, помог {voter.validation_count} раз(а), проверив исследование! Зайдите в @SciArticleBot, чтобы получить награду.")
        schedule_notification_deletion(req.chat_id, chat_notify.message_id, delay=3600)
    else:
        await context.bot.send_message(chat_id=voter.user_id, text=thank_text)

    votes = Validation.objects.filter(pdf_upload=pdf_upload)
    total_votes = votes.count()
    if total_votes >= 3:
        correct_votes = votes.filter(vote=True).count()
        incorrect_votes = total_votes - correct_votes
        pdf_upload.is_valid = True if correct_votes > incorrect_votes else False
        pdf_upload.validated_at = timezone.now()
        pdf_upload.save()
        try:
            await context.bot.edit_message_reply_markup(chat_id=req.chat_id, message_id=pdf_upload.chat_message_id, reply_markup=None)
        except:
            pass

        if pdf_upload.is_valid:
            req.status = "completed"
            req.save()
            if requester:
                if requester.has_bot:
                    await context.bot.send_message(chat_id=requester.user_id, text=f"✅ PDF по запросу {req.doi} найден и подтвержден! Спасибо за ожидание.")
                else:
                    await context.bot.send_message(chat_id=req.chat_id, text=f"✅ @{requester.username}, для вашей статьи {req.doi} найден корректный PDF!")
        else:
            req.status = "completed"
            req.save()
            new_req = Request.objects.create(
                doi=req.doi,
                chat_id=req.chat_id,
                created_at=timezone.now(),
                expires_at=timezone.now() + datetime.timedelta(days=3),
                status="pending",
                user=requester
            )
            await context.bot.send_message(
                chat_id=req.chat_id,
                text=f"📄 *Запрос на статью* {req.doi}\n_Предыдущий PDF признан некорректным, требуется другой источник._",
                parse_mode="Markdown"
            )
        schedule_pdf_deletion(pdf_upload.chat_message_id, req.chat_id, delay=3*24*3600)
