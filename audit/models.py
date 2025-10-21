from django.db import models
from django.conf import settings
from django.utils import timezone


class ImpersonationLog(models.Model):
    """
    Audit log for user impersonation events.
    Tracks when admins/superusers impersonate other users for testing/support.
    """
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='impersonation_sessions_started',
        help_text='The admin/staff user who initiated the impersonation'
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='impersonation_sessions_received',
        help_text='The user being impersonated'
    )
    started_at = models.DateTimeField(
        default=timezone.now,
        help_text='When the impersonation session started'
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the impersonation session ended'
    )
    readonly = models.BooleanField(
        default=True,
        help_text='Whether write operations were blocked during this session'
    )
    reason_note = models.TextField(
        blank=True,
        help_text='Optional reason for impersonation'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the admin when starting impersonation'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='Browser user agent string'
    )

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['admin_user', '-started_at']),
            models.Index(fields=['target_user', '-started_at']),
        ]

    def __str__(self):
        status = "Active" if self.ended_at is None else "Ended"
        return f"{self.admin_user.email} → {self.target_user.email} ({status})"

    @property
    def is_active(self):
        """Check if this impersonation session is still active."""
        return self.ended_at is None

    @property
    def duration(self):
        """Get the duration of the impersonation session."""
        if self.ended_at:
            return self.ended_at - self.started_at
        return timezone.now() - self.started_at

