import logging
import os

from datetime import timedelta, datetime
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
)

import src.db_partite as db
import src.API_connection as API

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


async def get_image_group_stage(bot):
    """
    Get the image of the group stage
    """
    group_stage_image = API.get_group_stage_standings()

    # send the image to the group chat
    await bot.send_photo(
        chat_id=os.environ.get("GROUP_CHAT_ID"),
        photo=group_stage_image,
    )


async def process_daily_matches(bot, job_queue):
    """
    Send the daily matches to the group chat in an automatic way
    """
    matches_today, daily_image_calendar = API.get_daily_calendar()

    if not matches_today:
        await bot.send_message(
            chat_id=os.environ.get("GROUP_CHAT_ID"),
            text="No matches today!" + CRY_EMOTE,
        )
    else:
        if matches_today[0]["stage"] == "GROUP_STAGE":
            await get_image_group_stage(bot)
        
        await bot.send_photo(
            chat_id=os.environ.get("GROUP_CHAT_ID"),
            photo=daily_image_calendar,
        )
        await schedule_poll_closing(bot, job_queue, matches_today)


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
    update_results_handler = CommandHandler("results", update_result_handler_func)
    leaderboard_handler = CommandHandler("leaderboard", leaderboard_handler_func)

    ### Unknown command handler
    unknown_handler = MessageHandler(filters.COMMAND, unknown_handler_func)

    ### Add handlers
    application.add_handler(start_handler)
    application.add_handler(sendtogroup_handler)
    application.add_handler(update_results_handler)
    application.add_handler(leaderboard_handler)

    ### Unknown command handler
    application.add_handler(unknown_handler)

    bot, job_queue = application.bot, application.job_queue

    # schedule.every().minute.at(":00").do(process_daily)

    # schedule.every().day.at("07:00").do(process_daily)
    # schedule.every().day.at("00:00").do(send_leaderboard)

    # we can just do it via telegram bot using run_repeating

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
    # repeat every minute for testing
    # job_queue.run_repeating(
    #     lambda *args: process_daily_matches(bot, job_queue),
    #     interval=timedelta(minutes=1),
    #     first=next_7am,
    # )

    # for testing purposes create a job that runs every 10 seconds starting from now
    job_queue.run_repeating(
        lambda *args: process_daily_matches(bot, job_queue),
        interval=timedelta(seconds=10),
        first=timedelta(seconds=0),
    )

    ### Run polling
    application.run_polling()


if __name__ == "__main__":
    main()
