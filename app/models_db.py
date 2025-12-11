from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, index=True)
    sport = Column(String(50), index=True)
    league = Column(String(100))
    home_team = Column(String(255))
    away_team = Column(String(255))
    event_datetime = Column(DateTime, index=True)
    completed = Column(Boolean, default=False)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    winner = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    markets = relationship("Market", back_populates="event")
    outcomes = relationship("Outcome", back_populates="event")

class Market(Base):
    __tablename__ = "markets"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), index=True)
    selection_name = Column(String(255))
    market_type = Column(String(50))
    bookmaker = Column(String(100))
    decimal_odds = Column(Float)
    captured_at = Column(DateTime, default=datetime.utcnow)
    
    event = relationship("Event", back_populates="markets")
    predictions = relationship("ModelPrediction", back_populates="market")

class Outcome(Base):
    __tablename__ = "outcomes"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), index=True)
    selection_name = Column(String(255))
    result = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    event = relationship("Event", back_populates="outcomes")

class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), index=True)
    model_name = Column(String(100))
    predicted_probability = Column(Float)
    ev = Column(Float)
    is_high_confidence = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    market = relationship("Market", back_populates="predictions")

class HistoricalData(Base):
    __tablename__ = "historical_data"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), index=True)
    team_name = Column(String(255), index=True)
    opponent = Column(String(255))
    is_home = Column(Boolean)
    team_score = Column(Integer)
    opponent_score = Column(Integer)
    won = Column(Boolean)
    event_date = Column(DateTime, index=True)
    season = Column(String(20))
    
    win_rate_last_10 = Column(Float, nullable=True)
    avg_points_for = Column(Float, nullable=True)
    avg_points_against = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TeamStats(Base):
    __tablename__ = "team_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), index=True)
    team_name = Column(String(255), index=True)
    season = Column(String(20), index=True)
    
    total_wins = Column(Integer, default=0)
    total_losses = Column(Integer, default=0)
    win_rate = Column(Float, default=0.5)
    home_wins = Column(Integer, default=0)
    home_losses = Column(Integer, default=0)
    away_wins = Column(Integer, default=0)
    away_losses = Column(Integer, default=0)
    
    avg_points_for = Column(Float, default=0)
    avg_points_against = Column(Float, default=0)
    point_differential = Column(Float, default=0)
    
    last_5_wins = Column(Integer, default=0)
    last_10_wins = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    
    ranking = Column(Integer, nullable=True)
    strength_rating = Column(Float, default=50.0)
    consistency_score = Column(Float, default=0.5)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RivalryTag(Base):
    __tablename__ = "rivalry_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), index=True)
    team1 = Column(String(255), index=True)
    team2 = Column(String(255), index=True)
    rivalry_name = Column(String(255))
    rivalry_intensity = Column(Float, default=0.5)
    
class DivisionalMatchup(Base):
    __tablename__ = "divisional_matchups"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(50), index=True)
    division = Column(String(100))
    team_name = Column(String(255), index=True)
