from django.contrib import admin
from .models import Contractor


@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    list_display = ["user", "nda_signed", "onboarding_complete", "w9_uploaded"]
    search_fields = ["user__email"]
    list_filter = ["nda_signed", "onboarding_complete"]

    def w9_uploaded(self, obj):
        return bool(obj.w9_file)
    w9_uploaded.boolean = True
    w9_uploaded.short_description = "W-9 Uploaded"



