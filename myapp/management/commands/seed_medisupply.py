from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from myapp.models import Hospital, Role


class Command(BaseCommand):
    help = "Seed MEDISUPPLY roles, Nakuru County facilities, and role-mapped user accounts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="Medisupply@2026",
            help="Password applied to seeded user accounts (default: Medisupply@2026).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        User = get_user_model()

        role_defs = [
            ("ROLE_ADMIN", "System Administrator", "Full system administration and access control."),
            ("ROLE_HOSPITAL_ADMIN", "Hospital Administrator", "Hub oversight, requisition review, and reporting."),
            ("ROLE_WAREHOUSE", "Warehouse Officer", "Inbound receipts, batch management, and FEFO dispatch."),
            ("ROLE_BRANCH_OFFICER", "Branch Facility Officer", "Branch stock, requisitions, and delivery confirmation."),
        ]

        roles = {}
        for role_code, role_name, description in role_defs:
            role_obj, _ = Role.objects.get_or_create(
                role_code=role_code,
                defaults={"role_name": role_name, "description": description},
            )
            updates = []
            if role_obj.role_name != role_name:
                role_obj.role_name = role_name
                updates.append("role_name")
            if role_obj.description != description:
                role_obj.description = description
                updates.append("description")
            if updates:
                role_obj.save(update_fields=updates)
            roles[role_code] = role_obj

        main_hospital, _ = Hospital.objects.get_or_create(
            hospital_code="HOSP-RVCRH",
            defaults={
                "name": "Rift Valley Central Referral Hospital",
                "facility_type": "MAIN_HOSPITAL",
                "county": "Nakuru",
                "sub_county": "Nakuru Town East",
                "is_active": True,
            },
        )

        branch_defs = [
            ("HOSP-SUBUKIA", "Subukia Community Clinic", "Subukia"),
            ("HOSP-BAHATI", "Bahati Sub-County Hospital", "Bahati"),
            ("HOSP-GILGIL", "Gilgil Health Centre", "Gilgil"),
        ]

        branches = {}
        for hospital_code, branch_name, sub_county in branch_defs:
            branch_obj, _ = Hospital.objects.get_or_create(
                hospital_code=hospital_code,
                defaults={
                    "name": branch_name,
                    "facility_type": "BRANCH_HOSPITAL",
                    "parent_hospital": main_hospital,
                    "county": "Nakuru",
                    "sub_county": sub_county,
                    "is_active": True,
                },
            )
            if branch_obj.parent_hospital_id != main_hospital.pk:
                branch_obj.parent_hospital = main_hospital
                branch_obj.save(update_fields=["parent_hospital"])
            branches[branch_name] = branch_obj

        # (username, full_name, email, role_code, hospital, is_staff)
        users_to_seed = [
            (
                "sysadmin",
                "System Administrator",
                "sysadmin@medisupply.local",
                "ROLE_ADMIN",
                main_hospital,
                True,
            ),
            (
                "rvcrh_admin",
                "RVCRH Hospital Administrator",
                "admin.rvcrh@medisupply.local",
                "ROLE_HOSPITAL_ADMIN",
                main_hospital,
                True,
            ),
            (
                "rvcrh_warehouse",
                "RVCRH Warehouse Officer",
                "warehouse.rvcrh@medisupply.local",
                "ROLE_WAREHOUSE",
                main_hospital,
                False,
            ),
            (
                "subukia_officer",
                "Subukia Facility Officer",
                "officer.subukia@medisupply.local",
                "ROLE_BRANCH_OFFICER",
                branches["Subukia Community Clinic"],
                False,
            ),
            (
                "bahati_officer",
                "Bahati Facility Officer",
                "officer.bahati@medisupply.local",
                "ROLE_BRANCH_OFFICER",
                branches["Bahati Sub-County Hospital"],
                False,
            ),
            (
                "gilgil_officer",
                "Gilgil Facility Officer",
                "officer.gilgil@medisupply.local",
                "ROLE_BRANCH_OFFICER",
                branches["Gilgil Health Centre"],
                False,
            ),
        ]

        for username, full_name, email, role_code, hospital, is_staff in users_to_seed:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "full_name": full_name,
                    "email": email,
                    "role": roles[role_code],
                    "hospital": hospital,
                    "is_staff": is_staff,
                    "is_active": True,
                },
            )
            if not created:
                user.full_name = full_name
                user.email = email
                user.role = roles[role_code]
                user.hospital = hospital
                user.is_staff = is_staff
                user.is_active = True
            user.set_password(password)
            user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(roles)} roles, 4 facilities, and {len(users_to_seed)} users (password: {password})."
            )
        )