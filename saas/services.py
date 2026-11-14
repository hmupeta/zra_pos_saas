"""SaaS provisioning service — creates tenant, admin, and default branch."""
import re
import secrets
from django.db import transaction
from django.utils import timezone
from core.models import (
    Tenant, Company, User, BranchAccess, SubscriptionPlan,
)
from .models import SignupApplication


class TenantProvisioner:
    """Provisions a new tenant with default admin + branch."""

    @staticmethod
    def generate_code(business_name):
        base = re.sub(r"[^A-Z0-9]", "", business_name.upper())[:10]
        if not base:
            base = "TENANT"
        suffix = secrets.token_hex(2).upper()
        return f"{base}-{suffix}"

    @staticmethod
    def generate_username(business_name, contact_email):
        base = re.sub(r"[^a-z0-9]", "", (contact_email.split("@")[0] or "admin"))[:15]
        return f"{base or 'admin'}"

    @classmethod
    @transaction.atomic
    def approve_and_provision(cls, application, reviewer, admin_password=None):
        """Approve a signup application and create the tenant."""
        if application.status != "PENDING":
            raise ValueError(f"Cannot approve application in {application.status} state")

        plan = application.plan or SubscriptionPlan.objects.filter(code="TRIAL").first()
        trial_days = plan.trial_days if plan else 14

        # Create tenant
        tenant = Tenant.objects.create(
            code=cls.generate_code(application.business_name),
            name=application.business_name,
            legal_name=application.business_name,
            contact_email=application.contact_email,
            contact_phone=application.contact_phone,
            address=application.address,
            country=application.country,
            plan=plan,
            subscription_status="TRIAL",
            trial_ends_at=timezone.now() + timezone.timedelta(days=trial_days),
            billing_email=application.contact_email,
            hq_tpin=application.tpin,
            onboarded_at=timezone.now(),
        )

        # Create default branch
        branch = Company.objects.create(
            name=f"{application.business_name} (Main)",
            tenant=tenant,
            branch_code="001",
            tpin=application.tpin or "0000000000",
            address=application.address or "To be configured",
            phone=application.contact_phone,
            email=application.contact_email,
        )

        # Create owner account
        username = cls.generate_username(application.business_name, application.contact_email)
        counter = 1
        base_username = username
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        password = admin_password or secrets.token_urlsafe(12)
        owner = User.objects.create_user(
            username=username,
            email=application.contact_email,
            password=password,
            first_name=application.contact_name.split()[0] if application.contact_name else "",
            last_name=" ".join(application.contact_name.split()[1:]) if application.contact_name else "",
            tenant=tenant,
            user_type="TENANT_OWNER",
            employment_status="ACTIVE",
            phone_number=application.contact_phone,
        )

        BranchAccess.objects.create(
            user=owner, company=branch, is_default=True,
        )

        # Update application
        application.status = "APPROVED"
        application.reviewed_by = reviewer
        application.reviewed_at = timezone.now()
        application.provisioned_tenant = tenant
        application.admin_username = username
        application.save()

        return {
            "tenant_id": tenant.id,
            "tenant_code": tenant.code,
            "branch_id": branch.id,
            "owner_username": username,
            "owner_password": password if not admin_password else None,
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
        }
