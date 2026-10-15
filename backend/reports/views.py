from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Booking, Membership, Payment, Refund, User


class OverviewReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        total_members = User.objects.filter(role=User.Role.MEMBER).count()
        active_memberships = Membership.objects.filter(status=Membership.Status.ACTIVE).count()
        total_bookings = Booking.objects.count()
        approved_bookings = Booking.objects.filter(status=Booking.Status.APPROVED).count()
        pending_refunds = Refund.objects.filter(status=Refund.Status.PENDING).count()
        total_revenue = (
            Payment.objects.filter(status=Payment.PaymentStatus.PAID).aggregate(
                total=Sum('amount')
            )['total']
            or 0
        )

        return Response(
            {
                'total_members': total_members,
                'active_memberships': active_memberships,
                'total_bookings': total_bookings,
                'approved_bookings': approved_bookings,
                'pending_refunds': pending_refunds,
                'total_revenue': float(total_revenue),
            }
        )
