--
-- PostgreSQL database dump
--

\restrict ufh0PGDdO820BsbKur4yXi3atdJzseAvL5QT0Dn0lW3rZUveTzIJD64E6KWZ7gv

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
-- Name: readingtype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.readingtype AS ENUM (
    'numeric',
    'text',
    'pass_fail'
);


ALTER TYPE public.readingtype OWNER TO horizon_user;

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
001
\.


--
-- Data for Name: chart_of_accounts; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.chart_of_accounts (id, organization_id, account_code, account_name, account_type, parent_account_id, level, is_group, opening_balance, current_balance, is_active, tags, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
aa2609fb-93f3-452d-9e18-8c06ab1d20a9	a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11	1000	Assets	asset	\N	1	t	0.00	0.00	t	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
3dd50f6f-6530-44ee-8fca-ffb66da268ef	a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11	1130	Inventory	asset	aa2609fb-93f3-452d-9e18-8c06ab1d20a9	2	f	0.00	0.00	t	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
\.


--
-- Data for Name: customers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.customers (id, organization_id, customer_name, customer_code, email, phone, address, address_line1, address_line2, city, state, postal_code, country, tax_number, status, credit_limit, outstanding_balance, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
60b23cd6-744b-495f-98e7-4730a6c1c1f9	a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11	Acme Corporation	CUST-001	contact@acme.com	+91-9876543001	\N	\N	\N	Mumbai	\N	\N	\N	\N	active	0.00	0.00	\N	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
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
\.


--
-- Data for Name: items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.items (id, organization_id, item_code, item_name, description, item_group_id, uom, maintain_stock, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at, item_type, valuation_method, status) FROM stdin;
ba33b62c-d77a-4e04-b4a9-0c047009d020	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALUM-001	Aluminum Alloy	\N	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Kg	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	\N	\N	\N	stock	fifo	active
63e1764c-6260-4508-9faa-0665ee4f7235	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	FG-SENS-100	Smart Hub	\N	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	\N	\N	\N	stock	fifo	active
0aeeead7-ce60-4310-bce9-ae3c65b36bc3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALIM-002	Alloy Mixture updated	string	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	01209123910	string	["string"]	["raw"]	{}	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-27 10:38:57.387063+00	2026-01-27 10:46:08.807782+00	\N	stock	fifo	active
07423f9a-c153-426b-84d3-9d37431fa4fa	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALIM-005	Wrong Alloy Mixture	string	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	01209123910	string	["string"]	["raw"]	{}	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-27 10:46:46.656609+00	2026-01-27 10:48:49.955462+00	2026-01-27 10:48:49.949627+00	stock	fifo	active
42f7d72f-3a80-4e28-9e32-16dbdcf87d6f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	RM-ALIM-007	Wrong Again Alloy Mixture	string	76fb273a-70cd-45a1-bbc7-fbb370f09b2b	Nos	t	f	f	\N	{}	f	f	string	string	0.00	0.00	f	0	0	1	0	0.000	string	f	f	\N	01209123910	string	["string"]	["raw"]	{}	\N	8d509f22-5fe5-4765-9496-3a236cae2af1	8d509f22-5fe5-4765-9496-3a236cae2af1	2026-01-27 10:49:15.173748+00	2026-01-27 10:50:01.304123+00	2026-01-27 10:50:01.300695+00	stock	fifo	active
\.


--
-- Data for Name: suppliers; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.suppliers (id, organization_id, supplier_name, supplier_code, email, phone, address, address_line1, address_line2, city, state, postal_code, country, tax_number, status, payment_terms, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
f68137ef-49df-4ea5-8a57-fe22a0f446d2	a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11	Steel India Ltd	SUPP-001	sales@steelindia.com	+91-9812345001	\N	\N	\N	Jamshedpur	\N	\N	\N	\N	active	30	\N	\N	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
\.


--
-- Data for Name: warehouses_extended; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.warehouses_extended (id, organization_id, name, code, description, parent_warehouse_id, warehouse_type, address_line1, address_line2, city, state, postal_code, country, contact_name, contact_phone, contact_email, total_capacity, capacity_uom, stock_account_id, is_active, is_default, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
cbf290a6-91cb-4c93-b9a6-db408bb3c274	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Main Warehouse	WH-MAIN	Primary warehouse for finished goods	\N	warehouse	123 Industrial Area	\N	Mumbai	Maharashtra	400001	India	John Smith	+91-9876543210	warehouse@example.com	\N	\N	\N	t	t	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
3c7956f3-d57a-4a01-936b-6d6cf98de665	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Retail Store	WH-STORE	Retail store location	\N	store	456 Market Street	\N	Mumbai	Maharashtra	400002	India	Jane Doe	+91-9876543211	store@example.com	\N	\N	\N	t	f	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
c5a6fa4d-becf-4365-a241-5b122f77dc7f	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Goods in Transit	WH-TRANSIT	Virtual warehouse for goods in transit	cbf290a6-91cb-4c93-b9a6-db408bb3c274	transit	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	t	f	\N	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22	2026-01-26 15:47:10.155932+00	2026-01-26 15:47:10.155932+00	\N
\.


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


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
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


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
-- Name: ix_items_item_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_items_item_code ON public.items USING btree (item_code);


--
-- Name: ix_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_items_organization_id ON public.items USING btree (organization_id);


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
-- PostgreSQL database dump complete
--

\unrestrict ufh0PGDdO820BsbKur4yXi3atdJzseAvL5QT0Dn0lW3rZUveTzIJD64E6KWZ7gv
