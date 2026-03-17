from django.core.management.base import BaseCommand
import time
from recommender.training.train_model import train_model


class Command(BaseCommand):

    help = "Train recommendation model every minute"

    def handle(self, *args, **kwargs):

        while True:

            self.stdout.write("Training recommender...")

            train_model()

            time.sleep(60)