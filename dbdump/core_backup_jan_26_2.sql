--
-- PostgreSQL database dump
--

\restrict wnrkQrnF5InbVwniA0XhbuPmMLB0rISfo4WiGQqeVSdrU4ttJ2eA3ksEYTBf1Us

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
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


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
-- Name: itemstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.itemstatus AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'DISCONTINUE'
);


ALTER TYPE public.itemstatus OWNER TO horizon_user;

--
-- Name: itemtype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.itemtype AS ENUM (
    'STOCK',
    'NON_STOCK',
    'SERVICE',
    'FIXED_ASSET'
);


ALTER TYPE public.itemtype OWNER TO horizon_user;

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
-- Name: valuationmethod; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.valuationmethod AS ENUM (
    'FIFO',
    'LIFO',
    'MOVING_AVERAGE',
    'STANDARD'
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
-- Name: item_groups; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.item_groups (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    code character varying(50) NOT NULL,
    description text,
    parent_id uuid,
    default_valuation_method public.valuationmethod,
    default_uom character varying(50),
    is_active boolean,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
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
    item_type public.itemtype,
    uom character varying(50),
    maintain_stock boolean,
    valuation_method public.valuationmethod,
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
    status public.itemstatus,
    image_url character varying(500),
    images jsonb,
    tags jsonb,
    custom_fields jsonb,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    deleted_at timestamp with time zone
);


ALTER TABLE public.items OWNER TO horizon_user;

--
-- Name: warehouses_extended; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.warehouses_extended (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    code character varying(50) NOT NULL,
    description text,
    parent_warehouse_id uuid,
    warehouse_type public.warehousetype,
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
    is_active boolean,
    is_default boolean,
    extra_data jsonb,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
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
-- Data for Name: item_groups; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.item_groups (id, organization_id, name, code, description, parent_id, default_valuation_method, default_uom, is_active, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
09c98761-3621-4495-9ba4-78e59aa6817c	68ad4197-97ec-4333-a0fb-6b3589dec124	Raw Materials	RM	Raw materials	\N	FIFO	Kg	t	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	2026-01-25 22:14:59.927634+00	2026-01-25 22:14:59.927634+00	\N
4e9f3a3b-2776-48f9-8662-754d5f79ef9b	68ad4197-97ec-4333-a0fb-6b3589dec124	Finished Goods	FG	Finished products	\N	MOVING_AVERAGE	Nos	t	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	2026-01-25 22:14:59.927634+00	2026-01-25 22:14:59.927634+00	\N
b65abacd-9496-474f-b27f-93205939d953	68ad4197-97ec-4333-a0fb-6b3589dec124	Consumables	CON	Consumable items	\N	FIFO	Nos	t	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	2026-01-25 22:14:59.927634+00	2026-01-25 22:14:59.927634+00	\N
2c91c21f-f007-47e1-8dbb-fd1ed83976ee	68ad4197-97ec-4333-a0fb-6b3589dec124	Services	SRV	Service items	\N	FIFO	Hrs	t	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	2026-01-25 22:14:59.927634+00	2026-01-25 22:14:59.927634+00	\N
\.


--
-- Data for Name: items; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.items (id, organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, allow_negative_stock, has_variants, variant_of, variant_attributes, has_batch_no, has_serial_no, batch_number_series, serial_number_series, standard_rate, valuation_rate, enable_auto_reorder, reorder_level, reorder_qty, min_order_qty, max_order_qty, weight_per_unit, weight_uom, inspection_required_before_purchase, inspection_required_before_delivery, quality_inspection_template, barcode, status, image_url, images, tags, custom_fields, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
7a96ca7b-2a15-4d70-9033-58e638c6513e	cd7845fa-8a99-44ac-bb2f-cf00fb8001ce	RM-STEEL-001	Steel Sheet (2mm)	Steel sheet	09c98761-3621-4495-9ba4-78e59aa6817c	STOCK	Kg	t	FIFO	\N	\N	\N	\N	\N	\N	\N	\N	85.00	75.00	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	ACTIVE	\N	\N	\N	\N	\N	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	2026-01-25 22:14:59.927634+00	2026-01-25 22:14:59.927634+00	\N
de5385d9-5f5a-4353-a055-251e0796d592	cd7845fa-8a99-44ac-bb2f-cf00fb8001ce	FG-WIDGET-001	Widget Pro	Premium widget	4e9f3a3b-2776-48f9-8662-754d5f79ef9b	STOCK	Nos	t	MOVING_AVERAGE	\N	\N	\N	\N	\N	\N	\N	\N	599.00	350.00	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	ACTIVE	\N	\N	\N	\N	\N	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	2026-01-25 22:14:59.927634+00	2026-01-25 22:14:59.927634+00	\N
f0ac73a6-cd64-4d89-ae5f-596ed7e9595a	cd7845fa-8a99-44ac-bb2f-cf00fb8001ce	CON-PACK-001	Packaging Box	Medium box	b65abacd-9496-474f-b27f-93205939d953	STOCK	Nos	t	FIFO	\N	\N	\N	\N	\N	\N	\N	\N	25.00	18.00	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	ACTIVE	\N	\N	\N	\N	\N	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	2026-01-25 22:14:59.927634+00	2026-01-25 22:14:59.927634+00	\N
71609368-a478-47f4-b04f-a2feddb04bed	cd7845fa-8a99-44ac-bb2f-cf00fb8000ce	SRV-INSTALL-001	Installation	Service	2c91c21f-f007-47e1-8dbb-fd1ed83976ee	SERVICE	Hrs	f	FIFO	\N	\N	\N	\N	\N	\N	\N	\N	500.00	0.00	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	ACTIVE	\N	\N	\N	\N	\N	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	2026-01-25 22:14:59.927634+00	2026-01-25 22:14:59.927634+00	\N
\.


--
-- Data for Name: warehouses_extended; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.warehouses_extended (id, organization_id, name, code, description, parent_warehouse_id, warehouse_type, address_line1, address_line2, city, state, postal_code, country, contact_name, contact_phone, contact_email, total_capacity, capacity_uom, stock_account_id, is_active, is_default, extra_data, created_by, updated_by, created_at, updated_at, deleted_at) FROM stdin;
053f9092-0a57-494e-9998-fafb85d467fd	68ad4197-97ec-4333-a0fb-6b3589dec124	Main Warehouse	WH-MAIN	Primary storage	\N	warehouse	123 Industrial Ave	\N	Mumbai	Maharashtra	400001	India	\N	\N	\N	\N	\N	\N	t	t	\N	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	2026-01-25 22:14:59.887383+00	2026-01-25 22:14:59.887383+00	\N
10648c4e-7d48-449a-a103-beb928c35611	68ad4197-97ec-4333-a0fb-6b3589dec124	Retail Store	WH-STORE	Retail outlet	\N	store	456 Market Street	\N	Mumbai	Maharashtra	400002	India	\N	\N	\N	\N	\N	\N	t	f	\N	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	2026-01-25 22:14:59.887383+00	2026-01-25 22:14:59.887383+00	\N
3fcebfd2-1935-481d-bda5-d7e35fc839f1	68ad4197-97ec-4333-a0fb-6b3589dec124	Transit Warehouse	WH-TRANSIT	Temporary storage	\N	transit	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	t	f	\N	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d	2026-01-25 22:14:59.887383+00	2026-01-25 22:14:59.887383+00	\N
\.


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


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
-- Name: warehouses_extended warehouses_extended_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.warehouses_extended
    ADD CONSTRAINT warehouses_extended_pkey PRIMARY KEY (id);


--
-- Name: ix_item_groups_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_groups_code ON public.item_groups USING btree (code);


--
-- Name: ix_item_groups_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_item_groups_organization_id ON public.item_groups USING btree (organization_id);


--
-- Name: ix_items_item_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_items_item_code ON public.items USING btree (item_code);


--
-- Name: ix_items_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_items_organization_id ON public.items USING btree (organization_id);


--
-- Name: ix_warehouses_extended_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_warehouses_extended_code ON public.warehouses_extended USING btree (code);


--
-- Name: ix_warehouses_extended_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_warehouses_extended_organization_id ON public.warehouses_extended USING btree (organization_id);


--
-- Name: item_groups item_groups_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.item_groups
    ADD CONSTRAINT item_groups_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.item_groups(id);


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
-- Name: warehouses_extended warehouses_extended_parent_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.warehouses_extended
    ADD CONSTRAINT warehouses_extended_parent_warehouse_id_fkey FOREIGN KEY (parent_warehouse_id) REFERENCES public.warehouses_extended(id);


--
-- PostgreSQL database dump complete
--

\unrestrict wnrkQrnF5InbVwniA0XhbuPmMLB0rISfo4WiGQqeVSdrU4ttJ2eA3ksEYTBf1Us
