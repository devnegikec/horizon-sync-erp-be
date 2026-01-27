--
-- PostgreSQL database dump
--

\restrict I5Fgcz4iU3PkGSxIRajoUuEFJIGV52riB4uNZuzYua23yStqUaJB6JG3rh78NUv

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
    'invite'
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
    'all'
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
f1ba16f1-0730-47bd-b933-6ed48e624b89	8d509f22-5fe5-4765-9496-3a236cae2af1	db1263fbdba11ad4aff8506a58c03ee9ebb5900ac0ce544464c6b77e2bb3c31a	2026-01-27 11:09:01.639837+00	\N	192.168.65.1	PostmanRuntime/7.51.0	2026-01-27 10:09:01.643915+00
\.


--
-- Data for Name: permissions; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.permissions (id, code, name, description, resource, action, module, category, is_active, extra_data, created_at, updated_at) FROM stdin;
676c8e81-b5c4-46c2-b8c4-b1f25dc78656	user.create	Create User	\N	user	create	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
0a3a14a9-1745-47ec-a83a-53f039e991bd	user.read	Read User	\N	user	read	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
f22fb138-7a26-4759-9f14-ebc38a1c1b56	user.update	Update User	\N	user	update	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
e1407dfb-e388-40d3-82d0-c03f00110b36	user.delete	Delete User	\N	user	delete	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
17d6fdd0-7332-421f-805d-b5f204f8bd7e	user.manage	Manage Users	\N	user	manage	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
8c518ff6-2206-4b35-b0b8-1b8f47ac13fd	org.create	Create Org	\N	organization	create	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
a7392ca4-f836-427c-af5d-0782dead2d20	org.read	Read Org	\N	organization	read	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
e135311e-4d1a-4964-be8a-c2f280c7537d	org.update	Update Org	\N	organization	update	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
9e90b390-dfef-4c29-8a66-d031b44c54e9	org.delete	Delete Org	\N	organization	delete	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
34d61530-7b12-474d-89a7-128ed062798f	org.manage	Manage Orgs	\N	organization	manage	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
4e5b2e79-af28-4936-aaa9-4714596493f0	role.create	Create Role	\N	role	create	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
54ed2f72-bac5-48e6-839d-8dbfdf2817e9	role.read	Read Role	\N	role	read	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
3ab99a70-ee53-43f0-9fd1-cd77385d9e37	role.update	Update Role	\N	role	update	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
4269f718-a643-4e2a-b533-3f013d588142	role.delete	Delete Role	\N	role	delete	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
4fa16528-463d-4ced-ad89-eb8d103634d4	role.manage	Manage Roles	\N	role	manage	identity	\N	t	\N	2026-01-26 10:00:59.27603+00	2026-01-26 10:00:59.27603+00
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
\.


