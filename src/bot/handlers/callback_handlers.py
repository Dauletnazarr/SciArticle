from bot.tasks import handle_vote_callback_task

async def handle_vote_callback(update, context):
    data = update.callback_query.data
    user = update.callback_query.from_user

    handle_vote_callback_task.delay(data, user.id, user.username or user.full_name)

    await update.callback_query.answer("Голос принят!")