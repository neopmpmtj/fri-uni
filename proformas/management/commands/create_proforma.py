from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from proformas.models import EquipmentModel, Site, TubingLength
from proformas.services import add_line, create_draft, issue_proforma


class Command(BaseCommand):
    help = "Create a proforma using the same services as the staff website."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="Staff email (created_by)")
        parser.add_argument("--site", type=int, required=True, help="Site id")
        parser.add_argument(
            "--line",
            action="append",
            required=True,
            help="model_id:qty or model_id:qty:tubing_length_id",
        )
        parser.add_argument("--discount-percent", default=None)
        parser.add_argument("--extra-labour", default=None)
        parser.add_argument("--observations", default="")
        parser.add_argument("--issue", action="store_true")

    def handle(self, *args, **options):
        try:
            user = User.objects.get(email=options["user"])
        except User.DoesNotExist as exc:
            raise CommandError(f"Unknown user {options['user']}") from exc
        try:
            site = Site.objects.get(pk=options["site"])
        except Site.DoesNotExist as exc:
            raise CommandError(f"Unknown site {options['site']}") from exc

        draft_kwargs = {"observations": options["observations"] or ""}
        if options["discount_percent"] is not None:
            draft_kwargs["discount_percent"] = Decimal(str(options["discount_percent"]))
        if options["extra_labour"] is not None:
            draft_kwargs["extra_labour"] = Decimal(str(options["extra_labour"]))

        proforma = create_draft(site, user, **draft_kwargs)
        for spec in options["line"]:
            parts = spec.split(":")
            if len(parts) not in (2, 3):
                raise CommandError(
                    "Each --line must be model_id:qty or model_id:qty:tubing_length_id"
                )
            try:
                model = EquipmentModel.objects.get(pk=int(parts[0]))
            except EquipmentModel.DoesNotExist as exc:
                raise CommandError(f"Unknown model {parts[0]}") from exc
            quantity = int(parts[1])
            tubing = None
            extra = False
            if len(parts) == 3:
                try:
                    tubing = TubingLength.objects.get(pk=int(parts[2]))
                except TubingLength.DoesNotExist as exc:
                    raise CommandError(f"Unknown tubing length {parts[2]}") from exc
                extra = True
            add_line(
                proforma,
                model,
                user,
                quantity=quantity,
                extra_tubing=extra,
                tubing_length=tubing,
            )
        if options["issue"]:
            issue_proforma(proforma, user)
        proforma.refresh_from_db()
        self.stdout.write(proforma.number)
