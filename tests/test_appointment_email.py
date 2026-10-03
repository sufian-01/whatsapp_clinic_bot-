import pytest
from app.tools.gmail import GmailTools
from app.services.crm_service import CrmService
from unittest.mock import MagicMock

def test_send_appointment_confirmation_email_valid():
    sender_mock = MagicMock()
    gmail = GmailTools(sender_mock)
    res = gmail.send_appointment_confirmation_email(
        "test@example.com",
        {"patient_name": "Test", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "token_no": "T1", "amount": "100", "payment_status": "Pending"},
        "Test Clinic",
        "123456"
    )
    assert res["success"] is True
    assert res["email_sent"] is True
    sender_mock.assert_called_once()

def test_send_appointment_confirmation_email_invalid():
    sender_mock = MagicMock()
    gmail = GmailTools(sender_mock)
    res = gmail.send_appointment_confirmation_email(
        "invalid_email",
        {},
        "Test Clinic",
        "123456"
    )
    assert res["success"] is False
    assert res["email_sent"] is False
    assert res.get("skipped") is True
    sender_mock.assert_not_called()

def test_send_appointment_confirmation_email_empty():
    sender_mock = MagicMock()
    gmail = GmailTools(sender_mock)
    res = gmail.send_appointment_confirmation_email(
        "",
        {},
        "Test Clinic",
        "123456"
    )
    assert res["success"] is False
    assert res["email_sent"] is False
    assert res.get("skipped") is True
    sender_mock.assert_not_called()

def test_send_appointment_confirmation_email_exception():
    def failing_sender(*args, **kwargs):
        raise Exception("SMTP error")
    gmail = GmailTools(failing_sender)
    res = gmail.send_appointment_confirmation_email(
        "test@example.com",
        {},
        "Test Clinic",
        "123456"
    )
    assert res["success"] is False
    assert res["email_sent"] is False
    assert res["error"] == "SMTP error"

def test_create_appointment_manual_with_email():
    gmail_mock = MagicMock()
    gmail_mock.send_appointment_confirmation_email.return_value = {"email_sent": True, "success": True}
    
    slots_mock = MagicMock()
    slots_mock.get_slot_by_id.return_value = {"Status": "Available", "Date": "2023-01-01", "Start Time": "10:00", "Doctor Name": "Doc"}
    slots_mock.book_slot.return_value = True
    
    patients_mock = MagicMock()
    patients_mock.generate_patient_id.return_value = {"patient_id": "P1"}
    patients_mock.generate_token.return_value = {"token_no": "T1"}
    
    crm = CrmService(slots_tools=slots_mock, patients_tools=patients_mock, gmail_tools=gmail_mock)
    
    res = crm.create_appointment_manual({
        "slot_id": "S1",
        "name": "Test User",
        "phone": "1234567890",
        "email": "test@example.com"
    })
    
    assert res["success"] is True
    assert res["email_result"]["email_sent"] is True
    gmail_mock.send_appointment_confirmation_email.assert_called_once()
    kwargs = gmail_mock.send_appointment_confirmation_email.call_args[1]
    assert kwargs["recipient"] == "test@example.com"

def test_create_appointment_manual_without_email():
    gmail_mock = MagicMock()
    slots_mock = MagicMock()
    slots_mock.get_slot_by_id.return_value = {"Status": "Available", "Date": "2023-01-01", "Start Time": "10:00", "Doctor Name": "Doc"}
    slots_mock.book_slot.return_value = True
    
    patients_mock = MagicMock()
    patients_mock.generate_patient_id.return_value = {"patient_id": "P1"}
    patients_mock.generate_token.return_value = {"token_no": "T1"}
    
    crm = CrmService(slots_tools=slots_mock, patients_tools=patients_mock, gmail_tools=gmail_mock)
    
    res = crm.create_appointment_manual({
        "slot_id": "S1",
        "name": "Test User",
        "phone": "1234567890",
        "email": ""
    })
    
    assert res["success"] is True
    assert res["email_result"]["skipped"] is True
    gmail_mock.send_appointment_confirmation_email.assert_not_called()

def test_create_appointment_manual_email_fails():
    gmail_mock = MagicMock()
    gmail_mock.send_appointment_confirmation_email.return_value = {"email_sent": False, "success": False, "error": "Failed"}
    
    slots_mock = MagicMock()
    slots_mock.get_slot_by_id.return_value = {"Status": "Available"}
    slots_mock.book_slot.return_value = True
    
    patients_mock = MagicMock()
    patients_mock.generate_patient_id.return_value = {"patient_id": "P1"}
    patients_mock.generate_token.return_value = {"token_no": "T1"}
    
    crm = CrmService(slots_tools=slots_mock, patients_tools=patients_mock, gmail_tools=gmail_mock)
    
    res = crm.create_appointment_manual({
        "slot_id": "S1",
        "name": "Test User",
        "phone": "1234567890",
        "email": "test@example.com"
    })
    
    assert res["success"] is True
    assert res["email_result"]["email_sent"] is False
