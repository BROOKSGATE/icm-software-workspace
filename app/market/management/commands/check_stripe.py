from django.core.management.base import BaseCommand, CommandError

from market import payments


class Command(BaseCommand):
    help = "Make one real Stripe call to confirm the test key works."

    def handle(self, *args, **options):
        try:
            livemode, available = payments.check_account()
        except Exception as error:
            raise CommandError(f"Stripe check failed: {error}")
        if livemode:
            raise CommandError("This key is in live mode. Use a test key.")
        self.stdout.write(self.style.SUCCESS(f"Stripe test key works. Available balance: {available or 'none yet'}"))
