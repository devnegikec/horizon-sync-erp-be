--
-- PostgreSQL database dump
--

\restrict S3A1Xtn9gBhyPQ8GK7w0nlRM2fBO9oLbs2JuJZ9ZOzmUjCEEpJQlnChtEKCLYj6

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
    'item',
    'item_group',
    'warehouse',
    'stock_entry',
    'batch',
    'serial',
    'report',
    'setting',
    'all',
    'invitation'
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
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
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
    message text,
    extra_data jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.invitations OWNER TO horizon_user;

--
-- Name: TABLE invitations; Type: COMMENT; Schema: public; Owner: horizon_user
--

COMMENT ON TABLE public.invitations IS 'Stores user invitations to organizations';


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

COPY public.invitations (id, organization_id, email, first_name, last_name, role_id, team_ids, invited_by_id, token_hash, status, expires_at, accepted_at, accepted_user_id, message, extra_data, created_at) FROM stdin;
\.


--
-- Data for Name: organizations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.organizations (id, name, slug, display_name, description, email, phone, website, address_line1, address_line2, city, state, postal_code, country, organization_type, industry, tax_id, logo_url, primary_color, domain, sso_enabled, sso_provider, sso_config, status, is_active, owner_id, settings, extra_data, deleted_at, created_at, updated_at) FROM stdin;
cd7845fa-8a99-44ac-bb2f-cf00fb8001ce	Default Organization	default-org	Default Organization	Default organization for the system	\N	\N	\N	\N	\N	\N	\N	\N	\N	business	\N	\N	\N	\N	\N	\N	\N	\N	active	t	\N	\N	\N	\N	2026-01-25 21:57:55.004903+00	2026-01-25 21:57:55.004903+00
\.


--
-- Data for Name: password_resets; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.password_resets (id, user_id, token_hash, expires_at, used_at, ip_address, user_agent, created_at) FROM stdin;
\.


--
-- Data for Name: permissions; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.permissions (id, code, name, description, resource, action, module, category, is_active, extra_data, created_at, updated_at) FROM stdin;
f4a18143-bff5-4a13-acf1-6a35756b7bf5	user.create	Create User	\N	user	create	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
f88f62d0-fc17-40c7-9741-872db41b9539	user.read	Read User	\N	user	read	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
10d84b85-5e4a-4536-a9bd-b919aae8eabd	user.update	Update User	\N	user	update	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
860ea1bc-d29e-4dff-9566-742901d341bc	user.delete	Delete User	\N	user	delete	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
58d5f68c-a7a3-4fa1-a591-ee753fd56423	user.manage	Manage Users	\N	user	manage	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
0b52cc3e-9b66-412e-a1c6-58a5fb6e2c37	org.create	Create Org	\N	organization	create	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
b1daa255-cafa-472e-8a1f-f55ca94250a1	org.read	Read Org	\N	organization	read	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
c591f9fc-dafe-465f-b28f-44a400471123	org.update	Update Org	\N	organization	update	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
fedd26c1-8cff-4d81-a47b-08ece4241c99	org.delete	Delete Org	\N	organization	delete	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
0e67b560-4e27-4bc8-9818-dbe4d1056237	org.manage	Manage Orgs	\N	organization	manage	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
2dc069b2-a0db-4058-9e4d-6967de48ae0c	role.create	Create Role	\N	role	create	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
5fc36fbb-2df4-4d25-ac21-0433e65eb103	role.read	Read Role	\N	role	read	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
a30207ea-25b9-4a22-9228-68eb13f1cf48	role.update	Update Role	\N	role	update	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
401a8882-8b1f-4781-a505-aab641d5f6e0	role.delete	Delete Role	\N	role	delete	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
9469bae4-f2a1-4947-8603-8c94060c0fd7	role.manage	Manage Roles	\N	role	manage	identity	\N	t	\N	2026-01-25 21:57:55.058654+00	2026-01-25 21:57:55.058654+00
\.


