import time
from recommender.training.train_model import train_model


def run_scheduler():

    while True:

        print("Training recommendation model...")

        train_model()

        print("Waiting 60 seconds...")

        time.sleep(60)