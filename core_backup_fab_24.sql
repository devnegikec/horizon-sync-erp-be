--
-- PostgreSQL database dump
--

\restrict 4XRh2NaB6witPPdzi8D2sp1OtK8TRDAEoo8hOhAek03bbqrVuPnUgjkJRBxBkqs

-- Dumped from database version 15.16
-- Dumped by pg_dump version 15.16

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: accountstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.accountstatus AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'ARCHIVED'
);


ALTER TYPE public.accountstatus OWNER TO horizon_user;

--
-- Name: accounttype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.accounttype AS ENUM (
    'asset',
    'liability',
    'equity',
    'income',
    'expense'
);


ALTER TYPE public.accounttype OWNER TO horizon_user;

--
-- Name: batchstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.batchstatus AS ENUM (
    'active',
    'expired',
    'consumed'
);


ALTER TYPE public.batchstatus OWNER TO horizon_user;

--
-- Name: communicationchannel; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.communicationchannel AS ENUM (
    'email',
    'whatsapp',
    'sms',
    'webhook'
);


ALTER TYPE public.communicationchannel OWNER TO horizon_user;

--
-- Name: communicationdoctype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.communicationdoctype AS ENUM (
    'quotation',
    'sales_order',
    'purchase_order',
    'invoice',
    'delivery_note',
    'purchase_receipt',
    'payment',
    'rfq',
    'material_request'
);


ALTER TYPE public.communicationdoctype OWNER TO horizon_user;

--
-- Name: communicationstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.communicationstatus AS ENUM (
    'pending',
    'sent',
    'delivered',
    'failed',
    'bounced'
);


ALTER TYPE public.communicationstatus OWNER TO horizon_user;

--
-- Name: customerstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.customerstatus AS ENUM (
    'active',
    'inactive',
    'blocked'
);


ALTER TYPE public.customerstatus OWNER TO horizon_user;

--
-- Name: documentstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.documentstatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);


ALTER TYPE public.documentstatus OWNER TO horizon_user;

--
-- Name: inspectionstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.inspectionstatus AS ENUM (
    'pending',
    'accepted',
    'rejected'
);


ALTER TYPE public.inspectionstatus OWNER TO horizon_user;

--
-- Name: inspectiontype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.inspectiontype AS ENUM (
    'incoming',
    'outgoing',
    'in_process'
);


ALTER TYPE public.inspectiontype OWNER TO horizon_user;

--
-- Name: invoicestatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.invoicestatus AS ENUM (
    'draft',
    'pending',
    'paid',
    'partial',
    'overdue',
    'cancelled'
);


ALTER TYPE public.invoicestatus OWNER TO horizon_user;

--
-- Name: invoicetype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.invoicetype AS ENUM (
    'sales',
    'purchase'
);


ALTER TYPE public.invoicetype OWNER TO horizon_user;

--
-- Name: itemstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.itemstatus AS ENUM (
    'active',
    'inactive',
    'discontinued'
);


ALTER TYPE public.itemstatus OWNER TO horizon_user;

--
-- Name: itemtype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.itemtype AS ENUM (
    'stock',
    'non_stock',
    'service',
    'fixed_asset'
);


ALTER TYPE public.itemtype OWNER TO horizon_user;

--
-- Name: journalstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.journalstatus AS ENUM (
    'draft',
    'posted',
    'cancelled'
);


ALTER TYPE public.journalstatus OWNER TO horizon_user;

--
-- Name: materialrequestpriority; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.materialrequestpriority AS ENUM (
    'low',
    'medium',
    'high',
    'urgent'
);


ALTER TYPE public.materialrequestpriority OWNER TO horizon_user;

--
-- Name: materialrequeststatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.materialrequeststatus AS ENUM (
    'draft',
    'submitted',
    'partially_quoted',
    'fully_quoted',
    'cancelled'
);


ALTER TYPE public.materialrequeststatus OWNER TO horizon_user;

--
-- Name: materialrequesttype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.materialrequesttype AS ENUM (
    'purchase',
    'transfer',
    'issue'
);


ALTER TYPE public.materialrequesttype OWNER TO horizon_user;

--
-- Name: movementtype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.movementtype AS ENUM (
    'in',
    'out',
    'transfer',
    'adjustment'
);


ALTER TYPE public.movementtype OWNER TO horizon_user;

--
-- Name: organizationstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.organizationstatus AS ENUM (
    'active',
    'inactive',
    'suspended'
);


ALTER TYPE public.organizationstatus OWNER TO horizon_user;

--
-- Name: organizationtype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.organizationtype AS ENUM (
    'business',
    'individual',
    'non_profit'
);


ALTER TYPE public.organizationtype OWNER TO horizon_user;

--
-- Name: paymentmethod; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.paymentmethod AS ENUM (
    'cash',
    'bank_transfer',
    'credit_card',
    'debit_card',
    'cheque',
    'upi',
    'other'
);


ALTER TYPE public.paymentmethod OWNER TO horizon_user;

--
-- Name: paymentstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.paymentstatus AS ENUM (
    'pending',
    'completed',
    'failed',
    'cancelled'
);


ALTER TYPE public.paymentstatus OWNER TO horizon_user;

--
-- Name: paymenttype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.paymenttype AS ENUM (
    'receive',
    'pay'
);


ALTER TYPE public.paymenttype OWNER TO horizon_user;

--
-- Name: pickliststatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.pickliststatus AS ENUM (
    'draft',
    'in_progress',
    'completed',
    'cancelled'
);


ALTER TYPE public.pickliststatus OWNER TO horizon_user;

--
-- Name: purchaseorderstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.purchaseorderstatus AS ENUM (
    'draft',
    'submitted',
    'partially_received',
    'fully_received',
    'closed',
    'cancelled'
);


ALTER TYPE public.purchaseorderstatus OWNER TO horizon_user;

--
-- Name: quotationstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.quotationstatus AS ENUM (
    'draft',
    'sent',
    'accepted',
    'rejected',
    'expired'
);


ALTER TYPE public.quotationstatus OWNER TO horizon_user;

--
-- Name: readingtype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.readingtype AS ENUM (
    'numeric',
    'text',
    'pass_fail'
);


ALTER TYPE public.readingtype OWNER TO horizon_user;

--
-- Name: recipienttype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.recipienttype AS ENUM (
    'customer',
    'supplier',
    'employee',
    'other'
);


ALTER TYPE public.recipienttype OWNER TO horizon_user;

--
-- Name: rfqstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.rfqstatus AS ENUM (
    'draft',
    'sent',
    'partially_responded',
    'fully_responded',
    'closed'
);


ALTER TYPE public.rfqstatus OWNER TO horizon_user;

--
-- Name: salesorderstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.salesorderstatus AS ENUM (
    'draft',
    'confirmed',
    'partially_delivered',
    'delivered',
    'closed',
    'cancelled'
);


ALTER TYPE public.salesorderstatus OWNER TO horizon_user;

--
-- Name: stockentrystatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.stockentrystatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);


ALTER TYPE public.stockentrystatus OWNER TO horizon_user;

--
-- Name: stockentrytype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.stockentrytype AS ENUM (
    'material_receipt',
    'material_issue',
    'material_transfer',
    'manufacture',
    'repack',
    'send_to_subcontractor'
);


ALTER TYPE public.stockentrytype OWNER TO horizon_user;

--
-- Name: supplierstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.supplierstatus AS ENUM (
    'active',
    'inactive',
    'blocked'
);


ALTER TYPE public.supplierstatus OWNER TO horizon_user;

--
-- Name: valuationmethod; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.valuationmethod AS ENUM (
    'fifo',
    'lifo',
    'moving_average',
    'standard'
);


ALTER TYPE public.valuationmethod OWNER TO horizon_user;

--
-- Name: warehousetype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.warehousetype AS ENUM (
    'warehouse',
    'store',
    'virtual',
    'transit'
);


ALTER TYPE public.warehousetype OWNER TO horizon_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account_audit_log; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.account_audit_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    account_id uuid NOT NULL,
    action character varying(20) NOT NULL,
    user_id character varying(100) NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    changes jsonb NOT NULL,
    audit_metadata jsonb,
    CONSTRAINT valid_action CHECK (((action)::text = ANY ((ARRAY['CREATE'::character varying, 'UPDATE'::character varying, 'DELETE'::character varying, 'STATUS_CHANGE'::character varying])::text[])))
);


ALTER TABLE public.account_audit_log OWNER TO horizon_user;

--
-- Name: account_balances; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.account_balances (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    account_id uuid NOT NULL,
    currency character varying(3) NOT NULL,
    debit_total numeric(19,4) DEFAULT '0'::numeric NOT NULL,
    credit_total numeric(19,4) DEFAULT '0'::numeric NOT NULL,
    balance numeric(19,4) DEFAULT '0'::numeric NOT NULL,
    base_currency_balance numeric(19,4) DEFAULT '0'::numeric NOT NULL,
    as_of_date date NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.account_balances OWNER TO horizon_user;

--
-- Name: accounts; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.accounts (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    account_code character varying(50) NOT NULL,
    account_name character varying(200) NOT NULL,
    account_type public.accounttype NOT NULL,
    parent_account_id uuid,
    currency character varying(3) DEFAULT 'USD'::character varying NOT NULL,
    status public.accountstatus DEFAULT 'ACTIVE'::public.accountstatus NOT NULL,
    is_posting_account boolean DEFAULT true NOT NULL,
    description text,
    created_by character varying(100) NOT NULL,
    updated_by character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.accounts OWNER TO horizon_user;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO horizon_user;

--
-- Name: batches; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.batches (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    batch_no character varying(100) NOT NULL,
    item_id uuid NOT NULL,
    manufacturing_date timestamp with time zone,
    expiry_date timestamp with time zone,
    supplier_id uuid,
    supplier_batch_no character varying(100),
    status public.batchstatus,
    reference_type character varying(50),
    reference_id uuid,
    description text,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.batches OWNER TO horizon_user;

--
-- Name: charge_templates; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.charge_templates (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    template_code character varying(100) NOT NULL,
    template_name character varying(255) NOT NULL,
    description text,
    charge_type character varying(50) NOT NULL,
    calculation_method character varying(20) NOT NULL,
    fixed_amount numeric(15,2),
    percentage_rate numeric(5,2),
    base_on character varying(20),
    account_head_id uuid NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    applicability_rules jsonb,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp with time zone
);


ALTER TABLE public.charge_templates OWNER TO horizon_user;

--
-- Name: chart_of_accounts; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.chart_of_accounts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    account_code character varying(50) NOT NULL,
    account_name character varying(255) NOT NULL,
    account_type public.accounttype NOT NULL,
    parent_account_id uuid,
    level integer DEFAULT 1,
    is_group boolean DEFAULT false,
    opening_balance numeric(15,2) DEFAULT 0,
    current_balance numeric(15,2) DEFAULT 0,
    is_active boolean DEFAULT true,
    tags jsonb,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamp with time zone
);


ALTER TABLE public.chart_of_accounts OWNER TO horizon_user;

--
-- Name: communication_logs; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.communication_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    doc_type public.communicationdoctype NOT NULL,
    doc_id uuid NOT NULL,
    doc_no character varying(100),
    version integer DEFAULT 1 NOT NULL,
    channel public.communicationchannel NOT NULL,
    recipient_type public.recipienttype,
    recipient character varying(255) NOT NULL,
    recipient_name character varying(255),
    sender_id uuid NOT NULL,
    sender_name character varying(255),
    sender_email character varying(255),
    subject character varying(500),
    message text,
    status public.communicationstatus DEFAULT 'pending'::public.communicationstatus NOT NULL,
    sent_at timestamp with time zone,
    delivered_at timestamp with time zone,
    failed_at timestamp with time zone,
    error_message text,
    extra_data json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.communication_logs OWNER TO horizon_user;

--
-- Name: customers; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.customers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    customer_name character varying(255) NOT NULL,
    customer_code character varying(50) NOT NULL,
    email character varying(255),
    phone character varying(50),
    address text,
    address_line1 character varying(255),
    address_line2 character varying(255),
    city character varying(100),
    state character varying(100),
    postal_code character varying(20),
    country character varying(100),
    tax_number character varying(50),
    status public.customerstatus DEFAULT 'active'::public.customerstatus,
    credit_limit numeric(15,2) DEFAULT 0,
    outstanding_balance numeric(15,2) DEFAULT 0,
    tags jsonb,
    custom_fields jsonb,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamp with time zone,
    is_tax_exempt boolean DEFAULT false NOT NULL,
    tax_exemption_certificate_no character varying(100)
);


ALTER TABLE public.customers OWNER TO horizon_user;

--
-- Name: default_accounts; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.default_accounts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    transaction_type character varying(100) NOT NULL,
    scenario character varying(100),
    account_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.default_accounts OWNER TO horizon_user;

--
-- Name: delivery_note_items; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.delivery_note_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    delivery_note_id uuid NOT NULL,
    item_id uuid NOT NULL,
    qty numeric(15,3) NOT NULL,
    uom character varying(50) NOT NULL,
    rate numeric(15,2),
    amount numeric(15,2),
    warehouse_id uuid,
    batch_no character varying(100),
    serial_nos jsonb,
    sort_order integer DEFAULT 0,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.delivery_note_items OWNER TO horizon_user;

--
-- Name: delivery_notes; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.delivery_notes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    delivery_note_no character varying(100) NOT NULL,
    customer_id uuid NOT NULL,
    delivery_date timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status public.documentstatus DEFAULT 'draft'::public.documentstatus NOT NULL,
    warehouse_id uuid,
    pick_list_id uuid,
    reference_type character varying(50),
    reference_id uuid,
    remarks text,
    submitted_at timestamp with time zone,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.delivery_notes OWNER TO horizon_user;

--
-- Name: document_numbering_config; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.document_numbering_config (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    document_type character varying(50) NOT NULL,
    prefix character varying(20) NOT NULL,
    padding integer DEFAULT 5 NOT NULL,
    include_year boolean DEFAULT true NOT NULL,
    separator character varying(5) DEFAULT '-'::character varying NOT NULL
);


ALTER TABLE public.document_numbering_config OWNER TO horizon_user;

--
-- Name: document_sequence_counter; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.document_sequence_counter (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    document_type character varying(50) NOT NULL,
    sequence_year integer,
    next_number integer DEFAULT 1 NOT NULL
);


ALTER TABLE public.document_sequence_counter OWNER TO horizon_user;

--
-- Name: exchange_rates; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.exchange_rates (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    from_currency character varying(3) NOT NULL,
    to_currency character varying(3) NOT NULL,
    rate numeric(19,6) NOT NULL,
    effective_date date NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_exchange_rate_positive CHECK ((rate > (0)::numeric))
);


ALTER TABLE public.exchange_rates OWNER TO horizon_user;

--
-- Name: invoice_items; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.invoice_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    invoice_id uuid NOT NULL,
    item_id uuid,
    item_code character varying(100),
    item_name character varying(255),
    qty numeric(15,3) NOT NULL,
    uom character varying(50) NOT NULL,
    rate numeric(15,2),
    amount numeric(15,2),
    sort_order integer DEFAULT 0,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.invoice_items OWNER TO horizon_user;

--
-- Name: invoices; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.invoices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    invoice_no character varying(100) NOT NULL,
    invoice_type public.invoicetype NOT NULL,
    party_id uuid NOT NULL,
    party_type character varying(20) NOT NULL,
    posting_date timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    due_date timestamp with time zone,
    status public.invoicestatus DEFAULT 'draft'::public.invoicestatus NOT NULL,
    grand_total numeric(15,2) DEFAULT 0,
    outstanding_amount numeric(15,2) DEFAULT 0,
    currency character varying(10) DEFAULT 'INR'::character varying,
    reference_type character varying(50),
    reference_id uuid,
    remarks text,
    submitted_at timestamp with time zone,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    net_total numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    total_tax numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    total_charges numeric(15,2) DEFAULT '0'::numeric NOT NULL
);


ALTER TABLE public.invoices OWNER TO horizon_user;

--
-- Name: item_groups; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.item_groups (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    code character varying(50) NOT NULL,
    description text,
    parent_id uuid,
    default_valuation_method public.valuationmethod,
    default_uom character varying(50),
    is_active boolean DEFAULT true,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamp with time zone,
    sales_tax_template_id uuid,
    purchase_tax_template_id uuid
);


ALTER TABLE public.item_groups OWNER TO horizon_user;

--
-- Name: item_prices; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.item_prices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    item_id uuid NOT NULL,
    price_list_id uuid,
    price numeric(15,2),
    currency character varying(10),
    valid_from timestamp with time zone,
    valid_upto timestamp with time zone,
    min_qty integer,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.item_prices OWNER TO horizon_user;

--
-- Name: item_suppliers; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.item_suppliers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    item_id uuid NOT NULL,
    supplier_id uuid NOT NULL,
    supplier_part_no character varying(100),
    lead_time_days integer,
    is_default boolean,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.item_suppliers OWNER TO horizon_user;

--
-- Name: items; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.items (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    item_code character varying(100) NOT NULL,
    item_name character varying(255) NOT NULL,
    description text,
    item_group_id uuid,
    uom character varying(50),
    maintain_stock boolean,
    allow_negative_stock boolean,
    has_variants boolean,
    variant_of uuid,
    variant_attributes jsonb,
    has_batch_no boolean,
    has_serial_no boolean,
    batch_number_series character varying(100),
    serial_number_series character varying(100),
    standard_rate numeric(15,2),
    valuation_rate numeric(15,2),
    enable_auto_reorder boolean,
    reorder_level integer,
    reorder_qty integer,
    min_order_qty integer,
    max_order_qty integer,
    weight_per_unit numeric(10,3),
    weight_uom character varying(50),
    inspection_required_before_purchase boolean,
    inspection_required_before_delivery boolean,
    quality_inspection_template uuid,
    barcode character varying(100),
    image_url character varying(500),
    images jsonb,
    tags jsonb,
    custom_fields jsonb,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    deleted_at timestamp with time zone,
    item_type public.itemtype DEFAULT 'stock'::public.itemtype,
    valuation_method public.valuationmethod DEFAULT 'fifo'::public.valuationmethod,
    status public.itemstatus DEFAULT 'active'::public.itemstatus,
    sales_tax_template_id uuid,
    purchase_tax_template_id uuid
);


ALTER TABLE public.items OWNER TO horizon_user;

