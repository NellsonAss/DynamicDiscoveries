from django.core.management.base import BaseCommand
from programs.models import Role, Responsibility, ResponsibilityFrequency
from decimal import Decimal


class Command(BaseCommand):
    help = 'Setup Excel-like role structure with responsibilities and hours from TT After School Workshops'

    def handle(self, *args, **options):
        # Excel-like role structure based on the TT After School Workshops spreadsheet
        EXCEL_ROLES = [
            {
                "title": "Facilitators",
                "description": "Primary workshop facilitators and session leaders",
                "responsibilities": [
                    {
                        "name": "Session facilitation",
                        "description": "Leading workshop sessions and activities",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("4.00")
                    },
                    {
                        "name": "Setup and Teardown",
                        "description": "Setting up and cleaning up workshop materials and space",
                        "frequency": "PER_SESSION",
                        "hours": Decimal("1.00")
                    },
                    {
                        "name": "Initial Assessment",
                        "description": "Conducting baseline assessments to understand student needs",
                        "frequency": "PER_SESSION",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Resource Allocation",
                        "description": "Managing and distributing workshop materials and resources",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Engagement Strategies",
                        "description": "Implementing strategies to keep students engaged and motivated",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Collaborative Planning",
                        "description": "Planning workshop activities and curriculum delivery",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Goal Setting",
                        "description": "Setting and tracking student learning goals",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Customization",
                        "description": "Adapting activities to meet individual student needs",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Parental Guidance",
                        "description": "Providing guidance and support to parents",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Open Communication",
                        "description": "Maintaining open communication with students and parents",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Feedback Implementation",
                        "description": "Implementing feedback to improve workshop delivery",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Feedback Sessions",
                        "description": "Conducting feedback sessions with students and parents",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Collaborative Review",
                        "description": "Reviewing workshop outcomes and planning improvements",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Actionable Responses",
                        "description": "Providing actionable responses to student and parent feedback",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Data Management",
                        "description": "Entering and updating student and workshop data",
                        "frequency": "PER_SESSION",
                        "hours": Decimal("0.125")
                    },
                    {
                        "name": "Comprehensive Reporting",
                        "description": "Creating comprehensive reports on workshop outcomes",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Progress Reports",
                        "description": "Generating and sharing student progress reports",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Recommendations for Support",
                        "description": "Providing recommendations for additional student support",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    }
                ]
            },
            {
                "title": "Facilitator Support",
                "description": "Support staff assisting facilitators with logistics and behavior management",
                "responsibilities": [
                    {
                        "name": "Session facilitation",
                        "description": "Assisting with workshop sessions and activities",
                        "frequency": "PER_SESSION",
                        "hours": Decimal("1.00")
                    },
                    {
                        "name": "Setup and Teardown",
                        "description": "Assisting with workshop setup and cleanup",
                        "frequency": "PER_SESSION",
                        "hours": Decimal("0.50")
                    }
                ]
            },
            {
                "title": "Operations Support",
                "description": "Business operations and administrative support",
                "responsibilities": [
                    {
                        "name": "Team Leadership",
                        "description": "Lead and motivate the operations team to achieve business goals",
                        "frequency": "PER_NEW_FACILITATOR",
                        "hours": Decimal("1.00")
                    },
                    {
                        "name": "Workforce Planning",
                        "description": "Determine staffing needs and schedule staff",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Conflict Resolution",
                        "description": "Address and resolve workplace conflicts",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.25")
                    },
                    {
                        "name": "Resource Allocation",
                        "description": "Allocate resources for educational programs and technology",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("1.00")
                    },
                    {
                        "name": "Feedback and Improvement",
                        "description": "Collect and analyze customer feedback for improvement",
                        "frequency": "PER_NEW_FACILITATOR",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Supply Chain Management",
                        "description": "Oversee procurement of materials and inventory management",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.25")
                    },
                    {
                        "name": "Cost Management",
                        "description": "Monitor and control operational costs",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.25")
                    },
                    {
                        "name": "Financial Analysis and Reporting",
                        "description": "Analyze financial data and perform cost analysis",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.25")
                    },
                    {
                        "name": "Data Management",
                        "description": "Oversee management of business data",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Analytics and Reporting",
                        "description": "Use analytics tools to track performance and generate reports",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("1.00")
                    },
                    {
                        "name": "Budgeting and Forecasting",
                        "description": "Develop and manage the business budget",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("1.00")
                    },
                    {
                        "name": "Quality Control",
                        "description": "Implement quality standards and conduct inspections",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("1.00")
                    },
                    {
                        "name": "Online Community Management",
                        "description": "Engage with customers and followers on social media",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("2.00")
                    },
                    {
                        "name": "Social Media Strategy",
                        "description": "Develop and execute social media strategy",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    },
                    {
                        "name": "Content Creation and Management",
                        "description": "Create and oversee engaging content",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("1.00")
                    }
                ]
            },
            {
                "title": "Service/Support",
                "description": "Customer service and technical support",
                "responsibilities": [
                    {
                        "name": "Customer Concerns",
                        "description": "Ensure timely and effective resolution of customer concerns",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.25")
                    },
                    {
                        "name": "Student Set-up",
                        "description": "Assist with the setup of new clients",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.25")
                    },
                    {
                        "name": "Tech Issues",
                        "description": "Provide first level of technical support to clients",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.25")
                    },
                    {
                        "name": "Program Qs/Issues",
                        "description": "Answer questions about programs and resolve issues",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("1.00")
                    }
                ]
            },
            {
                "title": "Business Consultant",
                "description": "Business strategy, compliance, and financial consulting",
                "responsibilities": [
                    {
                        "name": "Compliance and Risk Management",
                        "description": "Ensure business complies with all legal requirements and regulations",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("2.00")
                    },
                    {
                        "name": "New Hire Training",
                        "description": "Training for new hires in the first two weeks",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("5.00")
                    },
                    {
                        "name": "Business Registration",
                        "description": "Handle business registration and licensing requirements",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.25")
                    },
                    {
                        "name": "Tech Issues",
                        "description": "Provide second layer of technical support to clients",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("2.00")
                    },
                    {
                        "name": "Accounting and Taxes",
                        "description": "Annual accounting and tax work",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("1.00")
                    }
                ]
            },
            {
                "title": "Educational Consultant",
                "description": "Educational research, advocacy, and curriculum support",
                "responsibilities": [
                    {
                        "name": "Educational Research",
                        "description": "Conduct research on educational practices, trends, and best practices",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("3.00")
                    },
                    {
                        "name": "Advocacy",
                        "description": "Advocate for educational policies and practices that support learning",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("2.00")
                    },
                    {
                        "name": "Integration of Technology",
                        "description": "Recommend educational technologies to enhance learning",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("2.00")
                    },
                    {
                        "name": "Mentoring",
                        "description": "Offer mentoring and coaching to educators to improve skills",
                        "frequency": "PER_NEW_FACILITATOR",
                        "hours": Decimal("2.00")
                    },
                    {
                        "name": "Data Analysis",
                        "description": "Analyze data to inform decision-making and identify trends",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("2.00")
                    },
                    {
                        "name": "Intervention Strategies",
                        "description": "Recommend and help implement strategies for student support",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("2.00")
                    },
                    {
                        "name": "Facilitator Recruiting & Training",
                        "description": "Recruit and train new facilitators",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("4.00")
                    },
                    {
                        "name": "Community Engagement",
                        "description": "Foster partnerships between schools, families, and community",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("4.00")
                    },
                    {
                        "name": "Facilitator Supervision/QC",
                        "description": "Supervise facilitators and ensure quality control",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("0.50")
                    }
                ]
            },
            {
                "title": "Curriculum Design",
                "description": "Curriculum development and educational content creation",
                "responsibilities": [
                    {
                        "name": "Curriculum Development",
                        "description": "Develop, assess, and update curriculum to meet educational standards",
                        "frequency": "PER_WORKSHOP_CONCEPT",
                        "hours": Decimal("20.00")
                    },
                    {
                        "name": "Curriculum Updates",
                        "description": "Update and improve existing curriculum based on feedback",
                        "frequency": "PER_WORKSHOP",
                        "hours": Decimal("1.00")
                    }
                ]
            }
        ]

        # Process roles and responsibilities
        role_created_count = 0
        role_updated_count = 0
        responsibility_created_count = 0
        responsibility_updated_count = 0

        for role_data in EXCEL_ROLES:
            # Create or update role
            role, created = Role.objects.get_or_create(
                title=role_data["title"],
                defaults={
                    "description": role_data["description"],
                    "default_responsibilities": f"Default responsibilities for {role_data['title']}"
                }
            )
            
            if created:
                role_created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created role: {role.title}')
                )
            else:
                # Update existing role
                role.description = role_data["description"]
                role.save()
                role_updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated role: {role.title}')
                )

            # Create or update responsibilities for this role
            for resp_data in role_data["responsibilities"]:
                responsibility, created = Responsibility.objects.get_or_create(
                    role=role,
                    name=resp_data["name"],
                    defaults={
                        "description": resp_data["description"],
                        "frequency_type": resp_data["frequency"],
                        "hours": resp_data["hours"]
                    }
                )
                
                if created:
                    responsibility_created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  Created responsibility: {responsibility.name} ({responsibility.hours}h/{responsibility.frequency_type})')
                    )
                else:
                    # Update existing responsibility
                    responsibility.description = resp_data["description"]
                    responsibility.frequency_type = resp_data["frequency"]
                    responsibility.hours = resp_data["hours"]
                    responsibility.save()
                    responsibility_updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'  Updated responsibility: {responsibility.name} ({responsibility.hours}h/{responsibility.frequency_type})')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed:\n'
                f'  Roles: {role_created_count} created, {role_updated_count} updated\n'
                f'  Responsibilities: {responsibility_created_count} created, {responsibility_updated_count} updated'
            )
        )
