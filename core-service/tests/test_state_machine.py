"""Unit tests for state machine service"""

import pytest

from app.services.state_machine import StateMachine


class TestMaterialRequestStateMachine:
    """Test Material Request state transitions"""

    def test_draft_to_submitted_is_valid(self):
        """Test that DRAFT -> SUBMITTED is a valid transition"""
        sm = StateMachine("MATERIAL_REQUEST")
        assert sm.can_transition("draft", "submitted") is True

    def test_draft_to_cancelled_is_valid(self):
        """Test that DRAFT -> CANCELLED is a valid transition"""
        sm = StateMachine("MATERIAL_REQUEST")
        assert sm.can_transition("draft", "cancelled") is True

    def test_submitted_to_partially_quoted_is_valid(self):
        """Test that SUBMITTED -> PARTIALLY_QUOTED is a valid transition"""
        sm = StateMachine("MATERIAL_REQUEST")
        assert sm.can_transition("submitted", "partially_quoted") is True

    def test_submitted_to_fully_quoted_is_valid(self):
        """Test that SUBMITTED -> FULLY_QUOTED is a valid transition"""
        sm = StateMachine("MATERIAL_REQUEST")
        assert sm.can_transition("submitted", "fully_quoted") is True

    def test_partially_quoted_to_fully_quoted_is_valid(self):
        """Test that PARTIALLY_QUOTED -> FULLY_QUOTED is a valid transition"""
        sm = StateMachine("MATERIAL_REQUEST")
        assert sm.can_transition("partially_quoted", "fully_quoted") is True

    def test_draft_to_fully_quoted_is_invalid(self):
        """Test that DRAFT -> FULLY_QUOTED is invalid"""
        sm = StateMachine("MATERIAL_REQUEST")
        assert sm.can_transition("draft", "fully_quoted") is False

    def test_fully_quoted_is_terminal(self):
        """Test that FULLY_QUOTED is a terminal state"""
        sm = StateMachine("MATERIAL_REQUEST")
        assert sm.is_terminal_state("fully_quoted") is True
        assert sm.can_transition("fully_quoted", "submitted") is False

    def test_cancelled_is_terminal(self):
        """Test that CANCELLED is a terminal state"""
        sm = StateMachine("MATERIAL_REQUEST")
        assert sm.is_terminal_state("cancelled") is True
        assert sm.can_transition("cancelled", "submitted") is False

    def test_validate_transition_raises_on_invalid(self):
        """Test that validate_transition raises ValueError on invalid transition"""
        sm = StateMachine("MATERIAL_REQUEST")
        with pytest.raises(ValueError, match="Invalid status transition"):
            sm.validate_transition("draft", "fully_quoted")

    def test_validate_transition_succeeds_on_valid(self):
        """Test that validate_transition succeeds on valid transition"""
        sm = StateMachine("MATERIAL_REQUEST")
        # Should not raise
        sm.validate_transition("draft", "submitted")

    def test_get_allowed_transitions_from_draft(self):
        """Test getting allowed transitions from DRAFT"""
        sm = StateMachine("MATERIAL_REQUEST")
        allowed = sm.get_allowed_transitions("draft")
        assert "submitted" in allowed
        assert "cancelled" in allowed
        assert len(allowed) == 2

    def test_get_allowed_transitions_from_terminal(self):
        """Test getting allowed transitions from terminal state"""
        sm = StateMachine("MATERIAL_REQUEST")
        allowed = sm.get_allowed_transitions("fully_quoted")
        assert len(allowed) == 0

    def test_validate_transition_from_terminal_state_raises_error(self):
        """Test that validate_transition raises ValueError when transitioning from terminal state"""
        sm = StateMachine("MATERIAL_REQUEST")
        with pytest.raises(ValueError, match="Cannot transition from terminal state"):
            sm.validate_transition("fully_quoted", "submitted")

    def test_validate_transition_from_cancelled_terminal_state_raises_error(self):
        """Test that validate_transition raises ValueError when transitioning from CANCELLED"""
        sm = StateMachine("MATERIAL_REQUEST")
        with pytest.raises(ValueError, match="Cannot transition from terminal state"):
            sm.validate_transition("cancelled", "draft")


