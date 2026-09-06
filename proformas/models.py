from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils import timezone


class LiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AuditedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    objects = LiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["deleted_at", "deleted_by", "updated_at"])


class ActorType(models.TextChoices):
    USER = "user", "User"
    SYSTEM = "system", "System"


class Parameter(AuditedModel):
    key = models.CharField(max_length=64)
    value = models.TextField()

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["key"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_parameter_key",
            )
        ]

    def __str__(self):
        return self.key


class Client(AuditedModel):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_client_name",
            )
        ]

    def __str__(self):
        return self.name


class Site(AuditedModel):
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="sites")
    alias_1 = models.CharField(max_length=255)
    alias_2 = models.CharField(max_length=255, blank=True)
    alias_3 = models.CharField(max_length=255, blank=True)
    alias_4 = models.CharField(max_length=255, blank=True)
    street = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=32, blank=True)
    city = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.alias_1


class Brand(AuditedModel):
    name = models.CharField(max_length=128)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_brand_name",
            )
        ]

    def __str__(self):
        return self.name


class Style(AuditedModel):
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="styles")
    name = models.CharField(max_length=128)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["brand", "name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_style_name_per_brand",
            )
        ]

    def __str__(self):
        return f"{self.brand.name} {self.name}"


class EquipmentModel(AuditedModel):
    """Catalog machine (data-points table `models`)."""

    class Kind(models.TextChoices):
        INDOOR = "indoor", "Indoor"
        OUTDOOR = "outdoor", "Outdoor"

    style = models.ForeignKey(
        Style, on_delete=models.PROTECT, related_name="equipment_models"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    btu = models.IntegerField()
    list_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["style", "kind", "btu"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_model_style_kind_btu",
            )
        ]

    def __str__(self):
        return f"{self.style} {self.kind} {self.btu}"


class TubingLength(AuditedModel):
    length = models.DecimalField(max_digits=8, decimal_places=2)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["length"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_tubing_length",
            )
        ]

    def __str__(self):
        return f"{self.length} m"


class Proforma(AuditedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        CANCELLED = "cancelled", "Cancelled"

    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="proformas")
    number = models.CharField(max_length=32)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    upfront_discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    extra_labour = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observations = models.TextField(blank=True)
    equipment_subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    tubing_total = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    grand_total = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    client_name = models.CharField(max_length=255, blank=True)
    client_phone = models.CharField(max_length=64, blank=True)
    client_email = models.CharField(max_length=254, blank=True)
    site_alias_1 = models.CharField(max_length=255, blank=True)
    site_alias_2 = models.CharField(max_length=255, blank=True)
    site_alias_3 = models.CharField(max_length=255, blank=True)
    site_alias_4 = models.CharField(max_length=255, blank=True)
    site_street = models.CharField(max_length=255, blank=True)
    site_postal_code = models.CharField(max_length=32, blank=True)
    site_city = models.CharField(max_length=128, blank=True)
    site_notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["number"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_proforma_number",
            )
        ]

    def __str__(self):
        return self.number


class ProformaLine(AuditedModel):
    proforma = models.ForeignKey(Proforma, on_delete=models.CASCADE, related_name="lines")
    model = models.ForeignKey(
        EquipmentModel, on_delete=models.PROTECT, related_name="proforma_lines"
    )
    quantity = models.IntegerField(default=1)
    extra_tubing = models.BooleanField(default=False)
    tubing_length = models.ForeignKey(
        TubingLength,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="proforma_lines",
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tubing_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    brand_name = models.CharField(max_length=128, blank=True)
    style_name = models.CharField(max_length=128, blank=True)
    kind = models.CharField(max_length=16, blank=True)
    btu = models.IntegerField(null=True, blank=True)
    tubing_length_value = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return f"{self.proforma.number} line"


class ChangeLog(AuditedModel):
    entity_type = models.CharField(max_length=64)
    entity_id = models.PositiveBigIntegerField()
    field = models.CharField(max_length=64)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="change_logs",
    )
    actor_type = models.CharField(
        max_length=16, choices=ActorType.choices, default=ActorType.USER
    )
    occurred_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.entity_type}.{self.field}"


class ActivityLog(AuditedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_logs",
    )
    actor_type = models.CharField(
        max_length=16, choices=ActorType.choices, default=ActorType.USER
    )
    action = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64)
    object_id = models.PositiveBigIntegerField()
    occurred_at = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)

    def __str__(self):
        return self.action
