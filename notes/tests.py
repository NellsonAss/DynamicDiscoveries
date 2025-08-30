from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from programs.models import Child
from .models import StudentNote, ParentNote
from .permissions import (
    user_is_admin, user_is_facilitator, user_can_create_student_note,
    user_can_create_parent_note, user_can_edit_student_note, user_can_edit_parent_note,
    get_student_notes_queryset, get_parent_notes_queryset
)

User = get_user_model()


class NotesModelTestCase(TestCase):
    """Test cases for Notes models."""
    
    def setUp(self):
        """Set up test data."""
        # Create groups
        self.admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.facilitator_group, _ = Group.objects.get_or_create(name='Facilitator')
        self.parent_group, _ = Group.objects.get_or_create(name='Parent')
        
        # Create users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.facilitator_user = User.objects.create_user(
            email='facilitator@test.com',
            password='testpass123'
        )
        self.facilitator_user.groups.add(self.facilitator_group)
        
        self.parent_user = User.objects.create_user(
            email='parent@test.com',
            password='testpass123'
        )
        self.parent_user.groups.add(self.parent_group)
        
        self.other_parent_user = User.objects.create_user(
            email='otherparent@test.com',
            password='testpass123'
        )
        self.other_parent_user.groups.add(self.parent_group)
        
        # Create child
        self.child = Child.objects.create(
            parent=self.parent_user,
            first_name='Test',
            last_name='Child',
            date_of_birth='2010-01-01'
        )
    
    def test_student_note_creation(self):
        """Test student note creation."""
        note = StudentNote.objects.create(
            student=self.child,
            created_by=self.facilitator_user,
            title='Test Note',
            body='This is a test note.',
            visibility_scope='private_staff'
        )
        
        self.assertEqual(note.student, self.child)
        self.assertEqual(note.created_by, self.facilitator_user)
        self.assertEqual(note.title, 'Test Note')
        self.assertEqual(note.body, 'This is a test note.')
        self.assertEqual(note.visibility_scope, 'private_staff')
        self.assertFalse(note.is_public)
        self.assertFalse(note.soft_deleted)
    
    def test_student_note_public_visibility(self):
        """Test student note public visibility sync."""
        note = StudentNote.objects.create(
            student=self.child,
            created_by=self.facilitator_user,
            body='Public note',
            visibility_scope='public_parent'
        )
        
        self.assertTrue(note.is_public)
    
    def test_student_note_validation(self):
        """Test student note validation."""
        from django.core.exceptions import ValidationError
        
        # Empty body with public visibility should fail
        note = StudentNote(
            student=self.child,
            created_by=self.facilitator_user,
            body='',
            visibility_scope='public_parent'
        )
        
        with self.assertRaises(ValidationError):
            note.clean()
    
    def test_parent_note_creation(self):
        """Test parent note creation."""
        note = ParentNote.objects.create(
            parent=self.parent_user,
            created_by=self.admin_user,
            title='Parent Note',
            body='This is a parent note.',
            visibility_scope='private_staff'
        )
        
        self.assertEqual(note.parent, self.parent_user)
        self.assertEqual(note.created_by, self.admin_user)
        self.assertEqual(note.title, 'Parent Note')
        self.assertFalse(note.is_public)