--
-- Name: journal_entries; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.journal_entries (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    entry_no character varying(100) NOT NULL,
    posting_date timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status public.journalstatus DEFAULT 'draft'::public.journalstatus NOT NULL,
    voucher_type character varying(50),
    reference_type character varying(50),
    reference_id uuid,
    total_debit numeric(15,2) DEFAULT 0,
    total_credit numeric(15,2) DEFAULT 0,
    remarks text,
    posted_at timestamp with time zone,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.journal_entries OWNER TO horizon_user;

--
-- Name: journal_entry_lines; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.journal_entry_lines (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    journal_entry_id uuid NOT NULL,
    account_id uuid NOT NULL,
    debit numeric(15,2) DEFAULT 0,
    credit numeric(15,2) DEFAULT 0,
    against_account_id uuid,
    reference_type character varying(50),
    reference_id uuid,
    remarks text,
    sort_order integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.journal_entry_lines OWNER TO horizon_user;

--
-- Name: landed_cost_items; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.landed_cost_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    landed_cost_voucher_id uuid NOT NULL,
    purchase_receipt_id uuid,
    purchase_receipt_item_id uuid,
    item_id uuid NOT NULL,
    qty numeric(15,3) NOT NULL,
    amount numeric(15,2) NOT NULL,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.landed_cost_items OWNER TO horizon_user;

--
-- Name: landed_cost_purchase_receipts; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.landed_cost_purchase_receipts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    landed_cost_voucher_id uuid NOT NULL,
    purchase_receipt_id uuid NOT NULL,
    amount numeric(15,2) DEFAULT 0,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.landed_cost_purchase_receipts OWNER TO horizon_user;

--
-- Name: landed_cost_taxes_and_charges; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.landed_cost_taxes_and_charges (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    landed_cost_voucher_id uuid NOT NULL,
    description character varying(255),
    amount numeric(15,2) DEFAULT 0 NOT NULL,
    account_id uuid,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.landed_cost_taxes_and_charges OWNER TO horizon_user;

--
-- Name: landed_cost_vouchers; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.landed_cost_vouchers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    voucher_no character varying(100) NOT NULL,
    posting_date timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status public.documentstatus DEFAULT 'draft'::public.documentstatus NOT NULL,
    remarks text,
    submitted_at timestamp with time zone,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.landed_cost_vouchers OWNER TO horizon_user;

--
-- Name: material_request_lines; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.material_request_lines (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    material_request_id uuid NOT NULL,
    item_id uuid NOT NULL,
    quantity numeric(15,4) NOT NULL,
    required_date date NOT NULL,
    description text,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    uom character varying(50),
    estimated_unit_cost numeric(15,4),
    requested_for character varying(255),
    requested_for_department character varying(100),
    CONSTRAINT material_request_lines_quantity_check CHECK ((quantity > (0)::numeric))
);


ALTER TABLE public.material_request_lines OWNER TO horizon_user;

--
-- Name: material_requests; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.material_requests (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    status public.materialrequeststatus DEFAULT 'draft'::public.materialrequeststatus NOT NULL,
    notes text,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp with time zone,
    request_no character varying(50),
    type public.materialrequesttype DEFAULT 'purchase'::public.materialrequesttype NOT NULL,
    priority public.materialrequestpriority DEFAULT 'medium'::public.materialrequestpriority NOT NULL,
    target_warehouse_id uuid,
    requested_by uuid,
    department character varying(100)
);


ALTER TABLE public.material_requests OWNER TO horizon_user;

--
-- Name: organization_settings; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.organization_settings (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    default_sales_tax_template_id uuid,
    default_purchase_tax_template_id uuid,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.organization_settings OWNER TO horizon_user;

--
-- Name: payment_allocations; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.payment_allocations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    payment_id uuid NOT NULL,
    invoice_id uuid NOT NULL,
    allocated_amount numeric(15,2) NOT NULL,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.payment_allocations OWNER TO horizon_user;

--
-- Name: payments; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.payments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    payment_no character varying(100) NOT NULL,
    payment_type public.paymenttype NOT NULL,
    party_id uuid NOT NULL,
    party_type character varying(20) NOT NULL,
    posting_date timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    amount numeric(15,2) NOT NULL,
    status public.paymentstatus DEFAULT 'pending'::public.paymentstatus NOT NULL,
    payment_method public.paymentmethod,
    reference_no character varying(100),
    remarks text,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.payments OWNER TO horizon_user;

--
-- Name: pick_list_items; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.pick_list_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    pick_list_id uuid NOT NULL,
    item_id uuid NOT NULL,
    warehouse_id uuid NOT NULL,
    qty numeric(15,3) NOT NULL,
    picked_qty numeric(15,3) DEFAULT 0,
    uom character varying(50) NOT NULL,
    batch_no character varying(100),
    serial_nos jsonb,
    sort_order integer DEFAULT 0,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.pick_list_items OWNER TO horizon_user;

--
-- Name: pick_lists; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.pick_lists (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    pick_list_no character varying(100) NOT NULL,
    warehouse_id uuid NOT NULL,
    status public.pickliststatus DEFAULT 'draft'::public.pickliststatus NOT NULL,
    pick_date timestamp with time zone,
    reference_type character varying(50),
    reference_id uuid,
    remarks text,
    completed_at timestamp with time zone,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.pick_lists OWNER TO horizon_user;

--
-- Name: purchase_order_lines; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.purchase_order_lines (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    purchase_order_id uuid NOT NULL,
    item_id uuid NOT NULL,
    quantity numeric(15,4) NOT NULL,
    unit_price numeric(15,2) NOT NULL,
    line_total numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    received_quantity numeric(15,4) DEFAULT '0'::numeric NOT NULL,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT purchase_order_lines_quantity_check CHECK ((quantity > (0)::numeric)),
    CONSTRAINT purchase_order_lines_received_quantity_check CHECK ((received_quantity >= (0)::numeric)),
    CONSTRAINT purchase_order_lines_received_quantity_limit_check CHECK ((received_quantity <= quantity)),
    CONSTRAINT purchase_order_lines_unit_price_check CHECK ((unit_price >= (0)::numeric))
);


ALTER TABLE public.purchase_order_lines OWNER TO horizon_user;

--
-- Name: purchase_orders; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.purchase_orders (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    rfq_id uuid,
    reference_type character varying(50),
    reference_id uuid,
    party_type character varying(50) DEFAULT 'SUPPLIER'::character varying NOT NULL,
    party_id uuid NOT NULL,
    status public.purchaseorderstatus DEFAULT 'draft'::public.purchaseorderstatus NOT NULL,
    subtotal numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    tax_amount numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    tax_rate numeric(5,4),
    discount_amount numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    grand_total numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp with time zone,
    net_total numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    total_tax numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    total_charges numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    CONSTRAINT purchase_orders_party_type_check CHECK (((party_type)::text = 'SUPPLIER'::text)),
    CONSTRAINT purchase_orders_reference_type_check CHECK (((reference_type IS NULL) OR ((reference_type)::text = 'RFQ'::text)))
);


ALTER TABLE public.purchase_orders OWNER TO horizon_user;

--
-- Name: purchase_receipt_items; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.purchase_receipt_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    purchase_receipt_id uuid NOT NULL,
    item_id uuid NOT NULL,
    qty numeric(15,3) NOT NULL,
    uom character varying(50) NOT NULL,
    rate numeric(15,2),
    amount numeric(15,2),
    warehouse_id uuid,
    batch_no character varying(100),
    serial_nos jsonb,
    sort_order integer DEFAULT 0,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.purchase_receipt_items OWNER TO horizon_user;

--
-- Name: purchase_receipts; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.purchase_receipts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    purchase_receipt_no character varying(100) NOT NULL,
    supplier_id uuid NOT NULL,
    receipt_date timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status public.documentstatus DEFAULT 'draft'::public.documentstatus NOT NULL,
    warehouse_id uuid,
    reference_type character varying(50),
    reference_id uuid,
    remarks text,
    submitted_at timestamp with time zone,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.purchase_receipts OWNER TO horizon_user;

--
-- Name: put_away_rules; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.put_away_rules (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    item_id uuid,
    item_group_id uuid,
    warehouse_id uuid NOT NULL,
    capacity integer,
    priority integer,
    min_qty integer,
    max_qty integer,
    is_active boolean,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.put_away_rules OWNER TO horizon_user;

--
-- Name: quotation_items; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.quotation_items (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    quotation_id uuid NOT NULL,
    item_id uuid NOT NULL,
    qty numeric(15,3) NOT NULL,
    uom character varying(50) NOT NULL,
    rate numeric(15,2) NOT NULL,
    amount numeric(15,2) NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    tax_template_id uuid,
    tax_rate numeric(5,2) DEFAULT '0'::numeric,
    tax_amount numeric(15,2) DEFAULT '0'::numeric,
    total_amount numeric(15,2) DEFAULT 0 NOT NULL
);


ALTER TABLE public.quotation_items OWNER TO horizon_user;

--
-- Name: quotations; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.quotations (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    quotation_no character varying(100) NOT NULL,
    customer_id uuid NOT NULL,
    quotation_date timestamp with time zone NOT NULL,
    valid_until timestamp with time zone,
    status public.quotationstatus DEFAULT 'draft'::public.quotationstatus NOT NULL,
    grand_total numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    currency character varying(10) DEFAULT 'INR'::character varying NOT NULL,
    remarks text,
    submitted_at timestamp with time zone,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    net_total numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    total_tax numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    total_charges numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    converted_to_sales_order boolean DEFAULT false NOT NULL
);


ALTER TABLE public.quotations OWNER TO horizon_user;

--
-- Name: receipt_seq_2025; Type: SEQUENCE; Schema: public; Owner: horizon_user
--

CREATE SEQUENCE public.receipt_seq_2025
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.receipt_seq_2025 OWNER TO horizon_user;

--
-- Name: receipt_seq_2026; Type: SEQUENCE; Schema: public; Owner: horizon_user
--

CREATE SEQUENCE public.receipt_seq_2026
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.receipt_seq_2026 OWNER TO horizon_user;

--
-- Name: rfq_lines; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.rfq_lines (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    rfq_id uuid NOT NULL,
    item_id uuid NOT NULL,
    quantity numeric(15,4) NOT NULL,
    required_date date NOT NULL,
    description text,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT rfq_lines_quantity_check CHECK ((quantity > (0)::numeric))
);


ALTER TABLE public.rfq_lines OWNER TO horizon_user;

--
-- Name: rfq_suppliers; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.rfq_suppliers (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    rfq_id uuid NOT NULL,
    supplier_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.rfq_suppliers OWNER TO horizon_user;

--
-- Name: rfqs; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.rfqs (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    material_request_id uuid,
    reference_type character varying(50),
    reference_id uuid,
    status public.rfqstatus DEFAULT 'draft'::public.rfqstatus NOT NULL,
    closing_date date NOT NULL,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT rfqs_reference_type_check CHECK (((reference_type IS NULL) OR ((reference_type)::text = 'MATERIAL_REQUEST'::text)))
);


ALTER TABLE public.rfqs OWNER TO horizon_user;

--
-- Name: sales_order_items; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.sales_order_items (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    sales_order_id uuid NOT NULL,
    item_id uuid NOT NULL,
    qty numeric(15,3) NOT NULL,
    uom character varying(50) NOT NULL,
    rate numeric(15,2) NOT NULL,
    amount numeric(15,2) NOT NULL,
    billed_qty numeric(15,3) DEFAULT '0'::numeric NOT NULL,
    delivered_qty numeric(15,3) DEFAULT '0'::numeric NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    tax_template_id uuid,
    tax_rate numeric(5,2) DEFAULT '0'::numeric,
    tax_amount numeric(15,2) DEFAULT '0'::numeric,
    total_amount numeric(15,2) DEFAULT 0 NOT NULL
);


ALTER TABLE public.sales_order_items OWNER TO horizon_user;

--
-- Name: sales_orders; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.sales_orders (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    sales_order_no character varying(100) NOT NULL,
    customer_id uuid NOT NULL,
    order_date timestamp with time zone NOT NULL,
    delivery_date timestamp with time zone,
    status public.salesorderstatus DEFAULT 'draft'::public.salesorderstatus NOT NULL,
    grand_total numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    currency character varying(10) DEFAULT 'INR'::character varying NOT NULL,
    reference_type character varying(50),
    reference_id uuid,
    remarks text,
    submitted_at timestamp with time zone,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    net_total numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    total_tax numeric(15,2) DEFAULT '0'::numeric NOT NULL,
    total_charges numeric(15,2) DEFAULT '0'::numeric NOT NULL
);


ALTER TABLE public.sales_orders OWNER TO horizon_user;

--
-- Name: serial_no_history; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.serial_no_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    serial_no_id uuid NOT NULL,
    transaction_type character varying(50) NOT NULL,
    transaction_id uuid,
    from_warehouse_id uuid,
    to_warehouse_id uuid,
    transaction_date timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    remarks text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.serial_no_history OWNER TO horizon_user;

--
-- Name: serial_nos; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.serial_nos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    serial_no character varying(100) NOT NULL,
    item_id uuid NOT NULL,
    warehouse_id uuid NOT NULL,
    status character varying(50),
    purchase_date timestamp with time zone,
    purchase_rate numeric(15,2),
    supplier_id uuid,
    delivery_date timestamp with time zone,
    customer_id uuid,
    warranty_period integer,
    warranty_expiry_date timestamp with time zone,
    amc_expiry_date timestamp with time zone,
    batch_no character varying(100),
    description text,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.serial_nos OWNER TO horizon_user;

--
-- Name: status_transitions; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.status_transitions (
    id uuid NOT NULL,
    entity_type character varying(50) NOT NULL,
    entity_id uuid NOT NULL,
    previous_status character varying(50) NOT NULL,
    new_status character varying(50) NOT NULL,
    user_id uuid NOT NULL,
    transitioned_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.status_transitions OWNER TO horizon_user;

--
-- Name: stock_entries; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.stock_entries (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    stock_entry_no character varying(100) NOT NULL,
    stock_entry_type public.stockentrytype NOT NULL,
    from_warehouse_id uuid,
    to_warehouse_id uuid,
    posting_date timestamp with time zone NOT NULL,
    posting_time character varying(10),
    status public.stockentrystatus,
    reference_type character varying(50),
    reference_id uuid,
    remarks text,
    total_value numeric(15,2),
    expense_account_id uuid,
    cost_center_id uuid,
    is_backflush boolean,
    bom_id uuid,
    extra_data jsonb,
    submitted_at timestamp with time zone,
    cancelled_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    created_by uuid,
    updated_by uuid
);


ALTER TABLE public.stock_entries OWNER TO horizon_user;

--
-- Name: stock_entry_items; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.stock_entry_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    stock_entry_id uuid NOT NULL,
    item_id uuid NOT NULL,
    source_warehouse_id uuid,
    target_warehouse_id uuid,
    qty numeric(15,3) NOT NULL,
    uom character varying(50) NOT NULL,
    basic_rate numeric(15,2),
    basic_amount numeric(15,2),
    valuation_rate numeric(15,2),
    batch_no character varying(100),
    serial_nos jsonb,
    quality_inspection_id uuid,
    description text,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stock_entry_items OWNER TO horizon_user;

--
-- Name: stock_levels; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.stock_levels (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    product_id uuid NOT NULL,
    warehouse_id uuid NOT NULL,
    quantity_on_hand integer,
    quantity_reserved integer,
    quantity_available integer,
    last_counted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stock_levels OWNER TO horizon_user;

--
-- Name: stock_movements; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.stock_movements (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    product_id uuid NOT NULL,
    warehouse_id uuid NOT NULL,
    movement_type public.movementtype NOT NULL,
    quantity integer NOT NULL,
    unit_cost numeric(15,2),
    reference_type character varying(50),
    reference_id uuid,
    notes text,
    performed_by uuid,
    performed_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stock_movements OWNER TO horizon_user;

--
-- Name: stock_reconciliation_items; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.stock_reconciliation_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    reconciliation_id uuid NOT NULL,
    item_id uuid NOT NULL,
    warehouse_id uuid NOT NULL,
    current_qty numeric(15,3),
    qty numeric(15,3) NOT NULL,
    qty_difference numeric(15,3),
    current_valuation_rate numeric(15,2),
    valuation_rate numeric(15,2),
    batch_no character varying(100),
    serial_nos jsonb,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stock_reconciliation_items OWNER TO horizon_user;

--
-- Name: stock_reconciliations; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.stock_reconciliations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    reconciliation_no character varying(100) NOT NULL,
    purpose character varying(100),
    posting_date timestamp with time zone NOT NULL,
    posting_time character varying(10),
    status public.stockentrystatus,
    expense_account_id uuid,
    difference_account_id uuid,
    remarks text,
    extra_data jsonb,
    submitted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    created_by uuid,
    updated_by uuid
);


ALTER TABLE public.stock_reconciliations OWNER TO horizon_user;

--
-- Name: stock_settings; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.stock_settings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    item_naming_by character varying(50),
    item_naming_series character varying(100),
    stock_entry_naming_series character varying(100),
    delivery_note_naming_series character varying(100),
    purchase_receipt_naming_series character varying(100),
    default_warehouse_id uuid,
    allow_negative_stock boolean,
    over_delivery_receipt_allowance numeric(5,2),
    over_billing_allowance numeric(5,2),
    auto_indent boolean,
    auto_indent_notification jsonb,
    default_valuation_method character varying(50),
    auto_create_serial_no boolean,
    default_quality_inspection_template_id uuid,
    stock_frozen_upto character varying(50),
    stock_frozen_upto_days integer,
    show_barcode_field boolean,
    convert_item_desc_to_transaction_desc boolean,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.stock_settings OWNER TO horizon_user;

--
-- Name: supplier_quotes; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.supplier_quotes (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    rfq_line_id uuid NOT NULL,
    supplier_id uuid NOT NULL,
    quoted_price numeric(15,2) NOT NULL,
    quoted_delivery_date date NOT NULL,
    supplier_notes text,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT supplier_quotes_quoted_price_check CHECK ((quoted_price >= (0)::numeric))
);


ALTER TABLE public.supplier_quotes OWNER TO horizon_user;

--
-- Name: suppliers; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.suppliers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    supplier_name character varying(255) NOT NULL,
    supplier_code character varying(50) NOT NULL,
    email character varying(255),
    phone character varying(50),
    address text,
    address_line1 character varying(255),
    address_line2 character varying(255),
    city character varying(100),
    state character varying(100),
    postal_code character varying(20),
    country character varying(100),
    tax_number character varying(50),
    status public.supplierstatus DEFAULT 'active'::public.supplierstatus,
    payment_terms integer DEFAULT 30,
    tags jsonb,
    custom_fields jsonb,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamp with time zone
);


ALTER TABLE public.suppliers OWNER TO horizon_user;

--
-- Name: system_config; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.system_config (
    key character varying(100) NOT NULL,
    value text NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by character varying(100) NOT NULL
);


ALTER TABLE public.system_config OWNER TO horizon_user;

--
-- Name: tax_rules; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.tax_rules (
    id uuid NOT NULL,
    tax_template_id uuid NOT NULL,
    rule_name character varying(255) NOT NULL,
    tax_type character varying(100) NOT NULL,
    description text,
    tax_rate numeric(5,2) NOT NULL,
    account_head_id uuid NOT NULL,
    is_compound boolean DEFAULT false NOT NULL,
    sequence integer NOT NULL,
    applicability_conditions jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.tax_rules OWNER TO horizon_user;

--
-- Name: tax_templates; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.tax_templates (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    template_code character varying(100) NOT NULL,
    template_name character varying(255) NOT NULL,
    description text,
    tax_category character varying(50) NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    applicability_rules jsonb,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp with time zone
);


ALTER TABLE public.tax_templates OWNER TO horizon_user;

--
-- Name: transaction_charge_breakdown; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.transaction_charge_breakdown (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    transaction_type character varying(50) NOT NULL,
    transaction_id uuid NOT NULL,
    charge_template_id uuid,
    charge_type character varying(50) NOT NULL,
    description character varying(255),
    calculation_method character varying(20) NOT NULL,
    charge_amount numeric(15,2) NOT NULL,
    account_head_id uuid NOT NULL,
    is_auto_calculated boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.transaction_charge_breakdown OWNER TO horizon_user;

--
-- Name: transaction_tax_breakdown; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.transaction_tax_breakdown (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    transaction_type character varying(50) NOT NULL,
    transaction_id uuid NOT NULL,
    tax_template_id uuid NOT NULL,
    tax_rule_id uuid NOT NULL,
    tax_type character varying(100) NOT NULL,
    tax_rate numeric(5,2) NOT NULL,
    taxable_amount numeric(15,2) NOT NULL,
    tax_amount numeric(15,2) NOT NULL,
    is_compound boolean DEFAULT false NOT NULL,
    sequence integer NOT NULL,
    account_head_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.transaction_tax_breakdown OWNER TO horizon_user;

--
-- Name: warehouses_extended; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.warehouses_extended (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    code character varying(50) NOT NULL,
    description text,
    parent_warehouse_id uuid,
    warehouse_type public.warehousetype DEFAULT 'warehouse'::public.warehousetype,
    address_line1 character varying(255),
    address_line2 character varying(255),
    city character varying(100),
    state character varying(100),
    postal_code character varying(20),
    country character varying(100),
    contact_name character varying(255),
    contact_phone character varying(50),
    contact_email character varying(255),
    total_capacity integer,
    capacity_uom character varying(50),
    stock_account_id uuid,
    is_active boolean DEFAULT true,
    is_default boolean DEFAULT false,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamp with time zone
);


ALTER TABLE public.warehouses_extended OWNER TO horizon_user;

--
-- Data for Name: account_audit_log; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.account_audit_log (id, account_id, action, user_id, "timestamp", changes, audit_metadata) FROM stdin;
\.


--
-- Data for Name: account_balances; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.account_balances (id, account_id, currency, debit_total, credit_total, balance, base_currency_balance, as_of_date, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: accounts; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.accounts (id, organization_id, account_code, account_name, account_type, parent_account_id, currency, status, is_posting_account, description, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.alembic_version (version_num) FROM stdin;
k1l2m3n4o5p6q7
\.


--
-- Data for Name: batches; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.batches (id, organization_id, batch_no, item_id, manufacturing_date, expiry_date, supplier_id, supplier_batch_no, status, reference_type, reference_id, description, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: charge_templates; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.charge_templates (id, organization_id, template_code, template_name, description, charge_type, calculation_method, fixed_amount, percentage_rate, base_on, account_head_id, is_active, applicability_rules, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
\.


--
-- Data for Name: chart_of_accounts; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.chart_of_accounts (id, organization_id, account_code, account_name, account_type, parent_account_id, level, is_group, opening_balance, current_balance, is_active, tags, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
aa2609fb-93f3-452d-9e18-8c06ab1d20a9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1000	Assets	asset	\N	1	t	0.00	0.00	t	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
3dd50f6f-6530-44ee-8fca-ffb66da268ef	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1130	Inventory	asset	aa2609fb-93f3-452d-9e18-8c06ab1d20a9	2	f	0.00	0.00	t	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
\.


--
-- Data for Name: communication_logs; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.communication_logs (id, organization_id, doc_type, doc_id, doc_no, version, channel, recipient_type, recipient, recipient_name, sender_id, sender_name, sender_email, subject, message, status, sent_at, delivered_at, failed_at, error_message, extra_data, created_at, updated_at) FROM stdin;
c9d266c6-6d1e-46d4-8153-447918982d21	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	quotation	c71b994c-258f-42f6-973a-c31a5fd5eb78	SUN-009	1	email	\N	devnegikec@gmail.com	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	\N	Quotation SUN-009	Dear Customer,\n\nPlease find attached quotation SUN-009 for your review.\n\nBest regards	failed	\N	\N	2026-02-19 12:39:27.295034+00	Failed to send email: Error connecting to localhost on port 587: [Errno 111] Connection refused	{"cc": null, "has_attachments": false}	2026-02-19 12:39:27.323209+00	2026-02-19 12:39:27.323217+00
1422dd8e-6021-4cdd-b993-cdcbc9babd20	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	quotation	c71b994c-258f-42f6-973a-c31a5fd5eb78	SUN-009	1	email	\N	negi.yaten@gmail.com	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	\N	Quotation SUN-009	Dear Customer,\n\nPlease find attached quotation SUN-009 for your review.\n\nBest regards	sent	2026-02-19 13:04:34.314576+00	\N	\N	\N	{"cc": null, "has_attachments": false, "attachment_count": 0, "attachment_names": []}	2026-02-19 13:04:34.363002+00	2026-02-19 13:04:34.363012+00
54cc290d-5507-498d-b77b-7cdaa9e52a20	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	quotation	a32c9b86-144e-46c5-9686-0a6586093a38	MUNN-09	1	email	\N	yaten.negi@gmail.com	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	\N	Quotation MUNN-09	Dear Customer,\n\nPlease find attached quotation MUNN-09 for your review.\n\nBest regards\nDev	sent	2026-02-20 06:32:04.158437+00	\N	\N	\N	{"cc": null, "has_attachments": false, "attachment_count": 0, "attachment_names": []}	2026-02-20 06:32:04.185039+00	2026-02-20 06:32:04.185114+00
27528267-6465-4a4d-84e1-c1db038701e9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	quotation	c71b994c-258f-42f6-973a-c31a5fd5eb78	SUN-009	1	email	\N	devendera.negi@gmail.com	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	\N	Quotation SUN-009	Dear Customer,\n\nPlease find attached quotation SUN-009 for your review.\n\nBest regards\nDevendra Negi 	sent	2026-02-20 09:12:19.874718+00	\N	\N	\N	{"cc": null, "has_attachments": true, "attachment_count": 2, "attachment_names": ["SUN-009.pdf", "SUN-009.pdf"]}	2026-02-20 09:12:19.921173+00	2026-02-20 09:12:19.921205+00
43a24cd9-d345-4188-be63-177465834d83	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	invoice	d0000001-0001-4000-a000-000000000005	INV-SEED-001	1	email	\N	devnegikec@gmail.com	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	\N	Invoice INV-SEED-001	Dear Customer,\n\nPlease find attached invoice INV-SEED-001 for your review.\n\nBest regards	sent	2026-02-22 13:43:23.822701+00	\N	\N	\N	{"cc": null, "has_attachments": true, "attachment_count": 2, "attachment_names": ["INV-SEED-001.pdf", "INV-SEED-001.pdf"]}	2026-02-22 13:43:23.856914+00	2026-02-22 13:43:23.85692+00
\.


--
-- Data for Name: customers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.customers (id, organization_id, customer_name, customer_code, email, phone, address, address_line1, address_line2, city, state, postal_code, country, tax_number, status, credit_limit, outstanding_balance, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at, is_tax_exempt, tax_exemption_certificate_no) FROM stdin;
2442b9be-c640-4f8f-9a87-e07fb8ba875b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Suinoli Pvt Ltd, India	CUS-007	info@suinoli.com	+91-9787878790	13123, Sobha Dream Acres\nPanathur Main Road, Off Orr Balagere	13123, Sobha Dream Acres	Panathur Main Road, Off Orr Balagere	Bangalore Urban	Karnataka	560087	IN	UTZ9987265RT	active	100000.00	90800.00	["top", "first", "more"]	{}	{}	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-03 08:56:29.08008+00	2026-02-03 10:04:43.734254+00	\N	f	\N
60b23cd6-744b-495f-98e7-4730a6c1c1f9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Acme Corporation	CUST-001	contact@acme.com	+91-9876543001	\N	\N	\N	Mumbai	\N	\N	IN	\N	blocked	1524876.00	12350.00	\N	{}	{}	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-26 15:47:10.155932+00	2026-02-03 15:47:17.774462+00	\N	f	\N
08d25496-002c-4edb-b033-a76a9acfa674	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Huge Rock	HRU-01	ingo@hugerock.com	+91-9711452000	Bangalore	123, B block	Indra Nager	Bangalore	Karnataka	560087	IN	zo87992jd8kk99	inactive	10000.00	59098.00	["top"]	{}	{}	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-03 08:32:38.618222+00	2026-02-03 15:47:27.602657+00	\N	f	\N
\.


--
-- Data for Name: default_accounts; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.default_accounts (id, transaction_type, scenario, account_id, organization_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: delivery_note_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.delivery_note_items (id, organization_id, delivery_note_id, item_id, qty, uom, rate, amount, warehouse_id, batch_no, serial_nos, sort_order, extra_data, created_at, updated_at) FROM stdin;
82d1168e-994a-4c26-abe2-0254df2edf2f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000004	f47ac10b-58cc-4372-a567-0e02b2c3d471	3.000	Unit	1200.00	3600.00	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	1	\N	2026-01-30 14:00:00+00	2026-01-30 14:00:00+00
59e3ffa6-1427-4800-b267-80b560ff3236	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000004	f47ac10b-58cc-4372-a567-0e02b2c3d472	10.000	Piece	45.00	450.00	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	2	\N	2026-01-30 14:00:00+00	2026-01-30 14:00:00+00
c4d10273-3022-40f4-bc97-aaaf42f74e25	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000004	f47ac10b-58cc-4372-a567-0e02b2c3d473	5.000	Piece	85.00	425.00	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	3	\N	2026-01-30 14:00:00+00	2026-01-30 14:00:00+00
\.


--
-- Data for Name: delivery_notes; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.delivery_notes (id, organization_id, delivery_note_no, customer_id, delivery_date, status, warehouse_id, pick_list_id, reference_type, reference_id, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
1f72bc02-c105-4b10-ba36-19374a9259e1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	DN-2026-001	2442b9be-c640-4f8f-9a87-e07fb8ba875b	2026-02-11 11:15:40.269144+00	draft	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	\N	Standard delivery	\N	\N	\N	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
fc30c4d9-cb9c-44d4-9c3e-cc1f35f41d59	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	DN-2026-002	60b23cd6-744b-495f-98e7-4730a6c1c1f9	2026-02-11 11:15:40.269144+00	draft	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	\N	\N	Bulk shipment	\N	\N	\N	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
d0000001-0001-4000-a000-000000000004	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	DN-SEED-001	60b23cd6-744b-495f-98e7-4730a6c1c1f9	2026-01-30 14:00:00+00	submitted	cbf290a6-91cb-4c93-b9a6-db408bb3c274	d0000001-0001-4000-a000-000000000003	SALES_ORDER	d0000001-0001-4000-a000-000000000002	Delivery for SO-SEED-001	2026-01-30 14:30:00+00	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-01-30 14:00:00+00	2026-01-30 14:30:00+00
\.


--
-- Data for Name: document_numbering_config; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.document_numbering_config (id, organization_id, document_type, prefix, padding, include_year, separator) FROM stdin;
\.


--
-- Data for Name: document_sequence_counter; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.document_sequence_counter (id, organization_id, document_type, sequence_year, next_number) FROM stdin;
\.


--
-- Data for Name: exchange_rates; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.exchange_rates (id, from_currency, to_currency, rate, effective_date, created_at) FROM stdin;
\.


--
-- Data for Name: invoice_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.invoice_items (id, organization_id, invoice_id, item_id, item_code, item_name, qty, uom, rate, amount, sort_order, extra_data, created_at, updated_at) FROM stdin;
3581a92c-8448-46c8-b172-e6cf1a0f36b0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000005	f47ac10b-58cc-4372-a567-0e02b2c3d471	HZN-LP-01	Horizon Pro Laptop	3.000	Unit	1200.00	3600.00	1	\N	2026-01-30 16:00:00+00	2026-01-30 16:00:00+00
e8cc44e4-fed1-4056-8571-de11d3baf7dd	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000005	f47ac10b-58cc-4372-a567-0e02b2c3d472	HZN-MO-05	Optical Gaming Mouse	10.000	Piece	45.00	450.00	2	\N	2026-01-30 16:00:00+00	2026-01-30 16:00:00+00
c1e3d2d6-5960-40d6-a5d1-6cab9fe3e1a2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000005	f47ac10b-58cc-4372-a567-0e02b2c3d473	HZN-KB-09	Mechanical Keyboard	5.000	Piece	85.00	425.00	3	\N	2026-01-30 16:00:00+00	2026-01-30 16:00:00+00
093260aa-9a37-459c-ab9d-a7647d0be3a0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000005	f47ac10b-58cc-4372-a567-0e02b2c3d478	HZN-MN-27	27-inch 4K Monitor	20.000	Unit	410.00	8200.00	1	\N	2026-02-14 16:00:00+00	2026-02-14 16:00:00+00
10222923-8e09-4715-95d7-f92ca83137ad	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000005	f47ac10b-58cc-4372-a567-0e02b2c3d479	HZN-HD-02	Noise Cancelling Headphones	30.000	Piece	165.00	4950.00	2	\N	2026-02-14 16:00:00+00	2026-02-14 16:00:00+00
\.


--
-- Data for Name: invoices; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.invoices (id, organization_id, invoice_no, invoice_type, party_id, party_type, posting_date, due_date, status, grand_total, outstanding_amount, currency, reference_type, reference_id, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at, net_total, total_tax, total_charges) FROM stdin;
d0000001-0001-4000-a000-000000000005	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	INV-SEED-001	sales	60b23cd6-744b-495f-98e7-4730a6c1c1f9	CUSTOMER	2026-02-20 12:53:13.101274+00	2026-03-20 12:53:13.101274+00	paid	4450.00	0.00	USD	SALES_ORDER	d0000001-0001-4000-a000-000000000002	Invoice for SO-SEED-001 (Acme Corp)	2026-02-20 12:53:13.101274+00	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-02-18 12:53:13.101274+00	2026-02-18 12:53:13.101274+00	0.00	0.00	0.00
e0000001-0001-4000-a000-000000000005	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	INV-SEED-002	purchase	a1b2c3d4-1111-4aaa-bbbb-000000000001	SUPPLIER	2026-02-20 12:53:13.101274+00	2026-03-20 12:53:13.101274+00	paid	13150.00	0.00	USD	PURCHASE_ORDER	e0000001-0001-4000-a000-000000000003	Purchase invoice from TechWorld for PO from RFQ	2026-02-20 12:53:13.101274+00	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-02-18 12:53:13.101274+00	2026-02-18 12:53:13.101274+00	0.00	0.00	0.00
\.


--
-- Data for Name: item_groups; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.item_groups (id, organization_id, name, code, description, parent_id, default_valuation_method, default_uom, is_active, extra_data, created_by, updated_by, created_at, updated_at, deleted_at, sales_tax_template_id, purchase_tax_template_id) FROM stdin;
76fb273a-70cd-45a1-bbc7-fbb370f09b2b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Raw Materials	RAW	Raw materials for production	\N	fifo	Kg	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N	\N	\N
d3478470-32a3-4db2-b665-195920b44a7e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Finished Goods	FG	Finished products ready for sale	\N	fifo	Nos	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N	\N	\N
39de3d18-f925-4b09-875b-338e21bc2a7d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Consumables	CONS	Consumable items	\N	moving_average	Nos	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N	\N	\N
324ef9a3-dc4a-479b-be37-cc5f23ff2ea3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Services	SVC	Service items	\N	\N	Hour	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N	\N	\N
e07dc93d-1f02-4f1a-bf9d-255c1490f157	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Plastics	RAW-PLS	Plastic raw materials	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	fifo	Kg	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N	\N	\N
feacdbde-f4db-4725-b2bc-0efe83d84692	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Electronics	FG-ELEC	Electronic products	d3478470-32a3-4db2-b665-195920b44a7e	fifo	Nos	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N	\N	\N
59057b72-15a8-46a7-bae8-104c7fc73dbe	9a9b7483-4327-46f6-852b-70c5faab67d4	KIDS-ITEM	KID-P001	KIDS-ITEM	\N	fifo	Piece	t	{}	661678e8-12df-44bc-b50a-d69538eb9590	661678e8-12df-44bc-b50a-d69538eb9590	2026-02-05 16:47:06.042179+00	2026-02-05 16:47:06.042471+00	\N	\N	\N
c9d50dc8-0afd-4540-aedd-90d0373175b7	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Industrial Tools	IND-TOOL-1	Industrial Tools	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	fifo	Kg	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N	\N	\N
\.


--
-- Data for Name: item_prices; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.item_prices (id, organization_id, item_id, price_list_id, price, currency, valid_from, valid_upto, min_qty, extra_data, created_at, updated_at) FROM stdin;
5bc8ce47-9930-44b6-89df-959186151936	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d471	00000000-0000-0000-0000-000000000001	1200.00	USD	2025-01-01 00:00:00+00	\N	1	\N	2025-12-10 10:00:00+00	2025-12-10 10:00:00+00
a5607295-33c8-4300-8b38-86c1878f796b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d471	00000000-0000-0000-0000-000000000002	1080.00	USD	2025-01-01 00:00:00+00	\N	1	\N	2025-12-10 10:00:00+00	2025-12-10 10:00:00+00
80c54e88-21a1-4707-a425-f6c8287b2789	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d472	00000000-0000-0000-0000-000000000001	45.00	USD	2025-01-01 00:00:00+00	\N	1	\N	2025-12-10 10:00:00+00	2025-12-10 10:00:00+00
7675b568-5bb6-46a5-9374-6a461f6bdfa3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d472	00000000-0000-0000-0000-000000000002	38.00	USD	2025-01-01 00:00:00+00	\N	1	\N	2025-12-10 10:00:00+00	2025-12-10 10:00:00+00
0543a8b5-f0f5-4a60-b80e-afdce1954022	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d473	00000000-0000-0000-0000-000000000001	85.00	USD	2025-01-01 00:00:00+00	\N	1	\N	2025-12-10 10:00:00+00	2025-12-10 10:00:00+00
a0f5bb7a-a09f-40a4-b407-f65cc523fa52	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d473	00000000-0000-0000-0000-000000000002	72.00	USD	2025-01-01 00:00:00+00	\N	1	\N	2025-12-10 10:00:00+00	2025-12-10 10:00:00+00
d160fab3-f29e-41da-ae64-4cba8b4dc176	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d478	00000000-0000-0000-0000-000000000001	450.00	USD	2025-01-01 00:00:00+00	\N	1	\N	2025-12-10 10:00:00+00	2025-12-10 10:00:00+00
8244508a-5f0a-4b93-a315-7915ee70d794	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d478	00000000-0000-0000-0000-000000000002	399.00	USD	2025-01-01 00:00:00+00	\N	1	\N	2025-12-10 10:00:00+00	2025-12-10 10:00:00+00
9aa8782e-dde8-4231-9162-08b0c0b8b97c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d479	00000000-0000-0000-0000-000000000001	199.00	USD	2025-01-01 00:00:00+00	\N	1	\N	2025-12-10 10:00:00+00	2025-12-10 10:00:00+00
cc74a913-3350-41cf-bb99-e266190a5403	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d479	00000000-0000-0000-0000-000000000002	169.00	USD	2025-01-01 00:00:00+00	\N	1	\N	2025-12-10 10:00:00+00	2025-12-10 10:00:00+00
\.


--
-- Data for Name: item_suppliers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.item_suppliers (id, organization_id, item_id, supplier_id, supplier_part_no, lead_time_days, is_default, extra_data, created_at, updated_at) FROM stdin;
0f29c66d-a24e-42c4-b702-b9a7e40f6216	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d471	a1b2c3d4-1111-4aaa-bbbb-000000000001	TW-LP-PRO-15	7	t	\N	2025-12-15 10:00:00+00	2025-12-15 10:00:00+00
f948db8a-de5e-464d-9b4a-bc0f7d661e16	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d471	a1b2c3d4-1111-4aaa-bbbb-000000000002	GE-LAPTOP-001	10	f	\N	2025-12-15 10:00:00+00	2025-12-15 10:00:00+00
f6daf462-77d3-4705-9571-d1dc44128283	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d472	a1b2c3d4-1111-4aaa-bbbb-000000000001	TW-MS-OPT-G	5	t	\N	2025-12-15 10:00:00+00	2025-12-15 10:00:00+00
f59fb661-b221-4078-8599-7c73eec5e574	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d472	f68137ef-49df-4ea5-8a57-fe22a0f446d2	SI-MOUSE-100	14	f	\N	2025-12-15 10:00:00+00	2025-12-15 10:00:00+00
cdce07f0-88fc-4a81-8c09-2f2ea48951b4	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d473	a1b2c3d4-1111-4aaa-bbbb-000000000002	GE-KB-MECH-09	6	t	\N	2025-12-15 10:00:00+00	2025-12-15 10:00:00+00
dcecf125-5ba0-4c34-9605-f2eac6186c16	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d473	a1b2c3d4-1111-4aaa-bbbb-000000000001	TW-KB-MK-09	8	f	\N	2025-12-15 10:00:00+00	2025-12-15 10:00:00+00
55512888-da45-41f4-9dca-761d59dc5352	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d478	a1b2c3d4-1111-4aaa-bbbb-000000000002	GE-MON-4K-27	8	t	\N	2025-12-15 10:00:00+00	2025-12-15 10:00:00+00
e6bc5abe-b2da-4c31-a3fb-be3bb60f6f56	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d478	a1b2c3d4-1111-4aaa-bbbb-000000000001	TW-MN-27-4K	12	f	\N	2025-12-15 10:00:00+00	2025-12-15 10:00:00+00
e901a62d-dd3e-4a7a-ab47-71f7682f9f63	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d479	a1b2c3d4-1111-4aaa-bbbb-000000000001	TW-HP-NC-02	5	t	\N	2025-12-15 10:00:00+00	2025-12-15 10:00:00+00
6e197279-e840-4f96-8ba7-f8d9686dfeda	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d479	a1b2c3d4-1111-4aaa-bbbb-000000000002	GE-HDPH-NC-02	9	f	\N	2025-12-15 10:00:00+00	2025-12-15 10:00:00+00
\.


--
-- Data for Name: items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.items (id, organization_id, item_code, item_name, description, item_group_id, uom, maintain_stock, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at, item_type, valuation_method, status, sales_tax_template_id, purchase_tax_template_id) FROM stdin;
44e948b1-47a4-44b8-930d-87ab3bdb7fe6	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RAMBO-09	Rambo Mix	Makses you rambo, the fighter 	feacdbde-f4db-4725-b2bc-0efe83d84692	Piece	t	f	f	\N	{}	f	f			9808.00	1823.00	f	0	0	5	108	0.000		f	f	\N	82939345		[]	[]	{}	{}	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 12:53:13.101267+00	2026-02-18 12:53:13.101274+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
84e6f7bd-06d1-443f-b81d-676cae252f63	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	IEO-908	Red Tonic	KKS-9	feacdbde-f4db-4725-b2bc-0efe83d84692	Box	t	f	f	\N	{}	f	f			9009.00	780.00	f	0	0	10	100	0.000		f	f	\N	82939346		[]	[]	{}	{}	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-17 05:54:15.544899+00	2026-02-17 05:54:15.544922+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d471	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	HZN-LP-01	Horizon Pro Laptop	High-performance workstation for developers.	feacdbde-f4db-4725-b2bc-0efe83d84692	Unit	t	f	f	\N	{}	f	t	\N	\N	1200.00	850.00	\N	\N	\N	1	50	\N	\N	\N	\N	\N	8901001	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 10:00:00+00	2026-02-18 10:00:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d472	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	HZN-MO-05	Optical Gaming Mouse	RGB lighting with 12000 DPI sensor.	feacdbde-f4db-4725-b2bc-0efe83d84692	Piece	t	f	f	\N	{}	f	f	\N	\N	45.00	20.00	\N	\N	\N	5	200	\N	\N	\N	\N	\N	8901002	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 10:05:00+00	2026-02-18 10:05:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d473	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	HZN-KB-09	Mechanical Keyboard	Blue switch clicky feedback keyboard.	feacdbde-f4db-4725-b2bc-0efe83d84692	Piece	t	f	f	\N	{}	f	f	\N	\N	85.00	40.00	\N	\N	\N	2	100	\N	\N	\N	\N	\N	8901003	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 10:10:00+00	2026-02-18 10:10:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d478	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	HZN-MN-27	27-inch 4K Monitor	Ultra-sharp display for designers.	feacdbde-f4db-4725-b2bc-0efe83d84692	Unit	t	f	f	\N	{}	f	t	\N	\N	450.00	310.00	\N	\N	\N	1	30	\N	\N	\N	\N	\N	8901004	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 10:12:00+00	2026-02-18 10:12:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d479	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	HZN-HD-02	Noise Cancelling Headphones	Studio quality wireless audio.	feacdbde-f4db-4725-b2bc-0efe83d84692	Piece	t	f	f	\N	{}	f	f	\N	\N	199.00	120.00	\N	\N	\N	2	150	\N	\N	\N	\N	\N	8901005	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 10:14:00+00	2026-02-18 10:14:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d474	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	TOOL-DRL-18	Power Drill 18V	Industrial grade cordless power drill.	c9d50dc8-0afd-4540-aedd-90d0373175b7	Box	t	f	f	\N	{}	t	t	\N	\N	150.00	95.00	\N	\N	\N	1	20	\N	\N	\N	\N	\N	8902001	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 10:15:00+00	2026-02-18 10:15:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d475	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	TOOL-SRW-SET	Screwdriver Set 24pc	Chrome vanadium magnetic tip set.	c9d50dc8-0afd-4540-aedd-90d0373175b7	Set	t	f	f	\N	{}	f	f	\N	\N	30.00	12.00	\N	\N	\N	10	500	\N	\N	\N	\N	\N	8902002	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 10:20:00+00	2026-02-18 10:20:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d481	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	TOOL-WRE-ADJ	Adjustable Wrench 12"	Heavy duty forged steel wrench.	c9d50dc8-0afd-4540-aedd-90d0373175b7	Piece	t	f	f	\N	{}	f	f	\N	\N	18.50	8.00	\N	\N	\N	5	1000	\N	\N	\N	\N	\N	8902003	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 10:22:00+00	2026-02-18 10:22:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d489	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	APP-MW-900	Smart Microwave Oven	900W with inverter technology and WiFi.	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Unit	t	f	f	\N	{}	f	t	\N	\N	299.00	180.00	\N	\N	\N	1	20	12.500	kg	\N	\N	\N	8905001	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 08:00:00+00	2026-02-19 08:00:00+00	\N	stock	fifo	active	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	c30187e0-ce10-4afa-9235-eb395e978a81
f47ac10b-58cc-4372-a567-0e02b2c3d490	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	APP-AC-15	Split AC 1.5 Ton	5-star rated energy efficient cooling.	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Set	t	f	f	\N	{}	f	t	\N	\N	550.00	410.00	\N	\N	\N	1	10	35.000	kg	\N	\N	\N	8905002	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 08:05:00+00	2026-02-19 08:05:00+00	\N	stock	fifo	active	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	c30187e0-ce10-4afa-9235-eb395e978a81
f47ac10b-58cc-4372-a567-0e02b2c3d491	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	OFF-CH-ERGO	Ergonomic Task Chair	Breathable mesh back with lumbar support.	d3478470-32a3-4db2-b665-195920b44a7e	Piece	t	f	f	\N	{}	f	f	\N	\N	185.00	90.00	\N	\N	\N	2	100	15.000	kg	\N	\N	\N	8906001	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 08:10:00+00	2026-02-19 08:10:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d492	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	OFF-DK-STD	Standing Desk (Manual)	Height adjustable crank-operated desk.	d3478470-32a3-4db2-b665-195920b44a7e	Unit	t	f	f	\N	{}	f	f	\N	\N	240.00	140.00	\N	\N	\N	1	50	28.000	kg	\N	\N	\N	8906002	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 08:15:00+00	2026-02-19 08:15:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d493	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RAW-ALU-6061	Aluminum Sheet 6061	Industrial grade aluminum for manufacturing.	39de3d18-f925-4b09-875b-338e21bc2a7d	Kg	t	f	f	\N	{}	t	f	\N	\N	12.00	7.50	\N	\N	\N	100	5000	1.000	kg	\N	\N	\N	8907001	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 08:20:00+00	2026-02-19 08:20:00+00	\N	stock	fifo	active	c30187e0-ce10-4afa-9235-eb395e978a81	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
59f5be83-ad1d-444d-98c5-dd53b9ac0e31	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	PULP-FICTION-01	Pulp Fiction	teste it 	c9d50dc8-0afd-4540-aedd-90d0373175b7	Piece	t	f	f	\N	{}	f	f			980.00	890.00	f	0	0	9	150	0.000		f	f	\N	82934234		[]	[]	{}	{}	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 13:15:00.439964+00	2026-02-18 13:15:00.439981+00	\N	stock	fifo	active	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d494	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ELE-SSD-1TB	NVMe SSD 1TB Gen4	Ultra-fast storage for high-end systems.	324ef9a3-dc4a-479b-be37-cc5f23ff2ea3	Piece	t	f	f	\N	{}	t	t	\N	\N	110.00	65.00	\N	\N	\N	10	1000	0.100	kg	\N	\N	\N	8908001	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 08:25:00+00	2026-02-19 08:25:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f47ac10b-58cc-4372-a567-0e02b2c3d495	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	PKG-BOX-LRG	Corrugated Box Large	Heavy-duty shipping boxes (Pack of 50).	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Pack	t	f	f	\N	{}	f	f	\N	\N	45.00	22.00	\N	\N	\N	5	500	8.500	kg	\N	\N	\N	8909001	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 08:30:00+00	2026-02-19 08:30:00+00	\N	stock	fifo	active	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
a17ac10b-58cc-4372-a567-0e02b2c3d001	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	HZN-TAB-10	Horizon Tab 10	10-inch OLED tablet for business use.	324ef9a3-dc4a-479b-be37-cc5f23ff2ea3	Unit	t	f	f	\N	{}	f	t	\N	\N	450.00	310.00	\N	\N	\N	1	100	0.500	kg	\N	\N	\N	1000001	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 12:00:00+00	2026-02-19 12:00:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
a17ac10b-58cc-4372-a567-0e02b2c3d002	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	OFF-LMP-DSK	LED Desk Lamp	Adjustable brightness LED lamp with USB port.	d3478470-32a3-4db2-b665-195920b44a7e	Piece	t	f	f	\N	{}	f	f	\N	\N	35.00	15.00	\N	\N	\N	5	500	0.800	kg	\N	\N	\N	1000002	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 12:05:00+00	2026-02-19 12:05:00+00	\N	stock	fifo	active	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	c30187e0-ce10-4afa-9235-eb395e978a81
a17ac10b-58cc-4372-a567-0e02b2c3d003	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	IND-PNT-BLU	Industrial Blue Paint	5L Weather-resistant industrial coating.	feacdbde-f4db-4725-b2bc-0efe83d84692	Bucket	t	f	f	\N	{}	t	f	\N	\N	85.00	42.00	\N	\N	\N	2	200	5.000	kg	\N	\N	\N	1000003	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 12:10:00+00	2026-02-19 12:10:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
a17ac10b-58cc-4372-a567-0e02b2c3d004	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	APP-KTL-SS	Electric Kettle 1.7L	Stainless steel rapid boil kettle.	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Unit	t	f	f	\N	{}	f	t	\N	\N	45.00	22.00	\N	\N	\N	5	1000	1.200	kg	\N	\N	\N	1000004	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 12:15:00+00	2026-02-19 12:15:00+00	\N	stock	fifo	active	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	c30187e0-ce10-4afa-9235-eb395e978a81
a17ac10b-58cc-4372-a567-0e02b2c3d005	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RAW-ST-BAR	Steel Reinforcement Bar	Grade 60 structural steel bar 10m.	39de3d18-f925-4b09-875b-338e21bc2a7d	Length	t	f	f	\N	{}	t	f	\N	\N	15.00	9.00	\N	\N	\N	50	5000	12.000	kg	\N	\N	\N	1000005	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 12:20:00+00	2026-02-19 12:20:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
a17ac10b-58cc-4372-a567-0e02b2c3d006	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	PKG-TAPE-HVY	Heavy Duty Packing Tape	60m roll of reinforced brown tape.	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Roll	t	f	f	\N	{}	f	f	\N	\N	4.50	1.80	\N	\N	\N	24	2400	0.300	kg	\N	\N	\N	1000006	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 12:25:00+00	2026-02-19 12:25:00+00	\N	stock	fifo	active	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
a17ac10b-58cc-4372-a567-0e02b2c3d007	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	MED-GLV-LAT	Latex Gloves (Box 100)	Powder-free medical grade gloves.	59057b72-15a8-46a7-bae8-104c7fc73dbe	Box	t	f	f	\N	{}	t	f	\N	\N	12.00	5.50	\N	\N	\N	10	1000	0.400	kg	\N	\N	\N	1000007	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 12:30:00+00	2026-02-19 12:30:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
a17ac10b-58cc-4372-a567-0e02b2c3d008	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	CLE-SOL-5L	Multi-purpose Cleaner	Concentrated floor and surface cleaner.	c9d50dc8-0afd-4540-aedd-90d0373175b7	Bottle	t	f	f	\N	{}	t	f	\N	\N	18.00	7.50	\N	\N	\N	12	1200	5.200	kg	\N	\N	\N	1000008	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 12:35:00+00	2026-02-19 12:35:00+00	\N	stock	fifo	active	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	c30187e0-ce10-4afa-9235-eb395e978a81
a17ac10b-58cc-4372-a567-0e02b2c3d009	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ELE-CAB-HD	HDMI Cable 2m	High-speed 4K HDMI 2.1 braided cable.	324ef9a3-dc4a-479b-be37-cc5f23ff2ea3	Piece	t	f	f	\N	{}	f	f	\N	\N	15.00	4.50	\N	\N	\N	20	5000	0.100	kg	\N	\N	\N	1000009	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 12:40:00+00	2026-02-19 12:40:00+00	\N	stock	fifo	active	668321a8-31d6-4c26-9908-6e904d6a60d7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
a17ac10b-58cc-4372-a567-0e02b2c3d010	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	OFF-PPR-A4	A4 Printer Paper	80gsm white paper (Ream of 500).	d3478470-32a3-4db2-b665-195920b44a7e	Ream	t	f	f	\N	{}	f	f	\N	\N	8.00	3.20	\N	\N	\N	50	10000	2.500	kg	\N	\N	\N	1000010	\N	\N	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 12:45:00+00	2026-02-19 12:45:00+00	\N	stock	fifo	active	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a
f14b07be-fd40-49a3-a263-143af9abd0bd	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-007	TEST 007		feacdbde-f4db-4725-b2bc-0efe83d84692	Piece	t	f	f	\N	{}	f	f			908.00	670.00	f	0	0	1	1	0.000		f	f	\N	123123124289		[]	[]	{}	{}	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-21 16:13:07.790403+00	2026-02-21 16:13:07.79041+00	\N	stock	fifo	active	c30187e0-ce10-4afa-9235-eb395e978a81	\N
604f5a6b-28d5-4113-857c-8a41a95ea943	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	new	iPhone Case	best iPhone case in the market	feacdbde-f4db-4725-b2bc-0efe83d84692	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	5	200	0.000	string	f	f	\N	string	string	["string"]	["string"]	{}	{}	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-23 17:09:39.7963+00	2026-02-23 17:09:39.796329+00	\N	stock	fifo	active	\N	\N
a6a10302-b38c-49dd-b5ae-2240dab15cb6	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM_MIX-100	Top Green Botales	test	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Piece	t	f	f	\N	{}	f	f			15.00	9.00	f	0	0	10	100	0.000		f	f	\N	9202938909		[]	[]	{}	{}	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-24 05:59:38.43912+00	2026-02-24 05:59:38.439128+00	\N	stock	fifo	active	ea4c30fb-1c2f-43ae-a92f-c0fd7798433f	\N
\.


--
-- Data for Name: journal_entries; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.journal_entries (id, organization_id, entry_no, posting_date, status, voucher_type, reference_type, reference_id, total_debit, total_credit, remarks, posted_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: journal_entry_lines; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.journal_entry_lines (id, organization_id, journal_entry_id, account_id, debit, credit, against_account_id, reference_type, reference_id, remarks, sort_order, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: landed_cost_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.landed_cost_items (id, organization_id, landed_cost_voucher_id, purchase_receipt_id, purchase_receipt_item_id, item_id, qty, amount, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: landed_cost_purchase_receipts; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.landed_cost_purchase_receipts (id, organization_id, landed_cost_voucher_id, purchase_receipt_id, amount, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: landed_cost_taxes_and_charges; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.landed_cost_taxes_and_charges (id, organization_id, landed_cost_voucher_id, description, amount, account_id, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: landed_cost_vouchers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.landed_cost_vouchers (id, organization_id, voucher_no, posting_date, status, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: material_request_lines; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.material_request_lines (id, organization_id, material_request_id, item_id, quantity, required_date, description, extra_data, created_at, updated_at, uom, estimated_unit_cost, requested_for, requested_for_department) FROM stdin;
3d07e082-15e0-4d2f-a1e1-b2f89cd7660c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	2b468765-d2df-40ae-bae7-3889eef3e481	a17ac10b-58cc-4372-a567-0e02b2c3d005	100.0000	2026-02-28	Optional value 	null	2026-02-20 06:19:03.985501+00	2026-02-20 06:19:03.985508+00	\N	\N	\N	\N
2b62a870-5566-46e4-948b-da1761bc3590	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	5ca24ad0-cd67-4622-ad1d-47bbe8290991	f47ac10b-58cc-4372-a567-0e02b2c3d490	105.0000	2026-03-05	Urgent reqluet 	null	2026-02-20 06:23:14.226348+00	2026-02-20 06:23:14.22635+00	\N	\N	\N	\N
e0000001-0001-4000-a000-000000000011	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000001	f47ac10b-58cc-4372-a567-0e02b2c3d478	20.0000	2026-02-15	27-inch 4K Monitor for new hires	\N	2026-01-25 09:00:00+00	2026-01-25 09:00:00+00	Unit	420.0000	IT Procurement	IT Department
e0000001-0001-4000-a000-000000000012	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000001	f47ac10b-58cc-4372-a567-0e02b2c3d479	30.0000	2026-02-15	Noise Cancelling Headphones for remote workers	\N	2026-01-25 09:00:00+00	2026-01-25 09:00:00+00	Piece	175.0000	IT Procurement	IT Department
\.


--
-- Data for Name: material_requests; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.material_requests (id, organization_id, status, notes, extra_data, created_by, updated_by, created_at, updated_at, deleted_at, request_no, type, priority, target_warehouse_id, requested_by, department) FROM stdin;
2b468765-d2df-40ae-bae7-3889eef3e481	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	submitted	teste it 	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-20 06:19:03.955682+00	2026-02-20 06:19:50.317244+00	\N	MR-2026-0001	purchase	medium	\N	\N	Manufacturing Depo 
5ca24ad0-cd67-4622-ad1d-47bbe8290991	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	draft	assebly line 	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-20 06:23:14.214159+00	2026-02-20 06:23:14.214163+00	\N	MR-2026-0002	purchase	urgent	\N	\N	Assembly 
e0000001-0001-4000-a000-000000000001	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	fully_quoted	Restock monitors and headphones for Q1 2026 demand. Current stock running low.	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-01-25 09:00:00+00	2026-02-01 11:00:00+00	\N	MR-SEED-001	purchase	high	cbf290a6-91cb-4c93-b9a6-db408bb3c274	8d509f22-5fe5-4765-9496-3a236cae2af1	IT Department
\.


--
-- Data for Name: organization_settings; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.organization_settings (id, organization_id, default_sales_tax_template_id, default_purchase_tax_template_id, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: payment_allocations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.payment_allocations (id, organization_id, payment_id, invoice_id, allocated_amount, extra_data, created_at, updated_at) FROM stdin;
c12e64aa-d78a-4e27-9ea8-1c5811f5ba66	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000006	d0000001-0001-4000-a000-000000000005	4450.00	\N	2026-02-15 10:00:00+00	2026-02-15 10:00:00+00
26aeb7f6-2381-447e-840a-fbda6f9d68f7	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000006	e0000001-0001-4000-a000-000000000005	13150.00	\N	2026-02-20 10:00:00+00	2026-02-20 10:00:00+00
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.payments (id, organization_id, payment_no, payment_type, party_id, party_type, posting_date, amount, status, payment_method, reference_no, remarks, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
d0000001-0001-4000-a000-000000000006	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	PAY-SEED-001	receive	60b23cd6-744b-495f-98e7-4730a6c1c1f9	CUSTOMER	2026-02-15 10:00:00+00	4450.00	completed	bank_transfer	NEFT-20260215-ACME	Full payment for INV-SEED-001	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-02-15 10:00:00+00	2026-02-15 10:00:00+00
e0000001-0001-4000-a000-000000000006	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	PAY-SEED-002	pay	a1b2c3d4-1111-4aaa-bbbb-000000000001	SUPPLIER	2026-02-20 10:00:00+00	13150.00	completed	bank_transfer	NEFT-20260220-TECHWORLD	Full payment for INV-SEED-002 (TechWorld Supplies)	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-02-20 10:00:00+00	2026-02-20 10:00:00+00
\.


--
-- Data for Name: pick_list_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.pick_list_items (id, organization_id, pick_list_id, item_id, warehouse_id, qty, picked_qty, uom, batch_no, serial_nos, sort_order, extra_data, created_at, updated_at) FROM stdin;
c6c0f39d-52b8-47c8-9ba8-7c54ea78d135	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e5555555-5555-5555-5555-555555555555	f47ac10b-58cc-4372-a567-0e02b2c3d472	cbf290a6-91cb-4c93-b9a6-db408bb3c274	2.000	1.000	Unit	\N	\N	1	\N	2026-02-19 08:22:58.352739+00	2026-02-19 08:22:58.352739+00
e8b55f4c-45a6-4fa9-a175-ed7141f7833e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e5555555-5555-5555-5555-555555555555	44e948b1-47a4-44b8-930d-87ab3bdb7fe6	cbf290a6-91cb-4c93-b9a6-db408bb3c274	5.000	0.000	Piece	\N	\N	2	\N	2026-02-19 08:22:58.352739+00	2026-02-19 08:22:58.352739+00
9a196730-bb97-4864-ae68-b69cff3a34d7	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000003	f47ac10b-58cc-4372-a567-0e02b2c3d471	cbf290a6-91cb-4c93-b9a6-db408bb3c274	3.000	3.000	Unit	\N	\N	1	\N	2026-01-28 08:00:00+00	2026-01-28 10:30:00+00
8b1fa9fe-980a-4765-9db9-a805f0d5c1f9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000003	f47ac10b-58cc-4372-a567-0e02b2c3d472	cbf290a6-91cb-4c93-b9a6-db408bb3c274	10.000	10.000	Piece	\N	\N	2	\N	2026-01-28 08:00:00+00	2026-01-28 10:30:00+00
a25ee647-40af-4eb3-bb06-f88d04aa7de2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000003	f47ac10b-58cc-4372-a567-0e02b2c3d473	cbf290a6-91cb-4c93-b9a6-db408bb3c274	5.000	5.000	Piece	\N	\N	3	\N	2026-01-28 08:00:00+00	2026-01-28 10:30:00+00
4b8ca97e-d3a7-4851-94ce-cc917fb0fb72	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f1e82d51-e53f-4b60-b28e-36cf929a8a2d	f47ac10b-58cc-4372-a567-0e02b2c3d472	cbf290a6-91cb-4c93-b9a6-db408bb3c274	50.000	0.000	Piece	\N	null	0	null	2026-02-21 12:43:23.432595+00	2026-02-21 12:43:23.4326+00
0209367c-5558-4345-ba57-b8388f1bf257	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f1e82d51-e53f-4b60-b28e-36cf929a8a2d	f47ac10b-58cc-4372-a567-0e02b2c3d471	cbf290a6-91cb-4c93-b9a6-db408bb3c274	20.000	0.000	Unit	\N	null	1	null	2026-02-21 12:43:23.432602+00	2026-02-21 12:43:23.432603+00
54467034-4523-4b22-8056-e8c8df3203ed	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f1e82d51-e53f-4b60-b28e-36cf929a8a2d	f47ac10b-58cc-4372-a567-0e02b2c3d492	cbf290a6-91cb-4c93-b9a6-db408bb3c274	10.000	0.000	Unit	\N	null	2	null	2026-02-21 12:43:23.432604+00	2026-02-21 12:43:23.432606+00
cc3186b1-a9f7-4e84-a05c-94b0a29e9736	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f1e82d51-e53f-4b60-b28e-36cf929a8a2d	f47ac10b-58cc-4372-a567-0e02b2c3d478	cbf290a6-91cb-4c93-b9a6-db408bb3c274	15.000	0.000	Unit	\N	null	3	null	2026-02-21 12:43:23.432607+00	2026-02-21 12:43:23.432608+00
e46a694d-db70-4707-a15c-da591ddc1796	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f1e82d51-e53f-4b60-b28e-36cf929a8a2d	f47ac10b-58cc-4372-a567-0e02b2c3d478	3c7956f3-d57a-4a01-936b-6d6cf98de665	5.000	0.000	Unit	\N	null	4	null	2026-02-21 12:43:23.432609+00	2026-02-21 12:43:23.43261+00
99cb51e1-395c-4485-9881-11b92d7a0b1f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	27df2470-af69-4991-bc0c-d2bf54cd0601	f47ac10b-58cc-4372-a567-0e02b2c3d472	cbf290a6-91cb-4c93-b9a6-db408bb3c274	50.000	0.000	Piece	\N	null	0	null	2026-02-21 16:32:53.937484+00	2026-02-21 16:32:53.937514+00
7172fbfe-ef1f-4fd3-98bd-4177fd810998	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	27df2470-af69-4991-bc0c-d2bf54cd0601	f47ac10b-58cc-4372-a567-0e02b2c3d471	3c7956f3-d57a-4a01-936b-6d6cf98de665	10.000	0.000	Unit	\N	null	1	null	2026-02-21 16:32:53.937517+00	2026-02-21 16:32:53.937518+00
52fcd67c-8e64-42df-8e6e-3e21ef3e172d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	27df2470-af69-4991-bc0c-d2bf54cd0601	f47ac10b-58cc-4372-a567-0e02b2c3d471	cbf290a6-91cb-4c93-b9a6-db408bb3c274	5.000	0.000	Unit	\N	null	2	null	2026-02-21 16:32:53.93752+00	2026-02-21 16:32:53.937522+00
f2be285f-78f6-4e91-9566-6c230c510cdf	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	27df2470-af69-4991-bc0c-d2bf54cd0601	f47ac10b-58cc-4372-a567-0e02b2c3d492	cbf290a6-91cb-4c93-b9a6-db408bb3c274	10.000	0.000	Unit	\N	null	3	null	2026-02-21 16:32:53.937523+00	2026-02-21 16:32:53.937525+00
\.


--
-- Data for Name: pick_lists; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.pick_lists (id, organization_id, pick_list_no, warehouse_id, status, pick_date, reference_type, reference_id, remarks, completed_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
e5555555-5555-5555-5555-555555555555	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	PICK-2026-001	cbf290a6-91cb-4c93-b9a6-db408bb3c274	draft	2026-02-19 08:21:21.056292+00	Sales Order	\N	Priority shipment for Horizon Tech	\N	\N	\N	\N	2026-02-19 08:21:21.056292+00	2026-02-19 08:21:21.056292+00
d0000001-0001-4000-a000-000000000003	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	PL-SEED-001	cbf290a6-91cb-4c93-b9a6-db408bb3c274	completed	2026-01-28 08:00:00+00	SALES_ORDER	d0000001-0001-4000-a000-000000000002	Pick for SO-SEED-001 (Acme Corp)	2026-01-28 10:30:00+00	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-01-28 08:00:00+00	2026-01-28 10:30:00+00
f1e82d51-e53f-4b60-b28e-36cf929a8a2d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	PL-2026-0003	cbf290a6-91cb-4c93-b9a6-db408bb3c274	draft	2026-02-21 12:43:23.409065+00	sales_order	53bd9be0-0266-4ae3-9857-2489136cb2c6	\N	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-21 12:43:23.424013+00	2026-02-21 12:43:23.42402+00
27df2470-af69-4991-bc0c-d2bf54cd0601	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	PL-2026-0004	cbf290a6-91cb-4c93-b9a6-db408bb3c274	draft	2026-02-21 16:32:53.91545+00	sales_order	53bd9be0-0266-4ae3-9857-2489136cb2c6	\N	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-21 16:32:53.928096+00	2026-02-21 16:32:53.928104+00
\.


--
-- Data for Name: purchase_order_lines; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.purchase_order_lines (id, organization_id, purchase_order_id, item_id, quantity, unit_price, line_total, received_quantity, extra_data, created_at, updated_at) FROM stdin;
f965abf8-de21-4539-896b-16a77ca74543	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000003	f47ac10b-58cc-4372-a567-0e02b2c3d478	20.0000	410.00	8200.00	20.0000	\N	2026-02-05 14:00:00+00	2026-02-14 16:00:00+00
0253004e-b7f9-4d35-a679-987cdd5c5ff9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000003	f47ac10b-58cc-4372-a567-0e02b2c3d479	30.0000	165.00	4950.00	30.0000	\N	2026-02-05 14:00:00+00	2026-02-14 16:00:00+00
\.


--
-- Data for Name: purchase_orders; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.purchase_orders (id, organization_id, rfq_id, reference_type, reference_id, party_type, party_id, status, subtotal, tax_amount, tax_rate, discount_amount, grand_total, extra_data, created_by, updated_by, created_at, updated_at, deleted_at, net_total, total_tax, total_charges) FROM stdin;
e0000001-0001-4000-a000-000000000003	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000002	RFQ	e0000001-0001-4000-a000-000000000002	SUPPLIER	a1b2c3d4-1111-4aaa-bbbb-000000000001	fully_received	13150.00	0.00	\N	0.00	13150.00	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-02-05 14:00:00+00	2026-02-14 16:00:00+00	\N	0.00	0.00	0.00
\.


--
-- Data for Name: purchase_receipt_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.purchase_receipt_items (id, organization_id, purchase_receipt_id, item_id, qty, uom, rate, amount, warehouse_id, batch_no, serial_nos, sort_order, extra_data, created_at, updated_at) FROM stdin;
935da9d6-441c-44fc-8196-5c6c96a78059	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000004	f47ac10b-58cc-4372-a567-0e02b2c3d478	20.000	Unit	410.00	8200.00	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	1	\N	2026-02-14 10:00:00+00	2026-02-14 10:00:00+00
a8b7f1df-feba-4050-a1c9-6751714ae851	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000004	f47ac10b-58cc-4372-a567-0e02b2c3d479	30.000	Piece	165.00	4950.00	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	2	\N	2026-02-14 10:00:00+00	2026-02-14 10:00:00+00
\.


--
-- Data for Name: purchase_receipts; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.purchase_receipts (id, organization_id, purchase_receipt_no, supplier_id, receipt_date, status, warehouse_id, reference_type, reference_id, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
e0000001-0001-4000-a000-000000000004	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	PR-SEED-001	a1b2c3d4-1111-4aaa-bbbb-000000000001	2026-02-14 10:00:00+00	submitted	cbf290a6-91cb-4c93-b9a6-db408bb3c274	PURCHASE_ORDER	e0000001-0001-4000-a000-000000000003	Received 20 monitors and 30 headphones from TechWorld. All items inspected and in good condition.	2026-02-14 11:00:00+00	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-02-14 10:00:00+00	2026-02-14 11:00:00+00
\.


--
-- Data for Name: put_away_rules; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.put_away_rules (id, organization_id, name, item_id, item_group_id, warehouse_id, capacity, priority, min_qty, max_qty, is_active, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: quotation_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.quotation_items (id, organization_id, quotation_id, item_id, qty, uom, rate, amount, sort_order, extra_data, created_at, updated_at, tax_template_id, tax_rate, tax_amount, total_amount) FROM stdin;
5401485f-b886-4611-bec0-6b56d7fe20f7	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	c71b994c-258f-42f6-973a-c31a5fd5eb78	f47ac10b-58cc-4372-a567-0e02b2c3d471	1.000	Unit	1200.00	1200.00	1	null	2026-02-19 09:27:09.350661+00	2026-02-19 09:27:09.350665+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	216.00	1416.00
9c19159b-8415-4fdb-b9c4-16ed259d2c1d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	c71b994c-258f-42f6-973a-c31a5fd5eb78	a17ac10b-58cc-4372-a567-0e02b2c3d008	12.000	Bottle	18.00	216.00	2	null	2026-02-19 09:27:09.35067+00	2026-02-19 09:27:09.350671+00	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	5.00	10.80	226.80
4c2afe7a-8750-4049-afd4-2cf38d6d2879	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	c71b994c-258f-42f6-973a-c31a5fd5eb78	f47ac10b-58cc-4372-a567-0e02b2c3d475	10.000	Set	30.00	300.00	3	null	2026-02-19 09:27:09.350676+00	2026-02-19 09:27:09.350677+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	54.00	354.00
6909a1a7-c4c0-48df-9255-8f7975549470	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	9bf9eecf-715b-4ed6-ab0f-3ea569bffb4d	f47ac10b-58cc-4372-a567-0e02b2c3d472	15.000	Piece	45.00	675.00	1	null	2026-02-19 10:11:25.451117+00	2026-02-19 10:11:25.451127+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	121.50	796.50
d66385d7-c56b-45f0-8da1-ae611236d310	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a32c9b86-144e-46c5-9686-0a6586093a38	f47ac10b-58cc-4372-a567-0e02b2c3d472	5.000	Piece	45.00	225.00	1	null	2026-02-20 06:28:45.892384+00	2026-02-20 06:28:45.892391+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	40.50	265.50
97e7cd6d-c703-4b7e-b797-49e4c0f13fb0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a32c9b86-144e-46c5-9686-0a6586093a38	f47ac10b-58cc-4372-a567-0e02b2c3d490	6.000	Set	550.00	3300.00	2	null	2026-02-20 06:28:45.892397+00	2026-02-20 06:28:45.892398+00	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	5.00	165.00	3465.00
542be6dc-5c31-4a78-88e1-ef600814c646	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000001	f47ac10b-58cc-4372-a567-0e02b2c3d471	3.000	Unit	1200.00	3600.00	1	\N	2026-01-20 10:00:00+00	2026-01-20 10:00:00+00	\N	0.00	0.00	3600.00
180c476a-4113-4eb7-b542-b0aa205fb117	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000001	f47ac10b-58cc-4372-a567-0e02b2c3d472	10.000	Piece	45.00	450.00	2	\N	2026-01-20 10:00:00+00	2026-01-20 10:00:00+00	\N	0.00	0.00	450.00
b88c2cf6-ab56-4442-a6f8-28ab4bb674e8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000001	f47ac10b-58cc-4372-a567-0e02b2c3d473	5.000	Piece	85.00	425.00	3	\N	2026-01-20 10:00:00+00	2026-01-20 10:00:00+00	\N	0.00	0.00	425.00
cceef7a0-d362-4cbc-a620-94ff3be0e693	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	9ba06c5d-12e3-4bb3-8fb9-129cac5fc4fe	f47ac10b-58cc-4372-a567-0e02b2c3d472	20.000	Piece	45.00	900.00	1	null	2026-02-21 09:39:29.409483+00	2026-02-21 09:39:29.409494+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	162.00	1062.00
3b4acaa6-2323-4f12-9c53-9b9d2517d55c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	9ba06c5d-12e3-4bb3-8fb9-129cac5fc4fe	f47ac10b-58cc-4372-a567-0e02b2c3d471	20.000	Unit	1200.00	24000.00	2	null	2026-02-21 09:39:29.4095+00	2026-02-21 09:39:29.409501+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	4320.00	28320.00
acc4dd06-62e2-4253-acac-829f31087e44	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	9ba06c5d-12e3-4bb3-8fb9-129cac5fc4fe	f47ac10b-58cc-4372-a567-0e02b2c3d478	28.000	Unit	450.00	12600.00	3	null	2026-02-21 09:39:29.409506+00	2026-02-21 09:39:29.409507+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	2268.00	14868.00
77c6b1d4-d207-4c49-a1cb-1d53ffab1021	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	27517faa-2876-4b37-a2aa-0f4469e98df9	f47ac10b-58cc-4372-a567-0e02b2c3d472	50.000	Piece	45.00	2250.00	1	null	2026-02-21 12:40:46.392988+00	2026-02-21 12:40:46.392993+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	405.00	2655.00
cc7ffd60-8237-4512-9368-efbe0524717c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	27517faa-2876-4b37-a2aa-0f4469e98df9	f47ac10b-58cc-4372-a567-0e02b2c3d471	20.000	Unit	1200.00	24000.00	2	null	2026-02-21 12:40:46.392999+00	2026-02-21 12:40:46.393+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	4320.00	28320.00
37c0f122-75b3-4749-861e-dd552c98394f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	27517faa-2876-4b37-a2aa-0f4469e98df9	f47ac10b-58cc-4372-a567-0e02b2c3d492	10.000	Unit	240.00	2400.00	3	null	2026-02-21 12:40:46.393004+00	2026-02-21 12:40:46.393005+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	432.00	2832.00
ab6543f6-351d-4c9e-b072-e890e0c08ad3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	27517faa-2876-4b37-a2aa-0f4469e98df9	f47ac10b-58cc-4372-a567-0e02b2c3d478	20.000	Unit	450.00	9000.00	4	null	2026-02-21 12:40:46.39301+00	2026-02-21 12:40:46.393011+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	1620.00	10620.00
e126bbf0-09fc-45ae-b844-acdba00a9ff0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	544af2ae-176e-4925-a427-276f387683bd	f47ac10b-58cc-4372-a567-0e02b2c3d471	10.000	Unit	1200.00	12000.00	1	null	2026-02-21 16:19:57.115824+00	2026-02-21 16:19:57.11583+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	2160.00	14160.00
c3b64e1a-c4bf-4f13-b29b-e1fd9c97ac52	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	544af2ae-176e-4925-a427-276f387683bd	f47ac10b-58cc-4372-a567-0e02b2c3d472	50.000	Piece	45.00	2250.00	2	null	2026-02-21 16:19:57.115836+00	2026-02-21 16:19:57.115837+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	405.00	2655.00
390f81a2-4bc4-4bd7-967c-8da14903ca23	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	cd76c9ed-7050-448d-81dd-fb859f134f13	f47ac10b-58cc-4372-a567-0e02b2c3d474	1.000	Box	150.00	150.00	1	null	2026-02-23 16:04:09.027375+00	2026-02-23 16:04:09.027382+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	27.00	177.00
beefd6c4-63ae-471f-9707-8eab2b2be55f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	cd76c9ed-7050-448d-81dd-fb859f134f13	f47ac10b-58cc-4372-a567-0e02b2c3d472	5.000	Piece	45.00	225.00	2	null	2026-02-23 16:04:09.027388+00	2026-02-23 16:04:09.027389+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	40.50	265.50
\.


--
-- Data for Name: quotations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.quotations (id, organization_id, quotation_no, customer_id, quotation_date, valid_until, status, grand_total, currency, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at, net_total, total_tax, total_charges, converted_to_sales_order) FROM stdin;
9bf9eecf-715b-4ed6-ab0f-3ea569bffb4d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	FIRST-REL-01	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-19 00:00:00+00	2026-04-11 00:00:00+00	sent	796.50	USD	ramob 	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 09:25:51.237504+00	2026-02-20 06:29:23.386388+00	0.00	0.00	0.00	f
c71b994c-258f-42f6-973a-c31a5fd5eb78	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SUN-009	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-19 00:00:00+00	2026-04-11 00:00:00+00	accepted	1996.80	INR	teste	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 09:27:09.330899+00	2026-02-19 10:09:53.567277+00	0.00	0.00	0.00	t
a32c9b86-144e-46c5-9686-0a6586093a38	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	MUNN-09	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-20 00:00:00+00	2026-04-11 00:00:00+00	accepted	3730.50	INR	\N	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-20 06:28:45.860485+00	2026-02-20 06:32:40.288438+00	0.00	0.00	0.00	f
d0000001-0001-4000-a000-000000000001	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	QTN-SEED-001	60b23cd6-744b-495f-98e7-4730a6c1c1f9	2026-01-20 10:00:00+00	2026-02-20 10:00:00+00	accepted	4450.00	USD	IT equipment for Acme Corp new office setup	2026-01-20 10:30:00+00	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-01-20 10:00:00+00	2026-01-22 09:00:00+00	0.00	0.00	0.00	t
9ba06c5d-12e3-4bb3-8fb9-129cac5fc4fe	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	QO-FEB-021	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-21 00:00:00+00	2026-04-30 00:00:00+00	accepted	44250.00	INR	\N	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-21 09:39:29.373421+00	2026-02-21 09:40:38.776632+00	0.00	0.00	0.00	t
27517faa-2876-4b37-a2aa-0f4469e98df9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	MUST-09	2442b9be-c640-4f8f-9a87-e07fb8ba875b	2026-02-21 00:00:00+00	2026-04-30 00:00:00+00	accepted	44427.00	INR	\N	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-21 12:40:46.351299+00	2026-02-21 12:42:08.180932+00	0.00	0.00	0.00	t
544af2ae-176e-4925-a427-276f387683bd	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	QUO-099	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-21 00:00:00+00	2026-03-23 00:00:00+00	accepted	16815.00	INR	\N	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-21 16:19:57.091944+00	2026-02-21 16:27:25.386059+00	0.00	0.00	0.00	t
cd76c9ed-7050-448d-81dd-fb859f134f13	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SUN-019	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-23 00:00:00+00	2026-04-25 00:00:00+00	draft	442.50	INR	\N	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-23 16:04:08.960849+00	2026-02-23 16:04:08.960858+00	0.00	0.00	0.00	f
\.


--
-- Data for Name: rfq_lines; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.rfq_lines (id, organization_id, rfq_id, item_id, quantity, required_date, description, extra_data, created_at, updated_at) FROM stdin;
e0000001-0001-4000-a000-000000000021	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000002	f47ac10b-58cc-4372-a567-0e02b2c3d478	20.0000	2026-02-15	27-inch 4K Monitor	\N	2026-01-26 10:00:00+00	2026-01-26 10:00:00+00
e0000001-0001-4000-a000-000000000022	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000002	f47ac10b-58cc-4372-a567-0e02b2c3d479	30.0000	2026-02-15	Noise Cancelling Headphones	\N	2026-01-26 10:00:00+00	2026-01-26 10:00:00+00
\.


--
-- Data for Name: rfq_suppliers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.rfq_suppliers (id, organization_id, rfq_id, supplier_id, created_at) FROM stdin;
e0000001-0001-4000-a000-000000000031	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000002	a1b2c3d4-1111-4aaa-bbbb-000000000001	2026-01-26 10:00:00+00
e0000001-0001-4000-a000-000000000032	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000002	a1b2c3d4-1111-4aaa-bbbb-000000000002	2026-01-26 10:00:00+00
\.


--
-- Data for Name: rfqs; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.rfqs (id, organization_id, material_request_id, reference_type, reference_id, status, closing_date, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
e0000001-0001-4000-a000-000000000002	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000001	MATERIAL_REQUEST	e0000001-0001-4000-a000-000000000001	closed	2026-02-05	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-01-26 10:00:00+00	2026-02-05 17:00:00+00	\N
\.


--
-- Data for Name: sales_order_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.sales_order_items (id, organization_id, sales_order_id, item_id, qty, uom, rate, amount, billed_qty, delivered_qty, sort_order, extra_data, created_at, updated_at, tax_template_id, tax_rate, tax_amount, total_amount) FROM stdin;
b59ff57b-f24b-46cb-bb1d-cb2cb4cd2ec0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e5e5ea5a-a9a8-45dc-bc91-768846ae9abb	84e6f7bd-06d1-443f-b81d-676cae252f63	17.000	Box	9009.00	153153.00	0.000	0.000	1	null	2026-02-17 12:08:49.989429+00	2026-02-17 12:08:49.989433+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	27567.54	180720.54
dfb7bb37-dd08-40ba-ac94-19a48e6d9d15	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	c2138eda-f0e5-427a-81ae-3dd34fdf52a7	59f5be83-ad1d-444d-98c5-dd53b9ac0e31	9.000	Piece	980.00	8820.00	0.000	0.000	1	null	2026-02-18 13:21:37.087342+00	2026-02-18 13:21:37.08735+00	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a	28.00	2469.60	11289.60
21f5404c-ff53-49c7-b70f-9b5afdab416d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	c2138eda-f0e5-427a-81ae-3dd34fdf52a7	44e948b1-47a4-44b8-930d-87ab3bdb7fe6	5.000	Piece	9808.00	49040.00	0.000	0.000	2	null	2026-02-18 13:21:37.087357+00	2026-02-18 13:21:37.087358+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	8827.20	57867.20
68c59458-cc01-40f7-aef4-a398f4e60f32	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	9a86106e-d70b-43cd-9532-cc8f6e7e2914	84e6f7bd-06d1-443f-b81d-676cae252f63	10.000	Box	9009.00	90090.00	0.000	0.000	1	null	2026-02-18 15:47:52.125833+00	2026-02-18 15:47:52.125837+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	16216.20	106306.20
fd607dfd-9e99-467b-a615-f7d526e1db57	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	fd67f192-6961-41be-99e8-ab01f16d6946	84e6f7bd-06d1-443f-b81d-676cae252f63	18.000	Box	9009.00	162162.00	0.000	0.000	1	null	2026-02-18 15:48:55.138098+00	2026-02-18 15:48:55.138101+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	29189.16	191351.16
42f422bc-b984-4a09-b04b-d19484d2e3d3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	c613ae98-9543-431a-9bec-c33a1ca1617d	84e6f7bd-06d1-443f-b81d-676cae252f63	20.000	Box	9009.00	180180.00	0.000	0.000	1	null	2026-02-18 16:48:17.178083+00	2026-02-18 16:48:17.178089+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	32432.40	212612.40
1f7085d4-ace7-4429-90ad-eff74b9b3f7d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ea3da38f-988f-445d-8ff9-84a7e5c9e429	84e6f7bd-06d1-443f-b81d-676cae252f63	19.000	Box	9009.00	171171.00	0.000	0.000	1	null	2026-02-19 06:11:44.310825+00	2026-02-19 06:11:44.310828+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	30810.78	201981.78
7718becb-e40d-4e01-9cb0-b3003cf952fc	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ea3da38f-988f-445d-8ff9-84a7e5c9e429	44e948b1-47a4-44b8-930d-87ab3bdb7fe6	5.000	Piece	9808.00	49040.00	0.000	0.000	2	null	2026-02-19 06:11:44.310833+00	2026-02-19 06:11:44.310835+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	8827.20	57867.20
7d9b92f5-1cf6-488c-8ee5-32e206048efc	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	4f3c0ec6-da19-466f-b3f8-9a5127ca3a7a	f47ac10b-58cc-4372-a567-0e02b2c3d471	1.000	Unit	1200.00	1200.00	0.000	0.000	1	null	2026-02-19 10:09:53.514486+00	2026-02-19 10:09:53.514491+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	216.00	1416.00
d0979bc5-e503-416e-9977-744e35414ed0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	4f3c0ec6-da19-466f-b3f8-9a5127ca3a7a	a17ac10b-58cc-4372-a567-0e02b2c3d008	12.000	Bottle	18.00	216.00	0.000	0.000	2	null	2026-02-19 10:09:53.514497+00	2026-02-19 10:09:53.514498+00	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	5.00	10.80	226.80
8c838fb2-8cdd-48bc-b584-e0c94a9dc7ee	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	4f3c0ec6-da19-466f-b3f8-9a5127ca3a7a	f47ac10b-58cc-4372-a567-0e02b2c3d475	10.000	Set	30.00	300.00	0.000	0.000	3	null	2026-02-19 10:09:53.514502+00	2026-02-19 10:09:53.514503+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	54.00	354.00
23428ef4-aced-4272-9244-8261b836161f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000002	f47ac10b-58cc-4372-a567-0e02b2c3d471	3.000	Unit	1200.00	3600.00	3.000	3.000	1	\N	2026-01-22 09:00:00+00	2026-01-30 16:00:00+00	\N	0.00	0.00	3600.00
4e4e506e-4758-46f4-9492-6a026d464eb5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000002	f47ac10b-58cc-4372-a567-0e02b2c3d472	10.000	Piece	45.00	450.00	10.000	10.000	2	\N	2026-01-22 09:00:00+00	2026-01-30 16:00:00+00	\N	0.00	0.00	450.00
55939e77-0602-4583-ab34-cf6b9ce568df	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d0000001-0001-4000-a000-000000000002	f47ac10b-58cc-4372-a567-0e02b2c3d473	5.000	Piece	85.00	425.00	5.000	5.000	3	\N	2026-01-22 09:00:00+00	2026-01-30 16:00:00+00	\N	0.00	0.00	425.00
e5878ce8-47bb-4a56-ae5f-80e7be0c2037	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f41a896a-5590-4f54-a2a9-9c15bd449eb5	f47ac10b-58cc-4372-a567-0e02b2c3d472	20.000	Piece	45.00	900.00	0.000	0.000	1	null	2026-02-21 09:40:38.711234+00	2026-02-21 09:40:38.711243+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	162.00	1062.00
8daf0782-d3da-4ef7-8331-b35a36f173eb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f41a896a-5590-4f54-a2a9-9c15bd449eb5	f47ac10b-58cc-4372-a567-0e02b2c3d471	20.000	Unit	1200.00	24000.00	0.000	0.000	2	null	2026-02-21 09:40:38.71125+00	2026-02-21 09:40:38.711251+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	4320.00	28320.00
d9a58557-22c4-49de-9f15-9a9defdaec1c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f41a896a-5590-4f54-a2a9-9c15bd449eb5	f47ac10b-58cc-4372-a567-0e02b2c3d478	28.000	Unit	450.00	12600.00	0.000	0.000	3	null	2026-02-21 09:40:38.711256+00	2026-02-21 09:40:38.711257+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	2268.00	14868.00
e9fe1f16-6fea-4ae1-b14e-e9b224a4c79a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	53bd9be0-0266-4ae3-9857-2489136cb2c6	f47ac10b-58cc-4372-a567-0e02b2c3d472	50.000	Piece	45.00	2250.00	0.000	0.000	1	null	2026-02-21 12:42:08.078236+00	2026-02-21 12:42:08.078241+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	405.00	2655.00
3e78e5b3-f80f-4356-9d71-3860eab492e8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	53bd9be0-0266-4ae3-9857-2489136cb2c6	f47ac10b-58cc-4372-a567-0e02b2c3d471	20.000	Unit	1200.00	24000.00	0.000	0.000	2	null	2026-02-21 12:42:08.078248+00	2026-02-21 12:42:08.078249+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	4320.00	28320.00
a9ebd4a3-f09a-43b0-8f2b-57e581a96e41	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	53bd9be0-0266-4ae3-9857-2489136cb2c6	f47ac10b-58cc-4372-a567-0e02b2c3d492	10.000	Unit	240.00	2400.00	0.000	0.000	3	null	2026-02-21 12:42:08.078254+00	2026-02-21 12:42:08.078255+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	432.00	2832.00
5ced4041-8d5d-416b-8e66-f484d9ad9714	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	53bd9be0-0266-4ae3-9857-2489136cb2c6	f47ac10b-58cc-4372-a567-0e02b2c3d478	20.000	Unit	450.00	9000.00	0.000	0.000	4	null	2026-02-21 12:42:08.07826+00	2026-02-21 12:42:08.078261+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	1620.00	10620.00
a6ec1de0-c2c9-437a-ba1d-3fa211ed15d3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	43d8cb77-56af-4f3f-82a6-280637eb16e3	f47ac10b-58cc-4372-a567-0e02b2c3d471	10.000	Unit	1200.00	12000.00	0.000	0.000	1	null	2026-02-21 16:27:25.340332+00	2026-02-21 16:27:25.340338+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	2160.00	14160.00
c651ad21-3341-44ba-9a33-375769361517	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	43d8cb77-56af-4f3f-82a6-280637eb16e3	f47ac10b-58cc-4372-a567-0e02b2c3d472	50.000	Piece	45.00	2250.00	0.000	0.000	2	null	2026-02-21 16:27:25.340343+00	2026-02-21 16:27:25.340344+00	668321a8-31d6-4c26-9908-6e904d6a60d7	18.00	405.00	2655.00
\.


--
-- Data for Name: sales_orders; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.sales_orders (id, organization_id, sales_order_no, customer_id, order_date, delivery_date, status, grand_total, currency, reference_type, reference_id, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at, net_total, total_tax, total_charges) FROM stdin;
cae80967-7db7-412a-9f95-6f7fde94f5a8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-AB-001	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-14 00:00:00+00	2026-02-27 00:00:00+00	confirmed	203514.00	INR	\N	\N	Sales order	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-13 10:35:40.263727+00	2026-02-15 08:32:47.726058+00	0.00	0.00	0.00
d9aaddac-96bb-4692-b42f-6d69c3b29e88	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260215084826	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-15 00:00:00+00	2026-02-28 00:00:00+00	confirmed	9000.00	INR	Quotation	b2e7663b-45c6-4f5f-aaac-47dfa596b542	Details of imtes 	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-15 08:48:26.222936+00	2026-02-15 08:49:06.803514+00	0.00	0.00	0.00
9535a4b6-0db6-4268-beb8-2f8b095c3577	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260215085909	60b23cd6-744b-495f-98e7-4730a6c1c1f9	2026-02-15 00:00:00+00	\N	confirmed	102000.00	USD	Quotation	369de46e-dfdc-4799-89b1-d7ae66a55400	test currency is in USD	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-15 08:59:09.12419+00	2026-02-15 08:59:41.396301+00	0.00	0.00	0.00
21081e2b-b406-4ce7-b8f7-28f7209ac3f9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260215072808	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-15 00:00:00+00	\N	closed	108900.00	INR	Quotation	98cad958-6a6e-4afb-998e-96d70cdfe279	Tesest remark 	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-15 07:28:08.580088+00	2026-02-15 09:06:52.187489+00	0.00	0.00	0.00
ea3da38f-988f-445d-8ff9-84a7e5c9e429	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260219061144	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-19 00:00:00+00	2026-02-28 00:00:00+00	delivered	259848.98	INR	Quotation	c2d8886a-3489-406e-b08c-43ed0b75bf28	test	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 06:11:44.291264+00	2026-02-19 06:19:41.412956+00	0.00	0.00	0.00
9a86106e-d70b-43cd-9532-cc8f6e7e2914	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260217112745	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-17 00:00:00+00	\N	confirmed	106306.20	INR	Quotation	5877f731-45e4-4a15-831c-7a2d185bca45	sdfs	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-17 11:27:45.976525+00	2026-02-18 15:58:31.04419+00	0.00	0.00	0.00
c2138eda-f0e5-427a-81ae-3dd34fdf52a7	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260218132137	2442b9be-c640-4f8f-9a87-e07fb8ba875b	2026-02-18 00:00:00+00	\N	confirmed	69156.80	INR	Quotation	f95a3913-8864-470f-80fc-f28e86b6d7d0	Test it 	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 13:21:37.050809+00	2026-02-18 16:02:13.838394+00	0.00	0.00	0.00
e5e5ea5a-a9a8-45dc-bc91-768846ae9abb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260217120849	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-17 00:00:00+00	\N	confirmed	180720.54	INR	Quotation	43402238-96d4-4d46-981e-208005c82694	Test  it	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-17 12:08:49.952719+00	2026-02-18 16:06:45.302589+00	0.00	0.00	0.00
4f3c0ec6-da19-466f-b3f8-9a5127ca3a7a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260219100953	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-19 00:00:00+00	\N	delivered	1996.80	INR	Quotation	c71b994c-258f-42f6-973a-c31a5fd5eb78	teste	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-19 10:09:53.454022+00	2026-02-20 06:34:22.489371+00	0.00	0.00	0.00
c613ae98-9543-431a-9bec-c33a1ca1617d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260217120746	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-17 00:00:00+00	2026-02-28 00:00:00+00	confirmed	212612.40	INR	Quotation	8f523d0d-d3ee-4196-a5ac-308984332646	test item 	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-17 12:07:46.725564+00	2026-02-20 14:32:56.472373+00	0.00	0.00	0.00
fd67f192-6961-41be-99e8-ab01f16d6946	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260217112310	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-17 00:00:00+00	\N	cancelled	191351.16	INR	Quotation	8f523d0d-d3ee-4196-a5ac-308984332646	test item 	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-17 11:23:10.062775+00	2026-02-20 14:35:15.549239+00	0.00	0.00	0.00
d0000001-0001-4000-a000-000000000002	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-SEED-001	60b23cd6-744b-495f-98e7-4730a6c1c1f9	2026-01-22 09:00:00+00	2026-01-30 09:00:00+00	delivered	4450.00	USD	Quotation	d0000001-0001-4000-a000-000000000001	Converted from QTN-SEED-001	2026-01-22 09:30:00+00	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2026-01-22 09:00:00+00	2026-01-30 16:00:00+00	0.00	0.00	0.00
f41a896a-5590-4f54-a2a9-9c15bd449eb5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260221094038	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-21 00:00:00+00	\N	cancelled	44250.00	INR	Quotation	9ba06c5d-12e3-4bb3-8fb9-129cac5fc4fe	\N	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-21 09:40:38.648967+00	2026-02-21 11:30:03.906977+00	0.00	0.00	0.00
53bd9be0-0266-4ae3-9857-2489136cb2c6	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260221124208	2442b9be-c640-4f8f-9a87-e07fb8ba875b	2026-02-21 00:00:00+00	2026-02-28 00:00:00+00	confirmed	44427.00	INR	Quotation	27517faa-2876-4b37-a2aa-0f4469e98df9	\N	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-21 12:42:08.041256+00	2026-02-21 12:42:56.316438+00	0.00	0.00	0.00
43d8cb77-56af-4f3f-82a6-280637eb16e3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	SO-20260221162725	08d25496-002c-4edb-b033-a76a9acfa674	2026-02-21 16:27:25.310013+00	\N	draft	16815.00	INR	Quotation	544af2ae-176e-4925-a427-276f387683bd	\N	\N	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-21 16:27:25.318977+00	2026-02-21 16:27:25.3381+00	0.00	0.00	0.00
\.


--
-- Data for Name: serial_no_history; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.serial_no_history (id, organization_id, serial_no_id, transaction_type, transaction_id, from_warehouse_id, to_warehouse_id, transaction_date, remarks, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: serial_nos; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.serial_nos (id, organization_id, serial_no, item_id, warehouse_id, status, purchase_date, purchase_rate, supplier_id, delivery_date, customer_id, warranty_period, warranty_expiry_date, amc_expiry_date, batch_no, description, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: status_transitions; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.status_transitions (id, entity_type, entity_id, previous_status, new_status, user_id, transitioned_at) FROM stdin;
0266da08-7b56-4877-9999-b51ee4a12fd9	MATERIAL_REQUEST	2b468765-d2df-40ae-bae7-3889eef3e481	draft	submitted	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-20 06:19:50.472805+00
\.


--
-- Data for Name: stock_entries; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_entries (id, organization_id, stock_entry_no, stock_entry_type, from_warehouse_id, to_warehouse_id, posting_date, posting_time, status, reference_type, reference_id, remarks, total_value, expense_account_id, cost_center_id, is_backflush, bom_id, extra_data, submitted_at, cancelled_at, created_at, updated_at, created_by, updated_by) FROM stdin;
469fc274-3ef9-4630-88d4-32bdb3086e08	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	STE-2024-001	material_receipt	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	2026-01-10 11:59:11.034338+00	10:30:00	submitted	\N	\N	Initial stock receipt	50000.00	\N	\N	\N	\N	null	2026-01-10 11:59:11.034338+00	\N	2026-02-09 11:59:11.035598+00	2026-02-09 11:59:11.0356+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
987fdc7f-962a-49bd-97ab-799748c3f89f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	STE-2024-002	material_receipt	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	2026-01-12 11:59:11.034338+00	14:00:00	submitted	\N	\N	Production receipt	90500.00	\N	\N	\N	\N	null	2026-01-12 11:59:11.034338+00	\N	2026-02-09 11:59:11.038237+00	2026-02-09 11:59:11.03824+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
529f11d2-0955-4b02-ba22-e9787080290c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	STE-2024-003	material_transfer	cbf290a6-91cb-4c93-b9a6-db408bb3c274	3c7956f3-d57a-4a01-936b-6d6cf98de665	2026-01-15 11:59:11.034338+00	11:00:00	submitted	\N	\N	Transfer from Main Warehouse to Retail Store	25500.00	\N	\N	\N	\N	null	2026-01-15 11:59:11.034338+00	\N	2026-02-09 11:59:11.043151+00	2026-02-09 11:59:11.043153+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
7ae70bdd-6f74-4dc4-8a8e-c644dab7ce61	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	STE-2024-004	material_issue	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	2026-01-20 11:59:11.034338+00	15:30:00	submitted	\N	\N	Sales/Issue	7250.00	\N	\N	\N	\N	null	2026-01-20 11:59:11.034338+00	\N	2026-02-09 11:59:11.044879+00	2026-02-09 11:59:11.04488+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
b0000001-0001-4000-a000-000000000001	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	STE-SEED-001	material_receipt	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	2026-01-02 09:00:00+00	09:00	submitted	PURCHASE_RECEIPT	\N	Initial stock intake - IT peripherals from TechWorld	77500.00	\N	\N	\N	\N	\N	\N	\N	2026-01-02 09:00:00+00	2026-01-02 09:00:00+00	8d509f22-5fe5-4765-9496-3a236cae2af1	\N
b0000001-0001-4000-a000-000000000002	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	STE-SEED-002	material_receipt	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	2026-01-03 10:00:00+00	10:00	submitted	PURCHASE_RECEIPT	\N	Initial stock intake - displays & audio from Global Electronics	33425.00	\N	\N	\N	\N	\N	\N	\N	2026-01-03 10:00:00+00	2026-01-03 10:00:00+00	8d509f22-5fe5-4765-9496-3a236cae2af1	\N
b0000001-0001-4000-a000-000000000003	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	STE-SEED-003	material_transfer	cbf290a6-91cb-4c93-b9a6-db408bb3c274	3c7956f3-d57a-4a01-936b-6d6cf98de665	2026-01-10 14:00:00+00	14:00	submitted	\N	\N	Transfer to Retail Store for display and sales	8870.00	\N	\N	\N	\N	\N	\N	\N	2026-01-10 14:00:00+00	2026-01-10 14:00:00+00	8d509f22-5fe5-4765-9496-3a236cae2af1	\N
\.


--
-- Data for Name: stock_entry_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_entry_items (id, organization_id, stock_entry_id, item_id, source_warehouse_id, target_warehouse_id, qty, uom, basic_rate, basic_amount, valuation_rate, batch_no, serial_nos, quality_inspection_id, description, extra_data, created_at, updated_at) FROM stdin;
1c936158-25bd-4cda-b9e4-555dbbf76b59	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	b0000001-0001-4000-a000-000000000001	f47ac10b-58cc-4372-a567-0e02b2c3d471	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	60.000	Unit	1050.00	63000.00	1050.00	\N	\N	\N	Horizon Pro Laptop - initial stock	\N	2026-01-02 09:00:00+00	2026-01-02 09:00:00+00
4a98f04c-aba8-4b34-bd98-039004598f45	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	b0000001-0001-4000-a000-000000000001	f47ac10b-58cc-4372-a567-0e02b2c3d472	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	225.000	Piece	38.00	8550.00	38.00	\N	\N	\N	Optical Gaming Mouse - initial stock	\N	2026-01-02 09:00:00+00	2026-01-02 09:00:00+00
f0f0c01c-918f-43f2-9204-9d189345f62f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	b0000001-0001-4000-a000-000000000001	f47ac10b-58cc-4372-a567-0e02b2c3d473	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	110.000	Piece	72.00	7920.00	72.00	\N	\N	\N	Mechanical Keyboard - initial stock	\N	2026-01-02 09:00:00+00	2026-01-02 09:00:00+00
90469628-37c1-449b-8b7a-6f2a69169cf8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	b0000001-0001-4000-a000-000000000002	f47ac10b-58cc-4372-a567-0e02b2c3d478	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	40.000	Unit	399.00	15960.00	399.00	\N	\N	\N	27-inch 4K Monitor - initial stock	\N	2026-01-03 10:00:00+00	2026-01-03 10:00:00+00
eb294795-0068-4805-973f-82dd871d837e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	b0000001-0001-4000-a000-000000000002	f47ac10b-58cc-4372-a567-0e02b2c3d479	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	85.000	Piece	169.00	14365.00	169.00	\N	\N	\N	Noise Cancelling Headphones - initial stock	\N	2026-01-03 10:00:00+00	2026-01-03 10:00:00+00
bf337ff1-7fff-4f22-a067-65f774656429	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	b0000001-0001-4000-a000-000000000003	f47ac10b-58cc-4372-a567-0e02b2c3d471	cbf290a6-91cb-4c93-b9a6-db408bb3c274	3c7956f3-d57a-4a01-936b-6d6cf98de665	5.000	Unit	1050.00	5250.00	1050.00	\N	\N	\N	Transfer laptops to retail	\N	2026-01-10 14:00:00+00	2026-01-10 14:00:00+00
bc95464b-a963-4f2f-89be-8fdb49c10bc4	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	b0000001-0001-4000-a000-000000000003	f47ac10b-58cc-4372-a567-0e02b2c3d472	cbf290a6-91cb-4c93-b9a6-db408bb3c274	3c7956f3-d57a-4a01-936b-6d6cf98de665	5.000	Piece	38.00	190.00	38.00	\N	\N	\N	Transfer mice to retail	\N	2026-01-10 14:00:00+00	2026-01-10 14:00:00+00
c98b46ec-5aab-484f-bf71-428b4000ab42	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	b0000001-0001-4000-a000-000000000003	f47ac10b-58cc-4372-a567-0e02b2c3d473	cbf290a6-91cb-4c93-b9a6-db408bb3c274	3c7956f3-d57a-4a01-936b-6d6cf98de665	5.000	Piece	72.00	360.00	72.00	\N	\N	\N	Transfer keyboards to retail	\N	2026-01-10 14:00:00+00	2026-01-10 14:00:00+00
1e9ad7bd-957f-485c-9257-c5a8b0774423	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	b0000001-0001-4000-a000-000000000003	f47ac10b-58cc-4372-a567-0e02b2c3d478	cbf290a6-91cb-4c93-b9a6-db408bb3c274	3c7956f3-d57a-4a01-936b-6d6cf98de665	5.000	Unit	399.00	1995.00	399.00	\N	\N	\N	Transfer monitors to retail	\N	2026-01-10 14:00:00+00	2026-01-10 14:00:00+00
bbbe52b3-27ef-43a8-a56d-4921a7571572	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	b0000001-0001-4000-a000-000000000003	f47ac10b-58cc-4372-a567-0e02b2c3d479	cbf290a6-91cb-4c93-b9a6-db408bb3c274	3c7956f3-d57a-4a01-936b-6d6cf98de665	5.000	Piece	169.00	845.00	169.00	\N	\N	\N	Transfer headphones to retail	\N	2026-01-10 14:00:00+00	2026-01-10 14:00:00+00
\.


--
-- Data for Name: stock_levels; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_levels (id, organization_id, product_id, warehouse_id, quantity_on_hand, quantity_reserved, quantity_available, last_counted_at, created_at, updated_at) FROM stdin;
ecb07fa1-e73a-496e-9e74-388b3b6785e8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	44e948b1-47a4-44b8-930d-87ab3bdb7fe6	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
6dd791aa-a226-45d8-9b98-2d67641838dd	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d475	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
cdf1651c-84fc-46b0-a736-a747fdcd4ca0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d481	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
bea994c2-36a2-4d33-a592-ba1e11bc942d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d489	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
40b5aae8-8970-438e-aafe-6ac0daad1dad	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d490	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
d023c026-9f16-4606-aef7-7e75a75d70d8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d491	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
9c4cc80c-0c6b-4683-a7b7-6537c3e4393d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d493	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
22b6e1b2-3175-4bbd-9164-b024c1d39201	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	59f5be83-ad1d-444d-98c5-dd53b9ac0e31	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
fdf86eff-9024-4c1b-9465-35cbd2dad96a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d494	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
7d570fb5-2dde-41d7-84b7-028d2b9f234c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d495	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
772b8f68-f588-4056-ab88-38e0cd1e7d32	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a17ac10b-58cc-4372-a567-0e02b2c3d001	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
96294429-3ff6-4795-b107-9e200dc301ce	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a17ac10b-58cc-4372-a567-0e02b2c3d002	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
ed50dccc-be90-4cce-9b01-3ee4d70c934d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a17ac10b-58cc-4372-a567-0e02b2c3d003	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
ea81fe0f-ba54-4ded-8942-878e3f83a006	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a17ac10b-58cc-4372-a567-0e02b2c3d004	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
af2a655f-668d-42cb-a9e4-ba558240c964	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a17ac10b-58cc-4372-a567-0e02b2c3d005	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
e7234e14-2c12-4e11-bba5-3a9711783390	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d474	a1e5f3b3-197d-433f-a0db-50237a31bb63	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
8877353b-c9ae-4342-bc29-da114bce1ee9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	84e6f7bd-06d1-443f-b81d-676cae252f63	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	2	98	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-20 14:35:15.948702+00
d2b6aa54-ca92-4226-a04c-62325175e13b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d492	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	30	70	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-21 16:32:53.942266+00
252de0c2-4374-4d80-ae03-93a932e03b27	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a17ac10b-58cc-4372-a567-0e02b2c3d006	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
952ccc30-4b35-49c2-a2da-030ac4fd837f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a17ac10b-58cc-4372-a567-0e02b2c3d007	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
144610d9-f92b-483e-8032-52a7bd80fbae	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a17ac10b-58cc-4372-a567-0e02b2c3d008	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
6ad7db5f-a86e-44b6-bd42-0fbc1511c5a5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a17ac10b-58cc-4372-a567-0e02b2c3d009	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
7a434195-fd71-41d6-ac7f-09a4217992ee	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	a17ac10b-58cc-4372-a567-0e02b2c3d010	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100	0	100	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00	2026-02-19 07:50:53.737101+00
9b8c5f93-9b57-423e-b3c0-6537c7973102	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d473	cbf290a6-91cb-4c93-b9a6-db408bb3c274	95	0	95	2026-01-15 10:00:00+00	2026-01-01 00:00:00+00	2026-01-15 10:00:00+00
d551db99-2a0e-404b-b0db-f377830555eb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d479	cbf290a6-91cb-4c93-b9a6-db408bb3c274	75	0	75	2026-01-15 10:00:00+00	2026-01-01 00:00:00+00	2026-01-15 10:00:00+00
3fc60ef1-3cf7-40f6-9694-3840dc9c239f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d472	3c7956f3-d57a-4a01-936b-6d6cf98de665	25	0	25	2026-01-20 10:00:00+00	2026-01-10 00:00:00+00	2026-01-20 10:00:00+00
88d74881-caac-4ad7-a74b-7ed8ee80bc0a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d473	3c7956f3-d57a-4a01-936b-6d6cf98de665	15	0	15	2026-01-20 10:00:00+00	2026-01-10 00:00:00+00	2026-01-20 10:00:00+00
0048dc4d-c188-420e-806b-0566b7fc48f2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d479	3c7956f3-d57a-4a01-936b-6d6cf98de665	10	0	10	2026-01-20 10:00:00+00	2026-01-10 00:00:00+00	2026-01-20 10:00:00+00
1aa9aae0-d01a-4f38-b0b9-a6455a7acc14	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d478	cbf290a6-91cb-4c93-b9a6-db408bb3c274	35	35	0	2026-01-15 10:00:00+00	2026-01-01 00:00:00+00	2026-02-21 12:43:23.438414+00
316d4f8a-347d-4ef2-8828-009245a51a3f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d478	3c7956f3-d57a-4a01-936b-6d6cf98de665	5	5	0	2026-01-20 10:00:00+00	2026-01-10 00:00:00+00	2026-02-21 12:43:23.438417+00
3cfe2ecc-47ec-449f-8b75-e6512cd1accd	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d471	cbf290a6-91cb-4c93-b9a6-db408bb3c274	50	50	0	2026-01-15 10:00:00+00	2026-01-01 00:00:00+00	2026-02-21 16:32:53.94226+00
69e61ceb-45c4-4535-b52e-afc6235a81db	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d471	3c7956f3-d57a-4a01-936b-6d6cf98de665	10	10	0	2026-01-20 10:00:00+00	2026-01-10 00:00:00+00	2026-02-21 16:32:53.942264+00
9c3cce0e-0c14-4a4d-9e15-769259ff2958	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d472	cbf290a6-91cb-4c93-b9a6-db408bb3c274	199	150	49	2026-01-15 10:00:00+00	2026-01-01 00:00:00+00	2026-02-21 16:32:53.942265+00
\.


--
-- Data for Name: stock_movements; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_movements (id, organization_id, product_id, warehouse_id, movement_type, quantity, unit_cost, reference_type, reference_id, notes, performed_by, performed_at, created_at, updated_at) FROM stdin;
1d2d94b1-0065-4627-a020-fb62e02a91d5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d471	cbf290a6-91cb-4c93-b9a6-db408bb3c274	in	60	1050.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000001	Initial receipt - Laptops	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-02 09:00:00+00	2026-01-02 09:00:00+00	2026-01-02 09:00:00+00
e6900247-9974-4b56-82a5-2b7d33cd6964	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d472	cbf290a6-91cb-4c93-b9a6-db408bb3c274	in	225	38.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000001	Initial receipt - Mice	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-02 09:05:00+00	2026-01-02 09:05:00+00	2026-01-02 09:05:00+00
a2738ac2-e9a9-442a-8101-16bb3d4350fe	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d473	cbf290a6-91cb-4c93-b9a6-db408bb3c274	in	110	72.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000001	Initial receipt - Keyboards	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-02 09:10:00+00	2026-01-02 09:10:00+00	2026-01-02 09:10:00+00
12395d73-eec5-4163-a3c1-9506bfd4644a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d478	cbf290a6-91cb-4c93-b9a6-db408bb3c274	in	40	399.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000002	Initial receipt - Monitors	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-03 10:00:00+00	2026-01-03 10:00:00+00	2026-01-03 10:00:00+00
f441353b-d4be-419e-9a94-e2758e0a4d8a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d479	cbf290a6-91cb-4c93-b9a6-db408bb3c274	in	85	169.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000002	Initial receipt - Headphones	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-03 10:05:00+00	2026-01-03 10:05:00+00	2026-01-03 10:05:00+00
7d694af7-3ab3-4d1c-88fe-031d112571fc	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d471	cbf290a6-91cb-4c93-b9a6-db408bb3c274	out	5	1050.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000003	Transfer to Retail Store	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-10 14:00:00+00	2026-01-10 14:00:00+00	2026-01-10 14:00:00+00
60724f4f-1df0-4e3a-841a-d76ec4fd4782	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d471	3c7956f3-d57a-4a01-936b-6d6cf98de665	in	5	1050.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000003	Transfer from Main Warehouse	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-10 14:00:00+00	2026-01-10 14:00:00+00	2026-01-10 14:00:00+00
f537b910-830c-4218-b001-f32624537deb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d472	cbf290a6-91cb-4c93-b9a6-db408bb3c274	out	5	38.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000003	Transfer to Retail Store	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-10 14:05:00+00	2026-01-10 14:05:00+00	2026-01-10 14:05:00+00
943d6959-3fcc-4457-b2dd-21827fc6708d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d472	3c7956f3-d57a-4a01-936b-6d6cf98de665	in	5	38.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000003	Transfer from Main Warehouse	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-10 14:05:00+00	2026-01-10 14:05:00+00	2026-01-10 14:05:00+00
c35203f9-f62f-45ec-a0c7-4068e7c12552	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d473	cbf290a6-91cb-4c93-b9a6-db408bb3c274	out	5	72.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000003	Transfer to Retail Store	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-10 14:10:00+00	2026-01-10 14:10:00+00	2026-01-10 14:10:00+00
f8c43cea-773d-4cbe-b762-7b9fed545318	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d473	3c7956f3-d57a-4a01-936b-6d6cf98de665	in	5	72.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000003	Transfer from Main Warehouse	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-10 14:10:00+00	2026-01-10 14:10:00+00	2026-01-10 14:10:00+00
c04fc23a-17a9-4165-b216-9106426cdd06	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d478	cbf290a6-91cb-4c93-b9a6-db408bb3c274	out	5	399.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000003	Transfer to Retail Store	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-10 14:15:00+00	2026-01-10 14:15:00+00	2026-01-10 14:15:00+00
41ed8c3c-7fcc-4512-8ba2-f2a9452bbebe	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d478	3c7956f3-d57a-4a01-936b-6d6cf98de665	in	5	399.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000003	Transfer from Main Warehouse	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-10 14:15:00+00	2026-01-10 14:15:00+00	2026-01-10 14:15:00+00
1de9f087-15c2-4a92-9703-e9a0f989c22b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d479	cbf290a6-91cb-4c93-b9a6-db408bb3c274	out	5	169.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000003	Transfer to Retail Store	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-10 14:20:00+00	2026-01-10 14:20:00+00	2026-01-10 14:20:00+00
f8daca71-35d9-43eb-9dc6-9a23e9c5f7b4	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d479	3c7956f3-d57a-4a01-936b-6d6cf98de665	in	5	169.00	STOCK_ENTRY	b0000001-0001-4000-a000-000000000003	Transfer from Main Warehouse	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-10 14:20:00+00	2026-01-10 14:20:00+00	2026-01-10 14:20:00+00
a4ec1be2-0c73-4819-a8fb-339104ca069e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	f47ac10b-58cc-4372-a567-0e02b2c3d472	cbf290a6-91cb-4c93-b9a6-db408bb3c274	adjustment	-1	38.00	STOCK_RECONCILIATION	c0000001-0001-4000-a000-000000000001	Physical count adjustment: 1 unit missing (damaged during handling)	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-10 14:30:00+00	2026-02-10 14:30:00+00	2026-02-10 14:30:00+00
\.


--
-- Data for Name: stock_reconciliation_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_reconciliation_items (id, organization_id, reconciliation_id, item_id, warehouse_id, current_qty, qty, qty_difference, current_valuation_rate, valuation_rate, batch_no, serial_nos, extra_data, created_at, updated_at) FROM stdin;
e348cff6-64d5-467c-81ad-528c70b993c8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	c0000001-0001-4000-a000-000000000001	f47ac10b-58cc-4372-a567-0e02b2c3d472	cbf290a6-91cb-4c93-b9a6-db408bb3c274	200.000	199.000	-1.000	38.00	38.00	\N	\N	\N	2026-02-10 14:00:00+00	2026-02-10 14:00:00+00
\.


--
-- Data for Name: stock_reconciliations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_reconciliations (id, organization_id, reconciliation_no, purpose, posting_date, posting_time, status, expense_account_id, difference_account_id, remarks, extra_data, submitted_at, created_at, updated_at, created_by, updated_by) FROM stdin;
565847ad-58a9-44c6-8cc1-a95e36531980	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RECON-2024-001	Physical Stock Count - Monthly	2026-01-25 11:59:11.034338+00	16:00:00	submitted	\N	\N	Monthly physical stock verification	null	2026-01-25 11:59:11.034338+00	2026-02-09 11:59:11.051607+00	2026-02-09 11:59:11.051608+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
46aad0ee-ed45-4b07-a2c4-1d31ca1d7392	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RECON-2024-002	Damage Write-off	2026-01-30 11:59:11.034338+00	10:30:00	submitted	\N	\N	Write-off damaged items	null	2026-01-30 11:59:11.034338+00	2026-02-09 11:59:11.052487+00	2026-02-09 11:59:11.052488+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
c0000001-0001-4000-a000-000000000001	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RECON-SEED-001	Monthly Physical Count	2026-02-10 14:00:00+00	14:00	submitted	\N	\N	February monthly physical stock count. Found 1 unit discrepancy for Optical Gaming Mouse in Main Warehouse. Likely damaged during handling.	\N	\N	2026-02-10 14:00:00+00	2026-02-10 14:30:00+00	8d509f22-5fe5-4765-9496-3a236cae2af1	\N
\.


--
-- Data for Name: stock_settings; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_settings (id, organization_id, item_naming_by, item_naming_series, stock_entry_naming_series, delivery_note_naming_series, purchase_receipt_naming_series, default_warehouse_id, allow_negative_stock, over_delivery_receipt_allowance, over_billing_allowance, auto_indent, auto_indent_notification, default_valuation_method, auto_create_serial_no, default_quality_inspection_template_id, stock_frozen_upto, stock_frozen_upto_days, show_barcode_field, convert_item_desc_to_transaction_desc, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
2d659962-46c4-4851-b53f-f91ad0130584	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	\N	\N	\N	\N	\N	\N	f	\N	\N	\N	\N	fifo	f	\N	\N	\N	t	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2025-12-01 00:00:00+00	2025-12-01 00:00:00+00
\.


--
-- Data for Name: supplier_quotes; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.supplier_quotes (id, organization_id, rfq_line_id, supplier_id, quoted_price, quoted_delivery_date, supplier_notes, extra_data, created_at, updated_at) FROM stdin;
e0000001-0001-4000-a000-000000000041	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000021	a1b2c3d4-1111-4aaa-bbbb-000000000001	410.00	2026-02-12	Can deliver in 7 business days. Bulk discount applied.	\N	2026-01-30 11:00:00+00	2026-01-30 11:00:00+00
e0000001-0001-4000-a000-000000000042	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000022	a1b2c3d4-1111-4aaa-bbbb-000000000001	165.00	2026-02-10	In stock, ready to ship. Latest model with ANC 3.0.	\N	2026-01-30 11:00:00+00	2026-01-30 11:00:00+00
e0000001-0001-4000-a000-000000000043	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000021	a1b2c3d4-1111-4aaa-bbbb-000000000002	395.00	2026-02-18	Best price for 4K monitors. 14-day lead time.	\N	2026-02-01 09:00:00+00	2026-02-01 09:00:00+00
e0000001-0001-4000-a000-000000000044	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	e0000001-0001-4000-a000-000000000022	a1b2c3d4-1111-4aaa-bbbb-000000000002	180.00	2026-02-20	Premium model. 3-year warranty included.	\N	2026-02-01 09:00:00+00	2026-02-01 09:00:00+00
\.


--
-- Data for Name: suppliers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.suppliers (id, organization_id, supplier_name, supplier_code, email, phone, address, address_line1, address_line2, city, state, postal_code, country, tax_number, status, payment_terms, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
f68137ef-49df-4ea5-8a57-fe22a0f446d2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Steel India Ltd	SUPP-001	sales@steelindia.com	+91-9812345001	\N	\N	\N	Jamshedpur	\N	\N	\N	\N	active	30	\N	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
a1b2c3d4-1111-4aaa-bbbb-000000000001	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	TechWorld Supplies	SUPP-002	orders@techworld.com	+91-9876543210	\N	42 Electronics Park	\N	Bangalore	Karnataka	\N	India	GSTIN29AABCT1234F	active	30	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2025-12-01 03:30:00+00	2025-12-01 03:30:00+00	\N
a1b2c3d4-1111-4aaa-bbbb-000000000002	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Global Electronics Co	SUPP-003	sales@globalelec.com	+91-8765432109	\N	88 Industrial Zone	\N	Chennai	Tamil Nadu	\N	India	GSTIN33AABCG5678K	active	45	\N	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	\N	2025-12-05 04:30:00+00	2025-12-05 04:30:00+00	\N
\.


--
-- Data for Name: system_config; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.system_config (key, value, updated_at, updated_by) FROM stdin;
base_currency	USD	2026-02-18 10:22:00.057705+00	system
account_code_format	^[0-9]{4}-[0-9]{2}$	2026-02-18 10:22:00.057705+00	system
\.


--
-- Data for Name: tax_rules; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.tax_rules (id, tax_template_id, rule_name, tax_type, description, tax_rate, account_head_id, is_compound, sequence, applicability_conditions, created_at, updated_at) FROM stdin;
f6a69453-93e6-46fb-b36c-303e14591bef	668321a8-31d6-4c26-9908-6e904d6a60d7	CGST	GST	\N	9.00	8d509f22-5fe5-4765-9496-3a236cae2af1	t	1	null	2026-02-16 18:15:01.851652+00	2026-02-16 18:15:01.851658+00
3fd03aee-9110-4eca-bc1f-26f875509cf5	668321a8-31d6-4c26-9908-6e904d6a60d7	SCST	GST	\N	9.00	8d509f22-5fe5-4765-9496-3a236cae2af1	t	2	null	2026-02-16 18:15:01.851664+00	2026-02-16 18:15:01.851666+00
91df80b6-607d-438e-a550-f303595733d1	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	CGST	GST	this is center GST	2.50	8d509f22-5fe5-4765-9496-3a236cae2af1	t	1	null	2026-02-18 12:57:55.157766+00	2026-02-18 12:57:55.157774+00
f6ff1732-3c4d-4b76-88f9-9a6ca30efb8f	896e1d8b-f75b-4e76-952a-2d385ee3bfa7	SGST	GST	this is state GST	2.50	8d509f22-5fe5-4765-9496-3a236cae2af1	t	2	null	2026-02-18 12:57:55.157786+00	2026-02-18 12:57:55.157787+00
8e81d666-0f58-4537-bd1c-3f7cf633364b	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a	CGST	GST	this is center GST	14.00	8d509f22-5fe5-4765-9496-3a236cae2af1	t	1	null	2026-02-18 13:12:22.248383+00	2026-02-18 13:12:22.248389+00
6bda25ea-abf5-4839-aea8-8701495576c4	3eb6cf79-0871-4b31-bd00-5d0a0086ba7a	SGST	GST	this is state GST	14.00	8d509f22-5fe5-4765-9496-3a236cae2af1	t	2	null	2026-02-18 13:12:22.248395+00	2026-02-18 13:12:22.248396+00
a46e7347-9485-45bd-aeeb-cb60a1354ba7	c30187e0-ce10-4afa-9235-eb395e978a81	CGST	CGST	\N	12.00	8d509f22-5fe5-4765-9496-3a236cae2af1	t	1	null	2026-02-18 17:28:45.427738+00	2026-02-18 17:28:45.427742+00
7227ba82-1924-4c65-85a6-ab321dd87d4b	c30187e0-ce10-4afa-9235-eb395e978a81	SGST	GST	\N	12.00	8d509f22-5fe5-4765-9496-3a236cae2af1	t	2	null	2026-02-18 17:28:45.427748+00	2026-02-18 17:28:45.427749+00
e09c7cfe-9e39-4e7d-8206-5c386d8c921e	ea4c30fb-1c2f-43ae-a92f-c0fd7798433f	CGST	GST	this is center GST	5.00	8d509f22-5fe5-4765-9496-3a236cae2af1	t	1	null	2026-02-24 05:58:16.588645+00	2026-02-24 05:58:16.588651+00
1c003c49-235c-4660-8082-6a25db90a3e8	ea4c30fb-1c2f-43ae-a92f-c0fd7798433f	SGST	GST	this is state GST	5.00	8d509f22-5fe5-4765-9496-3a236cae2af1	t	2	null	2026-02-24 05:58:16.588658+00	2026-02-24 05:58:16.588659+00
a554b194-cd9a-4ec0-a569-91acb3fa883f	ea4c30fb-1c2f-43ae-a92f-c0fd7798433f	CGreenTax	Excise	\N	2.00	8d509f22-5fe5-4765-9496-3a236cae2af1	t	3	null	2026-02-24 05:58:16.588664+00	2026-02-24 05:58:16.588665+00
8271863f-783c-478a-aedb-ab2f3a86c87e	ea4c30fb-1c2f-43ae-a92f-c0fd7798433f	SGreenTax	Excise	\N	2.00	8d509f22-5fe5-4765-9496-3a236cae2af1	t	4	null	2026-02-24 05:58:16.58867+00	2026-02-24 05:58:16.588671+00
fe3a8b21-31cb-44ab-8295-062d2d690e20	ea4c30fb-1c2f-43ae-a92f-c0fd7798433f	CUSTOM Tax	Custom	\N	14.00	8d509f22-5fe5-4765-9496-3a236cae2af1	f	5	null	2026-02-24 05:58:16.588676+00	2026-02-24 05:58:16.588677+00
\.


--
-- Data for Name: tax_templates; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.tax_templates (id, organization_id, template_code, template_name, description, tax_category, is_default, is_active, applicability_rules, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
668321a8-31d6-4c26-9908-6e904d6a60d7	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	GST_18	GST 18	18 	Output	f	t	null	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-16 18:15:01.841941+00	2026-02-16 18:15:01.841949+00	\N
896e1d8b-f75b-4e76-952a-2d385ee3bfa7	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	GST_5	GST 5$	\N	Output	f	t	null	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 12:57:55.148315+00	2026-02-18 12:57:55.148322+00	\N
3eb6cf79-0871-4b31-bd00-5d0a0086ba7a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	GST_28_OUT	GST 28% Out	28 % test	Output	f	t	null	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 13:12:22.239019+00	2026-02-18 13:12:22.239026+00	\N
c30187e0-ce10-4afa-9235-eb395e978a81	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	GST_24	GST 24% Out	out	Output	f	t	null	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-18 17:28:45.420893+00	2026-02-18 17:28:45.420899+00	\N
ea4c30fb-1c2f-43ae-a92f-c0fd7798433f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	MIX-TAX-28	MIX-28%	teste	Output	f	t	null	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-24 05:58:16.583173+00	2026-02-24 05:58:16.58318+00	\N
\.


--
-- Data for Name: transaction_charge_breakdown; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.transaction_charge_breakdown (id, organization_id, transaction_type, transaction_id, charge_template_id, charge_type, description, calculation_method, charge_amount, account_head_id, is_auto_calculated, created_at) FROM stdin;
\.


--
-- Data for Name: transaction_tax_breakdown; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.transaction_tax_breakdown (id, organization_id, transaction_type, transaction_id, tax_template_id, tax_rule_id, tax_type, tax_rate, taxable_amount, tax_amount, is_compound, sequence, account_head_id, created_at) FROM stdin;
\.


--
-- Data for Name: warehouses_extended; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.warehouses_extended (id, organization_id, name, code, description, parent_warehouse_id, warehouse_type, address_line1, address_line2, city, state, postal_code, country, contact_name, contact_phone, contact_email, total_capacity, capacity_uom, stock_account_id, is_active, is_default, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
cbf290a6-91cb-4c93-b9a6-db408bb3c274	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Main Warehouse	WH-MAIN	Primary warehouse for finished goods	\N	warehouse	123 Industrial Area	\N	Mumbai	Maharashtra	400001	India	John Smith	+91-9876543210	warehouse@example.com	\N	\N	\N	t	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
3c7956f3-d57a-4a01-936b-6d6cf98de665	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Retail Store	WH-STORE	Retail store location	\N	store	456 Market Street	\N	Mumbai	Maharashtra	400002	India	Jane Doe	+91-9876543211	store@example.com	\N	\N	\N	t	f	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
c5a6fa4d-becf-4365-a241-5b122f77dc7f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Goods in Transit	WH-TRANSIT	Virtual warehouse for goods in transit	cbf290a6-91cb-4c93-b9a6-db408bb3c274	transit	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	t	f	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
8226d8f8-ec03-48e1-a68a-3eb4c2c183d8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Test Warehouse TC010	TC010WH001	Warehouse created during test TC010	\N	warehouse	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	t	f	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-28 08:13:28.580944+00	2026-01-28 08:13:29.815515+00	2026-01-28 08:13:29.809711+00
dcb1f459-9bdd-4755-8eb4-7da7699d35df	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Max Rock Delhi	WH-MXR-01	in delhi main	\N	store	Cyber Hub	C-256, Near Shubash Park	New Ashok Nagar	Delhi	110096	India	Devendra negi	09008750492	dev@maxrockstorage.com	200	\N	\N	t	f	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-03 17:14:17.038123+00	2026-02-03 17:14:17.038136+00	\N
1e13cb16-6d79-45ba-8077-27fbe611e79f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Max Rock Rohani	WH-MXR-02	tese	\N	store	Sobha Dream Acres	Panathur Main Road, Off Orr Balagere	Bangalore Urban	Karnataka	560087	India	Devendra Negi	9711452879	devnegikec@gmail.com	100	seq	\N	t	f	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-03 17:15:26.27631+00	2026-02-03 17:15:26.276315+00	\N
3dda0807-8d63-46e4-93bc-2bff76ae7ae2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Max Rock BadalaPur	WH-MXR-03	in Badapur	\N	transit	13123, Sobha Dream Acres	Panathur Main Road, Off Orr Balagere	Bangalore Urban	Karnataka	560087	India	Devendra Negi	9711452879	devnegikec@gmail.com	50	seq	\N	t	f	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-03 17:16:23.577317+00	2026-02-03 17:16:23.577322+00	\N
a1e5f3b3-197d-433f-a0db-50237a31bb63	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Max Rock Timkur	WH-MXR-04	timkur	\N	store	Cyber Hub 1	C-256, Near Shubash Park	New Ashok Nagar	Karnataka	560089	India	Sunita Rautela	9873642880	sunitarautela3@gmail.com	40	seq	\N	t	f	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-03 17:17:35.99823+00	2026-02-03 17:17:35.99824+00	\N
7e727303-d26e-4da4-b1f0-2194f90a9821	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse C4ca4	C4CA-1	Description for warehouse 1	\N	warehouse	\N	\N	Bangalore	\N	\N	India	\N	\N	\N	3942	Units	\N	t	f	\N	\N	\N	2026-01-13 17:54:37.197228+00	2026-02-04 16:17:56.270385+00	\N
6ddeac95-fbbf-47eb-acf3-4556ea51c000	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse C81e7	C81E-2	Description for warehouse 2	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	3536	Units	\N	t	f	\N	\N	\N	2026-01-06 03:33:48.143937+00	2026-02-04 16:17:56.270385+00	\N
94e6f295-2ce0-4f3b-af6c-fb6dcb12144d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse Eccbc	ECCB-3	Description for warehouse 3	\N	store	\N	\N	New York	\N	\N	India	\N	\N	\N	9664	Units	\N	t	f	\N	\N	\N	2026-01-31 12:20:54.237147+00	2026-02-04 16:17:56.270385+00	\N
90aec083-5722-44fa-890c-52c0d7f2b7ee	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse A87ff	A87F-4	Description for warehouse 4	\N	store	\N	\N	New York	\N	\N	India	\N	\N	\N	3965	Units	\N	t	f	\N	\N	\N	2026-01-30 16:40:55.643739+00	2026-02-04 16:17:56.270385+00	\N
372dbfa1-ca4a-4dc1-a8ba-8f597d8a799a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse E4da3	E4DA-5	Description for warehouse 5	\N	store	\N	\N	New York	\N	\N	India	\N	\N	\N	7667	Units	\N	t	f	\N	\N	\N	2026-01-31 10:39:13.105864+00	2026-02-04 16:17:56.270385+00	\N
a546b3cf-5c86-4629-b9d2-add3e1ab2d35	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 16790	1679-6	Description for warehouse 6	\N	transit	\N	\N	New York	\N	\N	India	\N	\N	\N	6838	Units	\N	t	f	\N	\N	\N	2026-01-12 01:45:35.077742+00	2026-02-04 16:17:56.270385+00	\N
8f21ba61-238d-45a5-b30d-128cdc5a8d9f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 8f14e	8F14-7	Description for warehouse 7	\N	warehouse	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	7006	Units	\N	t	f	\N	\N	\N	2026-02-02 01:12:30.205866+00	2026-02-04 16:17:56.270385+00	\N
7bb53d6d-b919-42c1-a50e-5b87c7b30cfb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse C9f0f	C9F0-8	Description for warehouse 8	\N	store	\N	\N	London	\N	\N	India	\N	\N	\N	6002	Units	\N	t	f	\N	\N	\N	2026-01-06 14:03:11.781014+00	2026-02-04 16:17:56.270385+00	\N
4bf9739f-cde3-4a6b-b6dc-10b91fbba6b1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 45c48	45C4-9	Description for warehouse 9	\N	warehouse	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	6700	Units	\N	t	f	\N	\N	\N	2026-01-19 00:36:44.335455+00	2026-02-04 16:17:56.270385+00	\N
e1be3aaf-bdee-4f5d-8f93-432a7c2bdec9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse D3d94	D3D9-10	Description for warehouse 10	\N	transit	\N	\N	New York	\N	\N	India	\N	\N	\N	4172	Units	\N	t	f	\N	\N	\N	2026-01-18 23:55:28.756946+00	2026-02-04 16:17:56.270385+00	\N
607c5d3c-0931-413c-b54e-1d8693098981	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 6512b	6512-11	Description for warehouse 11	\N	transit	\N	\N	New York	\N	\N	India	\N	\N	\N	5205	Units	\N	t	f	\N	\N	\N	2026-01-19 06:41:33.337492+00	2026-02-04 16:17:56.270385+00	\N
511efedb-a800-4268-be53-e2055372c46a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse C20ad	C20A-12	Description for warehouse 12	\N	warehouse	\N	\N	London	\N	\N	India	\N	\N	\N	4706	Units	\N	t	f	\N	\N	\N	2026-01-10 17:53:57.220206+00	2026-02-04 16:17:56.270385+00	\N
eef268c0-5cf5-46c2-82e1-ff4cf24e86b4	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse C51ce	C51C-13	Description for warehouse 13	\N	warehouse	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	7227	Units	\N	t	f	\N	\N	\N	2026-01-06 06:05:11.954479+00	2026-02-04 16:17:56.270385+00	\N
70e6ff11-1039-44b1-adda-dbfe931c0cfc	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse Aab32	AAB3-14	Description for warehouse 14	\N	transit	\N	\N	New York	\N	\N	India	\N	\N	\N	5323	Units	\N	t	f	\N	\N	\N	2026-02-01 22:25:18.667928+00	2026-02-04 16:17:56.270385+00	\N
396b408f-e763-4e0a-9f1c-10cf69a92183	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 9bf31	9BF3-15	Description for warehouse 15	\N	store	\N	\N	New York	\N	\N	India	\N	\N	\N	3877	Units	\N	t	f	\N	\N	\N	2026-01-16 03:20:13.04946+00	2026-02-04 16:17:56.270385+00	\N
e340e99d-cc8a-4952-8cff-c1b13a70e601	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse C74d9	C74D-16	Description for warehouse 16	\N	warehouse	\N	\N	New York	\N	\N	India	\N	\N	\N	7212	Units	\N	t	f	\N	\N	\N	2026-01-21 06:41:22.058268+00	2026-02-04 16:17:56.270385+00	\N
2481c33c-bc72-4649-ad3e-6bdf37f8319d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 70efd	70EF-17	Description for warehouse 17	\N	store	\N	\N	London	\N	\N	India	\N	\N	\N	3958	Units	\N	t	f	\N	\N	\N	2026-01-08 09:30:25.127077+00	2026-02-04 16:17:56.270385+00	\N
1157e127-b5dc-47be-9452-ea6193f67e32	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 6f492	6F49-18	Description for warehouse 18	\N	transit	\N	\N	London	\N	\N	India	\N	\N	\N	6507	Units	\N	t	f	\N	\N	\N	2026-01-27 06:20:48.807158+00	2026-02-04 16:17:56.270385+00	\N
acbb1321-8b6f-4fdf-90fa-59be40866336	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 1f0e3	1F0E-19	Description for warehouse 19	\N	store	\N	\N	Delhi	\N	\N	India	\N	\N	\N	6876	Units	\N	t	f	\N	\N	\N	2026-01-09 14:41:19.678542+00	2026-02-04 16:17:56.270385+00	\N
633a8121-179c-44e3-a3d5-d82763bddcdc	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 98f13	98F1-20	Description for warehouse 20	\N	store	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	9177	Units	\N	t	f	\N	\N	\N	2026-01-29 06:16:50.423461+00	2026-02-04 16:17:56.270385+00	\N
cd7c498c-4842-4344-a7e9-f2327c535dc8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 3c59d	3C59-21	Description for warehouse 21	\N	transit	\N	\N	London	\N	\N	India	\N	\N	\N	9262	Units	\N	t	f	\N	\N	\N	2026-01-27 02:30:42.340724+00	2026-02-04 16:17:56.270385+00	\N
a009830b-456f-475c-949d-d181e8bec045	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse B6d76	B6D7-22	Description for warehouse 22	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	4954	Units	\N	t	f	\N	\N	\N	2026-01-30 06:23:01.226072+00	2026-02-04 16:17:56.270385+00	\N
164e1ebd-4e3b-433a-9680-c57240683016	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 37693	3769-23	Description for warehouse 23	\N	transit	\N	\N	London	\N	\N	India	\N	\N	\N	1260	Units	\N	t	f	\N	\N	\N	2026-02-04 11:07:31.460144+00	2026-02-04 16:17:56.270385+00	\N
eabb4a85-11cf-42d3-b683-3a4a84d49cad	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 1ff1d	1FF1-24	Description for warehouse 24	\N	store	\N	\N	Delhi	\N	\N	India	\N	\N	\N	4453	Units	\N	t	f	\N	\N	\N	2026-02-02 00:31:42.165687+00	2026-02-04 16:17:56.270385+00	\N
972cd241-f10b-4629-b3e8-5383e087b1eb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 8e296	8E29-25	Description for warehouse 25	\N	store	\N	\N	London	\N	\N	India	\N	\N	\N	1391	Units	\N	t	f	\N	\N	\N	2026-01-31 14:59:51.926084+00	2026-02-04 16:17:56.270385+00	\N
abb6b5bc-9898-43f4-a543-5a7dcaa6c730	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 4e732	4E73-26	Description for warehouse 26	\N	store	\N	\N	Bangalore	\N	\N	India	\N	\N	\N	3986	Units	\N	t	f	\N	\N	\N	2026-01-19 11:43:37.038216+00	2026-02-04 16:17:56.270385+00	\N
e76e604c-8a5b-4c61-8c24-8c37601327aa	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 02e74	02E7-27	Description for warehouse 27	\N	transit	\N	\N	New York	\N	\N	India	\N	\N	\N	5321	Units	\N	t	f	\N	\N	\N	2026-01-06 15:07:58.031332+00	2026-02-04 16:17:56.270385+00	\N
9d274302-fe85-4e8c-b55f-a6417e177e11	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 33e75	33E7-28	Description for warehouse 28	\N	warehouse	\N	\N	London	\N	\N	India	\N	\N	\N	4372	Units	\N	t	f	\N	\N	\N	2026-01-11 17:37:05.82194+00	2026-02-04 16:17:56.270385+00	\N
a79fef85-24c9-43cf-9759-b365d96a5646	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 6ea9a	6EA9-29	Description for warehouse 29	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	5344	Units	\N	t	f	\N	\N	\N	2026-01-27 17:25:27.149288+00	2026-02-04 16:17:56.270385+00	\N
d5a5fe0f-99c4-4240-af9f-ad264ac9db98	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 34173	3417-30	Description for warehouse 30	\N	store	\N	\N	New York	\N	\N	India	\N	\N	\N	4449	Units	\N	t	f	\N	\N	\N	2026-01-13 04:16:54.855464+00	2026-02-04 16:17:56.270385+00	\N
1f5fbd06-c493-4987-8843-4f443f017953	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse C16a5	C16A-31	Description for warehouse 31	\N	warehouse	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	2044	Units	\N	t	f	\N	\N	\N	2026-01-11 11:51:26.17328+00	2026-02-04 16:17:56.270385+00	\N
d9d697c9-14ca-4983-a8b9-9513a5ac6d3e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 6364d	6364-32	Description for warehouse 32	\N	store	\N	\N	Delhi	\N	\N	India	\N	\N	\N	4033	Units	\N	t	f	\N	\N	\N	2026-01-15 04:00:42.674865+00	2026-02-04 16:17:56.270385+00	\N
56ede201-cfbf-408e-9250-c0cf8d02fd92	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 182be	182B-33	Description for warehouse 33	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	9662	Units	\N	t	f	\N	\N	\N	2026-01-06 01:45:20.172381+00	2026-02-04 16:17:56.270385+00	\N
6d3f2a9c-dd2a-4182-a39c-542a06c987c6	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse E3698	E369-34	Description for warehouse 34	\N	warehouse	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	5709	Units	\N	t	f	\N	\N	\N	2026-01-18 06:55:11.610273+00	2026-02-04 16:17:56.270385+00	\N
70ccd75b-9cdc-481b-93ea-e7dcec767d36	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 1c383	1C38-35	Description for warehouse 35	\N	warehouse	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	7056	Units	\N	t	f	\N	\N	\N	2026-01-14 12:01:07.540873+00	2026-02-04 16:17:56.270385+00	\N
504e646f-16be-4bba-b903-6a28e2730db2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 19ca1	19CA-36	Description for warehouse 36	\N	warehouse	\N	\N	London	\N	\N	India	\N	\N	\N	1779	Units	\N	t	f	\N	\N	\N	2026-02-04 14:08:10.542798+00	2026-02-04 16:17:56.270385+00	\N
324b0149-523a-46a9-847d-eb9bfcc9ab38	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse A5bfc	A5BF-37	Description for warehouse 37	\N	store	\N	\N	London	\N	\N	India	\N	\N	\N	2389	Units	\N	t	f	\N	\N	\N	2026-01-24 17:11:28.626513+00	2026-02-04 16:17:56.270385+00	\N
6bc73ace-6b58-498f-b6f0-d854c799d21d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse A5771	A577-38	Description for warehouse 38	\N	warehouse	\N	\N	New York	\N	\N	India	\N	\N	\N	7526	Units	\N	t	f	\N	\N	\N	2026-01-10 15:14:10.435142+00	2026-02-04 16:17:56.270385+00	\N
cd240717-8577-4d42-a60e-c778ef358fff	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse D67d8	D67D-39	Description for warehouse 39	\N	store	\N	\N	New York	\N	\N	India	\N	\N	\N	9811	Units	\N	t	f	\N	\N	\N	2026-01-25 00:56:23.382337+00	2026-02-04 16:17:56.270385+00	\N
37785eff-fdeb-418e-b3ee-60d51f41e304	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse D6459	D645-40	Description for warehouse 40	\N	store	\N	\N	Delhi	\N	\N	India	\N	\N	\N	4367	Units	\N	t	f	\N	\N	\N	2026-01-11 16:14:36.751409+00	2026-02-04 16:17:56.270385+00	\N
ba0855fc-3515-45da-8870-3ee40f249a34	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse A1d0c	A1D0-42	Description for warehouse 42	\N	transit	\N	\N	Bangalore	\N	\N	India	\N	\N	\N	5062	Units	\N	t	f	\N	\N	\N	2026-02-03 02:00:38.177385+00	2026-02-04 16:17:56.270385+00	\N
1b74f07f-38a9-49f6-adf2-cc9c17a24b1d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 17e62	17E6-43	Description for warehouse 43	\N	store	\N	\N	Bangalore	\N	\N	India	\N	\N	\N	1098	Units	\N	t	f	\N	\N	\N	2026-01-30 03:54:08.464706+00	2026-02-04 16:17:56.270385+00	\N
f62e7c98-6116-45d8-8d39-c2ceefdda060	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse F7177	F717-44	Description for warehouse 44	\N	store	\N	\N	New York	\N	\N	India	\N	\N	\N	4365	Units	\N	t	f	\N	\N	\N	2026-01-30 10:55:51.924735+00	2026-02-04 16:17:56.270385+00	\N
b1bdf065-d4b1-4dc6-93ec-9ccbf5935a75	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 6c834	6C83-45	Description for warehouse 45	\N	warehouse	\N	\N	London	\N	\N	India	\N	\N	\N	1347	Units	\N	t	f	\N	\N	\N	2026-01-31 09:08:25.217494+00	2026-02-04 16:17:56.270385+00	\N
6dfd2911-477c-4d5a-85e9-6935b9e84cbb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse D9d4f	D9D4-46	Description for warehouse 46	\N	store	\N	\N	New York	\N	\N	India	\N	\N	\N	1537	Units	\N	t	f	\N	\N	\N	2026-01-26 07:12:42.961911+00	2026-02-04 16:17:56.270385+00	\N
6c32480b-af53-4b44-b8ec-4530d264b470	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 67c6a	67C6-47	Description for warehouse 47	\N	transit	\N	\N	Delhi	\N	\N	India	\N	\N	\N	7878	Units	\N	t	f	\N	\N	\N	2026-02-02 21:13:49.869416+00	2026-02-04 16:17:56.270385+00	\N
399494ed-0f71-45f9-aebe-dc457a86dfe2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 642e9	642E-48	Description for warehouse 48	\N	warehouse	\N	\N	New York	\N	\N	India	\N	\N	\N	5020	Units	\N	t	f	\N	\N	\N	2026-02-02 05:32:39.647618+00	2026-02-04 16:17:56.270385+00	\N
879ee02c-c3f6-449a-97af-a23e4d66e3fc	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse F457c	F457-49	Description for warehouse 49	\N	warehouse	\N	\N	London	\N	\N	India	\N	\N	\N	8452	Units	\N	t	f	\N	\N	\N	2026-02-03 00:30:34.456712+00	2026-02-04 16:17:56.270385+00	\N
d9788ffb-19df-4f49-b386-995e4ad2a9e2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse C0c7c	C0C7-50	Description for warehouse 50	\N	store	\N	\N	New York	\N	\N	India	\N	\N	\N	9789	Units	\N	t	f	\N	\N	\N	2026-01-19 12:27:23.359203+00	2026-02-04 16:17:56.270385+00	\N
260e057a-895a-4dbc-8678-670ba7b805cc	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 28380	2838-51	Description for warehouse 51	\N	store	\N	\N	Delhi	\N	\N	India	\N	\N	\N	2715	Units	\N	t	f	\N	\N	\N	2026-02-03 03:42:19.685504+00	2026-02-04 16:17:56.270385+00	\N
73443251-d1e3-4ee9-bb6c-9032408e1154	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 9a115	9A11-52	Description for warehouse 52	\N	warehouse	\N	\N	New York	\N	\N	India	\N	\N	\N	6975	Units	\N	t	f	\N	\N	\N	2026-01-31 01:14:42.015653+00	2026-02-04 16:17:56.270385+00	\N
23cf7277-b13d-48f3-8737-b9dd755d30c1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse D82c8	D82C-53	Description for warehouse 53	\N	store	\N	\N	New York	\N	\N	India	\N	\N	\N	5480	Units	\N	t	f	\N	\N	\N	2026-01-26 10:51:28.394521+00	2026-02-04 16:17:56.270385+00	\N
95bd33b4-9b35-4574-a325-58d77d7f863b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse A684e	A684-54	Description for warehouse 54	\N	warehouse	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	4223	Units	\N	t	f	\N	\N	\N	2026-02-01 23:35:52.771252+00	2026-02-04 16:17:56.270385+00	\N
8b1e2182-453e-4a6b-831d-7443a0ed0c83	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse B53b3	B53B-55	Description for warehouse 55	\N	warehouse	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	1387	Units	\N	t	f	\N	\N	\N	2026-01-18 11:29:24.919837+00	2026-02-04 16:17:56.270385+00	\N
10b1d067-b44d-4182-8af5-38ec8f497b46	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 9f614	9F61-56	Description for warehouse 56	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	5163	Units	\N	t	f	\N	\N	\N	2026-01-08 09:21:28.533129+00	2026-02-04 16:17:56.270385+00	\N
95258f70-c69c-43f1-a7f2-83170b0f1ecc	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 72b32	72B3-57	Description for warehouse 57	\N	warehouse	\N	\N	London	\N	\N	India	\N	\N	\N	2212	Units	\N	t	f	\N	\N	\N	2026-02-01 11:57:10.05508+00	2026-02-04 16:17:56.270385+00	\N
a55da4e1-a6f6-4f2d-be34-dfa262dbcc6e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 66f04	66F0-58	Description for warehouse 58	\N	store	\N	\N	London	\N	\N	India	\N	\N	\N	6889	Units	\N	t	f	\N	\N	\N	2026-01-25 23:23:48.548414+00	2026-02-04 16:17:56.270385+00	\N
05ef5516-9eef-4867-b86e-2e4942520294	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 093f6	093F-59	Description for warehouse 59	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	7012	Units	\N	t	f	\N	\N	\N	2026-02-01 12:26:31.715322+00	2026-02-04 16:17:56.270385+00	\N
05cd5c93-f102-45b9-bbf7-60cc491d5cd0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 072b0	072B-60	Description for warehouse 60	\N	warehouse	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	6238	Units	\N	t	f	\N	\N	\N	2026-01-26 08:35:33.730725+00	2026-02-04 16:17:56.270385+00	\N
cb613a3a-8837-44c9-a209-1c8ba7012e58	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 7f39f	7F39-61	Description for warehouse 61	\N	warehouse	\N	\N	New York	\N	\N	India	\N	\N	\N	1176	Units	\N	t	f	\N	\N	\N	2026-01-15 07:16:34.985425+00	2026-02-04 16:17:56.270385+00	\N
c54d35a9-d161-4681-b160-671d917f158e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 44f68	44F6-62	Description for warehouse 62	\N	warehouse	\N	\N	New York	\N	\N	India	\N	\N	\N	4777	Units	\N	t	f	\N	\N	\N	2026-01-11 19:47:34.089215+00	2026-02-04 16:17:56.270385+00	\N
ac7b2e2d-7196-4115-a880-f7f5b242c98d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 03afd	03AF-63	Description for warehouse 63	\N	transit	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	5951	Units	\N	t	f	\N	\N	\N	2026-01-30 18:28:42.131172+00	2026-02-04 16:17:56.270385+00	\N
a18b5bca-581d-4ce1-a609-e7a69e4bd86c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse Ea5d2	EA5D-64	Description for warehouse 64	\N	transit	\N	\N	Delhi	\N	\N	India	\N	\N	\N	5223	Units	\N	t	f	\N	\N	\N	2026-01-17 08:21:24.060948+00	2026-02-04 16:17:56.270385+00	\N
36b39908-fa42-43ff-9738-74049b87c921	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse Fc490	FC49-65	Description for warehouse 65	\N	transit	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	4477	Units	\N	t	f	\N	\N	\N	2026-01-30 11:43:02.032932+00	2026-02-04 16:17:56.270385+00	\N
c7d91ac3-74ba-4c0d-9926-cf0bf4d4e83d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 3295c	3295-66	Description for warehouse 66	\N	store	\N	\N	London	\N	\N	India	\N	\N	\N	6819	Units	\N	t	f	\N	\N	\N	2026-01-13 20:58:48.101681+00	2026-02-04 16:17:56.270385+00	\N
960feb2f-867f-4c39-8bbd-de4e161b7b1e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 735b9	735B-67	Description for warehouse 67	\N	warehouse	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	8977	Units	\N	t	f	\N	\N	\N	2026-01-15 08:05:11.37378+00	2026-02-04 16:17:56.270385+00	\N
1763f3be-b925-4dbd-9c52-bf069fd40df1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse A3f39	A3F3-68	Description for warehouse 68	\N	transit	\N	\N	Bangalore	\N	\N	India	\N	\N	\N	2189	Units	\N	t	f	\N	\N	\N	2026-01-18 06:34:10.658233+00	2026-02-04 16:17:56.270385+00	\N
838fb1dc-4dc2-4dfa-a495-7e0161396f5c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 14bfa	14BF-69	Description for warehouse 69	\N	warehouse	\N	\N	Bangalore	\N	\N	India	\N	\N	\N	9099	Units	\N	t	f	\N	\N	\N	2026-01-17 09:37:16.375722+00	2026-02-04 16:17:56.270385+00	\N
8b008cd0-3b7b-4dbc-840d-d3a393547528	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 7cbbc	7CBB-70	Description for warehouse 70	\N	warehouse	\N	\N	London	\N	\N	India	\N	\N	\N	1666	Units	\N	t	f	\N	\N	\N	2026-01-20 16:31:37.463337+00	2026-02-04 16:17:56.270385+00	\N
7ed83d5a-55eb-4394-b03e-4a2b8046c1c2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse E2c42	E2C4-71	Description for warehouse 71	\N	transit	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	2170	Units	\N	t	f	\N	\N	\N	2026-01-06 17:08:00.624492+00	2026-02-04 16:17:56.270385+00	\N
bdecd3d2-83d8-4c73-b231-cc12fed9c894	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 32bb9	32BB-72	Description for warehouse 72	\N	warehouse	\N	\N	New York	\N	\N	India	\N	\N	\N	9936	Units	\N	t	f	\N	\N	\N	2026-01-23 03:27:17.95407+00	2026-02-04 16:17:56.270385+00	\N
5b12cdff-fe1c-4277-a57a-ed6732efde8c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse D2dde	D2DD-73	Description for warehouse 73	\N	transit	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	9412	Units	\N	t	f	\N	\N	\N	2026-01-08 16:13:40.355833+00	2026-02-04 16:17:56.270385+00	\N
3dd59b12-2354-4a51-84c4-2b66e5e609de	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse Ad61a	AD61-74	Description for warehouse 74	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	4832	Units	\N	t	f	\N	\N	\N	2026-01-18 18:19:33.20147+00	2026-02-04 16:17:56.270385+00	\N
e0ee74a5-0391-4e75-ac2c-757cdb8a6b3c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse D09bf	D09B-75	Description for warehouse 75	\N	transit	\N	\N	London	\N	\N	India	\N	\N	\N	4848	Units	\N	t	f	\N	\N	\N	2026-01-24 00:07:04.646936+00	2026-02-04 16:17:56.270385+00	\N
84482f05-d070-4627-a78c-4afc7f86d9fc	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse Fbd79	FBD7-76	Description for warehouse 76	\N	warehouse	\N	\N	London	\N	\N	India	\N	\N	\N	4049	Units	\N	t	f	\N	\N	\N	2026-01-29 00:03:32.930325+00	2026-02-04 16:17:56.270385+00	\N
2551264e-5810-4044-a19b-0a53203d6e79	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 28dd2	28DD-77	Description for warehouse 77	\N	transit	\N	\N	Delhi	\N	\N	India	\N	\N	\N	8112	Units	\N	t	f	\N	\N	\N	2026-01-12 10:52:45.573216+00	2026-02-04 16:17:56.270385+00	\N
1dbbea76-de41-446b-8287-10641983e891	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 35f4a	35F4-78	Description for warehouse 78	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	6901	Units	\N	t	f	\N	\N	\N	2026-01-14 04:42:26.901442+00	2026-02-04 16:17:56.270385+00	\N
fcd9fc0e-57c9-46b8-9eee-16f0dfe09d6f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse D1fe1	D1FE-79	Description for warehouse 79	\N	store	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	8684	Units	\N	t	f	\N	\N	\N	2026-01-07 02:18:14.101077+00	2026-02-04 16:17:56.270385+00	\N
d46630df-c3c7-44bc-a5c1-7d983e1112e2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse F033a	F033-80	Description for warehouse 80	\N	warehouse	\N	\N	Bangalore	\N	\N	India	\N	\N	\N	6369	Units	\N	t	f	\N	\N	\N	2026-02-04 12:53:32.996015+00	2026-02-04 16:17:56.270385+00	\N
8d1de676-f4ec-4448-b91d-eb4b71f1f0eb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 43ec5	43EC-81	Description for warehouse 81	\N	store	\N	\N	Delhi	\N	\N	India	\N	\N	\N	7390	Units	\N	t	f	\N	\N	\N	2026-01-15 20:52:57.415219+00	2026-02-04 16:17:56.270385+00	\N
24eed4c9-ba44-4289-a524-412a1787a1a4	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 9778d	9778-82	Description for warehouse 82	\N	transit	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	8371	Units	\N	t	f	\N	\N	\N	2026-01-11 15:50:12.829374+00	2026-02-04 16:17:56.270385+00	\N
6d403b06-8fe8-4271-b404-07f03407bc8c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse Fe9fc	FE9F-83	Description for warehouse 83	\N	warehouse	\N	\N	London	\N	\N	India	\N	\N	\N	8098	Units	\N	t	f	\N	\N	\N	2026-01-27 19:59:50.631741+00	2026-02-04 16:17:56.270385+00	\N
6eab0f9c-07f6-4783-8269-f9275c2a34b9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 68d30	68D3-84	Description for warehouse 84	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	3202	Units	\N	t	f	\N	\N	\N	2026-02-03 10:47:27.567+00	2026-02-04 16:17:56.270385+00	\N
925a1153-0438-428e-9e30-11cc3552bbd3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 3ef81	3EF8-85	Description for warehouse 85	\N	transit	\N	\N	Delhi	\N	\N	India	\N	\N	\N	8479	Units	\N	t	f	\N	\N	\N	2026-01-26 20:56:48.971173+00	2026-02-04 16:17:56.270385+00	\N
5aba7055-d8b1-4937-bb7b-e4692ba0335d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 93db8	93DB-86	Description for warehouse 86	\N	store	\N	\N	Delhi	\N	\N	India	\N	\N	\N	9017	Units	\N	t	f	\N	\N	\N	2026-01-14 01:25:44.359383+00	2026-02-04 16:17:56.270385+00	\N
b292ec95-ce41-4841-a4d8-e0e9654eae1e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse C7e12	C7E1-87	Description for warehouse 87	\N	transit	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	2533	Units	\N	t	f	\N	\N	\N	2026-01-23 11:16:37.68425+00	2026-02-04 16:17:56.270385+00	\N
c12530e0-cf66-4aaf-af68-12e3b9aff9e3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 2a38a	2A38-88	Description for warehouse 88	\N	transit	\N	\N	Delhi	\N	\N	India	\N	\N	\N	1696	Units	\N	t	f	\N	\N	\N	2026-01-21 09:26:14.271447+00	2026-02-04 16:17:56.270385+00	\N
3d208a8d-2af6-4b5a-9ab1-dff4e8a20cc5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 76479	7647-89	Description for warehouse 89	\N	warehouse	\N	\N	London	\N	\N	India	\N	\N	\N	3560	Units	\N	t	f	\N	\N	\N	2026-01-30 15:10:50.650253+00	2026-02-04 16:17:56.270385+00	\N
3f610919-bcc6-4456-905d-cb02fe0b7c99	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 86139	8613-90	Description for warehouse 90	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	8567	Units	\N	t	f	\N	\N	\N	2026-01-27 01:55:53.117667+00	2026-02-04 16:17:56.270385+00	\N
f47e9d5a-11de-4ff2-818c-d574b0f991e1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 54229	5422-91	Description for warehouse 91	\N	warehouse	\N	\N	Bangalore	\N	\N	India	\N	\N	\N	9356	Units	\N	t	f	\N	\N	\N	2026-01-22 19:29:00.785848+00	2026-02-04 16:17:56.270385+00	\N
435bd9e2-a197-491d-8a99-341a7929186a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 92cc2	92CC-92	Description for warehouse 92	\N	store	\N	\N	Bangalore	\N	\N	India	\N	\N	\N	3722	Units	\N	t	f	\N	\N	\N	2026-01-10 20:40:24.002341+00	2026-02-04 16:17:56.270385+00	\N
98376d19-3a4a-4044-86c4-f85b6cdd4e8f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 98dce	98DC-93	Description for warehouse 93	\N	transit	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	7761	Units	\N	t	f	\N	\N	\N	2026-01-29 15:50:57.990744+00	2026-02-04 16:17:56.270385+00	\N
f0289a52-c2b7-4070-995e-c38a119b8d6a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse F4b9e	F4B9-94	Description for warehouse 94	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	2737	Units	\N	t	f	\N	\N	\N	2026-01-30 19:02:35.664241+00	2026-02-04 16:17:56.270385+00	\N
a76406ee-8679-4836-b7a8-4b783db22a4a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 812b4	812B-95	Description for warehouse 95	\N	transit	\N	\N	London	\N	\N	India	\N	\N	\N	9126	Units	\N	t	f	\N	\N	\N	2026-01-19 23:26:25.288723+00	2026-02-04 16:17:56.270385+00	\N
6fab76f6-c7d4-404e-b810-d5593939b52f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 26657	2665-96	Description for warehouse 96	\N	store	\N	\N	Delhi	\N	\N	India	\N	\N	\N	6835	Units	\N	t	f	\N	\N	\N	2026-01-13 12:45:43.531191+00	2026-02-04 16:17:56.270385+00	\N
75129520-af94-4126-88ad-ff7ce67d07af	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse E2ef5	E2EF-97	Description for warehouse 97	\N	transit	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	5446	Units	\N	t	f	\N	\N	\N	2026-01-08 17:13:34.058852+00	2026-02-04 16:17:56.270385+00	\N
b308b7e5-cd9c-4c7e-a8fd-8b44334956d2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse Ed3d2	ED3D-98	Description for warehouse 98	\N	store	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	3542	Units	\N	t	f	\N	\N	\N	2026-01-29 06:54:03.277258+00	2026-02-04 16:17:56.270385+00	\N
564b1dfd-1608-4814-a8c7-f00eca757d7f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse Ac627	AC62-99	Description for warehouse 99	\N	store	\N	\N	Mumbai	\N	\N	India	\N	\N	\N	7289	Units	\N	t	f	\N	\N	\N	2026-01-16 11:30:21.835521+00	2026-02-04 16:17:56.270385+00	\N
58d158ab-36fa-4ac8-a5b3-dfecf6c3d4d2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse F8991	F899-100	Description for warehouse 100	\N	warehouse	\N	\N	New York	\N	\N	India	\N	\N	\N	6237	Units	\N	t	f	\N	\N	\N	2026-01-28 05:44:05.760938+00	2026-02-04 16:17:56.270385+00	\N
e67a7363-7e48-4890-854b-605ef3e43c8b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 3416a	3416-41	Description for warehouse 41	\N	warehouse	13123, Sobha Dream Acres	Varthur	Delhi	Karnataka	560087	India	devendra negi	09008750492	\N	1713	Units	\N	t	f	\N	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-04 13:18:07.734555+00	2026-02-18 16:45:21.522327+00	\N
\.


--
-- Name: receipt_seq_2025; Type: SEQUENCE SET; Schema: public; Owner: horizon_user
--

SELECT pg_catalog.setval('public.receipt_seq_2025', 1, false);


--
-- Name: receipt_seq_2026; Type: SEQUENCE SET; Schema: public; Owner: horizon_user
--

SELECT pg_catalog.setval('public.receipt_seq_2026', 1, false);


--
-- Name: account_audit_log account_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.account_audit_log
    ADD CONSTRAINT account_audit_log_pkey PRIMARY KEY (id);


--
-- Name: account_balances account_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.account_balances
    ADD CONSTRAINT account_balances_pkey PRIMARY KEY (id);


--
-- Name: accounts accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: batches batches_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_pkey PRIMARY KEY (id);


--
-- Name: charge_templates charge_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.charge_templates
    ADD CONSTRAINT charge_templates_pkey PRIMARY KEY (id);


--
-- Name: chart_of_accounts chart_of_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.chart_of_accounts
    ADD CONSTRAINT chart_of_accounts_pkey PRIMARY KEY (id);


--
-- Name: communication_logs communication_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.communication_logs
    ADD CONSTRAINT communication_logs_pkey PRIMARY KEY (id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


--
-- Name: default_accounts default_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.default_accounts
    ADD CONSTRAINT default_accounts_pkey PRIMARY KEY (id);


--
-- Name: delivery_note_items delivery_note_items_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.delivery_note_items
    ADD CONSTRAINT delivery_note_items_pkey PRIMARY KEY (id);


--
-- Name: delivery_notes delivery_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.delivery_notes
    ADD CONSTRAINT delivery_notes_pkey PRIMARY KEY (id);


--
-- Name: document_numbering_config document_numbering_config_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.document_numbering_config
    ADD CONSTRAINT document_numbering_config_pkey PRIMARY KEY (id);


--
-- Name: document_sequence_counter document_sequence_counter_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.document_sequence_counter
    ADD CONSTRAINT document_sequence_counter_pkey PRIMARY KEY (id);


--
-- Name: exchange_rates exchange_rates_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.exchange_rates
    ADD CONSTRAINT exchange_rates_pkey PRIMARY KEY (id);


--
-- Name: invoice_items invoice_items_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
-- Name: item_groups item_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.item_groups
    ADD CONSTRAINT item_groups_pkey PRIMARY KEY (id);


--
-- Name: item_prices item_prices_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.item_prices
    ADD CONSTRAINT item_prices_pkey PRIMARY KEY (id);


--
-- Name: item_suppliers item_suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.item_suppliers
    ADD CONSTRAINT item_suppliers_pkey PRIMARY KEY (id);


--
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


--
-- Name: journal_entries journal_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.journal_entries
    ADD CONSTRAINT journal_entries_pkey PRIMARY KEY (id);


--
-- Name: journal_entry_lines journal_entry_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.journal_entry_lines
    ADD CONSTRAINT journal_entry_lines_pkey PRIMARY KEY (id);


--
-- Name: landed_cost_items landed_cost_items_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.landed_cost_items
    ADD CONSTRAINT landed_cost_items_pkey PRIMARY KEY (id);


--
-- Name: landed_cost_purchase_receipts landed_cost_purchase_receipts_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.landed_cost_purchase_receipts
    ADD CONSTRAINT landed_cost_purchase_receipts_pkey PRIMARY KEY (id);


--
-- Name: landed_cost_taxes_and_charges landed_cost_taxes_and_charges_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.landed_cost_taxes_and_charges
    ADD CONSTRAINT landed_cost_taxes_and_charges_pkey PRIMARY KEY (id);


--
-- Name: landed_cost_vouchers landed_cost_vouchers_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.landed_cost_vouchers
    ADD CONSTRAINT landed_cost_vouchers_pkey PRIMARY KEY (id);


--
-- Name: material_request_lines material_request_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.material_request_lines
    ADD CONSTRAINT material_request_lines_pkey PRIMARY KEY (id);


--
-- Name: material_requests material_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.material_requests
    ADD CONSTRAINT material_requests_pkey PRIMARY KEY (id);


--
-- Name: organization_settings organization_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.organization_settings
    ADD CONSTRAINT organization_settings_pkey PRIMARY KEY (id);


--
-- Name: payment_allocations payment_allocations_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.payment_allocations
    ADD CONSTRAINT payment_allocations_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: pick_list_items pick_list_items_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.pick_list_items
    ADD CONSTRAINT pick_list_items_pkey PRIMARY KEY (id);


--
-- Name: pick_lists pick_lists_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.pick_lists
    ADD CONSTRAINT pick_lists_pkey PRIMARY KEY (id);


--
-- Name: purchase_order_lines purchase_order_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_pkey PRIMARY KEY (id);


--
-- Name: purchase_orders purchase_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_orders
    ADD CONSTRAINT purchase_orders_pkey PRIMARY KEY (id);


--
-- Name: purchase_receipt_items purchase_receipt_items_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipt_items
    ADD CONSTRAINT purchase_receipt_items_pkey PRIMARY KEY (id);


--
-- Name: purchase_receipts purchase_receipts_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipts
    ADD CONSTRAINT purchase_receipts_pkey PRIMARY KEY (id);


--
-- Name: put_away_rules put_away_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.put_away_rules
    ADD CONSTRAINT put_away_rules_pkey PRIMARY KEY (id);


--
-- Name: quotation_items quotation_items_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT quotation_items_pkey PRIMARY KEY (id);


--
-- Name: quotations quotations_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_pkey PRIMARY KEY (id);


--
-- Name: rfq_lines rfq_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.rfq_lines
    ADD CONSTRAINT rfq_lines_pkey PRIMARY KEY (id);


--
-- Name: rfq_suppliers rfq_suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.rfq_suppliers
    ADD CONSTRAINT rfq_suppliers_pkey PRIMARY KEY (id);


--
-- Name: rfqs rfqs_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.rfqs
    ADD CONSTRAINT rfqs_pkey PRIMARY KEY (id);


--
-- Name: sales_order_items sales_order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.sales_order_items
    ADD CONSTRAINT sales_order_items_pkey PRIMARY KEY (id);


--
-- Name: sales_orders sales_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.sales_orders
    ADD CONSTRAINT sales_orders_pkey PRIMARY KEY (id);


--
-- Name: serial_no_history serial_no_history_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.serial_no_history
    ADD CONSTRAINT serial_no_history_pkey PRIMARY KEY (id);


--
-- Name: serial_nos serial_nos_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.serial_nos
    ADD CONSTRAINT serial_nos_pkey PRIMARY KEY (id);


--
-- Name: status_transitions status_transitions_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.status_transitions
    ADD CONSTRAINT status_transitions_pkey PRIMARY KEY (id);


--
-- Name: stock_entries stock_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_entries
    ADD CONSTRAINT stock_entries_pkey PRIMARY KEY (id);


--
-- Name: stock_entry_items stock_entry_items_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_entry_items
    ADD CONSTRAINT stock_entry_items_pkey PRIMARY KEY (id);


--
-- Name: stock_levels stock_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_levels
    ADD CONSTRAINT stock_levels_pkey PRIMARY KEY (id);


--
-- Name: stock_movements stock_movements_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_movements
    ADD CONSTRAINT stock_movements_pkey PRIMARY KEY (id);


--
-- Name: stock_reconciliation_items stock_reconciliation_items_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_reconciliation_items
    ADD CONSTRAINT stock_reconciliation_items_pkey PRIMARY KEY (id);


--
-- Name: stock_reconciliations stock_reconciliations_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_reconciliations
    ADD CONSTRAINT stock_reconciliations_pkey PRIMARY KEY (id);


--
-- Name: stock_settings stock_settings_organization_id_key; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_settings
    ADD CONSTRAINT stock_settings_organization_id_key UNIQUE (organization_id);


--
-- Name: stock_settings stock_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_settings
    ADD CONSTRAINT stock_settings_pkey PRIMARY KEY (id);


--
-- Name: supplier_quotes supplier_quotes_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.supplier_quotes
    ADD CONSTRAINT supplier_quotes_pkey PRIMARY KEY (id);


--
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (id);


--
-- Name: system_config system_config_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.system_config
    ADD CONSTRAINT system_config_pkey PRIMARY KEY (key);


--
-- Name: tax_rules tax_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.tax_rules
    ADD CONSTRAINT tax_rules_pkey PRIMARY KEY (id);


--
-- Name: tax_templates tax_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.tax_templates
    ADD CONSTRAINT tax_templates_pkey PRIMARY KEY (id);


--
-- Name: transaction_charge_breakdown transaction_charge_breakdown_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.transaction_charge_breakdown
    ADD CONSTRAINT transaction_charge_breakdown_pkey PRIMARY KEY (id);


--
-- Name: transaction_tax_breakdown transaction_tax_breakdown_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.transaction_tax_breakdown
    ADD CONSTRAINT transaction_tax_breakdown_pkey PRIMARY KEY (id);


--
-- Name: supplier_quotes unique_quote; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.supplier_quotes
    ADD CONSTRAINT unique_quote UNIQUE (rfq_line_id, supplier_id);


--
-- Name: rfq_suppliers unique_rfq_supplier; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.rfq_suppliers
    ADD CONSTRAINT unique_rfq_supplier UNIQUE (rfq_id, supplier_id);


--
-- Name: account_balances uq_account_balances_account_date; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.account_balances
    ADD CONSTRAINT uq_account_balances_account_date UNIQUE (account_id, as_of_date);


--
-- Name: accounts uq_accounts_organization_account_code; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT uq_accounts_organization_account_code UNIQUE (organization_id, account_code);


--
-- Name: chart_of_accounts uq_chart_of_accounts_org_code; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.chart_of_accounts
    ADD CONSTRAINT uq_chart_of_accounts_org_code UNIQUE (organization_id, account_code);


--
-- Name: customers uq_customers_org_code; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT uq_customers_org_code UNIQUE (organization_id, customer_code);


--
-- Name: default_accounts uq_default_accounts_org_type_scenario; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.default_accounts
    ADD CONSTRAINT uq_default_accounts_org_type_scenario UNIQUE (organization_id, transaction_type, scenario);


--
-- Name: document_numbering_config uq_doc_numbering_org_type; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.document_numbering_config
    ADD CONSTRAINT uq_doc_numbering_org_type UNIQUE (organization_id, document_type);


--
-- Name: document_sequence_counter uq_doc_sequence_org_type_year; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.document_sequence_counter
    ADD CONSTRAINT uq_doc_sequence_org_type_year UNIQUE (organization_id, document_type, sequence_year);


--
-- Name: exchange_rates uq_exchange_rate_currency_date; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.exchange_rates
    ADD CONSTRAINT uq_exchange_rate_currency_date UNIQUE (from_currency, to_currency, effective_date);


--
-- Name: item_groups uq_item_groups_org_code; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.item_groups
    ADD CONSTRAINT uq_item_groups_org_code UNIQUE (organization_id, code);


--
-- Name: customers uq_org_customer_code; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT uq_org_customer_code UNIQUE (organization_id, customer_code);


--
-- Name: stock_levels uq_stock_levels_product_warehouse; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_levels
    ADD CONSTRAINT uq_stock_levels_product_warehouse UNIQUE (product_id, warehouse_id);


--
-- Name: suppliers uq_suppliers_org_code; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT uq_suppliers_org_code UNIQUE (organization_id, supplier_code);


--
-- Name: warehouses_extended uq_warehouses_extended_org_code; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.warehouses_extended
    ADD CONSTRAINT uq_warehouses_extended_org_code UNIQUE (organization_id, code);


--
-- Name: warehouses_extended warehouses_extended_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.warehouses_extended
    ADD CONSTRAINT warehouses_extended_pkey PRIMARY KEY (id);


--
-- Name: idx_account_balances_account_date; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_account_balances_account_date ON public.account_balances USING btree (account_id, as_of_date);


--
-- Name: idx_account_balances_account_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_account_balances_account_id ON public.account_balances USING btree (account_id);


--
-- Name: idx_account_balances_as_of_date; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_account_balances_as_of_date ON public.account_balances USING btree (as_of_date);


--
-- Name: idx_accounts_created_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_accounts_created_at ON public.accounts USING btree (created_at);


--
-- Name: idx_accounts_org_currency; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_accounts_org_currency ON public.accounts USING btree (organization_id, currency);


--
-- Name: idx_accounts_org_parent; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_accounts_org_parent ON public.accounts USING btree (organization_id, parent_account_id);


--
-- Name: idx_accounts_org_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_accounts_org_status ON public.accounts USING btree (organization_id, status);


--
-- Name: idx_accounts_org_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_accounts_org_type ON public.accounts USING btree (organization_id, account_type);


--
-- Name: idx_audit_account; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_audit_account ON public.account_audit_log USING btree (account_id);


--
-- Name: idx_audit_timestamp; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_audit_timestamp ON public.account_audit_log USING btree ("timestamp");


--
-- Name: idx_audit_user; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_audit_user ON public.account_audit_log USING btree (user_id);


--
-- Name: idx_communication_logs_channel; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_communication_logs_channel ON public.communication_logs USING btree (channel);


--
-- Name: idx_communication_logs_created_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_communication_logs_created_at ON public.communication_logs USING btree (created_at);


--
-- Name: idx_communication_logs_doc_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_communication_logs_doc_id ON public.communication_logs USING btree (doc_id);


--
-- Name: idx_communication_logs_doc_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_communication_logs_doc_type ON public.communication_logs USING btree (doc_type);


--
-- Name: idx_communication_logs_org_doc; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_communication_logs_org_doc ON public.communication_logs USING btree (organization_id, doc_type, doc_id);


--
-- Name: idx_communication_logs_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_communication_logs_organization_id ON public.communication_logs USING btree (organization_id);


--
-- Name: idx_communication_logs_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_communication_logs_status ON public.communication_logs USING btree (status);


--
-- Name: idx_default_accounts_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_default_accounts_organization_id ON public.default_accounts USING btree (organization_id);


--
-- Name: idx_default_accounts_scenario; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_default_accounts_scenario ON public.default_accounts USING btree (scenario);


--
-- Name: idx_default_accounts_transaction_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_default_accounts_transaction_type ON public.default_accounts USING btree (transaction_type);


--
-- Name: idx_quotations_converted_to_sales_order; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_quotations_converted_to_sales_order ON public.quotations USING btree (converted_to_sales_order);


--
-- Name: ix_accounts_account_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_accounts_account_code ON public.accounts USING btree (account_code);


--
-- Name: ix_accounts_account_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_accounts_account_type ON public.accounts USING btree (account_type);


--
-- Name: ix_accounts_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_accounts_organization_id ON public.accounts USING btree (organization_id);


--
-- Name: ix_accounts_parent_account_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_accounts_parent_account_id ON public.accounts USING btree (parent_account_id);


--
-- Name: ix_accounts_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_accounts_status ON public.accounts USING btree (status);


--
-- Name: ix_batches_batch_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_batches_batch_no ON public.batches USING btree (batch_no);


--
-- Name: ix_batches_item_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_batches_item_id ON public.batches USING btree (item_id);


--
-- Name: ix_batches_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_batches_organization_id ON public.batches USING btree (organization_id);


--
-- Name: ix_charge_templates_charge_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_charge_templates_charge_type ON public.charge_templates USING btree (charge_type);


--
-- Name: ix_charge_templates_deleted_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_charge_templates_deleted_at ON public.charge_templates USING btree (deleted_at);


--
-- Name: ix_charge_templates_org_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_charge_templates_org_type ON public.charge_templates USING btree (organization_id, charge_type) WHERE (deleted_at IS NULL);


--
-- Name: ix_charge_templates_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_charge_templates_organization_id ON public.charge_templates USING btree (organization_id);


--
-- Name: ix_charge_templates_template_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_charge_templates_template_code ON public.charge_templates USING btree (template_code);


--
-- Name: ix_chart_of_accounts_account_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_chart_of_accounts_account_code ON public.chart_of_accounts USING btree (account_code);


--
-- Name: ix_chart_of_accounts_account_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_chart_of_accounts_account_type ON public.chart_of_accounts USING btree (account_type);


--
-- Name: ix_chart_of_accounts_deleted_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_chart_of_accounts_deleted_at ON public.chart_of_accounts USING btree (deleted_at);


--
-- Name: ix_chart_of_accounts_is_active; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_chart_of_accounts_is_active ON public.chart_of_accounts USING btree (is_active);


--
-- Name: ix_chart_of_accounts_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_chart_of_accounts_organization_id ON public.chart_of_accounts USING btree (organization_id);


--
-- Name: ix_chart_of_accounts_parent_account_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_chart_of_accounts_parent_account_id ON public.chart_of_accounts USING btree (parent_account_id);


--
-- Name: ix_customers_customer_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_customers_customer_code ON public.customers USING btree (customer_code);


--
-- Name: ix_customers_customer_name; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_customers_customer_name ON public.customers USING btree (customer_name);


--
-- Name: ix_customers_deleted_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_customers_deleted_at ON public.customers USING btree (deleted_at);


--
-- Name: ix_customers_email; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_customers_email ON public.customers USING btree (email);


--
-- Name: ix_customers_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_customers_organization_id ON public.customers USING btree (organization_id);


--
-- Name: ix_customers_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_customers_status ON public.customers USING btree (status);


--
-- Name: ix_delivery_note_items_delivery_note_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_delivery_note_items_delivery_note_id ON public.delivery_note_items USING btree (delivery_note_id);


--
-- Name: ix_delivery_note_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_delivery_note_items_organization_id ON public.delivery_note_items USING btree (organization_id);


--
-- Name: ix_delivery_notes_customer_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_delivery_notes_customer_id ON public.delivery_notes USING btree (customer_id);


--
-- Name: ix_delivery_notes_delivery_note_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_delivery_notes_delivery_note_no ON public.delivery_notes USING btree (organization_id, delivery_note_no);


--
-- Name: ix_delivery_notes_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_delivery_notes_organization_id ON public.delivery_notes USING btree (organization_id);


--
-- Name: ix_document_numbering_config_document_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_document_numbering_config_document_type ON public.document_numbering_config USING btree (document_type);


--
-- Name: ix_document_numbering_config_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_document_numbering_config_organization_id ON public.document_numbering_config USING btree (organization_id);


--
-- Name: ix_document_sequence_counter_document_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_document_sequence_counter_document_type ON public.document_sequence_counter USING btree (document_type);


--
-- Name: ix_document_sequence_counter_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_document_sequence_counter_organization_id ON public.document_sequence_counter USING btree (organization_id);


--
-- Name: ix_exchange_rates_currencies; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_exchange_rates_currencies ON public.exchange_rates USING btree (from_currency, to_currency);


--
-- Name: ix_exchange_rates_effective_date; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_exchange_rates_effective_date ON public.exchange_rates USING btree (effective_date);


--
-- Name: ix_invoice_items_invoice_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_invoice_items_invoice_id ON public.invoice_items USING btree (invoice_id);


--
-- Name: ix_invoice_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_invoice_items_organization_id ON public.invoice_items USING btree (organization_id);


--
-- Name: ix_invoices_invoice_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_invoices_invoice_no ON public.invoices USING btree (organization_id, invoice_no);


--
-- Name: ix_invoices_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_invoices_organization_id ON public.invoices USING btree (organization_id);


--
-- Name: ix_invoices_party; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_invoices_party ON public.invoices USING btree (party_id, party_type);


--
-- Name: ix_invoices_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_invoices_status ON public.invoices USING btree (status);


--
-- Name: ix_item_groups_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_groups_code ON public.item_groups USING btree (code);


--
-- Name: ix_item_groups_deleted_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_groups_deleted_at ON public.item_groups USING btree (deleted_at);


--
-- Name: ix_item_groups_is_active; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_groups_is_active ON public.item_groups USING btree (is_active);


--
-- Name: ix_item_groups_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_groups_organization_id ON public.item_groups USING btree (organization_id);


--
-- Name: ix_item_groups_parent_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_groups_parent_id ON public.item_groups USING btree (parent_id);


--
-- Name: ix_item_prices_item_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_prices_item_id ON public.item_prices USING btree (item_id);


--
-- Name: ix_item_prices_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_prices_organization_id ON public.item_prices USING btree (organization_id);


--
-- Name: ix_item_suppliers_item_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_suppliers_item_id ON public.item_suppliers USING btree (item_id);


--
-- Name: ix_item_suppliers_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_suppliers_organization_id ON public.item_suppliers USING btree (organization_id);


--
-- Name: ix_item_suppliers_supplier_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_suppliers_supplier_id ON public.item_suppliers USING btree (supplier_id);


--
-- Name: ix_items_item_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_items_item_code ON public.items USING btree (item_code);


--
-- Name: ix_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_items_organization_id ON public.items USING btree (organization_id);


--
-- Name: ix_journal_entries_entry_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_journal_entries_entry_no ON public.journal_entries USING btree (organization_id, entry_no);


--
-- Name: ix_journal_entries_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_journal_entries_organization_id ON public.journal_entries USING btree (organization_id);


--
-- Name: ix_journal_entries_posting_date; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_journal_entries_posting_date ON public.journal_entries USING btree (posting_date);


--
-- Name: ix_journal_entry_lines_journal_entry_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_journal_entry_lines_journal_entry_id ON public.journal_entry_lines USING btree (journal_entry_id);


--
-- Name: ix_journal_entry_lines_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_journal_entry_lines_organization_id ON public.journal_entry_lines USING btree (organization_id);


--
-- Name: ix_landed_cost_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_landed_cost_items_organization_id ON public.landed_cost_items USING btree (organization_id);


--
-- Name: ix_landed_cost_items_voucher_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_landed_cost_items_voucher_id ON public.landed_cost_items USING btree (landed_cost_voucher_id);


--
-- Name: ix_landed_cost_purchase_receipts_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_landed_cost_purchase_receipts_organization_id ON public.landed_cost_purchase_receipts USING btree (organization_id);


--
-- Name: ix_landed_cost_purchase_receipts_voucher_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_landed_cost_purchase_receipts_voucher_id ON public.landed_cost_purchase_receipts USING btree (landed_cost_voucher_id);


--
-- Name: ix_landed_cost_taxes_and_charges_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_landed_cost_taxes_and_charges_organization_id ON public.landed_cost_taxes_and_charges USING btree (organization_id);


--
-- Name: ix_landed_cost_taxes_and_charges_voucher_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_landed_cost_taxes_and_charges_voucher_id ON public.landed_cost_taxes_and_charges USING btree (landed_cost_voucher_id);


--
-- Name: ix_landed_cost_vouchers_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_landed_cost_vouchers_organization_id ON public.landed_cost_vouchers USING btree (organization_id);


--
-- Name: ix_landed_cost_vouchers_voucher_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_landed_cost_vouchers_voucher_no ON public.landed_cost_vouchers USING btree (organization_id, voucher_no);


--
-- Name: ix_material_request_lines_item_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_material_request_lines_item_id ON public.material_request_lines USING btree (item_id);


--
-- Name: ix_material_request_lines_material_request_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_material_request_lines_material_request_id ON public.material_request_lines USING btree (material_request_id);


--
-- Name: ix_material_request_lines_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_material_request_lines_organization_id ON public.material_request_lines USING btree (organization_id);


--
-- Name: ix_material_requests_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_material_requests_organization_id ON public.material_requests USING btree (organization_id);


--
-- Name: ix_material_requests_request_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_material_requests_request_no ON public.material_requests USING btree (request_no);


--
-- Name: ix_material_requests_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_material_requests_status ON public.material_requests USING btree (status);


--
-- Name: ix_organization_settings_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX ix_organization_settings_organization_id ON public.organization_settings USING btree (organization_id);


--
-- Name: ix_payment_allocations_invoice_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_payment_allocations_invoice_id ON public.payment_allocations USING btree (invoice_id);


--
-- Name: ix_payment_allocations_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_payment_allocations_organization_id ON public.payment_allocations USING btree (organization_id);


--
-- Name: ix_payment_allocations_payment_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_payment_allocations_payment_id ON public.payment_allocations USING btree (payment_id);


--
-- Name: ix_payments_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_payments_organization_id ON public.payments USING btree (organization_id);


--
-- Name: ix_payments_party; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_payments_party ON public.payments USING btree (party_id, party_type);


--
-- Name: ix_payments_payment_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_payments_payment_no ON public.payments USING btree (organization_id, payment_no);


--
-- Name: ix_pick_list_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_pick_list_items_organization_id ON public.pick_list_items USING btree (organization_id);


--
-- Name: ix_pick_list_items_pick_list_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_pick_list_items_pick_list_id ON public.pick_list_items USING btree (pick_list_id);


--
-- Name: ix_pick_lists_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_pick_lists_organization_id ON public.pick_lists USING btree (organization_id);


--
-- Name: ix_pick_lists_pick_list_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_pick_lists_pick_list_no ON public.pick_lists USING btree (organization_id, pick_list_no);


--
-- Name: ix_pick_lists_warehouse_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_pick_lists_warehouse_id ON public.pick_lists USING btree (warehouse_id);


--
-- Name: ix_purchase_order_lines_item_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_order_lines_item_id ON public.purchase_order_lines USING btree (item_id);


--
-- Name: ix_purchase_order_lines_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_order_lines_organization_id ON public.purchase_order_lines USING btree (organization_id);


--
-- Name: ix_purchase_order_lines_purchase_order_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_order_lines_purchase_order_id ON public.purchase_order_lines USING btree (purchase_order_id);


--
-- Name: ix_purchase_orders_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_orders_organization_id ON public.purchase_orders USING btree (organization_id);


--
-- Name: ix_purchase_orders_party_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_orders_party_id ON public.purchase_orders USING btree (party_id);


--
-- Name: ix_purchase_orders_rfq_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_orders_rfq_id ON public.purchase_orders USING btree (rfq_id);


--
-- Name: ix_purchase_orders_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_orders_status ON public.purchase_orders USING btree (status);


--
-- Name: ix_purchase_receipt_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_receipt_items_organization_id ON public.purchase_receipt_items USING btree (organization_id);


--
-- Name: ix_purchase_receipt_items_purchase_receipt_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_receipt_items_purchase_receipt_id ON public.purchase_receipt_items USING btree (purchase_receipt_id);


--
-- Name: ix_purchase_receipts_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_receipts_organization_id ON public.purchase_receipts USING btree (organization_id);


--
-- Name: ix_purchase_receipts_purchase_receipt_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_receipts_purchase_receipt_no ON public.purchase_receipts USING btree (organization_id, purchase_receipt_no);


--
-- Name: ix_purchase_receipts_supplier_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_receipts_supplier_id ON public.purchase_receipts USING btree (supplier_id);


--
-- Name: ix_put_away_rules_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_put_away_rules_organization_id ON public.put_away_rules USING btree (organization_id);


--
-- Name: ix_put_away_rules_warehouse_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_put_away_rules_warehouse_id ON public.put_away_rules USING btree (warehouse_id);


--
-- Name: ix_quotation_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_quotation_items_organization_id ON public.quotation_items USING btree (organization_id);


--
-- Name: ix_quotation_items_quotation_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_quotation_items_quotation_id ON public.quotation_items USING btree (quotation_id);


--
-- Name: ix_quotations_customer_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_quotations_customer_id ON public.quotations USING btree (customer_id);


--
-- Name: ix_quotations_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_quotations_organization_id ON public.quotations USING btree (organization_id);


--
-- Name: ix_quotations_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_quotations_status ON public.quotations USING btree (status);


--
-- Name: ix_rfq_lines_item_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_rfq_lines_item_id ON public.rfq_lines USING btree (item_id);


--
-- Name: ix_rfq_lines_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_rfq_lines_organization_id ON public.rfq_lines USING btree (organization_id);


--
-- Name: ix_rfq_lines_rfq_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_rfq_lines_rfq_id ON public.rfq_lines USING btree (rfq_id);


--
-- Name: ix_rfq_suppliers_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_rfq_suppliers_organization_id ON public.rfq_suppliers USING btree (organization_id);


--
-- Name: ix_rfq_suppliers_rfq_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_rfq_suppliers_rfq_id ON public.rfq_suppliers USING btree (rfq_id);


--
-- Name: ix_rfq_suppliers_supplier_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_rfq_suppliers_supplier_id ON public.rfq_suppliers USING btree (supplier_id);


--
-- Name: ix_rfqs_material_request_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_rfqs_material_request_id ON public.rfqs USING btree (material_request_id);


--
-- Name: ix_rfqs_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_rfqs_organization_id ON public.rfqs USING btree (organization_id);


--
-- Name: ix_rfqs_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_rfqs_status ON public.rfqs USING btree (status);


--
-- Name: ix_sales_order_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_sales_order_items_organization_id ON public.sales_order_items USING btree (organization_id);


--
-- Name: ix_sales_order_items_sales_order_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_sales_order_items_sales_order_id ON public.sales_order_items USING btree (sales_order_id);


--
-- Name: ix_sales_orders_customer_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_sales_orders_customer_id ON public.sales_orders USING btree (customer_id);


--
-- Name: ix_sales_orders_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_sales_orders_organization_id ON public.sales_orders USING btree (organization_id);


--
-- Name: ix_sales_orders_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_sales_orders_status ON public.sales_orders USING btree (status);


--
-- Name: ix_serial_no_history_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_serial_no_history_organization_id ON public.serial_no_history USING btree (organization_id);


--
-- Name: ix_serial_no_history_serial_no_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_serial_no_history_serial_no_id ON public.serial_no_history USING btree (serial_no_id);


--
-- Name: ix_serial_no_history_transaction_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_serial_no_history_transaction_id ON public.serial_no_history USING btree (transaction_id);


--
-- Name: ix_serial_nos_item_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_serial_nos_item_id ON public.serial_nos USING btree (item_id);


--
-- Name: ix_serial_nos_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_serial_nos_organization_id ON public.serial_nos USING btree (organization_id);


--
-- Name: ix_serial_nos_serial_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_serial_nos_serial_no ON public.serial_nos USING btree (serial_no);


--
-- Name: ix_serial_nos_warehouse_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_serial_nos_warehouse_id ON public.serial_nos USING btree (warehouse_id);


--
-- Name: ix_status_transitions_entity_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_status_transitions_entity_id ON public.status_transitions USING btree (entity_id);


--
-- Name: ix_status_transitions_entity_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_status_transitions_entity_type ON public.status_transitions USING btree (entity_type);


--
-- Name: ix_status_transitions_transitioned_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_status_transitions_transitioned_at ON public.status_transitions USING btree (transitioned_at);


--
-- Name: ix_stock_entries_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_entries_organization_id ON public.stock_entries USING btree (organization_id);


--
-- Name: ix_stock_entries_posting_date; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_entries_posting_date ON public.stock_entries USING btree (posting_date);


--
-- Name: ix_stock_entries_stock_entry_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_entries_stock_entry_no ON public.stock_entries USING btree (stock_entry_no);


--
-- Name: ix_stock_entry_items_item_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_entry_items_item_id ON public.stock_entry_items USING btree (item_id);


--
-- Name: ix_stock_entry_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_entry_items_organization_id ON public.stock_entry_items USING btree (organization_id);


--
-- Name: ix_stock_entry_items_stock_entry_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_entry_items_stock_entry_id ON public.stock_entry_items USING btree (stock_entry_id);


--
-- Name: ix_stock_levels_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_levels_organization_id ON public.stock_levels USING btree (organization_id);


--
-- Name: ix_stock_levels_product_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_levels_product_id ON public.stock_levels USING btree (product_id);


--
-- Name: ix_stock_levels_warehouse_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_levels_warehouse_id ON public.stock_levels USING btree (warehouse_id);


--
-- Name: ix_stock_movements_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_movements_organization_id ON public.stock_movements USING btree (organization_id);


--
-- Name: ix_stock_movements_product_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_movements_product_id ON public.stock_movements USING btree (product_id);


--
-- Name: ix_stock_movements_reference; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_movements_reference ON public.stock_movements USING btree (reference_type, reference_id);


--
-- Name: ix_stock_movements_warehouse_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_movements_warehouse_id ON public.stock_movements USING btree (warehouse_id);


--
-- Name: ix_stock_reconciliation_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_reconciliation_items_organization_id ON public.stock_reconciliation_items USING btree (organization_id);


--
-- Name: ix_stock_reconciliation_items_reconciliation_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_reconciliation_items_reconciliation_id ON public.stock_reconciliation_items USING btree (reconciliation_id);


--
-- Name: ix_stock_reconciliations_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_reconciliations_organization_id ON public.stock_reconciliations USING btree (organization_id);


--
-- Name: ix_stock_reconciliations_reconciliation_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_reconciliations_reconciliation_no ON public.stock_reconciliations USING btree (reconciliation_no);


--
-- Name: ix_stock_settings_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_stock_settings_organization_id ON public.stock_settings USING btree (organization_id);


--
-- Name: ix_supplier_quotes_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_supplier_quotes_organization_id ON public.supplier_quotes USING btree (organization_id);


--
-- Name: ix_supplier_quotes_rfq_line_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_supplier_quotes_rfq_line_id ON public.supplier_quotes USING btree (rfq_line_id);


--
-- Name: ix_supplier_quotes_supplier_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_supplier_quotes_supplier_id ON public.supplier_quotes USING btree (supplier_id);


--
-- Name: ix_suppliers_deleted_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_suppliers_deleted_at ON public.suppliers USING btree (deleted_at);


--
-- Name: ix_suppliers_email; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_suppliers_email ON public.suppliers USING btree (email);


--
-- Name: ix_suppliers_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_suppliers_organization_id ON public.suppliers USING btree (organization_id);


--
-- Name: ix_suppliers_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_suppliers_status ON public.suppliers USING btree (status);


--
-- Name: ix_suppliers_supplier_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_suppliers_supplier_code ON public.suppliers USING btree (supplier_code);


--
-- Name: ix_suppliers_supplier_name; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_suppliers_supplier_name ON public.suppliers USING btree (supplier_name);


--
-- Name: ix_tax_rules_tax_template_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_tax_rules_tax_template_id ON public.tax_rules USING btree (tax_template_id);


--
-- Name: ix_tax_rules_template_sequence; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_tax_rules_template_sequence ON public.tax_rules USING btree (tax_template_id, sequence);


--
-- Name: ix_tax_templates_default; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_tax_templates_default ON public.tax_templates USING btree (organization_id, is_default, tax_category) WHERE (is_default = true);


--
-- Name: ix_tax_templates_deleted_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_tax_templates_deleted_at ON public.tax_templates USING btree (deleted_at);


--
-- Name: ix_tax_templates_is_default; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_tax_templates_is_default ON public.tax_templates USING btree (is_default);


--
-- Name: ix_tax_templates_org_category; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_tax_templates_org_category ON public.tax_templates USING btree (organization_id, tax_category) WHERE (deleted_at IS NULL);


--
-- Name: ix_tax_templates_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_tax_templates_organization_id ON public.tax_templates USING btree (organization_id);


--
-- Name: ix_tax_templates_template_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_tax_templates_template_code ON public.tax_templates USING btree (template_code);


--
-- Name: ix_trans_charge_breakdown_org_date; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_trans_charge_breakdown_org_date ON public.transaction_charge_breakdown USING btree (organization_id, created_at);


--
-- Name: ix_trans_charge_breakdown_trans; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_trans_charge_breakdown_trans ON public.transaction_charge_breakdown USING btree (transaction_type, transaction_id);


--
-- Name: ix_trans_tax_breakdown_org_date; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_trans_tax_breakdown_org_date ON public.transaction_tax_breakdown USING btree (organization_id, created_at);


--
-- Name: ix_trans_tax_breakdown_tax_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_trans_tax_breakdown_tax_type ON public.transaction_tax_breakdown USING btree (organization_id, tax_type, created_at);


--
-- Name: ix_trans_tax_breakdown_trans; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_trans_tax_breakdown_trans ON public.transaction_tax_breakdown USING btree (transaction_type, transaction_id);


--
-- Name: ix_transaction_charge_breakdown_charge_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_transaction_charge_breakdown_charge_type ON public.transaction_charge_breakdown USING btree (charge_type);


--
-- Name: ix_transaction_charge_breakdown_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_transaction_charge_breakdown_organization_id ON public.transaction_charge_breakdown USING btree (organization_id);


--
-- Name: ix_transaction_charge_breakdown_transaction_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_transaction_charge_breakdown_transaction_id ON public.transaction_charge_breakdown USING btree (transaction_id);


--
-- Name: ix_transaction_charge_breakdown_transaction_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_transaction_charge_breakdown_transaction_type ON public.transaction_charge_breakdown USING btree (transaction_type);


--
-- Name: ix_transaction_tax_breakdown_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_transaction_tax_breakdown_organization_id ON public.transaction_tax_breakdown USING btree (organization_id);


--
-- Name: ix_transaction_tax_breakdown_tax_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_transaction_tax_breakdown_tax_type ON public.transaction_tax_breakdown USING btree (tax_type);


--
-- Name: ix_transaction_tax_breakdown_transaction_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_transaction_tax_breakdown_transaction_id ON public.transaction_tax_breakdown USING btree (transaction_id);


--
-- Name: ix_transaction_tax_breakdown_transaction_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_transaction_tax_breakdown_transaction_type ON public.transaction_tax_breakdown USING btree (transaction_type);


--
-- Name: ix_warehouses_extended_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_warehouses_extended_code ON public.warehouses_extended USING btree (code);


--
-- Name: ix_warehouses_extended_deleted_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_warehouses_extended_deleted_at ON public.warehouses_extended USING btree (deleted_at);


--
-- Name: ix_warehouses_extended_is_active; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_warehouses_extended_is_active ON public.warehouses_extended USING btree (is_active);


--
-- Name: ix_warehouses_extended_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_warehouses_extended_organization_id ON public.warehouses_extended USING btree (organization_id);


--
-- Name: ix_warehouses_extended_parent_warehouse_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_warehouses_extended_parent_warehouse_id ON public.warehouses_extended USING btree (parent_warehouse_id);


--
-- Name: account_audit_log account_audit_log_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.account_audit_log
    ADD CONSTRAINT account_audit_log_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: account_balances account_balances_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.account_balances
    ADD CONSTRAINT account_balances_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: default_accounts default_accounts_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.default_accounts
    ADD CONSTRAINT default_accounts_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE RESTRICT;


--
-- Name: accounts fk_accounts_parent_account_id; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT fk_accounts_parent_account_id FOREIGN KEY (parent_account_id) REFERENCES public.accounts(id);


--
-- Name: batches fk_batches_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT fk_batches_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: chart_of_accounts fk_chart_of_accounts_parent; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.chart_of_accounts
    ADD CONSTRAINT fk_chart_of_accounts_parent FOREIGN KEY (parent_account_id) REFERENCES public.chart_of_accounts(id) ON DELETE SET NULL;


--
-- Name: delivery_notes fk_dn_customer; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.delivery_notes
    ADD CONSTRAINT fk_dn_customer FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: delivery_notes fk_dn_pick_list; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.delivery_notes
    ADD CONSTRAINT fk_dn_pick_list FOREIGN KEY (pick_list_id) REFERENCES public.pick_lists(id) ON DELETE SET NULL;


--
-- Name: delivery_notes fk_dn_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.delivery_notes
    ADD CONSTRAINT fk_dn_warehouse FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


--
-- Name: delivery_note_items fk_dni_delivery_note; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.delivery_note_items
    ADD CONSTRAINT fk_dni_delivery_note FOREIGN KEY (delivery_note_id) REFERENCES public.delivery_notes(id) ON DELETE CASCADE;


--
-- Name: delivery_note_items fk_dni_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.delivery_note_items
    ADD CONSTRAINT fk_dni_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: delivery_note_items fk_dni_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.delivery_note_items
    ADD CONSTRAINT fk_dni_warehouse FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


--
-- Name: invoice_items fk_invi_invoice; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT fk_invi_invoice FOREIGN KEY (invoice_id) REFERENCES public.invoices(id) ON DELETE CASCADE;


--
-- Name: invoice_items fk_invi_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT fk_invi_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE SET NULL;


--
-- Name: item_groups fk_item_groups_parent; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.item_groups
    ADD CONSTRAINT fk_item_groups_parent FOREIGN KEY (parent_id) REFERENCES public.item_groups(id) ON DELETE SET NULL;


--
-- Name: item_prices fk_item_prices_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.item_prices
    ADD CONSTRAINT fk_item_prices_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: item_suppliers fk_item_suppliers_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.item_suppliers
    ADD CONSTRAINT fk_item_suppliers_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: journal_entry_lines fk_jel_account; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.journal_entry_lines
    ADD CONSTRAINT fk_jel_account FOREIGN KEY (account_id) REFERENCES public.chart_of_accounts(id) ON DELETE CASCADE;


--
-- Name: journal_entry_lines fk_jel_against_account; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.journal_entry_lines
    ADD CONSTRAINT fk_jel_against_account FOREIGN KEY (against_account_id) REFERENCES public.chart_of_accounts(id) ON DELETE SET NULL;


--
-- Name: journal_entry_lines fk_jel_journal_entry; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.journal_entry_lines
    ADD CONSTRAINT fk_jel_journal_entry FOREIGN KEY (journal_entry_id) REFERENCES public.journal_entries(id) ON DELETE CASCADE;


--
-- Name: landed_cost_items fk_lci_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.landed_cost_items
    ADD CONSTRAINT fk_lci_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: landed_cost_items fk_lci_purchase_receipt; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.landed_cost_items
    ADD CONSTRAINT fk_lci_purchase_receipt FOREIGN KEY (purchase_receipt_id) REFERENCES public.purchase_receipts(id) ON DELETE SET NULL;


--
-- Name: landed_cost_items fk_lci_voucher; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.landed_cost_items
    ADD CONSTRAINT fk_lci_voucher FOREIGN KEY (landed_cost_voucher_id) REFERENCES public.landed_cost_vouchers(id) ON DELETE CASCADE;


--
-- Name: landed_cost_purchase_receipts fk_lcpr_purchase_receipt; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.landed_cost_purchase_receipts
    ADD CONSTRAINT fk_lcpr_purchase_receipt FOREIGN KEY (purchase_receipt_id) REFERENCES public.purchase_receipts(id) ON DELETE CASCADE;


--
-- Name: landed_cost_purchase_receipts fk_lcpr_voucher; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.landed_cost_purchase_receipts
    ADD CONSTRAINT fk_lcpr_voucher FOREIGN KEY (landed_cost_voucher_id) REFERENCES public.landed_cost_vouchers(id) ON DELETE CASCADE;


--
-- Name: landed_cost_taxes_and_charges fk_lctc_account; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.landed_cost_taxes_and_charges
    ADD CONSTRAINT fk_lctc_account FOREIGN KEY (account_id) REFERENCES public.chart_of_accounts(id) ON DELETE SET NULL;


--
-- Name: landed_cost_taxes_and_charges fk_lctc_voucher; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.landed_cost_taxes_and_charges
    ADD CONSTRAINT fk_lctc_voucher FOREIGN KEY (landed_cost_voucher_id) REFERENCES public.landed_cost_vouchers(id) ON DELETE CASCADE;


--
-- Name: payment_allocations fk_pa_invoice; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.payment_allocations
    ADD CONSTRAINT fk_pa_invoice FOREIGN KEY (invoice_id) REFERENCES public.invoices(id) ON DELETE CASCADE;


--
-- Name: payment_allocations fk_pa_payment; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.payment_allocations
    ADD CONSTRAINT fk_pa_payment FOREIGN KEY (payment_id) REFERENCES public.payments(id) ON DELETE CASCADE;


--
-- Name: pick_lists fk_pl_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.pick_lists
    ADD CONSTRAINT fk_pl_warehouse FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE CASCADE;


--
-- Name: pick_list_items fk_pli_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.pick_list_items
    ADD CONSTRAINT fk_pli_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: pick_list_items fk_pli_pick_list; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.pick_list_items
    ADD CONSTRAINT fk_pli_pick_list FOREIGN KEY (pick_list_id) REFERENCES public.pick_lists(id) ON DELETE CASCADE;


--
-- Name: pick_list_items fk_pli_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.pick_list_items
    ADD CONSTRAINT fk_pli_warehouse FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE CASCADE;


--
-- Name: purchase_receipts fk_pr_supplier; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipts
    ADD CONSTRAINT fk_pr_supplier FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE CASCADE;


--
-- Name: purchase_receipts fk_pr_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipts
    ADD CONSTRAINT fk_pr_warehouse FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


--
-- Name: purchase_receipt_items fk_pri_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipt_items
    ADD CONSTRAINT fk_pri_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: purchase_receipt_items fk_pri_purchase_receipt; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipt_items
    ADD CONSTRAINT fk_pri_purchase_receipt FOREIGN KEY (purchase_receipt_id) REFERENCES public.purchase_receipts(id) ON DELETE CASCADE;


--
-- Name: purchase_receipt_items fk_pri_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipt_items
    ADD CONSTRAINT fk_pri_warehouse FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


--
-- Name: put_away_rules fk_put_away_rules_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.put_away_rules
    ADD CONSTRAINT fk_put_away_rules_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: put_away_rules fk_put_away_rules_item_group; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.put_away_rules
    ADD CONSTRAINT fk_put_away_rules_item_group FOREIGN KEY (item_group_id) REFERENCES public.item_groups(id) ON DELETE CASCADE;


--
-- Name: put_away_rules fk_put_away_rules_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.put_away_rules
    ADD CONSTRAINT fk_put_away_rules_warehouse FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE CASCADE;


--
-- Name: serial_no_history fk_serial_no_history_serial_no; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.serial_no_history
    ADD CONSTRAINT fk_serial_no_history_serial_no FOREIGN KEY (serial_no_id) REFERENCES public.serial_nos(id) ON DELETE CASCADE;


--
-- Name: serial_nos fk_serial_nos_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.serial_nos
    ADD CONSTRAINT fk_serial_nos_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: serial_nos fk_serial_nos_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.serial_nos
    ADD CONSTRAINT fk_serial_nos_warehouse FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE CASCADE;


--
-- Name: stock_entries fk_stock_entries_from_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_entries
    ADD CONSTRAINT fk_stock_entries_from_warehouse FOREIGN KEY (from_warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


--
-- Name: stock_entries fk_stock_entries_to_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_entries
    ADD CONSTRAINT fk_stock_entries_to_warehouse FOREIGN KEY (to_warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


--
-- Name: stock_entry_items fk_stock_entry_items_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_entry_items
    ADD CONSTRAINT fk_stock_entry_items_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: stock_entry_items fk_stock_entry_items_source_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_entry_items
    ADD CONSTRAINT fk_stock_entry_items_source_warehouse FOREIGN KEY (source_warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


--
-- Name: stock_entry_items fk_stock_entry_items_stock_entry; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_entry_items
    ADD CONSTRAINT fk_stock_entry_items_stock_entry FOREIGN KEY (stock_entry_id) REFERENCES public.stock_entries(id) ON DELETE CASCADE;


--
-- Name: stock_entry_items fk_stock_entry_items_target_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_entry_items
    ADD CONSTRAINT fk_stock_entry_items_target_warehouse FOREIGN KEY (target_warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


--
-- Name: stock_levels fk_stock_levels_product; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_levels
    ADD CONSTRAINT fk_stock_levels_product FOREIGN KEY (product_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: stock_levels fk_stock_levels_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_levels
    ADD CONSTRAINT fk_stock_levels_warehouse FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE CASCADE;


--
-- Name: stock_movements fk_stock_movements_product; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_movements
    ADD CONSTRAINT fk_stock_movements_product FOREIGN KEY (product_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: stock_movements fk_stock_movements_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_movements
    ADD CONSTRAINT fk_stock_movements_warehouse FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE CASCADE;


--
-- Name: stock_reconciliation_items fk_stock_reconciliation_items_item; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_reconciliation_items
    ADD CONSTRAINT fk_stock_reconciliation_items_item FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: stock_reconciliation_items fk_stock_reconciliation_items_reconciliation; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_reconciliation_items
    ADD CONSTRAINT fk_stock_reconciliation_items_reconciliation FOREIGN KEY (reconciliation_id) REFERENCES public.stock_reconciliations(id) ON DELETE CASCADE;


--
-- Name: stock_reconciliation_items fk_stock_reconciliation_items_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_reconciliation_items
    ADD CONSTRAINT fk_stock_reconciliation_items_warehouse FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE CASCADE;


--
-- Name: stock_settings fk_stock_settings_default_warehouse; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.stock_settings
    ADD CONSTRAINT fk_stock_settings_default_warehouse FOREIGN KEY (default_warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


--
-- Name: warehouses_extended fk_warehouses_extended_parent; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.warehouses_extended
    ADD CONSTRAINT fk_warehouses_extended_parent FOREIGN KEY (parent_warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


--
-- Name: item_groups item_groups_purchase_tax_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.item_groups
    ADD CONSTRAINT item_groups_purchase_tax_template_id_fkey FOREIGN KEY (purchase_tax_template_id) REFERENCES public.tax_templates(id);


--
-- Name: item_groups item_groups_sales_tax_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.item_groups
    ADD CONSTRAINT item_groups_sales_tax_template_id_fkey FOREIGN KEY (sales_tax_template_id) REFERENCES public.tax_templates(id);


--
-- Name: items items_item_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_item_group_id_fkey FOREIGN KEY (item_group_id) REFERENCES public.item_groups(id);


--
-- Name: items items_purchase_tax_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_purchase_tax_template_id_fkey FOREIGN KEY (purchase_tax_template_id) REFERENCES public.tax_templates(id);


--
-- Name: items items_sales_tax_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_sales_tax_template_id_fkey FOREIGN KEY (sales_tax_template_id) REFERENCES public.tax_templates(id);


--
-- Name: items items_variant_of_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_variant_of_fkey FOREIGN KEY (variant_of) REFERENCES public.items(id);


--
-- Name: material_request_lines material_request_lines_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.material_request_lines
    ADD CONSTRAINT material_request_lines_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE RESTRICT;


--
-- Name: material_request_lines material_request_lines_material_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.material_request_lines
    ADD CONSTRAINT material_request_lines_material_request_id_fkey FOREIGN KEY (material_request_id) REFERENCES public.material_requests(id) ON DELETE CASCADE;


--
-- Name: organization_settings organization_settings_default_purchase_tax_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.organization_settings
    ADD CONSTRAINT organization_settings_default_purchase_tax_template_id_fkey FOREIGN KEY (default_purchase_tax_template_id) REFERENCES public.tax_templates(id);


--
-- Name: organization_settings organization_settings_default_sales_tax_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.organization_settings
    ADD CONSTRAINT organization_settings_default_sales_tax_template_id_fkey FOREIGN KEY (default_sales_tax_template_id) REFERENCES public.tax_templates(id);


--
-- Name: purchase_order_lines purchase_order_lines_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE RESTRICT;


--
-- Name: purchase_order_lines purchase_order_lines_purchase_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_purchase_order_id_fkey FOREIGN KEY (purchase_order_id) REFERENCES public.purchase_orders(id) ON DELETE CASCADE;


--
-- Name: purchase_orders purchase_orders_party_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_orders
    ADD CONSTRAINT purchase_orders_party_id_fkey FOREIGN KEY (party_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT;


--
-- Name: purchase_orders purchase_orders_rfq_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_orders
    ADD CONSTRAINT purchase_orders_rfq_id_fkey FOREIGN KEY (rfq_id) REFERENCES public.rfqs(id) ON DELETE RESTRICT;


--
-- Name: quotation_items quotation_items_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT quotation_items_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE RESTRICT;


--
-- Name: quotation_items quotation_items_quotation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT quotation_items_quotation_id_fkey FOREIGN KEY (quotation_id) REFERENCES public.quotations(id) ON DELETE CASCADE;


--
-- Name: quotation_items quotation_items_tax_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT quotation_items_tax_template_id_fkey FOREIGN KEY (tax_template_id) REFERENCES public.tax_templates(id);


--
-- Name: quotations quotations_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE RESTRICT;


--
-- Name: rfq_lines rfq_lines_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.rfq_lines
    ADD CONSTRAINT rfq_lines_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE RESTRICT;


--
-- Name: rfq_lines rfq_lines_rfq_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.rfq_lines
    ADD CONSTRAINT rfq_lines_rfq_id_fkey FOREIGN KEY (rfq_id) REFERENCES public.rfqs(id) ON DELETE CASCADE;


--
-- Name: rfq_suppliers rfq_suppliers_rfq_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.rfq_suppliers
    ADD CONSTRAINT rfq_suppliers_rfq_id_fkey FOREIGN KEY (rfq_id) REFERENCES public.rfqs(id) ON DELETE CASCADE;


--
-- Name: rfq_suppliers rfq_suppliers_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.rfq_suppliers
    ADD CONSTRAINT rfq_suppliers_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT;


--
-- Name: rfqs rfqs_material_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.rfqs
    ADD CONSTRAINT rfqs_material_request_id_fkey FOREIGN KEY (material_request_id) REFERENCES public.material_requests(id) ON DELETE RESTRICT;


--
-- Name: sales_order_items sales_order_items_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.sales_order_items
    ADD CONSTRAINT sales_order_items_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE RESTRICT;


--
-- Name: sales_order_items sales_order_items_sales_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.sales_order_items
    ADD CONSTRAINT sales_order_items_sales_order_id_fkey FOREIGN KEY (sales_order_id) REFERENCES public.sales_orders(id) ON DELETE CASCADE;


--
-- Name: sales_order_items sales_order_items_tax_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.sales_order_items
    ADD CONSTRAINT sales_order_items_tax_template_id_fkey FOREIGN KEY (tax_template_id) REFERENCES public.tax_templates(id) ON DELETE SET NULL;


--
-- Name: sales_orders sales_orders_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.sales_orders
    ADD CONSTRAINT sales_orders_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE RESTRICT;


--
-- Name: supplier_quotes supplier_quotes_rfq_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.supplier_quotes
    ADD CONSTRAINT supplier_quotes_rfq_line_id_fkey FOREIGN KEY (rfq_line_id) REFERENCES public.rfq_lines(id) ON DELETE CASCADE;


--
-- Name: supplier_quotes supplier_quotes_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.supplier_quotes
    ADD CONSTRAINT supplier_quotes_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT;


--
-- Name: tax_rules tax_rules_tax_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.tax_rules
    ADD CONSTRAINT tax_rules_tax_template_id_fkey FOREIGN KEY (tax_template_id) REFERENCES public.tax_templates(id) ON DELETE CASCADE;


--
-- Name: transaction_charge_breakdown transaction_charge_breakdown_charge_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.transaction_charge_breakdown
    ADD CONSTRAINT transaction_charge_breakdown_charge_template_id_fkey FOREIGN KEY (charge_template_id) REFERENCES public.charge_templates(id);


--
-- Name: transaction_tax_breakdown transaction_tax_breakdown_tax_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.transaction_tax_breakdown
    ADD CONSTRAINT transaction_tax_breakdown_tax_rule_id_fkey FOREIGN KEY (tax_rule_id) REFERENCES public.tax_rules(id);


--
-- Name: transaction_tax_breakdown transaction_tax_breakdown_tax_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.transaction_tax_breakdown
    ADD CONSTRAINT transaction_tax_breakdown_tax_template_id_fkey FOREIGN KEY (tax_template_id) REFERENCES public.tax_templates(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 4XRh2NaB6witPPdzi8D2sp1OtK8TRDAEoo8hOhAek03bbqrVuPnUgjkJRBxBkqs

