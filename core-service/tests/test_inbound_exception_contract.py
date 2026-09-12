"""Non-database contracts for inbound exception and staging behavior."""

from app.core.authorization import (
    INBOUND_EXCEPTION_CREATE,
    INBOUND_EXCEPTION_DISPOSE,
    INBOUND_EXCEPTION_READ,
    WMS_WORKER_PERMISSIONS,
)
from app.models.warehouse_location import (
    ReceivingConditionCode,
    ReceivingSlipItemFlag,
)
from app.schemas.inbound import EndSessionRequest
from app.services.inbound_exception_service import InboundExceptionService


def test_standard_wms_exception_flags_and_conditions_are_available():
    assert ReceivingSlipItemFlag.EXCESS.value == "excess"
    assert ReceivingSlipItemFlag.HOLD.value == "hold"
    assert ReceivingSlipItemFlag.QUARANTINE.value == "quarantine"
    assert ReceivingConditionCode.GOOD.value == "GOOD"
    assert ReceivingConditionCode.DAMAGED.value == "DAMAGED"
    assert ReceivingConditionCode.HOLD.value == "HOLD"


def test_handheld_end_session_contract_carries_reason_coded_exception():
    request = EndSessionRequest.model_validate(
        {
            "exceptions": [
                {
                    "serial_number": "IC-1001",
                    "classification": "damaged",
                    "reason_code": "DAMAGED",
                    "destination": "QUARANTINE",
                    "note": "Outer case split",
                }
            ]
        }
    )

    assert request.exceptions[0].serial_number == "IC-1001"
    assert request.exceptions[0].destination == "QUARANTINE"


def test_exception_permissions_separate_operator_classification_from_disposition():
    assert INBOUND_EXCEPTION_READ in WMS_WORKER_PERMISSIONS
    assert INBOUND_EXCEPTION_CREATE in WMS_WORKER_PERMISSIONS
    assert INBOUND_EXCEPTION_DISPOSE not in WMS_WORKER_PERMISSIONS


def test_exception_service_only_accepts_known_lifecycle_values():
    assert {"HOLD", "QUARANTINE"} == InboundExceptionService.DESTINATIONS
    assert "release_to_receiving" in InboundExceptionService.FINAL_DISPOSITIONS
    assert "move_to_hold" in InboundExceptionService.FINAL_DISPOSITIONS
    assert "move_to_quarantine" in InboundExceptionService.FINAL_DISPOSITIONS
