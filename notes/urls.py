from django.urls import path
from . import views

app_name = 'notes'

urlpatterns = [
    # Student Notes URLs
    path('students/<int:student_id>/notes/', views.student_notes_list, name='student_notes_list'),
    path('students/<int:student_id>/notes/new/', views.student_note_create, name='student_note_create'),
    path('students/<int:student_id>/notes/<int:note_id>/edit/', views.student_note_edit, name='student_note_edit'),
    path('students/<int:student_id>/notes/<int:note_id>/toggle-public/', views.student_note_toggle_public, name='student_note_toggle_public'),
    
    # Parent Notes URLs
    path('parents/<int:parent_id>/notes/', views.parent_notes_list, name='parent_notes_list'),
    path('parents/<int:parent_id>/notes/new/', views.parent_note_create, name='parent_note_create'),
    path('parents/<int:parent_id>/notes/<int:note_id>/edit/', views.parent_note_edit, name='parent_note_edit'),
    path('parents/<int:parent_id>/notes/<int:note_id>/toggle-public/', views.parent_note_toggle_public, name='parent_note_toggle_public'),
]
