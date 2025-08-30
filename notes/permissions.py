"""
Permission helpers for notes functionality.
"""
from django.contrib.auth import get_user_model

User = get_user_model()


def user_is_admin(user):
    """Check if user has admin role in the application."""
    if not user.is_authenticated:
        return False
    return user.groups.filter(name='Admin').exists() or user.is_staff or user.is_superuser


def user_is_facilitator(user):
    """Check if user has facilitator role."""
    if not user.is_authenticated:
        return False
    return user.groups.filter(name__in=['Facilitator', 'Contractor']).exists()


def user_is_parent_of_student(user, student):
    """Check if user is the parent of the given student (Child model)."""
    if not user.is_authenticated:
        return False
    return student.parent == user


def user_is_parent_record_owner(user, parent_user):
    """Check if user is the parent record owner (same user)."""
    if not user.is_authenticated:
        return False
    return user == parent_user


def user_can_create_student_note(user):
    """Check if user can create student notes."""
    return user_is_admin(user) or user_is_facilitator(user)


def user_can_create_parent_note(user):
    """Check if user can create parent notes."""
    return user_is_admin(user)


def user_can_edit_student_note(user, note):
    """Check if user can edit a specific student note."""
    if user_is_admin(user):
        return True
    if user_is_facilitator(user) and note.created_by == user:
        return True
    return False


def user_can_edit_parent_note(user, note):
    """Check if user can edit a specific parent note."""
    return user_is_admin(user)


def user_can_toggle_student_note_public(user, note):
    """Check if user can toggle public visibility of student note."""
    if user_is_admin(user):
        return True
    if user_is_facilitator(user) and note.created_by == user:
        return True
    return False


def user_can_toggle_parent_note_public(user, note):
    """Check if user can toggle public visibility of parent note."""
    return user_is_admin(user)


def get_student_notes_queryset(user, student):
    """Get filtered queryset of student notes based on user permissions."""
    from .models import StudentNote
    
    base_queryset = StudentNote.objects.filter(
        student=student,
        soft_deleted=False
    ).select_related('created_by', 'edited_by_last')
    
    if user_is_admin(user) or user_is_facilitator(user):
        # Staff can see all notes
        return base_queryset
    elif user_is_parent_of_student(user, student):
        # Parents can only see public notes for their child
        return base_queryset.filter(is_public=True)
    else:
        # No access
        return StudentNote.objects.none()


def get_parent_notes_queryset(user, parent_user):
    """Get filtered queryset of parent notes based on user permissions."""
    from .models import ParentNote
    
    base_queryset = ParentNote.objects.filter(
        parent=parent_user,
        soft_deleted=False
    ).select_related('created_by', 'edited_by_last')
    
    if user_is_admin(user):
        # Admins can see all notes
        return base_queryset
    elif user_is_parent_record_owner(user, parent_user):
        # Parents can only see their own public notes
        return base_queryset.filter(is_public=True)
    else:
        # Facilitators and others have no access to parent notes
        return ParentNote.objects.none()
