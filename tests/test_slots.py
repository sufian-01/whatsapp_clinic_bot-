import unittest

from app.tools.slots import SlotRepository


HEADERS = [["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"]]


class SlotTests(unittest.TestCase):
    def setUp(self):
        self.rows = HEADERS + [
            ["SLOT001", "D1", "Dr. Sana Khan", "2026-09-28", "16:00", "16:30", "Available", "", "", ""],
            ["SLOT002", "D1", "Dr. Sana Khan", "2026-09-28", "16:30", "17:00", "Booked", "PAT-1", "TKN-0001", "now"],
        ]

        def update(range_name, values):
            row_number = int(range_name.split("A", 1)[1].split(":", 1)[0])
            self.rows[row_number - 1] = values

        self.repository = SlotRepository(lambda: self.rows, update, "appointment_slots!A1:Z5000")

    def test_filters_available_and_booked_slots(self):
        self.assertEqual([slot["Slot ID"] for slot in self.repository.get_available_slots("Dr. Sana Khan", "2026-09-28")], ["SLOT001"])
        self.assertEqual([slot["Slot ID"] for slot in self.repository.get_booked_slots("Dr. Sana Khan", "2026-09-28")], ["SLOT002"])

    def test_booking_rechecks_and_prevents_double_booking(self):
        self.assertTrue(self.repository.book_slot("SLOT001", "PAT-2", "TKN-0002"))
        self.assertFalse(self.repository.book_slot("SLOT001", "PAT-3", "TKN-0003"))

    def test_missing_slot_cannot_be_booked(self):
        self.assertFalse(self.repository.book_slot("MISSING", "PAT-2", "TKN-0002"))