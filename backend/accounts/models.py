from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


def generate_payment_reference():
    return uuid.uuid4().hex


class User(AbstractUser):
    class Category(models.TextChoices):
        STUDENT = "student", "Student"
        STAFF = "staff", "Staff"
        EXTERNAL = "external", "External"

    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        COACH = "coach", "Coach"
        MANAGER = "manager", "Centre manager"
        FINANCE = "finance", "Finance officer"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        PENDING = "pending", "Pending"

    email = models.EmailField(unique=True)
    category = models.CharField(
        max_length=10, choices=Category.choices, default=Category.STUDENT
    )
    role = models.CharField(
        max_length=10, choices=Role.choices, default=Role.MEMBER
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_full_name() or self.username


class SportsCentre(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class MembershipType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    student_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    staff_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    external_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    duration_days = models.PositiveIntegerField(default=30)
    access_level = models.CharField(max_length=50, default="basic")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        PENDING = "pending", "Pending"
        EXPIRED = "expired", "Expired"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"
        PARTIAL = "partial", "Partial"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    membership_type = models.ForeignKey(
        MembershipType, on_delete=models.PROTECT, related_name="memberships"
    )
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.membership_type}"


class Facility(models.Model):
    class FacilityType(models.TextChoices):
        COURT = "court", "Court"
        FIELD = "field", "Field"
        GYM = "gym", "Gym"
        ROOM = "room", "Room"
        POOL = "pool", "Pool"

    class Availability(models.TextChoices):
        AVAILABLE = "available", "Available"
        UNAVAILABLE = "unavailable", "Unavailable"
        MAINTENANCE = "maintenance", "Maintenance"

    sports_centre = models.ForeignKey(
        SportsCentre, on_delete=models.CASCADE, related_name="facilities"
    )
    name = models.CharField(max_length=200)
    facility_type = models.CharField(
        max_length=20, choices=FacilityType.choices, default=FacilityType.COURT
    )
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    event_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    capacity = models.PositiveIntegerField(default=1)
    availability_status = models.CharField(
        max_length=20, choices=Availability.choices, default=Availability.AVAILABLE
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sports_centre} - {self.name}"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name="bookings"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_event = models.BooleanField(default=False)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_bookings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.facility} ({self.start_time})"

    @property
    def duration_hours(self):
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600


class Equipment(models.Model):
    class Condition(models.TextChoices):
        NEW = "new", "New"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        DAMAGED = "damaged", "Damaged"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        IN_USE = "in_use", "In Use"
        DAMAGED = "damaged", "Damaged"
        LOST = "lost", "Lost"

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    available_quantity = models.PositiveIntegerField(default=1)
    condition = models.CharField(
        max_length=20, choices=Condition.choices, default=Condition.GOOD
    )
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.available_quantity = self.quantity
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(available_quantity__lte=models.F('quantity')),
                name='equipment_available_not_above_total',
            ),
        ]


class EquipmentLoan(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending deposit"
        ACTIVE = "active", "Active"
        RETURNED = "returned", "Returned"
        OVERDUE = "overdue", "Overdue"
        LOST = "lost", "Lost"
        CANCELLED = "cancelled", "Cancelled"

    class DepositStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"
        RETURNED = "returned", "Returned"
        FORFEITED = "forfeited", "Forfeited"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="equipment_loans")
    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name="loans"
    )
    quantity = models.PositiveIntegerField(default=1)
    loan_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(blank=True, null=True)
    return_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    deposit_status = models.CharField(
        max_length=20, choices=DepositStatus.choices, default=DepositStatus.UNPAID
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user} - {self.equipment} ({self.status})"


class Payment(models.Model):
    class PaymentMethod(models.TextChoices):
        CARD = "card", "Card"
        CASH = "cash", "Cash"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    reference = models.CharField(
        max_length=100, unique=True, default=generate_payment_reference
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
    )
    equipment_loan = models.ForeignKey(
        EquipmentLoan,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CARD
    )
    status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    paid_at = models.DateTimeField(blank=True, null=True)
    receipt_number = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.amount:.2f}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(booking__isnull=False, membership__isnull=True, equipment_loan__isnull=True)
                    | models.Q(booking__isnull=True, membership__isnull=False, equipment_loan__isnull=True)
                    | models.Q(booking__isnull=True, membership__isnull=True, equipment_loan__isnull=False)
                ),
                name='payment_exactly_one_target',
            ),
        ]


class Refund(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="refunds"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refunds")
    reason = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_refunds",
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund for {self.payment} - {self.status}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default="general")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    entity = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} {self.entity} {self.entity_id}"
