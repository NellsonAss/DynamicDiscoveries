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
    help = 'Set up comprehensive test data for the entire system'

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
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created main parent account: jon.nellson@gmail.com')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Main parent account already exists: jon.nellson@gmail.com')
            )
        parent_user.groups.add(parent_group)

        # Create additional test users
        self.create_additional_users(parent_group, contractor_group, admin_group)
        
        # Create test children for the main parent
        self.create_test_children(parent_user)

        # Create comprehensive test data
        self.create_locations()
        self.create_program_types()
        self.create_program_buildouts(contractor_user, admin_user)
        self.create_program_instances()
        self.create_registrations()

        self.stdout.write(
            self.style.SUCCESS('\n🎉 Comprehensive test data setup complete!')
        )
        self.print_login_credentials()

    def create_additional_users(self, parent_group, contractor_group, admin_group):
        """Create additional test users for comprehensive testing"""
        
        # Additional parents
        additional_parents = [
            {
                'email': 'maria.rodriguez@gmail.com',
                'first_name': 'Maria',
                'last_name': 'Rodriguez'
            },
            {
                'email': 'david.chen@gmail.com',
                'first_name': 'David',
                'last_name': 'Chen'
            },
            {
                'email': 'jennifer.wilson@gmail.com',
                'first_name': 'Jennifer',
                'last_name': 'Wilson'
            }
        ]

        for parent_data in additional_parents:
            parent_user, created = User.objects.get_or_create(
                email=parent_data['email'],
                defaults={
                    'first_name': parent_data['first_name'],
                    'last_name': parent_data['last_name'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created parent: {parent_data["email"]}')
                )
            parent_user.groups.add(parent_group)

        # Additional contractors
        additional_contractors = [
            {
                'email': 'mike.facilitator@gmail.com',
                'first_name': 'Mike',
                'last_name': 'Thompson'
            },
            {
                'email': 'lisa.educator@gmail.com',
                'first_name': 'Lisa',
                'last_name': 'Anderson'
            },
            {
                'email': 'alex.curriculum@gmail.com',
                'first_name': 'Alex',
                'last_name': 'Martinez'
            }
        ]

        for contractor_data in additional_contractors:
            contractor_user, created = User.objects.get_or_create(
                email=contractor_data['email'],
                defaults={
                    'first_name': contractor_data['first_name'],
                    'last_name': contractor_data['last_name'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created contractor: {contractor_data["email"]}')
                )
            contractor_user.groups.add(contractor_group)

    def create_test_children(self, parent_user):
        """Create test children for the main parent"""
        children_data = [
            {
                'first_name': 'Emma',
                'last_name': 'Nellson',
                'date_of_birth': date(2015, 6, 15),
                'grade_level': '3rd Grade',
                'special_needs': 'None',
                'emergency_contact': 'Jon Nellson',
                'emergency_phone': '(555) 123-4567'
            },
            {
                'first_name': 'Liam',
                'last_name': 'Nellson', 
                'date_of_birth': date(2017, 3, 22),
                'grade_level': '1st Grade',
                'special_needs': 'Mild peanut allergy',
                'emergency_contact': 'Jon Nellson',
                'emergency_phone': '(555) 123-4567'
            },
            {
                'first_name': 'Sophia',
                'last_name': 'Nellson',
                'date_of_birth': date(2019, 8, 10),
                'grade_level': 'Pre-K',
                'special_needs': 'None',
                'emergency_contact': 'Jon Nellson',
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

    def create_locations(self):
        """Create diverse test locations with proper cost structures"""
        locations_data = [
            {
                'name': 'Downtown Community Center',
                'address': '123 Main St, Downtown, CA 90210',
                'description': 'Large community center with multiple rooms, parking, and modern facilities',
                'default_rate': Decimal('50.00'),
                'default_frequency': 'PER_PROGRAM',
                'max_capacity': 30,
                'features': 'Projector, whiteboard, parking, kitchen access',
                'contact_name': 'Jane Smith',
                'contact_phone': '(555) 100-2000',
                'contact_email': 'jane@downtowncc.org'
            },
            {
                'name': 'Riverside Library - Children\'s Section',
                'address': '456 Oak Ave, Riverside, CA 90211',
                'description': 'Cozy library space perfect for reading and creative activities',
                'default_rate': Decimal('25.00'),
                'default_frequency': 'PER_PROGRAM',
                'max_capacity': 15,
                'features': 'Books, quiet space, computer access',
                'contact_name': 'Bob Johnson',
                'contact_phone': '(555) 200-3000',
                'contact_email': 'bob@riversidelib.org'
            },
            {
                'name': 'Tech Hub Innovation Center',
                'address': '789 Innovation Dr, Tech City, CA 90212',
                'description': 'Modern tech facility with computers, robotics equipment, and maker space',
                'default_rate': Decimal('75.00'),
                'default_frequency': 'PER_PROGRAM',
                'max_capacity': 20,
                'features': 'Computers, 3D printers, robotics kits, high-speed internet',
                'contact_name': 'Sarah Tech',
                'contact_phone': '(555) 300-4000',
                'contact_email': 'sarah@techhub.org'
            },
            {
                'name': 'Art Studio Collective',
                'address': '321 Creative Blvd, Arts District, CA 90213',
                'description': 'Artist studio space with supplies and creative atmosphere',
                'default_rate': Decimal('40.00'),
                'default_frequency': 'PER_PROGRAM',
                'max_capacity': 12,
                'features': 'Art supplies, easels, kiln, outdoor patio',
                'contact_name': 'Maya Artist',
                'contact_phone': '(555) 400-5000',
                'contact_email': 'maya@artstudio.org'
            }
        ]

        for location_data in locations_data:
            location, created = Location.objects.get_or_create(
                name=location_data['name'],
                defaults=location_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created location: {location.name}')
                )

    def create_program_types(self):
        """Create comprehensive program types with realistic descriptions"""
        program_types_data = [
            {
                'name': 'STEAM Explorers',
                'description': 'Hands-on Science, Technology, Engineering, Arts, and Math activities that spark curiosity and creativity in young minds. Perfect for grades K-5.'
            },
            {
                'name': 'Literary Adventures',
                'description': 'Explore the magical world of reading, writing, and storytelling through interactive activities and creative projects. Ideal for grades 1-3.'
            },
            {
                'name': 'Math Masters',
                'description': 'Fun and engaging math activities that build number sense, problem-solving skills, and mathematical confidence. Great for grades 2-4.'
            },
            {
                'name': 'Creative Coding',
                'description': 'Introduction to programming concepts through visual coding, games, and interactive projects. Designed for grades 3-6.'
            },
            {
                'name': 'Art & Craft Studio',
                'description': 'Creative expression through various art mediums including painting, sculpture, and mixed media projects. Perfect for grades K-4.'
            }
        ]

        for program_data in program_types_data:
            program_type, created = ProgramType.objects.get_or_create(
                name=program_data['name'],
                defaults=program_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created program type: {program_type.name}')
                )

    def create_program_buildouts(self, contractor_user, admin_user):
        """Create detailed program buildouts with roles, costs, and locations"""
        # Get roles and base costs
        facilitator_role = Role.objects.get(title='Facilitator')
        curriculum_role = Role.objects.get(title='Curriculum Designer')
        admin_role = Role.objects.get(title='Admin Support')
        
        materials_cost = BaseCost.objects.get(name='Materials & Supplies')
        location_cost = BaseCost.objects.get(name='Location')
        platform_cost = BaseCost.objects.get(name='Platform & Insurance')
        
        # Get locations
        downtown_cc = Location.objects.get(name='Downtown Community Center')
        tech_hub = Location.objects.get(name='Tech Hub Innovation Center')
        art_studio = Location.objects.get(name='Art Studio Collective')
        
        # Create buildouts for each program type
        buildouts_data = [
            {
                'program_type': 'STEAM Explorers',
                'title': 'Standard STEAM Buildout',
                'num_facilitators': 2,
                'num_new_facilitators': 1,
                'students_per_program': 12,
                'sessions_per_program': 8,
                'rate_per_student': Decimal('120.00'),
                'is_new_program': True,
                'roles': [
                    {'role': facilitator_role, 'contractor': contractor_user, 'pay_type': 'HOURLY', 'pay_value': Decimal('35.00'), 'frequency_unit': 'PER_SESSION', 'frequency_count': 1, 'hours_per_frequency': Decimal('2.0')},
                    {'role': curriculum_role, 'contractor': contractor_user, 'pay_type': 'PER_PROGRAM', 'pay_value': Decimal('200.00'), 'frequency_unit': 'PER_PROGRAM', 'frequency_count': 1, 'hours_per_frequency': Decimal('8.0')},
                ],
                'base_costs': [
                    {'base_cost': materials_cost, 'rate': Decimal('20.00'), 'frequency': 'PER_PROGRAM'},
                    {'base_cost': platform_cost, 'rate': Decimal('15.00'), 'frequency': 'PER_PROGRAM'},
                ],
                'locations': [
                    {'location': downtown_cc, 'rate': Decimal('50.00'), 'frequency': 'PER_PROGRAM'},
                    {'location': tech_hub, 'rate': Decimal('75.00'), 'frequency': 'PER_PROGRAM'},
                ]
            },
            {
                'program_type': 'Literary Adventures',
                'title': 'Reading & Writing Buildout',
                'num_facilitators': 1,
                'num_new_facilitators': 0,
                'students_per_program': 10,
                'sessions_per_program': 6,
                'rate_per_student': Decimal('100.00'),
                'is_new_program': False,
                'roles': [
                    {'role': facilitator_role, 'contractor': contractor_user, 'pay_type': 'HOURLY', 'pay_value': Decimal('30.00'), 'frequency_unit': 'PER_SESSION', 'frequency_count': 1, 'hours_per_frequency': Decimal('1.5')},
                ],
                'base_costs': [
                    {'base_cost': materials_cost, 'rate': Decimal('15.00'), 'frequency': 'PER_PROGRAM'},
                    {'base_cost': platform_cost, 'rate': Decimal('10.00'), 'frequency': 'PER_PROGRAM'},
                ],
                'locations': [
                    {'location': downtown_cc, 'rate': Decimal('25.00'), 'frequency': 'PER_PROGRAM'},
                ]
            },
            {
                'program_type': 'Creative Coding',
                'title': 'Tech Innovation Buildout',
                'num_facilitators': 2,
                'num_new_facilitators': 1,
                'students_per_program': 8,
                'sessions_per_program': 12,
                'rate_per_student': Decimal('150.00'),
                'is_new_program': True,
                'roles': [
                    {'role': facilitator_role, 'contractor': contractor_user, 'pay_type': 'HOURLY', 'pay_value': Decimal('40.00'), 'frequency_unit': 'PER_SESSION', 'frequency_count': 1, 'hours_per_frequency': Decimal('2.5')},
                    {'role': curriculum_role, 'contractor': contractor_user, 'pay_type': 'PER_PROGRAM', 'pay_value': Decimal('300.00'), 'frequency_unit': 'PER_PROGRAM', 'frequency_count': 1, 'hours_per_frequency': Decimal('12.0')},
                ],
                'base_costs': [
                    {'base_cost': materials_cost, 'rate': Decimal('30.00'), 'frequency': 'PER_PROGRAM'},
                    {'base_cost': platform_cost, 'rate': Decimal('20.00'), 'frequency': 'PER_PROGRAM'},
                ],
                'locations': [
                    {'location': tech_hub, 'rate': Decimal('75.00'), 'frequency': 'PER_PROGRAM'},
                ]
            }
        ]

        for buildout_data in buildouts_data:
            program_type = ProgramType.objects.get(name=buildout_data['program_type'])
            
            buildout, created = ProgramBuildout.objects.get_or_create(
                program_type=program_type,
                title=buildout_data['title'],
                defaults={
                    'num_facilitators': buildout_data['num_facilitators'],
                    'num_new_facilitators': buildout_data['num_new_facilitators'],
                    'students_per_program': buildout_data['students_per_program'],
                    'sessions_per_program': buildout_data['sessions_per_program'],
                    'rate_per_student': buildout_data['rate_per_student'],
                    'is_new_program': buildout_data['is_new_program'],
                    'status': 'ready'
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created buildout: {buildout.title}')
                )
                
                # Add role assignments
                for role_data in buildout_data['roles']:
                    BuildoutRoleLine.objects.create(
                        buildout=buildout,
                        role=role_data['role'],
                        contractor=role_data['contractor'],
                        pay_type=role_data['pay_type'],
                        pay_value=role_data['pay_value'],
                        frequency_unit=role_data['frequency_unit'],
                        frequency_count=role_data['frequency_count'],
                        hours_per_frequency=role_data['hours_per_frequency']
                    )
                
                # Add base cost assignments
                for cost_data in buildout_data['base_costs']:
                    BuildoutBaseCostAssignment.objects.create(
                        buildout=buildout,
                        base_cost=cost_data['base_cost'],
                        rate=cost_data['rate'],
                        frequency=cost_data['frequency']
                    )
                
                # Add location assignments
                for location_data in buildout_data['locations']:
                    BuildoutLocationAssignment.objects.create(
                        buildout=buildout,
                        location=location_data['location'],
                        rate=location_data['rate'],
                        frequency=location_data['frequency']
                    )

    def create_program_instances(self):
        """Create program instances with proper scheduling and capacity"""
        # Get buildouts - use filter().first() to handle duplicates
        steam_buildout = ProgramBuildout.objects.filter(title='Standard STEAM Buildout').first()
        literary_buildout = ProgramBuildout.objects.filter(title='Reading & Writing Buildout').first()
        coding_buildout = ProgramBuildout.objects.filter(title='Tech Innovation Buildout').first()
        
        # Get contractor
        contractor = User.objects.get(email='tailoredtales@nellson.net')
        
        # Create instances
        instances_data = [
            {
                'buildout': steam_buildout,
                'title': 'STEAM Explorers - Spring Session',
                'start_date': timezone.now() + timedelta(days=7),
                'end_date': timezone.now() + timedelta(days=14),
                'location': 'Downtown Community Center - Room 101',
                'capacity': 12,
                'is_active': True
            },
            {
                'buildout': literary_buildout,
                'title': 'Literary Adventures - March Session',
                'start_date': timezone.now() + timedelta(days=14),
                'end_date': timezone.now() + timedelta(days=20),
                'location': 'Riverside Library - Children\'s Section',
                'capacity': 10,
                'is_active': True
            },
            {
                'buildout': coding_buildout,
                'title': 'Creative Coding - Summer Intensive',
                'start_date': timezone.now() + timedelta(days=30),
                'end_date': timezone.now() + timedelta(days=45),
                'location': 'Tech Hub Innovation Center - Lab A',
                'capacity': 8,
                'is_active': True
            }
        ]

        for instance_data in instances_data:
            instance, created = ProgramInstance.objects.get_or_create(
                buildout=instance_data['buildout'],
                title=instance_data['title'],
                defaults=instance_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created program instance: {instance.title}')
                )

    def create_registrations(self):
        """Create realistic parent-child registrations across programs"""
        # Get parent and children
        parent = User.objects.get(email='jon.nellson@gmail.com')
        children = parent.children.all()
        
        # Get program instances
        steam_instance = ProgramInstance.objects.filter(title='STEAM Explorers - Spring Session').first()
        literary_instance = ProgramInstance.objects.filter(title='Literary Adventures - March Session').first()
        
        # Create registrations
        registrations_data = [
            {
                'child': children[0],  # Emma
                'program_instance': steam_instance,
                'status': 'approved',
                'form_responses': {
                    'allergies': 'None',
                    'favorite_subject': 'Science',
                    'heard_from': 'School newsletter',
                    'updates': 'Yes'
                },
                'notes': 'Emma is very excited about the STEAM program!'
            },
            {
                'child': children[1],  # Liam
                'program_instance': literary_instance,
                'status': 'approved',
                'form_responses': {
                    'allergies': 'Mild peanut allergy',
                    'favorite_subject': 'Reading',
                    'heard_from': 'Friend recommendation',
                    'updates': 'Yes'
                },
                'notes': 'Liam loves books and storytelling'
            }
        ]

        for reg_data in registrations_data:
            registration, created = Registration.objects.get_or_create(
                child=reg_data['child'],
                program_instance=reg_data['program_instance'],
                defaults=reg_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created registration: {registration}')
                )

    def print_login_credentials(self):
        """Print comprehensive login credentials and test data summary"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('🔑 LOGIN INFORMATION')
        self.stdout.write('='*60)
        
        self.stdout.write(f'\n📧 LOGIN PROCESS:')
        self.stdout.write(f'  This system uses email verification codes for login.')
        self.stdout.write(f'  Enter any test email below and check your email for the verification code.')
        
        self.stdout.write(f'\n👨‍💼 ADMIN ACCOUNTS:')
        self.stdout.write(f'  • jon@nellson.net (Admin)')
        
        self.stdout.write(f'\n👷‍♀️ CONTRACTOR ACCOUNTS:')
        self.stdout.write(f'  • tailoredtales@nellson.net (Main Facilitator)')
        self.stdout.write(f'  • mike.facilitator@gmail.com')
        self.stdout.write(f'  • lisa.educator@gmail.com')
        self.stdout.write(f'  • alex.curriculum@gmail.com')
        
        self.stdout.write(f'\n👨‍👩‍👧‍👦 PARENT ACCOUNTS:')
        self.stdout.write(f'  • jon.nellson@gmail.com (Main Test Account)')
        self.stdout.write(f'  • maria.rodriguez@gmail.com')
        self.stdout.write(f'  • david.chen@gmail.com')
        self.stdout.write(f'  • jennifer.wilson@gmail.com')
        
        self.stdout.write(f'\n🌐 TEST URLS:')
        self.stdout.write(f'  • Login Page: /accounts/login/')
        self.stdout.write(f'  • Admin Interface: /admin/')
        self.stdout.write(f'  • Contractor Dashboard: /programs/contractor/dashboard/')
        self.stdout.write(f'  • Parent Dashboard: /programs/parent/dashboard/')
        
        # Print data summary
        self.print_data_summary()

    def print_data_summary(self):
        """Print summary of created test data"""
        self.stdout.write(f'\n📊 TEST DATA SUMMARY:')
        self.stdout.write(f'  • Program Types: {ProgramType.objects.count()}')
        self.stdout.write(f'  • Program Buildouts: {ProgramBuildout.objects.count()}')
        self.stdout.write(f'  • Program Instances: {ProgramInstance.objects.count()}')
        self.stdout.write(f'  • Locations: {Location.objects.count()}')
        self.stdout.write(f'  • Children: {Child.objects.count()}')
        self.stdout.write(f'  • Registrations: {Registration.objects.count()}')
        self.stdout.write(f'  • Users: {User.objects.count()}')
        
        self.stdout.write('\n' + '='*60)