--
-- Data for Name: role_permissions; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.role_permissions (id, role_id, permission_id, conditions) FROM stdin;
c87dab73-18a9-46a9-9d4c-e9e582f6ae42	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	676c8e81-b5c4-46c2-b8c4-b1f25dc78656	\N
2c44ec34-f2b2-44d3-893c-8a0056721e81	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	0a3a14a9-1745-47ec-a83a-53f039e991bd	\N
5651b3a4-0e50-423c-8360-b71c6e072b80	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	f22fb138-7a26-4759-9f14-ebc38a1c1b56	\N
e4e8810b-f5f8-4d6f-a8d4-134de026cd2a	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	e1407dfb-e388-40d3-82d0-c03f00110b36	\N
13a1fcd4-087c-40f6-9992-2af87ad76610	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	17d6fdd0-7332-421f-805d-b5f204f8bd7e	\N
92403f8f-1f58-4e1a-88f1-0fcc163e263b	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	8c518ff6-2206-4b35-b0b8-1b8f47ac13fd	\N
9b690d8e-f1ae-4235-b1fa-eb9c1be5a45d	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	a7392ca4-f836-427c-af5d-0782dead2d20	\N
0b81530e-60f3-4c10-8aca-b49f23b7789b	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	e135311e-4d1a-4964-be8a-c2f280c7537d	\N
dd3a42d8-536a-49cc-a3ee-313f62b2acbf	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	9e90b390-dfef-4c29-8a66-d031b44c54e9	\N
ae49e6e3-c5dd-4c9e-ac9c-d91f09a0bee2	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	34d61530-7b12-474d-89a7-128ed062798f	\N
a79ce70b-7bc2-4646-bf99-407e5c253ddb	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	4e5b2e79-af28-4936-aaa9-4714596493f0	\N
5961bbe9-5b2e-4e78-863e-a499f8e9a44f	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	54ed2f72-bac5-48e6-839d-8dbfdf2817e9	\N
edb88d3b-f9ce-4332-8987-c18e080fb723	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	3ab99a70-ee53-43f0-9fd1-cd77385d9e37	\N
e4baa4bf-1856-49ca-bafb-d4a7b83b080b	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	4269f718-a643-4e2a-b533-3f013d588142	\N
f7dae983-034b-4049-b2a5-70e18a7f0412	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	4fa16528-463d-4ced-ad89-eb8d103634d4	\N
41624a24-f5bd-4a71-a70a-209f1545390d	774f0485-d473-4016-92c3-dbb38634c3d3	0a3a14a9-1745-47ec-a83a-53f039e991bd	\N
b485bf5e-21e1-4595-8aed-f3b0a1e3c739	774f0485-d473-4016-92c3-dbb38634c3d3	f22fb138-7a26-4759-9f14-ebc38a1c1b56	\N
6503180e-5002-458e-8720-68f7785cbbbc	774f0485-d473-4016-92c3-dbb38634c3d3	8c518ff6-2206-4b35-b0b8-1b8f47ac13fd	\N
2feba1e0-0e2d-4784-9b87-7c16450b453e	774f0485-d473-4016-92c3-dbb38634c3d3	a7392ca4-f836-427c-af5d-0782dead2d20	\N
b4b88421-3501-4a71-aa64-73413d0af154	774f0485-d473-4016-92c3-dbb38634c3d3	e135311e-4d1a-4964-be8a-c2f280c7537d	\N
174af5af-38f0-4fa3-9ce7-41b6799d771c	774f0485-d473-4016-92c3-dbb38634c3d3	9e90b390-dfef-4c29-8a66-d031b44c54e9	\N
2e26ba30-e92f-403a-8b6d-1329d7a3d6ad	774f0485-d473-4016-92c3-dbb38634c3d3	34d61530-7b12-474d-89a7-128ed062798f	\N
916879c5-45c9-46ae-a30b-2419fbc28952	d7792db7-091b-4edd-bac3-b14d6ab7f859	0a3a14a9-1745-47ec-a83a-53f039e991bd	\N
95962945-968c-4f6b-a2c6-0bcb2637bd22	d7792db7-091b-4edd-bac3-b14d6ab7f859	a7392ca4-f836-427c-af5d-0782dead2d20	\N
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.roles (id, organization_id, name, code, description, is_system, is_default, hierarchy_level, is_active, extra_data, created_at, updated_at) FROM stdin;
38b9cb00-a985-4b0e-9bba-871c44e2d2d7	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	System Administrator	system_admin	Full system access	t	f	100	t	\N	2026-01-26 10:00:59.181253+00	2026-01-26 10:00:59.181253+00
774f0485-d473-4016-92c3-dbb38634c3d3	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	Organization Administrator	org_admin	Org-level admin access	t	f	50	t	\N	2026-01-26 10:00:59.181253+00	2026-01-26 10:00:59.181253+00
d7792db7-091b-4edd-bac3-b14d6ab7f859	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	User	user	Standard user access	t	t	10	t	\N	2026-01-26 10:00:59.181253+00	2026-01-26 10:00:59.181253+00
\.


