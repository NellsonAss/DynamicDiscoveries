"""
Template tags for role preview and impersonation.
"""
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def show_role_menu(context, role_name):
    """
    Determine if a role's menu should be shown based on effective_role.
    
    Logic:
    - If effective_role is "Auto", show menu if user has the role
    - If effective_role is set to a specific role, only show that role's menu
    - Never show menus the user doesn't actually have (no privilege escalation)
    
    Args:
        context: Template context
        role_name: Name of the role to check (e.g., "Parent", "Admin")
    
    Returns:
        bool: True if the menu should be shown
    """
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    
    # Get effective_role from context
    effective_role = context.get('effective_role', 'Auto')
    
    # User must actually have this role (no privilege escalation)
    user_has_role = request.user.groups.filter(name=role_name).exists()
    if not user_has_role:
        return False
    
    # If effective_role is Auto, show menu if user has the role
    if effective_role == 'Auto':
        return True
    
    # If effective_role is set, only show that role's menu
    return effective_role == role_name


@register.simple_tag(takes_context=True)
def should_show_contractor_menu(context):
    """
    Special case for Contractor menu which is shown to both Contractors and Admins.
    
    Returns:
        bool: True if contractor menu should be shown
    """
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    
    effective_role = context.get('effective_role', 'Auto')
    
    # Check if user has Contractor or Admin role
    is_contractor = request.user.groups.filter(name='Contractor').exists()
    is_admin = request.user.groups.filter(name='Admin').exists()
    
    if not (is_contractor or is_admin):
        return False
    
    # If Auto, show if they have either role
    if effective_role == 'Auto':
        return True
    
    # If previewing a specific role, only show if that role is Contractor or Admin
    return effective_role in ['Contractor', 'Admin']