class NotesPermissionsTestCase(TestCase):
    """Test cases for Notes permissions."""
    
    def setUp(self):
        """Set up test data."""
        # Create groups
        self.admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.facilitator_group, _ = Group.objects.get_or_create(name='Facilitator')
        self.parent_group, _ = Group.objects.get_or_create(name='Parent')
        
        # Create users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.facilitator_user = User.objects.create_user(
            email='facilitator@test.com',
            password='testpass123'
        )
        self.facilitator_user.groups.add(self.facilitator_group)
        
        self.parent_user = User.objects.create_user(
            email='parent@test.com',
            password='testpass123'
        )
        self.parent_user.groups.add(self.parent_group)
        
        self.other_parent_user = User.objects.create_user(
            email='otherparent@test.com',
            password='testpass123'
        )
        self.other_parent_user.groups.add(self.parent_group)
        
        # Create child
        self.child = Child.objects.create(
            parent=self.parent_user,
            first_name='Test',
            last_name='Child',
            date_of_birth='2010-01-01'
        )
        
        # Create notes
        self.facilitator_note = StudentNote.objects.create(
            student=self.child,
            created_by=self.facilitator_user,
            body='Facilitator note',
            visibility_scope='private_staff'
        )
        
        self.admin_note = StudentNote.objects.create(
            student=self.child,
            created_by=self.admin_user,
            body='Admin note',
            visibility_scope='public_parent'
        )
        
        self.parent_note = ParentNote.objects.create(
            parent=self.parent_user,
            created_by=self.admin_user,
            body='Parent note',
            visibility_scope='private_staff'
        )
    
    def test_user_role_detection(self):
        """Test user role detection functions."""
        self.assertTrue(user_is_admin(self.admin_user))
        self.assertFalse(user_is_admin(self.facilitator_user))
        self.assertFalse(user_is_admin(self.parent_user))
        
        self.assertTrue(user_is_facilitator(self.facilitator_user))
        self.assertFalse(user_is_facilitator(self.admin_user))
        self.assertFalse(user_is_facilitator(self.parent_user))
    
    def test_student_note_creation_permissions(self):
        """Test student note creation permissions."""
        self.assertTrue(user_can_create_student_note(self.admin_user))
        self.assertTrue(user_can_create_student_note(self.facilitator_user))
        self.assertFalse(user_can_create_student_note(self.parent_user))
    
    def test_parent_note_creation_permissions(self):
        """Test parent note creation permissions."""
        self.assertTrue(user_can_create_parent_note(self.admin_user))
        self.assertFalse(user_can_create_parent_note(self.facilitator_user))
        self.assertFalse(user_can_create_parent_note(self.parent_user))
    
    def test_student_note_edit_permissions(self):
        """Test student note edit permissions."""
        # Admin can edit any note
        self.assertTrue(user_can_edit_student_note(self.admin_user, self.facilitator_note))
        self.assertTrue(user_can_edit_student_note(self.admin_user, self.admin_note))
        
        # Facilitator can edit only their own notes
        self.assertTrue(user_can_edit_student_note(self.facilitator_user, self.facilitator_note))
        self.assertFalse(user_can_edit_student_note(self.facilitator_user, self.admin_note))
        
        # Parent cannot edit any notes
        self.assertFalse(user_can_edit_student_note(self.parent_user, self.facilitator_note))
    
    def test_student_notes_queryset_filtering(self):
        """Test student notes queryset filtering."""
        # Admin sees all notes
        admin_notes = get_student_notes_queryset(self.admin_user, self.child)
        self.assertEqual(admin_notes.count(), 2)
        
        # Facilitator sees all notes
        facilitator_notes = get_student_notes_queryset(self.facilitator_user, self.child)
        self.assertEqual(facilitator_notes.count(), 2)
        
        # Parent sees only public notes for their child
        parent_notes = get_student_notes_queryset(self.parent_user, self.child)
        self.assertEqual(parent_notes.count(), 1)
        self.assertEqual(parent_notes.first(), self.admin_note)
        
        # Other parent sees no notes
        other_parent_notes = get_student_notes_queryset(self.other_parent_user, self.child)
        self.assertEqual(other_parent_notes.count(), 0)
    
    def test_parent_notes_queryset_filtering(self):
        """Test parent notes queryset filtering."""
        # Create public parent note
        public_note = ParentNote.objects.create(
            parent=self.parent_user,
            created_by=self.admin_user,
            body='Public parent note',
            visibility_scope='public_parent'
        )
        
        # Admin sees all notes
        admin_notes = get_parent_notes_queryset(self.admin_user, self.parent_user)
        self.assertEqual(admin_notes.count(), 2)
        
        # Parent sees only their own public notes
        parent_notes = get_parent_notes_queryset(self.parent_user, self.parent_user)
        self.assertEqual(parent_notes.count(), 1)
        self.assertEqual(parent_notes.first(), public_note)
        
        # Facilitator sees no parent notes
        facilitator_notes = get_parent_notes_queryset(self.facilitator_user, self.parent_user)
        self.assertEqual(facilitator_notes.count(), 0)


