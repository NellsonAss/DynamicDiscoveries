from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import get_user_model
from programs.models import Child
from .models import StudentNote, ParentNote
from .forms import StudentNoteForm, ParentNoteForm
from .permissions import (
    user_can_create_student_note, user_can_create_parent_note,
    user_can_edit_student_note, user_can_edit_parent_note,
    user_can_toggle_student_note_public, user_can_toggle_parent_note_public,
    get_student_notes_queryset, get_parent_notes_queryset,
    user_is_parent_of_student, user_is_parent_record_owner
)

User = get_user_model()


# Student Notes Views

@login_required
def student_notes_list(request, student_id):
    """List notes for a student."""
    student = get_object_or_404(Child, id=student_id)
    notes = get_student_notes_queryset(request.user, student)
    
    context = {
        'student': student,
        'notes': notes,
        'can_create': user_can_create_student_note(request.user),
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'notes/partials/_student_notes_list.html', context)
    return render(request, 'notes/student_notes_list.html', context)


@login_required
def student_note_create(request, student_id):
    """Create a new student note."""
    student = get_object_or_404(Child, id=student_id)
    
    if not user_can_create_student_note(request.user):
        return HttpResponseForbidden("You don't have permission to create student notes.")
    
    if request.method == 'POST':
        form = StudentNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.student = student
            note.created_by = request.user
            note.save()
            
            messages.success(request, "Note created successfully.")
            
            if request.headers.get('HX-Request'):
                # Return the updated notes list
                notes = get_student_notes_queryset(request.user, student)
                context = {
                    'student': student,
                    'notes': notes,
                    'can_create': user_can_create_student_note(request.user),
                }
                return render(request, 'notes/partials/_student_notes_list.html', context)
            
            return redirect('notes:student_notes_list', student_id=student.id)
    else:
        form = StudentNoteForm()
    
    context = {
        'form': form,
        'student': student,
        'action': 'Create'
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'notes/partials/_student_note_form.html', context)
    return render(request, 'notes/student_note_form.html', context)


@login_required
def student_note_edit(request, student_id, note_id):
    """Edit a student note."""
    student = get_object_or_404(Child, id=student_id)
    note = get_object_or_404(StudentNote, id=note_id, student=student, soft_deleted=False)
    
    if not user_can_edit_student_note(request.user, note):
        return HttpResponseForbidden("You don't have permission to edit this note.")
    
    if request.method == 'POST':
        form = StudentNoteForm(request.POST, instance=note)
        if form.is_valid():
            note = form.save(commit=False)
            note.edited_by_last = request.user
            note.save()
            
            messages.success(request, "Note updated successfully.")
            
            if request.headers.get('HX-Request'):
                # Return the updated notes list
                notes = get_student_notes_queryset(request.user, student)
                context = {
                    'student': student,
                    'notes': notes,
                    'can_create': user_can_create_student_note(request.user),
                }
                return render(request, 'notes/partials/_student_notes_list.html', context)
            
            return redirect('notes:student_notes_list', student_id=student.id)
    else:
        form = StudentNoteForm(instance=note)
    
    context = {
        'form': form,
        'student': student,
        'note': note,
        'action': 'Edit'
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'notes/partials/_student_note_form.html', context)
    return render(request, 'notes/student_note_form.html', context)


@login_required
@require_POST
@csrf_protect
def student_note_toggle_public(request, student_id, note_id):
    """Toggle public visibility of a student note."""
    student = get_object_or_404(Child, id=student_id)
    note = get_object_or_404(StudentNote, id=note_id, student=student, soft_deleted=False)
    
    if not user_can_toggle_student_note_public(request.user, note):
        return HttpResponseForbidden("You don't have permission to change note visibility.")
    
    # Toggle visibility
    if note.visibility_scope == 'private_staff':
        if not note.body.strip():
            messages.error(request, "Cannot make an empty note public.")
        else:
            note.visibility_scope = 'public_parent'
            note.is_public = True
            note.edited_by_last = request.user
            note.save()
            messages.success(request, "Note is now visible to parent.")
    else:
        note.visibility_scope = 'private_staff'
        note.is_public = False
        note.edited_by_last = request.user
        note.save()
        messages.success(request, "Note is now private to staff.")
    
    if request.headers.get('HX-Request'):
        # Return the updated notes list
        notes = get_student_notes_queryset(request.user, student)
        context = {
            'student': student,
            'notes': notes,
            'can_create': user_can_create_student_note(request.user),
        }
        return render(request, 'notes/partials/_student_notes_list.html', context)
    
    return redirect('notes:student_notes_list', student_id=student.id)


