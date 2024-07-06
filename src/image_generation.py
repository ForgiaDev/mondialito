import os
import io

import API_connection as API

from datetime import datetime, timedelta
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont


## Load the environment variables that is located in the .env file one directory above
load_dotenv(dotenv_path="../.env")


def get_image_group_stage(teams):
    """
    Get the image of the group stage
    """
    # load the background image
    image = Image.open("background.png")

    # resize the image
    image = image.resize((1280, 720))

    # set the transparency level
    image.putalpha(30)

    # calculate the width and height
    width, height = image.size

    # draw on the image
    draw = ImageDraw.Draw(image)

    # load the font
    font_group = ImageFont.truetype(os.environ.get("FONT_NAME"), 40)
    font_team = ImageFont.truetype(os.environ.get("FONT_NAME"), 30)

    # text color (white)
    text_color = (255, 255, 255)

    # starting position using size of the image
    x = width // 2 - 400
    y = height // 2 - 200

    # for each group print the teams in order of position and the corresponding score
    for group in teams["standings"]:
        draw.text((x, y), f"{group['group']}", fill=text_color, font=font_group)
        y += 50
        for team in group["table"]:
            draw.text(
                (x, y),
                f"{team['position']}. {team['team']['name']}\t - {team['points']} points",
                fill=text_color,
                font=font_team,
            )
            y += 40

    # save the image using BytesIO
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    return image_bytes


def get_matchday_image(today_matches):
    """
    Create the image of the matches of the current matchday
    """
    # load the background image
    image = Image.open("background.png")

    # resize the image
    image = image.resize((1280, 720))

    # set the transparency level
    image.putalpha(30)

    # calculate the width and height
    width, height = image.size

    # draw on the image
    draw = ImageDraw.Draw(image)

    # load the font
    font_date = ImageFont.truetype(os.environ.get("FONT_NAME"), 40)
    font_time = ImageFont.truetype(os.environ.get("FONT_NAME"), 20)
    font_match = ImageFont.truetype(os.environ.get("FONT_NAME"), 30)

    # text color (white)
    text_color = (255, 255, 255)

    # starting position using size of the image
    x = width // 2 - 400
    y = height // 2 - 200

    # format the date
    formatted_date = datetime.strptime(datetime.now().date(), "%Y-%m-%d").strftime(
        "%d/%m/%Y"
    )

    draw.text(
        (x + 225, y - 100),
        f"Matchday {formatted_date}",
        fill=text_color,
        font=font_date,
    )

    # loop through the matches of today
    for i, match in enumerate(today_matches):

        if i == 2:
            x = width // 2 + 50
            y = height // 2 - 200

        # load the team names
        home_team = match["homeTeam"]["name"]
        away_team = match["awayTeam"]["name"]

        # get the score of the match
        score_home = (
            match["score"]["fullTime"]["home"] if match["status"] == "FINISHED" else "-"
        )
        score_away = (
            match["score"]["fullTime"]["away"] if match["status"] == "FINISHED" else "-"
        )

        # get the flags of the teams
        flag_home = API.get_flag(home_team)
        flag_away = API.get_flag(away_team)

        # get the time of the match increased by 2 hours
        time = (
            datetime.strptime(match["utcDate"], "%Y-%m-%dT%H:%M:%S%z")
            + timedelta(hours=2)
        ).strftime("%H:%M")

        # get the group of the match or the stage if it's not a group stage match
        group = match["group"]
        stage = match["stage"]

        if group:
            draw.text((x, y), f"{time}\t[{group}]", fill=text_color, font=font_time)
        else:
            draw.text((x, y), f"{time}\t[{stage}]", fill=text_color, font=font_time)

        y += 40

        image.paste(Image.open(flag_home), (x, y))
        draw.text((x + 100, y), f"{home_team}", fill=text_color, font=font_match)
        draw.text((x + 300, y), f"{score_home}", fill=text_color, font=font_match)

        y += 80

        image.paste(Image.open(flag_away), (x, y))
        draw.text((x + 100, y), f"{away_team}", fill=text_color, font=font_match)
        draw.text((x + 300, y), f"{score_away}", fill=text_color, font=font_match)
        y += 100

    # save the image using BytesIO
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    return image_bytes