class NotesViewsTestCase(TestCase):
    """Test cases for Notes views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create groups
        self.admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.facilitator_group, _ = Group.objects.get_or_create(name='Facilitator')
        self.parent_group, _ = Group.objects.get_or_create(name='Parent')
        
        # Create users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.facilitator_user = User.objects.create_user(
            email='facilitator@test.com',
            password='testpass123'
        )
        self.facilitator_user.groups.add(self.facilitator_group)
        
        self.parent_user = User.objects.create_user(
            email='parent@test.com',
            password='testpass123'
        )
        self.parent_user.groups.add(self.parent_group)
        
        # Create child
        self.child = Child.objects.create(
            parent=self.parent_user,
            first_name='Test',
            last_name='Child',
            date_of_birth='2010-01-01'
        )
    
    def test_student_notes_list_access(self):
        """Test student notes list access."""
        url = reverse('notes:student_notes_list', kwargs={'student_id': self.child.id})
        
        # Unauthenticated access should redirect
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
        # Admin access should work
        self.client.login(email='admin@test.com', password='testpass123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Parent access to their own child should work
        self.client.login(email='parent@test.com', password='testpass123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_student_note_creation(self):
        """Test student note creation."""
        url = reverse('notes:student_note_create', kwargs={'student_id': self.child.id})
        
        # Login as facilitator
        self.client.login(email='facilitator@test.com', password='testpass123')
        
        # GET request should show form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # POST request should create note
        data = {
            'title': 'Test Note',
            'body': 'This is a test note.',
            'visibility_scope': 'private_staff'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        
        # Check note was created
        note = StudentNote.objects.get(title='Test Note')
        self.assertEqual(note.student, self.child)
        self.assertEqual(note.created_by, self.facilitator_user)
    
    def test_student_note_creation_forbidden_for_parent(self):
        """Test that parents cannot create student notes."""
        url = reverse('notes:student_note_create', kwargs={'student_id': self.child.id})
        
        self.client.login(email='parent@test.com', password='testpass123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_parent_note_creation(self):
        """Test parent note creation."""
        url = reverse('notes:parent_note_create', kwargs={'parent_id': self.parent_user.id})
        
        # Login as admin
        self.client.login(email='admin@test.com', password='testpass123')
        
        # POST request should create note
        data = {
            'title': 'Parent Note',
            'body': 'This is a parent note.',
            'visibility_scope': 'private_staff'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        
        # Check note was created
        note = ParentNote.objects.get(title='Parent Note')
        self.assertEqual(note.parent, self.parent_user)
        self.assertEqual(note.created_by, self.admin_user)
    
    def test_parent_note_creation_forbidden_for_facilitator(self):
        """Test that facilitators cannot create parent notes."""
        url = reverse('notes:parent_note_create', kwargs={'parent_id': self.parent_user.id})
        
        self.client.login(email='facilitator@test.com', password='testpass123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_student_note_toggle_public(self):
        """Test toggling student note public visibility."""
        note = StudentNote.objects.create(
            student=self.child,
            created_by=self.facilitator_user,
            body='Test note',
            visibility_scope='private_staff'
        )
        
        url = reverse('notes:student_note_toggle_public', kwargs={
            'student_id': self.child.id,
            'note_id': note.id
        })
        
        # Login as note creator
        self.client.login(email='facilitator@test.com', password='testpass123')
        
        # Toggle to public
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        note.refresh_from_db()
        self.assertEqual(note.visibility_scope, 'public_parent')
        self.assertTrue(note.is_public)
    
    def test_htmx_requests(self):
        """Test HTMX requests return partials."""
        url = reverse('notes:student_notes_list', kwargs={'student_id': self.child.id})
        
        self.client.login(email='admin@test.com', password='testpass123')
        
        # Regular request
        response = self.client.get(url)
        self.assertContains(response, 'Notes for')
        
        # HTMX request
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        self.assertNotContains(response, 'extends')  # Should be partial
        self.assertContains(response, 'Notes for')


class NotesIntegrationTestCase(TestCase):
    """Integration tests for Notes functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create groups
        self.admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.facilitator_group, _ = Group.objects.get_or_create(name='Facilitator')
        self.parent_group, _ = Group.objects.get_or_create(name='Parent')
        
        # Create users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.parent_user = User.objects.create_user(
            email='parent@test.com',
            password='testpass123'
        )
        self.parent_user.groups.add(self.parent_group)
        
        # Create child
        self.child = Child.objects.create(
            parent=self.parent_user,
            first_name='Test',
            last_name='Child',
            date_of_birth='2010-01-01'
        )
    
    def test_full_workflow(self):
        """Test complete notes workflow."""
        # Admin creates a private note
        self.client.login(email='admin@test.com', password='testpass123')
        
        create_url = reverse('notes:student_note_create', kwargs={'student_id': self.child.id})
        data = {
            'title': 'Admin Note',
            'body': 'This is an admin note.',
            'visibility_scope': 'private_staff'
        }
        response = self.client.post(create_url, data)
        self.assertEqual(response.status_code, 302)
        
        note = StudentNote.objects.get(title='Admin Note')
        self.assertFalse(note.is_public)
        
        # Parent should not see the private note
        self.client.login(email='parent@test.com', password='testpass123')
        list_url = reverse('notes:student_notes_list', kwargs={'student_id': self.child.id})
        response = self.client.get(list_url)
        self.assertNotContains(response, 'Admin Note')
        
        # Admin toggles note to public
        self.client.login(email='admin@test.com', password='testpass123')
        toggle_url = reverse('notes:student_note_toggle_public', kwargs={
            'student_id': self.child.id,
            'note_id': note.id
        })
        response = self.client.post(toggle_url)
        self.assertEqual(response.status_code, 302)
        
        note.refresh_from_db()
        self.assertTrue(note.is_public)
        
        # Parent should now see the public note
        self.client.login(email='parent@test.com', password='testpass123')
        response = self.client.get(list_url)
        self.assertContains(response, 'Admin Note')