class TestRFQStateMachine:
    """Test RFQ state transitions"""

    def test_draft_to_sent_is_valid(self):
        """Test that DRAFT -> SENT is a valid transition"""
        sm = StateMachine("RFQ")
        assert sm.can_transition("draft", "sent") is True

    def test_draft_to_closed_is_valid(self):
        """Test that DRAFT -> CLOSED is a valid transition"""
        sm = StateMachine("RFQ")
        assert sm.can_transition("draft", "closed") is True

    def test_sent_to_partially_responded_is_valid(self):
        """Test that SENT -> PARTIALLY_RESPONDED is a valid transition"""
        sm = StateMachine("RFQ")
        assert sm.can_transition("sent", "partially_responded") is True

    def test_sent_to_fully_responded_is_valid(self):
        """Test that SENT -> FULLY_RESPONDED is a valid transition"""
        sm = StateMachine("RFQ")
        assert sm.can_transition("sent", "fully_responded") is True

    def test_partially_responded_to_fully_responded_is_valid(self):
        """Test that PARTIALLY_RESPONDED -> FULLY_RESPONDED is a valid transition"""
        sm = StateMachine("RFQ")
        assert sm.can_transition("partially_responded", "fully_responded") is True

    def test_fully_responded_to_closed_is_valid(self):
        """Test that FULLY_RESPONDED -> CLOSED is a valid transition"""
        sm = StateMachine("RFQ")
        assert sm.can_transition("fully_responded", "closed") is True

    def test_draft_to_fully_responded_is_invalid(self):
        """Test that DRAFT -> FULLY_RESPONDED is invalid"""
        sm = StateMachine("RFQ")
        assert sm.can_transition("draft", "fully_responded") is False

    def test_closed_is_terminal(self):
        """Test that CLOSED is a terminal state"""
        sm = StateMachine("RFQ")
        assert sm.is_terminal_state("closed") is True
        assert sm.can_transition("closed", "sent") is False

    def test_get_allowed_transitions_from_sent(self):
        """Test getting allowed transitions from SENT"""
        sm = StateMachine("RFQ")
        allowed = sm.get_allowed_transitions("sent")
        assert "partially_responded" in allowed
        assert "fully_responded" in allowed
        assert "closed" in allowed
        assert len(allowed) == 3

    def test_validate_transition_from_closed_terminal_state_raises_error(self):
        """Test that validate_transition raises ValueError when transitioning from CLOSED"""
        sm = StateMachine("RFQ")
        with pytest.raises(ValueError, match="Cannot transition from terminal state"):
            sm.validate_transition("closed", "sent")


