--
-- PostgreSQL database dump
--

\restrict VSWC521yBIlc02SZRRYCh304wKQQfp4FPeKNcnY646TsBuZ5abMekcBkoeXqLcW

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

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
    deleted_at timestamp with time zone
);


ALTER TABLE public.customers OWNER TO horizon_user;

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
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
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
    deleted_at timestamp with time zone
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
    status public.itemstatus DEFAULT 'active'::public.itemstatus
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
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
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
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.quotations OWNER TO horizon_user;

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
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
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
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
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
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.alembic_version (version_num) FROM stdin;
002
\.


--
-- Data for Name: batches; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.batches (id, organization_id, batch_no, item_id, manufacturing_date, expiry_date, supplier_id, supplier_batch_no, status, reference_type, reference_id, description, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: chart_of_accounts; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.chart_of_accounts (id, organization_id, account_code, account_name, account_type, parent_account_id, level, is_group, opening_balance, current_balance, is_active, tags, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
aa2609fb-93f3-452d-9e18-8c06ab1d20a9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1000	Assets	asset	\N	1	t	0.00	0.00	t	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
3dd50f6f-6530-44ee-8fca-ffb66da268ef	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1130	Inventory	asset	aa2609fb-93f3-452d-9e18-8c06ab1d20a9	2	f	0.00	0.00	t	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
\.


--
-- Data for Name: customers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.customers (id, organization_id, customer_name, customer_code, email, phone, address, address_line1, address_line2, city, state, postal_code, country, tax_number, status, credit_limit, outstanding_balance, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
2442b9be-c640-4f8f-9a87-e07fb8ba875b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Suinoli Pvt Ltd, India	CUS-007	info@suinoli.com	+91-9787878790	13123, Sobha Dream Acres\nPanathur Main Road, Off Orr Balagere	13123, Sobha Dream Acres	Panathur Main Road, Off Orr Balagere	Bangalore Urban	Karnataka	560087	IN	UTZ9987265RT	active	100000.00	90800.00	["top", "first", "more"]	{}	{}	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-03 08:56:29.08008+00	2026-02-03 10:04:43.734254+00	\N
60b23cd6-744b-495f-98e7-4730a6c1c1f9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Acme Corporation	CUST-001	contact@acme.com	+91-9876543001	\N	\N	\N	Mumbai	\N	\N	IN	\N	blocked	1524876.00	12350.00	\N	{}	{}	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-26 15:47:10.155932+00	2026-02-03 15:47:17.774462+00	\N
08d25496-002c-4edb-b033-a76a9acfa674	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Huge Rock	HRU-01	ingo@hugerock.com	+91-9711452000	Bangalore	123, B block	Indra Nager	Bangalore	Karnataka	560087	IN	zo87992jd8kk99	inactive	10000.00	59098.00	["top"]	{}	{}	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-03 08:32:38.618222+00	2026-02-03 15:47:27.602657+00	\N
\.


--
-- Data for Name: delivery_note_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.delivery_note_items (id, organization_id, delivery_note_id, item_id, qty, uom, rate, amount, warehouse_id, batch_no, serial_nos, sort_order, extra_data, created_at, updated_at) FROM stdin;
f05a9b55-9a11-47d3-a608-eda792b27bc1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1f72bc02-c105-4b10-ba36-19374a9259e1	774bcea0-9782-46cc-8477-038d1f04123f	4.017	PCS	100.00	100.00	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
89d563db-cf47-4563-b9db-40a0ee935d97	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1f72bc02-c105-4b10-ba36-19374a9259e1	3531e02a-28dc-4659-9a76-70fa0c12c933	1.228	PCS	100.00	100.00	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
5103aa4f-8483-4d8a-b994-1f6dba4d9219	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1f72bc02-c105-4b10-ba36-19374a9259e1	1aff047b-e5b2-4e0e-9626-b3cbdc23384e	10.865	PCS	100.00	100.00	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
f4a1c039-6a7d-4006-949c-88acfa1ae511	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1f72bc02-c105-4b10-ba36-19374a9259e1	0a75cf03-8b5b-471b-8d0d-0a4c2f194999	1.259	PCS	100.00	100.00	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
482b5c9c-f495-4253-9c83-4c32e084404e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1f72bc02-c105-4b10-ba36-19374a9259e1	d92b4647-a8d5-42d4-83b1-e33bf19dd414	4.061	PCS	100.00	100.00	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
1b10d681-c1f9-408f-a9c2-fad1040f84ca	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	fc30c4d9-cb9c-44d4-9c3e-cc1f35f41d59	07423f9a-c153-426b-84d3-9d37431fa4fa	7.044	PCS	100.00	100.00	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
6c3f285e-ffa4-4902-ad8b-c170eda76516	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	fc30c4d9-cb9c-44d4-9c3e-cc1f35f41d59	ba33b62c-d77a-4e04-b4a9-0c047009d020	3.137	PCS	100.00	100.00	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
67d9cfcf-f53d-4c1a-beb3-0466662c9a8e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	fc30c4d9-cb9c-44d4-9c3e-cc1f35f41d59	4df44234-2b66-4867-bf03-95871df0a629	4.420	PCS	100.00	100.00	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
0b202242-100b-4c2f-b71b-96123db438dd	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	fc30c4d9-cb9c-44d4-9c3e-cc1f35f41d59	7428ed48-7878-40b7-b0cb-bd8e24fdaf23	2.779	PCS	100.00	100.00	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
46c480f3-0ea8-456f-831c-ed75b24d9fd5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	fc30c4d9-cb9c-44d4-9c3e-cc1f35f41d59	3a652a33-b63b-4999-a339-ec5eb3fa4e47	3.466	PCS	100.00	100.00	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
e97969e6-84d9-43ca-b79f-ac96e0a20824	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	fc30c4d9-cb9c-44d4-9c3e-cc1f35f41d59	3f5d86f2-c1be-47b5-b30d-8a77da614a5c	6.799	PCS	100.00	100.00	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
631d29f9-00c0-4b58-9640-3f13a253a4d3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	fc30c4d9-cb9c-44d4-9c3e-cc1f35f41d59	fbe3d99c-317c-4581-b8e4-b2f5addaebb4	8.536	PCS	100.00	100.00	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	\N	0	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
\.


--
-- Data for Name: delivery_notes; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.delivery_notes (id, organization_id, delivery_note_no, customer_id, delivery_date, status, warehouse_id, pick_list_id, reference_type, reference_id, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
1f72bc02-c105-4b10-ba36-19374a9259e1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	DN-2026-001	2442b9be-c640-4f8f-9a87-e07fb8ba875b	2026-02-11 11:15:40.269144+00	draft	cbf290a6-91cb-4c93-b9a6-db408bb3c274	\N	\N	\N	Standard delivery	\N	\N	\N	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
fc30c4d9-cb9c-44d4-9c3e-cc1f35f41d59	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	DN-2026-002	60b23cd6-744b-495f-98e7-4730a6c1c1f9	2026-02-11 11:15:40.269144+00	draft	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	\N	\N	Bulk shipment	\N	\N	\N	\N	2026-02-11 11:15:40.269144+00	2026-02-11 11:15:40.269144+00
\.


--
-- Data for Name: invoice_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.invoice_items (id, organization_id, invoice_id, item_id, item_code, item_name, qty, uom, rate, amount, sort_order, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: invoices; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.invoices (id, organization_id, invoice_no, invoice_type, party_id, party_type, posting_date, due_date, status, grand_total, outstanding_amount, currency, reference_type, reference_id, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: item_groups; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.item_groups (id, organization_id, name, code, description, parent_id, default_valuation_method, default_uom, is_active, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
76fb273a-70cd-45a1-bbc7-fbb370f09b2b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Raw Materials	RAW	Raw materials for production	\N	fifo	Kg	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
d3478470-32a3-4db2-b665-195920b44a7e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Finished Goods	FG	Finished products ready for sale	\N	fifo	Nos	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
39de3d18-f925-4b09-875b-338e21bc2a7d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Consumables	CONS	Consumable items	\N	moving_average	Nos	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
324ef9a3-dc4a-479b-be37-cc5f23ff2ea3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Services	SVC	Service items	\N	\N	Hour	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
c9d50dc8-0afd-4540-aedd-90d0373175b7	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Metals	RAW-MTL	Metal raw materials	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	fifo	Kg	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
e07dc93d-1f02-4f1a-bf9d-255c1490f157	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Plastics	RAW-PLS	Plastic raw materials	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	fifo	Kg	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
feacdbde-f4db-4725-b2bc-0efe83d84692	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Electronics	FG-ELEC	Electronic products	d3478470-32a3-4db2-b665-195920b44a7e	fifo	Nos	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
59057b72-15a8-46a7-bae8-104c7fc73dbe	9a9b7483-4327-46f6-852b-70c5faab67d4	KIDS-ITEM	KID-P001	KIDS-ITEM	\N	fifo	Piece	t	{}	661678e8-12df-44bc-b50a-d69538eb9590	661678e8-12df-44bc-b50a-d69538eb9590	2026-02-05 16:47:06.042179+00	2026-02-05 16:47:06.042471+00	\N
\.


--
-- Data for Name: item_prices; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.item_prices (id, organization_id, item_id, price_list_id, price, currency, valid_from, valid_upto, min_qty, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: item_suppliers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.item_suppliers (id, organization_id, item_id, supplier_id, supplier_part_no, lead_time_days, is_default, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.items (id, organization_id, item_code, item_name, description, item_group_id, uom, maintain_stock, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at, item_type, valuation_method, status) FROM stdin;
774bcea0-9782-46cc-8477-038d1f04123f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RAMA-T-002	RAMA Mixture	string	\N	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	01209123910	string	["string"]	["raw"]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-05 11:06:03.615639+00	2026-02-05 11:06:03.615655+00	\N	stock	fifo	active
6d7aea17-8e88-4126-93c5-4bab41900c18	9a9b7483-4327-46f6-852b-70c5faab67d4	ELC-001	Kids Blanket	teset kk	59057b72-15a8-46a7-bae8-104c7fc73dbe	Piece	t	f	f	\N	{}	f	f			12498.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	null	661678e8-12df-44bc-b50a-d69538eb9590	661678e8-12df-44bc-b50a-d69538eb9590	2026-02-05 17:45:24.31734+00	2026-02-05 17:45:24.317358+00	\N	stock	fifo	active
3531e02a-28dc-4659-9a76-70fa0c12c933	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	GD-ALIM-008	New Gold Alloy Mixture	string	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	01209123910	string	["string"]	["raw"]	{}	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	2026-01-27 17:25:25.840176+00	stock	fifo	active
1aff047b-e5b2-4e0e-9626-b3cbdc23384e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0010	Product Name 10	Automated description for item 10	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	283.48	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000010	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
0a75cf03-8b5b-471b-8d0d-0a4c2f194999	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0011	Product Name 11	Automated description for item 11	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	206.37	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000011	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
d92b4647-a8d5-42d4-83b1-e33bf19dd414	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALM-011	Aluminium 		feacdbde-f4db-4725-b2bc-0efe83d84692	Kilogram	t	f	f	\N	{}	f	f			1990.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
07423f9a-c153-426b-84d3-9d37431fa4fa	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALIM-005	Wrong Alloy Mixture		76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	{}	f	f			1090.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
ba33b62c-d77a-4e04-b4a9-0c047009d020	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALUM-001	Aluminum Alloy		76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Kg	t	f	f	\N	{}	f	f			7180.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
4df44234-2b66-4867-bf03-95871df0a629	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0012	Product Name 12	Automated description for item 12	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	217.80	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000012	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
7428ed48-7878-40b7-b0cb-bd8e24fdaf23	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0013	Product Name 13	Automated description for item 13	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	147.42	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000013	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
3a652a33-b63b-4999-a339-ec5eb3fa4e47	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0014	Product Name 14	Automated description for item 14	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	244.93	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000014	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
3f5d86f2-c1be-47b5-b30d-8a77da614a5c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0015	Product Name 15	Automated description for item 15	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	757.63	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000015	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
fbe3d99c-317c-4581-b8e4-b2f5addaebb4	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0016	Product Name 16	Automated description for item 16	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	314.89	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000016	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
92fb86ac-8eab-4def-83a8-8f0f89f23d27	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0017	Product Name 17	Automated description for item 17	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	746.92	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000017	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
044e2abb-4453-4dd5-9bd4-ddec3e160dc8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0018	Product Name 18	Automated description for item 18	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	376.90	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000018	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
14f5e13e-191c-470a-b7f0-b32eeea5d334	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0019	Product Name 19	Automated description for item 19	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	475.03	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000019	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
6b6d8cf5-d9e9-4089-838d-8aaed54bf0fe	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0020	Product Name 20	Automated description for item 20	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	448.10	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000020	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
56a227c6-4a4a-4081-911d-4ab1e7151d14	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0021	Product Name 21	Automated description for item 21	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	63.77	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000021	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
e508d5f1-64c5-4f85-ac40-86148eb86cfb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0022	Product Name 22	Automated description for item 22	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	233.60	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000022	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
7b5b97dd-29ad-4632-8579-9a59e95fb781	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0023	Product Name 23	Automated description for item 23	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	173.46	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000023	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
e6efdcf2-b424-4951-8de5-a02d082763c5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0024	Product Name 24	Automated description for item 24	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	488.17	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000024	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
f6ae0d88-c1cc-4369-bc24-e22798a8a0c1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0025	Product Name 25	Automated description for item 25	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	593.05	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000025	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
17128173-ee67-4bd6-95a9-1b5b66dcf9a8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0026	Product Name 26	Automated description for item 26	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	619.40	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000026	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
6ac33ea2-c608-4e60-a832-0d1dcdde0d3e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0027	Product Name 27	Automated description for item 27	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	412.44	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000027	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
f1fb4d2e-1659-4387-990e-5426b9063fc4	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0028	Product Name 28	Automated description for item 28	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	29.94	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000028	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
985e0a23-a0f4-4c5c-a786-0e1483b2ddc6	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0029	Product Name 29	Automated description for item 29	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	945.02	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000029	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
f0bab02b-ceb6-4b4d-9a2c-fc58c3788c74	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0030	Product Name 30	Automated description for item 30	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	309.80	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000030	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
78c95742-dbef-49dd-8d74-769eb72fdb7a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0031	Product Name 31	Automated description for item 31	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	268.23	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000031	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
bcca67f1-97d2-40e7-b4f6-c5c014c96452	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0032	Product Name 32	Automated description for item 32	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	668.67	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000032	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
bc1d123e-0bd2-4be3-8e88-7652a1b3abbb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0033	Product Name 33	Automated description for item 33	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	743.91	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000033	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
df5873e7-9c97-402b-8b3b-998c6803cb71	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0034	Product Name 34	Automated description for item 34	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	324.26	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000034	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
9016d442-437f-4419-9b32-dc969172b287	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0035	Product Name 35	Automated description for item 35	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	582.72	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000035	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
9485cb3e-ddb2-4edf-a925-6b0cd9549eff	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0036	Product Name 36	Automated description for item 36	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	125.26	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000036	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
a73c23ce-8da4-4a52-a710-0da6d6fa812f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0037	Product Name 37	Automated description for item 37	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	854.32	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000037	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
4b32a5f1-1533-4e85-b562-7c40db9811ce	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0038	Product Name 38	Automated description for item 38	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	179.12	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000038	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
f1b7361f-4c5c-441d-acb1-c54d2ac2149c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0039	Product Name 39	Automated description for item 39	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	808.55	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000039	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
d914fbb1-1dc1-4b71-b4b2-9192b568df94	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0040	Product Name 40	Automated description for item 40	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	426.62	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000040	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
a92c6265-2c2a-4627-8532-2eb95cf84705	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0041	Product Name 41	Automated description for item 41	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	147.44	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000041	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
c18c6f8a-8b05-4b5a-803d-02d2d37c4f56	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0042	Product Name 42	Automated description for item 42	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	665.08	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000042	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
ba4cd139-8228-4708-99fd-e895e4f72f69	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0043	Product Name 43	Automated description for item 43	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	710.75	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000043	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
36c55607-d071-4644-ad5d-df30137508bb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0044	Product Name 44	Automated description for item 44	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	630.88	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000044	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
7405543d-3488-4964-84b9-43236b406dee	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0045	Product Name 45	Automated description for item 45	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	360.37	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000045	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
99adc56b-6e2e-42b3-9410-389556724321	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0046	Product Name 46	Automated description for item 46	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	725.66	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000046	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
825451c1-58d5-4c8c-a6a0-9b8dd924c3ae	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0047	Product Name 47	Automated description for item 47	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	22.92	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000047	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
c6ffe2ce-206f-401a-a135-b7ea90323e38	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0048	Product Name 48	Automated description for item 48	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	623.84	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000048	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
c33fb4f7-3987-4745-8127-fbcc91abacaf	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0049	Product Name 49	Automated description for item 49	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	544.95	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000049	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
08c7526a-acb7-43a2-aa6d-51b7c4c62912	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0050	Product Name 50	Automated description for item 50	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	19.27	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000050	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
d7193ba6-7cde-4a61-a77f-027b4b5ff69b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0051	Product Name 51	Automated description for item 51	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	695.84	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000051	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
818a4725-f599-4129-a4b8-22ffb0e7616c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0052	Product Name 52	Automated description for item 52	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	509.38	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000052	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
24ef10e3-d4e6-4706-b6a9-890c8ab8e421	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0053	Product Name 53	Automated description for item 53	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	94.46	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000053	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
e8589e63-1d60-49d1-9b74-939b30853b9a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0054	Product Name 54	Automated description for item 54	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	713.74	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000054	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
617169c2-4959-48bb-99aa-53dd67183dc4	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0055	Product Name 55	Automated description for item 55	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	763.55	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000055	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
0ef21358-bd1d-43c0-85aa-4102cd84ad5b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0056	Product Name 56	Automated description for item 56	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	208.31	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000056	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
8c79effc-cf44-4f68-b576-4b8b4b3436fb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0057	Product Name 57	Automated description for item 57	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	742.78	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000057	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
a5bb325a-4531-4961-abdf-0cf77b02967f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0058	Product Name 58	Automated description for item 58	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	246.28	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000058	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
0ceb88e2-cf25-405f-8370-164d1f1c9ed8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0059	Product Name 59	Automated description for item 59	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	96.34	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000059	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
62dfb5a7-d34a-4ded-907e-3d2971108334	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0060	Product Name 60	Automated description for item 60	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	378.94	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000060	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
4304c722-ab79-455f-9038-90b1ae1f6f80	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0061	Product Name 61	Automated description for item 61	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	230.86	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000061	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
74968814-ed13-4ad8-9a17-0710517d6cb1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0062	Product Name 62	Automated description for item 62	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	731.29	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000062	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
7f4e0575-f49e-42c4-908a-bae05d1115ae	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0063	Product Name 63	Automated description for item 63	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	895.70	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000063	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
251da877-2817-4ae9-a96a-6749ceeca2fa	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0064	Product Name 64	Automated description for item 64	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	103.89	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000064	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
2dafca5d-a09d-46da-98da-49c3fae4661b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0065	Product Name 65	Automated description for item 65	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	571.66	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000065	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
3e6c18b1-a00c-4b3b-9e32-b88a6cc5dc52	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0066	Product Name 66	Automated description for item 66	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	366.86	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000066	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
25f3a0f7-3546-4e47-898f-0a1aedae6703	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0067	Product Name 67	Automated description for item 67	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	949.63	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000067	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
9fea51bf-89ca-43ec-ab97-b605b01f39a9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0068	Product Name 68	Automated description for item 68	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	558.34	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000068	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
c380c7d2-b606-4182-8582-17734df62899	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0069	Product Name 69	Automated description for item 69	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	80.00	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000069	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
b00fadb0-e154-4e5c-a07d-608e539c0731	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0070	Product Name 70	Automated description for item 70	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	513.20	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000070	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
65042b50-5164-4ecc-93aa-ed48db6ea38a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0071	Product Name 71	Automated description for item 71	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	425.38	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000071	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
1dc128f4-9d44-4fd5-89ce-36c23c0b32c4	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0072	Product Name 72	Automated description for item 72	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	609.70	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000072	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
18024aa3-241d-4f8e-bb04-d9a4272bde76	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0073	Product Name 73	Automated description for item 73	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	279.17	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000073	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
12b6bae0-8bf7-4606-8815-bc7863797f4f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0074	Product Name 74	Automated description for item 74	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	11.63	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000074	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
9e401582-e388-4646-b30c-7208ca0de2a0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0075	Product Name 75	Automated description for item 75	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	151.72	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000075	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
8e4d90cd-79b4-4003-8347-bedbf618fc0a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0076	Product Name 76	Automated description for item 76	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	278.57	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000076	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
9056fdb3-e69d-4ca5-befc-48bdb8ce93a5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0077	Product Name 77	Automated description for item 77	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	550.09	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000077	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
c93c8504-8a90-4e8c-9fd6-90c0e89d53c6	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0078	Product Name 78	Automated description for item 78	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	751.83	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000078	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
bbb9b5f8-7c67-4725-a8f4-d586248c7f44	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0079	Product Name 79	Automated description for item 79	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	803.85	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000079	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
c1ba745d-be91-419a-a1d8-e7d5502fd29e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0080	Product Name 80	Automated description for item 80	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	388.38	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000080	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
a1983ea4-8435-4c26-86fc-d514cf40477f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0081	Product Name 81	Automated description for item 81	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	341.06	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000081	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
7563c7ad-d144-44ed-bcf4-45a0f5692a92	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0082	Product Name 82	Automated description for item 82	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	92.64	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000082	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
cd3655b8-d0d0-458d-a28b-693604611080	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0083	Product Name 83	Automated description for item 83	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	697.89	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000083	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
63e1764c-6260-4508-9faa-0665ee4f7235	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	FG-SENS-100	Smart Hub		76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Kilogram	t	f	f	\N	{}	f	f			7272.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
bd1e4222-f62c-4842-a694-4383bc85c114	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALM-019	Aluminum Alloy		feacdbde-f4db-4725-b2bc-0efe83d84692	Box	t	f	f	\N	{}	f	f			9090.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
eb547f3c-366c-46da-b001-4b1d717f9819	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ECL-001	TV Set	teste	feacdbde-f4db-4725-b2bc-0efe83d84692	Box	t	f	f	\N	{}	f	f			98089.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
6fea9782-695f-4b94-9576-d26fd7ace5c9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0001	Product Name 1	Automated description for item 1	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	312.81	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000001	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
6222e197-5aa6-400c-acf5-3afa77170ba4	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0002	Product Name 2	Automated description for item 2	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	835.88	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000002	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
fbde6d49-cd5a-4aa6-906a-2d970462a50f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0003	Product Name 3	Automated description for item 3	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	205.38	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000003	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
f206a78a-69d0-40e0-9cb8-2981546cc824	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0004	Product Name 4	Automated description for item 4	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	521.77	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000004	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
0aeeead7-ce60-4310-bce9-ae3c65b36bc3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALIM-002	Alloy Mixture updated		76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	{}	f	f			7860.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
fe55f5e5-ec13-441c-9c4b-e5c94aea5d4a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0005	Product Name 5	Automated description for item 5	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	99.87	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000005	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
66bd1fa7-a019-4635-a77d-19b852e7473e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0006	Product Name 6	Automated description for item 6	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	387.03	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000006	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
e83aa776-bbb3-423e-b77d-fc4810f634af	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0007	Product Name 7	Automated description for item 7	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	190.69	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000007	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
4ef94827-d751-4feb-bd1e-dbc2d9673a10	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0008	Product Name 8	Automated description for item 8	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	750.92	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000008	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
d38bbd60-d9ba-4f92-9677-ba8718bb4812	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0009	Product Name 9	Automated description for item 9	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	418.80	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000009	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
42f7d72f-3a80-4e28-9e32-16dbdcf87d6f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALIM-007	Wrong Again Alloy Mixture	string	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	01209123912	string	["string"]	["raw"]	{}	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	2026-01-27 17:23:09.383365+00	stock	fifo	active
b9819211-25e6-4017-b621-e8746e838248	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0084	Product Name 84	Automated description for item 84	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	593.40	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000084	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
06e78d5a-c49e-490b-86c4-ad898cc455b0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0085	Product Name 85	Automated description for item 85	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Mtr	t	\N	\N	\N	\N	\N	\N	\N	\N	433.89	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000085	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
b1be71c2-e4bb-4257-860a-4390c1c8d5e8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0086	Product Name 86	Automated description for item 86	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	536.16	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000086	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
0b832dc9-6ee5-40bf-89cb-00089dd721fa	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0087	Product Name 87	Automated description for item 87	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	329.03	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000087	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
dc2d8b27-e2bf-4917-b562-6b77242cd28d	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0088	Product Name 88	Automated description for item 88	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	765.72	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000088	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
f31cbbfe-e82a-46a6-8362-e7b90b6135b2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0089	Product Name 89	Automated description for item 89	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	124.86	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000089	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
97b3daae-1b07-4510-98b1-e70b62a91014	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0090	Product Name 90	Automated description for item 90	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	260.08	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000090	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
3c5fe391-461e-4f9d-85db-4588bba4d5f6	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0091	Product Name 91	Automated description for item 91	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	20.07	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000091	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
e1ffade5-31d3-472e-b8ce-6406d29e66d1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0092	Product Name 92	Automated description for item 92	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	888.02	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000092	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
99c426f9-fc20-43b0-b02d-f2a2f723f0b3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0093	Product Name 93	Automated description for item 93	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	998.26	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000093	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
449bda0e-04b0-4492-8991-20eba6ca3d50	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0094	Product Name 94	Automated description for item 94	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	182.07	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000094	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
a5ea5eb5-39eb-4541-98d4-c09dca5b1876	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0095	Product Name 95	Automated description for item 95	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	98.35	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000095	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
1ef35d6b-54c1-4150-b9eb-9695801c29d0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0096	Product Name 96	Automated description for item 96	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	678.19	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000096	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
a7983a9a-0e36-4c2e-b7a2-64467970c9ba	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0097	Product Name 97	Automated description for item 97	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	328.51	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000097	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
5940c700-6a52-4598-bca4-19146dca79b3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0098	Product Name 98	Automated description for item 98	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	\N	\N	\N	\N	\N	\N	\N	\N	466.89	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000098	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
02c63781-4aa4-483d-b1d0-ea4e4bee5fdf	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0099	Product Name 99	Automated description for item 99	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Kg	t	\N	\N	\N	\N	\N	\N	\N	\N	951.01	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000099	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
a3d655b0-2065-45a6-ba4e-7200a165956c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM-0100	Product Name 100	Automated description for item 100	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Box	t	\N	\N	\N	\N	\N	\N	\N	\N	523.07	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	8900000000100	\N	\N	\N	\N	\N	\N	\N	2026-02-04 10:12:34.46293+00	2026-02-04 10:12:34.46293+00	\N	stock	fifo	active
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
-- Data for Name: payment_allocations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.payment_allocations (id, organization_id, payment_id, invoice_id, allocated_amount, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.payments (id, organization_id, payment_no, payment_type, party_id, party_type, posting_date, amount, status, payment_method, reference_no, remarks, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: pick_list_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.pick_list_items (id, organization_id, pick_list_id, item_id, warehouse_id, qty, picked_qty, uom, batch_no, serial_nos, sort_order, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: pick_lists; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.pick_lists (id, organization_id, pick_list_no, warehouse_id, status, pick_date, reference_type, reference_id, remarks, completed_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: purchase_receipt_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.purchase_receipt_items (id, organization_id, purchase_receipt_id, item_id, qty, uom, rate, amount, warehouse_id, batch_no, serial_nos, sort_order, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: purchase_receipts; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.purchase_receipts (id, organization_id, purchase_receipt_no, supplier_id, receipt_date, status, warehouse_id, reference_type, reference_id, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: put_away_rules; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.put_away_rules (id, organization_id, name, item_id, item_group_id, warehouse_id, capacity, priority, min_qty, max_qty, is_active, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: quotation_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.quotation_items (id, organization_id, quotation_id, item_id, qty, uom, rate, amount, sort_order, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: quotations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.quotations (id, organization_id, quotation_no, customer_id, quotation_date, valid_until, status, grand_total, currency, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: sales_order_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.sales_order_items (id, organization_id, sales_order_id, item_id, qty, uom, rate, amount, billed_qty, delivered_qty, sort_order, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: sales_orders; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.sales_orders (id, organization_id, sales_order_no, customer_id, order_date, delivery_date, status, grand_total, currency, reference_type, reference_id, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
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
-- Data for Name: stock_entries; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_entries (id, organization_id, stock_entry_no, stock_entry_type, from_warehouse_id, to_warehouse_id, posting_date, posting_time, status, reference_type, reference_id, remarks, total_value, expense_account_id, cost_center_id, is_backflush, bom_id, extra_data, submitted_at, cancelled_at, created_at, updated_at, created_by, updated_by) FROM stdin;
469fc274-3ef9-4630-88d4-32bdb3086e08	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	STE-2024-001	material_receipt	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	2026-01-10 11:59:11.034338+00	10:30:00	submitted	\N	\N	Initial stock receipt	50000.00	\N	\N	\N	\N	null	2026-01-10 11:59:11.034338+00	\N	2026-02-09 11:59:11.035598+00	2026-02-09 11:59:11.0356+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
987fdc7f-962a-49bd-97ab-799748c3f89f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	STE-2024-002	material_receipt	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	2026-01-12 11:59:11.034338+00	14:00:00	submitted	\N	\N	Production receipt	90500.00	\N	\N	\N	\N	null	2026-01-12 11:59:11.034338+00	\N	2026-02-09 11:59:11.038237+00	2026-02-09 11:59:11.03824+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
529f11d2-0955-4b02-ba22-e9787080290c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	STE-2024-003	material_transfer	cbf290a6-91cb-4c93-b9a6-db408bb3c274	3c7956f3-d57a-4a01-936b-6d6cf98de665	2026-01-15 11:59:11.034338+00	11:00:00	submitted	\N	\N	Transfer from Main Warehouse to Retail Store	25500.00	\N	\N	\N	\N	null	2026-01-15 11:59:11.034338+00	\N	2026-02-09 11:59:11.043151+00	2026-02-09 11:59:11.043153+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
7ae70bdd-6f74-4dc4-8a8e-c644dab7ce61	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	STE-2024-004	material_issue	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	2026-01-20 11:59:11.034338+00	15:30:00	submitted	\N	\N	Sales/Issue	7250.00	\N	\N	\N	\N	null	2026-01-20 11:59:11.034338+00	\N	2026-02-09 11:59:11.044879+00	2026-02-09 11:59:11.04488+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
\.


--
-- Data for Name: stock_entry_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_entry_items (id, organization_id, stock_entry_id, item_id, source_warehouse_id, target_warehouse_id, qty, uom, basic_rate, basic_amount, valuation_rate, batch_no, serial_nos, quality_inspection_id, description, extra_data, created_at, updated_at) FROM stdin;
8dc91589-3771-4dca-ac6e-fda17944aa3a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	469fc274-3ef9-4630-88d4-32bdb3086e08	774bcea0-9782-46cc-8477-038d1f04123f	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	500.000	Nos	75.00	37500.00	75.00	\N	null	\N	RAMA Mixture - initial stock	null	2026-02-09 11:59:11.039142+00	2026-02-09 11:59:11.039143+00
3cd9024b-4333-44b8-a6dd-e83ee1fbd43b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	469fc274-3ef9-4630-88d4-32bdb3086e08	3531e02a-28dc-4659-9a76-70fa0c12c933	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	125.000	Nos	100.00	12500.00	100.00	\N	null	\N	New Gold Alloy Mixture - initial stock	null	2026-02-09 11:59:11.039145+00	2026-02-09 11:59:11.039145+00
8d081429-e7aa-4a0a-8f17-8a7e26ad7d5a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	987fdc7f-962a-49bd-97ab-799748c3f89f	1aff047b-e5b2-4e0e-9626-b3cbdc23384e	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	100.000	Nos	350.00	35000.00	350.00	\N	null	\N	Product Name 10 units	null	2026-02-09 11:59:11.043545+00	2026-02-09 11:59:11.043546+00
cfcb31b8-8ee4-43b4-8971-fead14817cc8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	987fdc7f-962a-49bd-97ab-799748c3f89f	0a75cf03-8b5b-471b-8d0d-0a4c2f194999	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	50.000	Nos	750.00	37500.00	750.00	\N	null	\N	Product Name 11 units	null	2026-02-09 11:59:11.043548+00	2026-02-09 11:59:11.043548+00
42391b50-0805-474e-8580-7c09ce07e676	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	987fdc7f-962a-49bd-97ab-799748c3f89f	d92b4647-a8d5-42d4-83b1-e33bf19dd414	\N	cbf290a6-91cb-4c93-b9a6-db408bb3c274	1000.000	Kilogram	18.00	18000.00	18.00	\N	null	\N	Aluminium  units	null	2026-02-09 11:59:11.04355+00	2026-02-09 11:59:11.04355+00
831868b8-bed5-4798-bb63-eeee23868584	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	529f11d2-0955-4b02-ba22-e9787080290c	1aff047b-e5b2-4e0e-9626-b3cbdc23384e	cbf290a6-91cb-4c93-b9a6-db408bb3c274	3c7956f3-d57a-4a01-936b-6d6cf98de665	30.000	Nos	350.00	10500.00	350.00	\N	null	\N	Transfer	null	2026-02-09 11:59:11.045163+00	2026-02-09 11:59:11.045164+00
88c274b1-9717-474e-a5f9-62d12d7fd2cf	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	529f11d2-0955-4b02-ba22-e9787080290c	0a75cf03-8b5b-471b-8d0d-0a4c2f194999	cbf290a6-91cb-4c93-b9a6-db408bb3c274	3c7956f3-d57a-4a01-936b-6d6cf98de665	20.000	Nos	750.00	15000.00	750.00	\N	null	\N	Transfer	null	2026-02-09 11:59:11.045166+00	2026-02-09 11:59:11.045166+00
da2352ca-b5bb-4ec6-ad80-be5a0706a722	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	7ae70bdd-6f74-4dc4-8a8e-c644dab7ce61	1aff047b-e5b2-4e0e-9626-b3cbdc23384e	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	10.000	Nos	350.00	3500.00	350.00	\N	null	\N	Sold	null	2026-02-09 11:59:11.046607+00	2026-02-09 11:59:11.046607+00
b3e3beca-4a59-4b80-8f5c-a2a1109ce459	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	7ae70bdd-6f74-4dc4-8a8e-c644dab7ce61	0a75cf03-8b5b-471b-8d0d-0a4c2f194999	3c7956f3-d57a-4a01-936b-6d6cf98de665	\N	5.000	Nos	750.00	3750.00	750.00	\N	null	\N	Sold	null	2026-02-09 11:59:11.046609+00	2026-02-09 11:59:11.04661+00
\.


--
-- Data for Name: stock_levels; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_levels (id, organization_id, product_id, warehouse_id, quantity_on_hand, quantity_reserved, quantity_available, last_counted_at, created_at, updated_at) FROM stdin;
8e15d1e9-97bd-4a33-a1f8-4d3df506a458	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	774bcea0-9782-46cc-8477-038d1f04123f	cbf290a6-91cb-4c93-b9a6-db408bb3c274	500	50	450	2026-02-08 11:59:11.046113+00	2026-02-09 11:59:11.047375+00	2026-02-09 11:59:11.047376+00
b842eb6c-9440-486e-b311-fabbe2bbe211	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	3531e02a-28dc-4659-9a76-70fa0c12c933	cbf290a6-91cb-4c93-b9a6-db408bb3c274	125	25	100	2026-02-08 11:59:11.046156+00	2026-02-09 11:59:11.047378+00	2026-02-09 11:59:11.047379+00
6d0c8a9a-aae4-4cfa-a470-a37f4a04f0cb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1aff047b-e5b2-4e0e-9626-b3cbdc23384e	cbf290a6-91cb-4c93-b9a6-db408bb3c274	70	10	60	2026-02-08 11:59:11.046173+00	2026-02-09 11:59:11.04738+00	2026-02-09 11:59:11.047381+00
c9f27747-1a34-4159-ba33-0e91486c91eb	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	0a75cf03-8b5b-471b-8d0d-0a4c2f194999	cbf290a6-91cb-4c93-b9a6-db408bb3c274	30	5	25	2026-02-08 11:59:11.046186+00	2026-02-09 11:59:11.047382+00	2026-02-09 11:59:11.047382+00
0fd1baf0-d2a4-446d-9c78-66c806c877fc	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d92b4647-a8d5-42d4-83b1-e33bf19dd414	cbf290a6-91cb-4c93-b9a6-db408bb3c274	1000	100	900	2026-02-08 11:59:11.046198+00	2026-02-09 11:59:11.047384+00	2026-02-09 11:59:11.047384+00
87f24643-d587-49c6-9443-fa556298d8c6	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1aff047b-e5b2-4e0e-9626-b3cbdc23384e	3c7956f3-d57a-4a01-936b-6d6cf98de665	20	0	20	2026-02-08 11:59:11.046211+00	2026-02-09 11:59:11.047386+00	2026-02-09 11:59:11.047386+00
311b8b89-839f-4fbd-82b7-945883e08bb0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	0a75cf03-8b5b-471b-8d0d-0a4c2f194999	3c7956f3-d57a-4a01-936b-6d6cf98de665	15	0	15	2026-02-08 11:59:11.046222+00	2026-02-09 11:59:11.047387+00	2026-02-09 11:59:11.047388+00
\.


--
-- Data for Name: stock_movements; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_movements (id, organization_id, product_id, warehouse_id, movement_type, quantity, unit_cost, reference_type, reference_id, notes, performed_by, performed_at, created_at, updated_at) FROM stdin;
a481e081-cddd-4980-b068-e4ed0dcf68d1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	774bcea0-9782-46cc-8477-038d1f04123f	cbf290a6-91cb-4c93-b9a6-db408bb3c274	in	500	75.00	stock_entry	469fc274-3ef9-4630-88d4-32bdb3086e08	Receipt - RAMA Mixture	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	2026-01-10 11:59:11.034338+00	2026-02-09 11:59:11.049439+00	2026-02-09 11:59:11.04944+00
a67ef1a8-7f1e-4a3f-b9cf-65c2bdc3fcd8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	3531e02a-28dc-4659-9a76-70fa0c12c933	cbf290a6-91cb-4c93-b9a6-db408bb3c274	in	125	100.00	stock_entry	469fc274-3ef9-4630-88d4-32bdb3086e08	Receipt - New Gold Alloy Mixture	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	2026-01-10 11:59:11.034338+00	2026-02-09 11:59:11.049442+00	2026-02-09 11:59:11.049442+00
9a01f023-6191-4665-abd4-78a25b38a1e5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1aff047b-e5b2-4e0e-9626-b3cbdc23384e	cbf290a6-91cb-4c93-b9a6-db408bb3c274	in	100	350.00	stock_entry	987fdc7f-962a-49bd-97ab-799748c3f89f	Receipt - Product Name 10	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	2026-01-12 11:59:11.034338+00	2026-02-09 11:59:11.049444+00	2026-02-09 11:59:11.049444+00
1ec582b2-8b9c-4037-861d-be4d5683cab0	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	0a75cf03-8b5b-471b-8d0d-0a4c2f194999	cbf290a6-91cb-4c93-b9a6-db408bb3c274	in	50	750.00	stock_entry	987fdc7f-962a-49bd-97ab-799748c3f89f	Receipt - Product Name 11	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	2026-01-12 11:59:11.034338+00	2026-02-09 11:59:11.049446+00	2026-02-09 11:59:11.049446+00
56a04ea9-f9e2-4a7d-b9d8-3c345f32d8fc	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d92b4647-a8d5-42d4-83b1-e33bf19dd414	cbf290a6-91cb-4c93-b9a6-db408bb3c274	in	1000	18.00	stock_entry	987fdc7f-962a-49bd-97ab-799748c3f89f	Receipt - Aluminium 	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	2026-01-12 11:59:11.034338+00	2026-02-09 11:59:11.049448+00	2026-02-09 11:59:11.049448+00
6561b9d3-25b9-4da4-8044-ddb656227484	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1aff047b-e5b2-4e0e-9626-b3cbdc23384e	cbf290a6-91cb-4c93-b9a6-db408bb3c274	out	30	350.00	stock_entry	529f11d2-0955-4b02-ba22-e9787080290c	Transfer out - Product Name 10	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	2026-01-15 11:59:11.034338+00	2026-02-09 11:59:11.049449+00	2026-02-09 11:59:11.04945+00
b84b2c83-ae77-499b-9aae-61063b720d97	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1aff047b-e5b2-4e0e-9626-b3cbdc23384e	3c7956f3-d57a-4a01-936b-6d6cf98de665	in	30	350.00	stock_entry	529f11d2-0955-4b02-ba22-e9787080290c	Transfer in - Product Name 10	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	2026-01-15 11:59:11.034338+00	2026-02-09 11:59:11.049451+00	2026-02-09 11:59:11.049451+00
bba87dca-a408-4f41-bcb7-46684790aa84	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	0a75cf03-8b5b-471b-8d0d-0a4c2f194999	cbf290a6-91cb-4c93-b9a6-db408bb3c274	out	20	750.00	stock_entry	529f11d2-0955-4b02-ba22-e9787080290c	Transfer out - Product Name 11	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	2026-01-15 11:59:11.034338+00	2026-02-09 11:59:11.049453+00	2026-02-09 11:59:11.049453+00
53881217-ad58-4408-8d8b-a36be2a9544e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	0a75cf03-8b5b-471b-8d0d-0a4c2f194999	3c7956f3-d57a-4a01-936b-6d6cf98de665	in	20	750.00	stock_entry	529f11d2-0955-4b02-ba22-e9787080290c	Transfer in - Product Name 11	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	2026-01-15 11:59:11.034338+00	2026-02-09 11:59:11.049455+00	2026-02-09 11:59:11.049455+00
96bfa1e1-6066-4b87-a39b-4655d767006c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	1aff047b-e5b2-4e0e-9626-b3cbdc23384e	3c7956f3-d57a-4a01-936b-6d6cf98de665	out	10	350.00	stock_entry	7ae70bdd-6f74-4dc4-8a8e-c644dab7ce61	Issue/Sale - Product Name 10	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	2026-01-20 11:59:11.034338+00	2026-02-09 11:59:11.049457+00	2026-02-09 11:59:11.049457+00
60f89b4d-31a9-47bd-8fd9-6ab2e29ca3f1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	0a75cf03-8b5b-471b-8d0d-0a4c2f194999	3c7956f3-d57a-4a01-936b-6d6cf98de665	out	5	750.00	stock_entry	7ae70bdd-6f74-4dc4-8a8e-c644dab7ce61	Issue/Sale - Product Name 11	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	2026-01-20 11:59:11.034338+00	2026-02-09 11:59:11.049458+00	2026-02-09 11:59:11.049459+00
\.


--
-- Data for Name: stock_reconciliation_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_reconciliation_items (id, organization_id, reconciliation_id, item_id, warehouse_id, current_qty, qty, qty_difference, current_valuation_rate, valuation_rate, batch_no, serial_nos, extra_data, created_at, updated_at) FROM stdin;
6669b454-e6a9-404a-92c1-4f1f313a59d5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	565847ad-58a9-44c6-8cc1-a95e36531980	1aff047b-e5b2-4e0e-9626-b3cbdc23384e	cbf290a6-91cb-4c93-b9a6-db408bb3c274	70.000	68.000	-2.000	350.00	350.00	\N	null	null	2026-02-09 11:59:11.053093+00	2026-02-09 11:59:11.053094+00
90203380-a599-48d4-a1c7-c0da7578dba9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	565847ad-58a9-44c6-8cc1-a95e36531980	d92b4647-a8d5-42d4-83b1-e33bf19dd414	cbf290a6-91cb-4c93-b9a6-db408bb3c274	1000.000	995.000	-5.000	18.00	18.00	\N	null	null	2026-02-09 11:59:11.053096+00	2026-02-09 11:59:11.053096+00
fad8c0d4-1bab-49b6-9225-d7f27372c286	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	565847ad-58a9-44c6-8cc1-a95e36531980	0a75cf03-8b5b-471b-8d0d-0a4c2f194999	3c7956f3-d57a-4a01-936b-6d6cf98de665	15.000	16.000	1.000	750.00	750.00	\N	null	null	2026-02-09 11:59:11.053098+00	2026-02-09 11:59:11.053098+00
ccd396b9-1b4d-4cf2-9fe3-6cd325876924	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	46aad0ee-ed45-4b07-a2c4-1d31ca1d7392	774bcea0-9782-46cc-8477-038d1f04123f	cbf290a6-91cb-4c93-b9a6-db408bb3c274	500.000	495.000	-5.000	75.00	75.00	\N	null	null	2026-02-09 11:59:11.055564+00	2026-02-09 11:59:11.055565+00
\.


--
-- Data for Name: stock_reconciliations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_reconciliations (id, organization_id, reconciliation_no, purpose, posting_date, posting_time, status, expense_account_id, difference_account_id, remarks, extra_data, submitted_at, created_at, updated_at, created_by, updated_by) FROM stdin;
565847ad-58a9-44c6-8cc1-a95e36531980	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RECON-2024-001	Physical Stock Count - Monthly	2026-01-25 11:59:11.034338+00	16:00:00	submitted	\N	\N	Monthly physical stock verification	null	2026-01-25 11:59:11.034338+00	2026-02-09 11:59:11.051607+00	2026-02-09 11:59:11.051608+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
46aad0ee-ed45-4b07-a2c4-1d31ca1d7392	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RECON-2024-002	Damage Write-off	2026-01-30 11:59:11.034338+00	10:30:00	submitted	\N	\N	Write-off damaged items	null	2026-01-30 11:59:11.034338+00	2026-02-09 11:59:11.052487+00	2026-02-09 11:59:11.052488+00	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae
\.


--
-- Data for Name: stock_settings; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_settings (id, organization_id, item_naming_by, item_naming_series, stock_entry_naming_series, delivery_note_naming_series, purchase_receipt_naming_series, default_warehouse_id, allow_negative_stock, over_delivery_receipt_allowance, over_billing_allowance, auto_indent, auto_indent_notification, default_valuation_method, auto_create_serial_no, default_quality_inspection_template_id, stock_frozen_upto, stock_frozen_upto_days, show_barcode_field, convert_item_desc_to_transaction_desc, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: suppliers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.suppliers (id, organization_id, supplier_name, supplier_code, email, phone, address, address_line1, address_line2, city, state, postal_code, country, tax_number, status, payment_terms, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
f68137ef-49df-4ea5-8a57-fe22a0f446d2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Steel India Ltd	SUPP-001	sales@steelindia.com	+91-9812345001	\N	\N	\N	Jamshedpur	\N	\N	\N	\N	active	30	\N	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
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
e67a7363-7e48-4890-854b-605ef3e43c8b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Warehouse 3416a	3416-41	Description for warehouse 41	\N	warehouse	\N	\N	Delhi	\N	\N	India	\N	\N	\N	1713	Units	\N	t	f	\N	\N	\N	2026-02-04 13:18:07.734555+00	2026-02-04 16:17:56.270385+00	\N
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
\.


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
-- Name: chart_of_accounts chart_of_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.chart_of_accounts
    ADD CONSTRAINT chart_of_accounts_pkey PRIMARY KEY (id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


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
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (id);


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
-- Name: items items_item_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_item_group_id_fkey FOREIGN KEY (item_group_id) REFERENCES public.item_groups(id);


--
-- Name: items items_variant_of_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_variant_of_fkey FOREIGN KEY (variant_of) REFERENCES public.items(id);


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
-- Name: quotations quotations_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE RESTRICT;


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
-- Name: sales_orders sales_orders_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.sales_orders
    ADD CONSTRAINT sales_orders_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict VSWC521yBIlc02SZRRYCh304wKQQfp4FPeKNcnY646TsBuZ5abMekcBkoeXqLcW