--
-- Data for Name: refresh_tokens; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.refresh_tokens (id, user_id, token_hash, token_family, device_id, device_name, device_type, os_info, browser_info, ip_address, user_agent, expires_at, revoked_at, revoked_reason, created_at, last_used_at) FROM stdin;
8768d7c0-335e-47d1-95fa-68d1c5cc683b	b9b857fb-876e-4e2c-809b-ec474b9f8a33	56a48e2eebbeb6a74106ec7e3a731f0056170e79a6f4dd7c512c94c222c422c8	46a0f58c-241a-4197-89fc-6b42d780a230	\N	\N	\N	\N	\N	192.168.65.1	PostmanRuntime/7.51.0	2026-02-01 22:07:23+00	\N	\N	2026-01-25 22:07:23.043345+00	\N
d23cce11-c858-44bb-aebb-fee802864e01	b9b857fb-876e-4e2c-809b-ec474b9f8a33	3a586257bfadd242cbe464790bc76b9e1dfb810121d55e606eaf8f298c874061	4c3373f6-61ba-40c0-afd2-84b6c09e5f41	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-01 22:13:12+00	\N	\N	2026-01-25 22:13:12.492286+00	\N
35a8d602-99a0-4c1f-88d8-a72d3a94d788	b9b857fb-876e-4e2c-809b-ec474b9f8a33	d674e228f49eb78aac1c80a084b450bc2555f5e0782b38c4ada2ad6c134da2fe	857f3e88-2fbe-455a-965e-711634548bed	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-01 22:22:25+00	\N	\N	2026-01-25 22:22:25.321407+00	\N
114ce9d1-a741-4e3a-add2-44a9a8a78291	b9b857fb-876e-4e2c-809b-ec474b9f8a33	e5b7bf3322cd0f86c0bad7c27263a5c0a0ef46921efb627cd4cb2b2ce9216a7c	54636fbf-e4d7-428b-a784-f8dc0f3bed4d	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-01 22:27:23+00	\N	\N	2026-01-25 22:27:23.318912+00	\N
71e26e15-ca3a-4430-bfbf-8c6221d2b830	b9b857fb-876e-4e2c-809b-ec474b9f8a33	82a63a4349f610fcbad8a9d42a787838222189e2f52591a0a6308fa2858992b0	8ac69841-0a5f-47f2-94d0-8aee3cbc0115	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-01 22:30:53+00	\N	\N	2026-01-25 22:30:53.486314+00	\N
50112499-0073-4529-b793-0d028521dbbf	b9b857fb-876e-4e2c-809b-ec474b9f8a33	c4a783d465566124bdc0a1e082e58f313e0b72348a369525734e73b3a1e860ff	3618c5f3-5273-42df-9e15-142614081f27	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-01 22:35:39+00	\N	\N	2026-01-25 22:35:39.185246+00	\N
5ddf4ecb-1b4e-4647-ad02-b8d2c56d1881	b9b857fb-876e-4e2c-809b-ec474b9f8a33	74817c88cef87543c6445be58a67f20af224165be6116396567de84549de7bfa	a9b28987-3993-4112-8416-915a182b47e0	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-01 22:38:08+00	\N	\N	2026-01-25 22:38:08.812988+00	\N
d6916000-3530-4ed3-8052-25e284988327	b9b857fb-876e-4e2c-809b-ec474b9f8a33	6298fbdc2e0e693466fd5b77a6e2b279643a4c97a0be267a10b16117263546b3	d11f730d-3e2e-4b8e-aac5-43f470b4f478	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-01 22:43:46+00	\N	\N	2026-01-25 22:43:46.571125+00	\N
1465d69e-9c9a-43f4-b992-a6f30c6f84e4	b9b857fb-876e-4e2c-809b-ec474b9f8a33	9d3d3f3992d83141dccda051164ecabc08066c12196318d4e0a0eacad378ed82	e91ce62f-e846-407a-9f49-cdd7efd34a0d	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-01 22:49:33+00	\N	\N	2026-01-25 22:49:33.582967+00	\N
342df8f3-619c-475e-a12a-797bd5a202c7	b9b857fb-876e-4e2c-809b-ec474b9f8a33	7d70279cb486aa4337475cc63e52c5c6a6d38457e800308f0f024734fa207ee3	c1bafb9e-4c45-4f25-a37b-522a7d4d0193	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-01 22:55:40+00	\N	\N	2026-01-25 22:55:40.071808+00	\N
5077c16f-77df-4484-a347-6159ad470129	b9b857fb-876e-4e2c-809b-ec474b9f8a33	13f89f4d532fed45aaf3248f00acf99b37a4de5cbf88ffc7d379a136d4877fae	4cfde021-cac7-4274-874c-a4090fbb5556	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-01 22:59:13+00	\N	\N	2026-01-25 22:59:13.05844+00	\N
8ea77752-fb69-4b9f-8afc-0b899d30ae51	b9b857fb-876e-4e2c-809b-ec474b9f8a33	7142390f0af9c11f8830798a9c852af9e0718b3e6df768d0c00c79b25492a1ad	b52a5e21-f314-4d92-b3d8-c9a6d5b52133	\N	iphone	phone	ios	edge	192.168.65.1	PostmanRuntime/7.51.0	2026-02-02 06:58:28+00	\N	\N	2026-01-26 06:58:28.38161+00	\N
\.


