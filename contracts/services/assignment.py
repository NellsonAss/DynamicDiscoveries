from django.core.exceptions import ValidationError


def assign_contractor_to_buildout(buildout, contractor):
    """Assign a contractor to a buildout with onboarding enforcement.

    Raises ValidationError if onboarding is incomplete.
    """
    if not getattr(contractor, "onboarding_complete", False):
        raise ValidationError("Contractor must complete NDA and W-9 before assignment.")
    buildout.assigned_contractor = contractor
    buildout.save(update_fields=["assigned_contractor", "updated_at"])


