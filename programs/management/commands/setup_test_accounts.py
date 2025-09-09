from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from programs.models import (
    Child, ProgramType, ProgramInstance, RegistrationForm, FormQuestion,
    ProgramBuildout, Role, BaseCost, Location, BuildoutRoleLine,
    BuildoutBaseCostAssignment, BuildoutLocationAssignment, Registration
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up comprehensive test accounts and data for the programs app'

    def handle(self, *args, **options):
        self.stdout.write('🚀 Setting up comprehensive test data...')

        # Get or create groups
        parent_group, _ = Group.objects.get_or_create(name='Parent')
        contractor_group, _ = Group.objects.get_or_create(name='Contractor')
        admin_group, _ = Group.objects.get_or_create(name='Admin')

        # Create admin user (jon@nellson.net)
        admin_user, created = User.objects.get_or_create(
            email='jon@nellson.net',
            defaults={
                'first_name': 'Jon',
                'last_name': 'Nellson',
                'is_active': True,
            }
        )
        if created:
            admin_user.set_password('adminpass123')
            admin_user.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created admin account: jon@nellson.net')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Admin account already exists: jon@nellson.net')
            )
        admin_user.groups.add(admin_group)

        # Create main contractor (tailoredtales@nellson.net)
        contractor_user, created = User.objects.get_or_create(
            email='tailoredtales@nellson.net',
            defaults={
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'is_active': True,
            }
        )
        if created:
            contractor_user.set_password('contractorpass123')
            contractor_user.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created main contractor: tailoredtales@nellson.net')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Main contractor already exists: tailoredtales@nellson.net')
            )
        contractor_user.groups.add(contractor_group)

        # Create main parent test account (jon.nellson@gmail.com)
        parent_user, created = User.objects.get_or_create(
            email='jon.nellson@gmail.com',
            defaults={
                'first_name': 'Jon',
                'last_name': 'Nellson',
                'is_active': True,
            }
        )
        if created:
            parent_user.set_password('parentpass123')
            parent_user.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created main parent account: jon.nellson@gmail.com')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Main parent account already exists: jon.nellson@gmail.com')
            )
        parent_user.groups.add(parent_group)

        # Create test children for the parent
        children_data = [
            {
                'first_name': 'Emma',
                'last_name': 'Smith',
                'date_of_birth': date(2015, 6, 15),
                'grade_level': '3rd Grade',
                'special_needs': 'None',
                'emergency_contact': 'John Smith',
                'emergency_phone': '(555) 123-4567'
            },
            {
                'first_name': 'Liam',
                'last_name': 'Smith', 
                'date_of_birth': date(2017, 3, 22),
                'grade_level': '1st Grade',
                'special_needs': 'Mild peanut allergy',
                'emergency_contact': 'John Smith',
                'emergency_phone': '(555) 123-4567'
            }
        ]

        for child_data in children_data:
            child, created = Child.objects.get_or_create(
                parent=parent_user,
                first_name=child_data['first_name'],
                last_name=child_data['last_name'],
                defaults=child_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created child: {child.full_name}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Child already exists: {child.full_name}')
                )

        # Create some sample program types and instances
        self.create_sample_programs()

        self.stdout.write(
            self.style.SUCCESS('\n🎉 Test accounts setup complete!')
        )
        self.stdout.write(f'\nParent Login:')
        self.stdout.write(f'  Email: {parent_email}')
        self.stdout.write(f'  Password: testpass123')
        self.stdout.write(f'  URL: /programs/parent/dashboard/')
        
        self.stdout.write(f'\nContractor Login:')
        self.stdout.write(f'  Email: jon.nellson@gmail.com')
        self.stdout.write(f'  URL: /programs/contractor/dashboard/')

    def create_sample_programs(self):
        """Create sample program types and instances for testing"""
        
        # Create STEAM program type
        steam_program, created = ProgramType.objects.get_or_create(
            name='STEAM Program',
            defaults={
                'description': 'Science, Technology, Engineering, Arts, and Math activities for curious minds!',
                'target_grade_levels': '3-5'
            }
        )
        
        if created:
            self.stdout.write('✓ Created STEAM Program program type')

        # Create Literary program type  
        literary_program, created = ProgramType.objects.get_or_create(
            name='Literary Adventures',
            defaults={
                'description': 'Explore the world through reading, writing, and creative storytelling!',
                'target_grade_levels': '1-3'
            }
        )
        
        if created:
            self.stdout.write('✓ Created Literary Adventures program type')

        # Create sample program instances
        start_date = timezone.now() + timedelta(days=7)
        end_date = start_date + timedelta(days=5)
        
        # STEAM Program instance
        steam_instance, created = ProgramInstance.objects.get_or_create(
            program_type=steam_program,
            start_date=start_date,
            defaults={
                'end_date': end_date,
                'location': 'Community Center - Room 101',
                'instructor': User.objects.filter(groups__name='Contractor').first(),
                'capacity': 15,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write('✓ Created STEAM Program program instance')

        # Literary Adventures instance
        literary_start = start_date + timedelta(days=14)
        literary_end = literary_start + timedelta(days=3)
        
        literary_instance, created = ProgramInstance.objects.get_or_create(
            program_type=literary_program,
            start_date=literary_start,
            defaults={
                'end_date': literary_end,
                'location': 'Library - Children\'s Section',
                'instructor': User.objects.filter(groups__name='Contractor').first(),
                'capacity': 12,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write('✓ Created Literary Adventures program instance')

        # Create a sample registration form
        sample_form, created = RegistrationForm.objects.get_or_create(
            title='Student Information Form',
            defaults={
                'description': 'Please provide additional information about your child to help us provide the best experience.',
                'created_by': User.objects.filter(groups__name='Contractor').first(),
                'is_active': True
            }
        )
        
        if created:
            # Add sample questions
            questions_data = [
                {
                    'question_text': 'Does your child have any allergies or medical conditions we should be aware of?',
                    'question_type': 'textarea',
                    'is_required': True,
                    'order': 1
                },
                {
                    'question_text': 'What is your child\'s favorite subject in school?',
                    'question_type': 'text',
                    'is_required': False,
                    'order': 2
                },
                {
                    'question_text': 'How did you hear about this program?',
                    'question_type': 'select',
                    'is_required': False,
                    'options': ['School newsletter', 'Social media', 'Friend recommendation', 'Other'],
                    'order': 3
                },
                {
                    'question_text': 'Would you like to receive updates about future programs?',
                    'question_type': 'radio',
                    'is_required': True,
                    'options': ['Yes', 'No'],
                    'order': 4
                }
            ]
            
            for q_data in questions_data:
                FormQuestion.objects.create(
                    form=sample_form,
                    **q_data
                )
            
            self.stdout.write('✓ Created sample registration form with questions') 