--
-- Data for Name: role_permissions; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.role_permissions (id, role_id, permission_id, conditions) FROM stdin;
a904dc12-f86c-4d9b-a833-f942aabf4f9f	452a9306-3aeb-45da-9051-b0b312ad5ac0	f4a18143-bff5-4a13-acf1-6a35756b7bf5	\N
5dff34d7-7018-4da0-bcec-7b07aff3f050	452a9306-3aeb-45da-9051-b0b312ad5ac0	f88f62d0-fc17-40c7-9741-872db41b9539	\N
0cb9b87d-7d23-4a48-9ea1-acab56d5a853	452a9306-3aeb-45da-9051-b0b312ad5ac0	10d84b85-5e4a-4536-a9bd-b919aae8eabd	\N
97c6c649-d743-4796-ba14-d47d0f45328a	452a9306-3aeb-45da-9051-b0b312ad5ac0	860ea1bc-d29e-4dff-9566-742901d341bc	\N
4d08cd5f-6a7e-4f64-bb4e-d4060a2ec6c9	452a9306-3aeb-45da-9051-b0b312ad5ac0	58d5f68c-a7a3-4fa1-a591-ee753fd56423	\N
e0085a86-8e3b-44d8-8b4d-cfc4915292dd	452a9306-3aeb-45da-9051-b0b312ad5ac0	0b52cc3e-9b66-412e-a1c6-58a5fb6e2c37	\N
71472417-2f2f-42fa-b0bc-b57fc6668512	452a9306-3aeb-45da-9051-b0b312ad5ac0	b1daa255-cafa-472e-8a1f-f55ca94250a1	\N
e8ead9f9-ecb5-4e22-a348-15664af6f9ac	452a9306-3aeb-45da-9051-b0b312ad5ac0	c591f9fc-dafe-465f-b28f-44a400471123	\N
b1285bf7-479b-47b9-9c19-adb414bdeed1	452a9306-3aeb-45da-9051-b0b312ad5ac0	fedd26c1-8cff-4d81-a47b-08ece4241c99	\N
60530ffe-571e-426e-8d96-5d392bcbe216	452a9306-3aeb-45da-9051-b0b312ad5ac0	0e67b560-4e27-4bc8-9818-dbe4d1056237	\N
d0d9ae3a-74e8-4bb0-86d4-ca78959b5f0d	452a9306-3aeb-45da-9051-b0b312ad5ac0	2dc069b2-a0db-4058-9e4d-6967de48ae0c	\N
20584a28-90b2-4b85-8bd0-4000c94dfc90	452a9306-3aeb-45da-9051-b0b312ad5ac0	5fc36fbb-2df4-4d25-ac21-0433e65eb103	\N
d70f001e-a5e5-412a-9491-96c895889d77	452a9306-3aeb-45da-9051-b0b312ad5ac0	a30207ea-25b9-4a22-9228-68eb13f1cf48	\N
5896d9e5-3b31-4a85-b6d0-668e8975ed45	452a9306-3aeb-45da-9051-b0b312ad5ac0	401a8882-8b1f-4781-a505-aab641d5f6e0	\N
265dc19b-1f37-4aaa-935e-ac93e9cb8f34	452a9306-3aeb-45da-9051-b0b312ad5ac0	9469bae4-f2a1-4947-8603-8c94060c0fd7	\N
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.roles (id, organization_id, name, code, description, is_system, is_default, hierarchy_level, is_active, extra_data, created_at, updated_at) FROM stdin;
452a9306-3aeb-45da-9051-b0b312ad5ac0	cd7845fa-8a99-44ac-bb2f-cf00fb8001ce	System Administrator	system_admin	Full system access	t	f	100	t	\N	2026-01-25 21:57:55.035462+00	2026-01-25 21:57:55.035462+00
3e24101a-db60-497d-87d2-ba31ac302204	cd7845fa-8a99-44ac-bb2f-cf00fb8001ce	Organization Administrator	org_admin	Org-level admin access	t	f	50	t	\N	2026-01-25 21:57:55.035462+00	2026-01-25 21:57:55.035462+00
267b57d0-2801-49c9-8d40-b6291ff37de0	cd7845fa-8a99-44ac-bb2f-cf00fb8001ce	User	user	Standard user access	t	t	10	t	\N	2026-01-25 21:57:55.035462+00	2026-01-25 21:57:55.035462+00
\.


