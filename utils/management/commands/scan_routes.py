"""
Management command to scan templates for undefined routes.

This command analyzes all HTML templates in the project and identifies
routes that may be undefined, then provides options to implement them.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pathlib import Path
import sys
import os

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.requirements_tracker import scan_templates_for_undefined_routes, parse_template_links


class Command(BaseCommand):
    help = 'Scan templates for undefined routes and provide implementation options'

    def add_arguments(self, parser):
        parser.add_argument(
            '--template',
            type=str,
            help='Scan a specific template file'
        )
        parser.add_argument(
            '--templates-dir',
            type=str,
            default='templates',
            help='Directory containing templates to scan (default: templates)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each template'
        )
        parser.add_argument(
            '--implement',
            action='store_true',
            help='Automatically prompt for implementation of undefined routes'
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        template_path = options.get('template')
        templates_dir = options.get('templates_dir')
        verbose = options.get('verbose')
        implement = options.get('implement')

        if template_path:
            # Scan a specific template
            self.scan_single_template(template_path, verbose)
        else:
            # Scan all templates
            self.scan_all_templates(templates_dir, verbose, implement)

    def scan_single_template(self, template_path, verbose):
        """Scan a single template file."""
        if not Path(template_path).exists():
            raise CommandError(f"Template file not found: {template_path}")

        self.stdout.write(f"Scanning template: {template_path}")
        
        result = parse_template_links(template_path)
        
        if verbose:
            self.stdout.write(f"  Links found: {len(result['links'])}")
            for link in result['links']:
                self.stdout.write(f"    - {link}")
            
            self.stdout.write(f"  HTMX calls found: {len(result['htmx_calls'])}")
            for htmx_call in result['htmx_calls']:
                self.stdout.write(f"    - {htmx_call}")
        
        if result['undefined_routes']:
            self.stdout.write(
                self.style.WARNING(
                    f"  Undefined routes found: {len(result['undefined_routes'])}"
                )
            )
            for route in result['undefined_routes']:
                self.stdout.write(f"    - {route}")
        else:
            self.stdout.write(
                self.style.SUCCESS("  No undefined routes found")
            )

    def scan_all_templates(self, templates_dir, verbose, implement):
        """Scan all templates in the specified directory."""
        if not Path(templates_dir).exists():
            raise CommandError(f"Templates directory not found: {templates_dir}")

        self.stdout.write(f"Scanning templates in: {templates_dir}")
        
        result = scan_templates_for_undefined_routes(templates_dir)
        
        if result['undefined_routes']:
            self.stdout.write(
                self.style.WARNING(
                    f"\nFound {len(result['undefined_routes'])} undefined routes:"
                )
            )
            for route in result['undefined_routes']:
                self.stdout.write(f"  - {route}")
            
            if implement:
                self.prompt_for_implementation(result['undefined_routes'])
        else:
            self.stdout.write(
                self.style.SUCCESS("\nNo undefined routes found in any templates")
            )

    def prompt_for_implementation(self, undefined_routes):
        """Prompt user to implement undefined routes."""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("ROUTE IMPLEMENTATION OPTIONS")
        self.stdout.write("="*50)
        
        for i, route in enumerate(undefined_routes, 1):
            self.stdout.write(f"\n{i}. {route}")
        
        self.stdout.write("\nWould you like to implement any of these routes?")
        self.stdout.write("Enter route numbers separated by commas (e.g., 1,3,5)")
        self.stdout.write("Or 'all' to implement all routes")
        self.stdout.write("Or 'none' to skip implementation")
        
        try:
            choice = input("\nYour choice: ").strip().lower()
            
            if choice == 'all':
                routes_to_implement = undefined_routes
            elif choice == 'none':
                self.stdout.write("Skipping route implementation")
                return
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in choice.split(',')]
                    routes_to_implement = [undefined_routes[i] for i in indices if 0 <= i < len(undefined_routes)]
                except (ValueError, IndexError):
                    self.stdout.write(
                        self.style.ERROR("Invalid choice. Please enter valid route numbers.")
                    )
                    return
        except KeyboardInterrupt:
            self.stdout.write("\nOperation cancelled by user")
            return
        
        if routes_to_implement:
            self.stdout.write(f"\nImplementing {len(routes_to_implement)} routes:")
            for route in routes_to_implement:
                self.stdout.write(f"  - {route}")
                self.implement_route(route)

    def implement_route(self, route):
        """Implement a single route."""
        self.stdout.write(f"\nImplementing route: {route}")
        
        # Parse the route to determine what needs to be created
        if ':' in route:
            namespace, view_name = route.split(':', 1)
        else:
            namespace = None
            view_name = route
        
        self.stdout.write(f"  Namespace: {namespace or 'None'}")
        self.stdout.write(f"  View name: {view_name}")
        
        # Provide implementation guidance
        self.stdout.write("\n  Implementation steps:")
        self.stdout.write("  1. Create view function in appropriate app")
        self.stdout.write("  2. Add URL pattern to app's urls.py")
        self.stdout.write("  3. Include app URLs in main urls.py (if needed)")
        self.stdout.write("  4. Create template file")
        self.stdout.write("  5. Test the route")
        
        # Suggest file locations
        if namespace:
            app_name = namespace
        else:
            app_name = "core"  # Default to core app
        
        self.stdout.write(f"\n  Suggested file locations:")
        self.stdout.write(f"    - View: {app_name}/views.py")
        self.stdout.write(f"    - URL: {app_name}/urls.py")
        self.stdout.write(f"    - Template: templates/{app_name}/{view_name}.html")
        
        self.stdout.write(
            self.style.SUCCESS(f"\n  Route '{route}' implementation guidance provided")
        ) 