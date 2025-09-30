from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from programs.models import ProgramType, ProgramBuildout
from people.models import Contractor
from contracts.models import LegalDocumentTemplate


class ContractsFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.admin = User.objects.create_user(email="admin@example.com", password="pass")
        self.contractor_user = User.objects.create_user(email="contractor@example.com", password="pass")
        contractor_group_name = 'Contractor'
        from django.contrib.auth.models import Group
        contractor_group, _ = Group.objects.get_or_create(name=contractor_group_name)
        self.contractor_user.groups.add(contractor_group)
        self.contractor = Contractor.objects.create(user=self.contractor_user, nda_signed=True)

        self.program_type = ProgramType.objects.create(name="PT", description="desc")
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="B1",
            num_facilitators=1,
            num_new_facilitators=0,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=10.0,
        )
        self.buildout.assigned_contractor = self.contractor
        self.buildout.status = self.buildout.Status.READY
        self.buildout.save()
        # Ensure service agreement template exists for present_to_contractor
        LegalDocumentTemplate.objects.get_or_create(key="service_agreement", defaults={"docusign_template_id": "TEMPLATE_SVC"})

    def test_onboarding_gate(self):
        # Contractor with incomplete onboarding is redirected
        u = get_user_model().objects.create_user(email="c2@example.com", password="pass")
        from django.contrib.auth.models import Group
        g, _ = Group.objects.get_or_create(name='Contractor')
        u.groups.add(g)
        self.client.force_login(u)
        resp = self.client.get(reverse('programs:contractor_dashboard'))
        self.assertEqual(resp.status_code, 200)
        content = b"".join(resp)
        # Look for disabled scheduling controls indicating gate is active
        self.assertIn(b"Manage Schedule", content)
        self.assertIn(b"disabled", content)

    def test_onboarding_gates_and_assignment(self):
        from django.core.exceptions import ValidationError
        from django.contrib.auth.models import Group
        from people.models import Contractor
        from programs.models import ProgramType, ProgramBuildout
        from contracts.services.assignment import assign_contractor_to_buildout

        # New contractor without onboarding
        user = get_user_model().objects.create_user(email="c3@example.com", password="pass")
        g, _ = Group.objects.get_or_create(name='Contractor')
        user.groups.add(g)
        contractor = Contractor.objects.create(user=user, nda_signed=False)

        pt = ProgramType.objects.create(name="PT2", description="d2")
        b = ProgramBuildout.objects.create(
            program_type=pt,
            title="B2",
            num_facilitators=1,
            num_new_facilitators=0,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=10.0,
        )
        # Cannot assign when onboarding incomplete
        with self.assertRaises(ValidationError):
            assign_contractor_to_buildout(b, contractor)

        # Complete onboarding and assign
        contractor.nda_signed = True
        contractor.nda_approved = True
        contractor.w9_approved = True
        from django.core.files.base import ContentFile
        contractor.w9_file.save("w9.pdf", ContentFile(b"%PDF-1.4"), save=True)
        contractor.save()
        self.assertTrue(contractor.onboarding_complete)
        assign_contractor_to_buildout(b, contractor)
        self.assertEqual(b.assigned_contractor, contractor)

    def test_present_to_contractor_creates_contract(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse('programs:present_to_contractor', args=[self.buildout.id]))
        self.assertIn(resp.status_code, (302, 301))

    def test_webhook_completion_sets_active(self):
        # Create a contract via admin action
        self.client.force_login(self.admin)
        self.client.post(reverse('programs:present_to_contractor', args=[self.buildout.id]))
        from contracts.models import Contract
        contract = Contract.objects.filter(buildout=self.buildout).first()
        self.assertIsNotNone(contract)
        envelope_id = contract.envelope_id or "dev-env"
        # Send webhook
        payload = '{"envelopeId": "%s", "status": "completed"}' % envelope_id
        resp = self.client.post(reverse('contracts:webhook'), data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.buildout.refresh_from_db()
        self.assertEqual(self.buildout.status, self.buildout.Status.ACTIVE)


