"""Repositories package."""

from .tenant_scoped import (
    TenantAppointmentRepository,
    TenantAuditRepository,
    TenantDoctorRepository,
    TenantInvoiceRepository,
    TenantPatientRepository,
    TenantPaymentRepository,
    TenantPrescriptionRepository,
    TenantScopedRepository,
    TenantSlotRepository,
)

__all__ = [
    "TenantAppointmentRepository",
    "TenantAuditRepository",
    "TenantDoctorRepository",
    "TenantInvoiceRepository",
    "TenantPatientRepository",
    "TenantPaymentRepository",
    "TenantPrescriptionRepository",
    "TenantScopedRepository",
    "TenantSlotRepository",
]

