--
-- PostgreSQL database dump
--

\restrict ye6BEdoJGJg7wjCoUai0tR131YR58aqqjmvFTVuB7DQvnqlueIGwuXWkJYDzaMQ

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
-- Name: actiontype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.actiontype AS ENUM (
    'create',
    'read',
    'update',
    'delete',
    'manage',
    'execute',
    'invite',
    '*.*',
    '.*'
);


ALTER TYPE public.actiontype OWNER TO horizon_user;

--
-- Name: organizationstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.organizationstatus AS ENUM (
    'active',
    'inactive',
    'suspended',
    'trial'
);


ALTER TYPE public.organizationstatus OWNER TO horizon_user;

--
-- Name: organizationtype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.organizationtype AS ENUM (
    'enterprise',
    'business',
    'startup',
    'individual'
);


ALTER TYPE public.organizationtype OWNER TO horizon_user;

--
-- Name: resourcetype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.resourcetype AS ENUM (
    'user',
    'organization',
    'team',
    'role',
    'permission',
    'invitation',
    'item',
    'item_group',
    'warehouse',
    'stock_entry',
    'batch',
    'serial',
    'report',
    'setting',
    'all',
    'customer',
    'sales_order',
    'invoice',
    'supplier',
    'purchase_order',
    'chart_of_account',
    'payment'
);


ALTER TYPE public.resourcetype OWNER TO horizon_user;

--
-- Name: teamrole; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.teamrole AS ENUM (
    'owner',
    'admin',
    'member',
    'viewer'
);


ALTER TYPE public.teamrole OWNER TO horizon_user;

--
-- Name: teamtype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.teamtype AS ENUM (
    'department',
    'project',
    'functional',
    'cross_functional'
);


ALTER TYPE public.teamtype OWNER TO horizon_user;

--
-- Name: userstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.userstatus AS ENUM (
    'active',
    'inactive',
    'suspended',
    'pending'
);


ALTER TYPE public.userstatus OWNER TO horizon_user;

--
-- Name: usertype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.usertype AS ENUM (
    'system_admin',
    'organization_admin',
    'user',
    'guest'
);


