--
-- PostgreSQL database dump
--

\restrict CnB3efe9nMk39v4jmXKOaGrN8DLQAQd90HwsgSFedPl9QkVjqc1qA7w3SBtyn7n

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
-- Name: accountstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.accountstatus AS ENUM (
    'active',
    'inactive',
    'archived'
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
-- Name: accounts; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.accounts (
    id uuid NOT NULL,
    account_code character varying(50) NOT NULL,
    account_name character varying(200) NOT NULL,
    account_type public.accounttype NOT NULL,
    parent_account_id uuid,
    currency character varying(3) NOT NULL,
    status public.accountstatus NOT NULL,
    is_posting_account boolean NOT NULL,
    description text,
    created_by character varying(100) NOT NULL,
    updated_by character varying(100) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
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
-- Name: bulk_export_jobs; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.bulk_export_jobs (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_by_id uuid NOT NULL,
    file_name character varying(255) NOT NULL,
    file_path character varying(255),
    file_format character varying(20) NOT NULL,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    total_rows character varying(20) DEFAULT '0'::character varying NOT NULL,
    filters jsonb,
    selected_columns jsonb,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    expires_at timestamp with time zone
);


ALTER TABLE public.bulk_export_jobs OWNER TO horizon_user;

--
-- Name: bulk_import_jobs; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.bulk_import_jobs (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_by_id uuid NOT NULL,
    file_name character varying(255) NOT NULL,
    file_path character varying(255),
    mime_type character varying(100) NOT NULL,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    total_rows integer DEFAULT 0 NOT NULL,
    successful_rows integer DEFAULT 0 NOT NULL,
    failed_rows integer DEFAULT 0 NOT NULL,
    error_details jsonb,
    summary text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone
);


ALTER TABLE public.bulk_import_jobs OWNER TO horizon_user;

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
-- Name: landed_cost_vouchers; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.landed_cost_vouchers (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    voucher_no character varying(100) NOT NULL,
    posting_date timestamp with time zone NOT NULL,
    status public.documentstatus DEFAULT 'draft'::public.documentstatus NOT NULL,
    remarks text,
    submitted_at timestamp with time zone,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
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
    deleted_at timestamp with time zone
);


ALTER TABLE public.material_requests OWNER TO horizon_user;

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
    CONSTRAINT purchase_orders_party_type_check CHECK (((party_type)::text = 'SUPPLIER'::text)),
    CONSTRAINT purchase_orders_reference_type_check CHECK (((reference_type IS NULL) OR ((reference_type)::text = 'RFQ'::text)))
);


ALTER TABLE public.purchase_orders OWNER TO horizon_user;

--
-- Name: purchase_receipt_items; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.purchase_receipt_items (
    id uuid NOT NULL,
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
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.purchase_receipt_items OWNER TO horizon_user;

--
-- Name: purchase_receipts; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.purchase_receipts (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    purchase_receipt_no character varying(100) NOT NULL,
    supplier_id uuid NOT NULL,
    receipt_date timestamp with time zone NOT NULL,
    status public.documentstatus DEFAULT 'draft'::public.documentstatus NOT NULL,
    warehouse_id uuid,
    reference_type character varying(50),
    reference_id uuid,
    remarks text,
    submitted_at timestamp with time zone,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
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
-- Data for Name: accounts; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.accounts (id, account_code, account_name, account_type, parent_account_id, currency, status, is_posting_account, description, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.alembic_version (version_num) FROM stdin;
8f1a2b3c4d5e
\.


--
-- Data for Name: batches; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.batches (id, organization_id, batch_no, item_id, manufacturing_date, expiry_date, supplier_id, supplier_batch_no, status, reference_type, reference_id, description, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: bulk_export_jobs; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.bulk_export_jobs (id, organization_id, created_by_id, file_name, file_path, file_format, status, total_rows, filters, selected_columns, error_message, created_at, updated_at, completed_at, expires_at) FROM stdin;
dd3524fd-81d9-41a7-babd-4241fdf72340	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	stock_items_export	\N	csv	PROCESSING	0	{"search": null, "status": "Active", "item_type": "Stock", "item_group_id": null}	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-05 10:35:37.470954+00	2026-02-05 10:35:37.505646+00	\N	2026-02-06 10:35:37.460093+00
b746211c-1c9f-40be-9100-3fb4d1aa99f5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	stock_items_export	\N	csv	PROCESSING	0	{"search": null, "status": "Active", "item_type": "Stock", "item_group_id": null}	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-05 10:36:52.073583+00	2026-02-05 10:36:52.097636+00	\N	2026-02-06 10:36:52.069754+00
d0808fbc-8000-4f36-8ae8-948a0162e1da	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	stock_items_export	/exports/d0808fbc-8000-4f36-8ae8-948a0162e1da/d0808fbc-8000-4f36-8ae8-948a0162e1da.csv	csv	COMPLETED	13	{"search": null, "status": "active", "item_type": "stock", "item_group_id": null}	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-05 10:37:12.175407+00	2026-02-05 10:37:12.401525+00	2026-02-05 10:37:12.388669+00	2026-02-06 10:37:12.167029+00
18f0e932-c722-487e-aec9-1b8d0e3abb45	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	items_export	\N	csv	PROCESSING	0	{"status": "Active", "item_type": "Stock"}	null	\N	2026-02-05 11:16:55.810597+00	2026-02-05 11:16:55.834988+00	\N	2026-02-06 11:16:55.803191+00
c06d8521-9bfd-41f1-9e65-35e34666af3b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	items_export_json	/exports/c06d8521-9bfd-41f1-9e65-35e34666af3b/c06d8521-9bfd-41f1-9e65-35e34666af3b.json	json	COMPLETED	0	{"search": "widget", "status": null, "item_type": null, "item_group_id": null}	null	\N	2026-02-05 10:39:09.644455+00	2026-02-05 10:55:42.072937+00	2026-02-05 10:55:42.071536+00	2026-02-06 10:39:09.642375+00
3cdb25de-1320-4f01-87d0-e0040b83e306	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	all_items_export	/exports/3cdb25de-1320-4f01-87d0-e0040b83e306/3cdb25de-1320-4f01-87d0-e0040b83e306.xlsx	xlsx	COMPLETED	13	null	null	\N	2026-02-05 10:38:03.47647+00	2026-02-05 10:57:36.914807+00	2026-02-05 10:57:36.914255+00	2026-02-06 10:38:03.474231+00
96025a13-cdc0-46ee-a8f0-428729239d24	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	items_export	\N	csv	PROCESSING	0	{"status": "Active", "item_type": "Stock"}	null	\N	2026-02-05 11:12:51.063777+00	2026-02-05 11:12:51.109278+00	\N	2026-02-06 11:12:50.595602+00
9cb41324-38a8-4968-8c75-6cc6564ce85b	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	items_export	\N	csv	PROCESSING	0	{"status": "Active", "item_type": "Stock"}	null	\N	2026-02-05 11:12:54.484754+00	2026-02-05 11:12:54.497532+00	\N	2026-02-06 11:12:54.482537+00
ecdc832c-8927-4953-9fa5-1724adecf674	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	items_export	\N	csv	PROCESSING	0	{"status": "Active", "item_type": "Stock"}	null	\N	2026-02-05 11:14:43.438442+00	2026-02-05 11:14:58.214761+00	\N	2026-02-06 11:14:43.432937+00
474a67d6-8711-4472-89c4-da45522526fe	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	items_export	\N	csv	PROCESSING	0	{"status": "Active", "item_type": "Stock"}	null	\N	2026-02-05 11:15:43.901045+00	2026-02-05 11:15:45.054238+00	\N	2026-02-06 11:15:43.896238+00
3e0f8c1e-bbfe-45f1-945d-07d0912a94f2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	items_export	\N	csv	PROCESSING	0	{"status": "active", "item_type": "Stock"}	null	\N	2026-02-05 11:17:36.201939+00	2026-02-05 11:17:36.222611+00	\N	2026-02-06 11:17:36.199762+00
dbb8c298-6a0f-4d01-86fa-f94c3d399682	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	items_export	\N	csv	PROCESSING	0	{"status": "active", "item_type": "Stock"}	null	\N	2026-02-05 11:17:49.301022+00	2026-02-05 11:17:49.310601+00	\N	2026-02-06 11:17:49.299583+00
fd6710a9-e3f9-4524-a27e-c0ab2fe234b6	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	items_export	/exports/fd6710a9-e3f9-4524-a27e-c0ab2fe234b6/fd6710a9-e3f9-4524-a27e-c0ab2fe234b6.csv	csv	COMPLETED	13	{"status": "active", "item_type": "stock"}	null	\N	2026-02-05 11:18:36.274997+00	2026-02-05 11:18:37.206989+00	2026-02-05 11:18:37.206046+00	2026-02-06 11:18:36.27294+00
e662e770-32bc-4248-ab7a-061295363939	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	items_export	/exports/e662e770-32bc-4248-ab7a-061295363939/e662e770-32bc-4248-ab7a-061295363939.xlsx	xlsx	COMPLETED	0	{"search": "widget"}	null	\N	2026-02-05 11:20:06.488272+00	2026-02-05 11:20:07.503407+00	2026-02-05 11:20:07.503016+00	2026-02-06 11:20:06.486077+00
7c2698c5-1aa1-4994-bcaf-4539099bf34d	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/7c2698c5-1aa1-4994-bcaf-4539099bf34d/7c2698c5-1aa1-4994-bcaf-4539099bf34d.xlsx	xlsx	COMPLETED	3	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-07 11:28:07.069021+00	2026-02-07 11:28:07.169834+00	2026-02-07 11:28:07.169227+00	2026-02-08 11:28:07.065914+00
8ab30f6d-c3e7-48b0-8a0a-1f177f60e71c	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	items_export	/exports/8ab30f6d-c3e7-48b0-8a0a-1f177f60e71c/8ab30f6d-c3e7-48b0-8a0a-1f177f60e71c.xlsx	xlsx	COMPLETED	0	{"search": "widget"}	null	\N	2026-02-05 11:25:54.542698+00	2026-02-05 11:25:54.630876+00	2026-02-05 11:25:54.630103+00	2026-02-06 11:25:54.537893+00
917b26e6-0d13-4e22-8040-71618f5b6447	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	stock_items_export	/exports/917b26e6-0d13-4e22-8040-71618f5b6447/917b26e6-0d13-4e22-8040-71618f5b6447.xlsx	xlsx	COMPLETED	3	null	["item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate", "id"]	\N	2026-02-07 11:12:46.926697+00	2026-02-07 11:12:47.166202+00	2026-02-07 11:12:47.165731+00	2026-02-08 11:12:46.925132+00
6e703025-84bb-43d9-967e-0b093c188d9e	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	stock_items_export	/exports/6e703025-84bb-43d9-967e-0b093c188d9e/6e703025-84bb-43d9-967e-0b093c188d9e.csv	csv	COMPLETED	3	null	["item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate", "id"]	\N	2026-02-07 11:11:48.823675+00	2026-02-07 11:11:48.892237+00	2026-02-07 11:11:48.891355+00	2026-02-08 11:11:48.811282+00
6dab3652-6545-4c4e-bf53-ac596f0f0b8a	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	stock_items_export	/exports/6dab3652-6545-4c4e-bf53-ac596f0f0b8a/6dab3652-6545-4c4e-bf53-ac596f0f0b8a.xlsx	xlsx	COMPLETED	3	null	["item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate", "id"]	\N	2026-02-07 11:20:12.934663+00	2026-02-07 11:20:13.02245+00	2026-02-07 11:20:13.022092+00	2026-02-08 11:20:12.93228+00
aa6497ed-234e-4f31-ae5d-06581126c1d3	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/aa6497ed-234e-4f31-ae5d-06581126c1d3/aa6497ed-234e-4f31-ae5d-06581126c1d3.csv	csv	COMPLETED	3	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-07 11:42:47.405392+00	2026-02-07 11:42:47.484286+00	2026-02-07 11:42:47.483238+00	2026-02-08 11:42:47.153553+00
fb4dc0f3-873c-4064-8d15-d5f231f2b733	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/fb4dc0f3-873c-4064-8d15-d5f231f2b733/fb4dc0f3-873c-4064-8d15-d5f231f2b733.csv	csv	COMPLETED	3	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-07 11:32:18.109508+00	2026-02-07 11:36:19.220362+00	2026-02-07 11:36:19.219992+00	2026-02-08 11:32:18.104573+00
030cec6f-b9fe-4fb5-a66f-8522f439f545	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/030cec6f-b9fe-4fb5-a66f-8522f439f545/030cec6f-b9fe-4fb5-a66f-8522f439f545.csv	csv	COMPLETED	3	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-07 11:29:05.226496+00	2026-02-07 11:29:05.256176+00	2026-02-07 11:29:05.255719+00	2026-02-08 11:29:05.224944+00
d450a71e-79a7-4394-9dd4-0ac1aac43faa	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/d450a71e-79a7-4394-9dd4-0ac1aac43faa/d450a71e-79a7-4394-9dd4-0ac1aac43faa.csv	csv	COMPLETED	3	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-08 16:08:57.71681+00	2026-02-08 16:08:57.784948+00	2026-02-08 16:08:57.784279+00	2026-02-09 16:08:57.70038+00
0a85efd0-60cb-49a2-8afd-6215efacdff0	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/0a85efd0-60cb-49a2-8afd-6215efacdff0/0a85efd0-60cb-49a2-8afd-6215efacdff0.csv	csv	COMPLETED	3	{"search": null, "status": "active", "item_type": "stock", "item_group_id": null}	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 08:02:26.101182+00	2026-02-12 08:02:26.159098+00	2026-02-12 08:02:26.158111+00	2026-02-13 08:02:26.086973+00
f73c1e8a-6b44-4cd7-9438-6cc1bc6d6595	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	\N	csv	PROCESSING	0	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 12:40:33.744587+00	2026-02-12 12:40:33.792363+00	\N	2026-02-13 12:40:33.718028+00
ecdc4457-6e2c-4b92-a566-e98ae7f1d629	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/ecdc4457-6e2c-4b92-a566-e98ae7f1d629/ecdc4457-6e2c-4b92-a566-e98ae7f1d629.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 12:52:58.194799+00	2026-02-12 12:52:58.249521+00	2026-02-12 12:52:58.248229+00	2026-02-13 12:52:58.182673+00
95898252-4108-4378-822e-6e728afb7c97	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/95898252-4108-4378-822e-6e728afb7c97/95898252-4108-4378-822e-6e728afb7c97.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:24:55.236915+00	2026-02-12 13:24:55.316399+00	2026-02-12 13:24:55.314056+00	2026-02-13 13:24:55.224298+00
5dcca79b-6dae-49b7-b0e5-c8b5116e646a	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/5dcca79b-6dae-49b7-b0e5-c8b5116e646a/5dcca79b-6dae-49b7-b0e5-c8b5116e646a.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 16:03:27.327296+00	2026-02-12 16:03:27.36342+00	2026-02-12 16:03:27.362971+00	2026-02-13 16:03:27.323393+00
993e9672-ed8b-42cf-9c9d-2a5094ee4c08	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/993e9672-ed8b-42cf-9c9d-2a5094ee4c08/993e9672-ed8b-42cf-9c9d-2a5094ee4c08.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 16:03:46.768389+00	2026-02-12 16:03:46.799336+00	2026-02-12 16:03:46.798796+00	2026-02-13 16:03:46.76699+00
1d6ecce0-0266-437b-befc-eba1a165110a	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file2	/exports/1d6ecce0-0266-437b-befc-eba1a165110a/1d6ecce0-0266-437b-befc-eba1a165110a.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:02:51.237381+00	2026-02-12 13:02:51.292972+00	2026-02-12 13:02:51.290613+00	2026-02-13 13:02:51.225156+00
69a05ae1-8117-48bd-8423-f639ee0fee4d	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/69a05ae1-8117-48bd-8423-f639ee0fee4d/69a05ae1-8117-48bd-8423-f639ee0fee4d.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 16:10:36.099738+00	2026-02-12 16:10:36.129931+00	2026-02-12 16:10:36.129529+00	2026-02-13 16:10:36.097549+00
6227d392-1646-4b43-8e78-d15da7e680b6	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/6227d392-1646-4b43-8e78-d15da7e680b6/6227d392-1646-4b43-8e78-d15da7e680b6.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:03:24.776053+00	2026-02-12 13:03:24.80781+00	2026-02-12 13:03:24.807386+00	2026-02-13 13:03:24.774389+00
f226b461-6703-45ad-92d9-0aea9b55c5c4	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/f226b461-6703-45ad-92d9-0aea9b55c5c4/f226b461-6703-45ad-92d9-0aea9b55c5c4.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 16:05:33.42692+00	2026-02-12 16:05:33.463143+00	2026-02-12 16:05:33.462683+00	2026-02-13 16:05:33.425046+00
59f3cabb-b1a9-4487-a972-376a7b21078e	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/59f3cabb-b1a9-4487-a972-376a7b21078e/59f3cabb-b1a9-4487-a972-376a7b21078e.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 16:06:40.555724+00	2026-02-12 16:06:40.588954+00	2026-02-12 16:06:40.588443+00	2026-02-13 16:06:40.553051+00
3254cee0-2d7c-41f3-8ba0-45b5e8c7691a	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/3254cee0-2d7c-41f3-8ba0-45b5e8c7691a/3254cee0-2d7c-41f3-8ba0-45b5e8c7691a.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:04:11.751642+00	2026-02-12 13:04:11.786231+00	2026-02-12 13:04:11.7858+00	2026-02-13 13:04:11.750255+00
eb4ea752-1880-433c-9bd9-a5a82e9d1bd4	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/eb4ea752-1880-433c-9bd9-a5a82e9d1bd4/eb4ea752-1880-433c-9bd9-a5a82e9d1bd4.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 16:14:35.235645+00	2026-02-12 16:14:35.265227+00	2026-02-12 16:14:35.264647+00	2026-02-13 16:14:35.234044+00
baae900e-1d4b-4dd6-80fa-137fdcc3edb9	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/baae900e-1d4b-4dd6-80fa-137fdcc3edb9/baae900e-1d4b-4dd6-80fa-137fdcc3edb9.xlsx	xlsx	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:13:13.894014+00	2026-02-12 13:13:13.95656+00	2026-02-12 13:13:13.955811+00	2026-02-13 13:13:13.892599+00
9f8f8046-78b9-4600-a674-bcd4a230db6f	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/9f8f8046-78b9-4600-a674-bcd4a230db6f/9f8f8046-78b9-4600-a674-bcd4a230db6f.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:04:57.635905+00	2026-02-12 13:04:57.67023+00	2026-02-12 13:04:57.669808+00	2026-02-13 13:04:57.633981+00
a7e32a4f-5679-4eae-88d3-bd7a215486e9	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/a7e32a4f-5679-4eae-88d3-bd7a215486e9/a7e32a4f-5679-4eae-88d3-bd7a215486e9.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 16:10:40.417369+00	2026-02-12 16:10:40.447765+00	2026-02-12 16:10:40.447314+00	2026-02-13 16:10:40.414665+00
d2b58719-2a87-4976-8e74-945b5f93d179	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/d2b58719-2a87-4976-8e74-945b5f93d179/d2b58719-2a87-4976-8e74-945b5f93d179.xlsx	xlsx	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:06:01.020856+00	2026-02-12 13:06:01.341513+00	2026-02-12 13:06:01.341014+00	2026-02-13 13:06:01.019479+00
e8880e5b-da8c-44cf-bb5b-7649f1402b0e	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/e8880e5b-da8c-44cf-bb5b-7649f1402b0e/e8880e5b-da8c-44cf-bb5b-7649f1402b0e.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 16:13:45.436337+00	2026-02-12 16:13:45.473439+00	2026-02-12 16:13:45.472877+00	2026-02-13 16:13:45.431862+00
9e3f405a-68cc-4fcd-b9b3-089d85a36988	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/9e3f405a-68cc-4fcd-b9b3-089d85a36988/9e3f405a-68cc-4fcd-b9b3-089d85a36988.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:12:42.641389+00	2026-02-12 13:12:42.690678+00	2026-02-12 13:12:42.68913+00	2026-02-13 13:12:42.631871+00
3b0830b6-8379-4d97-a6a0-f2f506605ca2	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/3b0830b6-8379-4d97-a6a0-f2f506605ca2/3b0830b6-8379-4d97-a6a0-f2f506605ca2.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 16:18:14.755205+00	2026-02-12 16:18:14.864237+00	2026-02-12 16:18:14.863676+00	2026-02-13 16:18:14.753855+00
2fd4a41f-bb1b-4e8b-aa5a-126e9f98d760	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/2fd4a41f-bb1b-4e8b-aa5a-126e9f98d760/2fd4a41f-bb1b-4e8b-aa5a-126e9f98d760.xlsx	xlsx	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:13:59.304223+00	2026-02-12 13:13:59.357846+00	2026-02-12 13:13:59.357359+00	2026-02-13 13:13:59.302916+00
78876607-2030-40d3-b2c8-aea4bd81533c	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/78876607-2030-40d3-b2c8-aea4bd81533c/78876607-2030-40d3-b2c8-aea4bd81533c.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:17:38.630688+00	2026-02-12 13:17:38.659263+00	2026-02-12 13:17:38.658831+00	2026-02-13 13:17:38.629247+00
89a455f4-87c2-4b3a-bd8c-67185c9641e2	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/89a455f4-87c2-4b3a-bd8c-67185c9641e2/89a455f4-87c2-4b3a-bd8c-67185c9641e2.json	json	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:15:09.380849+00	2026-02-12 13:15:09.426544+00	2026-02-12 13:15:09.425943+00	2026-02-13 13:15:09.379192+00
cea265de-de21-4479-8d3d-8bcfee15982f	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/cea265de-de21-4479-8d3d-8bcfee15982f/cea265de-de21-4479-8d3d-8bcfee15982f.json	json	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 13:17:31.322523+00	2026-02-12 13:17:31.358983+00	2026-02-12 13:17:31.358541+00	2026-02-13 13:17:31.32095+00
cb7d8f2c-9b16-4750-8d3f-8e5d29994735	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/cb7d8f2c-9b16-4750-8d3f-8e5d29994735/cb7d8f2c-9b16-4750-8d3f-8e5d29994735.pdf	pdf	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 17:06:44.855344+00	2026-02-12 17:06:45.335587+00	2026-02-12 17:06:45.335099+00	2026-02-13 17:06:44.845843+00
f540e982-e6b8-4bcc-a26c-f056f3e52260	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/f540e982-e6b8-4bcc-a26c-f056f3e52260/f540e982-e6b8-4bcc-a26c-f056f3e52260.csv	csv	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 17:26:55.867903+00	2026-02-12 17:26:55.997763+00	2026-02-12 17:26:55.997312+00	2026-02-13 17:26:55.855929+00
d53f235d-df8a-44c4-b9be-b1174911c6f9	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/d53f235d-df8a-44c4-b9be-b1174911c6f9/d53f235d-df8a-44c4-b9be-b1174911c6f9.pdf	pdf	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 17:27:06.067075+00	2026-02-12 17:27:06.524554+00	2026-02-12 17:27:06.524123+00	2026-02-13 17:27:06.065347+00
db6c4cd9-dc8c-4bdc-89ea-c98c20827ec0	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/db6c4cd9-dc8c-4bdc-89ea-c98c20827ec0/db6c4cd9-dc8c-4bdc-89ea-c98c20827ec0.xlsx	xlsx	COMPLETED	5	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-12 17:34:21.327281+00	2026-02-12 17:34:21.513798+00	2026-02-12 17:34:21.51331+00	2026-02-13 17:34:21.325225+00
532a5f6a-4009-4ca3-9fcb-cbf4449f4267	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/532a5f6a-4009-4ca3-9fcb-cbf4449f4267/532a5f6a-4009-4ca3-9fcb-cbf4449f4267.pdf	pdf	COMPLETED	6	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-13 06:05:02.974318+00	2026-02-13 06:05:03.361243+00	2026-02-13 06:05:03.360682+00	2026-02-14 06:05:02.967709+00
8dbf042a-2668-43f7-8a41-3b8fc4e40c49	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	items export file	/exports/8dbf042a-2668-43f7-8a41-3b8fc4e40c49/8dbf042a-2668-43f7-8a41-3b8fc4e40c49.xlsx	xlsx	COMPLETED	6	null	["id", "item_code", "item_name", "description", "item_type", "status", "uom", "standard_rate"]	\N	2026-02-13 06:05:34.218704+00	2026-02-13 06:05:34.437305+00	2026-02-13 06:05:34.436531+00	2026-02-14 06:05:34.217019+00
\.


--
-- Data for Name: bulk_import_jobs; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.bulk_import_jobs (id, organization_id, created_by_id, file_name, file_path, mime_type, status, total_rows, successful_rows, failed_rows, error_details, summary, created_at, updated_at, completed_at) FROM stdin;
f7f6f14e-1e64-41b5-b333-5cb254ea8bed	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	sample_import_data.csv	\N	text/csv	COMPLETED	25	0	25	{"errors": [{"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM001", "item_name": "Laptop Computer", "item_type": "Stock", "description": "Dell XPS 13 Laptop with Intel i7", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "1299.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...7', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('e1ebed79-399e-43ae-926d-c55ed8addb3b'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM001', 'item_name': 'Laptop Computer', 'description': 'Dell XPS 13 Laptop with Intel i7', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 1299.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 276935, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 276956, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 1}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM002", "item_name": "Office Chair", "item_type": "Stock", "description": "Ergonomic Office Chair with Lumbar Support", "item_group_id": "550e8400-e29b-41d4-a716-446655440002", "standard_rate": "299.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...t', '550e8400-e29b-41d4-a716-446655440002'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('4590d9e8-48f9-49d4-8ac2-840e5eaf1322'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM002', 'item_name': 'Office Chair', 'description': 'Ergonomic Office Chair with Lumbar Support', 'item_group_id': '550e8400-e29b-41d4-a716-446655440002', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 299.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 293395, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 293403, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 2}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM003", "item_name": "Desk Lamp", "item_type": "Stock", "description": "LED Desk Lamp with USB Charging", "item_group_id": "550e8400-e29b-41d4-a716-446655440002", "standard_rate": "49.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...g', '550e8400-e29b-41d4-a716-446655440002'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('2ac0053f-dda0-45e0-9a4e-2513cfbea55b'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM003', 'item_name': 'Desk Lamp', 'description': 'LED Desk Lamp with USB Charging', 'item_group_id': '550e8400-e29b-41d4-a716-446655440002', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 49.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 309617, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 309625, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 3}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM004", "item_name": "Wireless Mouse", "item_type": "Stock", "description": "Logitech Wireless Mouse with Nano Receiver", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "29.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...r', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('f66aecbb-9ef8-4708-b5e8-a8c83bb954a1'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM004', 'item_name': 'Wireless Mouse', 'description': 'Logitech Wireless Mouse with Nano Receiver', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 29.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 325556, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 325565, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 4}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM005", "item_name": "USB-C Cable", "item_type": "Stock", "description": "3 Pack USB-C Cables 6ft Each", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "19.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...h', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('2f3b8f53-314c-455e-834a-90abe619fd9b'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM005', 'item_name': 'USB-C Cable', 'description': '3 Pack USB-C Cables 6ft Each', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 19.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 339792, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 339801, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 5}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM006", "item_name": "Keyboard", "item_type": "Stock", "description": "Mechanical RGB Keyboard with Cherry MX Switches", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "89.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...s', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('94849c13-6a59-463d-86b9-9e8993cb27c4'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM006', 'item_name': 'Keyboard', 'description': 'Mechanical RGB Keyboard with Cherry MX Switches', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 89.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 358551, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 358566, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 6}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM007", "item_name": "Monitor Stand", "item_type": "Stock", "description": "Adjustable Monitor Stand with VESA Mount", "item_group_id": "550e8400-e29b-41d4-a716-446655440002", "standard_rate": "69.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...t', '550e8400-e29b-41d4-a716-446655440002'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('0a3cd37d-0dc6-4e7b-954f-9cc53fae010f'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM007', 'item_name': 'Monitor Stand', 'description': 'Adjustable Monitor Stand with VESA Mount', 'item_group_id': '550e8400-e29b-41d4-a716-446655440002', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 69.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 375963, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 375981, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 7}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM008", "item_name": "Webcam", "item_type": "Stock", "description": "1080p HD Webcam with Auto Focus", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "59.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...s', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('e5072b79-ca2a-4bf4-84ad-9aed73234d56'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM008', 'item_name': 'Webcam', 'description': '1080p HD Webcam with Auto Focus', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 59.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 389450, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 389475, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 8}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM009", "item_name": "Headphones", "item_type": "Stock", "description": "Wireless Bluetooth Headphones with Noise Cancellation", "item_group_id": "550e8400-e29b-41d4-a716-446655440002", "standard_rate": "129.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...n', '550e8400-e29b-41d4-a716-446655440002'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('4f0cb120-8410-48d4-83df-52607ddb1537'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM009', 'item_name': 'Headphones', 'description': 'Wireless Bluetooth Headphones with Noise Cancellation', 'item_group_id': '550e8400-e29b-41d4-a716-446655440002', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 129.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 411995, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 412015, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 9}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM010", "item_name": "Screen Protector", "item_type": "Stock", "description": "MacBook Pro Screen Protector 13 Inch", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "9.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...h', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('e357c904-7186-48bc-aac5-8e3d855eac6e'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM010', 'item_name': 'Screen Protector', 'description': 'MacBook Pro Screen Protector 13 Inch', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 9.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 431478, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 431505, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 10}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM011", "item_name": "Docking Station", "item_type": "Stock", "description": "USB-C Docking Station with 7 Ports", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "179.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...s', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('301fd039-abb7-427d-bfcd-9dfdba778ac5'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM011', 'item_name': 'Docking Station', 'description': 'USB-C Docking Station with 7 Ports', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 179.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 455488, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 455512, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 11}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM012", "item_name": "Power Bank", "item_type": "Stock", "description": "20000mAh Power Bank with Fast Charging", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "49.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...g', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('857351f3-ce8c-4b2e-abd3-af1734af43c8'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM012', 'item_name': 'Power Bank', 'description': '20000mAh Power Bank with Fast Charging', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 49.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 477012, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 477029, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 12}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM013", "item_name": "Mouse Pad", "item_type": "Stock", "description": "Large RGB Mouse Pad with Wireless Charging", "item_group_id": "550e8400-e29b-41d4-a716-446655440002", "standard_rate": "39.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...g', '550e8400-e29b-41d4-a716-446655440002'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('73e77630-edc6-4a3c-b534-483ec54a6934'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM013', 'item_name': 'Mouse Pad', 'description': 'Large RGB Mouse Pad with Wireless Charging', 'item_group_id': '550e8400-e29b-41d4-a716-446655440002', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 39.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 500130, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 500147, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 13}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM014", "item_name": "HDMI Cable", "item_type": "Stock", "description": "High Speed HDMI 2.1 Cable 6ft", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "19.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...t', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('b6e73285-bfb6-4cf0-8f33-985ba993d972'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM014', 'item_name': 'HDMI Cable', 'description': 'High Speed HDMI 2.1 Cable 6ft', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 19.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 522301, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 522311, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 14}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM015", "item_name": "Phone Stand", "item_type": "Stock", "description": "Adjustable Phone Stand for Desk", "item_group_id": "550e8400-e29b-41d4-a716-446655440002", "standard_rate": "14.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...k', '550e8400-e29b-41d4-a716-446655440002'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('22b5aac1-bd36-4c29-add7-b042d2a25437'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM015', 'item_name': 'Phone Stand', 'description': 'Adjustable Phone Stand for Desk', 'item_group_id': '550e8400-e29b-41d4-a716-446655440002', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 14.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 543102, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 543114, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 15}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM016", "item_name": "USB Hub", "item_type": "Stock", "description": "7 Port USB 3.0 Hub with Power Supply", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "39.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...y', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('4c20e965-cf34-4c79-82f1-8ed9417e0400'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM016', 'item_name': 'USB Hub', 'description': '7 Port USB 3.0 Hub with Power Supply', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 39.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 573893, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 573909, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 16}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM017", "item_name": "Desk Organizer", "item_type": "Stock", "description": "Bamboo Desk Organizer Set", "item_group_id": "550e8400-e29b-41d4-a716-446655440002", "standard_rate": "34.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...t', '550e8400-e29b-41d4-a716-446655440002'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('c4d6abff-b423-4f5e-a3dc-3a12afd90065'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM017', 'item_name': 'Desk Organizer', 'description': 'Bamboo Desk Organizer Set', 'item_group_id': '550e8400-e29b-41d4-a716-446655440002', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 34.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 611854, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 611868, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 17}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM018", "item_name": "Laptop Cooler", "item_type": "Stock", "description": "Laptop Cooling Pad with 5 Fans", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "44.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...s', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('785d206a-c6bd-446b-a36e-801cc90fa7ce'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM018', 'item_name': 'Laptop Cooler', 'description': 'Laptop Cooling Pad with 5 Fans', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 44.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 651493, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 651522, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 18}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM019", "item_name": "Portable Monitor", "item_type": "Stock", "description": "15.6 inch Portable Monitor USB-C", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "249.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...C', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('e199a2ac-4da8-41a8-82cb-c9acf1114aec'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM019', 'item_name': 'Portable Monitor', 'description': '15.6 inch Portable Monitor USB-C', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 249.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 683916, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 684011, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 19}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM020", "item_name": "Document Camera", "item_type": "Stock", "description": "HD Document Camera for Teaching", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "299.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...g', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('5e1418ef-66ac-4647-bd49-dd5264a46bb3'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM020', 'item_name': 'Document Camera', 'description': 'HD Document Camera for Teaching', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 299.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 728578, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 728600, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 20}, {"data": {"uom": "Nos", "status": "Inactive", "item_code": "ITEM021", "item_name": "Thermal Printer", "item_type": "Stock", "description": "Thermal Printer for Labels", "item_group_id": "550e8400-e29b-41d4-a716-446655440001", "standard_rate": "399.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...s', '550e8400-e29b-41d4-a716-446655440001'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('b71ebfc9-2d95-4853-ad2e-cb03a08a2155'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM021', 'item_name': 'Thermal Printer', 'description': 'Thermal Printer for Labels', 'item_group_id': '550e8400-e29b-41d4-a716-446655440001', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 399.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Inactive', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 775101, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 775121, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 21}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM022", "item_name": "Label Roll", "item_type": "Stock", "description": "4x6 White Label Roll 500 Count", "item_group_id": "550e8400-e29b-41d4-a716-446655440002", "standard_rate": "24.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...t', '550e8400-e29b-41d4-a716-446655440002'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('c140db37-e80f-4f7e-a173-35a344b50bd2'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM022', 'item_name': 'Label Roll', 'description': '4x6 White Label Roll 500 Count', 'item_group_id': '550e8400-e29b-41d4-a716-446655440002', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 24.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 805135, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 805149, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 22}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM023", "item_name": "Ink Cartridge", "item_type": "Stock", "description": "Black Ink Cartridge HP Compatible", "item_group_id": "550e8400-e29b-41d4-a716-446655440002", "standard_rate": "19.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...e', '550e8400-e29b-41d4-a716-446655440002'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('f644f321-dc8e-4818-aaf3-c9a913a673ef'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM023', 'item_name': 'Ink Cartridge', 'description': 'Black Ink Cartridge HP Compatible', 'item_group_id': '550e8400-e29b-41d4-a716-446655440002', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 19.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 847396, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 847430, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 23}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM024", "item_name": "Toner Cartridge", "item_type": "Stock", "description": "Toner Cartridge for LaserJet Printer", "item_group_id": "550e8400-e29b-41d4-a716-446655440002", "standard_rate": "89.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...r', '550e8400-e29b-41d4-a716-446655440002'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('6d653d08-d760-4e7d-8861-4293e58dc45b'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM024', 'item_name': 'Toner Cartridge', 'description': 'Toner Cartridge for LaserJet Printer', 'item_group_id': '550e8400-e29b-41d4-a716-446655440002', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 89.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 894869, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 894887, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 24}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM025", "item_name": "Paper Ream", "item_type": "Stock", "description": "White Paper Ream 8.5x11 500 sheets", "item_group_id": "550e8400-e29b-41d4-a716-446655440002", "standard_rate": "5.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...s', '550e8400-e29b-41d4-a716-446655440002'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('2ca542fa-839f-463e-b01d-60e973f5db41'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM025', 'item_name': 'Paper Ream', 'description': 'White Paper Ream 8.5x11 500 sheets', 'item_group_id': '550e8400-e29b-41d4-a716-446655440002', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 5.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 932670, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 8, 49, 9, 932698, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 25}]}	Import completed: 0/25 rows successful	2026-02-05 08:49:09.176758+00	2026-02-05 08:49:10.038161+00	2026-02-05 08:49:10.032585+00
058f0c7e-8063-4d55-94d0-67ed03421bc5	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	sample_import_data.csv	\N	text/csv	COMPLETED	25	0	25	{"errors": [{"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM001", "item_name": "Laptop Computer", "item_type": "Kilogram", "description": "Dell XPS 13 Laptop with Intel i7", "item_group_id": "76fb273a-70cd-45a1-bbc7-fbb370f09b2b", "standard_rate": "1299.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Kilogram\\"\\nLINE 1: ...7', '76fb273a-70cd-45a1-bbc7-fbb370f09b2b'::UUID, 'Kilogram'...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('80a2f9c9-22d4-4288-ad77-33255b79ba78'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM001', 'item_name': 'Laptop Computer', 'description': 'Dell XPS 13 Laptop with Intel i7', 'item_group_id': '76fb273a-70cd-45a1-bbc7-fbb370f09b2b', 'item_type': 'Kilogram', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 1299.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 9, 33, 22, 460816, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 9, 33, 22, 460842, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 1}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM002", "item_name": "Office Chair", "item_type": "Stock", "description": "Ergonomic Office Chair with Lumbar Support", "item_group_id": "e07dc93d-1f02-4f1a-bf9d-255c1490f157", "standard_rate": "299.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...t', 'e07dc93d-1f02-4f1a-bf9d-255c1490f157'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('85168526-5651-425f-aabb-25688d359d29'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM002', 'item_name': 'Office Chair', 'description': 'Ergonomic Office Chair with Lumbar Support', 'item_group_id': 'e07dc93d-1f02-4f1a-bf9d-255c1490f157', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 299.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 9, 33, 22, 475806, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 9, 33, 22, 475822, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 2}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 3: Missing required field 'item_name'", "Row 3: Missing required field 'item_code'"], "row_number": 3}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 4: Missing required field 'item_name'", "Row 4: Missing required field 'item_code'"], "row_number": 4}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 5: Missing required field 'item_name'", "Row 5: Missing required field 'item_code'"], "row_number": 5}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 6: Missing required field 'item_name'", "Row 6: Missing required field 'item_code'"], "row_number": 6}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 7: Missing required field 'item_name'", "Row 7: Missing required field 'item_code'"], "row_number": 7}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 8: Missing required field 'item_name'", "Row 8: Missing required field 'item_code'"], "row_number": 8}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 9: Missing required field 'item_name'", "Row 9: Missing required field 'item_code'"], "row_number": 9}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 10: Missing required field 'item_name'", "Row 10: Missing required field 'item_code'"], "row_number": 10}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 11: Missing required field 'item_name'", "Row 11: Missing required field 'item_code'"], "row_number": 11}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 12: Missing required field 'item_name'", "Row 12: Missing required field 'item_code'"], "row_number": 12}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 13: Missing required field 'item_name'", "Row 13: Missing required field 'item_code'"], "row_number": 13}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 14: Missing required field 'item_name'", "Row 14: Missing required field 'item_code'"], "row_number": 14}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 15: Missing required field 'item_name'", "Row 15: Missing required field 'item_code'"], "row_number": 15}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 16: Missing required field 'item_name'", "Row 16: Missing required field 'item_code'"], "row_number": 16}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 17: Missing required field 'item_name'", "Row 17: Missing required field 'item_code'"], "row_number": 17}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 18: Missing required field 'item_name'", "Row 18: Missing required field 'item_code'"], "row_number": 18}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 19: Missing required field 'item_name'", "Row 19: Missing required field 'item_code'"], "row_number": 19}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 20: Missing required field 'item_name'", "Row 20: Missing required field 'item_code'"], "row_number": 20}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 21: Missing required field 'item_name'", "Row 21: Missing required field 'item_code'"], "row_number": 21}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 22: Missing required field 'item_name'", "Row 22: Missing required field 'item_code'"], "row_number": 22}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 23: Missing required field 'item_name'", "Row 23: Missing required field 'item_code'"], "row_number": 23}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 24: Missing required field 'item_name'", "Row 24: Missing required field 'item_code'"], "row_number": 24}, {"data": {"uom": null, "status": null, "item_code": null, "item_name": null, "item_type": null, "description": null, "item_group_id": null, "standard_rate": null}, "errors": ["Row 25: Missing required field 'item_name'", "Row 25: Missing required field 'item_code'"], "row_number": 25}]}	Import completed: 0/25 rows successful	2026-02-05 09:33:17.723225+00	2026-02-05 09:33:22.511673+00	2026-02-05 09:33:22.510697+00
56454c70-4efd-44bd-990a-71ef200f8432	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	sample_import_data.csv	\N	text/csv	COMPLETED	2	0	2	{"errors": [{"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM003", "item_name": "Laptop Computer", "item_type": "Kilogram", "description": "Dell XPS 13 Laptop with Intel i7", "item_group_id": "76fb273a-70cd-45a1-bbc7-fbb370f09b2b", "standard_rate": "1299.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Kilogram\\"\\nLINE 1: ...7', '76fb273a-70cd-45a1-bbc7-fbb370f09b2b'::UUID, 'Kilogram'...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('a30b10d0-a6a6-49f4-8c0c-b7563f73801a'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM003', 'item_name': 'Laptop Computer', 'description': 'Dell XPS 13 Laptop with Intel i7', 'item_group_id': '76fb273a-70cd-45a1-bbc7-fbb370f09b2b', 'item_type': 'Kilogram', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 1299.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 9, 41, 1, 647487, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 9, 41, 1, 647523, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 1}, {"data": {"uom": "Nos", "status": "Active", "item_code": "ITEM004", "item_name": "Office Chair", "item_type": "Stock", "description": "Ergonomic Office Chair with Lumbar Support", "item_group_id": "e07dc93d-1f02-4f1a-bf9d-255c1490f157", "standard_rate": "299.99"}, "errors": ["Database error: (psycopg2.errors.InvalidTextRepresentation) invalid input value for enum itemtype: \\"Stock\\"\\nLINE 1: ...t', 'e07dc93d-1f02-4f1a-bf9d-255c1490f157'::UUID, 'Stock', '...\\n                                                             ^\\n\\n[SQL: INSERT INTO items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) VALUES (%(id)s::UUID, %(organization_id)s::UUID, %(item_code)s, %(item_name)s, %(description)s, %(item_group_id)s::UUID, %(item_type)s, %(uom)s, %(maintain_stock)s, %(valuation_method)s, %(allow_negative_stock)s, %(has_variants)s, %(variant_of)s::UUID, %(variant_attributes)s, %(has_batch_no)s, %(has_serial_no)s, %(batch_number_series)s, %(serial_number_series)s, %(standard_rate)s, %(valuation_rate)s, %(enable_auto_reorder)s, %(reorder_level)s, %(reorder_qty)s, %(min_order_qty)s, %(max_order_qty)s, %(weight_per_unit)s, %(weight_uom)s, %(inspection_required_before_purchase)s, %(inspection_required_before_delivery)s, %(quality_inspection_template)s::UUID, %(barcode)s, %(status)s, %(image_url)s, %(images)s, %(tags)s, %(custom_fields)s, %(extra_data)s, %(created_by)s::UUID, %(updated_by)s::UUID, %(created_at)s, %(updated_at)s, %(deleted_at)s)]\\n[parameters: {'id': UUID('a183644a-ef7c-4fb3-813e-cfd4a81d57df'), 'organization_id': UUID('bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'), 'item_code': 'ITEM004', 'item_name': 'Office Chair', 'description': 'Ergonomic Office Chair with Lumbar Support', 'item_group_id': 'e07dc93d-1f02-4f1a-bf9d-255c1490f157', 'item_type': 'Stock', 'uom': 'Nos', 'maintain_stock': True, 'valuation_method': 'fifo', 'allow_negative_stock': False, 'has_variants': False, 'variant_of': None, 'variant_attributes': 'null', 'has_batch_no': False, 'has_serial_no': False, 'batch_number_series': None, 'serial_number_series': None, 'standard_rate': 299.99, 'valuation_rate': 0, 'enable_auto_reorder': False, 'reorder_level': 0, 'reorder_qty': 0, 'min_order_qty': 1, 'max_order_qty': None, 'weight_per_unit': None, 'weight_uom': None, 'inspection_required_before_purchase': False, 'inspection_required_before_delivery': False, 'quality_inspection_template': None, 'barcode': None, 'status': 'Active', 'image_url': None, 'images': 'null', 'tags': 'null', 'custom_fields': 'null', 'extra_data': 'null', 'created_by': None, 'updated_by': None, 'created_at': datetime.datetime(2026, 2, 5, 9, 43, 41, 140253, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 2, 5, 9, 43, 41, 140269, tzinfo=datetime.timezone.utc), 'deleted_at': None}]\\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"], "row_number": 2}]}	Import completed: 0/2 rows successful	2026-02-05 09:38:35.872175+00	2026-02-05 09:45:35.178666+00	2026-02-05 09:45:35.177202+00
ef32e6e0-188f-4131-9dd0-2574703e4e7a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	sample_import_data.csv	\N	text/csv	COMPLETED	2	2	0	null	Import completed: 2/2 rows successful	2026-02-05 09:45:52.950318+00	2026-02-05 09:46:07.594091+00	2026-02-05 09:46:07.593581+00
aef2d7a1-5c3b-4106-9725-5e2cf5df4152	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	sample_import_data.csv	\N	text/csv	COMPLETED	2	0	2	{"errors": [{"data": {"uom": "Nos", "status": "active", "item_code": "ITEM003", "item_name": "Laptop Computer", "item_type": "stock", "description": "Dell XPS 13 Laptop with Intel i7", "item_group_id": "76fb273a-70cd-45a1-bbc7-fbb370f09b2b", "standard_rate": "1299.99"}, "errors": ["Item code 'ITEM003' already exists"], "row_number": 1}, {"data": {"uom": "Nos", "status": "active", "item_code": "ITEM004", "item_name": "Office Chair", "item_type": "stock", "description": "Ergonomic Office Chair with Lumbar Support", "item_group_id": "e07dc93d-1f02-4f1a-bf9d-255c1490f157", "standard_rate": "299.99"}, "errors": ["Item code 'ITEM004' already exists"], "row_number": 2}]}	Import completed: 0/2 rows successful	2026-02-05 10:10:05.634126+00	2026-02-05 10:10:05.736748+00	2026-02-05 10:10:05.73499+00
c08c539e-cdb7-43a0-8082-a07f988204ff	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	sample_import_data.csv	\N	text/csv	COMPLETED	2	2	0	null	Import completed: 2/2 rows successful	2026-02-05 10:12:55.578367+00	2026-02-05 10:12:55.725879+00	2026-02-05 10:12:55.725003+00
3fc40d39-f29a-4d0d-be3e-df09a266743e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	8d509f22-5fe5-4765-9496-3a236cae2af1	sample_import_data.csv	\N	text/csv	COMPLETED	2	2	0	null	Import completed: 2/2 rows successful	2026-02-05 10:21:54.387926+00	2026-02-05 10:21:54.586114+00	2026-02-05 10:21:54.58371+00
a42c008c-cfb7-479c-845d-c4bd7cebac68	b1f71de1-0a19-424e-9580-1d3f871c5b1f	48966607-dbc7-44a5-be10-ca56c6552e08	sample_import_data.csv	\N	text/csv	COMPLETED	2	2	0	null	Import completed: 2/2 rows successful	2026-02-07 10:47:05.227378+00	2026-02-07 10:47:05.391202+00	2026-02-07 10:47:05.390161+00
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
60b23cd6-744b-495f-98e7-4730a6c1c1f9	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Acme Corporation	CUST-001	contact@acme.com	+91-9876543001	\N	\N	\N	Mumbai	\N	\N	\N	\N	active	0.00	0.00	\N	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
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
91d4db4c-0e87-4f25-94d3-4bf5882f8901	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Food	FOOD	\N	\N	\N	\N	t	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-05 10:21:54.482526+00	2026-02-05 10:21:54.482541+00	\N
2e610200-936f-413a-9e0f-8791b40a9787	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Chemical	CHEMICAL	\N	\N	\N	\N	t	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-05 10:21:54.547137+00	2026-02-05 10:21:54.547148+00	\N
f24084e2-01fb-4885-ba92-77ca26cd77b7	b1f71de1-0a19-424e-9580-1d3f871c5b1f	Electronics	FG-ELEC	Electronics	\N	fifo	Piece	t	{}	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-05 12:58:11.21773+00	2026-02-05 12:58:11.21774+00	\N
9e1faf88-5d8c-4f15-8d02-32d8d6330424	b1f71de1-0a19-424e-9580-1d3f871c5b1f	Finished Goods	FG	Finished Goods	\N	fifo	Box	t	{}	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-05 13:03:00.002808+00	2026-02-05 13:03:00.002817+00	\N
1fba8c0a-69ac-478d-b588-27fa2946f72f	b1f71de1-0a19-424e-9580-1d3f871c5b1f	Food	FOOD	\N	\N	\N	\N	t	null	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-07 10:47:05.323106+00	2026-02-07 10:47:05.323125+00	\N
369c0dd6-75eb-43b5-b5ae-459504ae32d2	b1f71de1-0a19-424e-9580-1d3f871c5b1f	Chemical	CHEMICAL	\N	\N	\N	\N	t	null	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-07 10:47:05.365904+00	2026-02-07 10:47:05.36591+00	\N
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
63e1764c-6260-4508-9faa-0665ee4f7235	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	FG-SENS-100	Smart Hub		76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Kilogram	t	f	f	\N	{}	f	f			7272.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-27 10:38:57.387063+00	2026-02-02 12:30:34.862011+00	\N	stock	fifo	active
bd1e4222-f62c-4842-a694-4383bc85c114	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALM-019	Aluminum Alloy		feacdbde-f4db-4725-b2bc-0efe83d84692	Box	t	f	f	\N	{}	f	f			9090.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-02 12:31:52.052933+00	2026-02-02 12:43:36.564597+00	\N	stock	fifo	active
eb547f3c-366c-46da-b001-4b1d717f9819	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ECL-001	TV Set	teste	feacdbde-f4db-4725-b2bc-0efe83d84692	Box	t	f	f	\N	{}	f	f			98089.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-02 12:44:11.103345+00	2026-02-02 12:44:11.103353+00	\N	stock	fifo	active
0aeeead7-ce60-4310-bce9-ae3c65b36bc3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALIM-002	Alloy Mixture updated		76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	{}	f	f			7860.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-27 10:38:57.387063+00	2026-02-02 12:44:55.977474+00	\N	stock	fifo	active
42f7d72f-3a80-4e28-9e32-16dbdcf87d6f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALIM-007	Wrong Again Alloy Mixture	string	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	01209123912	string	["string"]	["raw"]	{}	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-27 10:49:15.173748+00	2026-01-27 17:23:09.392676+00	2026-01-27 17:23:09.383365+00	stock	fifo	active
3531e02a-28dc-4659-9a76-70fa0c12c933	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	GD-ALIM-008	New Gold Alloy Mixture	string	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	01209123910	string	["string"]	["raw"]	{}	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-27 17:24:38.238107+00	2026-01-27 17:25:25.844159+00	2026-01-27 17:25:25.840176+00	stock	fifo	active
d92b4647-a8d5-42d4-83b1-e33bf19dd414	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALM-011	Aluminium 		feacdbde-f4db-4725-b2bc-0efe83d84692	Kilogram	t	f	f	\N	{}	f	f			1990.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-02 09:06:51.837803+00	2026-02-02 12:29:38.076022+00	\N	stock	fifo	active
07423f9a-c153-426b-84d3-9d37431fa4fa	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALIM-005	Wrong Alloy Mixture		76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	{}	f	f			1090.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-27 10:46:46.656609+00	2026-02-02 12:29:54.775182+00	\N	stock	fifo	active
ba33b62c-d77a-4e04-b4a9-0c047009d020	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALUM-001	Aluminum Alloy		76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Kg	t	f	f	\N	{}	f	f			7180.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-27 10:38:57.387063+00	2026-02-02 12:30:12.244853+00	\N	stock	fifo	active
29950a07-b479-48a3-9b6d-1f115b249f44	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM003	Laptop Computer	Dell XPS 13 Laptop with Intel i7	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	null	f	f	\N	\N	1299.99	0.00	f	0	0	1	\N	\N	\N	f	f	\N	\N	\N	null	null	null	null	\N	\N	2026-02-05 09:45:58.215779+00	2026-02-05 09:45:58.2158+00	\N	stock	fifo	active
759fcef1-c9ea-4606-b31c-db2555f9caa2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM004	Office Chair	Ergonomic Office Chair with Lumbar Support	e07dc93d-1f02-4f1a-bf9d-255c1490f157	Nos	t	f	f	\N	null	f	f	\N	\N	299.99	0.00	f	0	0	1	\N	\N	\N	f	f	\N	\N	\N	null	null	null	null	\N	\N	2026-02-05 09:46:05.03026+00	2026-02-05 09:46:05.030271+00	\N	stock	fifo	active
7de8aa9c-e296-4a61-a18b-ebcb722fd216	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM005	Chicken	Leg pieces	91d4db4c-0e87-4f25-94d3-4bf5882f8901	Nos	t	f	f	\N	null	f	f	\N	\N	1299.99	0.00	f	0	0	1	\N	\N	\N	f	f	\N	\N	\N	null	null	null	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-05 10:21:54.531715+00	2026-02-05 10:21:54.531732+00	\N	stock	fifo	active
0974d4e2-10bb-4fc8-8e45-bc99fd118a60	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM006	Toilet cleaner	cleanner	2e610200-936f-413a-9e0f-8791b40a9787	Nos	t	f	f	\N	null	f	f	\N	\N	299.99	0.00	f	0	0	1	\N	\N	\N	f	f	\N	\N	\N	null	null	null	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-05 10:21:54.561+00	2026-02-05 10:21:54.561008+00	\N	stock	fifo	active
785f19fc-0750-4f32-a1e5-7006f7ea97a8	b1f71de1-0a19-424e-9580-1d3f871c5b1f	ECL-001	TV set	tv sets	f24084e2-01fb-4885-ba92-77ca26cd77b7	Piece	t	f	f	\N	{}	f	f			100.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	null	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-05 13:00:38.605437+00	2026-02-05 13:00:38.605452+00	\N	stock	fifo	active
17daa698-42cd-4d68-aaf6-52871908b3f8	b1f71de1-0a19-424e-9580-1d3f871c5b1f	ITEM007	Chicken26	Leg pieces	1fba8c0a-69ac-478d-b588-27fa2946f72f	Nos	t	f	f	\N	null	f	f	\N	\N	1200.99	0.00	f	0	0	1	\N	\N	\N	f	f	\N	\N	\N	null	null	null	null	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-07 10:47:05.351975+00	2026-02-07 10:47:05.351988+00	\N	stock	fifo	active
daa3b99b-e48e-41e4-b7e7-6752cb1455c6	b1f71de1-0a19-424e-9580-1d3f871c5b1f	ITEM008	Toilet cleaner26	cleanner	369c0dd6-75eb-43b5-b5ae-459504ae32d2	Nos	t	f	f	\N	null	f	f	\N	\N	288.99	0.00	f	0	0	1	\N	\N	\N	f	f	\N	\N	\N	null	null	null	null	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-07 10:47:05.374801+00	2026-02-07 10:47:05.374807+00	\N	stock	fifo	active
6bd2c728-dcc4-468b-ab56-27408c705e37	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM1003	Apple IPAD	apple product	f24084e2-01fb-4885-ba92-77ca26cd77b7	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	string	string	["string"]	["string"]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-09 17:28:01.223093+00	2026-02-09 17:28:01.223131+00	\N	stock	fifo	active
857ef042-aa4e-46ce-ab12-7be5477f623a	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM1004	Apple IPAD	apple product	f24084e2-01fb-4885-ba92-77ca26cd77b7	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	string	string	["string"]	["string"]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-09 18:00:12.945539+00	2026-02-09 18:00:12.945547+00	\N	stock	fifo	active
92940586-2afd-432e-91c9-9238660cd6aa	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM1005	Apple airpod	apple product	f24084e2-01fb-4885-ba92-77ca26cd77b7	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	string	string	["string"]	["string"]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-09 18:07:35.84035+00	2026-02-09 18:07:35.840359+00	\N	stock	fifo	active
54fcdc8d-f7a3-4ff7-95b6-bdaed0fb2742	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM1005234	Transistor	Transistor product	f24084e2-01fb-4885-ba92-77ca26cd77b7	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	string	string	["string"]	["string"]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-09 19:03:16.674562+00	2026-02-09 19:03:16.674572+00	\N	stock	fifo	active
be9cfbb0-10d6-4b48-aa99-a644cd9bc597	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ELC_2026	Fan	Summer season product	f24084e2-01fb-4885-ba92-77ca26cd77b7	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	string		[""]	[""]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-11 19:02:09.410464+00	2026-02-11 19:02:09.410473+00	\N	stock	fifo	active
545ca47a-597c-4b57-845c-0f97a4fc39a4	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM10056	Fan	Summer season product	f24084e2-01fb-4885-ba92-77ca26cd77b7	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	string		[""]	[""]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-11 19:07:29.514302+00	2026-02-11 19:07:29.514316+00	\N	stock	fifo	active
40b41f14-7fee-473a-a67c-db7aa17d6912	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM1123	Cooler	Cooler is a summer season product	f24084e2-01fb-4885-ba92-77ca26cd77b7	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	string		[""]	[""]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-11 19:12:11.333896+00	2026-02-11 19:12:11.333906+00	\N	stock	fifo	active
54a21364-184a-42ae-bc91-30d589d1516e	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	ITEM11234	Cooler1	Cooler is a summer season product	f24084e2-01fb-4885-ba92-77ca26cd77b7	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	string		[""]	[""]	{}	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-02-11 19:15:17.704446+00	2026-02-11 19:15:17.704455+00	\N	stock	fifo	active
952b09a9-7df0-491e-b00d-d18f4fefbcaa	b1f71de1-0a19-424e-9580-1d3f871c5b1f	GOLD	Gold chain	this is test item	9e1faf88-5d8c-4f15-8d02-32d8d6330424	Piece	t	f	f	\N	{}	f	f			1000.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	null	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-12 08:28:53.313096+00	2026-02-12 08:28:53.313107+00	\N	stock	fifo	active
83e70f33-27f3-4dac-8b52-64a4d7f531f9	b1f71de1-0a19-424e-9580-1d3f871c5b1f	SILVER	Silver chain		f24084e2-01fb-4885-ba92-77ca26cd77b7	Sheet	t	f	f	\N	{}	f	f			3000.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	null	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-12 08:43:28.65948+00	2026-02-12 08:46:45.566785+00	\N	stock	fifo	active
32233eb3-93b7-48bd-874e-5f79583555dd	b1f71de1-0a19-424e-9580-1d3f871c5b1f	Crokery	Cup set	this is cup set	9e1faf88-5d8c-4f15-8d02-32d8d6330424	Box	t	f	f	\N	{}	f	f			100.00	0.00	f	0	0	1	0	0.000		f	f	\N			[]	[]	{}	null	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-13 06:03:29.138447+00	2026-02-13 06:03:29.138459+00	\N	stock	fifo	active
\.


