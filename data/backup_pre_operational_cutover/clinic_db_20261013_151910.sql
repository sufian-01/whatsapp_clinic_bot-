--
-- PostgreSQL database dump
--

\restrict QGgvjgK4YpOiuX7d7yZbTYMWQTWWiTLgeXvQ9eZno2sQ4aqSVXhmXrKEx95aUPO

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS fk_users_tenant_id_clinics;
ALTER TABLE IF EXISTS ONLY public.prescriptions DROP CONSTRAINT IF EXISTS fk_prescriptions_tenant_id_clinics;
ALTER TABLE IF EXISTS ONLY public.prescriptions DROP CONSTRAINT IF EXISTS fk_prescriptions_patient_id_patients;
ALTER TABLE IF EXISTS ONLY public.prescriptions DROP CONSTRAINT IF EXISTS fk_prescriptions_doctor_id_doctors;
ALTER TABLE IF EXISTS ONLY public.prescriptions DROP CONSTRAINT IF EXISTS fk_prescriptions_appointment_id_appointments;
ALTER TABLE IF EXISTS ONLY public.prescription_items DROP CONSTRAINT IF EXISTS fk_prescription_items_prescription_id_prescriptions;
ALTER TABLE IF EXISTS ONLY public.payments DROP CONSTRAINT IF EXISTS fk_payments_tenant_id_clinics;
ALTER TABLE IF EXISTS ONLY public.payments DROP CONSTRAINT IF EXISTS fk_payments_invoice_id_invoices;
ALTER TABLE IF EXISTS ONLY public.payments DROP CONSTRAINT IF EXISTS fk_payments_appointment_id_appointments;
ALTER TABLE IF EXISTS ONLY public.patients DROP CONSTRAINT IF EXISTS fk_patients_tenant_id_clinics;
ALTER TABLE IF EXISTS ONLY public.invoices DROP CONSTRAINT IF EXISTS fk_invoices_tenant_id_clinics;
ALTER TABLE IF EXISTS ONLY public.invoices DROP CONSTRAINT IF EXISTS fk_invoices_patient_id_patients;
ALTER TABLE IF EXISTS ONLY public.invoices DROP CONSTRAINT IF EXISTS fk_invoices_appointment_id_appointments;
ALTER TABLE IF EXISTS ONLY public.doctors DROP CONSTRAINT IF EXISTS fk_doctors_tenant_id_clinics;
ALTER TABLE IF EXISTS ONLY public.audit_logs DROP CONSTRAINT IF EXISTS fk_audit_logs_tenant_id_clinics;
ALTER TABLE IF EXISTS ONLY public.appointments DROP CONSTRAINT IF EXISTS fk_appointments_tenant_id_clinics;
ALTER TABLE IF EXISTS ONLY public.appointments DROP CONSTRAINT IF EXISTS fk_appointments_slot_id_appointment_slots;
ALTER TABLE IF EXISTS ONLY public.appointments DROP CONSTRAINT IF EXISTS fk_appointments_patient_id_patients;
ALTER TABLE IF EXISTS ONLY public.appointments DROP CONSTRAINT IF EXISTS fk_appointments_doctor_id_doctors;
ALTER TABLE IF EXISTS ONLY public.appointment_slots DROP CONSTRAINT IF EXISTS fk_appointment_slots_tenant_id_clinics;
ALTER TABLE IF EXISTS ONLY public.appointment_slots DROP CONSTRAINT IF EXISTS fk_appointment_slots_doctor_id_doctors;
DROP INDEX IF EXISTS public.ix_users_username;
DROP INDEX IF EXISTS public.ix_users_tenant_id;
DROP INDEX IF EXISTS public.ix_users_status;
DROP INDEX IF EXISTS public.ix_users_role;
DROP INDEX IF EXISTS public.ix_users_email;
DROP INDEX IF EXISTS public.ix_users_doctor_id;
DROP INDEX IF EXISTS public.ix_user_tenant_role;
DROP INDEX IF EXISTS public.ix_slot_tenant_date_status;
DROP INDEX IF EXISTS public.ix_prescriptions_tenant_id;
DROP INDEX IF EXISTS public.ix_prescriptions_status;
DROP INDEX IF EXISTS public.ix_prescriptions_prescription_id;
DROP INDEX IF EXISTS public.ix_prescriptions_patient_id;
DROP INDEX IF EXISTS public.ix_prescriptions_doctor_id;
DROP INDEX IF EXISTS public.ix_prescriptions_appointment_id;
DROP INDEX IF EXISTS public.ix_prescription_tenant_date_status;
DROP INDEX IF EXISTS public.ix_prescription_items_prescription_id;
DROP INDEX IF EXISTS public.ix_payments_transaction_reference;
DROP INDEX IF EXISTS public.ix_payments_tenant_id;
DROP INDEX IF EXISTS public.ix_payments_payment_status;
DROP INDEX IF EXISTS public.ix_payments_payment_id;
DROP INDEX IF EXISTS public.ix_payments_invoice_id;
DROP INDEX IF EXISTS public.ix_payments_appointment_id;
DROP INDEX IF EXISTS public.ix_payment_tenant_status;
DROP INDEX IF EXISTS public.ix_patients_tenant_id;
DROP INDEX IF EXISTS public.ix_patients_phone;
DROP INDEX IF EXISTS public.ix_patients_patient_id;
DROP INDEX IF EXISTS public.ix_patients_name;
DROP INDEX IF EXISTS public.ix_patients_email;
DROP INDEX IF EXISTS public.ix_patient_tenant_phone;
DROP INDEX IF EXISTS public.ix_patient_tenant_name;
DROP INDEX IF EXISTS public.ix_invoices_tenant_id;
DROP INDEX IF EXISTS public.ix_invoices_payment_status;
DROP INDEX IF EXISTS public.ix_invoices_patient_id;
DROP INDEX IF EXISTS public.ix_invoices_invoice_number;
DROP INDEX IF EXISTS public.ix_invoices_appointment_id;
DROP INDEX IF EXISTS public.ix_invoice_tenant_status;
DROP INDEX IF EXISTS public.ix_doctors_tenant_id;
DROP INDEX IF EXISTS public.ix_doctors_status;
DROP INDEX IF EXISTS public.ix_doctors_specialization;
DROP INDEX IF EXISTS public.ix_doctors_name;
DROP INDEX IF EXISTS public.ix_doctors_doctor_id;
DROP INDEX IF EXISTS public.ix_doctor_tenant_specialization;
DROP INDEX IF EXISTS public.ix_doctor_tenant_name;
DROP INDEX IF EXISTS public.ix_clinics_status;
DROP INDEX IF EXISTS public.ix_clinics_name;
DROP INDEX IF EXISTS public.ix_clinics_is_active;
DROP INDEX IF EXISTS public.ix_audit_tenant_entity;
DROP INDEX IF EXISTS public.ix_audit_tenant_action;
DROP INDEX IF EXISTS public.ix_audit_logs_user;
DROP INDEX IF EXISTS public.ix_audit_logs_timestamp;
DROP INDEX IF EXISTS public.ix_audit_logs_tenant_id;
DROP INDEX IF EXISTS public.ix_audit_logs_entity_type;
DROP INDEX IF EXISTS public.ix_audit_logs_entity_id;
DROP INDEX IF EXISTS public.ix_audit_logs_audit_id;
DROP INDEX IF EXISTS public.ix_audit_logs_action;
DROP INDEX IF EXISTS public.ix_appointments_token_no;
DROP INDEX IF EXISTS public.ix_appointments_tenant_id;
DROP INDEX IF EXISTS public.ix_appointments_slot_id;
DROP INDEX IF EXISTS public.ix_appointments_payment_status;
DROP INDEX IF EXISTS public.ix_appointments_patient_id;
DROP INDEX IF EXISTS public.ix_appointments_doctor_id;
DROP INDEX IF EXISTS public.ix_appointments_booking_status;
DROP INDEX IF EXISTS public.ix_appointments_appointment_date;
DROP INDEX IF EXISTS public.ix_appointment_tenant_date_status;
DROP INDEX IF EXISTS public.ix_appointment_slots_tenant_id;
DROP INDEX IF EXISTS public.ix_appointment_slots_status;
DROP INDEX IF EXISTS public.ix_appointment_slots_start_time;
DROP INDEX IF EXISTS public.ix_appointment_slots_slot_id;
DROP INDEX IF EXISTS public.ix_appointment_slots_doctor_id;
DROP INDEX IF EXISTS public.ix_appointment_slots_date;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS uq_user_tenant_username;
ALTER TABLE IF EXISTS ONLY public.appointment_slots DROP CONSTRAINT IF EXISTS uq_slot_tenant_slot_id;
ALTER TABLE IF EXISTS ONLY public.appointment_slots DROP CONSTRAINT IF EXISTS uq_slot_doctor_date_start_time;
ALTER TABLE IF EXISTS ONLY public.prescriptions DROP CONSTRAINT IF EXISTS uq_prescription_tenant_rx_id;
ALTER TABLE IF EXISTS ONLY public.payments DROP CONSTRAINT IF EXISTS uq_payment_tenant_payment_id;
ALTER TABLE IF EXISTS ONLY public.patients DROP CONSTRAINT IF EXISTS uq_patient_tenant_patient_id;
ALTER TABLE IF EXISTS ONLY public.invoices DROP CONSTRAINT IF EXISTS uq_invoice_tenant_inv_no;
ALTER TABLE IF EXISTS ONLY public.doctors DROP CONSTRAINT IF EXISTS uq_doctor_tenant_doctor_id;
ALTER TABLE IF EXISTS ONLY public.audit_logs DROP CONSTRAINT IF EXISTS uq_audit_tenant_audit_id;
ALTER TABLE IF EXISTS ONLY public.appointments DROP CONSTRAINT IF EXISTS uq_appointment_tenant_token_no;
ALTER TABLE IF EXISTS ONLY public.appointments DROP CONSTRAINT IF EXISTS uq_appointment_doctor_datetime;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS pk_users;
ALTER TABLE IF EXISTS ONLY public.prescriptions DROP CONSTRAINT IF EXISTS pk_prescriptions;
ALTER TABLE IF EXISTS ONLY public.prescription_items DROP CONSTRAINT IF EXISTS pk_prescription_items;
ALTER TABLE IF EXISTS ONLY public.payments DROP CONSTRAINT IF EXISTS pk_payments;
ALTER TABLE IF EXISTS ONLY public.patients DROP CONSTRAINT IF EXISTS pk_patients;
ALTER TABLE IF EXISTS ONLY public.invoices DROP CONSTRAINT IF EXISTS pk_invoices;
ALTER TABLE IF EXISTS ONLY public.doctors DROP CONSTRAINT IF EXISTS pk_doctors;
ALTER TABLE IF EXISTS ONLY public.clinics DROP CONSTRAINT IF EXISTS pk_clinics;
ALTER TABLE IF EXISTS ONLY public.audit_logs DROP CONSTRAINT IF EXISTS pk_audit_logs;
ALTER TABLE IF EXISTS ONLY public.appointments DROP CONSTRAINT IF EXISTS pk_appointments;
ALTER TABLE IF EXISTS ONLY public.appointment_slots DROP CONSTRAINT IF EXISTS pk_appointment_slots;
ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;
DROP TABLE IF EXISTS public.users;
DROP TABLE IF EXISTS public.prescriptions;
DROP TABLE IF EXISTS public.prescription_items;
DROP TABLE IF EXISTS public.payments;
DROP TABLE IF EXISTS public.patients;
DROP TABLE IF EXISTS public.invoices;
DROP TABLE IF EXISTS public.doctors;
DROP TABLE IF EXISTS public.clinics;
DROP TABLE IF EXISTS public.audit_logs;
DROP TABLE IF EXISTS public.appointments;
DROP TABLE IF EXISTS public.appointment_slots;
DROP TABLE IF EXISTS public.alembic_version;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: appointment_slots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.appointment_slots (
    slot_id character varying(50) NOT NULL,
    doctor_id character varying(36) NOT NULL,
    date character varying(20) NOT NULL,
    start_time character varying(20) NOT NULL,
    end_time character varying(20) NOT NULL,
    status character varying(50) NOT NULL,
    locked_by character varying(100),
    locked_at timestamp with time zone,
    id character varying(36) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    tenant_id character varying(36)
);


ALTER TABLE public.appointment_slots OWNER TO postgres;

--
-- Name: appointments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.appointments (
    token_no character varying(50) NOT NULL,
    patient_id character varying(36) NOT NULL,
    doctor_id character varying(36) NOT NULL,
    slot_id character varying(36),
    appointment_date character varying(20) NOT NULL,
    appointment_time character varying(20) NOT NULL,
    amount character varying(20) NOT NULL,
    payment_method character varying(50) NOT NULL,
    payment_status character varying(50) NOT NULL,
    booking_status character varying(50) NOT NULL,
    notes text,
    id character varying(36) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    tenant_id character varying(36)
);


ALTER TABLE public.appointments OWNER TO postgres;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_logs (
    audit_id character varying(50) NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    "user" character varying(100) NOT NULL,
    action character varying(100) NOT NULL,
    entity_type character varying(100) NOT NULL,
    entity_id character varying(100) NOT NULL,
    details json,
    ip_address character varying(50),
    user_agent character varying(255),
    id character varying(36) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    tenant_id character varying(36)
);


ALTER TABLE public.audit_logs OWNER TO postgres;

--
-- Name: clinics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.clinics (
    name character varying(255) NOT NULL,
    legal_name character varying(255),
    phone character varying(50),
    email character varying(255),
    address text,
    timezone character varying(50) NOT NULL,
    currency character varying(10) NOT NULL,
    upi_id character varying(100),
    is_active boolean NOT NULL,
    id character varying(36) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    logo character varying(500),
    website character varying(255),
    status character varying(50) NOT NULL,
    working_days character varying(255),
    working_hours character varying(100),
    appointment_duration integer NOT NULL,
    booking_settings text,
    rag_config_status character varying(50) NOT NULL,
    channel_config_status character varying(50) NOT NULL
);


ALTER TABLE public.clinics OWNER TO postgres;

--
-- Name: doctors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.doctors (
    doctor_id character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    specialization character varying(255) NOT NULL,
    qualification character varying(255),
    registration_no character varying(100),
    phone character varying(50),
    email character varying(255),
    available_days character varying(255),
    start_time character varying(20),
    end_time character varying(20),
    consultation_fee character varying(20) NOT NULL,
    status character varying(50) NOT NULL,
    id character varying(36) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    tenant_id character varying(36)
);


ALTER TABLE public.doctors OWNER TO postgres;

--
-- Name: invoices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invoices (
    invoice_number character varying(50) NOT NULL,
    appointment_id character varying(36),
    patient_id character varying(36) NOT NULL,
    amount character varying(20) NOT NULL,
    payment_method character varying(50) NOT NULL,
    payment_status character varying(50) NOT NULL,
    upi_id character varying(100),
    qr_path character varying(500),
    pdf_path character varying(500),
    issued_date character varying(20),
    notes text,
    id character varying(36) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    tenant_id character varying(36)
);


ALTER TABLE public.invoices OWNER TO postgres;

--
-- Name: patients; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.patients (
    patient_id character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    phone character varying(50) NOT NULL,
    email character varying(255),
    age character varying(10),
    gender character varying(20),
    address text,
    medical_history text,
    id character varying(36) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    tenant_id character varying(36)
);


ALTER TABLE public.patients OWNER TO postgres;

--
-- Name: payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payments (
    payment_id character varying(50) NOT NULL,
    appointment_id character varying(36),
    invoice_id character varying(36),
    amount character varying(20) NOT NULL,
    currency character varying(10) NOT NULL,
    payment_method character varying(50) NOT NULL,
    payment_status character varying(50) NOT NULL,
    transaction_reference character varying(100),
    gateway character varying(50),
    gateway_payload json,
    paid_at timestamp with time zone,
    id character varying(36) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    tenant_id character varying(36)
);


ALTER TABLE public.payments OWNER TO postgres;

