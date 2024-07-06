import requests
import os
import cairosvg
import tempfile
import datetime

import image_generation as ig

from PIL import Image
from dotenv import load_dotenv

headers = {
    "X-Auth-Token": os.getenv("API_KEY"),
}

### Load the environment variables that is located in the .env file one directory above
load_dotenv(dotenv_path="../.env")


def get_team_flag(team_name):
    """
    Get the flag of the team in PNG format
    """
    # get the teams
    teams_url = "https://api.football-data.org/v4/competitions/EC/teams"
    teams_response = requests.get(teams_url, headers=headers)
    teams = teams_response.json()

    # create the path of the flag
    flag_path = f"flags/{team_name}.png"

    # check if the flag already exists
    if os.path.exists(flag_path):
        return flag_path

    # loop through the teams to find the team name
    for team in teams["teams"]:
        if team["name"] == team_name:
            # get the flag of the team in SVG format
            flag_url = team["crest"]
            flag_response = requests.get(flag_url)

            # save the SVG to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".svg") as temp_svg:
                temp_svg.write(flag_response.content)
                temp_svg_path = temp_svg.name

            # convert the SVG to PNG using CairoSVG
            cairosvg.svg2png(url=temp_svg_path, write_to=f"flags/{team_name}.png")

            # remove the temporary SVG file
            os.remove(temp_svg_path)

            # resize the flag
            flag = Image.open(flag_path)
            flag = flag.resize((80, 53))

            # save the resized flag
            flag.save(flag_path)

            return flag_path


def get_group_stage_standings():
    """
    Get the group stage and the corresponding teams in order to generate the image of the groups
    """
    # get the euro 2024 group stages
    teams_url = "https://api.football-data.org/v4/competitions/EC/standings"
    teams_response = requests.get(teams_url, headers=headers)
    teams = teams_response.json()

    # return the image of the group stage
    return ig.get_image_group_stage(teams)


def get_daily_calendar():
    """
    Get the daily calendar of matches
    """

    # create a function to obtain only the matches of the current day
    def get_matches_today(matches):
        """
        Get the matches of the current day
        """
        # get the current date
        current_date = datetime.now().date()

        # filter the matches of the current day
        matches_today = [
            match for match in matches if match["utcDate"].date() == current_date
        ]

        return matches_today

    # get the euro 2024 calendar
    calendar_url = "https://api.football-data.org/v4/competitions/EC/matches"
    calendar_response = requests.get(calendar_url, headers=headers)
    calendar = calendar_response.json()

    # get the matches
    matches = calendar["matches"]
    today_matches = get_matches_today(matches)

    if not today_matches:
        return None, None

    return today_matches, ig.get_matchday_image(today_matches)
