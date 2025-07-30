from django.db import models
from django.utils import timezone

# Create your models here.

class Contact(models.Model):
    """Model to store contact form submissions."""
    INTEREST_CHOICES = [
        ('after_school', 'After-School Enrichment'),
        ('small_group', 'Small Group Tutoring'),
        ('assessments', 'Educational Assessments'),
        ('workshops', 'Signature Workshops'),
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