# Parent Notes Views

@login_required
def parent_notes_list(request, parent_id):
    """List notes for a parent."""
    parent = get_object_or_404(User, id=parent_id, groups__name='Parent')
    notes = get_parent_notes_queryset(request.user, parent)
    
    context = {
        'parent': parent,
        'notes': notes,
        'can_create': user_can_create_parent_note(request.user),
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'notes/partials/_parent_notes_list.html', context)
    return render(request, 'notes/parent_notes_list.html', context)


@login_required
def parent_note_create(request, parent_id):
    """Create a new parent note."""
    parent = get_object_or_404(User, id=parent_id, groups__name='Parent')
    
    if not user_can_create_parent_note(request.user):
        return HttpResponseForbidden("You don't have permission to create parent notes.")
    
    if request.method == 'POST':
        form = ParentNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.parent = parent
            note.created_by = request.user
            note.save()
            
            messages.success(request, "Note created successfully.")
            
            if request.headers.get('HX-Request'):
                # Return the updated notes list
                notes = get_parent_notes_queryset(request.user, parent)
                context = {
                    'parent': parent,
                    'notes': notes,
                    'can_create': user_can_create_parent_note(request.user),
                }
                return render(request, 'notes/partials/_parent_notes_list.html', context)
            
            return redirect('notes:parent_notes_list', parent_id=parent.id)
    else:
        form = ParentNoteForm()
    
    context = {
        'form': form,
        'parent': parent,
        'action': 'Create'
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'notes/partials/_parent_note_form.html', context)
    return render(request, 'notes/parent_note_form.html', context)


@login_required
def parent_note_edit(request, parent_id, note_id):
    """Edit a parent note."""
    parent = get_object_or_404(User, id=parent_id, groups__name='Parent')
    note = get_object_or_404(ParentNote, id=note_id, parent=parent, soft_deleted=False)
    
    if not user_can_edit_parent_note(request.user, note):
        return HttpResponseForbidden("You don't have permission to edit this note.")
    
    if request.method == 'POST':
        form = ParentNoteForm(request.POST, instance=note)
        if form.is_valid():
            note = form.save(commit=False)
            note.edited_by_last = request.user
            note.save()
            
            messages.success(request, "Note updated successfully.")
            
            if request.headers.get('HX-Request'):
                # Return the updated notes list
                notes = get_parent_notes_queryset(request.user, parent)
                context = {
                    'parent': parent,
                    'notes': notes,
                    'can_create': user_can_create_parent_note(request.user),
                }
                return render(request, 'notes/partials/_parent_notes_list.html', context)
            
            return redirect('notes:parent_notes_list', parent_id=parent.id)
    else:
        form = ParentNoteForm(instance=note)
    
    context = {
        'form': form,
        'parent': parent,
        'note': note,
        'action': 'Edit'
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'notes/partials/_parent_note_form.html', context)
    return render(request, 'notes/parent_note_form.html', context)


@login_required
@require_POST
@csrf_protect
def parent_note_toggle_public(request, parent_id, note_id):
    """Toggle public visibility of a parent note."""
    parent = get_object_or_404(User, id=parent_id, groups__name='Parent')
    note = get_object_or_404(ParentNote, id=note_id, parent=parent, soft_deleted=False)
    
    if not user_can_toggle_parent_note_public(request.user, note):
        return HttpResponseForbidden("You don't have permission to change note visibility.")
    
    # Toggle visibility
    if note.visibility_scope == 'private_staff':
        if not note.body.strip():
            messages.error(request, "Cannot make an empty note public.")
        else:
            note.visibility_scope = 'public_parent'
            note.is_public = True
            note.edited_by_last = request.user
            note.save()
            messages.success(request, "Note is now visible to parent.")
    else:
        note.visibility_scope = 'private_staff'
        note.is_public = False
        note.edited_by_last = request.user
        note.save()
        messages.success(request, "Note is now private to staff.")
    
    if request.headers.get('HX-Request'):
        # Return the updated notes list
        notes = get_parent_notes_queryset(request.user, parent)
        context = {
            'parent': parent,
            'notes': notes,
            'can_create': user_can_create_parent_note(request.user),
        }
        return render(request, 'notes/partials/_parent_notes_list.html', context)
    
    return redirect('notes:parent_notes_list', parent_id=parent.id)