--
-- Name: prescription_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prescription_items (
    prescription_id character varying(36) NOT NULL,
    order_index integer NOT NULL,
    name character varying(255) NOT NULL,
    strength character varying(100),
    dosage character varying(100),
    frequency character varying(100),
    duration character varying(100),
    instructions text,
    id character varying(36) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.prescription_items OWNER TO postgres;

--
-- Name: prescriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prescriptions (
    prescription_id character varying(50) NOT NULL,
    patient_id character varying(36) NOT NULL,
    doctor_id character varying(36) NOT NULL,
    appointment_id character varying(36),
    date character varying(20) NOT NULL,
    version integer NOT NULL,
    status character varying(50) NOT NULL,
    chief_complaints text,
    diagnosis text,
    symptoms text,
    vitals json,
    clinical_notes text,
    tests_advised text,
    advice text,
    follow_up_date character varying(20),
    created_by character varying(100),
    updated_by character varying(100),
    finalized_at timestamp with time zone,
    version_history json,
    email_delivery json,
    pdf_path character varying(500),
    id character varying(36) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    tenant_id character varying(36)
);


ALTER TABLE public.prescriptions OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    username character varying(100) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(50) NOT NULL,
    doctor_id character varying(50),
    full_name character varying(255),
    email character varying(255),
    phone character varying(50),
    status character varying(50) NOT NULL,
    must_change_password boolean NOT NULL,
    last_login timestamp with time zone,
    id character varying(36) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    tenant_id character varying(36)
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
7d231a392105
\.


--
-- Data for Name: appointment_slots; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.appointment_slots (slot_id, doctor_id, date, start_time, end_time, status, locked_by, locked_at, id, created_at, updated_at, tenant_id) FROM stdin;
SLOT001	681ed33150b04917afc9dbd3282476f4	2026-09-28	10:00	10:30	booked	\N	\N	a034434a5bbf4253877e4511fe2595c6	2026-10-13 16:54:45.955454+05:30	2026-10-13 16:54:45.955454+05:30	default
SLOT002	681ed33150b04917afc9dbd3282476f4	2026-09-28	10:30	11:00	available	\N	\N	5ae0d87fc421416c81f021e116b6ee3b	2026-10-13 16:54:45.959523+05:30	2026-10-13 16:54:45.959523+05:30	default
SLOT003	f8775846cbdd471c9f14ff2eafa73d0d	2026-09-29	11:00	12:00	booked	\N	\N	0a63411ef217412bb605fd9487aae95e	2026-10-13 16:54:45.962843+05:30	2026-10-13 16:54:45.962843+05:30	default
SLOT004	681ed33150b04917afc9dbd3282476f4	2026-09-28	11:00	11:30	available	\N	\N	590bd4918af24e909ae5d0834a693b0e	2026-10-13 16:54:45.964883+05:30	2026-10-13 16:54:45.964883+05:30	default
SLOT005	681ed33150b04917afc9dbd3282476f4	2026-09-28	11:30	12:00	available	\N	\N	c4c6191d72304e19a015ba8fd8f04800	2026-10-13 16:54:45.966892+05:30	2026-10-13 16:54:45.966892+05:30	default
SLOT006	b926588a9dde4080a4b974137742b6c6	2026-09-29	16:00	16:30	available	\N	\N	04c7f3623f664382b559342029d0638d	2026-10-13 16:54:45.970368+05:30	2026-10-13 16:54:45.970368+05:30	default
SLOT007	b926588a9dde4080a4b974137742b6c6	2026-09-29	16:30	17:00	available	\N	\N	7d11eed1e5874c44b1c7fa851ace0148	2026-10-13 16:54:45.973582+05:30	2026-10-13 16:54:45.973582+05:30	default
SLOT008	f8775846cbdd471c9f14ff2eafa73d0d	2026-09-29	12:00	12:30	booked	\N	\N	f30a13698c6a46e3baf8c3db03971ca7	2026-10-13 16:54:45.975332+05:30	2026-10-13 16:54:45.975332+05:30	default
SLOT009	f8775846cbdd471c9f14ff2eafa73d0d	2026-09-29	12:30	13:00	booked	\N	\N	8dcf0493eae34bf18a541d6bb2d32ccc	2026-10-13 16:54:45.975332+05:30	2026-10-13 16:54:45.975332+05:30	default
SLOT010	fcd3cc09273a43978630e70cbc468926	2026-09-30	11:00	11:30	available	\N	\N	ec229e9f35d24348b78ae56d92d7dbb2	2026-10-13 16:54:45.975332+05:30	2026-10-13 16:54:45.975332+05:30	default
SLOT011	fcd3cc09273a43978630e70cbc468926	2026-09-30	11:30	12:00	available	\N	\N	89e2983cd5174253ac54eb5bd11518de	2026-10-13 16:54:45.980349+05:30	2026-10-13 16:54:45.980349+05:30	default
SLOT012	36240799cd7d4ae8b01d8902c3ddeb44	2026-10-01	10:00	10:30	available	\N	\N	ef643476243d4a17921259f28d50a96f	2026-10-13 16:54:45.981855+05:30	2026-10-13 16:54:45.981855+05:30	default
SLOT013	36240799cd7d4ae8b01d8902c3ddeb44	2026-10-01	10:30	11:00	available	\N	\N	40657c7516b3484b83402afa62c436dc	2026-10-13 16:54:45.984167+05:30	2026-10-13 16:54:45.984167+05:30	default
SLOT014	a3cd5362ce0b422ba6316eb011e6c28a	2026-10-01	15:00	15:30	available	\N	\N	9f18187afc3944a7bf59b8a55852a823	2026-10-13 16:54:45.98512+05:30	2026-10-13 16:54:45.98512+05:30	default
SLOT015	a3cd5362ce0b422ba6316eb011e6c28a	2026-10-01	15:30	16:00	available	\N	\N	65f117a9aa9e4a15bf5896f98f93105a	2026-10-13 16:54:45.98512+05:30	2026-10-13 16:54:45.98512+05:30	default
SLOT016	ab109a0898ce432ab32d00ebfb1d4ec6	2026-10-02	16:00	16:30	booked	\N	\N	392fce0824e94195b22e111615da03a5	2026-10-13 16:54:45.98512+05:30	2026-10-13 16:54:45.98512+05:30	default
SLOT017	ab109a0898ce432ab32d00ebfb1d4ec6	2026-10-02	16:30	17:00	available	\N	\N	a286860f0ce74faf92c1673724072ab9	2026-10-13 16:54:45.98512+05:30	2026-10-13 16:54:45.98512+05:30	default
SLOT018	4fc893efa2474b84be68de115c27e59a	2026-10-03	10:00	10:30	booked	\N	\N	d9bf21bbb12442f69e9a8a6d9187f37f	2026-10-13 16:54:45.98512+05:30	2026-10-13 16:54:45.98512+05:30	default
SLOT019	4fc893efa2474b84be68de115c27e59a	2026-10-03	10:30	11:00	booked	\N	\N	c31b635310d44acebdd56d461dee3547	2026-10-13 16:54:45.98512+05:30	2026-10-13 16:54:45.98512+05:30	default
S1	f8775846cbdd471c9f14ff2eafa73d0d	2026-10-05	10:00 AM	10:30 AM	booked	\N	\N	438b42b2d0d74cc9b990e810ce7e3131	2026-10-13 16:54:45.995981+05:30	2026-10-13 16:54:45.995981+05:30	default
S2	f8775846cbdd471c9f14ff2eafa73d0d	2026-10-06	10:00 AM	10:30 AM	booked	\N	\N	be248bb4b88e4705968c1cb687bbec19	2026-10-13 16:54:45.995981+05:30	2026-10-13 16:54:45.995981+05:30	default
\.


--
-- Data for Name: appointments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.appointments (token_no, patient_id, doctor_id, slot_id, appointment_date, appointment_time, amount, payment_method, payment_status, booking_status, notes, id, created_at, updated_at, tenant_id) FROM stdin;
TKN-0001	c66b44b822c246f5b19cc501c58bb408	681ed33150b04917afc9dbd3282476f4	a034434a5bbf4253877e4511fe2595c6	2026-09-28	10:00	500	Offline	Pending	Confirmed	\N	b8c9eb02c78845ab9b64695e621fd9d9	2026-10-13 16:54:46.453361+05:30	2026-10-13 16:54:46.453361+05:30	default
TKN-0002	8541e731df1a4a35b181c3f286742548	f8775846cbdd471c9f14ff2eafa73d0d	0a63411ef217412bb605fd9487aae95e	2026-09-29	11:00	900`	Offline	Paid	Confirmed	\N	c0423602d52d4931af3e8874fe3630e7	2026-10-13 16:54:46.460361+05:30	2026-10-13 16:54:46.460361+05:30	default
TKN-0003	4bbfa767f0c14855a7c0fc98c5475011	f8775846cbdd471c9f14ff2eafa73d0d	8dcf0493eae34bf18a541d6bb2d32ccc	2026-09-29	12:30	900	Offline	Pending	Confirmed	\N	2fc75850b7534c338d3bde8932ea2890	2026-10-13 16:54:46.464001+05:30	2026-10-13 16:54:46.464001+05:30	default
TKN-0004	e97af421901648c59e1c3d6c012b61c0	f8775846cbdd471c9f14ff2eafa73d0d	f30a13698c6a46e3baf8c3db03971ca7	2026-09-29	12:00	900	Offline	Pending	Confirmed	\N	43636956d8074299a2c0750ecd634919	2026-10-13 16:54:46.469549+05:30	2026-10-13 16:54:46.469549+05:30	default
TKN-0005	bb49d70c7cf44b7fbf5cfc08d87a580e	ab109a0898ce432ab32d00ebfb1d4ec6	392fce0824e94195b22e111615da03a5	2026-10-02	16:00	1200	Offline	Pending	Completed	\N	3aeb839b7ec54859bbe6e2a7f41deadd	2026-10-13 16:54:46.476575+05:30	2026-10-13 16:54:46.476575+05:30	default
TKN-0006	7474750da73649adaeb0d429c9e71a3f	4fc893efa2474b84be68de115c27e59a	d9bf21bbb12442f69e9a8a6d9187f37f	2026-10-03	10:00	800	Offline	Paid	Confirmed	\N	4819b8dd8aa246449f8a1cf62b98fdbe	2026-10-13 16:54:46.476575+05:30	2026-10-13 16:54:46.476575+05:30	default
TKN-0007	ccd2911b8aec42e198d9e993ef6a9aef	4fc893efa2474b84be68de115c27e59a	\N	2026-10-03	10:00+1	800	Offline	Paid	Confirmed	\N	9bc61da881d14db6b51233c52a7e1c3a	2026-10-13 16:54:46.4876+05:30	2026-10-13 16:54:46.4876+05:30	default
TKN-0008	871d42c48cb64560b6d4e94d9fd3f88d	4fc893efa2474b84be68de115c27e59a	c31b635310d44acebdd56d461dee3547	2026-10-03	10:30	800	Offline	Paid	Confirmed	\N	ddb73a38b670463bbde4ba503f5561d2	2026-10-13 16:54:46.496009+05:30	2026-10-13 16:54:46.496009+05:30	default
TKN-0009	79b9ffffbd3049e8904073001a1741fb	f8775846cbdd471c9f14ff2eafa73d0d	438b42b2d0d74cc9b990e810ce7e3131	2026-10-05	10:00 AM	900	Cash	Paid	Confirmed	\N	a710591788dd41bc803282587955bacb	2026-10-13 16:54:46.502897+05:30	2026-10-13 16:54:46.502897+05:30	default
TKN-0010	2bd918c7687b4692a1e4cc5b775de732	f8775846cbdd471c9f14ff2eafa73d0d	be248bb4b88e4705968c1cb687bbec19	2026-10-06	10:00 AM	900	Cash	Paid	Confirmed	\N	5c19c289b25c41d4a729e017f1cfe66a	2026-10-13 16:54:46.506533+05:30	2026-10-13 16:54:46.506533+05:30	default
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.audit_logs (audit_id, "timestamp", "user", action, entity_type, entity_id, details, ip_address, user_agent, id, created_at, updated_at, tenant_id) FROM stdin;
AUD-B75CDDB0E3A4	2026-10-02 14:40:06.576961+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	621ecc1e09ba4d6890c36da1f8b40e9f	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-5F066FA86226	2026-10-02 14:40:07.143946+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	82ee45d098ca49179b3d9b39e0f53dc8	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-BBBE01D4629E	2026-10-02 14:40:07.211168+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	3b16617d210e45dc99867077efba0166	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-FBE19FBDEE2A	2026-10-02 14:40:07.260298+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	28e9835561d64f9a939755f1bef21be7	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-F434890737C5	2026-10-02 14:40:07.3765+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	2c4dac8d980f4062bc52d5ef913428a0	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-D0977396D1A6	2026-10-02 14:40:07.576381+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	289ff8005f3649f1846a7af2097dc720	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-076F142BFBAF	2026-10-02 14:40:07.659894+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	e4331c30c8dc46309b9e82f6721f0b6e	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-012530EC3A55	2026-10-02 14:40:09.225868+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	10eb0858fed84f8d81ce457fabe543c1	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-6EB7FC9CCC21	2026-10-02 14:40:09.259124+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	801a9994cc114366b9da70913304d3b2	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-15C514E5FFC9	2026-10-02 14:40:11.999016+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	9958e7dc3fde4bbda0cfb986fcec79bd	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-D2A1D9098855	2026-10-02 14:40:12.003361+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	ec7a410099c94eeb98ebfe48436eacfe	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-45A5FB710895	2026-10-02 14:40:12.005526+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	94a734ad94584a7ea3737bf0cee886b3	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-BC0EE9558019	2026-10-02 14:40:12.066387+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	dff879697f2f4c13882521a478715609	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-CF9532A49DF7	2026-10-02 14:40:12.070376+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	0a241b12ed4e44f889a595ff03588306	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-19FC0434FB36	2026-10-02 14:40:12.079521+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	0f969547fec746a8866e17639e29b969	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-CB7D91F16556	2026-10-02 14:40:12.082186+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	e92ece31f8c64c728fad56d264391ecd	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-403C01C67AB2	2026-10-02 15:12:39.380148+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	86f42f1c1cbb440c96e7c4f853ad5151	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-B638CD1F508B	2026-10-02 15:12:40.1305+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	370f60d145d64619adef44c2452c945e	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-3B34A835E683	2026-10-02 15:12:40.204699+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	b50d2d597d4b4478892b56d5029b30a5	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-2CF82A0B4E1F	2026-10-02 15:12:40.287329+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	d0f4d820ea38480e83b70c5741df5b54	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-EF6919168620	2026-10-02 15:12:40.624328+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	8e87119eb1724989b2081a8f7a690e9d	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-CE318E46A0F4	2026-10-02 15:12:40.706597+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	60784d18bdb2433fac2ded3232989881	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-0B81B0EFFA7F	2026-10-02 15:12:40.793649+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	82a6b091365b43d0919eb51057f263b3	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-C64F54E6A1CF	2026-10-02 15:13:02.415732+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	d31e2e64ed5e49e4920ff3eff141e203	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-89211BBDE4E6	2026-10-02 15:13:02.544485+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	ac63295c47144b3c886ed73024b5aab4	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-107C6DC9F756	2026-10-02 15:13:15.144162+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	a42f09524c32443ba6bfada6b544f611	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-11CDDCDD64B8	2026-10-02 15:13:15.151153+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	4c1649e0c5a54fdab725415de92f3b55	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-E3C9F8C173D0	2026-10-02 15:13:15.154631+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	c80ede1c11854514a534138ff3476bd6	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-B7D21F036FE9	2026-10-02 15:13:15.304887+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	c1484e6b22be499e9671afc4d35bbb83	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-30793F073A44	2026-10-02 15:13:15.310858+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	bc9e3bf8ad3143f18877277f150c806e	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-5224966F6091	2026-10-02 15:13:15.33167+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	c3caa6267dad40dcbff2a5461f89b32e	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-8981AD5BE6F4	2026-10-02 15:13:15.336788+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	8564564e55454c9b9b231d79bfcfd881	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-568FB538A339	2026-10-02 15:23:16.082557+05:30	admin	APPOINTMENT_CREATE	appointment	TKN-0007	{"patient_id": "PAT-A724760CEC48", "patient_name": "asad", "doctor": "Dr. Priya Gupta", "date": "2026-10-03", "time": "10:00", "slot_id": "SLOT018", "amount": "800"}	\N	\N	51cf8468c18c4986aed1abbba02ee2a8	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-8F8A8339B2C2	2026-10-02 15:42:41.47823+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	e3d3288e9a984473805215192242d672	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-436FABA3B5D3	2026-10-02 15:42:41.484096+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	fc19de40b4a94a199aceeed81f208f39	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-41D3AF2FAC3E	2026-10-02 15:42:41.489759+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	bec29e4f8c484e1c97235ef84999b563	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-FF25BA17FD89	2026-10-02 15:44:00.115781+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	2d6a3cf607e048c4a2789b7b6004060d	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-D940471C9E19	2026-10-02 15:44:00.822276+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	9828abf8602c49919ff218f0d825d44d	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-70883A3F6595	2026-10-02 15:44:00.904506+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	73bb8871c2ff46b99ea92ae24afbcaea	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-B53A18BEF13F	2026-10-02 15:44:00.989808+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	52a37a666ab6490f862d230c471ab42b	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-2E352A25F7A5	2026-10-02 15:44:01.136852+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	c2a3df92ca7d490aa5682d04cbd2f600	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-04BD20B04C37	2026-10-02 15:44:01.380628+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	ad9f03238c644cf1baa9f582de8b49ba	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-34BE8DAE0F20	2026-10-02 15:44:01.461959+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	615fdc4683c84726b10cd3c90f7f4a5e	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-7541F2715389	2026-10-02 15:44:01.537468+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	a3cbc4753c8e45a5af89144c9fede958	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-9CC3E57C1988	2026-10-02 15:44:01.542217+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	d17b06802cae4e9f8087c610fd0f9a39	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-5E82E056C7DC	2026-10-02 15:44:01.546119+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	e7ace2548c1b4fdc9c03e499dd035454	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-DF1AD1F60AFA	2026-10-02 15:44:03.554306+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	095799cb699f4ce9914202b9392181ac	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-7A6BD267F842	2026-10-02 15:44:03.62036+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	e83cc450a4e74dd2963a5a50680bbc56	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-5931F05AA04B	2026-10-02 15:44:06.892467+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	06149ac937e94d3bb0d2ab6de2e63fdb	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-0878A24D9EB6	2026-10-02 15:44:06.89733+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	91d040f5c42945f29130be0e4cfbd3c9	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-620C34E6DA7B	2026-10-02 15:44:06.900102+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	07e84ab98851443b8a58ecccbb7d48dc	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-5FC09E76AC9E	2026-10-02 15:44:06.964008+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	613795efdc8d4f3f9f5ac6c61724eb10	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-B9F1A75DB637	2026-10-02 15:44:06.968174+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	b73b6dcc0d4d407b84ad4998d4f7d5e0	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-5831BEC5E815	2026-10-02 15:44:06.978831+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	3d93c65aaad94bf484330ccddbfdcff9	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-8C85910EB6EA	2026-10-02 15:44:06.982774+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	694a4ec23a884f509d18ef7939648366	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-084A36E116E3	2026-10-02 15:48:02.51026+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	90ab607764fc4a2ca6a401d1365b7afa	2026-10-13 16:54:46.869353+05:30	2026-10-13 16:54:46.869353+05:30	default
AUD-FD36DD1CEA2C	2026-10-02 15:48:03.048733+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	c2ba72cb2be0457eb82c598f49309925	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-6DBB64DD8C71	2026-10-02 15:48:03.111332+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	065a205946a64f4a9a8bbd6f0239a70e	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-1EED7510165E	2026-10-02 15:48:03.170202+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	e17a0870f3b242039e70e4d8490ba181	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-56DE01EE3F28	2026-10-02 15:48:03.436674+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	37fa08a088204da78f85da260c78963a	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-255093CC7136	2026-10-02 15:48:03.521738+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	e40d99a8967d4389910026aef7bc447c	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-D0E691C745A9	2026-10-02 15:48:03.598023+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	5ebf944ec6f74cfeabeaa30b336a7a72	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-5E48CD6A1110	2026-10-02 16:12:50.933745+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-DB6C3CAE3C	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	825d1d6dedd14e3d966cf89849891930	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-6769C40933CF	2026-10-02 15:48:21.541904+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	939683f4ddd747eb97c682e912b01675	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-0BAEC9F7E47F	2026-10-02 15:48:21.545124+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	7a6baae557db4f528db39f2e2705d20e	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-373CA9DD1324	2026-10-02 15:48:21.548292+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	9dc3f84c0e9f4197aeaaad7e0aeaffba	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-5F312A7F3183	2026-10-02 15:48:23.341396+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	76e7e70fa8a64a1f9c1d7467685431d2	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-7F39013AD1CD	2026-10-02 15:48:23.381709+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	eac90e9d1acd4b58a1cfa0a6d4ee88cf	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-04F077B1DD9F	2026-10-02 15:48:33.089348+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	33c5f8c78b774c7f96eb7cdb7fd9d655	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-FCF1F6AB3CEF	2026-10-02 15:48:33.094115+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	8da9b5514c6642cc8a306ff8a35e864e	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-640D2A87D5C3	2026-10-02 15:48:33.096288+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	2744dc1df9264218b215b83db74ba1bd	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-CAC450FC23AE	2026-10-02 15:48:33.150277+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	f01b1b1a5288419ab7b8330d934a3d5a	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-F04E531D85D4	2026-10-02 15:48:33.154502+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	6d0fe762b1ad431c8d7cc8dd6442050e	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-4B1CB36D35E4	2026-10-02 15:48:33.164284+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	2207628839b1472cb6980d1a1e9365fa	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-BBD28863FB1D	2026-10-02 15:48:33.167682+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	160f4f45b31c4ad29718475867546a56	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-CD2553485298	2026-10-02 15:51:20.544004+05:30	admin	APPOINTMENT_CREATE	appointment	TKN-0008	{"patient_id": "PAT-B4D645DB67C3", "patient_name": "meera", "doctor": "Dr. Priya Gupta", "date": "2026-10-03", "time": "10:30", "slot_id": "SLOT019", "amount": "800"}	\N	\N	42627e90e0414d02a5434b03b75e8851	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-35F60148BB8D	2026-10-02 16:01:15.215691+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	40dd8ef226164f9facb3855561463863	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-5ECBEB58BFF6	2026-10-02 16:01:15.847697+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	b0d1643051014b20964b72088c7c4a04	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-1D51E3ADBAA1	2026-10-02 16:01:15.897481+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	70b0a5d87235452ebd6c73681b030a6e	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-B6C054E06561	2026-10-02 16:01:15.96634+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	012bb69a4afe4c4caa3f779f0ab31a6b	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-4F09684EC003	2026-10-02 16:01:16.112687+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	f86bbafc164a4f738ae57c6f381b5165	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-FC0814D31E85	2026-10-02 16:01:16.314614+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	240e70f1ecb6432a84538d3b2c9b583a	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-6CE555F93BDC	2026-10-02 16:01:16.383549+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	b8f2f9d6212b4b71967de70dc14b123f	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-519F77A0D253	2026-10-02 16:09:02.620254+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	b9af2e5b128840d2904d69449a3380a1	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-2F7D077C4597	2026-10-02 16:09:03.671955+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	4bf1f134775647d393bf1d2b79ac34e1	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-61B4B2581EAA	2026-10-02 16:09:03.771453+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	a36c95791bfa4533812d75a6288d2abd	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-513FA6243817	2026-10-02 16:09:03.872101+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	0384a365f5af4d0a9963d06d76dc4954	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-3DED9A70564F	2026-10-02 16:09:04.238411+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	1c4569e60ad048918c0beb54987a7d30	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-626CF2EFA0E8	2026-10-02 16:09:04.347105+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	b3d82e8b4e54490fa08374d58fa5d9e6	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-DC43E3C3A633	2026-10-02 16:09:04.454921+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	3b72d5501af842098ba01219320c7d3a	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-8DDF59F994F6	2026-10-02 16:11:29.576152+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-70A5087181	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	75860311ced243cb8a4147b23bc50de9	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-D6FF15500876	2026-10-02 16:11:29.577729+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-70A5087181	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	7d75869934c44f488d57f4743b880648	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-CAB51E96E684	2026-10-02 16:11:29.593829+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-70A5087181	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	52781e37e2e04fde8fa3c775217fa463	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-7D8CFEE2055B	2026-10-02 16:12:47.818528+05:30	admin	DOCTOR_ACCOUNT_CREATE	doctor_account	dr_arjun_api	{"doctor_id": "DOC001", "doctor_name": "Dr. Arjun Mehta", "email": "dr.arjun@test.com"}	\N	\N	f65dd5e521b643b098fcaa5edb3fadea	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-9DD5B427BB50	2026-10-02 16:12:50.950423+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-DB6C3CAE3C	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	0fb04f6a53a246b88fa8a8447496d661	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-7F78564B6627	2026-10-02 16:12:50.978294+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-DB6C3CAE3C	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	473d4b007ca34edd8152274045d338de	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-7A0050D493B7	2026-10-02 16:13:51.520942+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-BE41B9E2FB	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	71eb1c17d9114eb3817e8ddb48d4ea84	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-59DAF65C77BD	2026-10-02 16:13:51.520942+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-BE41B9E2FB	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	72c44766d40145be8e888ae79d995512	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-29A01777F456	2026-10-02 16:13:51.550143+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-BE41B9E2FB	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	8c965caf7ee0434eaaefe4e36095730b	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-D654D83A4F29	2026-10-02 16:21:25.094059+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	ba4cbb1f6acb4769b73921ae41844f31	2026-10-13 16:54:46.870394+05:30	2026-10-13 16:54:46.870394+05:30	default
AUD-C299AA347CC2	2026-10-02 16:21:25.966313+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	95b99331df9243b1885c93c98d3addab	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-1DB5E4AD782C	2026-10-02 16:21:26.219408+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	37f739031a02421991d3c3542afc9e97	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-693B27F68554	2026-10-02 16:21:26.327043+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	079d20f53c724ddf91e40c9d01cb903f	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-606107C2CDE5	2026-10-02 16:21:26.525928+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	0ec5cab1fb574b5094137ab899eda188	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-85DEDFDE6132	2026-10-02 16:21:26.624915+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	684db15272f44b06b66ccc62c25f19f6	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-BBB03A597A0B	2026-10-02 16:21:26.727285+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	057b321e544d45cfb38bac13a67dce0f	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-C560F0397CA3	2026-10-02 16:21:31.34807+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	c8ee0559363b420494d7129d5056356a	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-F449A2482298	2026-10-02 16:21:31.355979+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	4e2ab6a29feb446ea10884205254b3fb	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-79E7B70ED5E9	2026-10-02 16:21:31.363629+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	103836b8dd2f45fda128fec765cc28d5	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-860A97CF9D39	2026-10-02 16:21:35.490256+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	d7ea8094f8cb456d87c9f9d442bd094f	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-418D7B29A17F	2026-10-02 16:21:35.522931+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	ce7213187cf64f66ad75a3ce84261b23	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-E5F794AA6949	2026-10-02 16:21:42.470344+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-621A581280	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	c308c11403bd4cdfb896e979bc40ea9f	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-62343C2DA8A3	2026-10-02 16:21:42.471056+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-621A581280	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	f219ca2caaf3441d8351fec854bfeb9d	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-53097EA4A969	2026-10-02 16:21:42.504259+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-621A581280	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	f949d266f288424c88031f8337f18840	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-CC7F374A4B08	2026-10-02 16:21:51.728783+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	f5952b631e764ab3a36403df216f99d1	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-15C00849B9E6	2026-10-02 16:21:51.738491+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	198e94e09a994dba9c3abe404cf3362c	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-4FB7009529C6	2026-10-02 16:21:51.744986+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	c7e93dff7b704341868af49508a2b271	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-998DD18B4C99	2026-10-02 16:21:51.936492+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	e36a3db55f7745818b6761945543fdd3	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-2D5F7D7BDA67	2026-10-02 16:21:51.953481+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	5cd86dee4021498c9c10e03bfa66f6e6	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-3568F6453C13	2026-10-02 16:21:51.971741+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	ed5a323ab2fc4d448d1522b330a3b1c9	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-4456A45AA54E	2026-10-02 16:21:51.977816+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	7dadc82b3aeb47588c36c0a5d3e436af	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-B901BAE7163C	2026-10-02 16:22:30.774613+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	f97876957d494a6dbdcccd204d70c847	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-737D061BA337	2026-10-02 16:22:32.362846+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	590182bb238b4af9b6a6093926e62e89	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-35B77E769478	2026-10-02 16:22:32.565008+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	d3e6fed5c25f4bf88186e31ce4b37ee8	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-A54515766430	2026-10-02 16:22:33.043546+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	4127f57c68ad4c60ab9fe4ab68bc973a	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-171DF9B81517	2026-10-02 16:22:33.692877+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	27284a05b3db4ac3ba05e9839b65a98f	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-1CF592D1D405	2026-10-02 16:22:33.971468+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	1718f103a21544dfbdd8ee2fb6e77487	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-BFC9BE2BAE77	2026-10-02 16:22:34.255845+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	c164f4010bc142adb60f4e0777de0b4e	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-F673C3983C8E	2026-10-02 16:22:34.799009+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	f6106ddead9b4e2c84e94699a304a33c	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-DC4E613DB98F	2026-10-02 16:22:34.809901+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	d50674c06e42470f891371e15f9b71b5	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-440E0E309866	2026-10-02 16:22:34.821809+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	ad6ea13dabc3468998f27fb9fd237039	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-3BFFE14B9E96	2026-10-02 16:22:39.491681+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	54b0ed59946e4550af62ea075d539bbd	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-3147554886F8	2026-10-02 16:22:39.540617+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	7e8cffcda96d48e8a86327b62dbb030c	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-5190BFC0EC8B	2026-10-02 16:22:45.577605+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-EB7B47FE11	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	e597a5802157446c949c5787b83e1bc2	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-F19B8E24F706	2026-10-02 16:22:45.5859+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-EB7B47FE11	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	a7f289e259804e388e090fd5bc4ce751	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-68C5E2C28A65	2026-10-02 16:22:45.618051+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-EB7B47FE11	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	daaa4dbc0a65451cbe2de2945ba75a1b	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-736A430C2F51	2026-10-02 16:50:03.969328+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	232031c8a9f346558bdd17fc1db41b86	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-5F1B7852853C	2026-10-02 16:50:05.192192+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	51c85496ccb34e2f926df1f44ee47de6	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-F882EBB393CC	2026-10-02 16:50:05.551461+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	850fbf823bd544f3b1316eb5970ef5ea	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-784123E1E646	2026-10-02 16:50:05.672559+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	4d66cfc1fb144d338bdb5ca3c7302f01	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-BB1FB7A6DE37	2026-10-02 16:50:05.919292+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	ea5ff3cfcb2d4e6d807be36869d34632	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-19BAD81F3C93	2026-10-02 16:50:06.050734+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	7a7cd78e3f6f4c7e83324cfcb425aa8b	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-E8EBE6D350D6	2026-10-02 16:50:06.189465+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	91d8818530984e50b53ed7aac8b90fe5	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-0A2E04ED27C6	2026-10-02 16:50:28.048888+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	c372f2cef39c48ab8a048bc786b00312	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-0912981D1206	2026-10-02 16:50:28.057769+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	efe041bd149242ea828d8f18ddf0d9f0	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-8913B9D4E0B8	2026-10-02 16:50:28.067133+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	ef23fc3dddda4b94904dfde3feff7ddd	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-F4E2105E32BA	2026-10-02 16:50:32.509625+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	506578c2c1db4b4e8aa456267f26a6be	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-FC6A20C27AB7	2026-10-02 16:50:32.575018+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	33eb60fc095447fea85d8aae9ae8f252	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-2613AA9128A7	2026-10-02 16:51:01.187131+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-96BCF8A495	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	b9094ecd267e4bb592e29d5fedc4673a	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-66F921E0511C	2026-10-02 16:51:01.198444+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-96BCF8A495	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	c13bf8e2edf44dc4abe76a5cad181cdc	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-16AD9A32AD70	2026-10-02 16:51:01.271464+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-96BCF8A495	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	38427c12465b41b7937b58bcfe034648	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-7FB958E96697	2026-10-02 16:51:13.928573+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	6d60b75dde0442cabb989eb9eab7a5c9	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-EE4FDD97440D	2026-10-02 16:51:13.940314+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	536629ad92544441a6ac49f3ca5bdb53	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-AE3495FEF237	2026-10-02 16:51:13.947464+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	8135fd2a62584e3d9a659f955ee69889	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-BDB5F29986E5	2026-10-02 16:51:14.153801+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	a6760692570c49f5b4e1021596ccd5cb	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-A0E264FD3D9F	2026-10-02 16:51:14.162303+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	291c7540fa1a45c68271a9cf91feadf5	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-536FE7ADBDD9	2026-10-02 16:51:14.179115+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	ccf0e2e083294b649cc935ea26400587	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-E29783067BF7	2026-10-02 16:51:14.187173+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	06caa299c26d41f3b9832c2979370c44	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-523FFD099739	2026-10-02 17:04:41.537882+05:30	admin	DOCTOR_ACCOUNT_CREATE	doctor_account	dr_sufian	{"doctor_id": "DOC003", "doctor_name": "Dr. sufian", "email": "dr.sufian@clinic.com"}	\N	\N	53a5217dc6804efc9660af062e5bdd8a	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-ECD2B9BE4F76	2026-10-02 17:39:47.598759+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	63871dfdf5454a5d9e5b843c4db0abc8	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-AC029910481D	2026-10-02 17:39:48.866294+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	c9ca796a4b084179ac496818f237d609	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-4D42AB1A30E7	2026-10-02 17:39:49.150302+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	10a390b78b694d9498c0f65111c25bd3	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-722C66554F60	2026-10-02 17:39:49.28185+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	89f0e7760f564ea6bb82c31ae377c7ee	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-474C7674A5F6	2026-10-02 17:39:49.532432+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	4dec81167aa843c29cd66a61190cce9c	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-2A1AC428DBB7	2026-10-02 17:39:49.673272+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	e6b5a72689794af488e8ace75a7246ca	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-53EAB67B7C33	2026-10-02 17:39:49.804399+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	25bcb69a922148e78b6ad5abbdd43afa	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-C15486DEC70F	2026-10-02 17:39:56.18333+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	d11f05051b9640db832211506f4f037b	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-9262FECA0539	2026-10-02 17:39:56.19117+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	bb7b934fc82647bab81ac5b0dc609e21	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-D08BCBE63F1E	2026-10-02 17:39:56.198016+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	2cf13d3d6dc040778fc6ce5f6247aee7	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-7EF9C1996722	2026-10-02 17:40:01.81265+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	8babc64236184e01a8b8bd739c5197ad	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-14B6823EC7B5	2026-10-02 17:40:01.917185+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	d4a3514473ea45849f3f58764d651fc1	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-C1F6420EAAE6	2026-10-02 17:40:22.21136+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-575E3E59C9	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	ef2c890be97b42e2a1124bbe55076bdf	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-F7E0CF8CF1F2	2026-10-02 17:40:22.224602+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-575E3E59C9	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	60b5dbc1a6ef4c4c9e13488fd3a0f94f	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-258C314E7A81	2026-10-02 17:40:22.295765+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-575E3E59C9	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	174173acf4524a9ebd4918eb9d2f4634	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-B26E847B4ED4	2026-10-02 17:40:32.533485+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	eb7e2c6218fe44ce8e0216222bd40406	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-A004E282AEC2	2026-10-02 17:40:32.552575+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	8e3be5f5ba8d44d98be716543e9f08c9	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-E1E19B7032D0	2026-10-02 17:40:32.564555+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	982eaa243f184d82b6ed51a434aa0d4a	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-AD66A29942AE	2026-10-02 17:40:32.84288+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	eb394c1c3647453183b66654c0f181a0	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-E2905B1F69FE	2026-10-02 17:40:32.850949+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	35365ad59dff43d7ae03097ceb29bb83	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-2C310C9B70FA	2026-10-02 17:40:32.876255+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-03", "old_time": "10:00 AM", "new_date": "2026-10-09", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	cc0abcc6982f4ab6be65cc8103d506e7	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-15527C3EA2DB	2026-10-02 17:40:32.886328+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	4d52cb19d43944c0a50eaa7ae5b13881	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-39BC679DE2B6	2026-10-02 17:44:23.460533+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-A7D00E7F77	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	f020d3c834a545ec8ef27a69e9231568	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-8BBB7037EBFC	2026-10-02 17:44:23.465275+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-A7D00E7F77	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	ea3c0815e944420e826c90dcabb18ae1	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-20B244CD0363	2026-10-02 17:44:23.474381+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-5B6161626C	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	892b1c3cb4b24f739b34be981c1f2f45	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-E25540903874	2026-10-02 17:44:23.477176+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-5B6161626C	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	d914cf7c4c234a4783282e2b1839e290	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-D23869EF48C7	2026-10-02 17:44:23.489301+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-01292BD61A	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	fecc02187434446b8fe10ec541662615	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-5A88BB014805	2026-10-02 17:44:23.490982+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-01292BD61A	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	be86553b56ef4a73a904c22255d4feb3	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-B4A937EC528B	2026-10-02 17:44:23.493211+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-01292BD61A	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	0c305ba114e54429b08b548ab021e12d	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-9AFC3478D94E	2026-10-02 17:44:23.501985+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-D2E0D7DB2A	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	fa19288d7670443d9862d06c3c4bd2c6	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-D53295DDF23B	2026-10-02 17:44:23.503615+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-D2E0D7DB2A	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	df94136e795f4b03b48747bf834349b8	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-DC21D2B39769	2026-10-02 17:44:23.528808+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-70937C7621	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	b061c980473543af97efcd1c9f0511ef	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-8CF7E7DC1CEA	2026-10-02 17:44:23.531062+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-70937C7621	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	bb9404a0c9d14863a578d3fd8304b9a5	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-00A8EC2BC363	2026-10-02 17:44:23.552952+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-BF1D247ED1	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	9db2d47f7ec6415cafd8b64864aa5826	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-5B257408D53C	2026-10-02 17:44:23.555221+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-BF1D247ED1	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	25b1cc9784c143778d145f7c68011a4c	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-AF5C833764EE	2026-10-02 17:45:10.206282+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-04883A530B	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	905f0de1104940d0b713aa4dcdf914d9	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-94715518EED2	2026-10-02 17:45:10.206282+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-04883A530B	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	6a32c831c28e4b5d98e8ff5862a12597	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-EAC374426F52	2026-10-02 17:45:10.221435+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-C26BC524D7	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	103fcbea5ab843fda9a043f85242d35c	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-9091A2F1EC13	2026-10-02 17:45:10.223669+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-C26BC524D7	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	a68079b8865b4f039424b006ce58eb68	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-78791E886DD6	2026-10-02 17:45:10.233533+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6ECD4E5D79	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	c9014ac96e2948679c9d89cb3ebe2750	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-058D9C271022	2026-10-02 17:45:10.236692+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-6ECD4E5D79	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	21e56d0bc6be4bfe8ba0302e163145ec	2026-10-13 16:54:46.976022+05:30	2026-10-13 16:54:46.976022+05:30	default
AUD-F3142F68A148	2026-10-02 17:45:10.238368+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-6ECD4E5D79	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	ed344324f93240f4a72dc7fc0fdf8003	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-ACEA5324D994	2026-10-02 17:45:10.250658+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-28C233560E	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	711bf85e1f6a4c0894851f95887e77f7	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-207A09E85A23	2026-10-02 17:45:10.253965+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-28C233560E	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	356719b618124e6d9a8036759d4c9093	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-497A5DA2BC3A	2026-10-02 17:45:10.283883+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6BA952B158	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	59bb942a94df4c0a91f987658591e9f6	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-B74A09541220	2026-10-02 17:45:10.287237+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-6BA952B158	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	aec874788f6448cdb9bf04d42b9ef329	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-ABDA843A377B	2026-10-02 17:45:10.311387+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-49B9A015BD	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	79c8af0ff5bd4d7c94ec41976024f30d	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-538BF5785E64	2026-10-02 17:45:10.313539+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-49B9A015BD	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	047cb13a99de452cbd474932ea534bc6	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-7977EEFC8D31	2026-10-02 17:45:14.828534+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-53BDA3B213	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	971977bbe6e2493ebe60dec98f69f542	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-248AA54E23C6	2026-10-02 17:45:14.850651+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-53BDA3B213	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	50569934ba754edebbaf1411d49412ed	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-1A54AF624BB6	2026-10-02 17:45:47.97502+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-DA7AC8838D	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	009b89fa4f1a48259dc7d70adeab0392	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-5CC7C844E93D	2026-10-02 17:45:47.979689+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-DA7AC8838D	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	623100b4b51040249d1573090bfe8a17	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-C63B2B8BF0EA	2026-10-02 17:45:48.005032+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-DA7AC8838D	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	222e701511644ba9ba622181486664ef	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-848FE719609B	2026-10-02 17:46:51.01816+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	b33b42f32ed2477188c26f4f967f5d26	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-5092D4D2B7BB	2026-10-02 17:46:52.53746+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	5c3f3a7ffe2b459a880ed53bc2a65e9a	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-383A799E9451	2026-10-02 17:46:52.662792+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	013f4b63ccf840c485a14aa25df9ef37	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-19C03A443167	2026-10-02 17:46:52.938073+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	c6ee46b36ae04447910b57fe630dffac	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-BFB26D0CB30C	2026-10-02 17:46:53.237224+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	48282351d9684fd989b7068280480272	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-0EA3014C42C9	2026-10-02 17:46:53.369966+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	6cf1fc3d2c7b4fa6b5dad89f2e6d3614	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-6C402AA19BB6	2026-10-02 17:46:53.490043+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	4ac9ef0598554238ad11e26d696dcfbf	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-88666794A7CD	2026-10-02 17:57:55.581268+05:30	dr_sufian	PRESCRIPTION_DRAFT_SAVE	prescription	RX-DE28DDAB57	{"patient_id": "PAT-533560FC8A6B", "appointment_id": "TKN-0003", "status": "draft"}	\N	\N	6e3024ed9ec149a3bfdd5547a2b74bb9	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-6836100E3D57	2026-10-02 17:57:55.587163+05:30	dr_sufian	PRESCRIPTION_FINALIZE	prescription	RX-DE28DDAB57	{"patient_id": "PAT-533560FC8A6B", "appointment_id": "TKN-0003", "version": 1}	\N	\N	eb99254cacd64f0e9c7e46fa943e4b57	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-A234E5F3EFB0	2026-10-02 23:00:45.413417+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-DB9F844D27	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	0f82fa3ff2834c3088993b819f099b26	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-778FAFE97729	2026-10-02 23:00:45.417454+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-DB9F844D27	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	2ed4602f7e7a41019d4d56948ba9637f	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-CBA3FDED013B	2026-10-02 23:00:45.429751+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-1EC5708B5F	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	ef3e847821d5428b97ff6130d65754bc	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-4BB68FEC09D7	2026-10-02 23:00:45.43206+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-1EC5708B5F	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	d1fc503650504c438d0fd32167b4e1d9	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-9D468634303A	2026-10-02 23:00:45.444776+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-AC3C1E6C22	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	aa4e697c41794083b06a5936467a2ea2	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-0EB7B8A94082	2026-10-02 23:00:45.444776+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-AC3C1E6C22	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	ecc0af9957494bed9d13070d3f7df5d9	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-C8670FB2DD81	2026-10-02 23:00:45.44961+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-AC3C1E6C22	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	7fab613c81084cf7a77bda57c7c3c44c	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-7F8B3612E836	2026-10-02 23:00:45.462416+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-9985C7F790	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	96de07ce5dff4fdcb2511a2949389034	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-FDC1C4F407B6	2026-10-02 23:00:45.464695+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-9985C7F790	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	9ef7967940944fe99239dc41ed976d6b	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-A5E770B4FEE4	2026-10-02 23:00:45.504198+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-A53502DA1E	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	86f09ab1260b4808890be09560936028	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-98DE79A65338	2026-10-02 23:00:45.509248+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-A53502DA1E	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	a082962b43d8444da1ff0a00163ed39a	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-A26E5488A59B	2026-10-02 23:00:45.537078+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-5A8EF1BB22	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	befb941456e9462f8a190c4855218947	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-4D52F5AF7F4D	2026-10-02 23:00:45.54052+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-5A8EF1BB22	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	a22c63b517004bf9952445115529a7ad	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-30453F8C17BA	2026-10-02 23:00:50.833636+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-F2CE183C82	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	f3badb0ed31d4ba8be552d18e70208e8	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-D1F3A52E09D5	2026-10-02 23:00:50.856115+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-F2CE183C82	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	d405dbfe69f14e70a4b58ca3f380f277	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-5A6A495D2F00	2026-10-02 23:00:56.5696+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	875a0ccf2db747e4b3a239a49cab17dd	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-5E9400A0DF9E	2026-10-02 23:00:58.21451+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	ab2bfbfd15034b799335401bda67f098	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-6B96B5231BAA	2026-10-02 23:00:58.512805+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	f8af8a7193f046c3960b4ebc18c4f9ab	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-6B13755DB304	2026-10-02 23:00:58.649602+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	e903b82d3444490ab90cc855837dda44	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-3E1E054E2C2D	2026-10-02 23:00:58.909845+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	c14da58735e5480cbe6530e684b2768c	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-197AEAAB6FDC	2026-10-02 23:00:59.070616+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	07aef55641b74beca86fa0e6912e1e2d	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-A52C9F15E378	2026-10-02 23:00:59.439709+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	94b3f9482a404a27949d947ed6d249d6	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-1881125E0892	2026-10-02 23:01:09.557264+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	4fd870546e994c779cd2abf155e263bf	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-FD21DD5A9815	2026-10-02 23:01:09.566895+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	248362d071884af18c1f769638dbc5b4	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-A5FECB5C5BDD	2026-10-02 23:01:09.577584+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	1fe007ba04264a5b9b055e33ec7640fa	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-5B633630E728	2026-10-02 23:06:40.135095+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-96ECEDD706	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	0a717f0974a441efa214a348f93f04fa	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-A1C874E09232	2026-10-02 23:06:40.137105+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-96ECEDD706	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	fdf69f364a9a418dab8ffa382a4c5d71	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-25542D1F52FB	2026-10-02 23:38:14.488059+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	6b2a16319e374d0bbca4863ae225defb	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-61EEFAE14728	2026-10-02 23:06:40.147756+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-670694AC4F	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	16e4436cb3de4217b5da2b0abaa54b3c	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-D8ACBC279BA2	2026-10-02 23:06:40.149891+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-670694AC4F	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	f7008b41f773423fa1767c7fee125686	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-36E4E4840388	2026-10-02 23:06:40.157058+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-C377E311D5	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	b6ff732a30724389a048c3c38886429c	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-D647D26244CC	2026-10-02 23:06:40.159217+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-C377E311D5	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	656bdc2a80224870a39d00743d171ba9	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-73ED5E2EAA7F	2026-10-02 23:06:40.162521+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-C377E311D5	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	fb931bae951140ffaa6c3cd61fa4d97c	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-D71EF7848DEC	2026-10-02 23:06:40.172319+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-90CA93ECB8	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	683850fef8d64d049e5a95bb808515ff	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-F7C3F9D5C6BA	2026-10-02 23:06:40.174553+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-90CA93ECB8	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	923fb85f5fdd4a37b477dcd99bb691e0	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-A61DD74DE079	2026-10-02 23:06:40.202947+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-FA984FBEA1	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	371b3b9e95c747a5b00d78569eb76cd0	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-C38C03F22944	2026-10-02 23:06:40.20471+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-FA984FBEA1	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	c36eac8c6f54446694c215c5092fb9ca	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-58CF5859D735	2026-10-02 23:06:40.241869+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-01F9CE48A6	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	ea6dd7f6de724c399e988f38cdee7cf1	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-1EEBF7508DBD	2026-10-02 23:06:40.244033+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-01F9CE48A6	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	b1141131144448e7bd87f3936ad93417	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-588376D180EC	2026-10-02 23:06:44.641465+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6B6F19C478	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	ab1e27860c3f42628c1f2e54a9d4e62b	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-7F81905B3110	2026-10-02 23:06:44.667575+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-6B6F19C478	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	4d6121d57c02485db5a4bc9fa9a37b73	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-AAE649C6D319	2026-10-02 23:06:50.770484+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	e4cd4b9382434007bed756b7e56068cf	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-8E4E7DF65D02	2026-10-02 23:06:52.0361+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	8aaf8f109c03400eb8d466a784317496	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-E8FADEA0DDC1	2026-10-02 23:06:52.333559+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	bc9f60569f6c46558f130d9df9b1e904	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-9BC35E704DAD	2026-10-02 23:06:52.475196+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	4967037b14784ae4bce3922f62ee4be2	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-8997D1A1952A	2026-10-02 23:06:52.725194+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	738c4e4ebe9640828f30604bcc6924b2	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-307B7953E22D	2026-10-02 23:06:53.025126+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	60807acb9b3e44c1a6594ca4f5f097a2	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-524A4F0EF893	2026-10-02 23:06:53.170006+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	3ecca80d72ca4c12b906311d63d2bd4c	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-B2E7E4B507FF	2026-10-02 23:06:53.320685+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	4989f05e7e4f432e8a9736d6249b12e9	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-C5438E697D80	2026-10-02 23:06:53.328494+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	84a1f6014de64ba9be07a0d4cb6849d1	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-FEED05842FBD	2026-10-02 23:06:53.335631+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	3e48f1154b7444adaf42fec251796662	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-6C15A832512B	2026-10-02 23:11:15.458983+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-5C34D56BC8	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	f460c070e4db4328a72a0b8e47dacbd9	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-CF77E13B50FF	2026-10-02 23:11:15.461339+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-5C34D56BC8	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	bc44a8099eb844ce8d9ffa46069afdce	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-FE70B438FB12	2026-10-02 23:11:15.471006+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-E19290F7D3	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	5133c41557bc4dff9a56dec4c56010da	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-A38C4A44843E	2026-10-02 23:11:15.473145+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-E19290F7D3	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	ccdad298960b45e3be091c58b4ab87d0	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-EFF5B4ECD338	2026-10-02 23:11:15.482376+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-75635F4871	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	027e25d723ee4ba8a6579c3ba4a46889	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-1595C0E73F87	2026-10-02 23:11:15.484607+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-75635F4871	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	ce78febee43e498c977ce18044c8632f	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-26EA420B2371	2026-10-02 23:11:15.486234+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-75635F4871	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	d20e415df2024ded80be781bc105a7d7	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-862B0F5B8DC3	2026-10-02 23:11:15.495019+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-C44B166173	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	e8ba72bc2e6340b0a12a41ddcabad874	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-B879345F9B31	2026-10-02 23:11:15.497856+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-C44B166173	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	dda0f36dcc1a477fa5346725e2ba7680	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-21E24E2A90F6	2026-10-02 23:11:15.521831+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-35829E0826	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	1fe7d2c94649455b8baf569ed1b268f8	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-4012C0441FA9	2026-10-02 23:11:15.52349+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-35829E0826	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	6799f905bb5f48fd94df7d96a32b1df2	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-22B260F23A3E	2026-10-02 23:11:15.551657+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-7BC4AA975E	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	9db0929d64a7464eacc6777e2287d90b	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-1F6B1F1767F7	2026-10-02 23:11:15.554431+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-7BC4AA975E	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	7aeb26c5c94e4f2b83ffb7dc5df2d175	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-196EB1366D61	2026-10-02 23:11:19.466983+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-58A0AF0614	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	2db26ea96aa1406b8f579841000930b0	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-4936A048B68D	2026-10-02 23:11:19.491771+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-58A0AF0614	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	df860adcbc464be2bf5332a1880a1f89	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-674F69452324	2026-10-02 23:11:26.079124+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	db410f64a746420aaf4f35a377392364	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-F8B25EFD84DE	2026-10-02 23:11:27.299821+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	6eff50825bba46f08e13af962e264ebf	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-B05212A415CC	2026-10-02 23:11:27.619117+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	39d6dfb2568c48708781fb2bab4de6fb	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-6BB50868600B	2026-10-02 23:11:27.789881+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	2639127cbda341e5b10feeaf109e843f	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-EFA5B57A0F56	2026-10-02 23:11:28.074515+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	907e69de954246f891be1a198e88e675	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-1F98AF8FC34B	2026-10-02 23:11:28.404024+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	02c6f997ecd14da0accd2a0285909447	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-C07F64DD2950	2026-10-02 23:11:28.550252+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	a8f6435817774533ac558a69ce7de837	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-FC34C3FACAFA	2026-10-02 23:11:28.705867+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	774a73fb376046f98d963ccda59b2b7c	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-EF8493B2DAA5	2026-10-02 23:11:28.717039+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	a85590c4c89c407697245f1d6eeefa06	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-031DE3928D25	2026-10-02 23:11:28.724753+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	11e8d75d4809402eb767349eae39c634	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-A27CE68865E5	2026-10-02 23:17:24.130741+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-A4E003E575	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	5a865626358643848243e817eb2a4d46	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-4DD634E0BDC2	2026-10-02 23:17:24.134237+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-A4E003E575	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	96c42289f48f45beb9e01738137f946e	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-45917AD756CE	2026-10-02 23:17:24.14621+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-B8F5615A75	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	81d417783dee415aab3c824db6c497b4	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-63C7975EE51C	2026-10-02 23:17:24.148987+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-B8F5615A75	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	b338aa12d125450480754b17a617f7da	2026-10-13 16:54:47.080448+05:30	2026-10-13 16:54:47.080448+05:30	default
AUD-6F155954F8F0	2026-10-02 23:17:24.158393+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-74875D20A5	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	c03c2ca23a484d45adac32b4f689b445	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-8E08AA82AD55	2026-10-02 23:17:24.160619+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-74875D20A5	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	ee460b3217214b89879088364f163a9d	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-CEB67E17FC04	2026-10-02 23:17:24.162852+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-74875D20A5	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	af111d284ff3468892eea579e5c592e2	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-D17C71DC8BA3	2026-10-02 23:17:24.174393+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-3E5DA20FA2	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	ea4ce5ef52284278a94b20464889867b	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-65A21CFB024A	2026-10-02 23:17:24.17722+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-3E5DA20FA2	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	332428d42ef9489bbdd1c6f28b752e78	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-88D985D77FF2	2026-10-02 23:17:24.257115+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-2045A4DB49	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	7b5172010adc43c986237174a57ad73e	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-05F9643E88F2	2026-10-02 23:17:24.259184+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-2045A4DB49	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	f770981b90a84f4ca2ddbe0eb1bb7bca	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-374E74D0629A	2026-10-02 23:17:24.308554+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-0E569B9084	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	28d64c2cd7344e54bf232612113ff42d	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-F6E2C0881AB6	2026-10-02 23:17:24.311299+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-0E569B9084	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	0ef56f42ac1548e6bc2d2bfa697bf861	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-34FCC11C565F	2026-10-02 23:17:28.49085+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-81501651A0	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	bdff46b82dc04c0ba1da80eb3646961c	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-134EC3345EEE	2026-10-02 23:17:28.516687+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-81501651A0	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	f0d59dec507d4a8a8cc631e558fc37a9	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-2FFD0BC3B4FE	2026-10-02 23:17:34.000922+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	62c461403d184624808238d8d64f2a32	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-DFF3EFEDD133	2026-10-02 23:17:35.394295+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	83b8fe3277df4f29ab5e11c7740c5c0a	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-526FDB42708D	2026-10-02 23:17:35.688925+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	dd45895c472043609e7bd4775b675920	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-D2D746D1AA95	2026-10-02 23:17:35.832373+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	f96a0c8d27f74784ac97cf26d8b2fdf5	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-BEF636835944	2026-10-02 23:17:36.162595+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	5e52ee0b66d246daa2b2a5186fcdc0af	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-ED7E2A73C61B	2026-10-02 23:17:36.294114+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	fa4c7226342947779d3b74301ce7ad51	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-38D6FC2DDC09	2026-10-02 23:17:36.618905+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	a258b913c33f4ffe917f8b54fcb079fd	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-B84E66156B58	2026-10-02 23:17:36.766656+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	1bc0109ba29344738ea2ccc1fad1c4e5	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-7A4470101C73	2026-10-02 23:17:36.774074+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	3b746828224b41038a588d0fa952a488	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-D319CACC7CB8	2026-10-02 23:17:36.784741+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	7a9a2c72f78949a6b0d966731e6bcc18	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-97231CA117DF	2026-10-02 23:38:01.167953+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-C244B45C5D	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	5ad8ea23ee784724b233d78dd12785ca	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-69A6FFF9BF79	2026-10-02 23:38:01.17204+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-C244B45C5D	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	56e451825b0c49ca8b6a7388188eae6a	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-C27DA44CF694	2026-10-02 23:38:01.181351+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-0E869DA065	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	d9360f2e95d146fbbfdf02c95cc2a71e	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-C2EB53259C5D	2026-10-02 23:38:01.184525+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-0E869DA065	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	c3027d480d5f45dc8f7236286ac7e083	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-3C415F4ABB81	2026-10-02 23:38:01.195409+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-DA2FE43C07	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	20a2dba43f9341f9bce13658f5d184a5	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-4FAEA5DA49CB	2026-10-02 23:38:01.198186+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-DA2FE43C07	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	8b44a3c62d70479d89ba22289aebae67	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-8526EC447DC9	2026-10-02 23:38:01.201562+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-DA2FE43C07	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	d76ddbfce73d42cc981a4471decb4842	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-FC0BC59D55B1	2026-10-02 23:38:01.213115+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-D460B59CF6	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	27f9cc058ab340648ee73e1633be02aa	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-1C179862DE6A	2026-10-02 23:38:01.215363+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-D460B59CF6	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	a4356b083dbd4f27af75516e85e33e7c	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-33A4315A94B9	2026-10-02 23:38:01.25264+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-8252565F47	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	5b243cda4d8149848f85480d9633876c	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-11A50C47A072	2026-10-02 23:38:01.256553+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-8252565F47	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	4e19a7dc5e7f4cb98b654dd540e6f7f5	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-EF833F7EB1F1	2026-10-02 23:38:01.282205+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-D2C49F33B9	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	7251e09bc4cb48e78fbec156b22ce55e	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-91A52DC7F0A9	2026-10-02 23:38:01.284952+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-D2C49F33B9	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	74b34db0cc0c4bb1b198d3db7008ecb2	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-308FFD41941C	2026-10-02 23:38:05.372034+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-00EE91BF22	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	82121295f4bb48b5be1dc1ffa805cf2d	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-D7D7D7BE2760	2026-10-02 23:38:05.402298+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-00EE91BF22	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	23a99d234cfd4f07946e7ff8e8c18b74	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-93D168EB547B	2026-10-02 23:38:12.072278+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	5f4d4c48aa1a4fedb92f426e65d56164	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-67D0DC7C6738	2026-10-02 23:38:13.363889+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	facff3c4e3c545c980971a315f65f331	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-7E478C1F00D9	2026-10-02 23:38:13.677814+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	69448e4752e04a7b93777d7a193a7077	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-66D50C9A41B3	2026-10-02 23:38:13.814459+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	07120052297d4a6da0898f506451e36b	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-793E46027EF4	2026-10-02 23:38:14.122018+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	1c9d9eaf4c3f44258169941992e33504	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-B8CF48ECC5A9	2026-10-02 23:38:14.662069+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	1041851808fd4bf3bc52fe906ec2f3a7	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-360BE9712ED1	2026-10-02 23:38:14.829387+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	3331b1666e524a5e9eb2312391fb883c	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-9DED4F2E37CC	2026-10-02 23:38:14.839071+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	5ff09ba20d814c669a307149a07ec42a	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-C127A21BCDCF	2026-10-02 23:38:14.848066+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	5e6e31a9233440b9a23b213f3220702b	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-5E9D08693F82	2026-10-02 23:47:37.529107+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-B50DD63440	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	724aceb6a6134992a395c8134e521f80	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-EAB5314F9320	2026-10-02 23:47:37.531928+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-B50DD63440	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	ba26ce32a6bd49fa8bae0a97dc5413b8	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-10AEDAEEFD5D	2026-10-02 23:47:37.545063+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-3D5B5E9340	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	16cd13b978514ea28ce14709798a9361	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-CFC3AB4D5791	2026-10-02 23:47:37.547255+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-3D5B5E9340	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	55eda9d67de249b9b96392d7905aea08	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-81EF5A5E500D	2026-10-02 23:47:37.558812+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-75706597CD	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	b89ea8c75f4c4cb19963160db53cd2ed	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-68AF3668EB9F	2026-10-02 23:47:37.561052+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-75706597CD	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	9ef55986428940d895e421979064334d	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-8DB329795EA0	2026-10-02 23:47:37.56323+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-75706597CD	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	286fd7ca12fe444184adf074dcb1dcb2	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-355D9E87F9B5	2026-10-02 23:47:37.572998+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-D79047CE4B	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	36ff76019a2a4214ac90523ff5a25764	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-11D79770DC57	2026-10-02 23:47:37.575597+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-D79047CE4B	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	48f667aff2e74c92851468dc52eab152	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-8991FD1524EA	2026-10-02 23:47:37.605612+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-0FC42C3BA5	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	0e841240a4bc44d0bce23bff181018dd	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-E17B6A235B25	2026-10-02 23:47:37.608501+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-0FC42C3BA5	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	36585281de8e4bf48c5cca9e177c466f	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-3849956A37A9	2026-10-02 23:47:37.656679+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-956C4B0DD3	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	a4e9bfe0fc3f4994b9f671c2203bf31b	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-441D21941EE4	2026-10-02 23:47:37.660006+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-956C4B0DD3	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	1312e790c7e9445b8dc837d30247b311	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-01CEEE3C052F	2026-10-02 23:47:42.048744+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-88893CCF3A	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	4e00233d096440be840fc3cee3b1f761	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-5BE009396D2D	2026-10-02 23:47:42.06083+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-88893CCF3A	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	bc04d0a2bba444a0b6731a2af0ffb7c9	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-9EA494F3CFD1	2026-10-02 23:47:45.905181+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	0e47dc291ffa4c359e99e60d4e94cc9a	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-F2E0CC3F6206	2026-10-02 23:47:47.365378+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	09b12003f1a5460582295d1cf85a76b5	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-A02D3805B551	2026-10-02 23:47:47.554245+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	9cff9df3730e4d5cba0d895ff5bad8aa	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-AD5D9ACB53DD	2026-10-02 23:47:47.840832+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	c53faf5b9736441bbd25ccadba377bfd	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-7D32E0A9A709	2026-10-02 23:47:48.132723+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	14f8511d75494d978168766b34d08fee	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-ABA4FFDD230D	2026-10-02 23:47:48.279098+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	818cf3eff52d422797edac155a8764fa	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-1F0F00F7CA62	2026-10-02 23:47:48.458708+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	f2e188fe3fa14bc7bda8fc2e65a6ae97	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-BBBBA674A22F	2026-10-02 23:47:48.771247+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	36cf53b465274916ad88a5727a2b6ddd	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-5E655070ADAE	2026-10-02 23:47:48.783731+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	dd99e8977d8e4a819114b4131f204053	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-6FEB83E8D637	2026-10-02 23:47:48.791499+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	4c4b711eac93481dbeecbaa1b77ef96e	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-063D791D2C6D	2026-10-03 13:46:23.129786+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-207C803C12	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	4615f072c2eb4f1aad6f8d9d3e74b9e0	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-9E09FD085603	2026-10-03 13:46:23.132044+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-207C803C12	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	7fd52ad176194ba5ae1d77ead1c4e613	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-B1A9C2330BF7	2026-10-03 13:46:23.142346+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-8FED700CB1	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	629bd8cf374a4a5aacfbe4e8e340e515	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-6E9110144186	2026-10-03 13:46:23.14466+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-8FED700CB1	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	19445480c33e4e01815af815cbc69f56	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-65CD476746F5	2026-10-03 13:46:23.154484+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-A4BB504351	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	508d6274953047699744b79baeb2524f	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-810CA86E7FE7	2026-10-03 13:46:23.156649+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-A4BB504351	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	1eb15394fb8e401481a09d1c559795b9	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-D2DFB83E1A9B	2026-10-03 13:46:23.158884+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-A4BB504351	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	92e51fa3bbee493f8172a485325674bd	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-A895468B40D7	2026-10-03 13:46:23.16895+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-25503F7F5A	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	67707e84ef16400784efd77746f5aa40	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-655649468E0B	2026-10-03 13:46:23.171227+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-25503F7F5A	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	ae92b0d4f7c043d98568fe783b5c3833	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-152E042137E3	2026-10-03 13:46:23.209705+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-0C10DF7866	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	7d8d4bb13793412ebdd65c39ec9c5411	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-46F3DA3AB0A6	2026-10-03 13:46:23.212486+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-0C10DF7866	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	c07e2d177c4a409e8c5051dcdd5a43ab	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-2526A6E3CF71	2026-10-03 13:46:23.249991+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-45BBE2B261	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	10f4094dc9c84a04acd16fcc3c547f35	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-65D61FE7E02D	2026-10-03 13:46:23.252734+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-45BBE2B261	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	a2b13e234e9c409481afa1b447d5fb9f	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-D9D3AE303C4E	2026-10-03 13:46:27.344415+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-7BD4953C39	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	d4e0b295e0d74acaab3b1b19a59cee5f	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-AFB5BCD8E1DB	2026-10-03 13:46:27.366379+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-7BD4953C39	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	ed0a4c3d63b84a619f989a38d36893d7	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-305E07B51311	2026-10-03 13:46:33.382077+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	1512163360714805b0b5852196b30792	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-76911AB73C6C	2026-10-03 13:46:34.818057+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	58b1a907a7f44c3fa62b940b95c8cf68	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-97D673465769	2026-10-03 13:46:34.945771+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	a1dc25350d6548c988a77568cece0ad1	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-1D1AA6F6D975	2026-10-03 13:46:35.06264+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	335b2e8e35414a2591c8a1632399fffd	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-D0DCB2F75971	2026-10-03 13:46:35.31256+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	92a40a3251094caa9d4ae16097490dd4	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-F0D4597E626E	2026-10-03 13:46:35.61488+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	2ba3d0d796de460c973f5c0ff16e0105	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-0A2356673B93	2026-10-03 13:46:35.760693+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	6c9d2990770e496b91e65ca22db5054a	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-9411DFFE7FE2	2026-10-03 13:46:35.894937+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	7af7088615f144269cda96717f85bbe7	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-A23B94197656	2026-10-03 13:46:35.907912+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	288ad1580442456895ecd2ed4c4489a0	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-BE2BE0332E88	2026-10-03 13:46:35.921046+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	47b2b4a07348443c81a65627bada9561	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-A440E581B53A	2026-10-03 13:53:11.922873+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	DOC002	{"status": "Active"}	\N	\N	b94da248a9744e37a43622d4f6a555e7	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-EE5F49795886	2026-10-04 14:48:07.06651+05:30	admin	SLOT_CREATE	slot	0	{"doctor_id": "DOC003", "doctor_name": "Dr. sufian", "date": "2026-10-05", "start_time": "10:00 am", "end_time": "10:30 am", "status": "Available"}	\N	\N	d2d894ddf65c4a0481bbb8ff5339bdbb	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-E78C6E86329F	2026-10-04 14:49:07.868301+05:30	admin	APPOINTMENT_CREATE	appointment	TKN-0009	{"patient_id": "PAT-E951FE619734", "patient_name": "mozammel", "doctor": "Dr. sufian", "date": "2026-10-05", "time": "10:00 AM", "slot_id": "S1", "amount": "900"}	\N	\N	192c240f47db4ab7aea2c665ac4b444e	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-1498FA167B17	2026-10-04 14:56:06.161601+05:30	dr_sufian	PRESCRIPTION_DRAFT_SAVE	prescription	RX-29E2D843CC	{"patient_id": "PAT-E951FE619734", "appointment_id": "TKN-0009", "status": "draft"}	\N	\N	f40a7b5732c14168a364c645029b0b81	2026-10-13 16:54:47.189831+05:30	2026-10-13 16:54:47.189831+05:30	default
AUD-1745011736A6	2026-10-04 14:56:06.20332+05:30	dr_sufian	PRESCRIPTION_FINALIZE	prescription	RX-29E2D843CC	{"patient_id": "PAT-E951FE619734", "appointment_id": "TKN-0009", "version": 1}	\N	\N	e0ce52e3287848ca819711135bc805b9	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-049FD7801F47	2026-10-04 18:52:07.441678+05:30	admin	SLOT_CREATE	slot	0	{"doctor_id": "DOC003", "doctor_name": "Dr. sufian", "date": "2026-10-06", "start_time": "10:00 am", "end_time": "10:30 am", "status": "Available"}	\N	\N	621a4b1db971450ba88b518ab6ebf736	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-1EDA9B15C873	2026-10-04 18:53:12.862984+05:30	admin	APPOINTMENT_CREATE	appointment	TKN-0010	{"patient_id": "PAT-DFFF93C77BB2", "patient_name": "tasjin", "doctor": "Dr. sufian", "date": "2026-10-06", "time": "10:00 AM", "slot_id": "S2", "amount": "900"}	\N	\N	a682508c9c7d480bb9deb5805b78f953	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-8CA8418AF288	2026-10-04 18:54:26.620982+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	DOC002	{"status": "Inactive"}	\N	\N	2473592b4ba84f7f8734b33087c1a224	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-6F31D5159780	2026-10-04 18:59:21.238127+05:30	dr_sufian	PRESCRIPTION_DRAFT_SAVE	prescription	RX-F36FD9B1EC	{"patient_id": "PAT-DFFF93C77BB2", "appointment_id": "TKN-0010", "status": "draft"}	\N	\N	493738ad5ef84394880dc52206b7866c	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-E6D273620316	2026-10-04 18:59:21.250537+05:30	dr_sufian	PRESCRIPTION_FINALIZE	prescription	RX-F36FD9B1EC	{"patient_id": "PAT-DFFF93C77BB2", "appointment_id": "TKN-0010", "version": 1}	\N	\N	b87a700d1e594572b03ba7d93a7f064d	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-5E7BDED55631	2026-10-05 13:43:10.926508+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-A22B67C139	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	f30906d2fa514413b95bec0d4e43c89d	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-58BEDD57F7D1	2026-10-05 13:43:10.943481+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-A22B67C139	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	3954dcb153f94dbeb69c8d08ec28eb6f	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-746FDA2EF33C	2026-10-05 13:43:10.960204+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-A22B67C139	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	a7fc61b7470f4b7b944acf9e7c8e4cf9	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-F351F673EB54	2026-10-05 13:44:01.166941+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	f22d1c87b8964ffda938e90a1889bfef	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-1377E4666817	2026-10-05 13:44:02.326384+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	85883e71abd3441bad3af33872af6023	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-BB30FC4F0031	2026-10-05 13:44:02.57642+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	9b5c12566c404618ab38f114798ef82c	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-EBC42501E545	2026-10-05 13:44:02.69431+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	931d417c96ac483bbdcae1ed0c2b1791	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-8587E8A52527	2026-10-05 13:44:02.907865+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	1c96d1a1e0b94f6c88a088ba671fbf0a	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-2EDE08DF9A16	2026-10-05 13:44:03.014479+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	2c928a5af098498fb463c4ffc6be11aa	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-7A75D4DD5BF0	2026-10-05 13:44:03.146626+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	3f667fa7288841c8847bf7322dca2ab7	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-DA616293F5B1	2026-10-05 13:44:12.114487+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	40260a3602144ea3bc93258f7c6bd655	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-109A293980B4	2026-10-05 13:44:12.130294+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	e12f6d8afc0440e2b9897999d131df7a	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-964ED29061C9	2026-10-05 13:44:12.142813+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	86dc0ca540ed4b299a593ddfb93140ba	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-59F2E57A135E	2026-10-05 13:44:19.046237+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	a7be7df3899047168421d74ad817308d	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-AA743573FF55	2026-10-05 13:44:19.1372+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	d82bba1b0359406cab5aee3811af27a2	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-A795B2D987CD	2026-10-05 13:44:28.673232+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-AD8FD70725	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	40e113f11211454989fad7ebcaa3c09a	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-9D456AEFD988	2026-10-05 13:44:28.686719+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-AD8FD70725	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	6e84a62aada04ffd8c7cc7789f3ee5c7	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-F6EF46096BFB	2026-10-05 13:44:28.724979+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-AD8FD70725	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	661f6116debf47668ac612d608d0cad4	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-35FB71E016C4	2026-10-05 13:44:41.343509+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-9DFF0518F8	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	340b708b90e24f82b67f39b4e6dd9524	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-A0460BBC120F	2026-10-05 13:44:41.34718+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-9DFF0518F8	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	86f39e17c2734cda87d86085a6d83416	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-93CDF330325D	2026-10-05 13:44:41.363576+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-D05F5F58B0	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	5428d3ee491847a58169aed4c39e93bc	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-C21729710F52	2026-10-05 13:44:41.367108+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-D05F5F58B0	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	993135a9b5f1481ba9117dd8994ceb8e	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-20E3D7F8E6E7	2026-10-05 13:44:41.384082+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-EEA3B42446	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	ca6a70da574047e6821674dbe1c87a4d	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-02053AB4773B	2026-10-05 13:44:41.387083+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-EEA3B42446	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	55cc17bfb8cf4ec98b620d00be1942c4	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-7301D203E7A2	2026-10-05 13:44:41.390081+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-EEA3B42446	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	56f426aa627c476ca6ea076992b8a0ec	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-F8C796BEEAD2	2026-10-05 13:44:41.406503+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-83E1610FEB	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	157c8f1403744895921e0bb8ed3909f5	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-CB2E60B47B85	2026-10-05 13:44:41.409506+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-83E1610FEB	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	146f5d3b897042bdbc541bf933c8705a	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-5AC69C60A592	2026-10-05 13:44:41.539812+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-CDE11391F1	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	7b545c533a224b459b811542c8b1e7b9	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-FDEBA6FB3B84	2026-10-05 13:44:41.551868+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-CDE11391F1	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	d6de5deabb9945939cc4909093a48186	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-FED9E9AA2E94	2026-10-05 13:44:41.6+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-48EA3FE19A	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	abef661eea5342b2b1fb2cfedb30b900	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-E299FB5CC146	2026-10-05 13:44:41.604991+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-48EA3FE19A	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	29d4b9dcd80846a388439ad60bf2595f	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-8CAD3CDAE979	2026-10-05 13:44:45.513714+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-1B61B5740A	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	892305fd789442b6b9065a65d2352d3f	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-740DF1070EAB	2026-10-05 13:44:45.529994+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-1B61B5740A	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	dcf5c072e6f74e7f9d61308b8c7bf277	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-51F66D41CDBD	2026-10-05 13:44:53.750947+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	6957a353ae17413282108db6780d3e97	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-B1B07741586D	2026-10-05 13:44:53.770105+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	aecc4874122a4c0db2fd6d1ea6b13791	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-F6832792DB73	2026-10-05 13:44:53.778842+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	93b303d4a5624e4f93de26e7dd6ce6c1	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-EE5D6420FE37	2026-10-05 13:44:53.909439+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	61161165964941b498a93f5890cbea10	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-3B0B8FA3A042	2026-10-05 13:44:53.913611+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	855fe448fa954362916e6f27839975bd	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-59BA13C9F2F1	2026-10-05 13:44:53.929507+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	5b6db920ac194f8bb18410df6c7ab9b4	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-0B19E86C6044	2026-10-05 13:44:53.936205+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	3e7af12474ab43218a216c5a4294c849	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-153FB7DB218B	2026-10-05 13:46:24.349468+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	9d1e9e334e354474b78b092de29a2925	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-C683BD335E25	2026-10-05 13:46:25.332957+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	6683a7d319424c3d961e1c6292cf3edf	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-465D140F0073	2026-10-05 13:46:25.61525+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	4c91dc4df0bd431da24599bfbb8ca1f0	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-8E1C2E8CF7E1	2026-10-05 13:46:25.731906+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	16d0ed0c924b40829ee2f2af21088824	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-0A10B4824D5F	2026-10-05 13:46:25.952314+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	4f192b1506da4831bf0beec824783d9d	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-CC4A0EE12359	2026-10-05 13:46:26.04802+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	6d0014f53ea1478dba69d1fa166c493e	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-7A53631A172A	2026-10-05 13:46:26.31506+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	01bb02e70edb41188b2bfc35f502f3a8	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-0978774EE458	2026-10-05 13:46:27.47813+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	7146005375f942ceb4cec038c32762d6	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-437A24607B9A	2026-10-05 13:46:27.489828+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	69b5ef6019544867b079c0b42599f161	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-21D1948FEF9B	2026-10-05 13:46:27.500258+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	a48a5182886a4752a88fc16d338d73d8	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-AE1350AA1566	2026-10-05 13:46:30.102708+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	6f4107f1b6ef4dfeb7d5cb49198c0fae	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-39C60482B283	2026-10-05 13:46:30.153805+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	a216f554c0e04d5d93615104c37bfba8	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-ECF9711ACA4C	2026-10-05 13:46:37.29564+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-940D0E29DC	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	4c1979366c954082b4895130c33626fe	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-45DD74B1748D	2026-10-05 13:46:37.311142+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-940D0E29DC	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	8d8aafe37c7c42a4b8fff85b90887c67	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-A6F8AAA697B2	2026-10-05 13:46:37.333271+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-940D0E29DC	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	072ae6371ab2489383c6616c7f967900	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-A1A2AB8FE88E	2026-10-05 13:46:44.443653+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-2EE0BA56ED	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	24336130ecbc460ea3074206059005c2	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-E6C2E5E8AFD0	2026-10-05 13:46:44.44579+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-2EE0BA56ED	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	40a707fd764c4044a1bf2f07e19f0f55	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-513AFF3425DA	2026-10-05 13:46:44.454514+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-620E14A24D	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	a581d5827a01446e94a8b44b829639e5	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-F4C8BF5F5182	2026-10-05 23:38:45.165234+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	5c177d9afc334cf98f7ecfec11155aef	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-5F3E28A506B5	2026-10-05 13:46:44.455567+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-620E14A24D	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	9d4fafab9b0046d58b58493c6dcdbe61	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-2E524013F95D	2026-10-05 13:46:44.460444+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-0D3ED1B1AA	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	a921cfe960e94e1787b4ae9ad4c8ae8f	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-84EB20A344A2	2026-10-05 13:46:44.467566+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-0D3ED1B1AA	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	5833502f16f340a3b228f8d31b1dcfd4	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-17967B0B1F6F	2026-10-05 13:46:44.469579+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-0D3ED1B1AA	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	965740e03e9b4cb0ab88ebab0237fd2d	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-829E9EDF0B8A	2026-10-05 13:46:44.485068+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-D4BA92BA28	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	13c59f2fa7f04113b6728589e96e3db9	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-3166F57DCC47	2026-10-05 13:46:44.485068+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-D4BA92BA28	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	3b2e81167ccc4868a392d45edd35b4e6	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-317064052C20	2026-10-05 13:46:44.514567+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-913004AB23	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	2891b5dd6a254181994793c462945402	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-D2F644BEEE83	2026-10-05 13:46:44.526068+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-913004AB23	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	9c010383292147c2b86f21311531336e	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-48DF94167D41	2026-10-05 13:46:44.560989+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-BCCF403D91	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	b06f184501464531855458792c5e914a	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-D840E0A5B1B4	2026-10-05 13:46:44.56322+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-BCCF403D91	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	77f23f61f2cb40fb9ee5c643b26bf370	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-5792553C8C8E	2026-10-05 13:46:47.075243+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-B4CFB1E075	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	cc11f9a75e9f484aa11f0245386d828a	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-A98AC5D52736	2026-10-05 13:46:47.085091+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-B4CFB1E075	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	ee8b6a4c2420400f85a5e523da6df4b1	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-93EEE63D16E5	2026-10-05 13:46:56.470216+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	89e3ba3a95d64d43918b918349322c09	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-07B69549DA79	2026-10-05 13:46:56.488251+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	8463755a24ac40698c52c8534cc55dfe	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-FEA4F93878F3	2026-10-05 13:46:56.498243+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	6e085eec095645daba535e1d980fea64	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-4EDABB3E342E	2026-10-05 13:46:56.69134+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	9d7c694648ea49cc98476ccfb3a43d7e	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-534240A6F3FF	2026-10-05 13:46:56.697342+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	f78077ea0a9f415faa642633ef7d5643	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-D48AADC7CA69	2026-10-05 13:46:56.726838+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	82827210740d466785a017fa8a1b8091	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-D66408E58B7C	2026-10-05 13:46:56.737306+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	b4ee4c113ae84ed88f2f0d9cbc1170df	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-BFA19984C715	2026-10-05 23:06:42.710938+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	51f3ed237f3b4790bb74d1ff8c6f2ae8	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-4509EE876B6D	2026-10-05 23:06:44.481562+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	618acab17c4b4ddcb77db5294c84f02c	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-11BFB13042A8	2026-10-05 23:06:44.714744+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	1643dac6a2794d94aebc7770c2a01bdf	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-C1CED3E7CD0D	2026-10-05 23:06:44.907384+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	3955cc60b06e4bdd8115fb0083caa91d	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-8804E4DD3CF9	2026-10-05 23:06:45.293519+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	27515bab85eb4febaf3ff25fb622f149	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-BD4DEB52F94E	2026-10-05 23:06:45.493905+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	3bb9779dfb8f4fc3b5668ac57afe90b9	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-2752E2E5A8CD	2026-10-05 23:06:46.086877+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	5358e23d174a4988b6cf573db884f93f	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-EF5D83DCAD0D	2026-10-05 23:06:47.393524+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	c6497610dcdc4744af539bd9894f31c8	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-49FF05C04FF7	2026-10-05 23:06:47.407017+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	30d4f616ced4426dac5000231cb14330	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-FA86535016AE	2026-10-05 23:06:47.419113+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	b8eb77962ecc44ae9bafdf691d093d48	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-0140EE7CC9E8	2026-10-05 23:06:50.99371+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	60c18c06fcb34e01add8259ed8454939	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-8B562D310A45	2026-10-05 23:38:45.469351+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	9ca542f00c7547ef98f052688148d3e8	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-23182220C3E2	2026-10-05 23:06:51.047252+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	78cad0ceee3246de87d7a546d39d2675	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-00BD6CB6B582	2026-10-05 23:06:58.319073+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-936616CA96	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	80d711b0acdc4ef396e43bdd300e3d86	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-0564A5593FD7	2026-10-05 23:06:58.323158+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-936616CA96	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	d210e573f14b49fca1007eb8837142d1	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-86217E111F90	2026-10-05 23:06:58.361978+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-936616CA96	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	9e06aea669e14e7698c89292752123ed	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-37339D91E759	2026-10-05 23:07:07.046807+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-568DF0114E	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	3746ee0ef5304bdd8c241452a1739bf4	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-BDC9DF6102CE	2026-10-05 23:07:07.047973+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-568DF0114E	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	595833a0806a43dabeb543a53265a9f0	2026-10-13 16:54:47.304046+05:30	2026-10-13 16:54:47.304046+05:30	default
AUD-4FBB5E4B37CB	2026-10-05 23:07:07.059481+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-212FA6942D	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	7d95f444752f4ae3bd12c7dcc2a35c24	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-D8CE8C6B4256	2026-10-05 23:07:07.062365+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-212FA6942D	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	a6250fbbbef74c1c8c0791299cddae43	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-B1D9DCBE3087	2026-10-05 23:07:07.0767+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-C4F04DB622	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	58e9c96767614bc0a87c1bdf8da950dc	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-D754FCD8F5CE	2026-10-05 23:07:07.0767+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-C4F04DB622	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	81b054891fbe4969bc153faa1ccc8abc	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-F9FEB06AB47F	2026-10-05 23:07:07.081839+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-C4F04DB622	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	abc54cb4ce574ce4a28747ea5ad98af2	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-4A76E3303771	2026-10-05 23:07:07.092037+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-4811890924	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	b0624976ed024c0483bebae4fc8cac67	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-22B8CDEDC40B	2026-10-05 23:07:07.093705+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-4811890924	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	d1a73f00ec634f50b30a9bd3a3e6ba91	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-3653268E0E7D	2026-10-05 23:07:07.120029+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-F9DB696BDA	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	996a3c369e0d41be8609ac13dacd38f1	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-D51CE0B2440E	2026-10-05 23:07:07.123237+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-F9DB696BDA	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	3a30ee785ba047b8ab329c430455d326	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-072CC7D455B8	2026-10-05 23:07:07.167276+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-BB272FC29C	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	e3c4635c9f3c45d9831d3e39384d5499	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-CD17F2CDFB26	2026-10-05 23:07:07.1696+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-BB272FC29C	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	2e62832a314e4864a2791089231f5ba3	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-B1084F92B1C6	2026-10-05 23:07:10.333137+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-0A531144C6	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	88fe95bd6e46411f8c53a197880bb46e	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-E1A5E3889125	2026-10-05 23:07:10.352707+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-0A531144C6	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	17220057a1ae44dc9a4b954d9a2d54fe	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-3360DA3DE5B6	2026-10-05 23:07:19.873049+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	55513dfc3daa4ab29cc2f1b21938d656	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-9E2C4448B8B6	2026-10-05 23:07:19.885049+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	0eebcbe932fb4122a485cf63159a77dc	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-26BC802438A8	2026-10-05 23:07:19.891624+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	b805c93dbb404d8db0ecf91fed8dc9a3	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-1DDD040C3E1C	2026-10-05 23:07:20.106135+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	f4f58c943027479e9cf29e3bf35d792f	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-31F34FCE520C	2026-10-05 23:07:20.110158+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	ab46613ee5e048b4a0a33ffb698e638c	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-01FFCD2E5EB1	2026-10-05 23:07:20.135271+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	cf53beeb284141859baa27429b5a4878	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-5A97AB76FFD9	2026-10-05 23:07:20.153906+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	032c61bd92734131a56f2de42342df37	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-CB34EC22E7BC	2026-10-05 23:38:43.333806+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	ebe80264f633480aa04e8c4c592bb0d7	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-5C355B368AF1	2026-10-05 23:38:44.653803+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	5676c585c48548bca53bf3dc6bba0c1b	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-2611DC3A8293	2026-10-05 23:38:44.778335+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	ba1319a1806745d2985b74cf9512fa39	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-BCAEC4131D32	2026-10-05 23:38:44.921035+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	538daf06e49846f499555218e9e9d9ea	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-26E4D10CEC78	2026-10-05 23:38:45.589808+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	627ba48508f944769bb30a605cdc7a0b	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-A9CAA43A56C1	2026-10-05 23:38:46.787557+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	cdcd6a20bdc644d985213b842d0dcdd4	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-309223FC698A	2026-10-05 23:38:46.797608+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	35133579d5154ac7b3549d4e620df61d	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-6382632B1B21	2026-10-05 23:38:46.80677+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	525c4d5055594a6ea873dd02f72954b4	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-10D5A1F42591	2026-10-05 23:38:50.276475+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	c3e95c05dfe64380b7f221f89dbe472b	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-08242C5BFF71	2026-10-05 23:38:50.400706+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	b4380d46a8cb4fb18d14160037c14275	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-74A81387256E	2026-10-05 23:38:58.325835+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-A7F3304DA3	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	8d3c4a7588e3452d89d70bf405007fde	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-47487D4F0075	2026-10-05 23:38:58.334739+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-A7F3304DA3	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	27b62526d705445ba60853b159bf0323	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-FC87F469E3D4	2026-10-05 23:38:58.36698+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-A7F3304DA3	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	869629265eed4091a52a5dd825ba889b	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-E9F6C4E70C84	2026-10-05 23:39:07.058129+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6243423DEB	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	e96f80112f4f4891bd9aaf2588107f0b	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-9CD1285CA6C3	2026-10-05 23:39:07.060339+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-6243423DEB	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	bc281b8422814c5483306ca7df2b5d50	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-621F49C665AC	2026-10-05 23:39:07.072134+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6B74486F03	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	affb37706b104e1590242492e6958a09	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-307A2B420D2A	2026-10-05 23:39:07.074355+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6B74486F03	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	96ffc89613d547bfbccb62bd26328c47	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-27B9BF02FD0D	2026-10-05 23:39:07.085108+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-82DC827397	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	4377e21a6eda47d5b8f305497a4fe5b5	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-FCBECFE3244F	2026-10-05 23:39:07.087942+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-82DC827397	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	44540306c0ec4e35abc9f75e255a4b62	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-462F10B4A788	2026-10-05 23:39:07.089957+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-82DC827397	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	1dce63bcb71e4d49be6a84932ed92be2	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-F46C724CAB60	2026-10-05 23:39:07.102013+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-5E4B1A1905	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	62d33f85a90d4d938f7617110d78b8da	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-29F42F17EED1	2026-10-05 23:39:07.103659+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-5E4B1A1905	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	881371ed7e51491ca0226eb7ccd9fec7	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-17A60AACD4CA	2026-10-05 23:39:07.138943+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-EB52093334	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	5a595063e4cd4bd3833b3fae9819dd86	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-0FCB627BCF81	2026-10-05 23:39:07.140969+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-EB52093334	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	f335138d7a0643db8f7f44cff6cfa02a	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-DC9E538DDD51	2026-10-05 23:39:07.182093+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-1639C958A5	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	0675eb9b05b54b2c96a94e1fd562ca71	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-5E4C46BA2354	2026-10-05 23:39:07.182638+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-1639C958A5	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	e0ab44d88cab45b586726f451a7e7db6	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-4D0D2D6D58BD	2026-10-05 23:39:09.96406+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-C185E2453F	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	f5d992c624574a1fba1b17bda9a03c5f	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-430E2DAB55D4	2026-10-05 23:39:09.988469+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-C185E2453F	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	14ea8a602c5642bd83bbc979ade63642	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-485C11E9C718	2026-10-05 23:39:16.327013+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	90fd0060d20542e08a03edffc36f4ea8	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-4955AA1E70DF	2026-10-05 23:39:16.591491+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	cfec2ae61d1b4b0794c3e9c05dc4d18e	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-FDFD6159EE39	2026-10-05 23:39:16.598256+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	bf507c8834364a87bc2cbeaa71fe2ebe	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-9E5CA04ABD3E	2026-10-05 23:39:16.704429+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	45a6f9af1cdd480ba23815f730462131	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-1DE2EC12F247	2026-10-05 23:39:16.709119+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	0b83d588213642e2a2afcc19bc31c8d7	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-76F04672D10A	2026-10-05 23:39:16.728967+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	5bfa66e12bce493d9c94c341c3857bad	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-93B037CDA105	2026-10-05 23:39:16.73625+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	303a4505102b425fa62f9b1f3c1d0670	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-71D1955251A0	2026-10-05 23:50:37.676584+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	fb0634a96d7f4fd792c1dee6309dda45	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-2B0A24D06869	2026-10-05 23:50:39.124261+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	b72333ebb61546fe83381e51f053de8b	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-AFE43A267750	2026-10-05 23:50:39.263294+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	1ba6ac4c3e5a4ba0b8cef7e173f29f06	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-BC2CC9A524B7	2026-10-05 23:50:39.416247+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	9282c6e85f464b06891f5a63c9987dba	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-083433D0ABD4	2026-10-05 23:50:39.678123+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	691f0b0272e34b99b96dfb31b330a25a	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-9D93290EB7FB	2026-10-05 23:50:39.988432+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	a05a37b98eb846f692fa8e60246a3ad4	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-FE7B216FA21A	2026-10-05 23:50:40.129345+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	ef4e3e040fd04aba90a72a560315a8ea	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-54FBED3DB7E3	2026-10-05 23:50:41.359936+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	e921bd501a714f2fa226f31bdc230d84	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-D5DCE74EE493	2026-10-05 23:50:41.371926+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	f3c62462f7ed434d8524a84543ab70aa	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-315E416D82E1	2026-10-05 23:50:41.388642+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	7ca2091fdfb54608896a19955de622a3	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-981F7C846B10	2026-10-05 23:50:46.070396+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	c5c07b68019f45d8a82829de94961c03	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-66EA1C5CF015	2026-10-05 23:50:46.14235+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	b74a052a6e914fe7a249e2a15860e774	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-FBB2F56BF0F8	2026-10-05 23:50:54.308581+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-F9324E1DF3	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	2ed83026a2d54a3196273adf66a1ad73	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-822A9639CE03	2026-10-05 23:50:54.32474+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-F9324E1DF3	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	dfebd448b6fe4a388dccedd71f75c678	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-52CD0B8B328F	2026-10-05 23:50:54.366281+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-F9324E1DF3	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	0ecb1ddc00c84c0fac736a250c347d66	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-87FAE12DA952	2026-10-05 23:51:05.740661+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6F639EBF2F	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	ae12c56dbe2641109fd2a2514574b76b	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-45EE9A7C3287	2026-10-05 23:51:05.742341+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-6F639EBF2F	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	70fae3c278f444b39ef078b38359df9a	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-66B8749E0906	2026-10-05 23:51:05.751839+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-25B3CE9429	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	e550238c89a04e45a9b0c54268ce268d	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-0186840043F9	2026-10-05 23:51:05.752956+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-25B3CE9429	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	ce8812f23dd643b99fb0b61e9562bff4	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-CEF7900F46E2	2026-10-05 23:51:05.759411+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-781546D8D2	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	7e068faf3cea4f758627f8cf501659dd	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-6852A5C8D4D5	2026-10-05 23:51:05.763611+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-781546D8D2	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	17465b1dd4d9445d8c4e7fa54431c98c	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-68E1AD6DFD25	2026-10-05 23:51:05.764625+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-781546D8D2	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	9c935d88da244aa4b98a67ec702c1bb3	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-9A0BE61F113D	2026-10-05 23:51:05.773548+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-7F481169A9	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	e601f598e36d4cc4a40f3b550e0813a4	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-747FA557B363	2026-10-05 23:51:05.775688+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-7F481169A9	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	b353f61097db49a89dc9b29df0f72252	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-94180568D6A6	2026-10-05 23:51:05.810404+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-8E8C8132A8	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	4c22bda818c6448e831edefe006f23d7	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-700ED522FEEE	2026-10-05 23:51:05.813448+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-8E8C8132A8	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	0ed8f913c79f4c668200956624fb0f43	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-85BD8D730717	2026-10-05 23:51:05.868093+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-15050051E9	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	38af8843820f4d75bad30d3d0f3c5580	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-26070790DFFC	2026-10-05 23:51:05.869737+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-15050051E9	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	96167b1233034a07b8d8f90f222ae813	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-75E73FA6C03B	2026-10-05 23:51:08.878953+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-9236DAA6D4	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	6a12b137d6d549379c582d67a0f65958	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-30FA3059DA0C	2026-10-05 23:51:08.903554+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-9236DAA6D4	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	f36542472b9e408282ac0857c289b7a2	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-E64B655A36EB	2026-10-05 23:51:18.409564+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	31174161827746ba9fb3eb63d424f373	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-2EF7AA29726D	2026-10-05 23:51:18.424803+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	84b46f80a1bf4b66985917c0f10681f7	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-E8A82C4A3A7B	2026-10-05 23:51:18.431393+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	ddb5b717082a439e9e33876f6928e595	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-E4E503F8B6AE	2026-10-05 23:51:18.552552+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	045aa5d1502440d1bd2bc2ccb34862c8	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-F77A755B7672	2026-10-05 23:51:18.556174+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	27328a918140463f81220dc061c0f6a5	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-022F53271CD0	2026-10-05 23:51:18.576238+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-06", "old_time": "10:00 AM", "new_date": "2026-10-12", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	c534a8d0dd8942e0a76bbbd1ff2fc941	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-CACE286FD57A	2026-10-05 23:51:18.587644+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	c12d8538bc0441e39c2b7b138f2ab06d	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-A0CB7C612C22	2026-10-07 22:19:24.253403+05:30	superadmin	TENANT_CREATE	tenant	clinic_inact_test	{"name": "Inactive Clinic", "status": "ACTIVE"}	\N	\N	1498a8e312dc4b1299363e4288e4065b	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-B5FD761583EA	2026-10-07 22:19:24.25844+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_inact_test	{"status": "INACTIVE"}	\N	\N	9a73538f2a854a26ad0649ba27040322	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-D7D11BD614DA	2026-10-07 22:19:24.808092+05:30	superadmin	TENANT_CREATE	tenant	none	{"name": "Hash Check Clinic", "status": "ACTIVE"}	\N	\N	07deb8904e9b4efcaf644b9cfe1b43c2	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-6BF99D612052	2026-10-07 22:19:24.912536+05:30	superadmin	TENANT_ADMIN_CREATE	user	hash_check_admin	{"tenant_id": "none", "username": "hash_check_admin", "role": "TENANT_ADMIN"}	\N	\N	545cb2757541463398967a5b0b2c716b	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-3158A0D80524	2026-10-07 22:19:25.174434+05:30	superadmin	TENANT_CREATE	tenant	audit_clinic	{"name": "Audit Clinic", "status": "ACTIVE"}	\N	\N	f3bfe9bcca1548f78e039fb4b4fedd8e	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-93F0281D05A5	2026-10-07 22:19:26.263881+05:30	superadmin	TENANT_CREATE	tenant	none	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	504de612676f455d8840c6d7ac2ed8ef	2026-10-13 16:54:47.420762+05:30	2026-10-13 16:54:47.420762+05:30	default
AUD-C3E1C3CE076B	2026-10-07 22:19:27.562587+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp_test	{"name": "Suspended Clinic", "status": "ACTIVE"}	\N	\N	1e6dea09858e414891973f380c69013f	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-70FAEF1D75A5	2026-10-07 22:19:27.564824+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp_test	{"status": "SUSPENDED", "reason": "Administrative suspension"}	\N	\N	9c5e9f69663f445d87db56b4c4bfe611	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-EA3B9903BC79	2026-10-07 22:19:28.074384+05:30	superadmin	TENANT_CREATE	tenant	clinic_act	{"name": "Clinic Act", "status": "INACTIVE"}	\N	\N	fb5784f9ba9b408c9f758b96641c3423	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-94BC4F7CF7D2	2026-10-07 22:19:28.082498+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_act	{"status": "ACTIVE"}	\N	\N	44e2dcdd149c42d0b1ff9c24a45cb451	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-68D38AA01039	2026-10-07 22:19:28.333963+05:30	superadmin	TENANT_CREATE	tenant	city_med	{"name": "City Medical", "status": "ACTIVE"}	\N	\N	1817fefa83c34eb18439324b4a04020e	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-320F1AA35D92	2026-10-07 22:19:28.434505+05:30	superadmin	TENANT_ADMIN_CREATE	user	city_admin	{"tenant_id": "city_med", "username": "city_admin", "role": "TENANT_ADMIN"}	\N	\N	fffe0de001a846379a25efa56fe92a73	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-CA2FDB9D245F	2026-10-07 22:19:28.942498+05:30	superadmin	TENANT_CREATE	tenant	health_plus	{"name": "Health Plus", "status": "ACTIVE"}	\N	\N	d41c29f7f8d6419eaff511bd78ba0ac8	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-78B1902DC287	2026-10-07 22:19:29.049403+05:30	superadmin	TENANT_ADMIN_CREATE	user	health_admin_user	{"tenant_id": "health_plus", "username": "health_admin_user", "role": "TENANT_ADMIN"}	\N	\N	ada504dd97924aa89a73b3eb5573d3ff	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-A745B0E32F5A	2026-10-07 22:19:29.298521+05:30	superadmin	TENANT_CREATE	tenant	lotus_health	{"name": "Lotus Health", "status": "ACTIVE"}	\N	\N	61aed4ee0c45493f9573acb1e125b470	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-1DDD6E6E23E6	2026-10-07 22:19:29.402639+05:30	superadmin	TENANT_ADMIN_CREATE	user	admin_lotus	{"tenant_id": "lotus_health", "username": "admin_lotus", "role": "TENANT_ADMIN"}	\N	\N	a187be8feed847b3b38547dcd58718b5	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-1F9DF07B1F0D	2026-10-07 22:19:29.704723+05:30	superadmin	TENANT_CREATE	tenant	clinic_deact	{"name": "Clinic Deact", "status": "ACTIVE"}	\N	\N	664de083718742468baa1185b94483ea	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-1EDBD479B787	2026-10-07 22:19:29.712212+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_deact	{"status": "INACTIVE"}	\N	\N	511842c0ca394db6b3348eab50f3e2a7	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-68CADEAB0C81	2026-10-07 22:19:29.948175+05:30	superadmin	TENANT_CREATE	tenant	none	{"name": "Green Valley Medical", "status": "ACTIVE"}	\N	\N	f3bff4976d7b4092897005054b309b40	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-18559F676895	2026-10-07 22:19:30.396798+05:30	superadmin	TENANT_CREATE	tenant	clinic_react	{"name": "Reactivate Clinic", "status": "ACTIVE"}	\N	\N	8394cd43a895467482153866934d0c83	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-D45DDE6D4643	2026-10-07 22:19:30.403726+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_react	{"status": "INACTIVE"}	\N	\N	23ad37d2b2ab49eab266198145cc4e1e	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-4377DB3F2426	2026-10-07 22:19:30.412291+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_react	{"status": "ACTIVE"}	\N	\N	dbb0416d638e41098b2928171d0d78dd	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-6C0B2BC719AD	2026-10-07 22:19:30.664152+05:30	superadmin	TENANT_CREATE	tenant	none	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	7da12a38ce6d4baa94dd3e493a68f5ab	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-E56D2F896A4F	2026-10-07 22:19:30.842392+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp	{"name": "Clinic Susp", "status": "ACTIVE"}	\N	\N	886782c76cfc416fb12907f7597cb879	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-E500E0344CF4	2026-10-07 22:19:30.845446+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp	{"status": "SUSPENDED", "reason": "Billing non-payment"}	\N	\N	7dc65ab2bcd04301b558fa186125bb23	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-02F6CE4AF0ED	2026-10-07 22:21:21.970757+05:30	superadmin	TENANT_CREATE	tenant	cln_apollo_care_cent_7bb273	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	e10466d86504491cad1cc7315f2f718d	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-FC2F340C3E9D	2026-10-07 22:21:43.655066+05:30	superadmin	TENANT_CREATE	tenant	none	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	66d77b5d5343459082a87a20178c6315	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-D3D430B7F0F3	2026-10-07 22:24:43.715332+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_act	{"status": "ACTIVE"}	\N	\N	e23493f364b1416cb78b3ba691b6c407	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-224B5C1D06AF	2026-10-07 22:21:56.912056+05:30	superadmin	TENANT_CREATE	tenant	none	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	044f9dca3eae4b118bbcd04b173a04eb	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-2CCAE2A5CD98	2026-10-07 22:22:20.899942+05:30	superadmin	TENANT_CREATE	tenant	clinic_inact_test	{"name": "Inactive Clinic", "status": "ACTIVE"}	\N	\N	aa7bbfac58004eaa9e72bfaff2adfb1e	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-E5F53922083C	2026-10-07 22:22:20.908547+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_inact_test	{"status": "INACTIVE"}	\N	\N	976860fb42564438817cd305d1ca8bb7	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-6A435F7BF911	2026-10-07 22:22:21.443948+05:30	superadmin	TENANT_CREATE	tenant	cln_hash_check_clini_630a6a	{"name": "Hash Check Clinic", "status": "ACTIVE"}	\N	\N	2d8aa6af993c4861ac8a441125f921f1	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-1889744D4799	2026-10-07 22:22:21.562199+05:30	superadmin	TENANT_ADMIN_CREATE	user	hash_check_admin	{"tenant_id": "cln_hash_check_clini_630a6a", "username": "hash_check_admin", "role": "TENANT_ADMIN"}	\N	\N	e7d4e978fe984ec3824304aa3263546a	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-F93A16506087	2026-10-07 22:22:21.804931+05:30	superadmin	TENANT_CREATE	tenant	audit_clinic	{"name": "Audit Clinic", "status": "ACTIVE"}	\N	\N	8af7705804324ab4865329ab7fc587a6	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-80F24C296775	2026-10-07 22:22:22.808799+05:30	superadmin	TENANT_CREATE	tenant	cln_apollo_care_cent_91a623	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	031ea9262a454fe482cb7732b2a412ef	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-8FD281DA0828	2026-10-07 22:22:23.79279+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp_test	{"name": "Suspended Clinic", "status": "ACTIVE"}	\N	\N	c45b05b4a7574088ae741de8134d5623	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-8FB1FD74E415	2026-10-07 22:22:23.800686+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp_test	{"status": "SUSPENDED", "reason": "Administrative suspension"}	\N	\N	9ab78cb0d8294c8c953b670943a24400	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-FEAD8362D502	2026-10-07 22:22:24.330074+05:30	superadmin	TENANT_CREATE	tenant	clinic_act	{"name": "Clinic Act", "status": "INACTIVE"}	\N	\N	13269d294c8e43acbc6a83f9476967ef	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-44406E9FC720	2026-10-07 22:22:24.331992+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_act	{"status": "ACTIVE"}	\N	\N	b5d3d094773247ccb4279da11d74ecd4	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-603A5D728B21	2026-10-07 22:22:24.575094+05:30	superadmin	TENANT_CREATE	tenant	city_med	{"name": "City Medical", "status": "ACTIVE"}	\N	\N	deef3a1acee74cd9a5131cc55b831974	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-8DED8D19B624	2026-10-07 22:22:24.674742+05:30	superadmin	TENANT_ADMIN_CREATE	user	city_admin	{"tenant_id": "city_med", "username": "city_admin", "role": "TENANT_ADMIN"}	\N	\N	dd70b8294f0a478fa4a44dbea0666d2f	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-E1F7BDED86AB	2026-10-07 22:22:25.175115+05:30	superadmin	TENANT_CREATE	tenant	health_plus	{"name": "Health Plus", "status": "ACTIVE"}	\N	\N	edd99ca4332f4fd9ab22ddea728f9f07	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-1B4A881D39E5	2026-10-07 22:22:25.292118+05:30	superadmin	TENANT_ADMIN_CREATE	user	health_admin_user	{"tenant_id": "health_plus", "username": "health_admin_user", "role": "TENANT_ADMIN"}	\N	\N	c09eee98c0e44effa7b1ec24ece05c70	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-5BD035F7FA5A	2026-10-07 22:22:25.582661+05:30	superadmin	TENANT_CREATE	tenant	lotus_health	{"name": "Lotus Health", "status": "ACTIVE"}	\N	\N	5cbf96ed9eb347d5a275839ad91ae9de	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-9D6A4CE794C0	2026-10-07 22:22:25.691032+05:30	superadmin	TENANT_ADMIN_CREATE	user	admin_lotus	{"tenant_id": "lotus_health", "username": "admin_lotus", "role": "TENANT_ADMIN"}	\N	\N	5470662161f94a93af66f706e5b001a7	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-4B67C377134F	2026-10-07 22:22:25.950684+05:30	superadmin	TENANT_CREATE	tenant	clinic_deact	{"name": "Clinic Deact", "status": "ACTIVE"}	\N	\N	94f46953717d4beb9c7ee47e1bc375a3	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-1DF3CDA3BF21	2026-10-07 22:22:25.957766+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_deact	{"status": "INACTIVE"}	\N	\N	e444f9a900fa4429b1416aa3590cb274	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-DCCB62126476	2026-10-07 22:22:26.220921+05:30	superadmin	TENANT_CREATE	tenant	cln_green_valley_med_7e20cc	{"name": "Green Valley Medical", "status": "ACTIVE"}	\N	\N	5b2fec2db7bb4a16912362ed36b67168	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-320147ADECA5	2026-10-07 22:22:26.770745+05:30	superadmin	TENANT_CREATE	tenant	clinic_react	{"name": "Reactivate Clinic", "status": "ACTIVE"}	\N	\N	7e5ddda7288548eaa7149fefb726a4ae	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-4544F697B7A8	2026-10-07 22:22:26.782046+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_react	{"status": "INACTIVE"}	\N	\N	ffa3bcefcf304d83946b996615830143	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-613946B63B03	2026-10-07 22:22:26.790802+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_react	{"status": "ACTIVE"}	\N	\N	725665cd4be744aaa82c624b7f3952d0	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-25FA765F7271	2026-10-07 22:22:27.015095+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_67bc30	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	e3118c3f11b14db89722871cf307fef8	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-6F4B49EF5E26	2026-10-07 22:22:27.02428+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_63d5d8	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	62672f1949404441bf4ca145d0ef7b02	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-8F9532A72141	2026-10-07 22:22:27.276283+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp	{"name": "Clinic Susp", "status": "ACTIVE"}	\N	\N	15559f03e0ce421591bf845ab88e1723	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-4536A4EB8D02	2026-10-07 22:22:27.284653+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp	{"status": "SUSPENDED", "reason": "Billing non-payment"}	\N	\N	cbc94596b8ea465e84e606ad97b9c6ac	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-D8CE86BD1C10	2026-10-07 22:22:57.829973+05:30	superadmin	TENANT_CREATE	tenant	clinic_inact_test	{"name": "Inactive Clinic", "status": "ACTIVE"}	\N	\N	27470e4124574c6592a29de9b8c1d1c5	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-4F85F62EEDA5	2026-10-07 22:22:57.835219+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_inact_test	{"status": "INACTIVE"}	\N	\N	24d595c6e3454d7a8b804ff6815a8727	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-B8F0D5E2278A	2026-10-07 22:22:58.352378+05:30	superadmin	TENANT_CREATE	tenant	cln_hash_check_clini_778369	{"name": "Hash Check Clinic", "status": "ACTIVE"}	\N	\N	d4e5634a644c4afc9066040647a780e9	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-B69984B6B136	2026-10-07 22:22:58.462088+05:30	superadmin	TENANT_ADMIN_CREATE	user	hash_check_admin	{"tenant_id": "cln_hash_check_clini_778369", "username": "hash_check_admin", "role": "TENANT_ADMIN"}	\N	\N	9d42c33c6e884efe84c572c45ea23707	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-C50A9C5D7769	2026-10-07 22:22:58.71806+05:30	superadmin	TENANT_CREATE	tenant	audit_clinic	{"name": "Audit Clinic", "status": "ACTIVE"}	\N	\N	bddf6cc8ecd840fb9c083cc2d0305b7a	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-3C241710F31C	2026-10-07 22:22:59.840841+05:30	superadmin	TENANT_CREATE	tenant	cln_apollo_care_cent_b2e22a	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	fb2e95ff26664350a8a965ed9a5bc160	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-FCA576F998F5	2026-10-07 22:23:00.742126+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp_test	{"name": "Suspended Clinic", "status": "ACTIVE"}	\N	\N	3e4fb618674448398bd1080a28733283	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-9BFD51C93126	2026-10-07 22:23:00.750949+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp_test	{"status": "SUSPENDED", "reason": "Administrative suspension"}	\N	\N	2094e11ec612441e96828fa9f6ed9a30	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-EFC7B95A3F6C	2026-10-07 22:23:01.252253+05:30	superadmin	TENANT_CREATE	tenant	clinic_act	{"name": "Clinic Act", "status": "INACTIVE"}	\N	\N	68f2ed7ce07c44f6963c63e68e0c185d	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-8CEBBD93FD61	2026-10-07 22:23:01.260726+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_act	{"status": "ACTIVE"}	\N	\N	55613ce553bd441885f7c47a588e6399	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-ADD1EFB73BB3	2026-10-07 22:23:01.500951+05:30	superadmin	TENANT_CREATE	tenant	city_med	{"name": "City Medical", "status": "ACTIVE"}	\N	\N	faa957ae55754d0bad4a7e54c1d008e0	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-523110E5DDD6	2026-10-07 22:23:01.602443+05:30	superadmin	TENANT_ADMIN_CREATE	user	city_admin	{"tenant_id": "city_med", "username": "city_admin", "role": "TENANT_ADMIN"}	\N	\N	adfae6be7e874bd0b0301a2947fdd291	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-D6BE2A218DC6	2026-10-07 22:23:02.080836+05:30	superadmin	TENANT_CREATE	tenant	health_plus	{"name": "Health Plus", "status": "ACTIVE"}	\N	\N	1b148009fb78433a83547fd68d53fd6e	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-41579EA9D911	2026-10-07 22:23:02.185171+05:30	superadmin	TENANT_ADMIN_CREATE	user	health_admin_user	{"tenant_id": "health_plus", "username": "health_admin_user", "role": "TENANT_ADMIN"}	\N	\N	44e13569745345f7bc82a4363cbced7c	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-71D2AEE54CDA	2026-10-07 22:23:02.42095+05:30	superadmin	TENANT_CREATE	tenant	lotus_health	{"name": "Lotus Health", "status": "ACTIVE"}	\N	\N	e922876e704247cc90c0c4bfa77157ea	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-B7EA5EA14C28	2026-10-07 22:23:02.523947+05:30	superadmin	TENANT_ADMIN_CREATE	user	admin_lotus	{"tenant_id": "lotus_health", "username": "admin_lotus", "role": "TENANT_ADMIN"}	\N	\N	97aca456b66d43eda15bd3c37f5612c6	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-61D5201F0627	2026-10-07 22:23:03.022913+05:30	superadmin	TENANT_CREATE	tenant	clinic_deact	{"name": "Clinic Deact", "status": "ACTIVE"}	\N	\N	7871a4f3931c4d2e8dcda5f7feb8eb58	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-2D4956153B5C	2026-10-07 22:23:03.029877+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_deact	{"status": "INACTIVE"}	\N	\N	7bbef947ed8a4a0e8f37d947469fd9b9	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-5A4CB746B1BA	2026-10-07 22:23:03.260783+05:30	superadmin	TENANT_CREATE	tenant	cln_green_valley_med_3ed637	{"name": "Green Valley Medical", "status": "ACTIVE"}	\N	\N	fe51695887424e6580b3de37e09110a2	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-ABB213E205EF	2026-10-07 22:23:03.790951+05:30	superadmin	TENANT_CREATE	tenant	clinic_react	{"name": "Reactivate Clinic", "status": "ACTIVE"}	\N	\N	caca0c9702ae4c0da6c73e91865403d7	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-CF74747E6090	2026-10-07 22:23:03.798291+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_react	{"status": "INACTIVE"}	\N	\N	47d54dc9c927423e8e650a278c87005d	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-F0AD39721CBB	2026-10-07 22:23:03.806707+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_react	{"status": "ACTIVE"}	\N	\N	2cb1bddf04c04e3c83de42984573c2ae	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-A502B013E1B3	2026-10-07 22:23:04.071928+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_2a09b8	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	bc9ced3e67374f9f90f2095c6855d08f	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-D3216A42BA4D	2026-10-07 22:23:04.080822+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_8a9937	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	8c68bd6436354180853dcfbd9a67dce9	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-055BC39DF311	2026-10-07 22:23:04.324281+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp	{"name": "Clinic Susp", "status": "ACTIVE"}	\N	\N	208ec0f0c9004e609d829f124f4f802d	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-8B9A9ADCC2AA	2026-10-07 22:23:04.330712+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp	{"status": "SUSPENDED", "reason": "Billing non-payment"}	\N	\N	d023f06270934878ae01900d521dc515	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-A4BAE2B9DDFF	2026-10-07 22:23:39.012721+05:30	superadmin	TENANT_CREATE	tenant	clinic_inact_test	{"name": "Inactive Clinic", "status": "ACTIVE"}	\N	\N	41f8a965456a4f10b9d9de0f8d63aa81	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-AE85D26C9E46	2026-10-07 22:23:39.020079+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_inact_test	{"status": "INACTIVE"}	\N	\N	8f1160aa0a92415bb22394aad95e1941	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-43F40EB3D906	2026-10-07 22:23:39.532583+05:30	superadmin	TENANT_CREATE	tenant	cln_hash_check_clini_35fc94	{"name": "Hash Check Clinic", "status": "ACTIVE"}	\N	\N	36fe483d5de04b40bce5268f2fde8e39	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-ED4425DCAAB0	2026-10-07 22:23:39.639186+05:30	superadmin	TENANT_ADMIN_CREATE	user	hash_check_admin	{"tenant_id": "cln_hash_check_clini_35fc94", "username": "hash_check_admin", "role": "TENANT_ADMIN"}	\N	\N	7f6d6c693cf54263a90af1c6efa19ab8	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-8380C65E86E2	2026-10-07 22:23:39.878653+05:30	superadmin	TENANT_CREATE	tenant	audit_clinic	{"name": "Audit Clinic", "status": "ACTIVE"}	\N	\N	2764c199c5784c0f834762a9346f80f4	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-B9207E486903	2026-10-07 22:23:40.991863+05:30	superadmin	TENANT_CREATE	tenant	cln_apollo_care_cent_3646da	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	da9a7d6f73cb42ad8e16efc185d7f7c0	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-28ED9650918E	2026-10-07 22:23:42.059956+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp_test	{"name": "Suspended Clinic", "status": "ACTIVE"}	\N	\N	63add9b47686488291023759079543b1	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-F91072C6986F	2026-10-07 22:23:42.068115+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp_test	{"status": "SUSPENDED", "reason": "Administrative suspension"}	\N	\N	70f86e96428042f2b99256834c9d6726	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-F18A94EDB75A	2026-10-07 22:23:42.550608+05:30	superadmin	TENANT_CREATE	tenant	clinic_act	{"name": "Clinic Act", "status": "INACTIVE"}	\N	\N	c7a5a56bf4954572afcbd3d1f9f1c02c	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-1D6FBD42999B	2026-10-07 22:23:42.556432+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_act	{"status": "ACTIVE"}	\N	\N	f83c672e5d014da69eacc091ef07b53e	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-2EE6CEE400BD	2026-10-07 22:23:42.751731+05:30	superadmin	TENANT_CREATE	tenant	city_med	{"name": "City Medical", "status": "ACTIVE"}	\N	\N	a2b14f8e1a7741f7bc627cb5dfd091ee	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-4E596832C519	2026-10-07 22:23:42.83189+05:30	superadmin	TENANT_ADMIN_CREATE	user	city_admin	{"tenant_id": "city_med", "username": "city_admin", "role": "TENANT_ADMIN"}	\N	\N	49d410195e4042598845ef902f6aed26	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-01EB6E9075DA	2026-10-07 22:23:43.200565+05:30	superadmin	TENANT_CREATE	tenant	health_plus	{"name": "Health Plus", "status": "ACTIVE"}	\N	\N	0ca7bcd203c64d79824aa817c0b8553d	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-C2EBFB8AFAE1	2026-10-07 22:23:43.273377+05:30	superadmin	TENANT_ADMIN_CREATE	user	health_admin_user	{"tenant_id": "health_plus", "username": "health_admin_user", "role": "TENANT_ADMIN"}	\N	\N	1b3d642f65b845958ad018caed65d0ad	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-8A7CA36CEF38	2026-10-07 22:23:43.475304+05:30	superadmin	TENANT_CREATE	tenant	lotus_health	{"name": "Lotus Health", "status": "ACTIVE"}	\N	\N	610858e6afb54fd993d5c85842178105	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-5FE0041E18EF	2026-10-07 22:23:43.5529+05:30	superadmin	TENANT_ADMIN_CREATE	user	admin_lotus	{"tenant_id": "lotus_health", "username": "admin_lotus", "role": "TENANT_ADMIN"}	\N	\N	2a90fb5a54a24ee5ae9fcecdba714911	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-3EB8B4BE1206	2026-10-07 22:23:43.930846+05:30	superadmin	TENANT_CREATE	tenant	clinic_deact	{"name": "Clinic Deact", "status": "ACTIVE"}	\N	\N	fa684a325aec4eb18247993444d8868e	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-A4362F3A6E19	2026-10-07 22:23:43.930846+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_deact	{"status": "INACTIVE"}	\N	\N	fc2216ceacdc4b93a2261806a550e008	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-564DF2D669E2	2026-10-07 22:23:44.139575+05:30	superadmin	TENANT_CREATE	tenant	cln_green_valley_med_96b5be	{"name": "Green Valley Medical", "status": "ACTIVE"}	\N	\N	9571e94166fa48dfb58ad9bf580bc21f	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-FE501229C83E	2026-10-07 22:23:44.736774+05:30	superadmin	TENANT_CREATE	tenant	clinic_react	{"name": "Reactivate Clinic", "status": "ACTIVE"}	\N	\N	fdaa189dfa9345e8b6dbd198944e6905	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-2118F58FFF2B	2026-10-07 22:23:44.741223+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_react	{"status": "INACTIVE"}	\N	\N	7b895261a53d4115a3a887cd04ee411a	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-A530F24D1FF9	2026-10-07 22:23:44.751682+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_react	{"status": "ACTIVE"}	\N	\N	aeec0381af1949eea7cc286354246535	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-4E7BEE4E6A75	2026-10-07 22:23:44.951869+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_bdca21	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	68b1024581794a47b10fb1745673cd3b	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-81B37C2820BA	2026-10-07 22:23:44.957877+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_2793d8	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	58e4e5c2351e4869bf19e692cd8c7a82	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-77EC851DDC11	2026-10-07 22:23:45.136804+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp	{"name": "Clinic Susp", "status": "ACTIVE"}	\N	\N	f7ebcfc3d0814080ba851fb199113386	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-8492BBEE9C31	2026-10-07 22:23:45.141913+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp	{"status": "SUSPENDED", "reason": "Billing non-payment"}	\N	\N	e8d5767747fb4a02a4b1af69d77ff453	2026-10-13 16:54:47.601678+05:30	2026-10-13 16:54:47.601678+05:30	default
AUD-9318D0A86AC0	2026-10-07 22:24:13.445559+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	2f1694c3a6d24943952544d8890afeb0	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-545334EC4556	2026-10-07 22:24:15.160878+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	c40c9a0234df43ab8e37457c4de951c6	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-984CF1DD4420	2026-10-07 22:24:15.321015+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	2fab5334249f494ab71b5a34ac1a1e49	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-31715F088A39	2026-10-07 22:24:15.441643+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	1bc61ee2ff5c4750920a7ca2d561270d	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-B47C199370B1	2026-10-07 22:24:15.687739+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	f338ef1781a940b88425baa3e6dae2d8	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-7FC9A90E7540	2026-10-07 22:24:16.062005+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	956219ff75414adb8ccc518ffe98f318	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-36B65211353C	2026-10-07 22:24:16.20186+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	ad51ccdce78d4796a352ec39f54bee10	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-0800970627B5	2026-10-07 22:24:17.455529+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	903200625b614ee7a72f51242182a847	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-9727CC99ED79	2026-10-07 22:24:17.47514+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	aaf081d3ec8b48fab77cdcce767a6ed4	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-673D9B102054	2026-10-07 22:24:17.49252+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	65ca5b6ba6e9491390fa52de1c15b692	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-AB9FE1318FDD	2026-10-07 22:24:22.243836+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	0e6417f121ba45cd9fbfa0b29d6370ca	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-00F4668184E6	2026-10-07 22:24:22.326983+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	c581d6787ae54fdd9727cad06bd1f799	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-81E7CA143BFD	2026-10-07 22:24:30.42289+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-7C16E114D3	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	799ae0be886441ed9359795bd1a93b16	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-8BB5961C7122	2026-10-07 22:24:30.432236+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-7C16E114D3	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	01b7b48171114083ae0180da3b230470	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-9655D7FB94FE	2026-10-07 22:24:30.488276+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-7C16E114D3	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	7855f85e271a45099b7d8d396465a758	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-23DAA38F35D6	2026-10-07 22:24:41.201797+05:30	superadmin	TENANT_CREATE	tenant	clinic_inact_test	{"name": "Inactive Clinic", "status": "ACTIVE"}	\N	\N	d18cec94f643419e9a8ad9fb77981157	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-5126079469F1	2026-10-07 22:24:41.20723+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_inact_test	{"status": "INACTIVE"}	\N	\N	6f5697c41f0843ddbe4b137f67d7af2b	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-387368218FB0	2026-10-07 22:24:41.579923+05:30	superadmin	TENANT_CREATE	tenant	cln_hash_check_clini_9a3691	{"name": "Hash Check Clinic", "status": "ACTIVE"}	\N	\N	2845c1cdc76840c6b60827a6e55759de	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-CDC86B19597B	2026-10-07 22:24:41.653289+05:30	superadmin	TENANT_ADMIN_CREATE	user	hash_check_admin	{"tenant_id": "cln_hash_check_clini_9a3691", "username": "hash_check_admin", "role": "TENANT_ADMIN"}	\N	\N	39ee616b4e54412caeb98e3224342899	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-0DF2D96A3181	2026-10-07 22:24:41.842333+05:30	superadmin	TENANT_CREATE	tenant	audit_clinic	{"name": "Audit Clinic", "status": "ACTIVE"}	\N	\N	48f82d3d19024030995d98633d4ecb6e	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-941B1D3BAD76	2026-10-07 22:24:42.675126+05:30	superadmin	TENANT_CREATE	tenant	cln_apollo_care_cent_acae11	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	1f521cb9469744ceb71c3cc543ff6ed0	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-AAEFE90AE023	2026-10-07 22:24:43.300626+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp_test	{"name": "Suspended Clinic", "status": "ACTIVE"}	\N	\N	85237c3abb744b2a9dcbc7acbc1cba44	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-7EA887E59ABD	2026-10-07 22:24:43.307813+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp_test	{"status": "SUSPENDED", "reason": "Administrative suspension"}	\N	\N	78ac15db267742779b30e98ca4da53c1	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-3E480A622004	2026-10-07 22:24:43.710634+05:30	superadmin	TENANT_CREATE	tenant	clinic_act	{"name": "Clinic Act", "status": "INACTIVE"}	\N	\N	c7f585c7042140f4b7cc1096d4440f48	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-9655C8EC5F8A	2026-10-07 22:24:43.901751+05:30	superadmin	TENANT_CREATE	tenant	city_med	{"name": "City Medical", "status": "ACTIVE"}	\N	\N	bc8477d3730645399b7b8dc46c40706e	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-1194BA142925	2026-10-07 22:24:43.985137+05:30	superadmin	TENANT_ADMIN_CREATE	user	city_admin	{"tenant_id": "city_med", "username": "city_admin", "role": "TENANT_ADMIN"}	\N	\N	517de45584094b76bcd96af843604813	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-0B1C9F847EA4	2026-10-07 22:24:44.563098+05:30	superadmin	TENANT_CREATE	tenant	health_plus	{"name": "Health Plus", "status": "ACTIVE"}	\N	\N	fd77a36bfda849f8b8d3030e5e8e35c3	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-891A5CB773BE	2026-10-07 22:24:44.642975+05:30	superadmin	TENANT_ADMIN_CREATE	user	health_admin_user	{"tenant_id": "health_plus", "username": "health_admin_user", "role": "TENANT_ADMIN"}	\N	\N	03cd58066cb8440a80f9d0206c2c9beb	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-9F2C5ACBBB10	2026-10-07 22:24:44.820834+05:30	superadmin	TENANT_CREATE	tenant	lotus_health	{"name": "Lotus Health", "status": "ACTIVE"}	\N	\N	5e052f1de8ab4ce4ac55bacd8e8ca875	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-C58D521B5EB8	2026-10-07 22:24:44.891832+05:30	superadmin	TENANT_ADMIN_CREATE	user	admin_lotus	{"tenant_id": "lotus_health", "username": "admin_lotus", "role": "TENANT_ADMIN"}	\N	\N	2ff9c9da2b0945d78f569c94f82d8b7a	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-598B00203F92	2026-10-07 22:24:45.247947+05:30	superadmin	TENANT_CREATE	tenant	clinic_deact	{"name": "Clinic Deact", "status": "ACTIVE"}	\N	\N	470398214c614d97bb49b537b18888d6	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-89C666C7A1A7	2026-10-07 22:24:45.253912+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_deact	{"status": "INACTIVE"}	\N	\N	a3330e163c1c4304874fef5ef4583fd1	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-C02E89A25D10	2026-10-07 22:24:45.446292+05:30	superadmin	TENANT_CREATE	tenant	cln_green_valley_med_fa486c	{"name": "Green Valley Medical", "status": "ACTIVE"}	\N	\N	3a1ee6680500409d8cc15f7e21788690	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-19BA95F625BF	2026-10-07 22:24:45.82723+05:30	superadmin	TENANT_CREATE	tenant	clinic_react	{"name": "Reactivate Clinic", "status": "ACTIVE"}	\N	\N	c9314432fd494b5996f6ce8f96027c9e	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-190F31022399	2026-10-07 22:24:45.831631+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_react	{"status": "INACTIVE"}	\N	\N	fcf8359dcaf34a999314f3af3253c9ba	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-8B486B21E625	2026-10-07 22:24:45.844366+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_react	{"status": "ACTIVE"}	\N	\N	e0cc7621ff094a7ab4b446543b0f8b22	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-6F7F69A79E97	2026-10-07 22:24:46.037343+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_ace8fa	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	f92d971e2743474a86244befd8862331	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-F7F1D6BCE556	2026-10-07 22:24:46.041935+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_0c0156	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	bebb0f6116dd479d98f90243ed0047c7	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-02E784DDFD9B	2026-10-07 22:24:46.263726+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp	{"name": "Clinic Susp", "status": "ACTIVE"}	\N	\N	7e047d14a4f04316a336602d326474a2	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-13206E82BF03	2026-10-07 22:24:46.271228+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp	{"status": "SUSPENDED", "reason": "Billing non-payment"}	\N	\N	750cc9ff1c304072939f306fe4756cfa	2026-10-13 16:54:47.73518+05:30	2026-10-13 16:54:47.73518+05:30	default
AUD-76AB3C1C1BA7	2026-10-07 22:24:47.364854+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-0DAD2A9D6E	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	37b3560f7e1446bc8fbf0e8c80b36956	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-95D15D9BE7CF	2026-10-07 22:24:47.368134+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-0DAD2A9D6E	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	8a11ac51201e4c019297f171aaeb0800	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-9AD726082D2B	2026-10-07 22:24:47.38294+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-A5EB421FB5	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	3b357aaf891c409c867ae47502f176fb	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-D6F9AA16C65F	2026-10-07 22:24:47.385747+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-A5EB421FB5	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	568c13453ee04d39a7e5abe65eec87b7	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-7AB3DFB4E7F3	2026-10-07 22:24:47.400574+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-11677249BE	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	6e9626ceee9d436f95bb9aaf6993490e	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-6F2F9767E70A	2026-10-07 22:24:47.403351+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-11677249BE	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	f3f03e1c94f94190badabf981f37f718	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-FD15B2F42980	2026-10-07 22:24:47.404614+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-11677249BE	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	899d31da7b254b8899b602cdacdc090d	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-CB978779777A	2026-10-07 22:24:47.421067+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-80AF472D49	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	e79f86ee5bb6463a98d7eddd8560feaf	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-1E4950CC7AB1	2026-10-07 22:24:47.422108+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-80AF472D49	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	36017d4257b842bb91e0bb881e0ea9f0	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-377B5698D7CB	2026-10-07 22:24:47.466067+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-7C196FCBB5	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	7cd21fc9532a41ff80b8b103ee70b7ee	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-D3D4BF2D1788	2026-10-07 22:24:47.470315+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-7C196FCBB5	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	a4480cd4292c4fbb83c222dee5de59f7	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-CD39CF386183	2026-10-07 22:24:47.515507+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-676C0FBC05	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	729e8799d8eb4a818f5777bf22315c91	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-58C51492ACB4	2026-10-07 22:24:47.519567+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-676C0FBC05	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	5a7b73d1724e440d97439f2538eede67	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-42E806428C15	2026-10-07 22:24:50.430588+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-9202D4D2D9	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	019e0100dc1c461ba4b6b2cb2a844c36	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-E1463CFC6E59	2026-10-07 22:24:50.449879+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-9202D4D2D9	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	f759d38d67f548e4b16e1aef328869c1	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-6CC482E9C444	2026-10-07 22:24:59.421265+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-08", "old_time": "10:00 AM", "new_date": "2026-10-14", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	fab8404e8be949b08b1c5f211a9d9d98	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-941CC0D86891	2026-10-07 22:24:59.435154+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	3c28466cdcbf49eba21d2cba0c0d9d80	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-1DDD9906C0B0	2026-10-07 22:24:59.443877+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	46bc2b7f33c046c7892755bea3f96a90	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-64EF428ED5D2	2026-10-07 22:24:59.551948+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-08", "old_time": "10:00 AM", "new_date": "2026-10-14", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	2fd09cca9a034957b16e42f884e20e77	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-6F13CC404C87	2026-10-07 22:24:59.551948+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	8c44d43e4f8c4984bb3b864bb6aaa14e	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-E10B0ACC3D35	2026-10-07 22:24:59.57624+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-08", "old_time": "10:00 AM", "new_date": "2026-10-14", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	cddabb5d4c9e454c8d4cc0925cf19428	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-5467E3353D36	2026-10-07 22:24:59.58407+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	6376332bcacb499d985b4ed27d5a6654	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-33BB4501C039	2026-10-12 16:13:27.892659+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	5514a47059304c439568c367aa478cfb	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-51A77D009E3F	2026-10-12 16:13:29.534553+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	21716f9381094a8d9c7cc357a0e66ac9	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-A816F102FF4A	2026-10-12 16:13:29.69562+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	a917f3b4fde541c4824d19e4b2d9bbfd	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-C77BC053C1D7	2026-10-12 16:13:29.845926+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	4c7691478eef41f1b32e9d9f8168cabf	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-1CFF7188A6A1	2026-10-12 16:13:30.160893+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	75fcf3b682c04b34919dbe8097b6f02e	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-7C929AFA4452	2026-10-12 16:13:30.506561+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	5569b044fcee44118c2938b25e2eb290	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-65B37C6F3BCA	2026-10-12 16:13:30.650157+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	c7f992a25c4a46bfa123c94b80ac8b17	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-42063D08402E	2026-10-12 16:13:31.871309+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	f3b9c3b8fab64b388ed81b389472cc0b	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-C229C9F64E88	2026-10-12 16:13:31.887248+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	85123d745ccf4df49f7b9b297c84940e	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-502A73CB698A	2026-10-12 16:13:31.904418+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	ee17c087431e4d79b7cf9cf109ae08b3	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-68C6DEF75262	2026-10-12 16:13:35.464798+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	c7500fcb63aa40f5a481842910f8fdab	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-1B70B8D89D56	2026-10-12 16:13:35.535645+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	d9f60cc6b6f8499daf7b11d0bb80b136	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-608DFC0B9BC7	2026-10-12 16:13:43.72232+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6E4889BE48	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	22e6257a989c4d2a84b7e6c8b5e6f739	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-C71E3CB63F0E	2026-10-12 16:13:43.738505+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-6E4889BE48	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	f7c062133c964c8495c15fb214cfbe8e	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-EDAD8A98EEF2	2026-10-12 16:13:43.78767+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-6E4889BE48	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	ffe8c72ddec740469bdf564d314501b1	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-11FEEAFE316D	2026-10-12 16:13:58.557389+05:30	superadmin	TENANT_CREATE	tenant	clinic_inact_test	{"name": "Inactive Clinic", "status": "ACTIVE"}	\N	\N	96123ecb97c842bdb91bbcc1d6913b94	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-3BB862D1815C	2026-10-12 16:13:58.565395+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_inact_test	{"status": "INACTIVE"}	\N	\N	643f6ca7268f4414acc2432ea608e0aa	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-B80FD682AFCD	2026-10-12 16:13:58.939215+05:30	superadmin	TENANT_CREATE	tenant	cln_hash_check_clini_766ca8	{"name": "Hash Check Clinic", "status": "ACTIVE"}	\N	\N	14b0435e6d6845c3893b5b470a8f03c2	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-46B0A6B39EE9	2026-10-12 16:13:59.012895+05:30	superadmin	TENANT_ADMIN_CREATE	user	hash_check_admin	{"tenant_id": "cln_hash_check_clini_766ca8", "username": "hash_check_admin", "role": "TENANT_ADMIN"}	\N	\N	c5ce815a588b4046b14e28679cc3d8ee	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-7FD6C3933173	2026-10-12 16:13:59.192775+05:30	superadmin	TENANT_CREATE	tenant	audit_clinic	{"name": "Audit Clinic", "status": "ACTIVE"}	\N	\N	cac14c3509454d1eb2cdf78d788be60d	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-23615E73A462	2026-10-12 16:14:00.022019+05:30	superadmin	TENANT_CREATE	tenant	cln_apollo_care_cent_edd13b	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	31d13d62e3aa4897a82c04fedb63386c	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-12E8CE96C271	2026-10-12 16:14:00.676242+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp_test	{"name": "Suspended Clinic", "status": "ACTIVE"}	\N	\N	c698719d8d4f481d9822179c2552c4ae	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-37DFF67A1236	2026-10-12 16:14:00.68874+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp_test	{"status": "SUSPENDED", "reason": "Administrative suspension"}	\N	\N	740990c747984b64a06366db93930fa4	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-C8A2BF36B488	2026-10-12 16:14:01.09085+05:30	superadmin	TENANT_CREATE	tenant	clinic_act	{"name": "Clinic Act", "status": "INACTIVE"}	\N	\N	12c239b3c6b74764b4e24d593e5e1a8d	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-C1A42BEC5721	2026-10-12 16:14:01.09085+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_act	{"status": "ACTIVE"}	\N	\N	398ae0e897024dbf84c1eda03fae07c6	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-B29E50C84231	2026-10-12 16:14:01.280028+05:30	superadmin	TENANT_CREATE	tenant	city_med	{"name": "City Medical", "status": "ACTIVE"}	\N	\N	35fe0762a6ce49089d1d328ea140ce2f	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-E1F817730E84	2026-10-12 16:14:01.365403+05:30	superadmin	TENANT_ADMIN_CREATE	user	city_admin	{"tenant_id": "city_med", "username": "city_admin", "role": "TENANT_ADMIN"}	\N	\N	a82c0d256bef4bb08b9003845933b9da	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-EC6D5B2333DC	2026-10-12 16:14:01.734723+05:30	superadmin	TENANT_CREATE	tenant	health_plus	{"name": "Health Plus", "status": "ACTIVE"}	\N	\N	e48919b0d37148f1a48f9b237db00997	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-A1F6F3D63C89	2026-10-12 16:14:01.870366+05:30	superadmin	TENANT_ADMIN_CREATE	user	health_admin_user	{"tenant_id": "health_plus", "username": "health_admin_user", "role": "TENANT_ADMIN"}	\N	\N	bd8611d6531d4388957decb21124969d	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-442BDE8E0E16	2026-10-12 16:14:02.046473+05:30	superadmin	TENANT_CREATE	tenant	lotus_health	{"name": "Lotus Health", "status": "ACTIVE"}	\N	\N	6dd15f177a0a40d3af545c2df7783ce4	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-A02F2D3A5056	2026-10-12 16:14:02.127358+05:30	superadmin	TENANT_ADMIN_CREATE	user	admin_lotus	{"tenant_id": "lotus_health", "username": "admin_lotus", "role": "TENANT_ADMIN"}	\N	\N	d3888047b10543488a0920912486933a	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-540364EA0443	2026-10-12 16:14:02.51294+05:30	superadmin	TENANT_CREATE	tenant	clinic_deact	{"name": "Clinic Deact", "status": "ACTIVE"}	\N	\N	8b4972c90d1341feb4c9165aa0e60fe0	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-F02297F828D1	2026-10-12 16:14:02.51294+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_deact	{"status": "INACTIVE"}	\N	\N	70764052b715468f9a813df1ac248170	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-D96A9683EB9B	2026-10-12 16:14:02.694507+05:30	superadmin	TENANT_CREATE	tenant	cln_green_valley_med_6279ce	{"name": "Green Valley Medical", "status": "ACTIVE"}	\N	\N	ca4e17a497874728a37695d89ae45fef	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-FF3083F71A6A	2026-10-12 16:14:03.068344+05:30	superadmin	TENANT_CREATE	tenant	clinic_react	{"name": "Reactivate Clinic", "status": "ACTIVE"}	\N	\N	577827951d4c42fcb4c818a401129b53	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-2836B5972244	2026-10-12 16:14:03.076562+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_react	{"status": "INACTIVE"}	\N	\N	519219a3fc914da9aa23bab88d20d505	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-31E7BC6D94D0	2026-10-12 16:14:03.084583+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_react	{"status": "ACTIVE"}	\N	\N	1904d15bf5f7466f9083a07bbbb32360	2026-10-13 16:54:47.736777+05:30	2026-10-13 16:54:47.736777+05:30	default
AUD-D3554A44B5B9	2026-10-12 16:14:03.264625+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_3eae07	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	e062f69e143743c6981ff7751a938bf3	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-C7E5B0384A6E	2026-10-12 16:14:03.267714+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_e0dc62	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	b63cf7f48a6749a392922b94926c31fd	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-96377EE1C620	2026-10-12 16:14:03.472408+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp	{"name": "Clinic Susp", "status": "ACTIVE"}	\N	\N	fb5af17bcf574751822eb023eae70dc7	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-E2F4C6A9A0F3	2026-10-12 16:14:03.477933+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp	{"status": "SUSPENDED", "reason": "Billing non-payment"}	\N	\N	2889cf5ce21a4afc902b81bd4bced3cc	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-F4EBCAFE5613	2026-10-12 16:14:04.785395+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6C07A151B9	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	1d357691bb4247899873f42ec4ac0f7d	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-5462E0944E6D	2026-10-12 16:14:04.787383+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-6C07A151B9	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	0bc48edd4aa44f388e887f39c2119e57	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-8EB70BCD6956	2026-10-12 16:14:04.799556+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-1D7C8DA834	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	752e8c98cb5a46628062394f95fb832b	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-624A73BD7292	2026-10-12 16:14:04.801351+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-1D7C8DA834	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	2fd2903638e04c188a4690640f2b7c19	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-9CFA8D249057	2026-10-12 16:14:04.813744+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-D1E9421975	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	870aa2bf7f1647ffb92242009dfdf126	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-787421D550B0	2026-10-12 16:14:04.814833+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-D1E9421975	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	6d215a32fe744be69b40fc64d8545906	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-EDB8405E4342	2026-10-12 16:14:04.816842+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-D1E9421975	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	3700e877f6f14365b5d3eea804bcb997	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-FA6AF2CEA511	2026-10-12 16:14:04.828309+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-06900A3BD9	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	9b8817dc80cf4cdfb6d0da785c3b636c	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-6056C9CD75A2	2026-10-12 16:14:04.830538+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-06900A3BD9	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	c52e23e5d6144190834a64e2ab1365a7	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-01AADE75B9AB	2026-10-12 16:14:04.859174+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-79CEC2A0F0	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	cd0caf0d79fe473da28195eecdcd1c0d	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-1249D2BEBCC8	2026-10-12 16:14:04.861407+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-79CEC2A0F0	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	eb8e8bfb0b6348a19e7178ff9777febf	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-FAD69DA286A8	2026-10-12 16:14:04.887388+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-55DC746F90	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	36a772945379411cab7018e0b2180bb8	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-0FEB66BC46E5	2026-10-12 16:14:04.889724+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-55DC746F90	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	58bd132f61dc47b9b7762f166d8b0c44	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-29AC94F91D73	2026-10-12 16:14:07.862828+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-E051484ABC	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	dc05bcb2b7eb48d185056fad92423b0a	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-C67D2BF86E2A	2026-10-12 16:14:07.889491+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-E051484ABC	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	a06ea5d7432a46bcba99bbaafe8f4b9c	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-7CB9534D2063	2026-10-12 16:14:16.714913+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	a83ef67393d04ccbb7f852facd8653ea	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-B7CCA5A6341B	2026-10-12 16:14:16.736241+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	23137d700e134f798b9f406acf9a748f	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-BB111A1D3737	2026-10-12 16:14:16.744365+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	5b8a8c4a996144068f86d846c9840891	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-748179CAEABE	2026-10-12 16:41:56.608695+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-3A86FD6DD8	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	2d5158010bb845fa871129ff662bb151	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-E123C8BF4D2D	2026-10-12 16:14:16.879481+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	d07a72c022214df4b4de88d2aea8e3b3	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-419BA33F0C60	2026-10-12 16:14:16.888425+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	28c932a8f9264394938c6cb4eae1d199	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-DF3B428FBAE1	2026-10-12 16:14:16.910833+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	f691090cf4c8409081546143e11a6e02	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-C7625791A943	2026-10-12 16:14:16.921054+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	93fd90e299304a978b2a307ec704ccda	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-3F642B18D8D5	2026-10-12 16:22:59.226002+05:30	superadmin	TENANT_CREATE	tenant	clinic_inact_test	{"name": "Inactive Clinic", "status": "ACTIVE"}	\N	\N	7c983b445da647689ccbd1a76f92709f	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-F854E8F21587	2026-10-12 16:22:59.233149+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_inact_test	{"status": "INACTIVE"}	\N	\N	d04a60f5486b4534a2b99b5c20f5c13a	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-E81B327BC391	2026-10-12 16:22:59.716898+05:30	superadmin	TENANT_CREATE	tenant	cln_hash_check_clini_dc9ac1	{"name": "Hash Check Clinic", "status": "ACTIVE"}	\N	\N	cb738b854d5e4de082d247f2bfc706d9	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-071C674429AF	2026-10-12 16:22:59.822234+05:30	superadmin	TENANT_ADMIN_CREATE	user	hash_check_admin	{"tenant_id": "cln_hash_check_clini_dc9ac1", "username": "hash_check_admin", "role": "TENANT_ADMIN"}	\N	\N	9904e53f1f9c4f0ea4a8357134c350f3	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-F59613CBBE38	2026-10-12 16:23:00.083545+05:30	superadmin	TENANT_CREATE	tenant	audit_clinic	{"name": "Audit Clinic", "status": "ACTIVE"}	\N	\N	ac3afa6e2dfb41858b5bc26442a3f25b	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-1F69FD392771	2026-10-12 16:23:01.218581+05:30	superadmin	TENANT_CREATE	tenant	cln_apollo_care_cent_a09815	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	a734aced2e094e949dc0780589f9eff2	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-E170C51DFBFC	2026-10-12 16:23:02.045485+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp_test	{"name": "Suspended Clinic", "status": "ACTIVE"}	\N	\N	ee4c2b59a290465497fd11f8f4caf104	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-278B7A7889E3	2026-10-12 16:23:02.053958+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp_test	{"status": "SUSPENDED", "reason": "Administrative suspension"}	\N	\N	26246acf6d7b432781f806d7c8b3048c	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-5B761283806E	2026-10-12 16:23:02.438756+05:30	superadmin	TENANT_CREATE	tenant	clinic_act	{"name": "Clinic Act", "status": "INACTIVE"}	\N	\N	e25f173b2f8d49f2a6ce3ac0454a6384	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-AAF89BE9A00B	2026-10-12 16:23:02.443793+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_act	{"status": "ACTIVE"}	\N	\N	286411fb4fa84443a4b89e6460ab371e	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-B71F195E5176	2026-10-12 16:23:02.617602+05:30	superadmin	TENANT_CREATE	tenant	city_med	{"name": "City Medical", "status": "ACTIVE"}	\N	\N	3296cbdc62d5456cb5f4f2103a21d676	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-A5D0409CAEAC	2026-10-12 16:23:02.692214+05:30	superadmin	TENANT_ADMIN_CREATE	user	city_admin	{"tenant_id": "city_med", "username": "city_admin", "role": "TENANT_ADMIN"}	\N	\N	8d84b7ff0a71471cb0d08def3e7600ab	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-76676E961E98	2026-10-12 16:23:03.063847+05:30	superadmin	TENANT_CREATE	tenant	health_plus	{"name": "Health Plus", "status": "ACTIVE"}	\N	\N	6d5158c0eabb44f286c33151139f52aa	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-A8036654C7DB	2026-10-12 16:23:03.149295+05:30	superadmin	TENANT_ADMIN_CREATE	user	health_admin_user	{"tenant_id": "health_plus", "username": "health_admin_user", "role": "TENANT_ADMIN"}	\N	\N	ea82ef8cbddf4bf48eae97419c5dcc29	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-F3780A000396	2026-10-12 16:23:03.311223+05:30	superadmin	TENANT_CREATE	tenant	lotus_health	{"name": "Lotus Health", "status": "ACTIVE"}	\N	\N	896ec4d0870348a99ea01512b535daea	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-DB8BEA567157	2026-10-12 16:23:03.393377+05:30	superadmin	TENANT_ADMIN_CREATE	user	admin_lotus	{"tenant_id": "lotus_health", "username": "admin_lotus", "role": "TENANT_ADMIN"}	\N	\N	1457558b4991482894732aafe0f95ad6	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-614101D0E9D9	2026-10-12 16:23:03.871077+05:30	superadmin	TENANT_CREATE	tenant	clinic_deact	{"name": "Clinic Deact", "status": "ACTIVE"}	\N	\N	33178a60dc704eaf82a78637348ece1a	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-1DD79E5742F1	2026-10-12 16:23:03.877197+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_deact	{"status": "INACTIVE"}	\N	\N	1ffd271d8d3c47cdab6daf6bfb190fc6	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-641D037286C8	2026-10-12 16:23:04.052397+05:30	superadmin	TENANT_CREATE	tenant	cln_green_valley_med_070291	{"name": "Green Valley Medical", "status": "ACTIVE"}	\N	\N	3deb7998d4b84e1a93c9babe470dc5b5	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-298EABFD7692	2026-10-12 16:23:04.454666+05:30	superadmin	TENANT_CREATE	tenant	clinic_react	{"name": "Reactivate Clinic", "status": "ACTIVE"}	\N	\N	9b2737b826b34f7a94f2e02b2f958fa7	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-DFEBAED501FB	2026-10-12 16:23:04.45869+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_react	{"status": "INACTIVE"}	\N	\N	e69553c11671480e8d231b62a99cde0d	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-7201C8209DB2	2026-10-12 16:23:04.468756+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_react	{"status": "ACTIVE"}	\N	\N	b62c13f973c1437c85f89a3bd7d782e1	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-8BEAAA1BACE5	2026-10-12 16:23:04.975071+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_3c8215	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	ec45ee90026e4f34a07ff996ab8067ee	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-B8D7BB084ED2	2026-10-12 16:23:04.983507+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_c30742	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	c3c890c2b49147ce9f0a70e065948697	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-B34ECC0061A9	2026-10-12 16:23:05.278013+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp	{"name": "Clinic Susp", "status": "ACTIVE"}	\N	\N	79fd76f07ab246d086852ebbcb2382d9	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-727BCEEF0B34	2026-10-12 16:23:05.284339+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp	{"status": "SUSPENDED", "reason": "Billing non-payment"}	\N	\N	6ddea908aebf444eb55eba46cdc2f45c	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-8834903CF95C	2026-10-12 16:41:56.576087+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-E39B683825	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	16730ca683144513afc8e8b7c5e80ef3	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-031EE03CC339	2026-10-12 16:41:56.5781+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-E39B683825	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	75f42fb3ce054cc18a64f6555f25e63e	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-3ADD546FB580	2026-10-12 16:41:56.592475+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-F5FE8D865F	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	aa15755db30a4138895e5a766ace30c7	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-95EFA3ECDB41	2026-10-12 16:41:56.594488+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-F5FE8D865F	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	bf2950412cf247de8da68dec594215d7	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-DA2BFCA639AB	2026-10-12 16:41:56.608695+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-3A86FD6DD8	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	7bafaab2fc6540df89c7df47860b7858	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-285DD1162982	2026-10-12 16:41:56.61277+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-3A86FD6DD8	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	48dd299388ba434ca1ca287f7f3ac376	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-8F824EAE2768	2026-10-12 16:41:56.626775+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-649322276C	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	990e1930993d401187330d62e45ae0de	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-1CCF422492C6	2026-10-12 16:41:56.627894+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-649322276C	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	cb48d9d229f746979f77f73017f74740	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-A02C78EFF475	2026-10-12 16:41:56.662771+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-0D4957A97C	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	4b972565171e4f97b03f8ac9da287546	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-D1DD42C2DCD4	2026-10-12 16:41:56.664929+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-0D4957A97C	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	7e94c8e250b841cba00e1517af3de756	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-F419A5D77E06	2026-10-12 16:41:56.693226+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-0FBD3D4B27	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	5a1419c85d434763a9e781956dce5f4a	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-E59313053DD0	2026-10-12 16:41:56.696894+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-0FBD3D4B27	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	2c730117bf3747b3b80ff70705753608	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-058FB4CD78F5	2026-10-12 16:42:01.193059+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-F414D81D44	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	36a955bdc39e4019b604acaab7afe31a	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-9752881DB600	2026-10-12 16:42:01.217819+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-F414D81D44	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	3b43ea40a67d4f08b8bd98c6c9636167	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-DCDC1B04B084	2026-10-12 16:42:01.737609+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	08f4991e0ef34130b26491b17d9350a4	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-82C60AEAF4B3	2026-10-12 16:42:01.758877+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	0408be3322bf49fd8a0ef620b845e014	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-86A34A9761C2	2026-10-12 16:42:01.770663+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	183485b28b55465a965566698a9b2f43	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-CBD8D0FE6EC8	2026-10-12 16:42:01.957775+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	badf681239524257a2ece7e9cf689f3d	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-FB7EDE355A18	2026-10-12 16:42:01.966298+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	edd2735c2ea14847ab974445c0f2b2d0	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-BD0340A2D7F1	2026-10-12 16:42:01.991283+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	b43bf4129b564230a77b67889f861ab3	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-81C949630A68	2026-10-12 16:42:02.006387+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	c0c399a964ba4237b2ab83988e7fee2b	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-9B39FF73A2A0	2026-10-12 16:46:22.547495+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-E0CA1A4E70	{"patient_id": "P101", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	c805a690e1874927be09ce2e1928e922	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-3F506C35A9D0	2026-10-12 16:46:22.551528+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-E0CA1A4E70	{"patient_id": "P101", "appointment_id": "TKN-101", "version": 1}	\N	\N	e4aba9ba6f0f4a1fa45900bd1a8f017d	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-B48F039F2957	2026-10-12 16:48:28.077956+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-B494246E4C	{"patient_id": "P101", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	493c3b8f557a4e259e42cf6380473adb	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-A80250CE1EC4	2026-10-12 16:48:28.079518+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-B494246E4C	{"patient_id": "P101", "appointment_id": "TKN-101", "version": 1}	\N	\N	deefa835ffb74311bfe0797f3c722b1d	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-DBB8392F8D2E	2026-10-12 16:49:55.846853+05:30	admin	APPOINTMENT_CREATE	appointment	TKN_726df8	{"patient_id": "PID_f03df3", "patient_name": "Patient 0", "doctor": "Dr. Rao", "date": "2026-10-13", "time": "11:00 AM", "slot_id": "S202", "amount": "500"}	\N	\N	29d53adc776e4bfb8b83cdbd3f2e0f3e	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-8E9E5C010A0B	2026-10-12 16:49:55.869685+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-362E60D99E	{"patient_id": "P101", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	0344ab266f884b27b4394577bb124cde	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-19EB811A2861	2026-10-12 16:49:55.90079+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-362E60D99E	{"patient_id": "P101", "appointment_id": "TKN-101", "version": 1}	\N	\N	cf895560b00246acbbbc4dc5702667eb	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-11EB681DF1CE	2026-10-12 16:51:13.659378+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	c8f4e3d5249c4e3b9dbe85a07a17386d	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-90BFFF64B464	2026-10-12 16:51:15.261485+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	341664e4927c443db44fa1fa7b8cec4e	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-A117A6A00CB2	2026-10-12 16:51:15.424387+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	7311ce36e79844289e46d016b99f62b7	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-4AB86475822C	2026-10-12 16:51:15.602214+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	aa90fe7f343748daa0ea96f29f0b11e3	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-F6B8BDF3AD5B	2026-10-12 16:51:16.115413+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	de0d68355d67459785d8cb5f7072d60c	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-EC56F2A28973	2026-10-12 16:51:16.261388+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	cf0497ad194c49158898dcaad8aeeffe	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-0ADF2AC56381	2026-10-12 16:51:16.508096+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	e951e47e8b324159b05fe162035f3212	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-642AE6BF6480	2026-10-12 16:51:17.707719+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	ff0221b17f984071817b39903d3454e7	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-BEC8CFC71082	2026-10-12 16:51:17.719573+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	50978012f8084f9dbb6bfabcfa56e868	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-F24972A4AF4E	2026-10-12 16:51:17.734535+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	ded78f1fc583471e9451d66a7e63c93b	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-DCD6E48742B3	2026-10-12 16:51:21.763883+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	4bc493fa7e8f420b9fc446a1aa0aa93b	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-6EE58C275187	2026-10-12 16:51:21.82715+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	7e851de37cbb4844bd7173d08e424946	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-ACC0891896E3	2026-10-12 16:51:30.171454+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-2BF9B7E473	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	38d5ca8c314748d0b6417db55c18fbd3	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-FA6BE62ED4A2	2026-10-12 16:51:30.188215+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-2BF9B7E473	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	46225754599747fdb8b02de4cd5a1b29	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-7BDAAFA94018	2026-10-12 16:51:30.244053+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-2BF9B7E473	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	e3a806aa8f134eddb89951ec194cf0f8	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-8693E16615C4	2026-10-12 16:51:40.466398+05:30	superadmin	TENANT_CREATE	tenant	clinic_inact_test	{"name": "Inactive Clinic", "status": "ACTIVE"}	\N	\N	21566d773c014464baaeb51554d857d7	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-5228954A3D27	2026-10-12 16:51:40.466398+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_inact_test	{"status": "INACTIVE"}	\N	\N	854fa7f4f04c4c29be69bde85801f7cf	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-BB8E93773528	2026-10-12 16:51:40.827346+05:30	superadmin	TENANT_CREATE	tenant	cln_hash_check_clini_1aa48f	{"name": "Hash Check Clinic", "status": "ACTIVE"}	\N	\N	69be5b6117c843f7be3153b1dfafe4c3	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-F4CBC6B9FC70	2026-10-12 16:51:40.900472+05:30	superadmin	TENANT_ADMIN_CREATE	user	hash_check_admin	{"tenant_id": "cln_hash_check_clini_1aa48f", "username": "hash_check_admin", "role": "TENANT_ADMIN"}	\N	\N	12556d7e6e15467282a485411125feb7	2026-10-13 16:54:47.871096+05:30	2026-10-13 16:54:47.871096+05:30	default
AUD-9CAE063C8A8C	2026-10-12 16:51:41.080198+05:30	superadmin	TENANT_CREATE	tenant	audit_clinic	{"name": "Audit Clinic", "status": "ACTIVE"}	\N	\N	dabced3a1a704036ad126c58e583af3f	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-9ADCFB40782E	2026-10-12 16:51:41.83133+05:30	superadmin	TENANT_CREATE	tenant	cln_apollo_care_cent_3b6abf	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	840f90ea6b3e4dc488819a8ffee04245	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-172E70CC7188	2026-10-12 16:51:42.697727+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp_test	{"name": "Suspended Clinic", "status": "ACTIVE"}	\N	\N	ffee562a94a846099e6da8cdb6718fce	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-F47B4CED2F1A	2026-10-12 16:51:42.706147+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp_test	{"status": "SUSPENDED", "reason": "Administrative suspension"}	\N	\N	2806cf8a3e46408087c4ae45a687261f	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-6426195CD67F	2026-10-12 16:51:43.066524+05:30	superadmin	TENANT_CREATE	tenant	clinic_act	{"name": "Clinic Act", "status": "INACTIVE"}	\N	\N	ee5544b7127d48aca7a4ab55dca7f09a	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-47337FB15F50	2026-10-12 16:51:43.066524+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_act	{"status": "ACTIVE"}	\N	\N	f265a95ffc004d0e8e0635c752ac1ea7	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-D6E93F15A2BC	2026-10-12 16:51:43.249857+05:30	superadmin	TENANT_CREATE	tenant	city_med	{"name": "City Medical", "status": "ACTIVE"}	\N	\N	fd02c6f707dc4d28acf22ade45224b4e	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-3B19E3CE5156	2026-10-12 16:51:43.319373+05:30	superadmin	TENANT_ADMIN_CREATE	user	city_admin	{"tenant_id": "city_med", "username": "city_admin", "role": "TENANT_ADMIN"}	\N	\N	7213bd575c764b9bada36e9765e19069	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-F9F60301A4FF	2026-10-12 16:51:43.675737+05:30	superadmin	TENANT_CREATE	tenant	health_plus	{"name": "Health Plus", "status": "ACTIVE"}	\N	\N	43434679058d45099ee1523f436f1402	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-06F4CF53C0D5	2026-10-12 16:51:43.756805+05:30	superadmin	TENANT_ADMIN_CREATE	user	health_admin_user	{"tenant_id": "health_plus", "username": "health_admin_user", "role": "TENANT_ADMIN"}	\N	\N	558bb09f1e754a7bb83affc03a72e732	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-135224ADA002	2026-10-12 16:51:43.930875+05:30	superadmin	TENANT_CREATE	tenant	lotus_health	{"name": "Lotus Health", "status": "ACTIVE"}	\N	\N	2e73b0cb189e4130ae250d9f5d0a015f	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-9DD2D1B3692F	2026-10-12 16:51:44.005737+05:30	superadmin	TENANT_ADMIN_CREATE	user	admin_lotus	{"tenant_id": "lotus_health", "username": "admin_lotus", "role": "TENANT_ADMIN"}	\N	\N	0cbb3fec21a5424aae52017ac394bc51	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-106A55F52C4C	2026-10-12 16:51:44.352428+05:30	superadmin	TENANT_CREATE	tenant	clinic_deact	{"name": "Clinic Deact", "status": "ACTIVE"}	\N	\N	902149717ed84afc981198b92362c519	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-2D1CBB285F8D	2026-10-12 16:51:44.357345+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_deact	{"status": "INACTIVE"}	\N	\N	c44fa35148ef46f3868745cfc77a4bb0	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-8A0F18137A75	2026-10-12 16:51:44.554247+05:30	superadmin	TENANT_CREATE	tenant	cln_green_valley_med_9da6b4	{"name": "Green Valley Medical", "status": "ACTIVE"}	\N	\N	9f5a0024989f409fa3fab2ea18abfae6	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-0609525558E8	2026-10-12 16:51:44.919891+05:30	superadmin	TENANT_CREATE	tenant	clinic_react	{"name": "Reactivate Clinic", "status": "ACTIVE"}	\N	\N	88e7bc5816464195821f4d509f19f74f	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-B1A72CEA594C	2026-10-12 16:51:44.919891+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_react	{"status": "INACTIVE"}	\N	\N	eba5556fa04343ec8a6beda8182ff478	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-15875F88D13F	2026-10-12 16:51:44.928348+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_react	{"status": "ACTIVE"}	\N	\N	c4915f0c602d422cae7b997ceef3381f	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-4FB5E5ACDECB	2026-10-12 16:51:45.116482+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_2a966f	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	603a34e0e4624159b80c83ebc7147b8c	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-8CD087945852	2026-10-12 16:51:45.124586+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_14f22e	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	3f2121f874b54003a9ee428dcefa9455	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-3F4C7324C3B8	2026-10-12 16:51:45.320242+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp	{"name": "Clinic Susp", "status": "ACTIVE"}	\N	\N	545295a25a774926abed3cef8a8ee407	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-AA346589B86D	2026-10-12 16:51:45.328423+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp	{"status": "SUSPENDED", "reason": "Billing non-payment"}	\N	\N	d7c3ec2f5df846a0ad79c9765c550173	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-F8AF06C4A4D7	2026-10-12 16:51:46.463863+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-A529609EDA	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	8c82bf545f5245528b40905eda695cba	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-7197DEB287EC	2026-10-12 16:51:46.465635+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-A529609EDA	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	74c653d1ac5c41f9a838140e3dc6f818	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-4735E1D040FD	2026-10-12 16:51:46.478218+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-A4734E18D2	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	85f0f3849e7e48e9a9073090a7b0a2c3	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-2B6798FFA912	2026-10-12 16:51:46.480384+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-A4734E18D2	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	0d95d8af945d40ee9ea19f647cd73656	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-7138518FCBB0	2026-10-12 16:51:46.499222+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-B9CDC62971	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	15414ed1c5af41d8a00d1f41d2c99ceb	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-1BDC85C07A59	2026-10-12 16:51:46.503474+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-B9CDC62971	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	7e35199da2d247aeb4acfd7e8e25a41e	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-01665CD4E95F	2026-10-12 16:51:46.505522+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-B9CDC62971	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	2f7e0e9d668641b9b3da434d994e9ee6	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-7F535D98A7A2	2026-10-12 16:51:46.523824+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-676FD1C6C7	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	db7a31a46f3a420e84ac201c30c25b0a	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-19C27C2C8AA2	2026-10-12 16:51:46.525844+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-676FD1C6C7	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	bc8cd60a88404aa088126c09242fb110	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-370D74FEE58B	2026-10-12 16:51:46.558481+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-4E6F619A09	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	cf94151f7a4046d8b96a4e8597cf667a	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-06B2BC1F9CE6	2026-10-12 16:51:46.559058+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-4E6F619A09	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	b0ab5eda6d05405481d9c9e233247704	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-7B7F6EF45D53	2026-10-12 16:51:46.584994+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-DB90023541	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	8066c591fe8b4d2db133c2cb43efb970	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-AA87F0D2989A	2026-10-12 16:51:46.586668+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-DB90023541	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	cd25edf6fd7d46bc9d575f973cdf7a2a	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-1529697785B7	2026-10-12 16:51:49.672006+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-C93264EFE3	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	e8cd3fca6c2c40b5b1ccc6af282d4d57	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-65716BB175F9	2026-10-12 16:51:49.681376+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-C93264EFE3	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	cd45601829794cfbb2e3ba3560b2815e	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-02C3632B368C	2026-10-12 16:51:59.214958+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	5cebd263329b44a9a14f30faffcad39f	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-3D5A12B09C6A	2026-10-12 16:51:59.234347+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	88876f78bc5a4aa5b6f8258f3bf1bc84	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-4525FC6AA5AC	2026-10-12 16:51:59.243208+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	cd8cf7e2c6c64cc2af6da5a316aaf017	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-D7841480C01F	2026-10-12 16:51:59.372599+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	f7990d6b33cd4f6497a74f2b60f4f288	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-A753953A1166	2026-10-12 16:51:59.378112+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	6cf72c1a53d1496e8311d18a2009a2fd	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-002704618D70	2026-10-12 16:51:59.405661+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	c73d4cac8b774652aeeb4c68ebcdf24a	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-56C48002A4B0	2026-10-12 16:51:59.418659+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	ab1bd6cbec744a3f9f400efd54c02b7f	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-D0D8512FE6F6	2026-10-12 16:52:00.790939+05:30	admin	APPOINTMENT_CREATE	appointment	TKN_e3b4c0	{"patient_id": "PID_2383d7", "patient_name": "Patient 0", "doctor": "Dr. Rao", "date": "2026-10-13", "time": "11:00 AM", "slot_id": "S202", "amount": "500"}	\N	\N	ea32d7391b854e1fa085d3d5ee9e472b	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-657E0A2E1B61	2026-10-12 16:52:00.813035+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-F79F4E049A	{"patient_id": "P101", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	544a6014f76a4049abf0e5c2e573d8ac	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-EA0CF66A1B5E	2026-10-12 16:52:00.815912+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-F79F4E049A	{"patient_id": "P101", "appointment_id": "TKN-101", "version": 1}	\N	\N	515e51c7b64446d6a5959bfe78b0e93f	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-2BAADF7E27E8	2026-10-12 23:43:52.412834+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	e1fe87ae600b4e01943b8c80493c08a7	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-9B92C3198B42	2026-10-12 23:43:54.422667+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	1eaf33ad6ace46f08f69e761ec3d2617	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-D0F837CF517F	2026-10-12 23:43:54.602879+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	38a3a5244489451581bc536e4ba3b2c9	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-E5E6AADCFF7A	2026-10-12 23:43:54.823215+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	8e60859fb1d94ef5a51b91c2d6db324c	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-4914F455128E	2026-10-12 23:43:55.177605+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	a4a6e03cbfae4353add06876f5946f1f	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-B2A738FC0DF2	2026-10-12 23:43:55.593704+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	e325eb7555a64deaa15cd403066c82f6	2026-10-13 16:54:47.989681+05:30	2026-10-13 16:54:47.989681+05:30	default
AUD-5DF2AE0CADF0	2026-10-12 23:43:55.783494+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	48e64ec85d18427eb267dbf9e3b9c696	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-5835B2F172CB	2026-10-12 23:43:57.071044+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	f26a1be57c2e4efdaeb58964c8b9d86a	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-E245FECF4DF2	2026-10-12 23:43:57.095521+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	44b11dff338246f9849e3f2cb9dba40b	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-FEDCE5665A08	2026-10-12 23:43:57.116806+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	c16a6d4a98ff49428979a0e189cd3164	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-828C06F23FAE	2026-10-12 23:44:01.884551+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	8b3c12479fdc4a35b47bba16a255bbd0	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-48296C16EF0E	2026-10-12 23:44:01.956681+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	86e94dca616042a0ae04139bdf66d3e8	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-ED32B01575A9	2026-10-12 23:44:12.916192+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-17F9303D76	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	6c2414cbb1a048ae98976f48779329cd	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-0E074CA6A3D8	2026-10-12 23:44:12.925884+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-17F9303D76	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	42535e4fdfce4a06ab485282895430a4	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-2149EA91CBC1	2026-10-12 23:44:12.969507+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-17F9303D76	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	14a1dc6266e84ac6ae0c1294fff43314	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-75E2FAE59A6D	2026-10-12 23:44:24.11979+05:30	superadmin	TENANT_CREATE	tenant	clinic_inact_test	{"name": "Inactive Clinic", "status": "ACTIVE"}	\N	\N	7c70a2a2e3e145dc80a8b9ed6cb12f23	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-4950AFBBBC79	2026-10-12 23:44:24.126036+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_inact_test	{"status": "INACTIVE"}	\N	\N	5bbc9539cf964cc6bed3ae227ee1106d	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-95641D49D92D	2026-10-12 23:44:24.575592+05:30	superadmin	TENANT_CREATE	tenant	cln_hash_check_clini_849aa9	{"name": "Hash Check Clinic", "status": "ACTIVE"}	\N	\N	d4d901ef24174f078986c9857dc0516e	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-7AA114D069C1	2026-10-12 23:44:24.670837+05:30	superadmin	TENANT_ADMIN_CREATE	user	hash_check_admin	{"tenant_id": "cln_hash_check_clini_849aa9", "username": "hash_check_admin", "role": "TENANT_ADMIN"}	\N	\N	2c25af43e09a40e9b18fe8993f749cf5	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-38868F144060	2026-10-12 23:44:24.858266+05:30	superadmin	TENANT_CREATE	tenant	audit_clinic	{"name": "Audit Clinic", "status": "ACTIVE"}	\N	\N	c5264d3c9e5c478e9e0240dd182e340f	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-B69B6A98B43E	2026-10-12 23:44:26.305768+05:30	superadmin	TENANT_CREATE	tenant	cln_apollo_care_cent_654fec	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	731e12cabda94ac7a57f9906841e1d0b	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-5757B4BA14DE	2026-10-12 23:44:26.939628+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp_test	{"name": "Suspended Clinic", "status": "ACTIVE"}	\N	\N	d6587e975bc7429f9963b1082ebfeb41	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-48D87BE45D6C	2026-10-12 23:44:26.939628+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp_test	{"status": "SUSPENDED", "reason": "Administrative suspension"}	\N	\N	26357e1cf0cf400fb4fabed9153baa7d	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-9721FCE7EF4C	2026-10-12 23:44:27.32147+05:30	superadmin	TENANT_CREATE	tenant	clinic_act	{"name": "Clinic Act", "status": "INACTIVE"}	\N	\N	2cc40f7cd67a487eae66760947a6a20e	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-28D2A290B2E9	2026-10-12 23:44:27.330406+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_act	{"status": "ACTIVE"}	\N	\N	b977012b3a39441eac781aeb87a7b6f0	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-984672428C4C	2026-10-12 23:44:27.543753+05:30	superadmin	TENANT_CREATE	tenant	city_med	{"name": "City Medical", "status": "ACTIVE"}	\N	\N	5a4c7ba7796f4026bfb845be831d6ff4	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-8E6966B01D98	2026-10-12 23:44:27.63413+05:30	superadmin	TENANT_ADMIN_CREATE	user	city_admin	{"tenant_id": "city_med", "username": "city_admin", "role": "TENANT_ADMIN"}	\N	\N	5723be7325fc413b995527781b50e4d3	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-2C46188172E7	2026-10-12 23:44:28.015678+05:30	superadmin	TENANT_CREATE	tenant	health_plus	{"name": "Health Plus", "status": "ACTIVE"}	\N	\N	fff3c58cd1d84e7d8d497365d596fb5b	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-00FDB3D19551	2026-10-12 23:44:28.100127+05:30	superadmin	TENANT_ADMIN_CREATE	user	health_admin_user	{"tenant_id": "health_plus", "username": "health_admin_user", "role": "TENANT_ADMIN"}	\N	\N	6782567a90e84586a3c7f8ad538de181	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-E85A9C367FD9	2026-10-12 23:44:28.271185+05:30	superadmin	TENANT_CREATE	tenant	lotus_health	{"name": "Lotus Health", "status": "ACTIVE"}	\N	\N	2e50a093e35e4f8ca2dd408c3e40eead	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-31F75714E133	2026-10-12 23:44:28.341528+05:30	superadmin	TENANT_ADMIN_CREATE	user	admin_lotus	{"tenant_id": "lotus_health", "username": "admin_lotus", "role": "TENANT_ADMIN"}	\N	\N	172a649ec263499584594ea8f8e03b76	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-E794E639C972	2026-10-12 23:44:28.800191+05:30	superadmin	TENANT_CREATE	tenant	clinic_deact	{"name": "Clinic Deact", "status": "ACTIVE"}	\N	\N	62172552c6c2441ab5175130e52ae1b0	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-2C93885EC10C	2026-10-12 23:44:28.808486+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_deact	{"status": "INACTIVE"}	\N	\N	f330e881155545058e71a753012d0d2b	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-A21E6FFBE10D	2026-10-12 23:44:28.995539+05:30	superadmin	TENANT_CREATE	tenant	cln_green_valley_med_8572da	{"name": "Green Valley Medical", "status": "ACTIVE"}	\N	\N	d3b866c375ad447dbf7d35f0fb5436b2	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-ECFFD0D08EE6	2026-10-12 23:44:29.367029+05:30	superadmin	TENANT_CREATE	tenant	clinic_react	{"name": "Reactivate Clinic", "status": "ACTIVE"}	\N	\N	c6a3a16db8674b47909073e0c22e431e	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-A84F6E0A22EB	2026-10-12 23:44:29.372943+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_react	{"status": "INACTIVE"}	\N	\N	46f81449be224078854ccb327d137cc0	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-E2FE82685CB8	2026-10-12 23:44:29.389447+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_react	{"status": "ACTIVE"}	\N	\N	093f9e1706b14f0b8337ca74ffd16083	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-B84269E8D0C2	2026-10-12 23:44:29.575438+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_091891	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	e7a95c6edf3e4d3dbf7bd70f754c7d7f	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-8D880C8D073D	2026-10-12 23:44:29.580243+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_7e7ccf	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	2ccea6ad3fe64964ad1f920c1b2d0bb6	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-59E767BDEF0D	2026-10-12 23:44:29.761635+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp	{"name": "Clinic Susp", "status": "ACTIVE"}	\N	\N	a5013f69a9dc43fba98d06091dd9c1ec	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-17295369F5A9	2026-10-12 23:44:29.767781+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp	{"status": "SUSPENDED", "reason": "Billing non-payment"}	\N	\N	a1b91d9d7ccc4dbb9da0a822752dd15c	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-003378E3D950	2026-10-12 23:44:30.869729+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-72396F3498	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	ba80d063dace4c2381beb2a2313d1834	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-BD36037DC557	2026-10-12 23:44:30.871933+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-72396F3498	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	d916390c64394d1f85c9051b8a7b7131	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-4F774D6E1F20	2026-10-12 23:44:30.885033+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6344E92CA3	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	a1d83b010d2543f18455f8c8c7be0f34	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-D95CBC628EA7	2026-10-12 23:44:30.887592+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6344E92CA3	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	99ca566f575b4c0a9745b1483347dd24	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-76EC1FD887A8	2026-10-12 23:44:30.90201+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-4437C7DC91	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	6f73fb26bdfa45cebb1b522cbbf84057	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-0106B559BDF9	2026-10-12 23:44:30.90336+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-4437C7DC91	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	4b24cf9d170f4739b9f4a137f4981ea9	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-809ADF02123A	2026-10-12 23:44:30.90336+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-4437C7DC91	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	1602aab7af694d77b031f8005c6cce71	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-0E7433627F8C	2026-10-12 23:44:30.920078+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-D0E3A06644	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	837c0d56d5bd44d9aeff58fd4baed6ab	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-DF6F9479DAF6	2026-10-12 23:44:30.920624+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-D0E3A06644	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	4f76158092564cf6ad1929560cc219c9	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-A694F731D1B2	2026-10-12 23:44:30.952+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-BB8DD3FEF2	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	7686cfff7fec40759af53a6aa4593d17	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-5A6E305F43C0	2026-10-12 23:44:30.952594+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-BB8DD3FEF2	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	c1304aa5bbe345c681041c0ebec01eb6	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-E83056805E84	2026-10-12 23:44:30.982453+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-B7A2CAF500	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	fe998460206047839e35120ec5ca6f93	2026-10-13 16:54:47.990734+05:30	2026-10-13 16:54:47.990734+05:30	default
AUD-14320EEDA0B3	2026-10-12 23:44:30.982453+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-B7A2CAF500	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	9322f01a74064a5aa603b89e775ec784	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-FE06B762F1F9	2026-10-12 23:44:34.201793+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-F94E4744C5	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	aa0b561e3d6b4608b09331ccad0f569b	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-DF37820CC8CA	2026-10-12 23:44:34.217472+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-F94E4744C5	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	90b4ee5ec2824c8eba3708ad5b809e2f	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-4907AF8ACDCF	2026-10-12 23:44:43.809244+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	e5681572dede47e681a6dbf468cc22a9	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-CCF884A820CF	2026-10-12 23:44:43.845461+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	90d8ee182f48424c99cb30fd9ff2dc38	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-D4DCE363A2DB	2026-10-12 23:44:43.865292+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	396cf1e453e14e9ba36ca295f6cb5225	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-0796F9F99CC9	2026-10-12 23:44:43.982138+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	5ffb2da0ecfc411b8a209d2826470b5e	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-38393E2B542F	2026-10-12 23:44:43.982138+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	d5816cf356eb4619bafb2dfb6af437dc	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-8CE21E417AC0	2026-10-12 23:44:44.009412+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	b5670105f5264a68a591e27af992e663	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-737851FE4D0E	2026-10-12 23:44:44.019844+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	a06485b5561540499a9a33ff30e456af	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-B121191A0EF6	2026-10-12 23:44:45.271153+05:30	admin	APPOINTMENT_CREATE	appointment	TKN_b53cd3	{"patient_id": "PID_6160a7", "patient_name": "Patient 0", "doctor": "Dr. Rao", "date": "2026-10-13", "time": "11:00 AM", "slot_id": "S202", "amount": "500"}	\N	\N	b14bcdc31a41432a85e27e5934a83988	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-48DFF6D02C56	2026-10-12 23:44:45.288786+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-0A11A0AAB6	{"patient_id": "P101", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	205ee120b0944b3a9446cc87fe1ec833	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-38BD3FDFAAC8	2026-10-12 23:44:45.291+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-0A11A0AAB6	{"patient_id": "P101", "appointment_id": "TKN-101", "version": 1}	\N	\N	a4bd672f2f6145d1a7dc763a90b7fdef	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-335435099617	2026-10-12 23:45:52.338694+05:30	admin	APPOINTMENT_CREATE	appointment	TKN_b49aeb	{"patient_id": "PID_e13721", "patient_name": "Patient 0", "doctor": "Dr. Rao", "date": "2026-10-13", "time": "11:00 AM", "slot_id": "S202", "amount": "500"}	\N	\N	4bab3c038ab0444bbb82bf2319a3dbb2	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-0711881B49F5	2026-10-12 23:45:52.360202+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-889B0EBCBB	{"patient_id": "P101", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	06cdd7bfb6f44ae78b367f214bcafdda	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-7898E3331B8E	2026-10-12 23:45:52.360202+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-889B0EBCBB	{"patient_id": "P101", "appointment_id": "TKN-101", "version": 1}	\N	\N	aadee28e01ae4b3a95f958fab59a8007	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-7488AA6E4A5D	2026-10-12 23:48:23.626534+05:30	admin	APPOINTMENT_STATUS_UPDATE	appointment	TKN-001	{"old_status": "Confirmed", "new_status": "Completed"}	\N	\N	0e61231adc5048abbe9ff9d9be5b1e4a	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-1D40A33F79D9	2026-10-12 23:48:24.960568+05:30	admin	DOCTOR_CREATE	doctor	D3	{"name": "Dr. Rohit Verma", "specialization": "Dermatologist", "qualification": "", "registration_number": "", "available_days": "Monday, Thursday", "start_time": "2:00 PM", "end_time": "5:00 PM", "consultation_fee": "600", "status": "Active"}	\N	\N	7697aa0980e3443d94f2b1fcce1daa1d	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-7E52B6D5C9DB	2026-10-12 23:48:25.092881+05:30	admin	DOCTOR_STATUS_CHANGE	doctor	D1	{"status": "Inactive"}	\N	\N	c50b74ed990d4c4d826b188067f572ab	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-CF19A3DF086A	2026-10-12 23:48:25.224666+05:30	admin	PATIENT_CREATE	patient	None	{"name": "Alice Wonderland", "phone": "9998887776", "email": "alice@example.com"}	\N	\N	4c2760750aa24aceb5feff3088ba3f0e	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-11A0CD66FBC2	2026-10-12 23:48:25.477269+05:30	admin	PATIENT_UPDATE	patient	PAT-001	{"email": "new_john@example.com", "age": "31"}	\N	\N	20006031dfdf4650a213ce4f1820002e	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-E08270834D81	2026-10-12 23:48:25.792638+05:30	admin	PAYMENT_STATUS_UPDATE	payment	TKN-001	{"payment_status": "Paid"}	\N	\N	a9349dbc83b549aaba2ea4d5bbcf40cd	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-702966BE427D	2026-10-12 23:48:25.941094+05:30	admin	SLOT_STATUS_CHANGE	slot	S2	{"status": "Unavailable"}	\N	\N	ca9e913234804138be619da7e0ca9973	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-2AD00AD1691E	2026-10-12 23:48:27.141451+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	c249985058914e71963f1ca79b9e70f7	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-7978A954B701	2026-10-12 23:48:27.165174+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "Doc", "date": "2023-01-01", "time": "10:00", "slot_id": "S1", "amount": "500"}	\N	\N	1534930d8532447183324ea92ee994bc	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-D0A601939056	2026-10-12 23:48:27.229319+05:30	admin	APPOINTMENT_CREATE	appointment	T1	{"patient_id": "P1", "patient_name": "Test User", "doctor": "", "date": "", "time": "", "slot_id": "S1", "amount": "500"}	\N	\N	644ca3a3c33941879258cfb217943754	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-2E8A81E8EB4F	2026-10-12 23:48:31.941776+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "S7"}	\N	\N	bd0c95019b2641ce8ba91440ece46674	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-B494F2F8BB1C	2026-10-12 23:48:32.02504+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-09-29", "old_time": "10:00", "new_date": "2026-09-30", "new_time": "10:00", "new_slot_id": "S1"}	\N	\N	2c9fdc96b96f4cd0abd4d6339cafb0e6	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-CAEF3C670E1A	2026-10-12 23:48:39.859191+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-86692987B9	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "status": "draft"}	\N	\N	b86e4f454fea42d2b6cc13c15b3aa09f	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-FA455DB87994	2026-10-12 23:48:39.877778+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-86692987B9	{"patient_id": "P-API-101", "appointment_id": "TKN-API-001", "version": 1}	\N	\N	4548ccaf8f134cc693fba4ad72e781fa	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-FE7A146F2F5B	2026-10-12 23:48:39.909393+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-86692987B9	{"new_version": 2, "reason": "Corrected duration"}	\N	\N	693107ea92c948b19f6a905b69f052fc	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-9EA9F4406E71	2026-10-12 23:48:50.639249+05:30	superadmin	TENANT_CREATE	tenant	clinic_inact_test	{"name": "Inactive Clinic", "status": "ACTIVE"}	\N	\N	5f3657566c8f4081bdc2b4742a8bc438	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-DC93011A68B4	2026-10-12 23:48:50.647162+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_inact_test	{"status": "INACTIVE"}	\N	\N	0bad28817d644b9481a2cc890e9becd0	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-79AA62BBD89F	2026-10-12 23:48:51.034408+05:30	superadmin	TENANT_CREATE	tenant	cln_hash_check_clini_8796be	{"name": "Hash Check Clinic", "status": "ACTIVE"}	\N	\N	b9b28e515aa548f285671b38385242b7	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-870471228ECB	2026-10-12 23:48:51.102228+05:30	superadmin	TENANT_ADMIN_CREATE	user	hash_check_admin	{"tenant_id": "cln_hash_check_clini_8796be", "username": "hash_check_admin", "role": "TENANT_ADMIN"}	\N	\N	0c330de6502443b7a9d3c66e76b1a03f	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-9BDF8885B1C1	2026-10-12 23:48:51.294386+05:30	superadmin	TENANT_CREATE	tenant	audit_clinic	{"name": "Audit Clinic", "status": "ACTIVE"}	\N	\N	fab155d78c5a47fcb35d3ac05d24879f	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-FB144743B193	2026-10-12 23:48:52.049951+05:30	superadmin	TENANT_CREATE	tenant	cln_apollo_care_cent_ca56ca	{"name": "Apollo Care Center", "status": "ACTIVE"}	\N	\N	24ef30e009874c4781e3057d7b23d70c	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-2B1E3FF75F70	2026-10-12 23:48:53.051618+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp_test	{"name": "Suspended Clinic", "status": "ACTIVE"}	\N	\N	58e85a684944462eab1174497127573b	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-7FCB29FF1E32	2026-10-12 23:48:53.056598+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp_test	{"status": "SUSPENDED", "reason": "Administrative suspension"}	\N	\N	477e0a7069024a92ab8a03b30c82e350	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-B1F41C6EE8F9	2026-10-12 23:48:53.424167+05:30	superadmin	TENANT_CREATE	tenant	clinic_act	{"name": "Clinic Act", "status": "INACTIVE"}	\N	\N	524f71a14db74c4982c6d5334b1424a2	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-29D43BB41B90	2026-10-12 23:48:53.42656+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_act	{"status": "ACTIVE"}	\N	\N	cbe26e3fadf94325a4ce7a8831f53fbf	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-D5404023DBA1	2026-10-12 23:48:53.616104+05:30	superadmin	TENANT_CREATE	tenant	city_med	{"name": "City Medical", "status": "ACTIVE"}	\N	\N	7038f442bc274946ab3347f8483a5c29	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-FBF44F36E5F8	2026-10-12 23:48:53.688609+05:30	superadmin	TENANT_ADMIN_CREATE	user	city_admin	{"tenant_id": "city_med", "username": "city_admin", "role": "TENANT_ADMIN"}	\N	\N	dfbebcaa7f284f91942c5e6da65a0a66	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-40BEBC31BBEB	2026-10-12 23:48:54.105057+05:30	superadmin	TENANT_CREATE	tenant	health_plus	{"name": "Health Plus", "status": "ACTIVE"}	\N	\N	debff15af14e4bef98e8e843e17f1e5b	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-63088613DE3D	2026-10-12 23:48:54.184741+05:30	superadmin	TENANT_ADMIN_CREATE	user	health_admin_user	{"tenant_id": "health_plus", "username": "health_admin_user", "role": "TENANT_ADMIN"}	\N	\N	50af0c1d0a774973b971675586f44622	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-2565F52E9F36	2026-10-12 23:48:54.367183+05:30	superadmin	TENANT_CREATE	tenant	lotus_health	{"name": "Lotus Health", "status": "ACTIVE"}	\N	\N	0a5f043ebca444ffbdc4a10bdb2ae838	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-08EC36C74A94	2026-10-12 23:48:54.442022+05:30	superadmin	TENANT_ADMIN_CREATE	user	admin_lotus	{"tenant_id": "lotus_health", "username": "admin_lotus", "role": "TENANT_ADMIN"}	\N	\N	11d06cb9f7d64eb5b259c6d8e70beb6e	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-4B3CD9DFB9D0	2026-10-12 23:48:54.818013+05:30	superadmin	TENANT_CREATE	tenant	clinic_deact	{"name": "Clinic Deact", "status": "ACTIVE"}	\N	\N	cd6a8f84a3ea415bae31f2f2ba5c233a	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-DBBA0549435F	2026-10-12 23:48:54.818013+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_deact	{"status": "INACTIVE"}	\N	\N	ce8951ba4a4046aba806afc891290548	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-2550D519780F	2026-10-12 23:48:55.048917+05:30	superadmin	TENANT_CREATE	tenant	cln_green_valley_med_519025	{"name": "Green Valley Medical", "status": "ACTIVE"}	\N	\N	d8189ebe62b84fa4b9e60c00b3d686db	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-D02B840DCD81	2026-10-12 23:48:55.384811+05:30	superadmin	TENANT_CREATE	tenant	clinic_react	{"name": "Reactivate Clinic", "status": "ACTIVE"}	\N	\N	f9eaef1fd4ba48c8bacad556221749ca	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-204DCDE599D9	2026-10-12 23:48:55.399635+05:30	superadmin	TENANT_DEACTIVATE	tenant	clinic_react	{"status": "INACTIVE"}	\N	\N	eeae777ea79c4310b719c8ace16835be	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-79CA0A197AC3	2026-10-12 23:48:55.409578+05:30	superadmin	TENANT_ACTIVATE	tenant	clinic_react	{"status": "ACTIVE"}	\N	\N	bc13608d27224e6e90f256434cc58e04	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-2EF9F0CF8F47	2026-10-12 23:48:55.634463+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_2fd3fe	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	716077abb9b349ad87fc907d103924e5	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-3D1BCBFD76C4	2026-10-12 23:48:55.64586+05:30	superadmin	TENANT_CREATE	tenant	cln_clinic_alpha_d586a3	{"name": "Clinic Alpha", "status": "ACTIVE"}	\N	\N	2563769f20d3424d86491773460788ce	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-53B5592E606F	2026-10-12 23:48:55.814466+05:30	superadmin	TENANT_CREATE	tenant	clinic_susp	{"name": "Clinic Susp", "status": "ACTIVE"}	\N	\N	47298b3e77674a458a549529a67c2be9	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-387738359395	2026-10-12 23:48:55.820476+05:30	superadmin	TENANT_SUSPEND	tenant	clinic_susp	{"status": "SUSPENDED", "reason": "Billing non-payment"}	\N	\N	bc60d3623b2b4335aa1bfff7560cd066	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-021070E7FC91	2026-10-12 23:48:56.893213+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6BCBA86AD1	{"patient_id": "PAT001", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	cad8e7a99e1343e7bdb472582e0b09a8	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-FC17F93B40D2	2026-10-12 23:48:56.893213+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-6BCBA86AD1	{"patient_id": "PAT001", "appointment_id": "TKN-101", "version": 1}	\N	\N	ae9c4b22893f4603b4a044fb238f7693	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-54FF6FDF349D	2026-10-12 23:48:56.912453+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-87051737CE	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	82ceddd42852487ebb966930114eb927	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-24D22B0BCBB0	2026-10-12 23:48:56.91492+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-87051737CE	{"patient_id": "PAT002", "appointment_id": "TKN-102", "status": "draft"}	\N	\N	da1dc29e604c4f6e838d28255d0177f2	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-FF52C6CC48A1	2026-10-12 23:48:56.930413+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-7D008B48C2	{"patient_id": "PAT003", "appointment_id": "TKN-103", "status": "draft"}	\N	\N	ee2030b9865c43efae360e1881d3de6d	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-8B924F2416A8	2026-10-12 23:48:56.931434+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-7D008B48C2	{"patient_id": "PAT003", "appointment_id": "TKN-103", "version": 1}	\N	\N	cde7eaad735d4b79a85b60c47b43e556	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-375E717849E9	2026-10-12 23:48:56.935466+05:30	dr_arjun_api	PRESCRIPTION_AMENDMENT	prescription	RX-7D008B48C2	{"new_version": 2, "reason": "Dosage escalated due to uncontrolled systolic BP"}	\N	\N	055cfb7cbffd483e893a13219ee036c9	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-A692B921D7D7	2026-10-12 23:48:56.948828+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-6C3B414007	{"patient_id": "PAT004", "appointment_id": "TKN-104", "status": "draft"}	\N	\N	6f08521cf5f445debaa8b5054409d867	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-EEB024B58FFD	2026-10-12 23:48:56.948828+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-6C3B414007	{"patient_id": "PAT004", "appointment_id": "TKN-104", "version": 1}	\N	\N	fe24ec01b95a4e1085b17d8a443c3aab	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-910B45F5E0E7	2026-10-12 23:48:56.980292+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-C78D514178	{"patient_id": "PAT005", "appointment_id": "TKN-105", "status": "draft"}	\N	\N	4f325ea7493b4a5bae50e365878e3210	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-24A258340A56	2026-10-12 23:48:56.984174+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-C78D514178	{"patient_id": "PAT005", "appointment_id": "TKN-105", "version": 1}	\N	\N	32a41a6bef024f9e982462738e01463a	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-F0D46E25A518	2026-10-12 23:48:57.025285+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-576E8B2395	{"patient_id": "PAT010", "appointment_id": "TKN-201", "status": "draft"}	\N	\N	5ad681b61622480fb6bf53277cd2966e	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-52343B6780D3	2026-10-12 23:48:57.027982+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-576E8B2395	{"patient_id": "PAT010", "appointment_id": "TKN-201", "version": 1}	\N	\N	aa13f181c0bb42ef893db4004de9ada7	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-52ECAA969889	2026-10-12 23:49:00.290564+05:30	dr_arjun_api	PRESCRIPTION_DRAFT_SAVE	prescription	RX-20C5EBB770	{"patient_id": "PAT020", "appointment_id": "TKN-301", "status": "draft"}	\N	\N	5c960a38a243443c826c1ae92ac5a024	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-A05281DF942F	2026-10-12 23:49:00.389034+05:30	dr_arjun_api	PRESCRIPTION_FINALIZE	prescription	RX-20C5EBB770	{"patient_id": "PAT020", "appointment_id": "TKN-301", "version": 1}	\N	\N	cfd6e572e1334be09dc62159bf34fc7c	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-2E7F3A3D619A	2026-10-12 23:49:09.234255+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	d76e775f62ae43f2abf281a248fbf0aa	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-CCD033E126BF	2026-10-12 23:49:09.252273+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Family emergency", "released_slot_id": "SLOT-OLD-1"}	\N	\N	5b89ffe5f61e43c9974e012975055463	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-4A37D269061A	2026-10-12 23:49:09.261161+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "", "released_slot_id": "SLOT-OLD-1"}	\N	\N	9168e1507d3b454aa5333cef5fe08eca	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-0138F27A3F67	2026-10-12 23:49:09.379511+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	0a0b69be9e3b4d3ebd6b80a3109bef8c	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-7A75A096325B	2026-10-12 23:49:09.393577+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Schedule change", "released_slot_id": "SLOT-NEW-2"}	\N	\N	0fbcb2a124ca4ac489915110fe0e14ee	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-631308F8A166	2026-10-12 23:49:09.417315+05:30	admin	APPOINTMENT_RESCHEDULE	appointment	TKN-1001	{"old_date": "2026-10-13", "old_time": "10:00 AM", "new_date": "2026-10-19", "new_time": "11:00 AM", "new_slot_id": "SLOT-NEW-2"}	\N	\N	4b5205104cc44dbba9a3df543bfa5a27	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-5AA7296156A1	2026-10-12 23:49:09.43573+05:30	admin	APPOINTMENT_CANCEL	appointment	TKN-1001	{"reason": "Patient requested cancellation via Telegram", "released_slot_id": "SLOT-OLD-1"}	\N	\N	d364f07af4234d969f161dd80f367946	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-17F6697B9552	2026-10-12 23:49:10.924374+05:30	admin	APPOINTMENT_CREATE	appointment	TKN_b1a55e	{"patient_id": "PID_3cf10a", "patient_name": "Patient 0", "doctor": "Dr. Rao", "date": "2026-10-13", "time": "11:00 AM", "slot_id": "S202", "amount": "500"}	\N	\N	98c3d48c90de4f7d87bccb07909145d5	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-DE5612CF3EBF	2026-10-12 23:49:10.949187+05:30	doctor	PRESCRIPTION_DRAFT_SAVE	prescription	RX-3057F1114A	{"patient_id": "P101", "appointment_id": "TKN-101", "status": "draft"}	\N	\N	abee399904af464dabb8e0c65e37ddc0	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
AUD-26C4790E673D	2026-10-12 23:49:10.951201+05:30	doctor	PRESCRIPTION_FINALIZE	prescription	RX-3057F1114A	{"patient_id": "P101", "appointment_id": "TKN-101", "version": 1}	\N	\N	7fb6c8d69aaf49a2b08a91e5b2dfb685	2026-10-13 16:54:48.093516+05:30	2026-10-13 16:54:48.093516+05:30	default
\.


--
-- Data for Name: clinics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.clinics (name, legal_name, phone, email, address, timezone, currency, upi_id, is_active, id, created_at, updated_at, logo, website, status, working_days, working_hours, appointment_duration, booking_settings, rag_config_status, channel_config_status) FROM stdin;
XYZ Clinic	XYZ Clinic	\N	\N	\N	Asia/Kolkata	INR	\N	t	default	2026-10-13 16:54:42.925588+05:30	2026-10-13 16:54:42.925588+05:30	\N	\N	ACTIVE	Monday - Friday	09:00 - 17:00	30	\N	CONFIGURED	CONFIGURED
\.


--
-- Data for Name: doctors; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.doctors (doctor_id, name, specialization, qualification, registration_no, phone, email, available_days, start_time, end_time, consultation_fee, status, id, created_at, updated_at, tenant_id) FROM stdin;
DOC001	Dr. Arjun Mehta	General Physician	\N	\N	\N	\N	Monday, Wednesday, Friday	10:00 AM	1:00 PM	500	Active	681ed33150b04917afc9dbd3282476f4	2026-10-13 16:54:45.021095+05:30	2026-10-13 16:54:45.021095+05:30	default
DOC002	Dr. Sana Khan	Gynecologist	\N	\N	\N	\N	Tuesday, Thursday, Saturday	4:00 PM	7:00 PM	700	Inactive	b926588a9dde4080a4b974137742b6c6	2026-10-13 16:54:45.025174+05:30	2026-10-13 16:54:45.025174+05:30	default
DOC003	Dr. sufian	Cardiologist	\N	\N	\N	\N	Tuesday, Thursday, Saturday	4:00 PM	6:00 PM	900	Active	f8775846cbdd471c9f14ff2eafa73d0d	2026-10-13 16:54:45.0274+05:30	2026-10-13 16:54:45.0274+05:30	default
DOC004	Dr. Neha Sharma	Dermatologist	\N	\N	\N	\N	Monday, Wednesday, Friday	11:00 AM	2:00 PM	800	Active	fcd3cc09273a43978630e70cbc468926	2026-10-13 16:54:45.030924+05:30	2026-10-13 16:54:45.030924+05:30	default
DOC005	Dr. Rahul Verma	Orthopedic	\N	\N	\N	\N	Tuesday, Thursday, Saturday	10:00 AM	1:00 PM	900	Active	36240799cd7d4ae8b01d8902c3ddeb44	2026-10-13 16:54:45.030924+05:30	2026-10-13 16:54:45.030924+05:30	default
DOC006	Dr. Ayesha Khan	Pediatrician	\N	\N	\N	\N	Monday, Tuesday, Thursday	3:00 PM	6:00 PM	700	Active	a3cd5362ce0b422ba6316eb011e6c28a	2026-10-13 16:54:45.034904+05:30	2026-10-13 16:54:45.034904+05:30	default
DOC007	Dr. Vivek Singh	Cardiologist	\N	\N	\N	\N	Wednesday, Friday, Saturday	4:00 PM	7:00 PM	1200	Active	ab109a0898ce432ab32d00ebfb1d4ec6	2026-10-13 16:54:45.039037+05:30	2026-10-13 16:54:45.039037+05:30	default
DOC008	Dr. Priya Gupta	Gynecologist	\N	\N	\N	\N	Monday, Wednesday, Saturday	10:00 AM	1:00 PM	800	Active	4fc893efa2474b84be68de115c27e59a	2026-10-13 16:54:45.041637+05:30	2026-10-13 16:54:45.041637+05:30	default
\.


--
-- Data for Name: invoices; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.invoices (invoice_number, appointment_id, patient_id, amount, payment_method, payment_status, upi_id, qr_path, pdf_path, issued_date, notes, id, created_at, updated_at, tenant_id) FROM stdin;
INV-TKN-0001	b8c9eb02c78845ab9b64695e621fd9d9	c66b44b822c246f5b19cc501c58bb408	500	Offline	Pending	\N	\N	\N	2026-09-28	\N	ebfd2f693be9459bbf0b664aa40adea0	2026-10-13 16:54:46.510947+05:30	2026-10-13 16:54:46.510947+05:30	default
INV-TKN-0002	c0423602d52d4931af3e8874fe3630e7	8541e731df1a4a35b181c3f286742548	900`	Offline	Paid	\N	\N	\N	2026-09-29	\N	802d6861d444471fbcf1f4867ae60cf4	2026-10-13 16:54:46.521582+05:30	2026-10-13 16:54:46.521582+05:30	default
INV-TKN-0003	2fc75850b7534c338d3bde8932ea2890	4bbfa767f0c14855a7c0fc98c5475011	900	Offline	Pending	\N	\N	\N	2026-09-29	\N	3a74305046104c77acb0b86174090350	2026-10-13 16:54:46.528341+05:30	2026-10-13 16:54:46.528341+05:30	default
INV-TKN-0004	43636956d8074299a2c0750ecd634919	e97af421901648c59e1c3d6c012b61c0	900	Offline	Pending	\N	\N	\N	2026-09-29	\N	8534ce773fa74a81bc3673eb5eed00e9	2026-10-13 16:54:46.534895+05:30	2026-10-13 16:54:46.534895+05:30	default
INV-TKN-0005	3aeb839b7ec54859bbe6e2a7f41deadd	bb49d70c7cf44b7fbf5cfc08d87a580e	1200	Offline	Pending	\N	\N	\N	2026-10-02	\N	ed9c0d5b24274707a43fa3edea93faaf	2026-10-13 16:54:46.538681+05:30	2026-10-13 16:54:46.538681+05:30	default
INV-TKN-0006	4819b8dd8aa246449f8a1cf62b98fdbe	7474750da73649adaeb0d429c9e71a3f	800	Offline	Paid	\N	\N	\N	2026-10-03	\N	7bd5e44faade490d9b83f0882b2549b8	2026-10-13 16:54:46.543407+05:30	2026-10-13 16:54:46.543407+05:30	default
INV-TKN-0007	9bc61da881d14db6b51233c52a7e1c3a	ccd2911b8aec42e198d9e993ef6a9aef	800	Offline	Paid	\N	\N	\N	2026-10-03	\N	e8d3b83d8b29421fb239c9f5def558a5	2026-10-13 16:54:46.549391+05:30	2026-10-13 16:54:46.549391+05:30	default
INV-TKN-0008	ddb73a38b670463bbde4ba503f5561d2	871d42c48cb64560b6d4e94d9fd3f88d	800	Offline	Paid	\N	\N	\N	2026-10-03	\N	79a0a8ea78af40f6bedb2c36ec9f40e9	2026-10-13 16:54:46.554003+05:30	2026-10-13 16:54:46.554003+05:30	default
INV-TKN-0009	a710591788dd41bc803282587955bacb	79b9ffffbd3049e8904073001a1741fb	900	Cash	Paid	\N	\N	\N	2026-10-05	\N	f4f5b45400cf42d38879d10ea2629baf	2026-10-13 16:54:46.558652+05:30	2026-10-13 16:54:46.558652+05:30	default
INV-TKN-0010	5c19c289b25c41d4a729e017f1cfe66a	2bd918c7687b4692a1e4cc5b775de732	900	Cash	Paid	\N	\N	\N	2026-10-06	\N	2d915e5b6eea4169a963c58f522757c9	2026-10-13 16:54:46.561706+05:30	2026-10-13 16:54:46.561706+05:30	default
\.


--
-- Data for Name: patients; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.patients (patient_id, name, phone, email, age, gender, address, medical_history, id, created_at, updated_at, tenant_id) FROM stdin;
PAT-F1482B84D01A	shadab	6200126662	khansyrian1@gmail.com			\N	\N	c66b44b822c246f5b19cc501c58bb408	2026-10-13 16:54:45.481587+05:30	2026-10-13 16:54:45.481587+05:30	default
PAT-BD1B1B70C66F	mozammel	6200126662	khansyrian1@gmail.com			\N	\N	8541e731df1a4a35b181c3f286742548	2026-10-13 16:54:45.48546+05:30	2026-10-13 16:54:45.48546+05:30	default
PAT-533560FC8A6B	sufian	6200126662	khansyrian1@gmail.com			\N	\N	4bbfa767f0c14855a7c0fc98c5475011	2026-10-13 16:54:45.488274+05:30	2026-10-13 16:54:45.488274+05:30	default
PAT-7DE5B634532E	habiba	8826078511	habibashahid8743@gmail.com			\N	\N	e97af421901648c59e1c3d6c012b61c0	2026-10-13 16:54:45.491738+05:30	2026-10-13 16:54:45.491738+05:30	default
PAT-61BA36994E86	sufian	6200126662	khansyrian1@gmail.com			\N	\N	bb49d70c7cf44b7fbf5cfc08d87a580e	2026-10-13 16:54:45.493255+05:30	2026-10-13 16:54:45.493255+05:30	default
PAT-8DF0C5F8566E	मेरा नाम सुफियान है	5415563565	khansyrian1@gmail.com			\N	\N	7474750da73649adaeb0d429c9e71a3f	2026-10-13 16:54:45.493255+05:30	2026-10-13 16:54:45.493255+05:30	default
PAT-A724760CEC48	asad	9939759658	mrsufiankhan69@gmail.com			\N	\N	ccd2911b8aec42e198d9e993ef6a9aef	2026-10-13 16:54:45.498529+05:30	2026-10-13 16:54:45.498529+05:30	default
PAT-B4D645DB67C3	meera	9939759658	mrsufiankhan69@gmail.com			\N	\N	871d42c48cb64560b6d4e94d9fd3f88d	2026-10-13 16:54:45.498529+05:30	2026-10-13 16:54:45.498529+05:30	default
PAT-E951FE619734	mozammel	9939759658	khansyrian1@gmail.com			\N	\N	79b9ffffbd3049e8904073001a1741fb	2026-10-13 16:54:45.503866+05:30	2026-10-13 16:54:45.503866+05:30	default
PAT-DFFF93C77BB2	tasjin	9939759658	khansyrian1@gmail.com			\N	\N	2bd918c7687b4692a1e4cc5b775de732	2026-10-13 16:54:45.503866+05:30	2026-10-13 16:54:45.503866+05:30	default
P-API-101	Test Patient	0000000000	patient@example.com	\N	\N	\N	\N	ea6b15af48224e5585eeb88fc2cadf3d	2026-10-13 16:54:46.566334+05:30	2026-10-13 16:54:46.566334+05:30	default
PAT020	Kavita Rao	9988776655	kavita@example.com	\N	\N	\N	\N	094c920ea3c44c2c9c3f67b35414cc79	2026-10-13 16:54:46.613309+05:30	2026-10-13 16:54:46.613309+05:30	default
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payments (payment_id, appointment_id, invoice_id, amount, currency, payment_method, payment_status, transaction_reference, gateway, gateway_payload, paid_at, id, created_at, updated_at, tenant_id) FROM stdin;
PAY-TKN-0001	b8c9eb02c78845ab9b64695e621fd9d9	ebfd2f693be9459bbf0b664aa40adea0	500	INR	Offline	Pending	\N	Offline	\N	\N	0fa5b9ce29044ddb96eec0b6d44e7fe7	2026-10-13 16:54:46.521582+05:30	2026-10-13 16:54:46.521582+05:30	default
PAY-TKN-0002	c0423602d52d4931af3e8874fe3630e7	802d6861d444471fbcf1f4867ae60cf4	900`	INR	Offline	Paid	\N	Offline	\N	\N	2d9ebb8968f54de7a9239f00f91e90c9	2026-10-13 16:54:46.528341+05:30	2026-10-13 16:54:46.528341+05:30	default
PAY-TKN-0003	2fc75850b7534c338d3bde8932ea2890	3a74305046104c77acb0b86174090350	900	INR	Offline	Pending	\N	Offline	\N	\N	8601e506c99840c585f49e459282a8c3	2026-10-13 16:54:46.528341+05:30	2026-10-13 16:54:46.528341+05:30	default
PAY-TKN-0004	43636956d8074299a2c0750ecd634919	8534ce773fa74a81bc3673eb5eed00e9	900	INR	Offline	Pending	\N	Offline	\N	\N	1c7a3edda19547599e7456b1a0a1df78	2026-10-13 16:54:46.536148+05:30	2026-10-13 16:54:46.536148+05:30	default
PAY-TKN-0005	3aeb839b7ec54859bbe6e2a7f41deadd	ed9c0d5b24274707a43fa3edea93faaf	1200	INR	Offline	Pending	\N	Offline	\N	\N	42bc8a71fc7e486db9f394f2027fb7cb	2026-10-13 16:54:46.543407+05:30	2026-10-13 16:54:46.543407+05:30	default
PAY-TKN-0006	4819b8dd8aa246449f8a1cf62b98fdbe	7bd5e44faade490d9b83f0882b2549b8	800	INR	Offline	Paid	\N	Offline	\N	\N	fe781641027e42bab8dba12c86f4e9d3	2026-10-13 16:54:46.543407+05:30	2026-10-13 16:54:46.543407+05:30	default
PAY-TKN-0007	9bc61da881d14db6b51233c52a7e1c3a	e8d3b83d8b29421fb239c9f5def558a5	800	INR	Offline	Paid	\N	Offline	\N	\N	9ca10641554f4e00b525f8ca0aafbf45	2026-10-13 16:54:46.552272+05:30	2026-10-13 16:54:46.552272+05:30	default
PAY-TKN-0008	ddb73a38b670463bbde4ba503f5561d2	79a0a8ea78af40f6bedb2c36ec9f40e9	800	INR	Offline	Paid	\N	Offline	\N	\N	9852bd6bb3c441d08c63e5e5000840d1	2026-10-13 16:54:46.557112+05:30	2026-10-13 16:54:46.557112+05:30	default
PAY-TKN-0009	a710591788dd41bc803282587955bacb	f4f5b45400cf42d38879d10ea2629baf	900	INR	Cash	Paid	\N	Offline	\N	\N	3424e2eb825f453e9b7d0c81bd593465	2026-10-13 16:54:46.560169+05:30	2026-10-13 16:54:46.560169+05:30	default
PAY-TKN-0010	5c19c289b25c41d4a729e017f1cfe66a	2d915e5b6eea4169a963c58f522757c9	900	INR	Cash	Paid	\N	Offline	\N	\N	a355b9c9ba8048a6954e1a10e5c7e942	2026-10-13 16:54:46.563247+05:30	2026-10-13 16:54:46.563247+05:30	default
\.


--
-- Data for Name: prescription_items; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.prescription_items (prescription_id, order_index, name, strength, dosage, frequency, duration, instructions, id, created_at, updated_at) FROM stdin;
048e2b57d6594db7bc2d6949d9c0fae2	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	8f04bbd63f684aaf877f523941adea09	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
1b4f88f4b7104349a4c8901636c57f44	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	56c27de724464a848c1b54439eed9753	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
e3e4e40359764db6a710511b5cf7ce29	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	1fe07b59ce0044b6a7aee0ea0946023c	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
a51d4b89e9e849d2817d1fb081f5f278	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	15f7faf671254e92b3dc7ed41b74bc92	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
4c68266052614759af2a233093a152ee	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	20f8fb57f325455c94a849b416f50c1c	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
65ee535e47554d6abc02103eb18efbf6	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	53464122c2dc443d887871e87ebead53	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
084790c93d454635917f37b899d549fc	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	431f8045ccbf4048aa3cf7433c17d40a	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
7d0f390dff9f4004bae467afe50e0a55	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	239c1a2205604a19ac009e2e9c20ed97	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
e0baf16bf68a4e5fb710fad0d1d4a4f3	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	205754c871624ba5a080924a55b2a780	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
d4b4686592e84e55b07bf4aa6a83b7a3	0	paracetomol	\N	1 `	1	5	after food	0258c34e4b10474a9fa931bb5e711f9a	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
e53ffd118514477b8b92633d58816467	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	98654fd2667d4ff08496bf91fc89cee6	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
3e24a08cc29947109c2b475640fb5162	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	9366e48b5da3481a90cbbf28da0b6c82	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
899ccd17ee2b4a6294815e7a96875221	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	b761a55cc11f435db75b4de7b3004cd6	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
de2930374a384390b41a9cee1d97b721	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	08796671e5ec488f81d126b7a176d38d	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
2d3b993766514c27958661f67045b734	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	f121971b0e9f4c8c9c415e34215b256c	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
877d2253b7d44fedaaf7a71eafc35445	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	1187e6625b1a4514b8562fb04d44e66e	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
876387a85591462cbb00d84694a21d18	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	dfc5af2f37f845fe8e4be4c399651a6a	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
67cba536d21047a4935de98998594dba	0	paracetomal	\N	1	1	7 days	after dinner	305e0bc263e1408d84b13d02658461ca	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
df6996c3fa5b450bbc4f765bcd11e11d	0	sejdnfka	\N	1	1	5	after food	e4aef7da840740e8be83a83b01b2dcb4	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
4953755218fd4557b625922ae95baf24	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	75610f9f2073412287f0580088a3df1d	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
67e104c2cc444525a62853c052a36840	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	3c157407ebce47b1ba9405c29031a0ef	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
5a62fc3178524fe19bb20314d75ebcb4	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	4012577f67454612b37c3a0f005e0d0e	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
0c2bfd7d3b914d4ca5b072a7e3ac1dde	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	3ce2fa17c90449f98b3c69b2da851d76	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
7141841bf22b4bedbf66b76493065823	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	44c981d20bb04f099aa9740c83303685	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
0972400eb2d246259962241c2d32872c	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	f13a033c446b4dceaea654fe84b0906b	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
e91dbec4e8ef4d00bb7b629e7f8a6906	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	5075672839fd413c9d7e799e122f4e4d	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
aa2b75d71bbc4deda4dcb342837b6994	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	4743b63503694232b17bb6e3fb9d0e6e	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
5fd1536d87c94430bcb08aabf3a508a1	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	3bfbf24c640b494c8d1ba0f1e1a649d3	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
be2527ce4eb64bf5a49603ff97602a82	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	8612dacca3eb4c1f9f2237dfc0e768a4	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
3f4ca5300ce147619f89483b30f53cb9	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	a2292f887b464408a8be93b7b8cdbdee	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
9ae0a3138ca64f30a490cc92767f64f0	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	00647f58ed934c5599a65f1efbae48e6	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
8db06173d4834d5b9dc638ac4ea04628	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	904572ec8a614cab8700c67663bff07c	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
59a17864947b4e17ac40a2ddbb545efe	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	4237cd98ff354c63968a2f0fcb04bc41	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
88e50a0c387d49909aa637cb03185c28	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	116589872b0e4401af9073744fc5435d	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
2f98227f594143109ae5899124950510	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	d6af332388dd48b5aac337de8e1d69df	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
b798df8eb25743da941b6a135475d0e3	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	f4ab66eca855448ebef539ef51acd6f0	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
bb0d8925f9e14f5d82a93cf44778c6b2	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	e768c8752d7f4b9693c324a4a7508d42	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
7522c7ac1fc840f780cefbdd80397daf	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	c7913ac4542c44bf8e2d041d2aebc5c5	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
fe7d27e05d164bba82193af25bc40685	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	c33c0df9c64a4bb28c5c7e9ae3a8efb6	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
e5872c07bf3f45ba9e9b93e53461be5f	0	Paracetamol	\N	500mg	1-0-1	5 days	After food with warm water	0588d6ee6387402cbdb60f101f335388	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
0766ec9e0b234815b2c9705741994485	0	Paracetamol	\N	1 tab	1-0-1	5 days	After meals	e92ed27bcc004b8cb6bc13b9c8a4e6b6	2026-10-13 16:55:45.75837+05:30	2026-10-13 16:55:45.75837+05:30
\.


--
-- Data for Name: prescriptions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.prescriptions (prescription_id, patient_id, doctor_id, appointment_id, date, version, status, chief_complaints, diagnosis, symptoms, vitals, clinical_notes, tests_advised, advice, follow_up_date, created_by, updated_by, finalized_at, version_history, email_delivery, pdf_path, id, created_at, updated_at, tenant_id) FROM stdin;
RX-70A5087181	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	2	finalized	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "diagnosis": "Viral Fever", "symptoms": "High temperature", "medicines": [{"name": "Paracetamol", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "advice": "", "follow_up_date": "", "finalized_at": "2026-10-02T10:41:29.577729+00:00", "amended_at": "2026-10-02T10:41:29.593829+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	048e2b57d6594db7bc2d6949d9c0fae2	2026-10-13 16:54:46.577155+05:30	2026-10-13 16:54:46.577155+05:30	default
RX-DB6C3CAE3C	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	2	finalized	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "diagnosis": "Viral Fever", "symptoms": "High temperature", "medicines": [{"name": "Paracetamol", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "advice": "", "follow_up_date": "", "finalized_at": "2026-10-02T10:42:50.950423+00:00", "amended_at": "2026-10-02T10:42:50.967115+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	1b4f88f4b7104349a4c8901636c57f44	2026-10-13 16:54:46.581675+05:30	2026-10-13 16:54:46.581675+05:30	default
RX-BE41B9E2FB	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	2	finalized	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "diagnosis": "Viral Fever", "symptoms": "High temperature", "medicines": [{"name": "Paracetamol", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "advice": "", "follow_up_date": "", "finalized_at": "2026-10-02T10:43:51.520942+00:00", "amended_at": "2026-10-02T10:43:51.550143+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	e3e4e40359764db6a710511b5cf7ce29	2026-10-13 16:54:46.592153+05:30	2026-10-13 16:54:46.592153+05:30	default
RX-621A581280	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	2	finalized	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "diagnosis": "Viral Fever", "symptoms": "High temperature", "medicines": [{"name": "Paracetamol", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "advice": "", "follow_up_date": "", "finalized_at": "2026-10-02T10:51:42.471056+00:00", "amended_at": "2026-10-02T10:51:42.504259+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	a51d4b89e9e849d2817d1fb081f5f278	2026-10-13 16:54:46.593105+05:30	2026-10-13 16:54:46.593105+05:30	default
RX-EB7B47FE11	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	2	finalized	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "diagnosis": "Viral Fever", "symptoms": "High temperature", "medicines": [{"name": "Paracetamol", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "advice": "", "follow_up_date": "", "finalized_at": "2026-10-02T10:52:45.585900+00:00", "amended_at": "2026-10-02T10:52:45.618051+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	4c68266052614759af2a233093a152ee	2026-10-13 16:54:46.606214+05:30	2026-10-13 16:54:46.606214+05:30	default
RX-96BCF8A495	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	2	finalized	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "diagnosis": "Viral Fever", "symptoms": "High temperature", "medicines": [{"name": "Paracetamol", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "advice": "", "follow_up_date": "", "finalized_at": "2026-10-02T11:21:01.193643+00:00", "amended_at": "2026-10-02T11:21:01.268186+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	65ee535e47554d6abc02103eb18efbf6	2026-10-13 16:54:46.613309+05:30	2026-10-13 16:54:46.613309+05:30	default
RX-575E3E59C9	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-02T12:10:22.221175+00:00", "amended_at": "2026-10-02T12:10:22.266262+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	084790c93d454635917f37b899d549fc	2026-10-13 16:54:46.613309+05:30	2026-10-13 16:54:46.613309+05:30	default
RX-53BDA3B213	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	7d0f390dff9f4004bae467afe50e0a55	2026-10-13 16:54:46.627386+05:30	2026-10-13 16:54:46.627386+05:30	default
RX-DA7AC8838D	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-02T12:15:47.979689+00:00", "amended_at": "2026-10-02T12:15:48.005032+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	e0baf16bf68a4e5fb710fad0d1d4a4f3	2026-10-13 16:54:46.636128+05:30	2026-10-13 16:54:46.636128+05:30	default
RX-DE28DDAB57	4bbfa767f0c14855a7c0fc98c5475011	f8775846cbdd471c9f14ff2eafa73d0d	2fc75850b7534c338d3bde8932ea2890	2026-09-29	1	finalized	\N	acute viral infection	frontal	\N	\N	\N		2026-10-09	dr_sufian	\N	\N	[]	\N	\N	d4b4686592e84e55b07bf4aa6a83b7a3	2026-10-13 16:54:46.636128+05:30	2026-10-13 16:54:46.636128+05:30	default
RX-F2CE183C82	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	e53ffd118514477b8b92633d58816467	2026-10-13 16:54:46.642921+05:30	2026-10-13 16:54:46.642921+05:30	default
RX-6B6F19C478	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	3e24a08cc29947109c2b475640fb5162	2026-10-13 16:54:46.647488+05:30	2026-10-13 16:54:46.647488+05:30	default
RX-58A0AF0614	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	899ccd17ee2b4a6294815e7a96875221	2026-10-13 16:54:46.652641+05:30	2026-10-13 16:54:46.652641+05:30	default
RX-81501651A0	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	de2930374a384390b41a9cee1d97b721	2026-10-13 16:54:46.655966+05:30	2026-10-13 16:54:46.655966+05:30	default
RX-00EE91BF22	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	2d3b993766514c27958661f67045b734	2026-10-13 16:54:46.659742+05:30	2026-10-13 16:54:46.659742+05:30	default
RX-88893CCF3A	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	877d2253b7d44fedaaf7a71eafc35445	2026-10-13 16:54:46.666696+05:30	2026-10-13 16:54:46.666696+05:30	default
RX-7BD4953C39	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	876387a85591462cbb00d84694a21d18	2026-10-13 16:54:46.669524+05:30	2026-10-13 16:54:46.669524+05:30	default
RX-29E2D843CC	79b9ffffbd3049e8904073001a1741fb	f8775846cbdd471c9f14ff2eafa73d0d	a710591788dd41bc803282587955bacb	2026-10-05	1	finalized	\N	acute viral infection	headace	\N	\N	\N	paani jyada peena	2026-10-08	dr_sufian	\N	\N	[]	\N	\N	67cba536d21047a4935de98998594dba	2026-10-13 16:54:46.669524+05:30	2026-10-13 16:54:46.669524+05:30	default
RX-F36FD9B1EC	2bd918c7687b4692a1e4cc5b775de732	f8775846cbdd471c9f14ff2eafa73d0d	5c19c289b25c41d4a729e017f1cfe66a	2026-10-06	1	finalized	\N	acute viral infection		\N	\N	\N		2026-10-07	dr_sufian	\N	\N	[]	\N	\N	df6996c3fa5b450bbc4f765bcd11e11d	2026-10-13 16:54:46.677374+05:30	2026-10-13 16:54:46.677374+05:30	default
RX-A22B67C139	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-05	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-05T08:13:10.942472+00:00", "amended_at": "2026-10-05T08:13:10.960204+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	4953755218fd4557b625922ae95baf24	2026-10-13 16:54:46.677374+05:30	2026-10-13 16:54:46.677374+05:30	default
RX-AD8FD70725	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-05	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-05T08:14:28.680228+00:00", "amended_at": "2026-10-05T08:14:28.719988+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	67e104c2cc444525a62853c052a36840	2026-10-13 16:54:46.687993+05:30	2026-10-13 16:54:46.687993+05:30	default
RX-1B61B5740A	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	5a62fc3178524fe19bb20314d75ebcb4	2026-10-13 16:54:46.687993+05:30	2026-10-13 16:54:46.687993+05:30	default
RX-940D0E29DC	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-05	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-05T08:16:37.295640+00:00", "amended_at": "2026-10-05T08:16:37.330918+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	0c2bfd7d3b914d4ca5b072a7e3ac1dde	2026-10-13 16:54:46.692506+05:30	2026-10-13 16:54:46.692506+05:30	default
RX-B4CFB1E075	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	7141841bf22b4bedbf66b76493065823	2026-10-13 16:54:46.698971+05:30	2026-10-13 16:54:46.698971+05:30	default
RX-936616CA96	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-05	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-05T17:36:58.323158+00:00", "amended_at": "2026-10-05T17:36:58.356279+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	0972400eb2d246259962241c2d32872c	2026-10-13 16:54:46.701942+05:30	2026-10-13 16:54:46.701942+05:30	default
RX-0A531144C6	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	e91dbec4e8ef4d00bb7b629e7f8a6906	2026-10-13 16:54:46.70929+05:30	2026-10-13 16:54:46.70929+05:30	default
RX-A7F3304DA3	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-05	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-05T18:08:58.325835+00:00", "amended_at": "2026-10-05T18:08:58.350935+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	aa2b75d71bbc4deda4dcb342837b6994	2026-10-13 16:54:46.70929+05:30	2026-10-13 16:54:46.70929+05:30	default
RX-C185E2453F	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	5fd1536d87c94430bcb08aabf3a508a1	2026-10-13 16:54:46.70929+05:30	2026-10-13 16:54:46.70929+05:30	default
RX-F9324E1DF3	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-05	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-05T18:20:54.319412+00:00", "amended_at": "2026-10-05T18:20:54.360705+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	be2527ce4eb64bf5a49603ff97602a82	2026-10-13 16:54:46.723871+05:30	2026-10-13 16:54:46.723871+05:30	default
RX-9236DAA6D4	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	3f4ca5300ce147619f89483b30f53cb9	2026-10-13 16:54:46.724517+05:30	2026-10-13 16:54:46.724517+05:30	default
RX-7C16E114D3	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-07	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-07T16:54:30.432236+00:00", "amended_at": "2026-10-07T16:54:30.479925+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	9ae0a3138ca64f30a490cc92767f64f0	2026-10-13 16:54:46.733079+05:30	2026-10-13 16:54:46.733079+05:30	default
RX-9202D4D2D9	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	8db06173d4834d5b9dc638ac4ea04628	2026-10-13 16:54:46.735091+05:30	2026-10-13 16:54:46.735091+05:30	default
RX-6E4889BE48	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-12	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-12T10:43:43.734455+00:00", "amended_at": "2026-10-12T10:43:43.782086+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	59a17864947b4e17ac40a2ddbb545efe	2026-10-13 16:54:46.741494+05:30	2026-10-13 16:54:46.741494+05:30	default
RX-E051484ABC	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	88e50a0c387d49909aa637cb03185c28	2026-10-13 16:54:46.742192+05:30	2026-10-13 16:54:46.742192+05:30	default
RX-F414D81D44	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	2f98227f594143109ae5899124950510	2026-10-13 16:54:46.749162+05:30	2026-10-13 16:54:46.749162+05:30	default
RX-2BF9B7E473	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-12	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-12T11:21:30.171454+00:00", "amended_at": "2026-10-12T11:21:30.214116+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	b798df8eb25743da941b6a135475d0e3	2026-10-13 16:54:46.753485+05:30	2026-10-13 16:54:46.753485+05:30	default
RX-C93264EFE3	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	bb0d8925f9e14f5d82a93cf44778c6b2	2026-10-13 16:54:46.757328+05:30	2026-10-13 16:54:46.757328+05:30	default
RX-17F9303D76	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-12	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-12T18:14:12.923671+00:00", "amended_at": "2026-10-12T18:14:12.963641+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	7522c7ac1fc840f780cefbdd80397daf	2026-10-13 16:54:46.764636+05:30	2026-10-13 16:54:46.764636+05:30	default
RX-F94E4744C5	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	fe7d27e05d164bba82193af25bc40685	2026-10-13 16:54:46.769308+05:30	2026-10-13 16:54:46.769308+05:30	default
RX-86692987B9	ea6b15af48224e5585eeb88fc2cadf3d	681ed33150b04917afc9dbd3282476f4	\N	2026-10-12	2	amended	\N	Viral Fever	High temperature	\N	\N	\N			dr_arjun_api	\N	\N	[{"version": 1, "chief_complaints": "", "diagnosis": "Viral Fever", "symptoms": "High temperature", "vitals": {}, "clinical_notes": "", "medicines": [{"name": "Paracetamol", "strength": "", "dosage": "500mg", "frequency": "1-0-1", "duration": "3 days", "instructions": "After food"}], "tests_advised": "", "advice": "", "follow_up_date": "", "finalized_at": "2026-10-12T18:18:39.866312+00:00", "amended_at": "2026-10-12T18:18:39.909393+00:00", "amended_by": "dr_arjun_api", "amendment_reason": "Corrected duration"}]	\N	\N	e5872c07bf3f45ba9e9b93e53461be5f	2026-10-13 16:54:46.773413+05:30	2026-10-13 16:54:46.773413+05:30	default
RX-20C5EBB770	094c920ea3c44c2c9c3f67b35414cc79	681ed33150b04917afc9dbd3282476f4	\N	2026-10-02	1	finalized	\N	Osteoarthritis Grade 1		\N	\N	\N	Gentle physiotherapy exercises		dr_arjun_api	\N	\N	[]	\N	\N	0766ec9e0b234815b2c9705741994485	2026-10-13 16:54:46.773413+05:30	2026-10-13 16:54:46.773413+05:30	default
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (username, password_hash, role, doctor_id, full_name, email, phone, status, must_change_password, last_login, id, created_at, updated_at, tenant_id) FROM stdin;
superadmin	pbkdf2:sha256:100000$e1f840dbb312c080a8726d1133ab95df$55e3963e6387e92e642369c60aea0eb32a882cd8f6a180ab5cd9b65ca03dbecd	SUPER_ADMIN	\N	Super Administrator	superadmin@clinic.local	\N	Active	f	\N	b2f28a186e1f434a93321427ee61b69a	2026-10-13 16:54:42.99724+05:30	2026-10-13 16:54:42.99724+05:30	\N
admin	pbkdf2:sha256:100000$184dc5b332c22c3858a5c81bca0df32b$8c17ad1ec955f15b60302d62578237835c5ef3bb2ae3797ecfc84163ed4db5e9	TENANT_ADMIN	\N	XYZ Clinic Admin	admin@clinic.local	\N	Active	f	\N	813cae4d7e1c44e09a362ad34b4221bd	2026-10-13 16:54:43.072057+05:30	2026-10-13 16:54:43.072057+05:30	default
dr_arjun_api	pbkdf2:sha256:100000$1fcda9a524c63d52e10bc7c49fcdcb60$61f6fc7afe16a7c6f0af396a3ac74427e44fc4312dc6c9d9682479d266a219fc	DOCTOR	DOC001	Dr. Arjun Mehta	dr.arjun@test.com	\N	Active	t	\N	0255b4a0ad3c4f50a96a00b181133014	2026-10-13 16:54:45.045199+05:30	2026-10-13 16:54:45.045199+05:30	default
dr_sufian	pbkdf2:sha256:100000$f4006a8b2fc21a66dffb410285a01d9d$56d6a191fba0dbb520b4e119fa117ad94d402aeeb27873040368dfd798a11175	DOCTOR	DOC003	Dr. sufian	dr.sufian@clinic.com	\N	Active	t	\N	fcd659f3e1e946449558ac248bd96ab6	2026-10-13 16:54:45.047841+05:30	2026-10-13 16:54:45.047841+05:30	default
\.


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: appointment_slots pk_appointment_slots; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointment_slots
    ADD CONSTRAINT pk_appointment_slots PRIMARY KEY (id);


--
-- Name: appointments pk_appointments; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT pk_appointments PRIMARY KEY (id);


--
-- Name: audit_logs pk_audit_logs; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT pk_audit_logs PRIMARY KEY (id);


--
-- Name: clinics pk_clinics; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.clinics
    ADD CONSTRAINT pk_clinics PRIMARY KEY (id);


--
-- Name: doctors pk_doctors; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT pk_doctors PRIMARY KEY (id);


--
-- Name: invoices pk_invoices; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT pk_invoices PRIMARY KEY (id);


--
-- Name: patients pk_patients; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT pk_patients PRIMARY KEY (id);


--
-- Name: payments pk_payments; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT pk_payments PRIMARY KEY (id);


--
-- Name: prescription_items pk_prescription_items; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescription_items
    ADD CONSTRAINT pk_prescription_items PRIMARY KEY (id);


--
-- Name: prescriptions pk_prescriptions; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT pk_prescriptions PRIMARY KEY (id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: appointments uq_appointment_doctor_datetime; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT uq_appointment_doctor_datetime UNIQUE (doctor_id, appointment_date, appointment_time);


--
-- Name: appointments uq_appointment_tenant_token_no; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT uq_appointment_tenant_token_no UNIQUE (tenant_id, token_no);


--
-- Name: audit_logs uq_audit_tenant_audit_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT uq_audit_tenant_audit_id UNIQUE (tenant_id, audit_id);


--
-- Name: doctors uq_doctor_tenant_doctor_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT uq_doctor_tenant_doctor_id UNIQUE (tenant_id, doctor_id);


--
-- Name: invoices uq_invoice_tenant_inv_no; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT uq_invoice_tenant_inv_no UNIQUE (tenant_id, invoice_number);


--
-- Name: patients uq_patient_tenant_patient_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT uq_patient_tenant_patient_id UNIQUE (tenant_id, patient_id);


--
-- Name: payments uq_payment_tenant_payment_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT uq_payment_tenant_payment_id UNIQUE (tenant_id, payment_id);


--
-- Name: prescriptions uq_prescription_tenant_rx_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT uq_prescription_tenant_rx_id UNIQUE (tenant_id, prescription_id);


--
-- Name: appointment_slots uq_slot_doctor_date_start_time; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointment_slots
    ADD CONSTRAINT uq_slot_doctor_date_start_time UNIQUE (doctor_id, date, start_time);


--
-- Name: appointment_slots uq_slot_tenant_slot_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointment_slots
    ADD CONSTRAINT uq_slot_tenant_slot_id UNIQUE (tenant_id, slot_id);


--
-- Name: users uq_user_tenant_username; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_user_tenant_username UNIQUE (tenant_id, username);


--
-- Name: ix_appointment_slots_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointment_slots_date ON public.appointment_slots USING btree (date);


--
-- Name: ix_appointment_slots_doctor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointment_slots_doctor_id ON public.appointment_slots USING btree (doctor_id);


--
-- Name: ix_appointment_slots_slot_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointment_slots_slot_id ON public.appointment_slots USING btree (slot_id);


--
-- Name: ix_appointment_slots_start_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointment_slots_start_time ON public.appointment_slots USING btree (start_time);


--
-- Name: ix_appointment_slots_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointment_slots_status ON public.appointment_slots USING btree (status);


--
-- Name: ix_appointment_slots_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointment_slots_tenant_id ON public.appointment_slots USING btree (tenant_id);


--
-- Name: ix_appointment_tenant_date_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointment_tenant_date_status ON public.appointments USING btree (tenant_id, appointment_date, booking_status);


--
-- Name: ix_appointments_appointment_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointments_appointment_date ON public.appointments USING btree (appointment_date);


--
-- Name: ix_appointments_booking_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointments_booking_status ON public.appointments USING btree (booking_status);


--
-- Name: ix_appointments_doctor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointments_doctor_id ON public.appointments USING btree (doctor_id);


--
-- Name: ix_appointments_patient_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointments_patient_id ON public.appointments USING btree (patient_id);


--
-- Name: ix_appointments_payment_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointments_payment_status ON public.appointments USING btree (payment_status);


--
-- Name: ix_appointments_slot_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointments_slot_id ON public.appointments USING btree (slot_id);


--
-- Name: ix_appointments_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointments_tenant_id ON public.appointments USING btree (tenant_id);


--
-- Name: ix_appointments_token_no; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appointments_token_no ON public.appointments USING btree (token_no);


--
-- Name: ix_audit_logs_action; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: ix_audit_logs_audit_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_audit_id ON public.audit_logs USING btree (audit_id);


--
-- Name: ix_audit_logs_entity_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_entity_id ON public.audit_logs USING btree (entity_id);


--
-- Name: ix_audit_logs_entity_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_entity_type ON public.audit_logs USING btree (entity_type);


--
-- Name: ix_audit_logs_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_tenant_id ON public.audit_logs USING btree (tenant_id);


--
-- Name: ix_audit_logs_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_timestamp ON public.audit_logs USING btree ("timestamp");


--
-- Name: ix_audit_logs_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_user ON public.audit_logs USING btree ("user");


--
-- Name: ix_audit_tenant_action; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_tenant_action ON public.audit_logs USING btree (tenant_id, action);


--
-- Name: ix_audit_tenant_entity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_tenant_entity ON public.audit_logs USING btree (tenant_id, entity_type, entity_id);


--
-- Name: ix_clinics_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_clinics_is_active ON public.clinics USING btree (is_active);


--
-- Name: ix_clinics_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_clinics_name ON public.clinics USING btree (name);


--
-- Name: ix_clinics_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_clinics_status ON public.clinics USING btree (status);


--
-- Name: ix_doctor_tenant_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_doctor_tenant_name ON public.doctors USING btree (tenant_id, name);


--
-- Name: ix_doctor_tenant_specialization; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_doctor_tenant_specialization ON public.doctors USING btree (tenant_id, specialization);


--
-- Name: ix_doctors_doctor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_doctors_doctor_id ON public.doctors USING btree (doctor_id);


--
-- Name: ix_doctors_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_doctors_name ON public.doctors USING btree (name);


--
-- Name: ix_doctors_specialization; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_doctors_specialization ON public.doctors USING btree (specialization);


--
-- Name: ix_doctors_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_doctors_status ON public.doctors USING btree (status);


--
-- Name: ix_doctors_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_doctors_tenant_id ON public.doctors USING btree (tenant_id);


--
-- Name: ix_invoice_tenant_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_invoice_tenant_status ON public.invoices USING btree (tenant_id, payment_status);


--
-- Name: ix_invoices_appointment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_invoices_appointment_id ON public.invoices USING btree (appointment_id);


--
-- Name: ix_invoices_invoice_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_invoices_invoice_number ON public.invoices USING btree (invoice_number);


--
-- Name: ix_invoices_patient_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_invoices_patient_id ON public.invoices USING btree (patient_id);


--
-- Name: ix_invoices_payment_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_invoices_payment_status ON public.invoices USING btree (payment_status);


--
-- Name: ix_invoices_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_invoices_tenant_id ON public.invoices USING btree (tenant_id);


--
-- Name: ix_patient_tenant_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_patient_tenant_name ON public.patients USING btree (tenant_id, name);


--
-- Name: ix_patient_tenant_phone; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_patient_tenant_phone ON public.patients USING btree (tenant_id, phone);


--
-- Name: ix_patients_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_patients_email ON public.patients USING btree (email);


--
-- Name: ix_patients_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_patients_name ON public.patients USING btree (name);


--
-- Name: ix_patients_patient_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_patients_patient_id ON public.patients USING btree (patient_id);


--
-- Name: ix_patients_phone; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_patients_phone ON public.patients USING btree (phone);


--
-- Name: ix_patients_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_patients_tenant_id ON public.patients USING btree (tenant_id);


--
-- Name: ix_payment_tenant_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payment_tenant_status ON public.payments USING btree (tenant_id, payment_status);


--
-- Name: ix_payments_appointment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payments_appointment_id ON public.payments USING btree (appointment_id);


--
-- Name: ix_payments_invoice_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payments_invoice_id ON public.payments USING btree (invoice_id);


--
-- Name: ix_payments_payment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payments_payment_id ON public.payments USING btree (payment_id);


--
-- Name: ix_payments_payment_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payments_payment_status ON public.payments USING btree (payment_status);


--
-- Name: ix_payments_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payments_tenant_id ON public.payments USING btree (tenant_id);


--
-- Name: ix_payments_transaction_reference; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payments_transaction_reference ON public.payments USING btree (transaction_reference);


--
-- Name: ix_prescription_items_prescription_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_prescription_items_prescription_id ON public.prescription_items USING btree (prescription_id);


--
-- Name: ix_prescription_tenant_date_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_prescription_tenant_date_status ON public.prescriptions USING btree (tenant_id, date, status);


--
-- Name: ix_prescriptions_appointment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_prescriptions_appointment_id ON public.prescriptions USING btree (appointment_id);


--
-- Name: ix_prescriptions_doctor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_prescriptions_doctor_id ON public.prescriptions USING btree (doctor_id);


--
-- Name: ix_prescriptions_patient_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_prescriptions_patient_id ON public.prescriptions USING btree (patient_id);


--
-- Name: ix_prescriptions_prescription_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_prescriptions_prescription_id ON public.prescriptions USING btree (prescription_id);


--
-- Name: ix_prescriptions_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_prescriptions_status ON public.prescriptions USING btree (status);


--
-- Name: ix_prescriptions_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_prescriptions_tenant_id ON public.prescriptions USING btree (tenant_id);


--
-- Name: ix_slot_tenant_date_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_slot_tenant_date_status ON public.appointment_slots USING btree (tenant_id, date, status);


--
-- Name: ix_user_tenant_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_tenant_role ON public.users USING btree (tenant_id, role);


--
-- Name: ix_users_doctor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_doctor_id ON public.users USING btree (doctor_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- Name: ix_users_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_status ON public.users USING btree (status);


--
-- Name: ix_users_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_tenant_id ON public.users USING btree (tenant_id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: appointment_slots fk_appointment_slots_doctor_id_doctors; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointment_slots
    ADD CONSTRAINT fk_appointment_slots_doctor_id_doctors FOREIGN KEY (doctor_id) REFERENCES public.doctors(id) ON DELETE CASCADE;


--
-- Name: appointment_slots fk_appointment_slots_tenant_id_clinics; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointment_slots
    ADD CONSTRAINT fk_appointment_slots_tenant_id_clinics FOREIGN KEY (tenant_id) REFERENCES public.clinics(id) ON DELETE CASCADE;


--
-- Name: appointments fk_appointments_doctor_id_doctors; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT fk_appointments_doctor_id_doctors FOREIGN KEY (doctor_id) REFERENCES public.doctors(id) ON DELETE CASCADE;


--
-- Name: appointments fk_appointments_patient_id_patients; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT fk_appointments_patient_id_patients FOREIGN KEY (patient_id) REFERENCES public.patients(id) ON DELETE CASCADE;


--
-- Name: appointments fk_appointments_slot_id_appointment_slots; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT fk_appointments_slot_id_appointment_slots FOREIGN KEY (slot_id) REFERENCES public.appointment_slots(id) ON DELETE SET NULL;


--
-- Name: appointments fk_appointments_tenant_id_clinics; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT fk_appointments_tenant_id_clinics FOREIGN KEY (tenant_id) REFERENCES public.clinics(id) ON DELETE CASCADE;


--
-- Name: audit_logs fk_audit_logs_tenant_id_clinics; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT fk_audit_logs_tenant_id_clinics FOREIGN KEY (tenant_id) REFERENCES public.clinics(id) ON DELETE CASCADE;


--
-- Name: doctors fk_doctors_tenant_id_clinics; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT fk_doctors_tenant_id_clinics FOREIGN KEY (tenant_id) REFERENCES public.clinics(id) ON DELETE CASCADE;


--
-- Name: invoices fk_invoices_appointment_id_appointments; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT fk_invoices_appointment_id_appointments FOREIGN KEY (appointment_id) REFERENCES public.appointments(id) ON DELETE SET NULL;


--
-- Name: invoices fk_invoices_patient_id_patients; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT fk_invoices_patient_id_patients FOREIGN KEY (patient_id) REFERENCES public.patients(id) ON DELETE CASCADE;


--
-- Name: invoices fk_invoices_tenant_id_clinics; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT fk_invoices_tenant_id_clinics FOREIGN KEY (tenant_id) REFERENCES public.clinics(id) ON DELETE CASCADE;


--
-- Name: patients fk_patients_tenant_id_clinics; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT fk_patients_tenant_id_clinics FOREIGN KEY (tenant_id) REFERENCES public.clinics(id) ON DELETE CASCADE;


--
-- Name: payments fk_payments_appointment_id_appointments; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_payments_appointment_id_appointments FOREIGN KEY (appointment_id) REFERENCES public.appointments(id) ON DELETE SET NULL;


--
-- Name: payments fk_payments_invoice_id_invoices; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_payments_invoice_id_invoices FOREIGN KEY (invoice_id) REFERENCES public.invoices(id) ON DELETE SET NULL;


--
-- Name: payments fk_payments_tenant_id_clinics; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_payments_tenant_id_clinics FOREIGN KEY (tenant_id) REFERENCES public.clinics(id) ON DELETE CASCADE;


--
-- Name: prescription_items fk_prescription_items_prescription_id_prescriptions; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescription_items
    ADD CONSTRAINT fk_prescription_items_prescription_id_prescriptions FOREIGN KEY (prescription_id) REFERENCES public.prescriptions(id) ON DELETE CASCADE;


--
-- Name: prescriptions fk_prescriptions_appointment_id_appointments; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT fk_prescriptions_appointment_id_appointments FOREIGN KEY (appointment_id) REFERENCES public.appointments(id) ON DELETE SET NULL;


--
-- Name: prescriptions fk_prescriptions_doctor_id_doctors; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT fk_prescriptions_doctor_id_doctors FOREIGN KEY (doctor_id) REFERENCES public.doctors(id) ON DELETE CASCADE;


--
-- Name: prescriptions fk_prescriptions_patient_id_patients; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT fk_prescriptions_patient_id_patients FOREIGN KEY (patient_id) REFERENCES public.patients(id) ON DELETE CASCADE;


--
-- Name: prescriptions fk_prescriptions_tenant_id_clinics; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT fk_prescriptions_tenant_id_clinics FOREIGN KEY (tenant_id) REFERENCES public.clinics(id) ON DELETE CASCADE;


--
-- Name: users fk_users_tenant_id_clinics; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_tenant_id_clinics FOREIGN KEY (tenant_id) REFERENCES public.clinics(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict QGgvjgK4YpOiuX7d7yZbTYMWQTWWiTLgeXvQ9eZno2sQ4aqSVXhmXrKEx95aUPO

