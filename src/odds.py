import requests
import os
import cairosvg
import tempfile
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

### Load the environment variables that is located in the .env file one directory above
load_dotenv(dotenv_path="../.env")


# create a function to get the group stage and the corresponding teams in order to print the groups
def get_group_stage_standings(headers):
    # get the euro 2024 group stages
    teams_url = "https://api.football-data.org/v4/competitions/EC/standings"
    teams_response = requests.get(teams_url, headers=headers)
    teams = teams_response.json()

    # for each group print the teams in order of position and the corresponding score
    for group in teams["standings"]:
        print(f"{group['group']}")
        for team in group["table"]:
            print(
                f"{team['position']}. {team['team']['name']}\t - {team['points']} points"
            )
        print("\n")

# create a function to get the daily calendar of the matches of the euro 2024
def get_daily_calendar(headers):

    # create a function to group the matches by date
    def group_matches_by_date(matches):
        matches_by_date = {}
        for match in matches:
            date = match["utcDate"].split("T")[0]
            if date not in matches_by_date:
                matches_by_date[date] = []
            matches_by_date[date].append(match)
        return matches_by_date

    # create a function to get the flag of the team in PNG format
    def get_flag(team_name):
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
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".svg"
                ) as temp_svg:
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

    # create a function to create the image of the matchday
    def create_matchday_image():
        # load the background image
        image = Image.open("77.png")

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

        # get the current date
        today = datetime.now().strftime("%Y-%m-%d")
        # today = "2024-06-18"

        # format the date
        formatted_date = datetime.strptime(today, "%Y-%m-%d").strftime("%d/%m/%Y")

        draw.text(
            (x + 225, y - 100),
            f"Matchday {formatted_date}",
            fill=text_color,
            font=font_date,
        )

        # loop through the matches of today
        for i, match in enumerate(matches_by_date[today]):

            if i == 2:
                x = width // 2 + 50
                y = height // 2 - 200

            # load the team names
            home_team = match["homeTeam"]["name"]
            away_team = match["awayTeam"]["name"]

            # get the score of the match
            score_home = (
                match["score"]["fullTime"]["home"]
                if match["status"] == "FINISHED"
                else "-"
            )
            score_away = (
                match["score"]["fullTime"]["away"]
                if match["status"] == "FINISHED"
                else "-"
            )

            # get the flags of the teams
            flag_home = get_flag(home_team)
            flag_away = get_flag(away_team)

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

        image.save("calendar.png")
        image.show()

    # get the euro 2024 calendar
    calendar_url = "https://api.football-data.org/v4/competitions/EC/matches"
    calendar_response = requests.get(calendar_url, headers=headers)
    calendar = calendar_response.json()

    # get the matches
    matches = calendar["matches"]
    matches_by_date = group_matches_by_date(matches)

    create_matchday_image()

    # print the matches by date
    for date, matches in matches_by_date.items():

        # print date in the format dd/mm/yyyy
        print(f"{date.split('-')[2]}/{date.split('-')[1]}/{date.split('-')[0]}")
        for match in matches:
            home_team = match["homeTeam"]["name"]
            away_team = match["awayTeam"]["name"]
            group = match["group"]
            stage = match["stage"]
            time = match["utcDate"].split("T")[1].split(":00Z")[0]
            if group:
                if match["status"] == "FINISHED":
                    result = f"{match['score']['fullTime']['home']}-{match['score']['fullTime']['away']}"
                else:
                    result = "TBD"
                print(f"[{group}] {time} - {home_team} vs {away_team:<14}\t {result}")

            if stage not in ["GROUP_STAGE"]:
                if match["status"] == "FINISHED":
                    result = f"{match['score']['fullTime']['home']}-{match['score']['fullTime']['away']}"
                else:
                    result = "TBD"
                print(f"[{stage}] {time} - {home_team} vs {away_team}\t {result}")
        print("\n")


if __name__ == "__main__":
    # set the headers
    headers = {"X-Auth-Token": os.getenv("API_KEY")}

    # get_group_stage_standings(headers=headers)
    get_daily_calendar(headers=headers)