--
-- Data for Name: user_organization_roles; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.user_organization_roles (id, user_id, organization_id, role_id, is_primary, is_active, status, invited_by_id, invited_at, joined_at, extra_data, created_at, updated_at) FROM stdin;
e1564254-61af-4c38-81b1-8d8b69b1b41a	17c129d5-685b-4196-9ed1-c412f648ce88	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d7792db7-091b-4edd-bac3-b14d6ab7f859	t	t	active	\N	\N	2026-01-26 10:00:59.377133+00	\N	2026-01-26 10:00:59.377133+00	2026-01-26 10:00:59.377133+00
1a0bdde0-6899-47c3-9af8-8f085ac639a0	5a54bc15-5af0-4577-8188-77f0adb2b989	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	d7792db7-091b-4edd-bac3-b14d6ab7f859	t	t	active	\N	\N	2026-01-26 10:00:59.377133+00	\N	2026-01-26 10:00:59.377133+00	2026-01-26 10:00:59.377133+00
3646233f-b92c-4828-927f-89e5f01945f8	8d509f22-5fe5-4765-9496-3a236cae2af1	bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150	38b9cb00-a985-4b0e-9bba-871c44e2d2d7	t	t	active	\N	\N	2026-01-26 10:00:59.377133+00	\N	2026-01-26 10:00:59.377133+00	2026-01-26 10:00:59.377133+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.users (id, email, password_hash, first_name, last_name, display_name, phone, avatar_url, user_type, status, is_active, email_verified, email_verified_at, mfa_enabled, mfa_secret, mfa_backup_codes, last_login_at, last_login_ip, failed_login_attempts, locked_until, preferences, timezone, language, extra_data, deleted_at, created_at, updated_at) FROM stdin;
afcc0f32-1bf6-4fa0-bfef-c1d0243d34ae	admin@example.com	$2b$12$ExR8Mv.K4V5K.T/Yv/T.m.Fw1F1F1F1F1F1F1F1F1F1F1F1F1F1F1F	System	Administrator	System Administrator	\N	\N	system_admin	active	t	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	2026-01-26 10:00:59.363341+00	2026-01-26 10:00:59.363341+00
17c129d5-685b-4196-9ed1-c412f648ce88	john.doe@example.com	$2b$12$KkR8Mv.K4V5K.T/Yv/T.m.Fw1F1F1F1F1F1F1F1F1F1F1F1F1F1F1F	John	Doe	John Doe	\N	\N	user	active	t	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	2026-01-26 10:00:59.363341+00	2026-01-26 10:00:59.363341+00
5a54bc15-5af0-4577-8188-77f0adb2b989	jane.smith@example.com	$2b$12$KkR8Mv.K4V5K.T/Yv/T.m.Fw1F1F1F1F1F1F1F1F1F1F1F1F1F1F1F	Jane	Smith	Jane Smith	\N	\N	user	active	t	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	2026-01-26 10:00:59.363341+00	2026-01-26 10:00:59.363341+00
386f1db2-caf1-40aa-aaec-bcf9a531356a	negi.yaten@gmail.com	$2b$12$B1kmjv2THI78DsItPZuiEuBX8BylSrGEvh4gvau0DZtRFewDH9hcy	Yaten	Negi	Yaten Negi	9008750492	\N	user	active	t	t	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-01-27 05:31:43.952107+00	2026-01-27 05:31:43.952113+00
8d509f22-5fe5-4765-9496-3a236cae2af1	devendera.negi@gmail.com	$2b$12$ckGV6IZw7aVeCxPK/QeZ/.W/sLylhDqe3ri9NDuFZclQ3NUt/l7Uy	Devendera	Negi	Devendera Negi	9008750492	\N	user	active	t	t	\N	f	\N	\N	2026-01-27 10:38:16.609444+00	192.168.65.1	0	\N	{}	UTC	en	{}	\N	2026-01-26 16:01:22.18562+00	2026-01-27 10:38:16.623192+00
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

\unrestrict I5Fgcz4iU3PkGSxIRajoUuEFJIGV52riB4uNZuzYua23yStqUaJB6JG3rh78NUv

