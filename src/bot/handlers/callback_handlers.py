from bot.tasks import handle_vote_callback_task

async def handle_vote_callback(update, context):
    callback_query = update.callback_query
    data = update.callback_query.data
    user = update.callback_query.from_user

    result = handle_vote_callback_task.delay(
        callback_query.id, data, user.id, user.username or user.full_name
    ).get()

    if result.get('blocked', False):
        await callback_query.answer(
            text=result['message'],
            show_alert=True
        )
    else:
        await callback_query.answer("Голос принят!")
