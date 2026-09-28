from game_data_platform.database import engine
from game_data_platform.models import Base


def main():
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")


if __name__ == "__main__":
    main()