--
-- Data for Name: landed_cost_vouchers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.landed_cost_vouchers (id, organization_id, voucher_no, posting_date, status, remarks, submitted_at, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: material_request_lines; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.material_request_lines (id, organization_id, material_request_id, item_id, quantity, required_date, description, extra_data, created_at, updated_at) FROM stdin;
0b9481f1-997b-4939-a556-b33155c79c93	b1f71de1-0a19-424e-9580-1d3f871c5b1f	f3e2f42b-e3c7-4575-bb83-8ac967e63b9b	daa3b99b-e48e-41e4-b7e7-6752cb1455c6	5.0000	2026-02-21	test2	null	2026-02-14 11:59:53.830013+00	2026-02-14 11:59:53.830018+00
16c40f7b-7e37-41e1-88bb-80a88ce9031d	b1f71de1-0a19-424e-9580-1d3f871c5b1f	91d7544a-a49b-46c6-b038-2d90f035d6ab	83e70f33-27f3-4dac-8b52-64a4d7f531f9	3.0000	2026-02-21	asdfasdf	null	2026-02-14 12:41:10.6581+00	2026-02-14 12:41:10.658107+00
\.


--
-- Data for Name: material_requests; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.material_requests (id, organization_id, status, notes, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
91d7544a-a49b-46c6-b038-2d90f035d6ab	b1f71de1-0a19-424e-9580-1d3f871c5b1f	submitted	asdfasdf	null	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-14 12:30:48.877552+00	2026-02-14 20:40:26.378618+00	\N
f3e2f42b-e3c7-4575-bb83-8ac967e63b9b	b1f71de1-0a19-424e-9580-1d3f871c5b1f	submitted	test2	null	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-14 11:59:53.821839+00	2026-02-14 20:40:29.659657+00	\N
\.


--
-- Data for Name: purchase_order_lines; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.purchase_order_lines (id, organization_id, purchase_order_id, item_id, quantity, unit_price, line_total, received_quantity, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: purchase_orders; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.purchase_orders (id, organization_id, rfq_id, reference_type, reference_id, party_type, party_id, status, subtotal, tax_amount, tax_rate, discount_amount, grand_total, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
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
-- Data for Name: rfq_lines; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.rfq_lines (id, organization_id, rfq_id, item_id, quantity, required_date, description, extra_data, created_at, updated_at) FROM stdin;
a7734125-3e96-44c6-b643-a11ed2105862	b1f71de1-0a19-424e-9580-1d3f871c5b1f	209c529d-8ea8-4e90-afa9-945ceb1cb15b	83e70f33-27f3-4dac-8b52-64a4d7f531f9	3.0000	2026-02-21	asdfasdf	null	2026-02-14 20:41:00.020087+00	2026-02-14 20:41:00.020098+00
\.


--
-- Data for Name: rfq_suppliers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.rfq_suppliers (id, organization_id, rfq_id, supplier_id, created_at) FROM stdin;
5c3870b0-8a51-42e9-bb91-ae886a75815b	b1f71de1-0a19-424e-9580-1d3f871c5b1f	209c529d-8ea8-4e90-afa9-945ceb1cb15b	b9a20c30-2557-4624-9dc3-f739d5424470	2026-02-14 20:41:00.040278+00
\.


--
-- Data for Name: rfqs; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.rfqs (id, organization_id, material_request_id, reference_type, reference_id, status, closing_date, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
209c529d-8ea8-4e90-afa9-945ceb1cb15b	b1f71de1-0a19-424e-9580-1d3f871c5b1f	91d7544a-a49b-46c6-b038-2d90f035d6ab	MATERIAL_REQUEST	91d7544a-a49b-46c6-b038-2d90f035d6ab	sent	2026-02-20	null	48966607-dbc7-44a5-be10-ca56c6552e08	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-14 20:40:59.996386+00	2026-02-15 15:16:42.233423+00	\N
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
-- Data for Name: status_transitions; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.status_transitions (id, entity_type, entity_id, previous_status, new_status, user_id, transitioned_at) FROM stdin;
daf51249-9729-4bc2-b852-7598fdb27ea7	RFQ	209c529d-8ea8-4e90-afa9-945ceb1cb15b	draft	sent	48966607-dbc7-44a5-be10-ca56c6552e08	2026-02-15 15:16:42.281302+00
\.


--
-- Data for Name: stock_entries; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_entries (id, organization_id, stock_entry_no, stock_entry_type, from_warehouse_id, to_warehouse_id, posting_date, posting_time, status, reference_type, reference_id, remarks, total_value, expense_account_id, cost_center_id, is_backflush, bom_id, extra_data, submitted_at, cancelled_at, created_at, updated_at, created_by, updated_by) FROM stdin;
\.


--
-- Data for Name: stock_entry_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_entry_items (id, organization_id, stock_entry_id, item_id, source_warehouse_id, target_warehouse_id, qty, uom, basic_rate, basic_amount, valuation_rate, batch_no, serial_nos, quality_inspection_id, description, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: stock_levels; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_levels (id, organization_id, product_id, warehouse_id, quantity_on_hand, quantity_reserved, quantity_available, last_counted_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: stock_movements; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_movements (id, organization_id, product_id, warehouse_id, movement_type, quantity, unit_cost, reference_type, reference_id, notes, performed_by, performed_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: stock_reconciliation_items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_reconciliation_items (id, organization_id, reconciliation_id, item_id, warehouse_id, current_qty, qty, qty_difference, current_valuation_rate, valuation_rate, batch_no, serial_nos, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: stock_reconciliations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_reconciliations (id, organization_id, reconciliation_no, purpose, posting_date, posting_time, status, expense_account_id, difference_account_id, remarks, extra_data, submitted_at, created_at, updated_at, created_by, updated_by) FROM stdin;
\.


--
-- Data for Name: stock_settings; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.stock_settings (id, organization_id, item_naming_by, item_naming_series, stock_entry_naming_series, delivery_note_naming_series, purchase_receipt_naming_series, default_warehouse_id, allow_negative_stock, over_delivery_receipt_allowance, over_billing_allowance, auto_indent, auto_indent_notification, default_valuation_method, auto_create_serial_no, default_quality_inspection_template_id, stock_frozen_upto, stock_frozen_upto_days, show_barcode_field, convert_item_desc_to_transaction_desc, extra_data, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: supplier_quotes; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.supplier_quotes (id, organization_id, rfq_line_id, supplier_id, quoted_price, quoted_delivery_date, supplier_notes, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: suppliers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.suppliers (id, organization_id, supplier_name, supplier_code, email, phone, address, address_line1, address_line2, city, state, postal_code, country, tax_number, status, payment_terms, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
f68137ef-49df-4ea5-8a57-fe22a0f446d2	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Steel India Ltd	SUPP-001	sales@steelindia.com	+91-9812345001	\N	\N	\N	Jamshedpur	\N	\N	\N	\N	active	30	\N	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
b9a20c30-2557-4624-9dc3-f739d5424470	b1f71de1-0a19-424e-9580-1d3f871c5b1f	Acme Corporation1	ACME001	contact@acmecorp1.com	+1-555-0101	\N	123 Industrial Blvd	\N	New York	\N	\N	USA	\N	active	30	null	null	null	\N	\N	2026-02-14 19:32:24.525944+00	2026-02-14 19:32:24.525946+00	\N
b8e470d7-404a-4ae6-86b1-7217b9bc16fb	b1f71de1-0a19-424e-9580-1d3f871c5b1f	Global Suppliers1	GLOBAL001	info@globalsuppliers1.com	+1-555-0102	\N	456 Trade Street	\N	Los Angeles	\N	\N	USA	\N	active	45	null	null	null	\N	\N	2026-02-14 19:32:24.538927+00	2026-02-14 19:32:24.538929+00	\N
892361ee-c834-4a4f-bbc4-4dc8ce35086e	b1f71de1-0a19-424e-9580-1d3f871c5b1f	Tech Parts Ltd	TECH001	sales@techparts.com	+1-555-0103	\N	789 Tech Avenue	\N	San Francisco	\N	\N	USA	\N	active	30	null	null	null	\N	\N	2026-02-14 19:32:24.542551+00	2026-02-14 19:32:24.542552+00	\N
ab6afb54-9716-4c17-bb5a-e661d9bac51a	b1f71de1-0a19-424e-9580-1d3f871c5b1f	Industrial Materials Co	INDMAT001	orders@indmaterials.com	+1-555-0104	\N	321 Materials Way	\N	Chicago	\N	\N	USA	\N	active	60	null	null	null	\N	\N	2026-02-14 19:32:24.547047+00	2026-02-14 19:32:24.547049+00	\N
\.


--
-- Data for Name: warehouses_extended; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.warehouses_extended (id, organization_id, name, code, description, parent_warehouse_id, warehouse_type, address_line1, address_line2, city, state, postal_code, country, contact_name, contact_phone, contact_email, total_capacity, capacity_uom, stock_account_id, is_active, is_default, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
cbf290a6-91cb-4c93-b9a6-db408bb3c274	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Main Warehouse	WH-MAIN	Primary warehouse for finished goods	\N	warehouse	123 Industrial Area	\N	Mumbai	Maharashtra	400001	India	John Smith	+91-9876543210	warehouse@example.com	\N	\N	\N	t	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
3c7956f3-d57a-4a01-936b-6d6cf98de665	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Retail Store	WH-STORE	Retail store location	\N	store	456 Market Street	\N	Mumbai	Maharashtra	400002	India	Jane Doe	+91-9876543211	store@example.com	\N	\N	\N	t	f	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
c5a6fa4d-becf-4365-a241-5b122f77dc7f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Goods in Transit	WH-TRANSIT	Virtual warehouse for goods in transit	cbf290a6-91cb-4c93-b9a6-db408bb3c274	transit	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	t	f	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
8226d8f8-ec03-48e1-a68a-3eb4c2c183d8	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Test Warehouse TC010	TC010WH001	Warehouse created during test TC010	\N	warehouse	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	t	f	null	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-28 08:13:28.580944+00	2026-01-28 08:13:29.815515+00	2026-01-28 08:13:29.809711+00
\.


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
-- Name: bulk_export_jobs bulk_export_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.bulk_export_jobs
    ADD CONSTRAINT bulk_export_jobs_pkey PRIMARY KEY (id);


--
-- Name: bulk_import_jobs bulk_import_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.bulk_import_jobs
    ADD CONSTRAINT bulk_import_jobs_pkey PRIMARY KEY (id);


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
-- Name: accounts uq_accounts_account_code; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT uq_accounts_account_code UNIQUE (account_code);


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
-- Name: ix_accounts_account_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_accounts_account_code ON public.accounts USING btree (account_code);


--
-- Name: ix_accounts_account_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_accounts_account_type ON public.accounts USING btree (account_type);


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
-- Name: ix_bulk_export_jobs_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_bulk_export_jobs_organization_id ON public.bulk_export_jobs USING btree (organization_id);


--
-- Name: ix_bulk_export_jobs_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_bulk_export_jobs_status ON public.bulk_export_jobs USING btree (status);


--
-- Name: ix_bulk_import_jobs_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_bulk_import_jobs_organization_id ON public.bulk_import_jobs USING btree (organization_id);


--
-- Name: ix_bulk_import_jobs_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_bulk_import_jobs_status ON public.bulk_import_jobs USING btree (status);


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
-- Name: ix_landed_cost_vouchers_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_landed_cost_vouchers_organization_id ON public.landed_cost_vouchers USING btree (organization_id);


--
-- Name: ix_landed_cost_vouchers_voucher_no; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_landed_cost_vouchers_voucher_no ON public.landed_cost_vouchers USING btree (voucher_no);


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
-- Name: ix_material_requests_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_material_requests_status ON public.material_requests USING btree (status);


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
-- Name: ix_purchase_receipts_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_purchase_receipts_organization_id ON public.purchase_receipts USING btree (organization_id);


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
-- Name: accounts fk_accounts_parent_account_id; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT fk_accounts_parent_account_id FOREIGN KEY (parent_account_id) REFERENCES public.accounts(id) ON DELETE RESTRICT;


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
-- Name: purchase_receipt_items purchase_receipt_items_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipt_items
    ADD CONSTRAINT purchase_receipt_items_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: purchase_receipt_items purchase_receipt_items_purchase_receipt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipt_items
    ADD CONSTRAINT purchase_receipt_items_purchase_receipt_id_fkey FOREIGN KEY (purchase_receipt_id) REFERENCES public.purchase_receipts(id) ON DELETE CASCADE;


--
-- Name: purchase_receipt_items purchase_receipt_items_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipt_items
    ADD CONSTRAINT purchase_receipt_items_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


--
-- Name: purchase_receipts purchase_receipts_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipts
    ADD CONSTRAINT purchase_receipts_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE CASCADE;


--
-- Name: purchase_receipts purchase_receipts_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.purchase_receipts
    ADD CONSTRAINT purchase_receipts_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouses_extended(id) ON DELETE SET NULL;


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
-- PostgreSQL database dump complete
--

\unrestrict CnB3efe9nMk39v4jmXKOaGrN8DLQAQd90HwsgSFedPl9QkVjqc1qA7w3SBtyn7n

