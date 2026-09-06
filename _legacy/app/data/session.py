from sqlalchemy.orm import Session
from sqlmodel import create_engine

# Database setup
engine = create_engine("sqlite:///./franchise_football.db", echo=True)

def get_db():
    with Session(engine) as session:
        yield session

