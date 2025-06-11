from django.core.management.base import BaseCommand
from django.conf import settings
import importlib


class Command(BaseCommand):
    help = 'Register Agno agents with the platform'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app-module',
            type=str,
            help='Module path to your Django Ninja app with Agno integration',
            default='myapp.api'
        )

    def handle(self, *args, **options):
        try:
            module_path = options['app_module']
            module = importlib.import_module(module_path)

            # Assuming the DjangoNinjaApp instance is named 'agno_app'
            agno_app = getattr(module, 'agno_app', None)

            if not agno_app:
                self.stdout.write(
                    self.style.ERROR(
                        f'No agno_app found in {module_path}. '
                        'Make sure your DjangoNinjaApp instance is named "agno_app"'
                    )
                )
                return

            # Re-register all components
            agno_app._register_on_platform()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully registered {len(agno_app.agents)} agents, '
                    f'{len(agno_app.teams)} teams, and '
                    f'{len(agno_app.workflows)} workflows'
                )
            )

        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'Could not import {module_path}: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error registering agents: {e}')
            )