class TestPurchaseOrderStateMachine:
    """Test Purchase Order state transitions"""

    def test_draft_to_submitted_is_valid(self):
        """Test that DRAFT -> SUBMITTED is a valid transition"""
        sm = StateMachine("PURCHASE_ORDER")
        assert sm.can_transition("draft", "submitted") is True

    def test_draft_to_cancelled_is_valid(self):
        """Test that DRAFT -> CANCELLED is a valid transition"""
        sm = StateMachine("PURCHASE_ORDER")
        assert sm.can_transition("draft", "cancelled") is True

    def test_submitted_to_partially_received_is_valid(self):
        """Test that SUBMITTED -> PARTIALLY_RECEIVED is a valid transition"""
        sm = StateMachine("PURCHASE_ORDER")
        assert sm.can_transition("submitted", "partially_received") is True

    def test_submitted_to_fully_received_is_valid(self):
        """Test that SUBMITTED -> FULLY_RECEIVED is a valid transition"""
        sm = StateMachine("PURCHASE_ORDER")
        assert sm.can_transition("submitted", "fully_received") is True

    def test_partially_received_to_fully_received_is_valid(self):
        """Test that PARTIALLY_RECEIVED -> FULLY_RECEIVED is a valid transition"""
        sm = StateMachine("PURCHASE_ORDER")
        assert sm.can_transition("partially_received", "fully_received") is True

    def test_fully_received_to_closed_is_valid(self):
        """Test that FULLY_RECEIVED -> CLOSED is a valid transition"""
        sm = StateMachine("PURCHASE_ORDER")
        assert sm.can_transition("fully_received", "closed") is True

    def test_draft_to_fully_received_is_invalid(self):
        """Test that DRAFT -> FULLY_RECEIVED is invalid"""
        sm = StateMachine("PURCHASE_ORDER")
        assert sm.can_transition("draft", "fully_received") is False

    def test_submitted_to_closed_is_invalid(self):
        """Test that SUBMITTED -> CLOSED is invalid (must be FULLY_RECEIVED first)"""
        sm = StateMachine("PURCHASE_ORDER")
        assert sm.can_transition("submitted", "closed") is False

    def test_closed_is_terminal(self):
        """Test that CLOSED is a terminal state"""
        sm = StateMachine("PURCHASE_ORDER")
        assert sm.is_terminal_state("closed") is True
        assert sm.can_transition("closed", "submitted") is False

    def test_cancelled_is_terminal(self):
        """Test that CANCELLED is a terminal state"""
        sm = StateMachine("PURCHASE_ORDER")
        assert sm.is_terminal_state("cancelled") is True
        assert sm.can_transition("cancelled", "submitted") is False

    def test_get_allowed_transitions_from_submitted(self):
        """Test getting allowed transitions from SUBMITTED"""
        sm = StateMachine("PURCHASE_ORDER")
        allowed = sm.get_allowed_transitions("submitted")
        assert "partially_received" in allowed
        assert "fully_received" in allowed
        assert "cancelled" in allowed
        assert len(allowed) == 3

    def test_validate_transition_from_closed_terminal_state_raises_error(self):
        """Test that validate_transition raises ValueError when transitioning from CLOSED"""
        sm = StateMachine("PURCHASE_ORDER")
        with pytest.raises(ValueError, match="Cannot transition from terminal state"):
            sm.validate_transition("closed", "submitted")

    def test_validate_transition_from_cancelled_terminal_state_raises_error(self):
        """Test that validate_transition raises ValueError when transitioning from CANCELLED"""
        sm = StateMachine("PURCHASE_ORDER")
        with pytest.raises(ValueError, match="Cannot transition from terminal state"):
            sm.validate_transition("cancelled", "draft")


class TestStateMachineGeneral:
    """Test general state machine functionality"""

    def test_invalid_document_type_raises_error(self):
        """Test that invalid document type raises ValueError"""
        with pytest.raises(ValueError, match="Unknown document type"):
            StateMachine("INVALID_TYPE")

    def test_case_insensitive_status_matching(self):
        """Test that status matching is case-insensitive"""
        sm = StateMachine("MATERIAL_REQUEST")
        assert sm.can_transition("DRAFT", "SUBMITTED") is True
        assert sm.can_transition("Draft", "Submitted") is True
        assert sm.can_transition("draft", "submitted") is True

    def test_invalid_status_returns_false(self):
        """Test that invalid status values return False"""
        sm = StateMachine("MATERIAL_REQUEST")
        assert sm.can_transition("invalid_status", "submitted") is False
        assert sm.can_transition("draft", "invalid_status") is False

    def test_get_allowed_transitions_with_invalid_status(self):
        """Test that get_allowed_transitions returns empty set for invalid status"""
        sm = StateMachine("MATERIAL_REQUEST")
        allowed = sm.get_allowed_transitions("invalid_status")
        assert len(allowed) == 0
