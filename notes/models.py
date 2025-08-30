from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from programs.models import Child

User = get_user_model()


class StudentNote(models.Model):
    """Note about a student, created by staff members."""
    VISIBILITY_CHOICES = [
        ('private_staff', 'Private to staff'),
        ('public_parent', 'Visible to parent'),
    ]

    # Core fields
    student = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='student_notes_created'
    )
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(help_text="Note content")
    
    # Visibility control
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this note is visible to the parent"
    )
    visibility_scope = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='private_staff',
        help_text="Who can see this note"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_by_last = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='student_notes_edited',
        null=True,
        blank=True
    )
    soft_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete for audit trail"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['is_public', 'student']),
        ]

    def __str__(self):
        title_part = f": {self.title}" if self.title else ""
        return f"Note for {self.student.full_name}{title_part}"

    def clean(self):
        """Ensure visibility_scope and is_public are in sync."""
        if self.visibility_scope == 'public_parent':
            if not self.body.strip():
                raise ValidationError("Cannot make an empty note public.")
            self.is_public = True
        else:
            self.is_public = False

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class ParentNote(models.Model):
    """Note about a parent/user, created by admin staff."""
    VISIBILITY_CHOICES = [
        ('private_staff', 'Private to staff'),
        ('public_parent', 'Visible to parent'),
    ]

    # Core fields
    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='parent_notes',
        limit_choices_to={'groups__name': 'Parent'}
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='parent_notes_created'
    )
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(help_text="Note content")
    
    # Visibility control
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this note is visible to the parent"
    )
    visibility_scope = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='private_staff',
        help_text="Who can see this note"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_by_last = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='parent_notes_edited',
        null=True,
        blank=True
    )
    soft_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete for audit trail"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['parent', '-created_at']),
            models.Index(fields=['is_public', 'parent']),
        ]

    def __str__(self):
        title_part = f": {self.title}" if self.title else ""
        return f"Note for {self.parent.email}{title_part}"

    def clean(self):
        """Ensure visibility_scope and is_public are in sync."""
        if self.visibility_scope == 'public_parent':
            if not self.body.strip():
                raise ValidationError("Cannot make an empty note public.")
            self.is_public = True
        else:
            self.is_public = False

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
