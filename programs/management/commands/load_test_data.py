from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import date, timedelta
from programs.models import Child, ProgramType, ProgramInstance, RegistrationForm, FormQuestion, Registration, ProgramBuildout
from communications.models import Contact

User = get_user_model()


class Command(BaseCommand):
    help = 'Load comprehensive test data for the entire system'

    def handle(self, *args, **options):
        self.stdout.write('🚀 Loading comprehensive test data...')
        
        # Step 1: Seed roles and base costs
        self.stdout.write('\n1️⃣ Seeding roles and base costs...')
        call_command('seed_roles')
        
        # Step 2: Create sample buildout
        self.stdout.write('\n2️⃣ Creating sample program buildout...')
        call_command('create_sample_buildout')
        
        # Step 3: Setup comprehensive test data
        self.stdout.write('\n3️⃣ Setting up comprehensive test data...')
        call_command('setup_comprehensive_test_data')
        
        # Step 4: Seed contact submissions
        self.stdout.write('\n4️⃣ Seeding contact form submissions...')
        call_command('seed_contacts')
        
        # Step 5: Create additional test data
        self.stdout.write('\n5️⃣ Creating additional test data...')
        self.create_additional_test_data()
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 All test data loaded successfully!')
        )
        
        self.print_test_data_summary()

    def create_additional_test_data(self):
        """Create additional test data for a more complete system"""
        
        # Create additional program types
        additional_programs = [
            {
                'name': 'Math Explorers',
                'description': 'Fun math activities that build number sense and problem-solving skills. Perfect for grades 2-4.'
            },
            {
                'name': 'Creative Writing Program',
                'description': 'Develop storytelling skills through creative writing exercises. Ideal for grades 4-6.'
            },
            {
                'name': 'Science Lab',
                'description': 'Hands-on science experiments and discovery activities. Great for grades 3-5.'
            }
        ]

        for prog_data in additional_programs:
            program, created = ProgramType.objects.get_or_create(
                name=prog_data['name'],
                defaults=prog_data
            )
            if created:
                self.stdout.write(f'✓ Created program type: {program.name}')
        
        # Create additional program instances
        start_dates = [
            timezone.now() + timedelta(days=14),
            timezone.now() + timedelta(days=21),
            timezone.now() + timedelta(days=28)
        ]
        
        # Get some buildouts to create instances from
        buildouts = ProgramBuildout.objects.all()[:3]  # Get first 3 buildouts
        
        for i, (buildout, start_date) in enumerate(zip(buildouts, start_dates)):
            end_date = start_date + timedelta(days=3)
            
            instance, created = ProgramInstance.objects.get_or_create(
                buildout=buildout,
                title=f'{buildout.program_type.name} - Additional Session',
                start_date=start_date,
                defaults={
                    'end_date': end_date,
                    'location': f'Community Center - Room {101 + i}',
                    'capacity': 10 + (i * 2),
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'✓ Created program instance: {instance.title}')
        
        # Create some sample registrations
        parent_user = User.objects.filter(groups__name='Parent').first()
        if parent_user and parent_user.children.exists():
            child = parent_user.children.first()
            program_instance = ProgramInstance.objects.filter(is_active=True).first()
            
            if program_instance:
                registration, created = Registration.objects.get_or_create(
                    child=child,
                    program_instance=program_instance,
                    defaults={
                        'status': 'approved',
                        'form_responses': {
                            'allergies': 'None',
                            'favorite_subject': 'Science',
                            'heard_from': 'School newsletter',
                            'updates': 'Yes'
                        },
                        'notes': 'Sample registration for testing'
                    }
                )
                if created:
                    self.stdout.write(f'✓ Created sample registration for {child.full_name}')

    def print_test_data_summary(self):
        """Print a summary of all test data created"""
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write('📊 TEST DATA SUMMARY')
        self.stdout.write('='*60)
        
        # User accounts
        parent_count = User.objects.filter(groups__name='Parent').count()
        contractor_count = User.objects.filter(groups__name='Contractor').count()
        admin_count = User.objects.filter(groups__name='Admin').count()
        
        self.stdout.write(f'\n👥 USERS:')
        self.stdout.write(f'  • Parents: {parent_count}')
        self.stdout.write(f'  • Contractors: {contractor_count}')
        self.stdout.write(f'  • Admins: {admin_count}')
        
        # Children
        children_count = Child.objects.count()
        self.stdout.write(f'\n👶 CHILDREN: {children_count}')
        
        # Programs
        program_types_count = ProgramType.objects.count()
        program_instances_count = ProgramInstance.objects.count()
        registrations_count = Registration.objects.count()
        
        self.stdout.write(f'\n📚 PROGRAMS:')
        self.stdout.write(f'  • Program Types: {program_types_count}')
        self.stdout.write(f'  • Program Instances: {program_instances_count}')
        self.stdout.write(f'  • Registrations: {registrations_count}')
        
        # Communications
        contacts_count = Contact.objects.count()
        self.stdout.write(f'\n📞 CONTACTS: {contacts_count}')
        
        # Login information
        self.stdout.write(f'\n🔑 LOGIN CREDENTIALS:')
        self.stdout.write(f'  Parent: DynamicDiscoveries@nellson.net / testpass123')
        self.stdout.write(f'  Contractor: jon@nellson.net')
        
        self.stdout.write(f'\n🌐 TEST URLS:')
        self.stdout.write(f'  • Parent Dashboard: /programs/parent/dashboard/')
        self.stdout.write(f'  • Contractor Dashboard: /programs/contractor/dashboard/')
        self.stdout.write(f'  • Admin Interface: /admin/')
        self.stdout.write(f'  • Contact Management: /communications/contacts/')
        
        self.stdout.write('\n' + '='*60) 