ALTER TYPE public.usertype OWNER TO horizon_user;

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
-- Name: email_verifications; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.email_verifications (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    email character varying(255) NOT NULL,
    token_hash character varying(255) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    verified_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.email_verifications OWNER TO horizon_user;

--
-- Name: invitations; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.invitations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    email character varying(255) NOT NULL,
    first_name character varying(100),
    last_name character varying(100),
    role_id uuid,
    team_ids jsonb DEFAULT '[]'::jsonb,
    invited_by_id uuid,
    token_hash character varying(255) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    accepted_at timestamp with time zone,
    accepted_user_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    message text,
    extra_data jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.invitations OWNER TO horizon_user;

--
-- Name: TABLE invitations; Type: COMMENT; Schema: public; Owner: horizon_user
--

COMMENT ON TABLE public.invitations IS 'User invitations to organizations; used by Invitations API.';


--
-- Name: COLUMN invitations.team_ids; Type: COMMENT; Schema: public; Owner: horizon_user
--

COMMENT ON COLUMN public.invitations.team_ids IS 'JSON array of team UUIDs';


--
-- Name: COLUMN invitations.token_hash; Type: COMMENT; Schema: public; Owner: horizon_user
--

COMMENT ON COLUMN public.invitations.token_hash IS 'Hashed token for /invitations/validate/{token} and /invitations/accept';


--
-- Name: COLUMN invitations.status; Type: COMMENT; Schema: public; Owner: horizon_user
--

COMMENT ON COLUMN public.invitations.status IS 'pending | accepted | expired | cancelled';


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.organizations (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(100) NOT NULL,
    display_name character varying(255),
    description text,
    email character varying(255),
    phone character varying(20),
    website character varying(255),
    address_line1 character varying(255),
    address_line2 character varying(255),
    city character varying(100),
    state character varying(100),
    postal_code character varying(20),
    country character varying(100),
    organization_type public.organizationtype,
    industry character varying(100),
    tax_id character varying(100),
    logo_url character varying(500),
    primary_color character varying(7),
    domain character varying(255),
    sso_enabled boolean,
    sso_provider character varying(50),
    sso_config jsonb,
    status public.organizationstatus NOT NULL,
    is_active boolean NOT NULL,
    owner_id uuid,
    settings jsonb,
    extra_data jsonb,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.organizations OWNER TO horizon_user;

--
-- Name: password_resets; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.password_resets (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(255) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    ip_address character varying(45),
    user_agent character varying(500),
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.password_resets OWNER TO horizon_user;

--
-- Name: permissions; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.permissions (
    id uuid NOT NULL,
    code character varying(100) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    resource public.resourcetype NOT NULL,
    action public.actiontype NOT NULL,
    module character varying(50),
    category character varying(50),
    is_active boolean NOT NULL,
    extra_data jsonb,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.permissions OWNER TO horizon_user;

--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.refresh_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(255) NOT NULL,
    token_family character varying(255),
    device_id character varying(255),
    device_name character varying(255),
    device_type character varying(50),
    os_info character varying(100),
    browser_info character varying(100),
    ip_address character varying(45),
    user_agent text,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    revoked_reason character varying(100),
    created_at timestamp with time zone NOT NULL,
    last_used_at timestamp with time zone
);


ALTER TABLE public.refresh_tokens OWNER TO horizon_user;

--
-- Name: role_permissions; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.role_permissions (
    id uuid NOT NULL,
    role_id uuid NOT NULL,
    permission_id uuid NOT NULL,
    conditions jsonb
);


ALTER TABLE public.role_permissions OWNER TO horizon_user;

--
-- Name: roles; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.roles (
    id uuid NOT NULL,
    organization_id uuid,
    name character varying(100) NOT NULL,
    code character varying(50) NOT NULL,
    description text,
    is_system boolean,
    is_default boolean,
    hierarchy_level integer,
    is_active boolean NOT NULL,
    extra_data jsonb,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.roles OWNER TO horizon_user;

--
-- Name: user_organization_roles; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.user_organization_roles (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    role_id uuid NOT NULL,
    is_primary boolean,
    is_active boolean NOT NULL,
    status character varying(20),
    invited_by_id uuid,
    invited_at timestamp with time zone,
    joined_at timestamp with time zone,
    extra_data jsonb,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.user_organization_roles OWNER TO horizon_user;

--
-- Name: users; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    display_name character varying(200),
    phone character varying(20),
    avatar_url character varying(500),
    user_type public.usertype NOT NULL,
    status public.userstatus NOT NULL,
    is_active boolean NOT NULL,
    email_verified boolean NOT NULL,
    email_verified_at timestamp with time zone,
    mfa_enabled boolean,
    mfa_secret character varying(255),
    mfa_backup_codes jsonb,
    last_login_at timestamp with time zone,
    last_login_ip character varying(45),
    failed_login_attempts integer,
    locked_until timestamp with time zone,
    preferences jsonb,
    timezone character varying(50),
    language character varying(10),
    extra_data jsonb,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.users OWNER TO horizon_user;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.alembic_version (version_num) FROM stdin;
002
\.


--
-- Data for Name: email_verifications; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.email_verifications (id, user_id, email, token_hash, expires_at, verified_at, created_at) FROM stdin;
\.


--
-- Data for Name: invitations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.invitations (id, organization_id, email, first_name, last_name, role_id, team_ids, invited_by_id, token_hash, status, expires_at, accepted_at, accepted_user_id, created_at, message, extra_data) FROM stdin;
\.


--
-- Data for Name: organizations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.organizations (id, name, slug, display_name, description, email, phone, website, address_line1, address_line2, city, state, postal_code, country, organization_type, industry, tax_id, logo_url, primary_color, domain, sso_enabled, sso_provider, sso_config, status, is_active, owner_id, settings, extra_data, deleted_at, created_at, updated_at) FROM stdin;
bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Default Organization	default-org	Default Organization	Default organization for the system	\N	\N	\N	\N	\N	\N	\N	\N	\N	business	\N	\N	\N	\N	\N	\N	\N	\N	active	t	\N	\N	\N	\N	2026-01-26 10:00:59.126378+00	2026-01-26 10:00:59.126378+00
9fe2bee3-cc0a-45e9-a1c5-fe1aaaf8ff6d	Cisco System	cisco-system	Cisco System	test it 			https://www.cisco.com	\N	\N	\N	\N	\N	\N	business	Technology	\N	\N	\N	\N	f	\N	\N	trial	t	23877693-a1d6-4cb2-9649-27f30cf98c2a	{}	{}	\N	2026-02-05 11:00:14.320065+00	2026-02-05 11:00:14.320071+00
9a9b7483-4327-46f6-852b-70c5faab67d4	Jumbal Mumbal	jumbal-mumbal	Jumbal Mumbal	kids brand 	dev11@gmail.com	9911452879	https://www.jumbalmumbal.com	\N	\N	\N	\N	\N	\N	business	Finance & Banking	\N	\N	\N	\N	f	\N	\N	trial	t	661678e8-12df-44bc-b50a-d69538eb9590	{}	{}	\N	2026-02-05 16:45:51.344787+00	2026-02-05 16:45:51.344796+00
\.


--
-- Data for Name: password_resets; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.password_resets (id, user_id, token_hash, expires_at, used_at, ip_address, user_agent, created_at) FROM stdin;
67a06c24-c316-40bf-813d-904ec09a2f16	386f1db2-caf1-40aa-aaec-bcf9a531356a	c438ffc197f73a45ec7fdf6990a03f3140fef84972bdcee61804c20d38421412	2026-01-27 06:33:37.164952+00	2026-01-27 05:46:39.588894+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 05:33:37.170197+00
c7bd0f9a-c298-4666-a140-f933fa1967be	386f1db2-caf1-40aa-aaec-bcf9a531356a	39a32e634742d10619f8100f8512eac4c1b36b3dc37eaa0f5ce8115ff0331050	2026-01-27 06:46:39.605367+00	2026-01-27 05:48:03.687111+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 05:46:39.60716+00
37d3b2e6-37d4-475c-8c6d-a292780ca28e	386f1db2-caf1-40aa-aaec-bcf9a531356a	5443ba4d2ccf93cc6de61fd79a17476f13b27c639fd6ee31a9a764c7ce4e3783	2026-01-27 06:48:03.696645+00	\N	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 05:48:03.698209+00
cda603ac-c33d-4c7b-9e29-1bf36bbb6ddc	8d509f22-5fe5-4765-9496-3a236cae2af1	937cec3b26a35b9deb911b1a82e5454752c890a0c7940d0cda49a502f27ff633	2026-01-27 06:48:53.510172+00	2026-01-27 05:49:17.729764+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 05:48:53.511449+00
1f957e01-08c5-4ccc-b4fd-6567fe417e8b	8d509f22-5fe5-4765-9496-3a236cae2af1	fc1009b7845e1560540f43914073b4d9da46f4cd31164fe7371d66d290b25116	2026-01-27 06:49:17.736587+00	2026-01-27 05:51:13.848115+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 05:49:17.737384+00
189c4d04-e889-4306-bd8d-64141dc6ffc7	8d509f22-5fe5-4765-9496-3a236cae2af1	e6ca645f38985f19cc042e891b423abacf9cc171e5c67f8a2e6c2715769ee4a2	2026-01-27 06:51:13.866049+00	2026-01-27 05:52:15.80142+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 05:51:13.868219+00
cede96ad-4140-468b-a8e2-7a8ec2db084b	8d509f22-5fe5-4765-9496-3a236cae2af1	b44f57be290a4e496628991aaf283baaf5e28bd2abbc46407e555778773db5e8	2026-01-27 06:52:15.815247+00	2026-01-27 06:12:51.743195+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 05:52:15.817569+00
8aba757f-afe4-4da2-af29-53db5a50ef21	8d509f22-5fe5-4765-9496-3a236cae2af1	2ba5b17780a0efdcf578e1e7c25ad44795565d51474ba0aa337cfc7a835a08df	2026-01-27 07:12:51.832214+00	2026-01-27 06:15:10.335412+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 06:12:51.836207+00
48c3daea-c0ad-4f42-9753-aa179f34483b	8d509f22-5fe5-4765-9496-3a236cae2af1	eb09b6af57566def0738961a802d54074df73bbc99e79d26f1129baad89898c6	2026-01-27 07:15:10.809717+00	2026-01-27 06:16:59.080993+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 06:15:10.828474+00
9789a73c-c5e4-4f05-bbab-3949c75fd5ad	8d509f22-5fe5-4765-9496-3a236cae2af1	aa45007ae8dd33dca2546014c7b5cb4ce0bc2327e8e0795aa4230db41d020ddf	2026-01-27 07:16:59.255801+00	2026-01-27 06:40:28.876288+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 06:16:59.289577+00
35ccdcc5-d347-4c05-9c22-eab3af03df45	8d509f22-5fe5-4765-9496-3a236cae2af1	3d9108d5ac6e467b0b8952fbb9f08cf89fd3cdb5028cfcc4c7e20d04c4923a33	2026-01-27 07:40:28.919907+00	2026-01-27 06:41:18.27393+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 06:40:28.935382+00
eb4057f9-0232-43b7-ba47-ffabeb7edf4e	8d509f22-5fe5-4765-9496-3a236cae2af1	d460b78a0a0b75284a39257a6bb12d2fa15dc62924e9acb4e4205d8683cd6841	2026-01-27 07:41:18.303323+00	2026-01-27 06:42:17.407291+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 06:41:18.305454+00
d808d199-d894-4a3f-a74c-9d9451e1e199	8d509f22-5fe5-4765-9496-3a236cae2af1	952f56beb0b9df68caadd5b542ef37ac9aca805a148a2193ace64ee90452e1de	2026-01-27 07:42:17.438671+00	2026-01-27 06:54:08.689058+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 06:42:17.44517+00
0403abeb-32a3-42d0-9c5c-6c17362758c5	8d509f22-5fe5-4765-9496-3a236cae2af1	7cdf53fdebfd41b32ad1b38a0baabeba3fef719d368bf77e7ab464d0c27f355a	2026-01-27 07:54:08.754732+00	2026-01-27 07:17:17.884767+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 06:54:08.763842+00
183f298d-3c94-42bc-aa53-1c3dd9ab4235	8d509f22-5fe5-4765-9496-3a236cae2af1	33bb3a4dbb565453e8a4baecb92e0aa8ed1540361d00c2522f394aa695923dcb	2026-01-27 08:17:17.949086+00	2026-01-27 07:33:27.022182+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 07:17:17.958186+00
5533c32f-2397-4041-aa51-51a3880e4adf	8d509f22-5fe5-4765-9496-3a236cae2af1	2a850427f681873ddbb16e70833a6c7de2a03e749dafa55e1f9d299af894b376	2026-01-27 08:33:27.046757+00	2026-01-27 07:34:30.91685+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 07:33:27.051206+00
8e35eae8-6d47-4a92-8545-afe947955045	8d509f22-5fe5-4765-9496-3a236cae2af1	b732cde2fcf1c78b300b1ef931d10a5e03be515a268c1ec0ab9a081b9d61f4fa	2026-01-27 08:34:30.959007+00	2026-01-27 07:55:51.583579+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 07:34:30.963755+00
848d0d7c-a414-43ec-9355-84e34810818e	8d509f22-5fe5-4765-9496-3a236cae2af1	b4fb624eaf5a439b2502c961c862de3a2fc43e6dcb221d678a3a1bb387e3f540	2026-01-27 08:55:51.628104+00	2026-01-27 10:09:01.612712+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 07:55:51.633393+00
f1ba16f1-0730-47bd-b933-6ed48e624b89	8d509f22-5fe5-4765-9496-3a236cae2af1	db1263fbdba11ad4aff8506a58c03ee9ebb5900ac0ce544464c6b77e2bb3c31a	2026-01-27 11:09:01.639837+00	2026-01-28 12:47:38.263319+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 10:09:01.643915+00
59168b54-d051-43ff-bd60-946b99c264c6	8d509f22-5fe5-4765-9496-3a236cae2af1	24feff31d8d000fbe0fa9aa269e3b81a454dd4896594db52195aa941742b378b	2026-01-28 13:47:38.27634+00	2026-01-28 12:55:23.409733+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-28 12:47:38.278616+00
72c40279-d55b-4c84-b117-ea6cb0f9869c	8d509f22-5fe5-4765-9496-3a236cae2af1	dc929d8e4dcb1fa49ef29a21f2da0e3c629a930be167270729a304c2d12311ad	2026-01-28 13:55:23.431343+00	2026-01-28 13:11:12.003278+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-28 12:55:23.435141+00
4b449058-a375-4ac0-bc01-bcd4b28251c2	8d509f22-5fe5-4765-9496-3a236cae2af1	e0cf3da7976009dbb4db99e914e563ff7b77971a9c7155b667dd3eb50472a2ff	2026-01-28 14:11:12.017384+00	2026-01-28 13:23:04.644505+00	192.168.65.1	PostmanRuntime/7.51.0	2026-01-28 13:11:12.019805+00
1533dbbb-9109-43c3-a1ab-73a4294134a2	8d509f22-5fe5-4765-9496-3a236cae2af1	7f49332d662b501fbdc64e5515b6c325bbcdd8e270d18a3d1f94c349b85e789d	2026-01-28 14:23:04.658466+00	\N	192.168.65.1	PostmanRuntime/7.51.0	2026-01-28 13:23:04.660635+00
\.


--
-- Data for Name: permissions; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.permissions (id, code, name, description, resource, action, module, category, is_active, extra_data, created_at, updated_at) FROM stdin;
676c8e81-b5c4-46c2-b8c4-b1f25dc78656	user.create	Create User	\N	user	create	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
0a3a14a9-1745-47ec-a83a-53f039e991bd	user.read	Read User	\N	user	read	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
f22fb138-7a26-4759-9f14-ebc38a1c1b56	user.update	Update User	\N	user	update	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
e1407dfb-e388-40d3-82d0-c03f00110b36	user.delete	Delete User	\N	user	delete	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
54ed2f72-bac5-48e6-839d-8dbfdf2817e9	role.read	Read Role	\N	role	read	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
3ab99a70-ee53-43f0-9fd1-cd77385d9e37	role.update	Update Role	\N	role	update	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
4269f718-a643-4e2a-b533-3f013d588142	role.delete	Delete Role	\N	role	delete	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
4fa16528-463d-4ced-ad89-eb8d103634d4	role.manage	Manage Roles	\N	role	manage	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
deb41dfa-239d-417c-a310-ecfb014c859b	warehouse.read	Warehouse Read	\N	warehouse	read	core	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
21310445-2f18-4302-9f2a-97b07aed8bb3	warehouse.create	Warehouse Create	\N	warehouse	create	core	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
17d6fdd0-7332-421f-805d-b5f204f8bd7e	user.*	User Admin	Mange User, All user module permissions	user	manage	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
b3baefb1-399f-4ff7-874f-b131014aa9f1	*.*	Full access (all resources and actions)	\N	all	manage	identity	\N	t	{}	2026-02-05 11:00:14.337744+00	2026-02-05 11:00:14.337746+00
a7392ca4-f836-427c-af5d-0782dead2d20	organization.read	Read Org	\N	organization	read	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
e135311e-4d1a-4964-be8a-c2f280c7537d	organization.update	Update Org	\N	organization	update	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
9e90b390-dfef-4c29-8a66-d031b44c54e9	organization.delete	Delete Org	\N	organization	delete	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
34d61530-7b12-474d-89a7-128ed062798f	organization.manage	Manage Orgs	\N	organization	manage	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
4e5b2e79-af28-4936-aaa9-4714596493f0	role.create	Create Role	\N	role	create	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
8c518ff6-2206-4b35-b0b8-1b8f47ac13fd	organization.owner	Create Org	\N	organization	create	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
c19e7a1d-9a36-47fa-a237-13213a80d674	customer.read	View Customers	View customers and contacts	customer	read	sales	Sales & Orders	t	\N	2026-02-07 16:59:37.503057+00	2026-02-07 16:59:37.503057+00
f0270ddc-dcc2-4e3f-96d7-b2c2b42cc594	customer.create	Create Customers	Create new customers	customer	create	sales	Sales & Orders	t	\N	2026-02-07 16:59:37.524275+00	2026-02-07 16:59:37.524275+00
2ed6b917-e3e2-434b-b440-6213e077abf2	customer.update	Edit Customers	Edit existing customers	customer	update	sales	Sales & Orders	t	\N	2026-02-07 16:59:37.526011+00	2026-02-07 16:59:37.526011+00
31d3ca77-f7bf-4064-b277-cefd09d99b22	customer.delete	Delete Customers	Delete customers	customer	delete	sales	Sales & Orders	t	\N	2026-02-07 16:59:37.527235+00	2026-02-07 16:59:37.527235+00
d3bdfe56-6436-4c72-9a1f-05628a516216	sales_order.read	View Sales Orders	View sales orders and quotes	sales_order	read	sales	Sales & Orders	t	\N	2026-02-07 16:59:37.527694+00	2026-02-07 16:59:37.527694+00
d57e8b48-e07c-4e3e-b6cc-8827e913c1bf	sales_order.create	Create Sales Orders	Create new sales orders	sales_order	create	sales	Sales & Orders	t	\N	2026-02-07 16:59:37.528644+00	2026-02-07 16:59:37.528644+00
eadbaa22-9c4b-4edc-9938-421caa5ae4d4	sales_order.update	Edit Sales Orders	Edit sales orders	sales_order	update	sales	Sales & Orders	t	\N	2026-02-07 16:59:37.52947+00	2026-02-07 16:59:37.52947+00
77a7f535-a162-47b2-9737-2cd206ae7a9b	sales_order.delete	Delete Sales Orders	Delete sales orders	sales_order	delete	sales	Sales & Orders	t	\N	2026-02-07 16:59:37.530691+00	2026-02-07 16:59:37.530691+00
159b3e0e-9110-4903-b9e7-0de734e47840	invoice.read	View Invoices	View sales invoices	invoice	read	sales	Sales & Orders	t	\N	2026-02-07 16:59:37.531712+00	2026-02-07 16:59:37.531712+00
df7e2b4d-2588-4aed-a2c1-c1373502abc8	invoice.create	Create Invoices	Create sales invoices	invoice	create	sales	Sales & Orders	t	\N	2026-02-07 16:59:37.532994+00	2026-02-07 16:59:37.532994+00
6f5988db-2fc2-456b-84b4-1eb2838365ef	supplier.read	View Suppliers	View suppliers and vendors	supplier	read	procurement	Procurement	t	\N	2026-02-07 16:59:37.533798+00	2026-02-07 16:59:37.533798+00
100fae83-e4ef-456d-bfaf-35b200396d26	supplier.create	Create Suppliers	Create new suppliers	supplier	create	procurement	Procurement	t	\N	2026-02-07 16:59:37.534437+00	2026-02-07 16:59:37.534437+00
be0e5f99-6be7-469c-ba3f-c2631eae7842	supplier.update	Edit Suppliers	Edit existing suppliers	supplier	update	procurement	Procurement	t	\N	2026-02-07 16:59:37.535014+00	2026-02-07 16:59:37.535014+00
a9b76098-5db6-4c13-a6e8-7b2595183ee4	supplier.delete	Delete Suppliers	Delete suppliers	supplier	delete	procurement	Procurement	t	\N	2026-02-07 16:59:37.535488+00	2026-02-07 16:59:37.535488+00
8978b045-700a-46f8-9f78-8826e61d6233	purchase_order.read	View Purchase Orders	View purchase orders	purchase_order	read	procurement	Procurement	t	\N	2026-02-07 16:59:37.536159+00	2026-02-07 16:59:37.536159+00
4889fee9-e89b-4003-954c-129a96786a45	purchase_order.create	Create Purchase Orders	Create new purchase orders	purchase_order	create	procurement	Procurement	t	\N	2026-02-07 16:59:37.536785+00	2026-02-07 16:59:37.536785+00
8be49709-7e8b-42b4-bffa-1943c168100d	purchase_order.update	Edit Purchase Orders	Edit purchase orders	purchase_order	update	procurement	Procurement	t	\N	2026-02-07 16:59:37.537362+00	2026-02-07 16:59:37.537362+00
ce9d3314-bd77-4fc5-ae3c-f146da6908d7	purchase_order.delete	Delete Purchase Orders	Delete purchase orders	purchase_order	delete	procurement	Procurement	t	\N	2026-02-07 16:59:37.537909+00	2026-02-07 16:59:37.537909+00
285a2ca5-b5b7-44ed-a3b2-ec800b0bc67e	item.read	View Items	View items and products	item	read	inventory	Inventory	t	\N	2026-02-07 16:59:37.538694+00	2026-02-07 16:59:37.538694+00
d807ae54-0869-49c3-b9f9-681de17c39ad	item.create	Create Items	Create new items	item	create	inventory	Inventory	t	\N	2026-02-07 16:59:37.53944+00	2026-02-07 16:59:37.53944+00
ee409d72-b300-4fdb-bc01-6154b16ebd3e	item.update	Edit Items	Edit existing items	item	update	inventory	Inventory	t	\N	2026-02-07 16:59:37.539907+00	2026-02-07 16:59:37.539907+00
2025d416-4850-46f2-bcaa-5623d78ccf90	item.delete	Delete Items	Delete items	item	delete	inventory	Inventory	t	\N	2026-02-07 16:59:37.54043+00	2026-02-07 16:59:37.54043+00
b2b17491-51eb-4750-ac32-ced20f006174	stock_entry.read	View Stock Movements	View stock entries and movements	stock_entry	read	inventory	Inventory	t	\N	2026-02-07 16:59:37.541577+00	2026-02-07 16:59:37.541577+00
ea789dac-9d6f-47ff-b0e7-6884c993af06	stock_entry.create	Create Stock Movements	Create stock entries	stock_entry	create	inventory	Inventory	t	\N	2026-02-07 16:59:37.542059+00	2026-02-07 16:59:37.542059+00
3af132fa-89a4-4b61-9ee9-0b44e1796783	batch.read	View Batches	View batch/lot information	batch	read	inventory	Inventory	t	\N	2026-02-07 16:59:37.542499+00	2026-02-07 16:59:37.542499+00
3b3f6a87-371f-4294-b784-f739eba477dd	serial.read	View Serial Numbers	View serial number tracking	serial	read	inventory	Inventory	t	\N	2026-02-07 16:59:37.542977+00	2026-02-07 16:59:37.542977+00
dcdd8b05-81ce-4fa7-8275-9b2e560fbb09	chart_of_account.read	View Chart of Accounts	View chart of accounts	chart_of_account	read	accounting	Accounting	t	\N	2026-02-07 16:59:37.54341+00	2026-02-07 16:59:37.54341+00
1afa24e4-e1bd-4573-94ae-c0489fd387d4	chart_of_account.create	Create Chart of Accounts	Create accounts	chart_of_account	create	accounting	Accounting	t	\N	2026-02-07 16:59:37.543941+00	2026-02-07 16:59:37.543941+00
bf551dfa-5d6f-4fe1-ad0b-61d7e5f26d0e	chart_of_account.update	Edit Chart of Accounts	Edit accounts	chart_of_account	update	accounting	Accounting	t	\N	2026-02-07 16:59:37.54464+00	2026-02-07 16:59:37.54464+00
670fa2a8-e7a3-40b7-b680-4a714679c123	payment.read	View Payments	View payments and transactions	payment	read	accounting	Accounting	t	\N	2026-02-07 16:59:37.545259+00	2026-02-07 16:59:37.545259+00
f0acf0ca-60ce-403e-866c-c3b884d75f6a	payment.create	Process Payments	Record and process payments	payment	create	accounting	Accounting	t	\N	2026-02-07 16:59:37.545947+00	2026-02-07 16:59:37.545947+00
af4658ad-7e73-4574-bbd4-64f2b5ceb54c	payment.update	Edit Payments	Edit payment records	payment	update	accounting	Accounting	t	\N	2026-02-07 16:59:37.547666+00	2026-02-07 16:59:37.547666+00
\.


--
-- Data for Name: refresh_tokens; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.refresh_tokens (id, user_id, token_hash, token_family, device_id, device_name, device_type, os_info, browser_info, ip_address, user_agent, expires_at, revoked_at, revoked_reason, created_at, last_used_at) FROM stdin;
a1f82344-11d1-4234-8cf6-752fe1810eb5	8d509f22-5fe5-4765-9496-3a236cae2af1	2353e38fc36f788c91fc4fe48d81d33fd414e73dc64214d07ccaabced7b54122	027f5d13-3ba2-4046-b339-18aac15fffc0	\N	\N	\N	\N	\N	192.168.65.1	PostmanRuntime/7.51.0	2026-02-02 16:01:22+00	\N	\N	2026-01-26 16:01:22.239939+00	\N
75d12443-69e5-4fb7-b068-54ca815539ac	8d509f22-5fe5-4765-9496-3a236cae2af1	a9cf5a0063e2bd11ef8f19980d49cbd0b9f3eaa0caee76bff510fa5c51df623f	101da132-6415-4a2f-80ba-8de82d706781	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-02 16:03:35+00	\N	\N	2026-01-26 16:03:35.86344+00	\N
6df0c44a-bb28-4307-8b7a-199504ecf8ec	8d509f22-5fe5-4765-9496-3a236cae2af1	4c66d4833d8f7bbb4d59bd88d12e27772018fde69f4c2d4f881b665bc2ff6093	4ca5b244-21a7-40cc-a882-6bcff3c62a91	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-02 16:28:21+00	\N	\N	2026-01-26 16:28:21.734422+00	\N
2f36e14e-9c89-494d-85a7-2875ab833943	8d509f22-5fe5-4765-9496-3a236cae2af1	9eb77ca832e8f46f1f7c61fe8992b467796a4ff4aa3bd0aeda22f68a87da56b4	847da4b5-52b4-4c21-8689-13cbe1bc67d3	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-02 16:47:17+00	\N	\N	2026-01-26 16:47:17.829679+00	\N
d9d07e79-56d3-4201-af1d-f4c3780936f3	8d509f22-5fe5-4765-9496-3a236cae2af1	fe8041d95091ae13f8a74483e3b5a94f4076696a07b54d41daab1a97fbf07c38	8b7a91b3-06ec-48d9-a1f1-e8b7250ec51c	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-02 17:02:59+00	\N	\N	2026-01-26 17:02:59.430075+00	\N
fc725610-f9ba-4ee7-8c39-81a2feaaae75	8d509f22-5fe5-4765-9496-3a236cae2af1	1fdeb885d28f070378f62426a4fe17bc3f6d016c2c4f2758c8e0711a105d5f56	85958dfe-aba4-453a-9ced-243096a916cc	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-02 17:16:23+00	\N	\N	2026-01-26 17:16:23.297546+00	\N
d0ec75c7-a73c-4724-a6d8-f488658cbc89	8d509f22-5fe5-4765-9496-3a236cae2af1	06a8e72dae5efb0afdf4b2cc64405f869133d4adc6484dfb6fffe5deec06bfac	4e35dd9e-9f8b-42b5-bcb8-da05bb6918ba	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-02 17:23:51+00	\N	\N	2026-01-26 17:23:51.687477+00	\N
6af99240-d0de-4f34-a041-f471759b740a	386f1db2-caf1-40aa-aaec-bcf9a531356a	e5c9c4ff4aa5aaf0768e7a72e2b5d808ad304f3caa1a2b64c5b59a53d9388cd1	ed9c97e4-3a88-4ce2-9ab5-dcd41af1b7bb	\N	\N	\N	\N	\N	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 05:31:43+00	\N	\N	2026-01-27 05:31:44.001284+00	\N
b6e3a403-56fa-4291-8652-05c06870b0c5	8d509f22-5fe5-4765-9496-3a236cae2af1	83166a9817e1ad20c31317739b202cf330c0c04c7904dd7c6400f40cf67f9d77	ae697580-1445-4ab8-9ae4-52c9753eb261	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 10:03:56+00	\N	\N	2026-01-27 10:03:56.688739+00	\N
9fac839b-2f2a-4fe5-b6dd-281c21969b37	8d509f22-5fe5-4765-9496-3a236cae2af1	fe4244550728ff07f0e6358694d238709ea4b868fcf010f9ed27c89c33c07ac8	dd842f40-8444-4513-b879-5a836b252803	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 10:19:49+00	\N	\N	2026-01-27 10:19:49.705894+00	\N
08c87ab8-f368-4cf1-8b8c-de35d9b7854c	8d509f22-5fe5-4765-9496-3a236cae2af1	660b1d78c99cc00208e6ec3606059d5c36a367041cfc8787f7cad15283427368	a24ca080-5dd5-4ba7-b6b5-126d05d6490c	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 10:38:16+00	\N	\N	2026-01-27 10:38:16.650758+00	\N
00084246-b9b8-45f2-bfd3-5b954cf8b21b	8d509f22-5fe5-4765-9496-3a236cae2af1	8e559da7165757c141c4ee634907c1921f7812a07bb8682114735a7e04ac7e77	a59f7efe-c06c-43f4-8075-24fcaf0630e0	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 16:34:04+00	\N	\N	2026-01-27 16:34:04.737035+00	\N
21a32dc4-d900-48c1-848a-5c9fc3b1c0c7	8d509f22-5fe5-4765-9496-3a236cae2af1	db5d815cbf04fde2540bf25dfc806c2ddd4dd786cc99b63ff78b2adcb27fce0b	cf1b4ab2-b492-43c6-a2d6-e1ba70d6f0e4	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 16:51:08+00	\N	\N	2026-01-27 16:51:08.050933+00	\N
a45e66d1-9bcf-49aa-85a3-163893fec49e	8d509f22-5fe5-4765-9496-3a236cae2af1	25b39cc91d08283041761dc43b9498fd3cb7907296254c3609d8449cb810e34f	3e42fddd-6576-456a-8322-30949110bc31	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 16:54:38+00	\N	\N	2026-01-27 16:54:38.268373+00	\N
f1638f00-2267-465f-86e7-920536408983	8d509f22-5fe5-4765-9496-3a236cae2af1	3078011948afeb13d38cc5e43b78bdfa7a24b7fbc4cc74f77cef18318792c626	887f93ce-e19a-47c5-b1e3-4b6123b212f5	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 16:57:49+00	\N	\N	2026-01-27 16:57:49.944191+00	\N
e68dc618-425d-4019-a669-17ac12cbccb4	8d509f22-5fe5-4765-9496-3a236cae2af1	2eb4a03b8030f0acbdd61d5f2157bf86a9baa0d5f55691ab67c8cc800bf666fd	05f8c2e5-7a04-4a84-802d-b950889ab568	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 17:04:55+00	\N	\N	2026-01-27 17:04:55.02811+00	\N
f0d0a226-675a-45ed-b73e-37e4d5706a2f	8d509f22-5fe5-4765-9496-3a236cae2af1	50eb59189de51b773d48ba4d2e631ee532b9ee758456ae16130f060774f9bafa	835a2b0c-74cf-4a8c-b6ad-abe3215e1a16	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 17:04:59+00	\N	\N	2026-01-27 17:04:59.025525+00	\N
fef9470a-1d95-4401-91cd-635e05f7ac9f	8d509f22-5fe5-4765-9496-3a236cae2af1	6b2e69148f484d484a7737a197a0bc58b9f08845e0a7aa7fe36236dbef651689	d90ea59c-2d4d-4364-bc32-03a5a89c11e2	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 17:09:00+00	\N	\N	2026-01-27 17:09:00.176989+00	\N
46290522-efc5-464a-b18f-129bdb3f773f	8d509f22-5fe5-4765-9496-3a236cae2af1	ad3725e3cecfbe8ed78c76ff862ff595f183c4d6d4988f2d754fbb7157d3a711	593340a2-1ba7-4863-8b04-35a343081bfa	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 17:20:55+00	\N	\N	2026-01-27 17:20:55.816368+00	\N
699b34b8-6337-4010-80c4-53173c225d09	8d509f22-5fe5-4765-9496-3a236cae2af1	3ef0ec3900f8ef70ffe5f6bb3abec50c24e2876760be7cf18b5f1a1ef15910bf	17d53ba7-4683-4848-b635-c6ae6d991833	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-03 17:48:32+00	\N	\N	2026-01-27 17:48:32.049323+00	\N
48263883-d716-40b9-80e1-2cb99830956a	8d509f22-5fe5-4765-9496-3a236cae2af1	624fd6ce6b3576df63729de46258fa2bc008931e1721e30d959fe2214a4047df	6bbec4a9-3187-40ab-8959-3c3cb89aa146	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-04 07:50:33+00	\N	\N	2026-01-28 07:50:33.717088+00	\N
708885f3-4e30-4909-b341-ab1172b9c718	956138ed-1e93-491c-b204-2824c88df765	2592232c1069515e43bfa3ea3ec5865397131939f8c9114661ca359f6be5a6c1	8226bfee-d9d1-4a7c-83a1-81261bccb7de	\N	\N	\N	\N	\N	192.168.65.1	python-requests/2.32.3	2026-02-04 08:13:02+00	\N	\N	2026-01-28 08:13:02.065435+00	\N
fe9f7196-cb5b-440d-8fb8-f37eaed41e28	cc7f225b-f30e-4559-a0b9-7bfba2062a82	a89901e68df5bce3802e4f2a91c7ffc057d52a972d575c338210dd6c90c4f115	3f8506f5-6faa-4995-ae45-17fd4aeb9085	\N	\N	\N	\N	\N	192.168.65.1	python-requests/2.32.3	2026-02-04 08:13:13+00	\N	\N	2026-01-28 08:13:13.823541+00	\N
4ff378ed-5de3-438f-8a9e-6c4cd1a6f561	72c698bf-3d7d-4f9b-812b-66fb3109dbc1	fb2e9a48a55523f54d0c3eddb9f8921f5e95aa8b7ca3e3619d43ae5db2f0f912	a0b2b0e2-6edb-47ca-b274-53d3f4382845	\N	\N	\N	\N	\N	192.168.65.1	python-requests/2.32.3	2026-02-04 08:13:23+00	\N	\N	2026-01-28 08:13:23.681538+00	\N
6d7d030c-4627-4c8a-9e84-a77f0a5f33d0	8d509f22-5fe5-4765-9496-3a236cae2af1	6d3dc3c9edb956df9e0a8ae322ea99e939eda21f1dabe185606fad007f7b0d71	9ca679bd-1c6d-4c34-96bd-f1a29a561116	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-05 17:52:51+00	\N	\N	2026-01-29 17:52:51.811916+00	\N
894488ee-ae36-41c7-ae11-61c1138ea521	8d509f22-5fe5-4765-9496-3a236cae2af1	df21a2fde7ba20451e097a06316c5e91e84a9df823dcb71c18c2bfa4f1416ff4	d3bbdc67-f181-410a-b0d5-17678dbe0fe1	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-04 06:11:20+00	2026-01-30 07:38:12.11684+00	user_logout	2026-01-28 06:11:20.713351+00	\N
a16363ec-09a1-468b-9772-d6d6f0237587	7f8a4e1a-db39-4615-8a21-2e93f0a80875	a365a2cffd7e7d4a24b7d6578bfe6b10968254c762b0db1435cc255f2cdfdf1d	55b281ea-ba66-4ec2-b278-e14aa21dc93e	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	2026-02-06 08:01:06+00	\N	\N	2026-01-30 08:01:06.035038+00	\N
067c18bf-a6df-4710-8db5-5ec109fae16b	de75c704-b47e-4598-a546-3795650cc67b	024ef5faf3ed64cbde66ee553ed4f572f64faa2f858a988299698fde34e405da	4d463839-71ab-4f9b-95e9-2441721d1ab4	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-06 13:43:44+00	2026-01-30 13:44:11.944036+00	user_logout	2026-01-30 13:43:44.92517+00	\N
adab4734-46c9-4457-b6fa-97686293fc6e	8d509f22-5fe5-4765-9496-3a236cae2af1	ce4b3b7a90af5de52d1d170b1362e69573cfff3ba80383d1935192cfa8a56187	3bf53df0-ea71-4628-b5fb-3205569aceec	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-06 13:44:29+00	2026-01-30 13:44:40.894587+00	user_logout	2026-01-30 13:44:29.885844+00	\N
2a7db772-bb5a-4b37-a9b4-c8b40afcc05e	8d509f22-5fe5-4765-9496-3a236cae2af1	18283bbfc665817aa15515625b2a3d8333b555d5233d1cfc51b9d275fb844ab4	d0673b5c-2b92-4e92-ae94-9ff04f176f68	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-06 13:45:04+00	2026-01-30 13:45:38.914545+00	user_logout	2026-01-30 13:45:04.18217+00	\N
3480a11e-28eb-4350-b2a4-97f9fc7a5161	8d509f22-5fe5-4765-9496-3a236cae2af1	5874b960c918f6cfd76809cc2e991ef5e127ee882b3da1d5ff27dc6d00a41251	c09cdddd-b7b3-45e0-aa99-e1c88ebd8192	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-06 14:20:58+00	\N	\N	2026-01-30 14:20:58.176117+00	\N
b022b033-2512-49bc-bee0-c9794e48f67d	8d509f22-5fe5-4765-9496-3a236cae2af1	2c04cb05366ece1e3ac6e8258d13aaa9d8439c8da80b63a78312bf869e99a11c	841dac6e-c877-4eeb-ac2e-fa85e0878bfa	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-06 14:31:11+00	2026-01-30 14:31:18.510853+00	user_logout	2026-01-30 14:31:11.558392+00	\N
d6633e95-2a5f-419f-ad3e-922b74b9a4cd	8d509f22-5fe5-4765-9496-3a236cae2af1	76f24d2f3de919ea7fd6d757423dd5be7ab9ac81749a13f7dc327f4d287b7558	a933a3ff-3dbe-4e1f-8242-010a1961cac3	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-06 17:06:02+00	2026-01-30 17:06:06.98161+00	user_logout	2026-01-30 17:06:02.758686+00	\N
8e11980d-9b51-4a1c-be7e-7990851b9d6f	de75c704-b47e-4598-a546-3795650cc67b	b78ccd2ff999f741445d3428abeb8de8661bbaf6a697445e28c46f3932b13f60	dfe484b7-3312-44cb-b54f-3f0c98970d3d	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-06 17:19:47+00	\N	\N	2026-01-30 17:19:47.495773+00	\N
6c3110d8-ffb6-4d03-aca4-55632010903c	8d509f22-5fe5-4765-9496-3a236cae2af1	b20cddf1553ded496c01bb6e379526a8e0092e0223fd04537b06b73057c543a8	ba6dd24a-d31b-4e69-ac54-c544bb43fe5c	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-06 17:20:59+00	\N	\N	2026-01-30 17:20:59.483684+00	\N
aac9aaef-32d3-4b5e-a984-708cb1a9fc31	8d509f22-5fe5-4765-9496-3a236cae2af1	28d9707d1907cf1234292714fb6365acbe98d472c2605a1b0679ad8333363452	7f8db768-bfef-448b-bc9d-ebb47e007670	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-07 02:01:11+00	2026-01-31 09:30:05.305678+00	user_logout	2026-01-31 02:01:11.849546+00	\N
695638b3-0c20-4a22-90d0-aab6b7b22edd	8d509f22-5fe5-4765-9496-3a236cae2af1	93b4e2051b5467b9726820a06a5e43f0a349ac2c790145012300cf5b87564424	d8897d6a-37b9-4f90-89a5-5a77ff80cdf2	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-07 09:30:57+00	\N	\N	2026-01-31 09:30:57.804246+00	\N
9df00364-b637-462c-bbc8-ff49c99ce1b8	8d509f22-5fe5-4765-9496-3a236cae2af1	dce28087706659829227ac6b291887139c21e299992f299e0e23a8dac2ed898c	59accd0a-b442-43dd-bfb9-f37418311448	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-07 09:57:38+00	\N	\N	2026-01-31 09:57:38.935191+00	\N
bbda23bf-d195-446e-8556-e9067a827305	8d509f22-5fe5-4765-9496-3a236cae2af1	d3de1f452e4fac268d5fc12421616a8e2709bd465940007ce6f7cab2324dfccf	6b7bccf2-8d92-490d-a283-8a862e54f6b7	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-07 13:50:08+00	2026-01-31 13:55:40.184885+00	user_logout	2026-01-31 13:50:08.212542+00	\N
536f42c3-8251-47f1-817e-a4e189a6f919	129a038c-888a-47f6-ac80-8b0c35646afd	8f4b493eedfe79030ba06abb79d7135ea92f1f728bdb7efac930eb02f7934040	c1cda384-55de-47ca-908d-ed94d6886829	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-07 18:07:33+00	\N	\N	2026-01-31 18:07:33.234436+00	\N
8defd911-a286-418f-a90e-67b9443da95f	8f993936-5cc5-4181-8046-9a7faf046e57	1ccc0b537a15a91400476c83174d7d9bd1bb58d3817f2ae2cfe4a1a103ac41d6	92cb6d40-5db3-4773-b18a-81b86460871d	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-07 20:53:12+00	2026-01-31 20:59:56.518153+00	user_logout	2026-01-31 20:53:12.977601+00	\N
eacb0228-34f8-4c8f-999c-bbcb0b245dd4	4f676bac-7a97-4a6a-8dbe-2f16a03e0c30	3151c9975cc1f85d423b8e84d9f1c767cc96810eff0dfcbc0c540520585a04a5	bdb9f311-c712-49e7-b659-b4ded55eb9e9	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-07 21:00:37+00	2026-02-01 10:53:35.590091+00	user_logout	2026-01-31 21:00:37.360812+00	\N
b20ae2a2-b0da-4ab6-bbbc-1295a5867bb0	fd0aaaac-f93c-4b69-9cfc-f33d7e650545	130a087b2ae404ef24319748606a15cdbacddb764cf1bb8e736e991d222dd3a9	8833391d-d7fa-495f-9656-402dc5067c21	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-08 10:54:20+00	2026-02-01 16:44:36.413203+00	user_logout	2026-02-01 10:54:20.45549+00	\N
fd2f2c6c-f981-4010-a88f-af14967a1ca7	8d509f22-5fe5-4765-9496-3a236cae2af1	596f8686359ca1464e5eb6d15c01ed408041be5a43456c12db9ba1eef5371d48	4001499c-24f9-4dd6-9e80-8de224aada2e	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-09 07:37:41+00	\N	\N	2026-02-02 07:37:41.817368+00	\N
7971970e-2375-41c5-9616-fd398119a74c	421a11a3-d224-47fc-954e-af332b5bbc65	2b6bce75b0fb2e36da00131867fe2b629654af07a0bd34bb717414936e759e0f	902b8296-699d-462a-b7d9-b2b58dc848a5	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-08 16:45:48+00	2026-02-02 08:02:32.265716+00	user_logout	2026-02-01 16:45:48.335695+00	\N
9cf46d16-89cf-4169-8fce-4df6ef9bc057	8d509f22-5fe5-4765-9496-3a236cae2af1	f80e39fa83b32386726db94f4bb1fd2995cfabc82a58d3e4e4129e7b8e517b4e	d7bd4c95-c287-44b1-af50-78abb8ca37ea	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-09 08:04:23+00	\N	\N	2026-02-02 08:04:23.49165+00	\N
e8f6012e-25af-4832-83a7-7005fc923f47	8d509f22-5fe5-4765-9496-3a236cae2af1	6e7ab16affbf8d412abc63ae4e948661d1998ff1eb14ccb77f708855e48707d7	95c6e992-8c81-44d0-b27d-878acde69684	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-09 09:36:33+00	\N	\N	2026-02-02 09:36:33.659478+00	\N
46187eee-1b87-406c-a87e-3dad3d46e905	8d509f22-5fe5-4765-9496-3a236cae2af1	606243075badd20b0393a2b72a433ffa358898995612c08861685da90f5f4d90	1ca3b942-6915-4e01-a0a7-3107abfb9e01	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-09 10:02:49+00	\N	\N	2026-02-02 10:02:49.201797+00	\N
c406a935-af14-423e-858a-effa96637f8e	8d509f22-5fe5-4765-9496-3a236cae2af1	f8019213000d61d31022759e9d89768c1881c0069d8fbc0a65214eaa869bddf2	39184596-40d1-415c-a319-1342aa26031a	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-09 10:20:42+00	\N	\N	2026-02-02 10:20:42.652403+00	\N
2c92dd26-87b2-447b-9e09-c7e73d802a46	8d509f22-5fe5-4765-9496-3a236cae2af1	41907d313ff6262e82c0344a74e6f135c238dce54c57cfaad1cc99cefa1c694e	53897809-de26-4de6-a6ad-9382d888cd38	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-09 10:25:40+00	\N	\N	2026-02-02 10:25:40.062274+00	\N
d4895772-4856-46c8-84e1-59b125601658	8d509f22-5fe5-4765-9496-3a236cae2af1	2d23563b12f83aed3cc9114222b525014e0c073dfb1b9ff0f7eeeca82fc517f3	cf001f58-b5d2-4b88-bbae-b1681dafb6b4	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-09 12:58:27+00	\N	\N	2026-02-02 12:58:27.671157+00	\N
18412ae1-cbff-4161-ba82-fad671877bed	8d509f22-5fe5-4765-9496-3a236cae2af1	b763edb003195f44834208491056b9bdc9e48beb3362f35e7e3906a96957b974	99445b2a-ceec-4f52-b37e-5a94710a1d1f	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-09 13:21:36+00	2026-02-02 13:29:12.586893+00	user_logout	2026-02-02 13:21:36.685483+00	\N
32a9a3ee-1317-43b0-a77f-ba794571a144	8d509f22-5fe5-4765-9496-3a236cae2af1	e4fe4bf357ccf12cd862b8f5c36ebfa67b0ca2b4365cfd55408f417eb7fe6915	651a54d5-22c3-41ae-a929-bb6b6dcaecd2	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-09 16:06:51+00	\N	\N	2026-02-02 16:06:51.784286+00	\N
3a975cba-3814-43df-81c3-eaad2053cb1e	8d509f22-5fe5-4765-9496-3a236cae2af1	353d354cc8cbe48489fa6023c5a20e86923d2e3ab5df71b1ac5dc2540e7cf97a	0b4a3f28-7130-4061-8985-c6304159f148	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-09 16:09:08+00	\N	\N	2026-02-02 16:09:08.319785+00	\N
9295b555-aab6-452c-bd02-be9afae12bce	8d509f22-5fe5-4765-9496-3a236cae2af1	e0525fba5dbaca3c7c34962cc5fd2ae136ff43daad4805bd7d1fbe3cc33c2f8e	fe2b782f-c69b-49b3-bb46-efebc7927273	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-09 16:19:43+00	\N	\N	2026-02-02 16:19:43.568451+00	\N
be8fee4f-cd91-4740-9028-36b8d170a606	8d509f22-5fe5-4765-9496-3a236cae2af1	4153633384e4831de244ae87b942b6e26c3cb88cf4ba9c51b1ee02768ccf614b	5a0cec7a-2bec-49c5-8d81-60564e73fb17	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-10 06:58:57+00	\N	\N	2026-02-03 06:58:57.76425+00	\N
dbcf7d23-c584-4792-a624-c91c82006048	8d509f22-5fe5-4765-9496-3a236cae2af1	dc05e6557ef9382309b05bf570dc00360d30ec313a71ecb7c78732146bdcdc9b	30127ae9-89fc-4c1b-8639-bb8e141fce3b	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-09 13:37:39+00	2026-02-03 08:10:13.709857+00	user_logout	2026-02-02 13:37:39.896712+00	\N
aae0e62a-6a0e-4b44-9e3b-abd38cb904d7	8d509f22-5fe5-4765-9496-3a236cae2af1	ff498b86ef32007958abe927887e6340f44d3891a0bf0740660fd1153e6466f9	fee7955e-a47d-41e0-8e42-8a66e3d3d87c	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-10 08:10:36+00	2026-02-04 10:07:05.351266+00	user_logout	2026-02-03 08:10:36.371445+00	\N
d5b82f4d-528e-4aa1-b33a-3824adfad411	8d509f22-5fe5-4765-9496-3a236cae2af1	ab5b3bfe59a6a2c5a41ed711c1dee5f3b96b8635dd7cb451d752b084fc1bd697	bbb05020-f93b-463b-a01c-9b417bd0cb24	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-11 10:07:25+00	2026-02-04 10:31:44.249349+00	user_logout	2026-02-04 10:07:25.53841+00	\N
d4e815e1-d814-4d7b-978a-a22cac138131	8d509f22-5fe5-4765-9496-3a236cae2af1	552d28cd2ccfc93527cf929aa6bbd59d45399189066387c122e11c5a05059e43	42cf4226-19c8-4652-85d6-3a97f4c45273	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-11 10:31:57+00	\N	\N	2026-02-04 10:31:57.296783+00	\N
a14117ca-689c-47ef-afa7-09dc00c4613d	8d509f22-5fe5-4765-9496-3a236cae2af1	944026a5d4fb8f30d7096f915c2c4d8289cfd0583d64a6167194c0ab2f13c106	fdb33d36-cc89-4ad4-a528-2c915e492ad8	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-11 14:10:44+00	2026-02-05 07:34:25.545305+00	user_logout	2026-02-04 14:10:44.113939+00	\N
527eba4c-a23e-4487-ba2f-3d3736bc03e4	23877693-a1d6-4cb2-9649-27f30cf98c2a	1fd2d81a08297fd28de6e4f144471866a6145bd5e2a91160c34bd5e22678aa79	373f32e3-2314-4237-92af-510064d59b75	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-12 08:03:17+00	\N	\N	2026-02-05 08:03:17.444638+00	\N
8d392f6c-7b81-4564-a32f-a1c72d28afbf	23877693-a1d6-4cb2-9649-27f30cf98c2a	caa302bc090b938637d4b0574cca63024c957ff87167349e164acc0902320a2a	d2872f88-1dc9-4932-a0a4-04a1eeae818a	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-12 08:06:58+00	\N	\N	2026-02-05 08:06:58.028769+00	\N
eaa9f1d7-8795-4b56-a80d-54c6e0099177	661678e8-12df-44bc-b50a-d69538eb9590	40466afb726a49591b1579a745bef33eb4cc276aae1c5c4e9a9a6441d51c79e3	3db00399-7f12-41fb-a795-141b69107456	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-12 08:46:10+00	\N	\N	2026-02-05 08:46:10.933113+00	\N
dba4ac78-ebc4-486c-8618-9cf2d0524b4a	c086f967-cac9-4ebe-88e5-aa9b6c43e22c	0773be6beb22493e50f039ee599e52efe0434aeb37d31b1d96ac1cbccfb7b539	c83a82f2-ff72-4804-9fd1-f4b5320bd764	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-12 09:33:13+00	\N	\N	2026-02-05 09:33:13.47804+00	\N
d4e4047b-7e2e-4ced-bda0-4db49172f03f	e6b6d300-77f3-4812-9c73-eef8280a2466	bdbdb65b3a05cafdfe247f2648a823f2ae6ef8b460bd5aca6a069ccabcc9a8e5	dfeb6c6f-034e-4994-a7b4-54fba8f5162b	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-12 10:15:27+00	2026-02-05 10:44:44.913307+00	user_logout	2026-02-05 10:15:27.046308+00	\N
f5d2e1c5-b33b-494b-b5be-2b34f1c0665f	dd017f5e-5532-4d25-a472-087ac3828c9c	40bc03105598d381f3238bd64b3e6d11039f45e1449dcda3caa4c4e1051f0167	19a4b939-a9a9-4227-8514-5b48f634762e	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-12 10:46:15+00	\N	\N	2026-02-05 10:46:15.651317+00	\N
be75d6ee-2573-4801-be8b-0cfd5f49dae7	23877693-a1d6-4cb2-9649-27f30cf98c2a	759c80bd21be7b1def238e7b7f1bafbf908a14649ff137683db7eefb9e442b5b	3df7a315-28bc-4b8b-bdef-563e27f94f2e	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-12 10:58:28+00	\N	\N	2026-02-05 10:58:28.385382+00	\N
94dcb3c4-186a-4fbf-bca7-901cc485dcb3	23877693-a1d6-4cb2-9649-27f30cf98c2a	611fcbd5737545f86a20705e226b2b7f314d58fa6fc5ae0cfe009d4cc1242b4c	7ee57c35-0838-4886-accc-695fa0180353	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-12 12:11:07+00	\N	\N	2026-02-05 12:11:07.592367+00	\N
2611f796-9c5c-42dc-96cc-2b0e4723f327	8d509f22-5fe5-4765-9496-3a236cae2af1	a186fdb7762150e8b1de1859d135f45c7953f7618f28c1e68314357e7fcd8cfa	bc272ab8-5998-4619-828c-44eb9f46cba2	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-12 16:22:38+00	\N	\N	2026-02-05 16:22:38.27267+00	\N
747fad2a-2f5b-47ab-9807-d5e8a59658ff	661678e8-12df-44bc-b50a-d69538eb9590	9964d39442a122304981a53e7f94d2316d81e753a6c163b7e142786f9dea697c	44613d7d-3c1a-4095-a262-166a8e5bd92e	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-12 16:45:03+00	\N	\N	2026-02-05 16:45:04.004328+00	\N
704334ac-0e96-46a2-a679-02df2129d56e	661678e8-12df-44bc-b50a-d69538eb9590	94c4c5564fab9916e3382e9675507710fb37f542cc2ebed67a7f138283f8286b	d950f9e8-300e-436a-92ea-ccca22760d6c	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-12 17:44:46+00	\N	\N	2026-02-05 17:44:46.381489+00	\N
0ba10613-a3fe-4410-b185-272988d54f80	23877693-a1d6-4cb2-9649-27f30cf98c2a	e8988b067dd80fe24616c4f56706973ac08d7ec6a8dff34c748ad9b84daadc46	5ca5397b-d0c4-4dfd-ba93-56f723857e31	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-12 17:47:09+00	\N	\N	2026-02-05 17:47:09.903604+00	\N
b0db8092-64d5-456a-a0db-e409d05abe41	8d509f22-5fe5-4765-9496-3a236cae2af1	04afc8d46d23755bf4ad9ab5f622a2f01780b6e79d56444314787a1911545366	3a475b74-e559-490c-8019-884c65511089	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-12 18:11:28+00	\N	\N	2026-02-05 18:11:28.536091+00	\N
0a95b2a8-5216-4446-be29-978d9d32f92e	8d509f22-5fe5-4765-9496-3a236cae2af1	c1d17e2e7ac9f76a145c8b9319dcd5442180dcf5ee15bc32a9caa4722af5ef55	0b94c6cd-a559-40b4-b108-14d69bce83fa	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 04:10:48+00	\N	\N	2026-02-06 04:10:48.446415+00	\N
d2c6d0b9-e29b-410e-93f8-c82520815db8	661678e8-12df-44bc-b50a-d69538eb9590	a9dc3cdf30013d0671cbe73964fe8b94987d504342ceadcd36fd07a5f22abae2	199e1ada-bbff-4c18-a6e4-c3cd75b6daec	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 04:14:35+00	\N	\N	2026-02-06 04:14:35.621013+00	\N
d5f80ce5-4687-4102-ae4e-5aa9b6aad047	23877693-a1d6-4cb2-9649-27f30cf98c2a	74111c77553468de6747a5de6f409586bd4d068f5b4ec4e4b293af3d57375cea	46ce49b8-f362-4534-908d-50a864118ad8	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-13 04:58:56+00	\N	\N	2026-02-06 04:58:56.654512+00	\N
5804dd84-98e4-4172-b2e4-97e4ec04fcf0	8d509f22-5fe5-4765-9496-3a236cae2af1	619a48efd9cb8e6374fe25de3b6349ce47eb711845994e226144b45ce2459682	dcd5a0c7-9f5d-4e55-96d0-b1e48e62f366	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 05:24:15+00	\N	\N	2026-02-06 05:24:15.817631+00	\N
c2c7252d-2881-4376-bdca-3d95f73be3fe	661678e8-12df-44bc-b50a-d69538eb9590	ca4bf3e55134a797ea99ca5461fd25c1a157e6971100a9f38d4cf391425a991a	1907ca67-5eb8-4b82-b044-c8fcdd26f96b	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 05:46:37+00	\N	\N	2026-02-06 05:46:37.807694+00	\N
96bb1cdc-9a50-433d-a4ca-30f8ce012929	8d509f22-5fe5-4765-9496-3a236cae2af1	a19d6ce3e5a7947278d339ac6e106de7a8cca18d566d45f83e9dcaa1a92d7585	e0b1083d-8f5e-4d9d-b757-b20339048950	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 06:01:47+00	\N	\N	2026-02-06 06:01:47.220007+00	\N
f919f663-10c3-4632-84f3-5166d4d75332	23877693-a1d6-4cb2-9649-27f30cf98c2a	60097c386b918d58b00166ff1289a5316048ff36ec971280a39a248bf7ea13be	0340359b-d8f7-4d50-ae63-b2a256ba6809	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-13 07:06:12+00	\N	\N	2026-02-06 07:06:12.463644+00	\N
5f94dcf9-bca5-4cff-9c6f-540cb8ca0f45	8d509f22-5fe5-4765-9496-3a236cae2af1	b2c8945996534283c3c4edd2784280b344c5c622272377d654e5efcaa9aa818c	53aa3d66-f14f-4cdc-8433-2413a3d3b15e	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-13 07:06:23+00	\N	\N	2026-02-06 07:06:23.231447+00	\N
a8bdd1ef-c913-4286-886f-862b5eb99d9d	8d509f22-5fe5-4765-9496-3a236cae2af1	0c1c56ae66ed2fb37ca62b81d30fa50b564c69fbda678f305c18b5266115ef9c	43de91c4-f0e2-4c2b-95c8-e4ad115a2f76	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 08:02:49+00	\N	\N	2026-02-06 08:02:49.411521+00	\N
78f90f10-0508-4878-947c-13349dd392c7	8d509f22-5fe5-4765-9496-3a236cae2af1	0e8194c41d49219b0cf1fe25cffc1c8e261044255c5258ccb6f9f8f885807fca	7811abd4-26e5-43ae-96df-2a7941b8ac09	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 11:37:05+00	\N	\N	2026-02-06 11:37:05.582608+00	\N
198c40e2-e334-4dc4-b186-30dd35c8f2e4	8d509f22-5fe5-4765-9496-3a236cae2af1	edf5b66383dc4997387409bd614f7aea83103ca2c58e6d87be418772136307fc	e71f7dfa-7b44-4a32-a2e7-13ff73aedeae	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 11:39:10+00	\N	\N	2026-02-06 11:39:10.997397+00	\N
cf57dab7-505d-403f-b36f-b33d69509059	8d509f22-5fe5-4765-9496-3a236cae2af1	b1473c56ec049d5bfbc8bb5fa0e6d28b7464acef70eb9dd164267a2f468caac0	cdc4fd9f-b0e2-4e65-b44e-f029db8e8476	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 12:09:17+00	\N	\N	2026-02-06 12:09:17.046204+00	\N
b222710a-36bd-4aa9-8401-a94344610848	8d509f22-5fe5-4765-9496-3a236cae2af1	2fe66d5defd08ab30920b249491992b803154276d9a41f744256231e8f5d6770	e2f35708-e625-492d-af66-3ed44b38410b	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 12:12:43+00	2026-02-06 12:55:55.311435+00	user_logout	2026-02-06 12:12:43.669342+00	\N
90d330c4-ad45-49c4-9a6e-2a8544d4c8a9	d7f6d093-b88e-443e-afd6-9c79e48ee641	83a2f46f84f450ff71d24ac20d60a2cdd024a65749f189bb8dd9a92e56942ef2	caf7b917-4bcf-418d-82e4-439e766cb89f	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 12:57:43+00	\N	\N	2026-02-06 12:57:43.535653+00	\N
46ed858c-b3ce-4472-9509-d283b41fe143	8d509f22-5fe5-4765-9496-3a236cae2af1	29c2460c4373086b55d79f7c7481e13352c5cc56b37bb92989f7ff59d5b17541	62725e23-410d-4c65-8cfc-75381562bbd0	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 14:52:50+00	\N	\N	2026-02-06 14:52:50.717064+00	\N
5b732237-109b-4340-bbc0-e07467f01706	8d509f22-5fe5-4765-9496-3a236cae2af1	ce86b534ded8c7f4feb1ab265951101ba9301acc0e57d7c236aeaa4f46c0f6af	5eedcf81-bea7-466b-b6dd-85dc90f5443f	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-13 14:54:47+00	\N	\N	2026-02-06 14:54:47.732072+00	\N
361cff48-0945-4e9a-bc3e-7bb64531d930	8d509f22-5fe5-4765-9496-3a236cae2af1	2444d3326b5299ba097d2bc4af677753d9bcbb5ad76898bd8e382ab435f7e2b9	26bfe141-8d3a-407f-8d01-8ecc6caf03f0	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-14 04:49:12+00	\N	\N	2026-02-07 04:49:12.965574+00	\N
ef97588b-91e2-4586-b1e7-7dd82e476e18	8d509f22-5fe5-4765-9496-3a236cae2af1	d13fe2a07820216faa8f1fa9cb16fb55f1b420d48fa8d492715e4009cc34c193	fa17bd0c-e4f0-4ec9-8688-11ae8d8a4ffc	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-14 05:25:39+00	\N	\N	2026-02-07 05:25:39.214473+00	\N
c73b7656-690c-49ff-ae4b-30851cebbec1	8d509f22-5fe5-4765-9496-3a236cae2af1	ba263d04909e9c7828afbff72af48e0ae900fca16798648e36fdc63ec2125b42	3f3ae17d-e282-4b9b-822d-d9a5d2e12e71	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-14 14:21:53+00	\N	\N	2026-02-07 14:21:53.484749+00	\N
ee35d972-7edd-4f7e-a57a-b7d7c21a9393	8d509f22-5fe5-4765-9496-3a236cae2af1	36e2e2d03952bc24dad1b4a85da3a02d35544dc20737b460ca2d14761876fc75	c94293c6-dac8-49b7-becb-771d58e5aac5	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-14 16:09:16+00	\N	\N	2026-02-07 16:09:16.430657+00	\N
55c0f69f-8bee-4e02-877b-821407c3d9de	8d509f22-5fe5-4765-9496-3a236cae2af1	5e547f444051744836e95eeff9aec3e091f9dfd7f92f410adba796ad35427c14	a27b83b4-d1ad-4493-934a-cf4b2e9f39ff	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-14 17:29:18+00	2026-02-08 02:35:40.460965+00	user_logout	2026-02-07 17:29:18.704903+00	\N
439825e0-1993-488e-8d0f-8b471d86b3f7	8d509f22-5fe5-4765-9496-3a236cae2af1	29082908e20be60d1459ded8fb9301e42d9695deb054f6702b3ec06497118415	8c9f0666-ba24-4048-9b8d-aafca22e0f4a	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-15 02:35:54+00	\N	\N	2026-02-08 02:35:54.768181+00	\N
bc7388bb-8247-4194-84d0-c622c8e79766	8d509f22-5fe5-4765-9496-3a236cae2af1	086b830d18dc3c97ef7ef6d9e52730cac90613ecef7e1a029948de548c8c6f83	0856a0f6-7a47-42d7-b56c-5f0d7a17e33c	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-15 03:21:05+00	\N	\N	2026-02-08 03:21:05.962483+00	\N
5f029d6a-1b5f-4a2f-9b0e-86e6a40672c1	8d509f22-5fe5-4765-9496-3a236cae2af1	f400ff7382051e0bd82cf7f440f0817fd5d81da113ece85a83c5b64a134038b3	f637b1d0-d827-4e02-9dcd-4b7a65415928	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-15 03:35:33+00	\N	\N	2026-02-08 03:35:33.527911+00	\N
e93d65d0-bf87-4714-8072-611396325eaa	8d509f22-5fe5-4765-9496-3a236cae2af1	b49948320a58b2e63a53dcfefb392bf410c8833cc6a875569e4cf623c4b621d1	11fa2434-66d5-4bd1-b17a-cd7a40018b54	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-15 06:53:45+00	\N	\N	2026-02-08 06:53:45.566626+00	\N
2fb9a156-c206-4d52-8951-4338c0bf25ca	8d509f22-5fe5-4765-9496-3a236cae2af1	de7771dbba88ca0ea38d790afc342e9c3ae29ca7daa4315177eb3cfbf3ba7468	7a0a165c-08f3-4b22-8e05-8558e673ecec	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-15 11:49:47+00	\N	\N	2026-02-08 11:49:48.007819+00	\N
c87aa901-fd76-45b8-8815-3674da076ec6	8d509f22-5fe5-4765-9496-3a236cae2af1	a4a9b828c1ee63abadc25b95e581f2243eab2e3949869325f77204289dc31558	9cd539f0-fc39-4e88-a712-9c7d70f82d9b	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-15 12:25:42+00	\N	\N	2026-02-08 12:25:42.350549+00	\N
0035a1cb-a345-46f4-aa93-5498393498be	8d509f22-5fe5-4765-9496-3a236cae2af1	3a56250cc19cbda4234ae1c3638040b1ad695997a83be274ac994ea97950c3b9	a56ef8ba-0ada-4ff2-a022-8dc37ba86d93	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-15 12:28:41+00	\N	\N	2026-02-08 12:28:41.390623+00	\N
a507dc39-88e6-4b9b-9701-b279d812fdf8	8d509f22-5fe5-4765-9496-3a236cae2af1	0660f9563d782b5e7f85c3ba716f3c54f2941b3639f6a11812528ee399ce1c9c	7a59bc09-dddb-4d3d-a3eb-a9de86b6b7af	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-16 05:46:28+00	\N	\N	2026-02-09 05:46:28.635468+00	\N
a14cccb4-30af-44f8-9148-3ebc61d63af4	8d509f22-5fe5-4765-9496-3a236cae2af1	daea2cc41f48a3b2e5b5368173f9b998e7bab3694f83cdf9c4fadce04340ade3	406e0cea-8d87-4024-9cbf-2a6f86254684	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-16 05:48:28+00	\N	\N	2026-02-09 05:48:28.7467+00	\N
fb3d1d41-644b-492f-add6-2f903dfdee84	8d509f22-5fe5-4765-9496-3a236cae2af1	6301441c0733d9dedcbdcf0c592aa8f4c0f32a342132e7ef38d52191d8e1232a	d8c4f62d-9e62-4183-b115-0d561b785abf	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 06:32:52+00	\N	\N	2026-02-09 06:32:52.829535+00	\N
7b298315-8149-4ae2-af7d-c7ab98fcdb12	8d509f22-5fe5-4765-9496-3a236cae2af1	c1a628e5f5f496b5a4a831ea75392fb1cc4a90f45052242bbe7f9e6acbf6fb76	07bce28f-6e93-4279-9981-d4d9fe28196e	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 06:33:55+00	2026-02-09 07:10:12.377571+00	user_logout	2026-02-09 06:33:55.864442+00	\N
4d051925-0300-4c1e-b4f9-cddcdbab82ef	8d509f22-5fe5-4765-9496-3a236cae2af1	e6962e3c9a79f158ffb853e813ecf37830a5ccd230c6d1f9545ed5b9b07ac646	500434a3-816d-43a9-9a3e-f410d1dc53cf	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 07:13:01+00	\N	\N	2026-02-09 07:13:01.248581+00	\N
3795d00f-3103-4bf3-a9ce-71a1312f4abe	8d509f22-5fe5-4765-9496-3a236cae2af1	70d5301ad1b4187a62294d8f3e2a4a5c1ccbf958556a154f3306e7d88b016776	d5b24c92-3ab4-4f25-8332-a846dfd32c4c	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 07:22:00+00	\N	\N	2026-02-09 07:22:00.57378+00	\N
e62d1e1c-9d91-41b2-8b3c-c18c29ec030c	8d509f22-5fe5-4765-9496-3a236cae2af1	0769493e6966e3c5d10868117363d23c9a6becb0915ee77cfe77db3542253d16	66218a7f-6875-46b6-8672-05614c941e2d	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 07:28:38+00	\N	\N	2026-02-09 07:28:38.312937+00	\N
79e4fa14-6360-4c39-9f42-c6e451f4fe1f	8d509f22-5fe5-4765-9496-3a236cae2af1	3496daadff982ee17fe86e9051de843bcac780ad51c1909c38a0c0953dfcb573	8b71a2ca-2f4f-42af-aebe-ccd23ebcfaa7	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 07:50:17+00	2026-02-09 07:50:33.952423+00	user_logout	2026-02-09 07:50:17.042972+00	\N
dc4aa699-8c2b-422b-a91e-ba155a076692	8d509f22-5fe5-4765-9496-3a236cae2af1	74e89838322954074e4924e942a97c62dfad99a246412b0e471b603b504146bf	e9241c17-597b-4b26-b524-d38a301d5d52	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 07:51:58+00	\N	\N	2026-02-09 07:51:58.539247+00	\N
dbe1f607-dd9e-4042-b7a5-c2ca41d5e2c1	8d509f22-5fe5-4765-9496-3a236cae2af1	f98e004ad8022c9a4444da2403ddd27541ffd5c8800c6047213d11583df02def	24856543-254c-4e37-ada3-a9622a10cdda	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 07:59:35+00	\N	\N	2026-02-09 07:59:35.732132+00	\N
495a0b4b-1cca-41d3-9871-e0d58292e419	8d509f22-5fe5-4765-9496-3a236cae2af1	59a22bafa83009437c7003e33b2ca1545d6bfad605234a952203b9d6ed805018	457e135a-3d72-4bba-8e98-c372112665b7	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-16 08:30:45+00	\N	\N	2026-02-09 08:30:45.903561+00	\N
802ff63a-2c30-4318-bec3-2a8e3997523b	8d509f22-5fe5-4765-9496-3a236cae2af1	97922f017034443e61b00bc56bfa60b540614ce89fd4da5df725c0037217a41b	c7b00d7d-d44c-4146-a690-00a0f96e35a0	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 09:45:44+00	\N	\N	2026-02-09 09:45:44.986017+00	\N
0b2e0127-ae15-4e4f-b37f-1c3061bad95d	8d509f22-5fe5-4765-9496-3a236cae2af1	22d4ec123e49f39feb7981af43fa95bb23262f3ba9602ad4106a1a96367667b9	cdeb5d8c-9f52-4def-94b0-665577cb1be6	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 12:08:44+00	\N	\N	2026-02-09 12:08:44.8849+00	\N
fcc73297-00ab-42fe-aa54-dd0117150394	8d509f22-5fe5-4765-9496-3a236cae2af1	ee87905eafbaf77e662887235755c04098f09d9e91aab12ffb1bf35143915dfc	f7232ae3-d5f6-45e8-8097-7084fbde2504	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 16:53:56+00	\N	\N	2026-02-09 16:53:56.95476+00	\N
b6474147-4d44-42df-97f9-e14d0fcd832f	8d509f22-5fe5-4765-9496-3a236cae2af1	8528a4ae9a5e8239d4dcb8edc6b57e0be8dea4092b662120de135ed95ec29a42	fe8af2f6-0086-41fd-8af7-08d3af48dd97	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 17:08:50+00	\N	\N	2026-02-09 17:08:50.029451+00	\N
4e81f400-112a-45b3-acc3-d8a8dee616c8	8d509f22-5fe5-4765-9496-3a236cae2af1	c04f490306a321f39bf8cc002b21da38658ef1fa8506dfb6d3f5c0f8e1d2dbdb	4503e229-710f-4502-8c36-bdf3dfdbf7b5	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 17:46:17+00	\N	\N	2026-02-09 17:46:17.134097+00	\N
56d50a03-7e83-4fe1-bdf2-193d724f39f7	8d509f22-5fe5-4765-9496-3a236cae2af1	069d31bfa7fac0696aed208b0e2ffeaeb6d374bb0f1349ea1a978f87339c62bd	fa8eb946-6ad4-412d-8d6f-5e35a708ce1f	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 18:09:16+00	\N	\N	2026-02-09 18:09:16.708+00	\N
8160e2fb-5ee3-4245-8a8b-1892aed2c104	8d509f22-5fe5-4765-9496-3a236cae2af1	aa1404717d62c073b168e246a467bb668566bc4524f791902ed19b0b93b5c6d0	fa86c3d3-850c-418a-97c1-7de952de4da8	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 18:23:33+00	\N	\N	2026-02-09 18:23:33.361923+00	\N
3ea4737e-0a40-4525-b7f1-1c386df34361	8d509f22-5fe5-4765-9496-3a236cae2af1	afa0eeadd325b90efa78520b911323faa90212a54e8d750ba0baf3af8bbcc168	91ff34b0-0e33-4b61-aa8f-3ed64425a0a3	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-10 18:27:05+00	\N	\N	2026-02-09 18:27:05.181023+00	\N
b6a26c01-8981-4b71-905e-96bb71a892fd	8d509f22-5fe5-4765-9496-3a236cae2af1	89d4df3886e7df2ee91f8e7a3382b9ba4d2402a3ba7e5e65458fef7408de75b6	422ba538-bfab-4dc9-b762-6317f5faa4e0	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 08:36:08+00	\N	\N	2026-02-10 08:36:08.606293+00	\N
493ae6d5-cefd-497b-b7be-dc8c2648fb7f	8d509f22-5fe5-4765-9496-3a236cae2af1	7716f800e97a51f971741f967ab248dc8322071ae575b3076cb4f622f0681634	74f4fc6b-7baa-42e2-9432-2fed450a60fe	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 09:00:32+00	\N	\N	2026-02-10 09:00:33.002917+00	\N
8740ff2f-52af-4439-8de7-b5a60106eaba	8d509f22-5fe5-4765-9496-3a236cae2af1	1674eec4f5197842480ddb0fc9af3f29e9ca56ae59471a74feb77a137a74e10a	01dd90ec-19f2-4412-ac03-af771e781736	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 09:16:08+00	\N	\N	2026-02-10 09:16:08.993152+00	\N
b77e1dd4-2eee-4efc-896c-ddfcf526b6f3	8d509f22-5fe5-4765-9496-3a236cae2af1	da3ca1bad98f44f244eeb1b5fe620f6dfc3b11f9d8fc2ee4b74f5c2f0a42c68e	d5042ee6-23c6-4626-a823-a22e3e2b2403	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 09:35:16+00	\N	\N	2026-02-10 09:35:16.904549+00	\N
20148ea6-2303-4c69-b6d8-2130b6fcf15d	8d509f22-5fe5-4765-9496-3a236cae2af1	cf18c0b5078097091bba4170d8086be28ce41a7bd50776f8306c3cabc8c5f729	035ebac6-e206-4972-9659-f4d016f8abf8	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 09:42:36+00	\N	\N	2026-02-10 09:42:36.809119+00	\N
7faef90d-7f2a-420c-ac57-7543c1fca6e8	8d509f22-5fe5-4765-9496-3a236cae2af1	550ab74b38731b8f5c1b3834312683231d83c1c45a6371e69cf5499ca65f87ea	1a7519af-7810-4d0e-8950-64f766a7ed73	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 13:06:28+00	\N	\N	2026-02-10 13:06:28.953892+00	\N
a6ce4552-9302-4de9-aea4-f02f5f748a87	8d509f22-5fe5-4765-9496-3a236cae2af1	aed730bede2b4c3cdd190790cb949659f647c0602b419a10ff7e38fc6295d3e3	d8760747-d678-4683-bfac-22b269f4bc8a	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-17 13:58:41+00	\N	\N	2026-02-10 13:58:41.730353+00	\N
f9856502-54d5-4a30-a16d-696fa46347f6	8d509f22-5fe5-4765-9496-3a236cae2af1	b10d4fd7639a759b27634fec1b7bbe7b09f288f7ae972c7ab97af8df5ef43cfc	48268d8c-0dcb-4255-b48e-e28d3d67e5ba	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.1	2026-02-17 15:10:08+00	\N	\N	2026-02-10 15:10:08.433644+00	\N
ea9c118a-381f-47e5-9a33-9d463b532122	8d509f22-5fe5-4765-9496-3a236cae2af1	75746e59ef79f4140809fc30bf82e09bcfcacd6590881c28d1b0358633e33c9e	93b65551-1d43-47d3-a31b-59b046c63536	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 15:32:10+00	2026-02-10 15:53:26.030479+00	user_logout	2026-02-10 15:32:10.969172+00	\N
5f45e960-81ab-4ec8-a42f-30ea6c26e03a	661678e8-12df-44bc-b50a-d69538eb9590	ba4d34a41bdc98592aba52bfb2f5903b37feddbf3a3c9c7a63c9cfad22589e2e	64c4a01e-8e63-4dba-824d-525a99472c7e	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 15:54:05+00	2026-02-10 15:54:28.966718+00	user_logout	2026-02-10 15:54:05.6655+00	\N
1185b54a-b97e-46bd-b5ea-ecab7af26c5f	661678e8-12df-44bc-b50a-d69538eb9590	2460840fd7aecc186d25f469ffc83f0062c6cb83a1b1b1d9b674d3364778bb54	5608e1d3-ac5b-453f-b897-12d34aa72f95	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 15:56:17+00	\N	\N	2026-02-10 15:56:17.225114+00	\N
96bbb4dd-1670-4188-a4df-85a6a7a6c61c	661678e8-12df-44bc-b50a-d69538eb9590	17d08765da4d8339cd39ed496f3c36a2c5969f9947fb13558f5af04d899cae2c	183b68e2-158c-44b5-9381-1bd3c61ad6e8	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-17 16:00:30+00	\N	\N	2026-02-10 16:00:30.798744+00	\N
e6ad53c6-4f09-45f3-9406-73928be08fb3	8d509f22-5fe5-4765-9496-3a236cae2af1	ed1dcbf75d634ac0538b4d83d25865b6e225b008a03087192f5be889b9eb5cc0	eddde68b-8dcb-44ff-aca9-e522e69a7403	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 16:03:42+00	2026-02-10 16:14:50.732347+00	user_logout	2026-02-10 16:03:42.368457+00	\N
f9a32c29-55e3-4cfc-892e-c9aaeaf8854c	8d509f22-5fe5-4765-9496-3a236cae2af1	bd91b0dd7b07c715be8cdcf521e6a2957c4621a62c9eb2da33badef1c17cb346	fd514612-cd94-4ea9-86f1-80f7862ed46d	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 16:15:21+00	2026-02-10 16:16:19.232159+00	user_logout	2026-02-10 16:15:21.87683+00	\N
ed1c2819-bb23-4c03-b74a-434bb48430b9	661678e8-12df-44bc-b50a-d69538eb9590	0d19ffffd59c20fa9a0bb278fb8d8322508f6b49614e44a0ee04b692c52f2aaf	b9c5d8ec-477a-42c9-9474-b53553f265f2	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 16:16:54+00	2026-02-10 16:18:33.343551+00	user_logout	2026-02-10 16:16:54.153776+00	\N
ac0afd4d-84fc-4c4c-a20f-9f4898325d82	661678e8-12df-44bc-b50a-d69538eb9590	0e15ee930553eb0969d2a8b67e218a23393cb70cb6e4768670547b62bf5a34f5	539e32d3-3279-4059-a81d-c365be709fba	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 16:19:21+00	2026-02-10 16:45:09.46257+00	user_logout	2026-02-10 16:19:21.970638+00	\N
11131c7f-05dc-4243-97ce-a69d30e5a2b0	8d509f22-5fe5-4765-9496-3a236cae2af1	a9866673cbc9c98aee3b94de4d869e8f489a7ee3d9f1198e5ba280042903148d	bdf2212a-6e16-4b61-9b37-f3faf31aebae	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-11 16:52:17+00	\N	\N	2026-02-10 16:52:17.109842+00	\N
47e2452d-7981-42b9-b6d3-c29e49149ee9	e79e0010-f4ea-42cb-9829-c2375e5fa034	b7496591b304df608faedc356b1bea6f02ae688d9bfdbe7733e3224fcd0be4f5	84e09ecc-f9bc-49a4-aa4a-eede4ac6387e	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-17 16:49:10+00	2026-02-11 05:46:02.706596+00	user_logout	2026-02-10 16:49:10.663464+00	\N
cff5819b-aa6d-419b-a041-67bbca815af6	661678e8-12df-44bc-b50a-d69538eb9590	2593f7813a5a34dcc822970677736e3585b2ab4f09828e296da483f68340471a	6bb76acf-0ed4-495d-8068-9fc741deaf06	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-12 05:46:27+00	2026-02-11 05:49:33.69146+00	user_logout	2026-02-11 05:46:27.970145+00	\N
d6861388-1431-48c2-bc1c-50ef30cedfae	661678e8-12df-44bc-b50a-d69538eb9590	9ab7df3833c573e842e28ee0dd63d64a628828403fddedd801c805df4680ff55	acf57e82-0ec3-4ab1-b354-9c2a46db1b1c	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-12 05:49:53+00	\N	\N	2026-02-11 05:49:53.973917+00	\N
d26ee402-4d3c-4ced-8319-388f7a9f0358	8d509f22-5fe5-4765-9496-3a236cae2af1	a750040d0e388fd69eabef358cb3f7942e3dd96895968fa5af4b7cc37669a491	0cb17d64-a991-4dd8-80ea-c1189be0a6c6	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-12 06:18:26+00	\N	\N	2026-02-11 06:18:26.683754+00	\N
d61d8451-be46-4c95-9711-a7c0edcd24f6	8d509f22-5fe5-4765-9496-3a236cae2af1	84967e14002a8b6bb2d28801d39e430a95ac730ab75692905eab221bca2de7d2	baba4af3-6593-4089-86d6-4cc70d8a7eb6	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-12 06:20:24+00	2026-02-11 06:24:28.603956+00	user_logout	2026-02-11 06:20:24.55492+00	\N
8f9f16d1-4fe4-48ce-a283-1d8ba8595c84	8d509f22-5fe5-4765-9496-3a236cae2af1	e567d9f93da013a7e105b1e9518a193bbd67a3d257329f57665de7f95a373619	0e838e98-f518-4396-a4bb-acd87a919897	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-12 06:32:59+00	\N	\N	2026-02-11 06:32:59.159646+00	\N
e2b68965-7e1f-411a-9eab-ab2e9aea14c7	8d509f22-5fe5-4765-9496-3a236cae2af1	f7ca6ce0a6fcff389832d802cfbdadef0f10eda891ac92bf0d987a3498fb8350	1b6bfb7b-df36-4a85-98ab-e133551dd911	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 06:50:47+00	\N	\N	2026-02-11 06:50:47.773944+00	\N
5d5cabca-4a9f-41d5-a9c1-166c362409b3	8d509f22-5fe5-4765-9496-3a236cae2af1	1145c523d079b1142f27ededbd9f2a02ed3493be200c2e80839aed945f360c69	e315626d-b235-4179-a129-745a168d7717	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-05-12 07:19:09+00	2026-02-11 07:45:23.77282+00	user_logout	2026-02-11 07:19:09.505966+00	\N
f98244ae-b09e-4299-a845-9a3280cfea2f	8d509f22-5fe5-4765-9496-3a236cae2af1	15dad0e2a15bfb7cdc5b3b2c356c376092ce9145f91113c3f3a8565d17cf1e5d	f0a7c0c6-f947-457b-bf06-15e0af80d155	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 07:45:56+00	\N	\N	2026-02-11 07:45:56.783406+00	\N
9f5b060f-1053-44b1-879a-d49e214d5eef	8d509f22-5fe5-4765-9496-3a236cae2af1	7bae84ad5c5a9512dc52f72d5d0d4f23422d974c05d82d5db84ff4d279aa1470	056f666b-3f8c-4853-84ff-101b4f469ef3	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 08:25:56+00	2026-02-11 08:42:11.159963+00	user_logout	2026-02-11 08:25:56.299172+00	\N
e933c675-85b7-4105-b22b-1a0144ccfd1b	8d509f22-5fe5-4765-9496-3a236cae2af1	8aed5df071ea7e2204c4186b89d2f046ca4018cfd595d5e20a2191390fb4d297	5833e37e-5db4-4483-89bd-eb76f9e00a54	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 08:43:08+00	\N	\N	2026-02-11 08:43:08.2233+00	\N
88eb9578-1aad-478c-8eac-0bdebfcb8909	8d509f22-5fe5-4765-9496-3a236cae2af1	ff2ba98d7a2d865775f6e246f1fb04640f44b794f095bb789275b994c7413c2b	82c3605a-b348-4d7b-8bd8-004fd6b52c58	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 09:29:17+00	\N	\N	2026-02-11 09:29:17.67952+00	\N
326a6a5a-64bb-4376-adf1-34c05191a114	8d509f22-5fe5-4765-9496-3a236cae2af1	8f303be80a8912bc6a2fd5aeb2d7368d3fe1889e0ad11e1b8850ad4420dec442	f7a7386c-34f7-4683-b901-f48c629ce47e	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 09:32:24+00	\N	\N	2026-02-11 09:32:24.274238+00	\N
263520f2-c4dc-4322-a3c7-528d22a301c3	8d509f22-5fe5-4765-9496-3a236cae2af1	2fc1e295b5e8d9b31ea1734cc790ce4bbfeded9db8a65ae68e6cdb595ff5f6e4	625e3c3f-00ab-4629-b24e-a74907601bd9	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 11:16:54+00	2026-02-11 11:17:27.656556+00	user_logout	2026-02-11 11:16:54.491694+00	\N
7e7f453b-bd4c-4e8d-b9c2-638d02eeb5b2	8d509f22-5fe5-4765-9496-3a236cae2af1	fb1ce79750603b3ca94da542a1a103b585a67d307c71185ffad6cf5a606f27b7	49946a84-abab-4994-8c4d-2bc6af03101d	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 11:17:48+00	\N	\N	2026-02-11 11:17:48.901222+00	\N
172f615b-f7f3-4274-9dd9-54f4dfd37ab2	8d509f22-5fe5-4765-9496-3a236cae2af1	3ed47aeea973bd452b0757ab4d212a4179ed1fc94a279ec4985fcd119c7bff9e	11ef0132-9699-4e65-a372-3abca24b6a6e	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 11:30:38+00	\N	\N	2026-02-11 11:30:38.739267+00	\N
d9cc0128-7d98-4903-b8ce-7b151da5f202	8d509f22-5fe5-4765-9496-3a236cae2af1	3066be5c5ec9decf11cc982a7049b40de5af3777f4b73ef7608131dc3ae1f2b7	e435ff0c-bec2-4977-90ea-05d89683854b	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 11:41:58+00	2026-02-11 13:36:56.696983+00	user_logout	2026-02-11 11:41:58.198646+00	\N
ab2249e9-5fe1-4eed-8a66-22e886a7f75d	8d509f22-5fe5-4765-9496-3a236cae2af1	1df3a6542f066ee482b7719ccacf9f93afe33b426ae599a62bfda6780bdf9444	6b6090f8-6a1d-42be-8798-7adaa3b514c5	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 13:37:51+00	\N	\N	2026-02-11 13:37:51.472227+00	\N
f87123b6-98c0-4b09-bf66-2c688889ec21	8d509f22-5fe5-4765-9496-3a236cae2af1	4cd26f4bc4ab8b21e6d663a84b32f6246316fc5ff58d75ac7e1d2048dc7b79ec	662212aa-1396-49e6-a1b8-f0281426e1e6	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 15:46:13+00	2026-02-11 16:31:33.81499+00	user_logout	2026-02-11 15:46:13.4197+00	\N
deeec25f-4002-4a57-9737-0721608013c4	8d509f22-5fe5-4765-9496-3a236cae2af1	17648011e650bf0e9f0414dd647f8ae8e2eace45603b9d3bdb8fbc2af5e0aba2	040ade64-6d2e-4b71-b668-874fddda44ff	\N	\N	\N	\N	\N	192.168.65.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	2026-02-18 16:31:57+00	\N	\N	2026-02-11 16:31:57.696315+00	\N
\.


--
-- Data for Name: role_permissions; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.role_permissions (id, role_id, permission_id, conditions) FROM stdin;
83725c3f-63d8-4d8c-a3fc-bb745f8fb586	774f0485-d473-4016-92c3-dbb38634c3d3	b3baefb1-399f-4ff7-874f-b131014aa9f1	\N
774bcea0-9782-46cc-8477-038d1f04123f	d7792db7-091b-4edd-bac3-b14d6ab7f859	17d6fdd0-7332-421f-805d-b5f204f8bd7e	\N
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.roles (id, organization_id, name, code, description, is_system, is_default, hierarchy_level, is_active, extra_data, created_at, updated_at) FROM stdin;
38b9cb00-a985-4b0e-9bba-871c44e2d2d7	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	System Administrator	system_admin	Full system access	t	f	100	t	\N	2026-01-26 10:00:59.181253+00	2026-01-26 10:00:59.181253+00
2089b406-42cd-44e1-9895-5bd5904ece04	9fe2bee3-cc0a-45e9-a1c5-fe1aaaf8ff6d	Organization Owner	owner	User who created the organization; has full access in this org.	f	f	100	t	{}	2026-02-05 11:00:14.346207+00	2026-02-05 11:00:14.346209+00
bde0029d-463d-4e35-8b8a-bc1b0e96ef96	9a9b7483-4327-46f6-852b-70c5faab67d4	Organization Owner	owner	User who created the organization; has full access in this org.	f	f	100	t	{}	2026-02-05 16:45:51.361985+00	2026-02-05 16:45:51.361988+00
774f0485-d473-4016-92c3-dbb38634c3d3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Organization Owner	owner	Full access to all resources in the organization	f	f	50	t	\N	2026-01-26 10:00:59.181253+00	2026-01-26 10:00:59.181253+00
e0fd94ad-1415-40f7-8f0b-4e570ef5d151	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Inventory Reder	inventory_reder		f	f	0	t	{}	2026-02-08 03:34:40.204848+00	2026-02-08 03:34:40.20485+00
84c0758b-d35e-4d9a-937c-9aa86b51b1e1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Customer Admin	customer_admin	only access to customers' data, no delete 	f	f	0	t	{}	2026-02-08 07:02:01.169333+00	2026-02-08 07:02:01.169335+00
943cafa3-d5b1-467e-9874-1b2a46db59af	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Sales Manager 	sales_manager_		f	f	0	t	{}	2026-02-08 11:53:06.07967+00	2026-02-08 11:53:06.079682+00
d3546950-65d4-47fc-b269-464efb08a220	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Sales  Manger and Inventory Manager 	sales_manger_and_inventory_manager_		f	f	0	t	{}	2026-02-09 12:12:22.976492+00	2026-02-09 12:12:22.976494+00
d7792db7-091b-4edd-bac3-b14d6ab7f859	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	User Admin	user	Standard user access	t	t	10	t	\N	2026-01-26 10:00:59.181253+00	2026-01-26 10:00:59.181253+00
\.


--
-- Data for Name: user_organization_roles; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.user_organization_roles (id, user_id, organization_id, role_id, is_primary, is_active, status, invited_by_id, invited_at, joined_at, extra_data, created_at, updated_at) FROM stdin;
0d525f4b-25e0-4f63-978b-77be14803006	8d509f22-5fe5-4765-9496-3a236cae2af1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	774f0485-d473-4016-92c3-dbb38634c3d3	t	t	active	\N	\N	\N	\N	2026-02-06 14:48:26.675775+00	2026-02-06 14:48:26.675775+00
41921d24-404e-4410-b6cd-3e41346ff354	661678e8-12df-44bc-b50a-d69538eb9590	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d7792db7-091b-4edd-bac3-b14d6ab7f859	\N	t	active	\N	\N	\N	\N	2026-02-06 14:48:26.675775+00	\N
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.users (id, email, password_hash, first_name, last_name, display_name, phone, avatar_url, user_type, status, is_active, email_verified, email_verified_at, mfa_enabled, mfa_secret, mfa_backup_codes, last_login_at, last_login_ip, failed_login_attempts, locked_until, preferences, timezone, language, extra_data, deleted_at, created_at, updated_at) FROM stdin;
afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	admin@example.com	$2b$12$ExR8Mv.K4V5K.T/Yv/T.m.Fw1F1F1F1F1F1F1F1F1F1F1F1F1F1F1F	System	Administrator	System Administrator	\N	\N	system_admin	active	t	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	2026-01-26 10:00:59.363341+00	2026-01-26 10:00:59.363341+00
17c129d5-685b-4196-9ed1-c412f648ce88	john.doe@example.com	$2b$12$KkR8Mv.K4V5K.T/Yv/T.m.Fw1F1F1F1F1F1F1F1F1F1F1F1F1F1F1F	John	Doe	John Doe	\N	\N	user	active	t	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	2026-01-26 10:00:59.363341+00	2026-01-26 10:00:59.363341+00
5a54bc15-5af0-4577-8188-77f0adb2b989	jane.smith@example.com	$2b$12$KkR8Mv.K4V5K.T/Yv/T.m.Fw1F1F1F1F1F1F1F1F1F1F1F1F1F1F1F	Jane	Smith	Jane Smith	\N	\N	user	active	t	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	2026-01-26 10:00:59.363341+00	2026-01-26 10:00:59.363341+00
23877693-a1d6-4cb2-9649-27f30cf98c2a	dev1@gmail.com	$2b$12$8WG08FfMnbJItEtaATNrruFWzH/rCwgbxM53SETL80TeRD.DL1fbq	dev	negi	dev negi	8811452879	\N	user	pending	t	f	\N	f	\N	\N	2026-02-06 07:06:12.2647+00	192.168.65.1	0	\N	{}	UTC	en	{}	\N	2026-02-05 08:03:17.400099+00	2026-02-06 07:06:12.29444+00
956138ed-1e93-491c-b204-2824c88df765	testuser_e4905268-c107-41fd-ad82-f1056212f326@example.com	$2b$12$KZV/yt5JOkIfwoG6iqMejeDMoi3KseUltDy2Pa9/oqeO8Dzy2Hg7O	Test	User	Test User	\N	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-01-28 08:13:02.02322+00	2026-01-28 08:13:02.023241+00
cc7f225b-f30e-4559-a0b9-7bfba2062a82	testuser_7c106163-81cc-42fc-a63a-9ea0498c78fd@example.com	$2b$12$hQ5bHKXbZvam0nzfe6Tt8ehPsd64YCnrmVwKVWsJzuqIMtoVnU0Z.	Test	User	Test User	\N	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-01-28 08:13:13.813206+00	2026-01-28 08:13:13.813214+00
72c698bf-3d7d-4f9b-812b-66fb3109dbc1	testuser_e2296b13-5015-4cac-80b2-5837907ce917@example.com	$2b$12$niwObHdaW/WMMjkXCbLfkeozw7c.UHszxCXuCkuwzlHijjzW.ak/O	Test	User	Test User	\N	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-01-28 08:13:23.670663+00	2026-01-28 08:13:23.670667+00
386f1db2-caf1-40aa-aaec-bcf9a531356a	negi.yaten@gmail.com	$2b$12$B1kmjv2THI78DsItPZuiEuBX8BylSrGEvh4gvau0DZtRFewDH9hcy	Yaten	Negi	Yaten Negi	9008750492	\N	user	active	t	t	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-01-27 05:31:43.952107+00	2026-01-27 05:31:43.952113+00
7f8a4e1a-db39-4615-8a21-2e93f0a80875	test@example.com	$2b$12$52j5SeAtkDTx545WIxac..Jsv7CMc9St1d5v9bzmhlX6qI8HLu6ea	Test	User	Test User	9008750493	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-01-30 08:01:06.005369+00	2026-01-30 08:01:06.005388+00
c086f967-cac9-4ebe-88e5-aa9b6c43e22c	dev123@gmail.com	$2b$12$lRbbESl739UFb30ceJ.Mf.deOgjtGkf4/.T0cH09QThypg0PfNW0y	Dev123	Negi	Dev123 Negi	6663642880	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-02-05 09:33:13.368584+00	2026-02-05 09:33:13.368609+00
e6b6d300-77f3-4812-9c73-eef8280a2466	dev978@gmail.com	$2b$12$LEc//97hBog/15KxwMAjJOV0eDN9B6R2/zT.95cGUwOj6nzLyk1H6	Dev12kk	Negi	Dev12kk Negi	2378758180	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-02-05 10:15:26.990305+00	2026-02-05 10:15:26.990309+00
dd017f5e-5532-4d25-a472-087ac3828c9c	jhon1@gmail.com	$2b$12$hBOMNdo0SfPyX2ZUnGmvU.HwBPRkeINos7FvYHh5/XGrmX.fbsA3y	John	Smith	John Smith	1711452879	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-02-05 10:46:15.604947+00	2026-02-05 10:46:15.604969+00
129a038c-888a-47f6-ac80-8b0c35646afd	devnegikec1@gmail.com	$2b$12$ZHiAGlS2zbb16y3jdtGZYupZWnmZD9.SbY0T2Y1CP3z4ynYQuTRui	Devendra	Negi	Devendra Negi	8711452879	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-01-31 18:07:33.205473+00	2026-01-31 18:07:33.205476+00
8f993936-5cc5-4181-8046-9a7faf046e57	devnegikec2@gmail.com	$2b$12$9P7cQFQ9kmdsMmVo6EijJe5CB35QnO4Wd9O5UNU0KheRDcA.FuscS	test2	Negi	test2 Negi	8111452879	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-01-31 20:53:12.925779+00	2026-01-31 20:53:12.925793+00
4f676bac-7a97-4a6a-8dbe-2f16a03e0c30	devnegikec11@gmail.com	$2b$12$MTK07UdhDZlvKH1czJ4StO38H4HMF28OgmaghwlMPe2/9RRsMK3sG	TEst 1	Negi3	TEst 1 Negi3	9711452889	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-01-31 21:00:37.346168+00	2026-01-31 21:00:37.34617+00
fd0aaaac-f93c-4b69-9cfc-f33d7e650545	devnegikec34@gmail.com	$2b$12$0lngt5JDICL77klwOwYC2.dw4Bw.4ySPs.Kh2o.YOdCWSTMxFcLHq	Test	Negi	Test Negi	9711452811	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{"theme": "light", "onboarding_step": 2}	Asia/Kolkata	en	{"bio": "hjhjkhkh", "job_title": "UI Architect", "department": "Human Resources"}	\N	2026-02-01 10:54:20.412561+00	2026-02-01 11:31:36.71441+00
421a11a3-d224-47fc-954e-af332b5bbc65	devnegikecdfadfa@gmail.com	$2b$12$IOh2xHSQjPrKdhtFn.Y6duVUdc4bCM6kbkAUoS2Qg20SiFGo5OOS6	testet	Negi	testet Negi	09711452879	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-02-01 16:45:48.310283+00	2026-02-01 16:45:48.310285+00
661678e8-12df-44bc-b50a-d69538eb9590	dev11@gmail.com	$2b$12$LZRicPvwnf8Hl0lz.ms.n.uqD/H8UVhUHxq61VFavRgiz3Boz/iBC	Devaa11	Negi	Devaa11 Negi	9911452879	\N	user	pending	t	f	\N	f	\N	\N	2026-02-11 05:49:53.957243+00	192.168.65.1	0	\N	{}	UTC	en	{}	\N	2026-02-05 08:46:10.848128+00	2026-02-11 05:49:53.959719+00
d7f6d093-b88e-443e-afd6-9c79e48ee641	dev21@gmail.com	$2b$12$vddigXLaBzyMnFbllHZoL.jnnLFVXEoAoEoFpUkvXqS8hLYjDvPH6	Dev	Negi	Dev Negi	7773642880	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-02-06 12:57:43.466971+00	2026-02-06 12:57:43.466974+00
8d509f22-5fe5-4765-9496-3a236cae2af1	devendera.negi@gmail.com	$2b$12$8WG08FfMnbJItEtaATNrruFWzH/rCwgbxM53SETL80TeRD.DL1fbq	Devendera	Negi	Devendera Negi	9008750492	\N	user	active	t	t	\N	f	\N	\N	2026-02-11 16:31:57.659034+00	192.168.65.1	0	\N	{}	UTC	en	{}	\N	2026-01-26 16:01:22.18562+00	2026-02-11 16:31:57.666304+00
de75c704-b47e-4598-a546-3795650cc67b	devnegikec@gmail.com	$2b$12$8WG08FfMnbJItEtaATNrruFWzH/rCwgbxM53SETL80TeRD.DL1fbq	Devendra	Negi	Devendra Negi	09711452800	\N	user	active	t	f	\N	f	\N	\N	2026-01-30 17:19:47.471501+00	192.168.65.1	0	\N	{}	UTC	en	{}	\N	2026-01-30 13:43:44.906348+00	2026-01-30 17:19:47.478362+00
e79e0010-f4ea-42cb-9829-c2375e5fa034	johnD@gmail.com	$2b$12$ohg7CNuf72wFB3IYmMX7IeXzrmI0JMO9OK6RuKlSfAE66TKd2N1..	John	Do	John Do	8979786574	\N	user	pending	t	f	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-02-10 16:49:10.560134+00	2026-02-10 16:49:10.560146+00
\.


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: email_verifications email_verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.email_verifications
    ADD CONSTRAINT email_verifications_pkey PRIMARY KEY (id);


--
-- Name: invitations invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: password_resets password_resets_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: role_permissions role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: invitations uq_invitations_token_hash; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT uq_invitations_token_hash UNIQUE (token_hash);


--
-- Name: user_organization_roles user_organization_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.user_organization_roles
    ADD CONSTRAINT user_organization_roles_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_invitations_email; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_invitations_email ON public.invitations USING btree (email);


--
-- Name: idx_invitations_expires_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_invitations_expires_at ON public.invitations USING btree (expires_at);


--
-- Name: idx_invitations_org_created; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_invitations_org_created ON public.invitations USING btree (organization_id, created_at DESC);


--
-- Name: idx_invitations_org_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_invitations_org_status ON public.invitations USING btree (organization_id, status);


--
-- Name: idx_invitations_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_invitations_organization_id ON public.invitations USING btree (organization_id);


--
-- Name: idx_invitations_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_invitations_status ON public.invitations USING btree (status);


--
-- Name: ix_email_verifications_token_hash; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX ix_email_verifications_token_hash ON public.email_verifications USING btree (token_hash);


--
-- Name: ix_organizations_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_organizations_id ON public.organizations USING btree (id);


--
-- Name: ix_organizations_slug; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX ix_organizations_slug ON public.organizations USING btree (slug);


--
-- Name: ix_password_resets_expires_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_password_resets_expires_at ON public.password_resets USING btree (expires_at);


--
-- Name: ix_password_resets_token_hash; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX ix_password_resets_token_hash ON public.password_resets USING btree (token_hash);


--
-- Name: ix_password_resets_user_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_password_resets_user_id ON public.password_resets USING btree (user_id);


--
-- Name: ix_permissions_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX ix_permissions_code ON public.permissions USING btree (code);


--
-- Name: ix_permissions_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_permissions_id ON public.permissions USING btree (id);


--
-- Name: ix_refresh_tokens_expires_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_refresh_tokens_expires_at ON public.refresh_tokens USING btree (expires_at);


--
-- Name: ix_refresh_tokens_token_family; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_refresh_tokens_token_family ON public.refresh_tokens USING btree (token_family);


--
-- Name: ix_refresh_tokens_token_hash; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX ix_refresh_tokens_token_hash ON public.refresh_tokens USING btree (token_hash);


--
-- Name: ix_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_refresh_tokens_user_id ON public.refresh_tokens USING btree (user_id);


--
-- Name: ix_role_permissions_permission_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_role_permissions_permission_id ON public.role_permissions USING btree (permission_id);


--
-- Name: ix_role_permissions_role_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_role_permissions_role_id ON public.role_permissions USING btree (role_id);


--
-- Name: ix_roles_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_roles_code ON public.roles USING btree (code);


--
-- Name: ix_roles_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_roles_id ON public.roles USING btree (id);


--
-- Name: ix_roles_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_roles_organization_id ON public.roles USING btree (organization_id);


--
-- Name: ix_user_organization_roles_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_user_organization_roles_organization_id ON public.user_organization_roles USING btree (organization_id);


--
-- Name: ix_user_organization_roles_role_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_user_organization_roles_role_id ON public.user_organization_roles USING btree (role_id);


--
-- Name: ix_user_organization_roles_user_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_user_organization_roles_user_id ON public.user_organization_roles USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: email_verifications email_verifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.email_verifications
    ADD CONSTRAINT email_verifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: invitations invitations_accepted_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_accepted_user_id_fkey FOREIGN KEY (accepted_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: invitations invitations_invited_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_invited_by_id_fkey FOREIGN KEY (invited_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: invitations invitations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: invitations invitations_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE SET NULL;


--
-- Name: password_resets password_resets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: refresh_tokens refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: role_permissions role_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;


--
-- Name: role_permissions role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: roles roles_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: user_organization_roles user_organization_roles_invited_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.user_organization_roles
    ADD CONSTRAINT user_organization_roles_invited_by_id_fkey FOREIGN KEY (invited_by_id) REFERENCES public.users(id);


--
-- Name: user_organization_roles user_organization_roles_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.user_organization_roles
    ADD CONSTRAINT user_organization_roles_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: user_organization_roles user_organization_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.user_organization_roles
    ADD CONSTRAINT user_organization_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: user_organization_roles user_organization_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.user_organization_roles
    ADD CONSTRAINT user_organization_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict ye6BEdoJGJg7wjCoUai0tR131YR58aqqjmvFTVuB7DQvnqlueIGwuXWkJYDzaMQ
