import logging
import os
import src.db_partite as db
import time
from datetime import timedelta, datetime
import schedule
import threading
import asyncio
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
)

### Load environment variables
load_dotenv()

# EMOTES
FIRE_EMOTE = "\U0001F525"
CRY_EMOTE = "\U0001F62D"
ALERT_EMOTE = "\U000026A0"
WARNING_MARK = "\U000026A0"
EXCLAMATION_MARK = "\U00002757"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# utility commands for the bot
async def unknown_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send a message when the command is not recognized
    """
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command.",
    )


async def stg_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send a message to the group chat using the /sendmessage command
    """
    await context.bot.send_message(
        chat_id=os.environ.get("GROUP_CHAT_ID"),
        text=update.message.text.replace("/sendmessage ", ""),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send a message when the command /start is issued
    """
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I'm a bot, please talk to me!",
    )


async def new_match_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Add a new match to the database using the /newmatch command
    """
    current_msg = update.message.text.replace("/newmatch\n", "").split("\n")

    first_team, second_team, datetime_string = current_msg
    ### Try to parse datetime from the third element
    try:
        start_time = datetime.strptime(datetime_string, "%Y-%m-%d %H:%M")
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Invalid date/time format. Please use the format YYYY-MM-DD HH:MM",
        )
        return

    match_id = db.add_match(
        team1=first_team,
        team2=second_team,
        start_time=start_time,
    )

    match_text = f"""
    Match added!
    Match ID: {match_id}
    Match: {first_team} - {second_team}
    Date: {start_time.date()}
    Time: {start_time.time()}
    """

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=match_text,
    )


async def delete_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Delete a match from the database using the /deletematch command
    """
    match_id = update.message.text.replace("/deletematch ", "")

    db.delete_match(match_id)

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"Match {match_id} deleted!"
    )


async def send_daily_matches(bot):
    """
    Send the daily matches to the group chat
    """
    current_date = datetime.now().date()
    matches_today = db.get_daily_matches(current_date)

    for match in matches_today:
        message = f"""
        *{match.team1} - {match.team2}*
        Date: _{match.start_time.date()}_
        Time: _{match.start_time.time()}_
        Place your bet!
        {FIRE_EMOTE}
        """

        # Message(channel_chat_created=False, chat=Chat(api_kwargs={'all_members_are_administrators': True}, id=-4169073932, title='Euro 2024 - PiccoloPollo Edition', type=<ChatType.GROUP>), date=datetime(2024, 6, 10, 21, 22, tzinfo=<UTC>), delete_chat_photo=False, from_user=User(first_name='Euro2024BetBot', id=7201341729, is_bot=True, username='Euro2024_bet_bot'), group_chat_created=False, message_id=92, poll=Poll(allows_multiple_answers=False, id='5998810491957281723', is_anonymous=False, is_closed=False, options=(PollOption(text='1', voter_count=0), PollOption(text='X', voter_count=0), PollOption(text='2', voter_count=0)), question='*Italia - Albania*\n        Date: _2024-06-10_\n        Time: _23:22:00_         Place your bet!         🔥', total_voter_count=0, type=<PollType.REGULAR>), supergroup_chat_created=False)

        message = await bot.send_poll(
            chat_id=os.environ.get("GROUP_CHAT_ID"),
            question=message,
            options=["1", "X", "2"],
            is_anonymous=False,
            allows_multiple_answers=False,
        )

        poll_id = message.poll.id

        ### Add the poll_id to the database
        db.add_poll(poll_id=poll_id, match_id=match.match_id)

    return matches_today


async def process_daily_matches(bot, job_queue):
    """
    Send the daily matches to the group chat, or a message when there are no matches
    """

    # send a test message ehre
    await bot.send_message(
        chat_id=os.environ.get("GROUP_CHAT_ID"),
        text="Hello! I'm here to help you bet on the matches today!",
    )

    matches_today = await send_daily_matches(bot)

    if not matches_today:
        await print_no_daily_matches(bot)
    else:
        await schedule_poll_closing(bot, job_queue, matches_today)


async def print_no_daily_matches(bot):
    """
    Send a message when there are no matches today
    """

    await bot.send_message(
        chat_id=os.environ.get("GROUP_CHAT_ID"),
        text="No matches today!" + CRY_EMOTE,
    )


def schedule_poll_closing(bot, job_queue, matches_today):
    """
    Schedule the closing of the polls
    """
    current_time = datetime.now()

    matches_today = [
        match
        for match in db.get_daily_matches(current_time.date())
        if match.start_time > current_time
    ]

    def close_poll_func(match, poll):
        return lambda: close_poll(bot, match, poll)

    for match in matches_today:
        poll = db.get_poll(match.match_id)

        job_queue.run_once(
            close_poll_func(match, poll)(
                match.start_time - current_time
            ).total_seconds(),
        )


async def close_poll(bot, match, poll):
    """
    Close the poll after the match has started
    """
    message = await bot.stop_poll(
        chat_id=os.environ.get("GROUP_CHAT_ID"), message_id=poll.poll_id
    )

    ### Add the bets to the database
    for option_id, voters in enumerate(message.options):
        for voter in voters.voter_ids:
            if db.get_player(voter) is None:
                db.add_player(user_id=voter, name=voters.voter_usernames[0], score=0)

            db.add_bet(user_id=voter, poll_id=poll.poll_id, bet_value=option_id)

    db.close_poll(poll_id=poll.poll_id)

    await bot.send_message(
        chat_id=os.environ.get("GROUP_CHAT_ID"),
        text=f"{ALERT_EMOTE}: The match {match.team1} - {match.team2} has started! Poll closed!",
    )


async def leaderboard_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send the leaderboard to the group chat
    """
    await send_leaderboard_message(context.bot)


