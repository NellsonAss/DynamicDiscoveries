from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.

class Contact(models.Model):
    """Model to store contact form submissions."""
    INTEREST_CHOICES = [
        ('after_school', 'After-School Enrichment'),
        ('small_group', 'Small Group Tutoring'),
        ('assessments', 'Educational Assessments'),
        ('programs', 'Signature Programs'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('contacted', 'Contacted'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    # Contact Information
    parent_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    interest = models.CharField(max_length=20, choices=INTEREST_CHOICES)
    message = models.TextField()
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, help_text="Internal notes for staff")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Inquiry'
        verbose_name_plural = 'Contact Inquiries'
    
    def __str__(self):
        return f"{self.parent_name} - {self.interest} ({self.created_at.strftime('%Y-%m-%d')})"
    
    @property
    def is_new(self):
        return self.status == 'new'
    
    @property
    def days_old(self):
        return (timezone.now() - self.created_at).days
    
    @property
    def days_old_display(self):
        days = self.days_old
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        else:
            return f"{days} days ago"


class Conversation(models.Model):
    """Model to store conversations between parents and staff."""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('pending', 'Pending'),
        ('closed', 'Closed'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
    
    def __str__(self):
        return f"{self.owner.email} - {self.subject}"
    
    @property
    def message_count(self):
        return self.messages.count()
    
    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()


class Message(models.Model):
    """Model to store individual messages within conversations."""
    ROLE_CHOICES = [
        ('parent', 'Parent'),
        ('staff', 'Staff'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    body = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
    
    def __str__(self):
        return f"{self.role} - {self.conversation.subject} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
