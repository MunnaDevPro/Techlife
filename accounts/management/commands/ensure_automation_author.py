import sys
import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Idempotently ensures the automation author account exists as a normal active user "
        "with an unusable password."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            dest='check_mode',
            help='Dry-run mode: checks configuration and user status without modifying database. Exits non-zero if invalid.'
        )

    def handle(self, *args, **options):
        check_mode = options.get('check_mode', False)

        author_username = getattr(settings, 'TECHLIFE_AUTOMATION_AUTHOR_USERNAME', 'techlife_desk')
        if not author_username or not str(author_username).strip():
            msg = "TECHLIFE_AUTOMATION_AUTHOR_USERNAME is not configured."
            if check_mode:
                self.stderr.write(self.style.ERROR(f"CHECK FAILED: {msg}"))
                sys.exit(1)
            raise CommandError(msg)

        author_identifier = str(author_username).strip()
        token = getattr(settings, 'TECHLIFE_AUTOMATION_TOKEN', '')
        token_configured = bool(token and str(token).strip())

        User = get_user_model()
        username_field = getattr(User, 'USERNAME_FIELD', 'username')

        if username_field == 'email':
            user = User.objects.filter(email__iexact=author_identifier).first()
            if not user and '@' not in author_identifier:
                user = User.objects.filter(email__iexact=f"{author_identifier}@techlifebd.com").first()
        else:
            user = User.objects.filter(**{f"{username_field}__iexact": author_identifier}).first()

        if check_mode:
            errors = []
            if not token_configured:
                errors.append("TECHLIFE_AUTOMATION_TOKEN is missing or empty.")
            if not user:
                errors.append(f"Automation author user '{author_identifier}' does not exist.")
            else:
                user_label = getattr(user, 'email', str(user))
                if not user.is_active:
                    errors.append(f"Automation author user '{user_label}' is inactive.")
                if user.is_staff:
                    errors.append(f"Automation author user '{user_label}' has is_staff=True.")
                if user.is_superuser:
                    errors.append(f"Automation author user '{user_label}' has is_superuser=True.")

            if errors:
                for err in errors:
                    self.stderr.write(self.style.ERROR(f"CHECK FAILED: {err}"))
                sys.exit(1)
            else:
                user_label = getattr(user, 'email', str(user))
                self.stdout.write(self.style.SUCCESS(
                    f"CHECK PASSED: Automation author '{user_label}' is valid and configured."
                ))
                return

        # Write Mode: Create or Update User Idempotently
        if not user:
            email_val = author_identifier if "@" in author_identifier else f"{author_identifier}@techlifebd.com"
            temp_pass = secrets.token_urlsafe(32)
            user = User.objects.create_user(
                email=email_val,
                password=temp_pass,
                first_name="TechLife",
                last_name="Desk",
                is_active=True,
                is_staff=False,
                is_superuser=False
            )
            user.set_unusable_password()
            user.save()
            user_label = getattr(user, 'email', str(user))
            self.stdout.write(self.style.SUCCESS(
                f"Successfully created automation author user '{user_label}' (TechLife Desk)."
            ))
        else:
            updated = False
            if not user.is_active:
                user.is_active = True
                updated = True
            if user.is_staff:
                user.is_staff = False
                updated = True
            if user.is_superuser:
                user.is_superuser = False
                updated = True
            if user.has_usable_password():
                user.set_unusable_password()
                updated = True

            if updated:
                user.save()
                user_label = getattr(user, 'email', str(user))
                self.stdout.write(self.style.SUCCESS(
                    f"Updated existing user '{user_label}' to enforce normal active user status."
                ))
            else:
                user_label = getattr(user, 'email', str(user))
                self.stdout.write(self.style.SUCCESS(
                    f"Automation author user '{user_label}' already exists and is properly configured."
                ))
