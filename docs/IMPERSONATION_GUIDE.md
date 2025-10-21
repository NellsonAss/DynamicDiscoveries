# Admin "View As" Feature Guide

## Overview

The "View As" feature provides two powerful capabilities for administrators:

1. **Role Preview** - View the site as different roles you already have
2. **User Impersonation** - Preview the site as another user (with optional read-only mode)

All impersonation events are fully audited for security and compliance.

## Role Preview (Self)

### What is it?
Role Preview allows multi-role users (e.g., someone who is both Admin and Parent) to see how the site appears for different roles without logging out.

### Who can use it?
Any authenticated user with 2 or more roles.

### How to use it:

1. **Access the Role Switcher**
   - Look for the role badge in the top navigation bar (next to your user menu)
   - Click the dropdown to see all your roles

2. **Switch Roles**
   - Select a role to preview (e.g., "Parent", "Contractor", "Admin")
   - Or select "Auto (Default)" to clear the preview

3. **What Happens**
   - You're redirected to that role's landing page (e.g., Parent Dashboard)
   - The UI will adjust to show features/content for that role
   - Navigation menus will reflect the selected role
   - A badge shows your current preview mode: "Viewing as: Parent"

4. **Important Notes**
   - Your actual permissions don't change - this is UI-only
   - You can only preview roles you actually have
   - Cannot use role preview while impersonating another user

## User Impersonation

### What is it?
User Impersonation allows admins/superusers to view the site exactly as another user would see it, useful for:
- QA testing
- User support
- Debugging user-specific issues
- Training and demonstrations

### Who can use it?
- Superusers
- Users with `can_impersonate_users` permission

### How to use it:

1. **Start Impersonation**
   - Go to Admin → User Management
   - Find the user you want to impersonate
   - Click the "Impersonate" button (person-badge icon)
   - A modal will appear

2. **Configure Impersonation**
   - **Read-Only Mode** (Recommended)
     - Blocks all write operations (POST/PUT/PATCH/DELETE)
     - Prevents accidental data modifications
     - Shows a lock icon in the banner
   
   - **Full Access Mode** (Use with caution)
     - Allows data modifications
     - Use only when necessary
     - Shows an unlock icon in the banner
   
   - **Reason** (Optional but recommended)
     - Explain why you're impersonating
     - Logged for audit purposes

3. **While Impersonating**
   - A bright warning banner appears at the top
   - Shows who you're impersonating and your real identity
   - Shows the access mode (Read-Only or Full Access)
   - All actions are logged

4. **Stop Impersonation**
   - Click "Stop Impersonating" in the banner
   - You'll return to your normal account
   - Audit log is closed with end timestamp

### Security Restrictions

The following actions are **blocked** for security:

- ❌ Impersonating yourself (use role preview instead)
- ❌ Impersonating inactive/disabled users
- ❌ Non-superusers impersonating superusers
- ❌ Write operations in read-only mode
- ❌ Using role preview while impersonating

## Audit Logging

### What's Logged?
Every impersonation event records:
- Admin user who initiated impersonation
- Target user being impersonated
- Start timestamp
- End timestamp (when stopped)
- Read-only flag
- Optional reason note
- IP address
- User agent (browser info)

### Viewing Audit Logs
1. Go to Admin Tools → Impersonation Logs
2. Or visit: `/admin-interface/impersonation-logs/`
3. Search by admin, target user, or reason
4. Filter by active/closed sessions
5. View duration and access mode

### Audit Log Integrity
- Logs cannot be deleted (only viewable)
- Logs cannot be manually created
- All fields are read-only
- Timestamps are automatic

## Best Practices

### For Admins
1. ✅ Use read-only mode by default
2. ✅ Provide a reason when impersonating
3. ✅ Stop impersonation when done
4. ✅ Review audit logs periodically
5. ❌ Don't leave impersonation sessions open
6. ❌ Don't use full access unless necessary

### For Developers
1. ✅ Use `get_effective_user_and_roles()` for user checks
2. ✅ Apply `readonly_enforcement_required` to write views
3. ✅ Test views with both role preview and impersonation
4. ✅ Consider effective_role in templates
5. ❌ Don't bypass permission checks during impersonation
6. ❌ Don't assume `request.user` is the actual user

## Troubleshooting

### "Cannot switch roles while impersonating"
- You're trying to use role preview during impersonation
- Stop impersonation first, then switch roles

### "You don't have permission to impersonate users"
- Only superusers or users with `can_impersonate_users` permission can impersonate
- Contact a superuser to grant permission

### "Write actions are disabled in preview mode"
- You're in read-only impersonation mode
- Either stop impersonation or use full access mode (if appropriate)

### Session expired during impersonation
- The system will gracefully clean up
- You'll be returned to your normal account
- Check audit logs for session details