--
-- Data for Name: user_organization_roles; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.user_organization_roles (id, user_id, organization_id, role_id, is_primary, is_active, status, invited_by_id, invited_at, joined_at, extra_data, created_at, updated_at) FROM stdin;
34180cb3-03b6-4153-be6d-da9bf3845c4b	b9b857fb-876e-4e2c-809b-ec474b9f8a33	cd7845fa-8a99-44ac-bb2f-cf00fb8001ce	452a9306-3aeb-45da-9051-b0b312ad5ac0	t	t	active	\N	\N	2026-01-25 22:11:48.457477+00	\N	2026-01-25 22:11:48.457477+00	2026-01-25 22:11:48.457477+00
03aec504-f293-4b7d-ad98-d836c9ca39d3	b9b857fb-876e-4e2c-809b-ec474b9f8a33	cd7845fa-8a99-44ac-bb2f-cf00fb8001ce	267b57d0-2801-49c9-8d40-b6291ff37de0	t	t	active	\N	\N	2026-01-25 22:11:48.457477+00	\N	2026-01-25 22:11:48.457477+00	2026-01-25 22:11:48.457477+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.users (id, email, password_hash, first_name, last_name, display_name, phone, avatar_url, user_type, status, is_active, email_verified, email_verified_at, mfa_enabled, mfa_secret, mfa_backup_codes, last_login_at, last_login_ip, failed_login_attempts, locked_until, preferences, timezone, language, extra_data, deleted_at, created_at, updated_at) FROM stdin;
b9b857fb-876e-4e2c-809b-ec474b9f8a33	devendera.negi@gmail.com	$2b$12$EmasHj.wGc.rCVfu3DMIJe7bAFWm1EFkqvSHANeYPueOKVy5CkBFu	Devendera	Negi	Devendera Negi	9008750492	\N	user	pending	t	f	\N	f	\N	\N	2026-01-26 06:58:28.31717+00	192.168.65.1	0	\N	{}	UTC	en	{}	\N	2026-01-25 22:07:23.015105+00	2026-01-26 06:58:28.322923+00
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
-- Name: invitations invitations_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_token_hash_key UNIQUE (token_hash);


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
-- Name: idx_invitations_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_invitations_organization_id ON public.invitations USING btree (organization_id);


--
-- Name: idx_invitations_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_invitations_status ON public.invitations USING btree (status);


--
-- Name: idx_invitations_token_hash; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_invitations_token_hash ON public.invitations USING btree (token_hash);


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

\unrestrict S3A1Xtn9gBhyPQ8GK7w0nlRM2fBO9oLbs2JuJZ9ZOzmUjCEEpJQlnChtEKCLYj6

