"""Operator/admin-side reads of company state and hooks (FR-043, FR-044).

This exposes state for the admin-side actor; it provides no fraud-management tooling and no
company-owner UI. Verification decisions are shown read-only because they are append-only.
"""

from django.contrib import admin

from companies.models import (
    Company,
    CompanyRegistrationDraft,
    CompanyStepProgress,
    CreditLedgerEntry,
    VerificationDecision,
)


class CompanyStepProgressInline(admin.TabularInline):
    model = CompanyStepProgress
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "company_name",
        "domain",
        "owner",
        "verification_status",
        "is_archived",
    )
    list_filter = (
        "verification_status",
        "is_archived",
    )
    search_fields = ("company_name", "domain", "representative_name")
    inlines = (CompanyStepProgressInline,)


@admin.register(VerificationDecision)
class VerificationDecisionAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "outcome", "actor", "decided_at")
    list_filter = ("outcome",)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CreditLedgerEntry)
class CreditLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "direction", "amount", "reason", "created_at")
    list_filter = ("direction", "reason")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CompanyRegistrationDraft)
class CompanyRegistrationDraftAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "company", "step_key", "created_at")
