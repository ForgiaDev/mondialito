import requests
import os
from dotenv import load_dotenv

### get the api key from the environment
load_dotenv()


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
            # index the position, the team name and the points
            print(f"{team['position']}. {team['team']['name']}\t - {team['points']} points")
        print("\n")


if __name__ == "__main__":
    # set the headers
    headers = {"X-Auth-Token": os.getenv("API_KEY")}

    get_group_stage_standings(headers=headers)
