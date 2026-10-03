"""Structured Gmail invoice delivery tool using the existing Gmail foundation."""


class GmailTools:
    def __init__(self, sender) -> None:
        self._sender = sender

    def send_invoice_email(self, recipient: str, invoice_number: str, subject: str, body: str, file_path: str) -> dict:
        try:
            self._sender(recipient, subject, body, file_path)
            return {"success": True, "email_sent": True, "recipient": recipient, "invoice_number": invoice_number}
        except Exception:
            return {"success": False, "email_sent": False, "recipient": recipient, "invoice_number": invoice_number, "error_code": "GMAIL_SEND_FAILED"}

    def send_appointment_confirmation_email(self, recipient: str, appointment_data: dict, clinic_name: str, support_phone: str) -> dict:
        import re
        if not recipient or not re.match(r".+@.+\..+", recipient):
            return {"success": False, "email_sent": False, "skipped": True, "reason": "No valid email"}
        
        try:
            subject = f"Appointment Confirmation - {clinic_name}"
            
            patient_name = appointment_data.get("patient_name", "")
            doctor = appointment_data.get("doctor", "")
            spec = appointment_data.get("specialization", "")
            date = appointment_data.get("date", "")
            time = appointment_data.get("time", "")
            token = appointment_data.get("token_no", "")
            amount = appointment_data.get("amount", "")
            payment_status = appointment_data.get("payment_status", "")
            
            doc_display = f"Dr. {doctor}"
            if spec:
                doc_display += f" ({spec})"
                
            body = f"""
            <html>
                <body>
                    <h2>Appointment Confirmation</h2>
                    <p>Dear {patient_name},</p>
                    <p>Your appointment at <strong>{clinic_name}</strong> has been confirmed.</p>
                    <h3>Details:</h3>
                    <ul>
                        <li><strong>Doctor:</strong> {doc_display}</li>
                        <li><strong>Date:</strong> {date}</li>
                        <li><strong>Time:</strong> {time}</li>
                        <li><strong>Booking ID/Token:</strong> {token}</li>
                        <li><strong>Consultation Fee:</strong> Rs.{amount}</li>
                        <li><strong>Payment Status:</strong> {payment_status}</li>
                    </ul>
                    <p>If you have any questions, please contact us at {support_phone}.</p>
                    <br/>
                    <p>Best Regards,</p>
                    <p><strong>{clinic_name}</strong></p>
                </body>
            </html>
            """
            self._sender(recipient, subject, body, None)
            return {"success": True, "email_sent": True, "recipient": recipient, "error": None}
        except Exception as e:
            return {"success": False, "email_sent": False, "recipient": recipient, "error": str(e)}

    def send_prescription_email(
        self,
        recipient: str,
        prescription_data: dict,
        clinic_name: str,
        support_phone: str,
        pdf_path: str,
    ) -> dict:
        import re
        if not recipient or not re.match(r".+@.+\..+", recipient):
            return {"success": False, "email_sent": False, "skipped": True, "reason": "No valid email"}

        try:
            patient_name = prescription_data.get("patient_name", "Patient")
            doctor_name = prescription_data.get("doctor_name", "Doctor")
            rx_id = prescription_data.get("prescription_id", "")
            date = prescription_data.get("date", "")
            doc_display = f"Dr. {doctor_name}" if not str(doctor_name).startswith("Dr.") else doctor_name

            subject = f"Your Medical Prescription ({rx_id}) - {clinic_name}"
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #1e293b; line-height: 1.6;">
                    <h2 style="color: #1e3a8a;">{clinic_name} — Medical Prescription</h2>
                    <p>Dear {patient_name},</p>
                    <p>Please find attached your digital prescription issued by <strong>{doc_display}</strong> on {date}.</p>
                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; margin: 16px 0;">
                        <p style="margin: 4px 0;"><strong>Prescription ID:</strong> {rx_id}</p>
                        <p style="margin: 4px 0;"><strong>Physician:</strong> {doc_display}</p>
                        <p style="margin: 4px 0;"><strong>Consultation Date:</strong> {date}</p>
                    </div>
                    <p>Please review the attached PDF document for full dosage instructions, medication schedule, and follow-up advice.</p>
                    <p>For any queries or medical concerns, please contact the clinic at {support_phone}.</p>
                    <br/>
                    <p>Warm regards,<br/><strong>{clinic_name} Healthcare Team</strong></p>
                </body>
            </html>
            """
            self._sender(recipient, subject, body, pdf_path)
            return {"success": True, "email_sent": True, "recipient": recipient, "error": None}
        except Exception as e:
            return {"success": False, "email_sent": False, "recipient": recipient, "error": str(e)}