async def send_leaderboard_message(bot):
    players = db.get_leaderboard()

    message = f"""
    {WARNING_MARK} LEADERBOARD {WARNING_MARK}

    {"".join([f"{player.name}:\t{player.score}\n" for player in players])}
    """

    await bot.send_message(chat_id=os.environ.get("GROUP_CHAT_ID"), text=message)


async def update_result_handler_func(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """
    Add the results to the database and update the leaderboard
    """

    current_msg = update.message.text.replace("/results\n", "").split("\n")
    match_id = current_msg[0]
    result = current_msg[1]

    db.update_result(match_id, result)

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"Results added! for match {match_id}"
    )

    match = db.get_match(match_id)

    message = f"""
    {EXCLAMATION_MARK} Final Result {EXCLAMATION_MARK}
    
    {match.team1} - {match.team2}: {result}
    """

    await context.bot.send_message(
        chat_id=os.environ.get("GROUP_CHAT_ID"), text=message
    )

    await send_leaderboard_message(context.bot)


def main():
    ### Application
    application = ApplicationBuilder().token(os.environ.get("TELEGRAM_TOKEN")).build()

    ### Handlers
    start_handler = CommandHandler("start", start)
    sendtogroup_handler = CommandHandler("sendmessage", stg_handler_func)
    new_match_handler = CommandHandler("newmatch", new_match_handler_func)
    update_results_handler = CommandHandler("results", update_result_handler_func)
    leaderboard_handler = CommandHandler("leaderboard", leaderboard_handler_func)

    ### Unknown command handler
    unknown_handler = MessageHandler(filters.COMMAND, unknown_handler_func)

    ### Add handlers
    application.add_handler(start_handler)
    application.add_handler(sendtogroup_handler)
    application.add_handler(new_match_handler)
    application.add_handler(update_results_handler)
    application.add_handler(leaderboard_handler)

    ### Unknown command handler
    application.add_handler(unknown_handler)

    bot, job_queue = application.bot, application.job_queue

    # schedule.every().minute.at(":00").do(process_daily)

    # schedule.every().day.at("07:00").do(process_daily)
    # schedule.every().day.at("00:00").do(send_leaderboard)

    # we can just do it via telegram bot using run_repeating
    # TODO: remove, just for testing
    async def test_message(*args):
        await bot.send_message(
            chat_id=os.environ.get("GROUP_CHAT_ID"), text="test message"
        )

    # job_queue.run_repeating(test_message, interval=10, first=0)

    next_midnight = datetime.replace(
        datetime.now(),
        hour=0,
        minute=0,
    ) + timedelta(days=1)
    
    next_7am = datetime.replace(
        datetime.now(),
        hour=7,
        minute=0,
    ) + timedelta(days=1)

    # run at 00:00 every day
    job_queue.run_repeating(
        lambda *args: send_leaderboard_message(bot),
        interval=timedelta(days=1),
        first=next_midnight,
    )

    # run at 07:00 every day
    job_queue.run_repeating(
        lambda *args: process_daily_matches(bot, job_queue),
        interval=timedelta(days=1),
        first=next_7am,
    )

    ### Run polling
    application.run_polling()


if __name__ == "__main__":
    main()
