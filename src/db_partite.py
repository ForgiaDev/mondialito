from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()
engine = create_engine("sqlite:///resources/euro2024.db")

### DATABASE ###


class Matches(Base):
    __tablename__ = "matches"
    match_id = Column(Integer, primary_key=True)
    team1 = Column(String)
    team2 = Column(String)
    start_time = Column(DateTime)
    result = Column(String)


class Polls(Base):
    __tablename__ = "polls"
    poll_id = Column(String, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.match_id"))
    closed = Column(Boolean)
    match = relationship("Matches")


class Players(Base):
    __tablename__ = "players"
    player_id = Column(String, primary_key=True)
    name = Column(String)
    score = Column(Integer)


class Bets(Base):
    __tablename__ = "bets"
    user_id = Column(String, ForeignKey("players.player_id"), primary_key=True)
    poll_id = Column(String, ForeignKey("polls.poll_id"), primary_key=True)
    bet_value = Column(String)
    player = relationship("Players")
    poll = relationship("Polls")

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

### FUNCTIONS ###


# add a new match
def add_match(team1, team2, start_time):
    # calculate the next match_id
    match_id = session.query(Matches).count() + 1
    match = Matches(
        match_id=match_id,
        team1=team1,
        team2=team2,
        start_time=start_time,
        result="Pending",
    )
    session.add(match)
    session.commit()
    return match.match_id


# add a new poll
def add_poll(poll_id, match_id):
    poll = Polls(poll_id=poll_id, match_id=match_id, closed=False)
    session.add(poll)
    session.commit()


# add a new player
def add_player(user_id, name):
    player = Players(player_id=user_id, name=name, score=0)
    session.add(player)
    session.commit()


# add points to a player. Check if the player exists update the score, otherwise create a new player
def add_points(user_id, points):
    player = session.query(Players).filter(Players.player_id == user_id).first()
    if player is None:
        add_player(user_id, "")
    else:
        player.score += points
        session.commit()


# add a new bet
def add_bet(user_id, poll_id, bet_value):
    bet = Bets(user_id=user_id, poll_id=poll_id, bet_value=bet_value)
    session.add(bet)
    session.commit()


# get the match from match_id
def get_match(match_id):
    match = session.query(Matches).filter(Matches.match_id == match_id).first()
    return match


# get the poll_id from match_id
def get_poll_id(match_id):
    poll = session.query(Polls).filter(Polls.match_id == match_id).first()
    return poll.poll_id


# get all the daily matches
def get_daily_matches(start_date):
    matches = session.query(Matches).filter(Matches.start_time.like(f"{start_date}%")).all()
    return matches


# close a poll
def close_poll(poll_id):
    poll = session.query(Polls).filter(Polls.poll_id == poll_id).first()
    poll.closed = True
    session.commit()


# update the result of a match
def update_result(match_id, result):
    match = session.query(Matches).filter(Matches.match_id == match_id).first()
    match.result = result
    session.commit()


# get the bets of a poll
def get_bets(poll_id):
    bets = session.query(Bets).filter(Bets.poll_id == poll_id).all()
    return bets


# get player
def get_player(user_id):
    player = session.query(Players).filter(Players.player_id == user_id).first()
    return player


# get the leaderboard
def get_leaderboard():
    leaderboard = session.query(Players).order_by(Players.score.desc()).all()
    return leaderboard


# delete a match
def delete_match(match_id):
    match = session.query(Matches).filter(Matches.match_id == match_id).first()
    session.delete(match)
    session.commit()