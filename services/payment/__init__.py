"""Payment service package"""
from services.payment.lesson_ops import _LessonOpsMixin
from services.payment.bulk_balance import _BalanceMixin


class PaymentService(_LessonOpsMixin, _BalanceMixin):
    """Service for managing lesson payment tracking"""
    pass


__all__ = ['PaymentService']
