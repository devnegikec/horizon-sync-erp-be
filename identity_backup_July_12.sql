--
-- PostgreSQL database dump
--

\restrict qHOpkViatHyjNbyDQEHHVT3erdiD6FM5r8GYiD48WSFdonVH3124trC4li9QfDv

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

SET statement_timeout = 0;

SET lock_timeout = 0;

SET idle_in_transaction_session_timeout = 0;

SET client_encoding = 'UTF8';

SET standard_conforming_strings = on;

SELECT pg_catalog.set_config ('search_path', '', false);

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
    'scan'
);

ALTER TYPE public.actiontype OWNER TO horizon_user;

--
-- Name: auditactiontype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.auditactiontype AS ENUM (
    'assign',
    'update',
    'revoke',
    'access_grant',
    'access_revoke'
);

ALTER TYPE public.auditactiontype OWNER TO horizon_user;

--
-- Name: organizationstatus; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.organizationstatus AS ENUM (
    'active',
    'inactive',
    'suspended',
    'trial',
    'overdue',
    'deactivated'
);

ALTER TYPE public.organizationstatus OWNER TO horizon_user;

--
-- Name: organizationtype; Type: TYPE; Schema: public; Owner: horizon_user
--

CREATE TYPE public.organizationtype AS ENUM (
    'enterprise',
    'business',
    'startup',
    'individual',
    'master',
    'customer'
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
    'payment',
    'billing',
    'reporting',
    'asn_order',
    'pick_list',
    'receiving_slip'
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
    'guest',
    'warehouse_worker'
);

ALTER TYPE public.usertype OWNER TO horizon_user;

--
-- Name: check_single_master_org(); Type: FUNCTION; Schema: public; Owner: horizon_user
--

CREATE FUNCTION public.check_single_master_org() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.organization_type = 'master' THEN
                IF EXISTS (
                    SELECT 1 FROM organizations
                    WHERE organization_type = 'master'
                    AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::uuid)
                    AND deleted_at IS NULL
                ) THEN
                    RAISE EXCEPTION 'Only one master organization is allowed';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;

ALTER FUNCTION public.check_single_master_org() OWNER TO horizon_user;

--
-- Name: validate_system_admin_role_assignment(); Type: FUNCTION; Schema: public; Owner: horizon_user
--

CREATE FUNCTION public.validate_system_admin_role_assignment() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            -- Check if the role being assigned has system admin permissions
            IF EXISTS (
                SELECT 1 FROM role_permissions rp
                JOIN permissions p ON rp.permission_id = p.id
                WHERE rp.role_id = NEW.role_id
                AND (
                    p.code LIKE 'system_admin.%'
                    OR p.code = '*.*'
                    OR p.code = 'system.admin'
                )
            ) THEN
                -- Ensure the user being assigned belongs to master organization
                -- (We'll validate this in application code since we need to identify master org)
                -- For now, just log the system admin role assignment
                RAISE NOTICE 'System admin role assignment for user % in organization %',
                    NEW.user_id, NEW.organization_id;
            END IF;

            RETURN NEW;
        END;
        $$;

ALTER FUNCTION public.validate_system_admin_role_assignment() OWNER TO horizon_user;

--
-- Name: FUNCTION validate_system_admin_role_assignment(); Type: COMMENT; Schema: public; Owner: horizon_user
--

COMMENT ON FUNCTION public.validate_system_admin_role_assignment () IS 'Task 1C-2: Validates system admin role assignments to ensure proper organization membership';

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
-- Name: entity_audit_logs; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.entity_audit_logs (
    id uuid NOT NULL,
    user_id uuid,
    organization_id uuid,
    action character varying(10) NOT NULL,
    table_name character varying(100) NOT NULL,
    record_id uuid NOT NULL,
    old_values json,
    new_values json,
    changed_fields json,
    ip_address character varying(45),
    user_agent text,
    created_at timestamp with time zone DEFAULT now()
);

ALTER TABLE public.entity_audit_logs OWNER TO horizon_user;

--
-- Name: invitations; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.invitations (
    id uuid DEFAULT gen_random_uuid () NOT NULL,
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
    updated_at timestamp with time zone,
    base_currency character varying(3) NOT NULL,
    billing_status public.organizationstatus DEFAULT 'active'::public.organizationstatus NOT NULL,
    subscription_start_date timestamp with time zone,
    subscription_end_date timestamp with time zone,
    seat_limit integer DEFAULT 10 NOT NULL,
    credit_limit integer DEFAULT 1000 NOT NULL,
    trial_end_date timestamp without time zone,
    max_users integer,
    max_credits integer,
    billing_contact_email character varying(255),
    billing_cycle character varying(20),
    customer_since timestamp with time zone,
    last_billed_date timestamp without time zone,
    next_billing_date timestamp without time zone,
    parent_organization_id uuid
);

ALTER TABLE public.organizations OWNER TO horizon_user;

--
-- Name: otp_verifications; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.otp_verifications (
    id uuid NOT NULL,
    organization_id uuid,
    otp_type character varying(20) NOT NULL,
    target character varying(255) NOT NULL,
    otp_code character varying(10) NOT NULL,
    is_verified boolean DEFAULT false NOT NULL,
    verified_at timestamp with time zone,
    expires_at timestamp with time zone NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    ip_address character varying(45),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.otp_verifications OWNER TO horizon_user;

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
-- Name: service_credentials; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.service_credentials (
    id uuid NOT NULL,
    client_id character varying(255) NOT NULL,
    client_secret_hash character varying(255) NOT NULL,
    service_name character varying(255) NOT NULL,
    permissions jsonb DEFAULT '[]'::jsonb NOT NULL,
    scopes character varying(255),
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_used_at timestamp with time zone
);

ALTER TABLE public.service_credentials OWNER TO horizon_user;

--
-- Name: system_admin_audit_logs; Type: TABLE; Schema: public; Owner: horizon_user
--

CREATE TABLE public.system_admin_audit_logs (
    id uuid DEFAULT gen_random_uuid () NOT NULL,
    action_id character varying(255) NOT NULL,
    action_type public.auditactiontype NOT NULL,
    admin_user_id uuid NOT NULL,
    admin_username character varying(255) NOT NULL,
    target_user_id uuid,
    target_username character varying(255),
    target_organization_id uuid,
    target_organization_name character varying(255),
    changes_made jsonb DEFAULT '{}'::jsonb NOT NULL,
    performed_by character varying(255) NOT NULL,
    notes character varying(1000),
    performed_date timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.system_admin_audit_logs OWNER TO horizon_user;

--
-- Name: TABLE system_admin_audit_logs; Type: COMMENT; Schema: public; Owner: horizon_user
--

COMMENT ON TABLE public.system_admin_audit_logs IS 'Audit log for tracking all system admin actions and administrative activities';

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
    updated_at timestamp with time zone,
    qr_code character varying(100)
);

ALTER TABLE public.users OWNER TO horizon_user;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: horizon_user
--

COPY public.alembic_version (version_num) FROM stdin; 013 \.

--
-- Data for Name: email_verifications; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.email_verifications (id, user_id, email, token_hash, expires_at, verified_at, created_at) FROM stdin;
\.

--
-- Data for Name: entity_audit_logs; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.entity_audit_logs (id, user_id, organization_id, action, table_name, record_id, old_values, new_values, changed_fields, ip_address, user_agent, created_at) FROM stdin;
8806e9bd-c02d-407c-bfc8-a37d82d7123e	\N	\N	CREATE	users	20c0587a-7145-48e0-9471-caae8de8fe4d	null	{"id": "20c0587a-7145-48e0-9471-caae8de8fe4d", "email": "negi.yaten+Raj0078@gmail.com", "first_name": "Raj", "last_name": "SN", "display_name": "Raj SN", "phone": "+916565432562", "avatar_url": null, "user_type": "user", "status": "pending", "is_active": "True", "email_verified": "False", "email_verified_at": null, "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-04T13:08:49.067324", "updated_at": "2026-06-04T13:08:49.067328"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-04 13:08:49.086405+00
b6918fae-a6e8-4a77-838e-95de46fcab7f	\N	\N	UPDATE	users	20c0587a-7145-48e0-9471-caae8de8fe4d	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-07T05:03:29.650341+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-07 05:03:29.982609+00
19efc771-2680-4ff5-8c8e-9ce800333dff	20c0587a-7145-48e0-9471-caae8de8fe4d	\N	CREATE	organizations	05397b7b-95bb-4560-b3d0-dff21b3db1ee	null	{"id": "05397b7b-95bb-4560-b3d0-dff21b3db1ee", "name": "system Org", "slug": "system-org", "display_name": "system Org", "description": "asdfasdfasdfasdfasdfasdf", "email": "negi.yaten+Raj0078@gmail.com", "phone": "+916565432562", "website": "https://www.tatasoft.com", "address_line1": null, "address_line2": null, "city": null, "state": null, "postal_code": null, "country": "IN", "organization_type": "business", "industry": "Healthcare", "tax_id": null, "base_
": "INR", "logo_url": null, "primary_color": null, "domain": null, "sso_enabled": "False", "sso_provider": null, "sso_config": null, "status": "active", "is_active": "True", "billing_status": "trial", "subscription_start_date": "2026-06-07", "subscription_end_date": null, "trial_end_date": "2026-07-07", "max_users": "10", "max_credits": "1000", "billing_contact_email": null, "billing_cycle": "monthly", "customer_since": "2026-06-07T05:20:15.617769+00:00", "last_billed_date": null, "next_billing_date": "2026-08-06", "parent_organization_id": null, "owner_id": "20c0587a-7145-48e0-9471-caae8de8fe4d", "settings": "{}", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-07T05:20:15.623135", "updated_at": "2026-06-07T05:20:15.623140"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-07 05:20:15.644872+00
e721e724-bd94-4531-9a4a-d4487266cd81	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-07T06:09:36.155702+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-07 06:09:36.179769+00
10373e9a-713e-4681-a935-46a9c4dbddee	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"last_login_at": "2026-06-07T06:09:36.155702+00:00"}	{"last_login_at": "2026-06-07T06:10:42.407779+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-07 06:10:42.414269+00
f61fcf67-b2b6-4c4c-8b3b-3cb7ec9de305	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"last_login_at": "2026-06-07T06:10:42.407779+00:00"}	{"last_login_at": "2026-06-07T06:16:39.191040+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-07 06:16:39.218935+00
e4b91847-fbdb-48d7-8b83-b994b126479b	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"last_login_at": "2026-06-07T06:16:39.191040+00:00"}	{"last_login_at": "2026-06-07T06:25:05.335634+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-07 06:25:05.368637+00
d04b84e5-bed1-4f2c-8188-6c9176498483	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"last_login_at": "2026-06-07T06:25:05.335634+00:00"}	{"last_login_at": "2026-06-07T06:28:22.943730+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-07 06:28:23.00862+00
de408ea7-655e-4dde-af9d-984eb80aec49	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"last_login_at": "2026-06-07T06:28:22.943730+00:00"}	{"last_login_at": "2026-06-07T06:33:53.640390+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-07 06:33:53.662926+00
d8d4206c-47a4-48b6-9e56-1a65661064f8	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"email_verified_at": "2026-06-07T06:23:39.827668+00:00"}	{"email_verified_at": "2026-06-07T06:47:27.812973"}	["email_verified_at"]	\N	\N	2026-06-07 06:47:27.835888+00
1a26a91e-e858-49c1-a0b9-92b5e2ac8a85	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"last_login_at": "2026-06-07T06:33:53.640390+00:00"}	{"last_login_at": "2026-06-07T07:03:13.901664+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-07 07:03:13.91262+00
92a4c58b-9bde-403e-b362-b8301acb6711	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"email_verified_at": "2026-06-07T06:47:27.812973+00:00"}	{"email_verified_at": "2026-06-07T07:04:28.026537"}	["email_verified_at"]	\N	\N	2026-06-07 07:04:28.053576+00
052b3d99-9bea-4f9b-aba7-1e440a6af08f	\N	\N	UPDATE	users	20c0587a-7145-48e0-9471-caae8de8fe4d	{"last_login_at": "2026-06-07T05:03:29.650341+00:00"}	{"last_login_at": "2026-06-08T12:34:49.746191+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-08 12:34:49.788959+00
afe8ccd6-2c72-472a-96ea-7efb1dbdcfb8	\N	\N	UPDATE	users	20c0587a-7145-48e0-9471-caae8de8fe4d	{"last_login_at": "2026-06-08T12:34:49.746191+00:00"}	{"last_login_at": "2026-06-08T12:49:53.245113+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-08 12:49:53.24934+00
d7462b87-cbf4-4c39-96d2-567377976ede	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"last_login_at": "2026-06-07T07:03:13.901664+00:00"}	{"last_login_at": "2026-06-08T12:51:02.337781+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-08 12:51:02.344583+00
a7e4692a-80c9-47f0-bff1-be93dd0cef7f	\N	\N	UPDATE	users	20c0587a-7145-48e0-9471-caae8de8fe4d	{"last_login_at": "2026-06-08T12:49:53.245113+00:00"}	{"last_login_at": "2026-06-08T15:22:29.474581+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-08 15:22:29.490931+00
b656591a-4996-4d12-826b-c840ea4fd7e6	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"last_login_at": "2026-06-08T12:51:02.337781+00:00"}	{"last_login_at": "2026-06-09T18:10:27.007373+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-09 18:10:27.0756+00
48fb96b1-db0c-447f-a738-c60f2396d518	\N	\N	UPDATE	users	20c0587a-7145-48e0-9471-caae8de8fe4d	{"last_login_at": "2026-06-08T15:22:29.474581+00:00"}	{"last_login_at": "2026-06-09T18:11:55.481858+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-09 18:11:55.490755+00
ea154b8a-fa81-4d4f-87da-97dd70139449	\N	\N	UPDATE	users	fbfd7719-159d-4751-ba13-5fc9e35fa470	{"last_login_at": "2026-06-12T06:26:05.670963+00:00"}	{"last_login_at": "2026-06-17T10:53:40.436947+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-17 10:53:40.495566+00
6cdd4e2b-6946-4706-a775-61821643bf01	\N	\N	CREATE	users	fbfd7719-159d-4751-ba13-5fc9e35fa470	null	{"id": "fbfd7719-159d-4751-ba13-5fc9e35fa470", "email": "wmsTesting@gmail.com", "first_name": "wmsTesting", "last_name": "SN", "display_name": "wmsTesting SN", "phone": "+916622334423", "avatar_url": null, "user_type": "user", "status": "pending", "is_active": "True", "email_verified": "False", "email_verified_at": null, "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-11T17:53:48.184554", "updated_at": "2026-06-11T17:53:48.184558"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-11 17:53:48.465542+00
cca3c60f-ed10-446f-8af3-be523b3789f6	fbfd7719-159d-4751-ba13-5fc9e35fa470	\N	CREATE	organizations	ddfad734-9afb-497b-81a3-ffc85caec590	null	{"id": "ddfad734-9afb-497b-81a3-ffc85caec590", "name": "WMS manager ", "slug": "wms-manager", "display_name": "WMS manager ", "description": "asdfasdfasdfasdf", "email": "wmsTesting@gmail.com", "phone": "+916622334423", "website": "https://www.flipsalt12.com", "address_line1": null, "address_line2": null, "city": null, "state": null, "postal_code": null, "country": "IN", "organization_type": "individual", "industry": "Healthcare", "tax_id": null, "base_currency": "INR", "logo_url": null, "primary_color": null, "domain": null, "sso_enabled": "False", "sso_provider": null, "sso_config": null, "status": "active", "is_active": "True", "billing_status": "trial", "subscription_start_date": "2026-06-11", "subscription_end_date": null, "trial_end_date": "2026-07-11", "max_users": "10", "max_credits": "1000", "billing_contact_email": null, "billing_cycle": "monthly", "customer_since": "2026-06-11T17:54:13.797086+00:00", "last_billed_date": null, "next_billing_date": "2026-08-10", "parent_organization_id": null, "owner_id": "fbfd7719-159d-4751-ba13-5fc9e35fa470", "settings": "{}", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-11T17:54:13.801057", "updated_at": "2026-06-11T17:54:13.801060"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-11 17:54:13.807594+00
ae6d41e8-fdad-4a2c-8108-e95e3084166e	\N	\N	UPDATE	users	ba121f89-c767-4fdd-ab43-fd658c42a9d4	{"last_login_at": "2026-06-09T18:10:27.007373+00:00"}	{"last_login_at": "2026-06-11T18:10:01.865416+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-11 18:10:01.875762+00
348cdb06-7889-4b59-b8a9-fa51c92ac579	\N	\N	CREATE	users	6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	null	{"id": "6b5f5d1c-28e8-4253-ae1c-acdded9e88c1", "email": "negi.yaten+wms_manager_01@gmail.com", "first_name": "Prestige", "last_name": "Manager", "display_name": null, "phone": null, "avatar_url": null, "user_type": "user", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": "2026-06-11T19:21:37.676535+00:00", "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-11T19:21:37.687439", "updated_at": "2026-06-11T19:21:37.687444"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-11 19:21:37.721353+00
b3020fb1-ccd2-412c-8f81-597ba3aab164	\N	\N	UPDATE	users	6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-11T19:22:13.292603+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-11 19:22:13.30033+00
6fb13bfe-dc58-4607-bc7c-5954977e62ec	\N	\N	UPDATE	users	6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	{"last_login_at": "2026-06-11T19:22:13.292603+00:00"}	{"last_login_at": "2026-06-12T04:38:36.786883+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-12 04:38:36.793187+00
cb53617c-eeb4-4907-81b0-02b7e5173429	\N	\N	UPDATE	users	fbfd7719-159d-4751-ba13-5fc9e35fa470	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-12T04:43:42.624877+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-12 04:43:42.628793+00
5293361e-119a-4ed1-bc10-f58fc6c442d5	\N	\N	CREATE	users	c0bf7fb1-687d-47cf-b020-b5c6007b589d	null	{"id": "c0bf7fb1-687d-47cf-b020-b5c6007b589d", "email": "negi.yaten+user1@gmail.com", "first_name": "Lovleen", "last_name": "Rawat", "display_name": null, "phone": null, "avatar_url": null, "user_type": "user", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": "2026-06-12T04:49:52.614827+00:00", "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-12T04:49:52.616148", "updated_at": "2026-06-12T04:49:52.616151"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 04:49:52.619123+00
c315dc5f-e95a-4f5b-9889-fecf2cf518af	\N	\N	UPDATE	users	fbfd7719-159d-4751-ba13-5fc9e35fa470	{"last_login_at": "2026-06-12T04:43:42.624877+00:00"}	{"last_login_at": "2026-06-12T05:01:43.130659+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-12 05:01:43.134298+00
038f491d-bba4-4af8-b5dd-0e8545098356	fbfd7719-159d-4751-ba13-5fc9e35fa470	ddfad734-9afb-497b-81a3-ffc85caec590	UPDATE	users	c0bf7fb1-687d-47cf-b020-b5c6007b589d	{"status": "active", "is_active": "True"}	{"status": "inactive", "is_active": "False"}	["status", "is_active"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-12 05:01:56.431665+00
915a5d7c-aa6f-4a39-a89c-e0dd6e3dbaeb	\N	\N	UPDATE	users	6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	{"last_login_at": "2026-06-12T04:38:36.786883+00:00"}	{"last_login_at": "2026-06-12T05:02:17.980854+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-12 05:02:17.984488+00
e42ae0a5-c47a-4d67-b29d-c974a49305c7	\N	\N	UPDATE	users	fbfd7719-159d-4751-ba13-5fc9e35fa470	{"last_login_at": "2026-06-12T05:01:43.130659+00:00"}	{"last_login_at": "2026-06-12T06:08:24.933956+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-12 06:08:24.957452+00
0b2e9e35-552a-48c5-9ed5-f23434d48826	\N	\N	UPDATE	users	6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	{"last_login_at": "2026-06-12T05:02:17.980854+00:00"}	{"last_login_at": "2026-06-12T06:25:27.177237+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-12 06:25:27.464363+00
2a014695-8e60-4ee5-9ffd-6966ba3ea229	\N	\N	UPDATE	users	fbfd7719-159d-4751-ba13-5fc9e35fa470	{"last_login_at": "2026-06-12T06:08:24.933956+00:00"}	{"last_login_at": "2026-06-12T06:26:05.670963+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-12 06:26:05.680493+00
9d5c298a-ac45-4313-af86-bb4df37bb588	\N	\N	UPDATE	users	fbfd7719-159d-4751-ba13-5fc9e35fa470	{"last_login_at": "2026-06-17T10:53:40.436947+00:00"}	{"last_login_at": "2026-06-17T10:59:39.180455+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-17 10:59:39.188575+00
aa2154e8-aec2-427c-9b50-460fd5560493	\N	\N	CREATE	users	8a5f437f-8277-4c85-89c3-cffbafe61fa4	null	{"id": "8a5f437f-8277-4c85-89c3-cffbafe61fa4", "email": "negi.yaten+wms_manager_02@gmail.com", "first_name": "wms manger", "last_name": "two", "display_name": null, "phone": null, "avatar_url": null, "user_type": "user", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": "2026-06-12T06:28:39.335775+00:00", "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-12T06:28:39.340587", "updated_at": "2026-06-12T06:28:39.340590"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 06:28:39.344765+00
1d34d264-790e-412e-9677-855b585c5624	\N	\N	UPDATE	users	8a5f437f-8277-4c85-89c3-cffbafe61fa4	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-12T06:28:56.575541+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 06:28:56.581495+00
56d2c0cf-b9b0-479b-8980-8bda5b992b29	\N	\N	CREATE	users	04aa34fe-f4ee-4f55-8624-b7e3665fd137	null	{"id": "04aa34fe-f4ee-4f55-8624-b7e3665fd137", "email": "negi.yaten+wms_manager_03@gmail.com", "first_name": "wms manager", "last_name": "transit", "display_name": null, "phone": null, "avatar_url": null, "user_type": "user", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": "2026-06-12T08:28:00.699345+00:00", "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-12T08:28:00.704095", "updated_at": "2026-06-12T08:28:00.704098"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 08:28:00.719201+00
208fbf8c-90c8-4e1f-8584-d2bf51571ef8	\N	\N	UPDATE	users	04aa34fe-f4ee-4f55-8624-b7e3665fd137	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-12T08:28:31.081128+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 08:28:31.087064+00
33c2e98a-aab9-4fd0-8d27-579209a4c404	\N	\N	CREATE	users	57f8a2b2-3866-468f-b68d-d4950df43d1c	null	{"id": "57f8a2b2-3866-468f-b68d-d4950df43d1c", "email": "negi.yaten+wms_manager_04@gmail.com", "first_name": "wms Manager four", "last_name": "transit", "display_name": null, "phone": null, "avatar_url": null, "user_type": "user", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": "2026-06-12T08:41:09.116143+00:00", "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-12T08:41:09.119744", "updated_at": "2026-06-12T08:41:09.119748"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 08:41:09.125641+00
a78799e2-be13-4680-98fe-6b7947bf464f	\N	\N	UPDATE	users	57f8a2b2-3866-468f-b68d-d4950df43d1c	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-12T08:41:26.607044+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 08:41:26.6104+00
e1f48014-1e65-4d78-bfb0-cad3b140970d	\N	\N	CREATE	users	d842127f-7520-4612-987f-2faf88b8c0b9	null	{"id": "d842127f-7520-4612-987f-2faf88b8c0b9", "email": "negi.yaten+wms_ppt_admin_01@gmail.com", "first_name": "PPT Wms one", "last_name": "Admin", "display_name": null, "phone": null, "avatar_url": null, "user_type": "user", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": "2026-06-12T12:39:23.810899+00:00", "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-12T12:39:23.817698", "updated_at": "2026-06-12T12:39:23.817703"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 12:39:23.85196+00
278d1399-a822-45ae-a89a-9e4a9e923333	\N	\N	UPDATE	users	d842127f-7520-4612-987f-2faf88b8c0b9	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-12T12:39:46.897670+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 12:39:46.905866+00
19298793-0181-4a49-956b-8501758efa7c	\N	\N	CREATE	users	f4c9c4a8-ad3f-4e90-afaf-f437b8644585	null	{"id": "f4c9c4a8-ad3f-4e90-afaf-f437b8644585", "email": "negi.yaten+wms_ppt_manager_01@gmail.com", "first_name": "PPT Wms one", "last_name": "Manager", "display_name": null, "phone": null, "avatar_url": null, "user_type": "user", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": "2026-06-12T12:40:57.077147+00:00", "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-12T12:40:57.079746", "updated_at": "2026-06-12T12:40:57.079750"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 12:40:57.08267+00
0304df17-6403-4fd0-8826-9cfbc19e0379	\N	\N	UPDATE	users	f4c9c4a8-ad3f-4e90-afaf-f437b8644585	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-12T12:41:09.810197+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 12:41:09.816943+00
d0cbef4f-27bc-4bd4-b0a1-eaa49f0bdf1b	\N	\N	UPDATE	users	d842127f-7520-4612-987f-2faf88b8c0b9	{"last_login_at": "2026-06-12T12:39:46.897670+00:00"}	{"last_login_at": "2026-06-12T12:42:54.738767+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 12:42:54.743446+00
30000e66-4111-4d6e-9c3f-71d309200eeb	\N	\N	UPDATE	users	f4c9c4a8-ad3f-4e90-afaf-f437b8644585	{"last_login_at": "2026-06-12T12:41:09.810197+00:00"}	{"last_login_at": "2026-06-12T12:53:44.111834+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 12:53:44.114872+00
de68832e-4239-43ae-81a1-5920593dadc1	\N	\N	UPDATE	users	f4c9c4a8-ad3f-4e90-afaf-f437b8644585	{"last_login_at": "2026-06-12T12:53:44.111834+00:00"}	{"last_login_at": "2026-06-12T14:29:01.076255+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-12 14:29:01.080986+00
2cc3a81d-36f2-48cd-9f7b-6e0017ff7c42	\N	\N	UPDATE	users	d842127f-7520-4612-987f-2faf88b8c0b9	{"last_login_at": "2026-06-12T12:42:54.738767+00:00"}	{"last_login_at": "2026-06-12T14:33:34.712284+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-12 14:33:34.726101+00
c8781b27-9df1-4bbe-8723-9e804463fe8d	\N	\N	UPDATE	users	8a5f437f-8277-4c85-89c3-cffbafe61fa4	{"last_login_at": "2026-06-12T06:28:56.575541+00:00"}	{"last_login_at": "2026-06-15T12:08:18.905464+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-15 12:08:19.224963+00
1ae8d2c2-e910-44f1-868d-93c8d14f6f8d	\N	\N	UPDATE	users	d842127f-7520-4612-987f-2faf88b8c0b9	{"last_login_at": "2026-06-12T14:33:34.712284+00:00"}	{"last_login_at": "2026-06-15T13:06:37.105201+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-15 13:06:37.134767+00
6d48ce67-6a24-4c38-9580-96714dcf5fbe	\N	\N	UPDATE	users	8a5f437f-8277-4c85-89c3-cffbafe61fa4	{"last_login_at": "2026-06-15T12:08:18.905464+00:00"}	{"last_login_at": "2026-06-17T11:01:54.153258+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-17 11:01:54.156443+00
c29c9d8c-ce08-4d48-b875-a7e7c7cb1e78	\N	\N	UPDATE	users	fbfd7719-159d-4751-ba13-5fc9e35fa470	{"last_login_at": "2026-06-17T10:59:39.180455+00:00"}	{"last_login_at": "2026-06-17T12:55:36.585557+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-17 12:55:36.643563+00
8ae783cb-778a-4b32-b720-60c714a64263	\N	\N	UPDATE	users	fbfd7719-159d-4751-ba13-5fc9e35fa470	{"last_login_at": "2026-06-17T12:55:36.585557+00:00"}	{"last_login_at": "2026-06-17T17:20:19.866767+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-17 17:20:19.937876+00
54ff6490-87a1-4fc4-9e3b-cabaf446de89	\N	\N	UPDATE	users	fbfd7719-159d-4751-ba13-5fc9e35fa470	{"last_login_at": "2026-06-17T17:20:19.866767+00:00"}	{"last_login_at": "2026-06-18T09:59:01.717490+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-18 09:59:04.94899+00
59835129-05a9-4f92-b7e8-689c0f657d10	\N	\N	UPDATE	users	fbfd7719-159d-4751-ba13-5fc9e35fa470	{"last_login_at": "2026-06-18T09:59:01.717490+00:00"}	{"last_login_at": "2026-06-18T12:34:38.530761+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-18 12:34:38.585529+00
9c807b2b-1c46-4295-ab38-d1bd2d00f45e	\N	\N	CREATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	null	{"id": "ffae90be-8ac1-447d-bca1-90cace2ff429", "email": "PrestigeTTK@gmail.com", "first_name": "Prestige", "last_name": "TTK", "display_name": "Prestige TTK", "phone": "+919988776633", "avatar_url": null, "user_type": "user", "status": "pending", "is_active": "True", "email_verified": "False", "email_verified_at": null, "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-19T04:07:17.543297", "updated_at": "2026-06-19T04:07:17.543301"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 04:07:17.576272+00
9b3425fa-b1eb-43f7-99af-5c4d2f073895	ffae90be-8ac1-447d-bca1-90cace2ff429	\N	CREATE	organizations	b5863590-fb53-4d22-a956-956aafc1c13e	null	{"id": "b5863590-fb53-4d22-a956-956aafc1c13e", "name": "Prestige TTK", "slug": "prestige-ttk", "display_name": "Prestige TTK", "description": "This is manufacturer company", "email": "PrestigeTTK@gmail.com", "phone": "+919988776633", "website": "https://TTK@prestige.com", "address_line1": null, "address_line2": null, "city": null, "state": null, "postal_code": null, "country": "IN", "organization_type": "business", "industry": "Manufacturing", "tax_id": null, "base_currency": "INR", "logo_url": null, "primary_color": null, "domain": null, "sso_enabled": "False", "sso_provider": null, "sso_config": null, "status": "active", "is_active": "True", "billing_status": "trial", "subscription_start_date": "2026-06-19", "subscription_end_date": null, "trial_end_date": "2026-07-19", "max_users": "10", "max_credits": "1000", "billing_contact_email": null, "billing_cycle": "monthly", "customer_since": "2026-06-19T04:08:29.745528+00:00", "last_billed_date": null, "next_billing_date": "2026-08-18", "parent_organization_id": null, "owner_id": "ffae90be-8ac1-447d-bca1-90cace2ff429", "settings": "{}", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-19T04:08:29.749374", "updated_at": "2026-06-19T04:08:29.749378"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 04:08:29.757354+00
76c95ef3-8ab3-4618-8e51-93f40521ffe7	\N	\N	CREATE	users	171e65d7-60c5-451b-a5b6-c174fbc842c1	null	{"id": "171e65d7-60c5-451b-a5b6-c174fbc842c1", "email": "negi.yaten+ecity_admin@gmail.com", "first_name": "Admin", "last_name": "eCity", "display_name": null, "phone": null, "avatar_url": null, "user_type": "user", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": "2026-06-19T04:18:23.867855+00:00", "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-19T04:18:23.871323", "updated_at": "2026-06-19T04:18:23.871326"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 04:18:23.876991+00
ec770bb2-a0be-43c5-a915-a2a339937061	\N	\N	UPDATE	users	171e65d7-60c5-451b-a5b6-c174fbc842c1	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-19T04:18:36.907189+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 04:18:36.913518+00
7bfd7f5e-f78c-4d12-b3e3-debd1e612c63	\N	\N	CREATE	users	82b119e8-6a0d-41f9-9b01-0f34c3cc29b9	null	{"id": "82b119e8-6a0d-41f9-9b01-0f34c3cc29b9", "email": "negi.yaten+ecity_manager@gmail.com", "first_name": "manger", "last_name": "eCity", "display_name": null, "phone": null, "avatar_url": null, "user_type": "user", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": "2026-06-19T04:19:17.489847+00:00", "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-19T04:19:17.494072", "updated_at": "2026-06-19T04:19:17.494082"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-19 04:19:17.50142+00
1823cbb2-af2b-426c-80b0-e41eefe9ce27	\N	\N	UPDATE	users	82b119e8-6a0d-41f9-9b01-0f34c3cc29b9	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-19T04:19:34.502151+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-19 04:19:34.507808+00
00cffcb6-f639-4bff-94f4-65eb29e66b7d	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-19T04:43:27.313495+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 04:43:27.321091+00
5985018b-9173-4270-bd48-a3eb1e382e71	\N	\N	UPDATE	users	171e65d7-60c5-451b-a5b6-c174fbc842c1	{"last_login_at": "2026-06-19T04:18:36.907189+00:00"}	{"last_login_at": "2026-06-19T04:44:35.461486+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 04:44:35.469714+00
07e52bb9-c812-4bcf-bb76-c1d7381cef84	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-19T04:43:27.313495+00:00"}	{"last_login_at": "2026-06-19T04:46:45.270924+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 04:46:45.284623+00
cb364582-6312-44de-b97d-54c9af64f1bf	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-19T04:46:45.270924+00:00"}	{"last_login_at": "2026-06-19T05:46:03.017183+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 05:46:03.063101+00
1d2c5773-0dc1-4299-a796-441e72199ae6	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-19T05:46:03.017183+00:00"}	{"last_login_at": "2026-06-19T10:10:08.868091+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 10:10:08.91609+00
ad4ab195-618f-4694-bdfb-550a4bfb5c81	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-19T10:10:08.868091+00:00"}	{"last_login_at": "2026-06-19T11:15:22.196519+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 11:15:22.290249+00
5ea00c95-120e-41b1-a185-c2cb61960661	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-19T11:15:22.196519+00:00"}	{"last_login_at": "2026-06-19T14:12:46.564484+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 14:12:46.584237+00
43474e4c-2200-4b7c-8616-f4ebae72ed1f	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-19T14:12:46.564484+00:00"}	{"last_login_at": "2026-06-19T15:26:18.997748+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 15:26:19.016104+00
11b3e63d-b074-4460-946f-8907bd9492b9	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-19T15:26:18.997748+00:00"}	{"last_login_at": "2026-06-22T03:44:47.585778+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-22 03:44:47.72002+00
499bfb3c-afb2-4e60-96aa-4e71433677e0	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-22T03:44:47.585778+00:00"}	{"last_login_at": "2026-06-22T03:53:47.013332+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-22 03:53:47.030767+00
836d240c-e1e2-4b8f-ae46-255bec9de07a	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-22T03:53:47.013332+00:00"}	{"last_login_at": "2026-06-22T05:08:34.050004+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-22 05:08:34.093953+00
04eb4b71-50c4-4f0c-a77e-874dddf5cb04	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-22T05:08:34.050004+00:00"}	{"last_login_at": "2026-06-22T09:32:17.881623+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-22 09:32:19.101348+00
333c5f46-c025-43d5-a4f9-89ed6e3f097d	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-22T09:32:17.881623+00:00"}	{"last_login_at": "2026-06-22T10:10:15.160943+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-22 10:10:15.181185+00
2021aae8-cb67-486e-92d0-cea653c3c293	\N	\N	UPDATE	users	171e65d7-60c5-451b-a5b6-c174fbc842c1	{"last_login_at": "2026-06-19T04:44:35.461486+00:00"}	{"last_login_at": "2026-06-22T10:14:25.666280+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-22 10:14:25.669616+00
73fdefa2-9b8a-4374-a847-0baf76559543	171e65d7-60c5-451b-a5b6-c174fbc842c1	b5863590-fb53-4d22-a956-956aafc1c13e	CREATE	users	f2d43104-b97c-4554-a68a-b8ef9bb11dd1	null	{"id": "f2d43104-b97c-4554-a68a-b8ef9bb11dd1", "email": "yaten.s@gmail.com", "first_name": "yaten", "last_name": "singh", "display_name": "yaten singh", "phone": "0000000000", "avatar_url": null, "user_type": "warehouse_worker", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": null, "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "qr_code": "WRK-5LYXXIH0Q46E", "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{'login_username': 'yaten.singh', 'employee_id': 'W-MQP3CWM6'}", "deleted_at": null, "created_at": "2026-06-22T10:47:26.078723", "updated_at": "2026-06-22T10:47:26.078726"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-22 10:47:26.09063+00
0f1449f5-3d4b-4765-af14-416eb32bed25	171e65d7-60c5-451b-a5b6-c174fbc842c1	b5863590-fb53-4d22-a956-956aafc1c13e	UPDATE	users	f2d43104-b97c-4554-a68a-b8ef9bb11dd1	{"email": "yaten.s@gmail.com"}	{"email": "yaten@gmail.com"}	["email"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-22 10:51:14.313422+00
d1364483-56af-4b25-9876-0c54b334290a	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-22T10:10:15.160943+00:00"}	{"last_login_at": "2026-06-22T14:20:11.207066+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-22 14:20:11.232535+00
c0799603-879b-40c8-9a78-914427220367	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-22T14:20:11.207066+00:00"}	{"last_login_at": "2026-06-25T17:11:07.275004+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 17:11:07.377099+00
bfbc896d-7acf-4307-a579-7e453e08bf02	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-25T17:11:07.275004+00:00"}	{"last_login_at": "2026-06-25T17:41:03.306949+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 17:41:03.318713+00
23f9499c-d75f-4290-98c3-95fb6dfdd6fb	\N	\N	UPDATE	users	171e65d7-60c5-451b-a5b6-c174fbc842c1	{"last_login_at": "2026-06-22T10:14:25.666280+00:00"}	{"last_login_at": "2026-06-25T17:41:26.735228+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 17:41:26.73966+00
3369648f-78fe-43a4-b2ab-07c40e7ea909	171e65d7-60c5-451b-a5b6-c174fbc842c1	b5863590-fb53-4d22-a956-956aafc1c13e	UPDATE	users	f2d43104-b97c-4554-a68a-b8ef9bb11dd1	{"status": "active", "is_active": "True"}	{"status": "inactive", "is_active": "False"}	["status", "is_active"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 17:42:15.395953+00
e28151d6-88f4-40de-836a-9644176d1454	171e65d7-60c5-451b-a5b6-c174fbc842c1	b5863590-fb53-4d22-a956-956aafc1c13e	CREATE	users	bd097e86-1759-4be1-9312-94e60346dbfd	null	{"id": "bd097e86-1759-4be1-9312-94e60346dbfd", "email": "Ram.singh@gmail.com", "first_name": "Ram", "last_name": "Singh", "display_name": "Ram Singh", "phone": "0000000000", "avatar_url": null, "user_type": "warehouse_worker", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": null, "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "qr_code": "WRK-V8KJFPBZHZ52", "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{'login_username': 'ram.singh', 'employee_id': 'W-MQTSIDP2'}", "deleted_at": null, "created_at": "2026-06-25T17:42:37.021154", "updated_at": "2026-06-25T17:42:37.021157"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 17:42:37.024304+00
21050dcc-0086-4a67-84c5-6c8b57d4c59d	\N	\N	UPDATE	users	bd097e86-1759-4be1-9312-94e60346dbfd	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-25T17:49:57.096564+00:00", "last_login_ip": "49.207.59.41"}	["last_login_at", "last_login_ip"]	49.207.59.41	okhttp/4.12.0	2026-06-25 17:49:57.110413+00
14f46694-878c-4dc4-be39-4a95411ad1e3	\N	\N	UPDATE	users	82b119e8-6a0d-41f9-9b01-0f34c3cc29b9	{"last_login_at": "2026-06-19T04:19:34.502151+00:00"}	{"last_login_at": "2026-06-25T17:56:07.340831+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 17:56:07.348957+00
c9e26766-e208-4c4b-846c-6e583c9a3713	\N	\N	CREATE	users	ca0eabd2-f796-4bd9-935a-47562d0880a4	null	{"id": "ca0eabd2-f796-4bd9-935a-47562d0880a4", "email": "TTK-prestige_ECITY@gmail.com", "first_name": "TTK", "last_name": "eCITY", "display_name": "TTK eCITY", "phone": "+919988776633", "avatar_url": null, "user_type": "user", "status": "pending", "is_active": "True", "email_verified": "False", "email_verified_at": null, "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "qr_code": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-25T18:02:54.815638", "updated_at": "2026-06-25T18:02:54.815643"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 18:02:54.821107+00
189301fd-eb94-49c5-b8d4-f7e72f1a25f8	b9f2eb20-2fd2-4318-a67e-f8796fe1b128	4acc19e3-fa77-463e-86e5-6838912edbf8	CREATE	users	32440aa3-3413-4906-8282-bb860a838f64	null	{"id": "32440aa3-3413-4906-8282-bb860a838f64", "email": "ram.lal@gmail.com", "first_name": "Ram", "last_name": "Lal", "display_name": "Ram Lal", "phone": "0000000000", "avatar_url": null, "user_type": "warehouse_worker", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": null, "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "qr_code": "WRK-ZHH0RV0D6TEM", "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{'login_username': 'ram.lal', 'employee_id': 'W-MQTTQI5N'}", "deleted_at": null, "created_at": "2026-06-25T18:16:55.751377", "updated_at": "2026-06-25T18:16:55.751381"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 18:16:55.755826+00
9a0f8451-754a-4d32-9910-0637e1862406	ca0eabd2-f796-4bd9-935a-47562d0880a4	\N	CREATE	organizations	4acc19e3-fa77-463e-86e5-6838912edbf8	null	{"id": "4acc19e3-fa77-463e-86e5-6838912edbf8", "name": "TTK-Prestige_one", "slug": "ttk-prestige-one", "display_name": "TTK-Prestige_one", "description": "", "email": "TTK-prestige_ECITY@gmail.com", "phone": "+919988776633", "website": "https://www.tatasoft.com", "address_line1": null, "address_line2": null, "city": null, "state": null, "postal_code": null, "country": "IN", "organization_type": "startup", "industry": "Finance & Banking", "tax_id": null, "base_currency": "INR", "logo_url": null, "primary_color": null, "domain": null, "sso_enabled": "False", "sso_provider": null, "sso_config": null, "status": "active", "is_active": "True", "billing_status": "trial", "subscription_start_date": "2026-06-25", "subscription_end_date": null, "trial_end_date": "2026-07-25", "max_users": "10", "max_credits": "1000", "billing_contact_email": null, "billing_cycle": "monthly", "customer_since": "2026-06-25T18:03:24.604794+00:00", "last_billed_date": null, "next_billing_date": "2026-08-24", "parent_organization_id": null, "owner_id": "ca0eabd2-f796-4bd9-935a-47562d0880a4", "settings": "{}", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-25T18:03:24.611313", "updated_at": "2026-06-25T18:03:24.611316"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 18:03:24.62136+00
4fd44f3d-6734-4217-86a5-030768f73190	\N	\N	CREATE	users	b9f2eb20-2fd2-4318-a67e-f8796fe1b128	null	{"id": "b9f2eb20-2fd2-4318-a67e-f8796fe1b128", "email": "devnegikec+ecity_ttk_manager@gmail.com", "first_name": "Ecity TTK Manager", "last_name": "SN", "display_name": null, "phone": null, "avatar_url": null, "user_type": "user", "status": "active", "is_active": "True", "email_verified": "True", "email_verified_at": "2026-06-25T18:09:12.363536+00:00", "mfa_enabled": "False", "mfa_secret": null, "mfa_backup_codes": null, "last_login_at": null, "last_login_ip": null, "failed_login_attempts": "0", "locked_until": null, "qr_code": null, "preferences": "{}", "timezone": "UTC", "language": "en", "extra_data": "{}", "deleted_at": null, "created_at": "2026-06-25T18:09:12.369981", "updated_at": "2026-06-25T18:09:12.369986"}	null	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 18:09:12.373711+00
0e97cd75-9951-4c20-886b-92149c207581	\N	\N	UPDATE	users	ffae90be-8ac1-447d-bca1-90cace2ff429	{"last_login_at": "2026-06-25T17:41:03.306949+00:00"}	{"last_login_at": "2026-06-25T18:10:19.902480+00:00"}	["last_login_at"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 18:10:19.91266+00
08779514-9bdf-4ae6-97bf-2374ce17c13b	\N	\N	UPDATE	users	b9f2eb20-2fd2-4318-a67e-f8796fe1b128	{"last_login_at": "2026-06-25T18:16:12.986364+00:00", "last_login_ip": "172.18.0.1"}	{"last_login_at": "2026-06-25T18:20:29.058075+00:00", "last_login_ip": "49.207.59.41"}	["last_login_at", "last_login_ip"]	49.207.59.41	okhttp/4.12.0	2026-06-25 18:20:29.06199+00
8c395c59-7e5c-40f0-a79a-e3cbc6ab0df5	\N	\N	UPDATE	users	ca0eabd2-f796-4bd9-935a-47562d0880a4	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-25T18:15:36.105821+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 18:15:36.114877+00
0ef9520d-a80e-402c-84a7-1f6ecb69d29e	\N	\N	UPDATE	users	b9f2eb20-2fd2-4318-a67e-f8796fe1b128	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-25T18:16:12.986364+00:00", "last_login_ip": "172.18.0.1"}	["last_login_at", "last_login_ip"]	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 18:16:12.991481+00
58823d62-9e4c-4b1e-8a22-9da33a8c1e57	\N	\N	UPDATE	users	32440aa3-3413-4906-8282-bb860a838f64	{"last_login_at": null, "last_login_ip": null}	{"last_login_at": "2026-06-25T18:17:09.947360+00:00", "last_login_ip": "49.207.59.41"}	["last_login_at", "last_login_ip"]	49.207.59.41	okhttp/4.12.0	2026-06-25 18:17:09.951721+00
\.

--
-- Data for Name: invitations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.invitations (id, organization_id, email, first_name, last_name, role_id, team_ids, invited_by_id, token_hash, status, expires_at, accepted_at, accepted_user_id, created_at, message, extra_data) FROM stdin;
b71f5a3d-92ab-48ea-863c-689b68c877a8	ddfad734-9afb-497b-81a3-ffc85caec590	negi.yaten+wms_manager_01@gmail.com	Prestige	Manager	42146f28-9b13-4af1-acd7-9d3da69b15d0	[]	fbfd7719-159d-4751-ba13-5fc9e35fa470	c971ade5b62c784924915a9d1ed11245ef72084c0f54f92dd6acc6d12d2d30c6	accepted	2026-06-18 19:19:57.377761+00	2026-06-11 19:21:37.77302+00	6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	2026-06-11 19:11:50.031541+00	\N	{"warehouse_ids": ["357db81b-3b90-47de-912b-ac7af96b50e2"], "warehouse_role": "manager"}
6fcc9266-e34a-4226-8bf2-e3d504327559	ddfad734-9afb-497b-81a3-ffc85caec590	negi.yaten+user1@gmail.com	Lovleen	Rawat	42146f28-9b13-4af1-acd7-9d3da69b15d0	[]	fbfd7719-159d-4751-ba13-5fc9e35fa470	199ec76668568df25d205c86c504f47bbfd6378a7cc55a4ec8230614840baacf	accepted	2026-06-19 04:47:55.462699+00	2026-06-12 04:49:52.629038+00	c0bf7fb1-687d-47cf-b020-b5c6007b589d	2026-06-12 04:47:55.465873+00	\N	{"warehouse_ids": ["357db81b-3b90-47de-912b-ac7af96b50e2", "0d45c37e-2b80-4967-9ff1-e65ededb86a2"], "warehouse_role": "manager"}
9b7ebab0-fdf9-45f3-b98e-bfef702cc1ca	ddfad734-9afb-497b-81a3-ffc85caec590	negi.yaten+wms_manager_02@gmail.com	wms manger	two	42146f28-9b13-4af1-acd7-9d3da69b15d0	[]	fbfd7719-159d-4751-ba13-5fc9e35fa470	31641015930f7d304c95dff3deabc77c6bd26a14bd8bd892a4b3d8fd4261db4f	accepted	2026-06-19 06:27:45.463614+00	2026-06-12 06:28:39.357299+00	8a5f437f-8277-4c85-89c3-cffbafe61fa4	2026-06-12 06:27:45.481468+00	\N	{"warehouse_ids": ["0d45c37e-2b80-4967-9ff1-e65ededb86a2"], "warehouse_role": "manager"}
7161995c-1963-45f5-8ff1-9fbaa7b283ac	ddfad734-9afb-497b-81a3-ffc85caec590	negi.yaten+wms_manager_03@gmail.com	wms manager	transit	42146f28-9b13-4af1-acd7-9d3da69b15d0	[]	fbfd7719-159d-4751-ba13-5fc9e35fa470	3bb2c6435b5bc5de58ce512a83c78841122c8bb52446edb2baf1f5fa61669a84	accepted	2026-06-19 08:27:18.509489+00	2026-06-12 08:28:00.736508+00	04aa34fe-f4ee-4f55-8624-b7e3665fd137	2026-06-12 08:27:18.519046+00	\N	{"warehouse_ids": ["0d45c37e-2b80-4967-9ff1-e65ededb86a2"], "warehouse_role": "manager"}
be11c319-eea4-4fd3-b666-d9075b4b95d2	ddfad734-9afb-497b-81a3-ffc85caec590	negi.yaten+wms_manager_04@gmail.com	wms Manager four	transit	42146f28-9b13-4af1-acd7-9d3da69b15d0	[]	fbfd7719-159d-4751-ba13-5fc9e35fa470	d64cb2f8d0ad8450df1707cd1a56a259f906afcff765a1cc07af6ba7ddca8648	accepted	2026-06-19 08:40:37.77857+00	2026-06-12 08:41:09.140346+00	57f8a2b2-3866-468f-b68d-d4950df43d1c	2026-06-12 08:40:37.7846+00	\N	{"warehouse_ids": ["0d45c37e-2b80-4967-9ff1-e65ededb86a2"], "warehouse_role": "manager"}
aab2e7f8-a88c-4e1b-b441-88b6d4273684	ddfad734-9afb-497b-81a3-ffc85caec590	negi.yaten+wms_ppt_admin_01@gmail.com	PPT Wms one	Admin	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	[]	fbfd7719-159d-4751-ba13-5fc9e35fa470	2363c9d4631c22aa21c9d52d9bb84b877c6f5a9d381f200ddc57da88a46f1b8e	accepted	2026-06-19 12:36:37.558932+00	2026-06-12 12:39:23.877524+00	d842127f-7520-4612-987f-2faf88b8c0b9	2026-06-12 12:36:37.580515+00	\N	{"warehouse_ids": [], "warehouse_role": "supervisor"}
4440ef89-30ec-450b-b523-459bbbd9a49f	ddfad734-9afb-497b-81a3-ffc85caec590	negi.yaten+wms_ppt_manager_01@gmail.com	PPT Wms one	Manager	42146f28-9b13-4af1-acd7-9d3da69b15d0	[]	fbfd7719-159d-4751-ba13-5fc9e35fa470	cc45afe1a88a3b3d2e7d13f8b00d0a85b44abc6859778daefd60d95822f09d03	accepted	2026-06-19 12:37:49.851402+00	2026-06-12 12:40:57.096+00	f4c9c4a8-ad3f-4e90-afaf-f437b8644585	2026-06-12 12:37:49.853021+00	\N	{"warehouse_ids": ["0d45c37e-2b80-4967-9ff1-e65ededb86a2"], "warehouse_role": "manager"}
1f217173-48bf-4c7b-9e95-96882c0be8b3	b5863590-fb53-4d22-a956-956aafc1c13e	negi.yaten+ecity_admin@gmail.com	Admin	eCity	d51883b9-2184-4390-8cf7-26e4dfd4acde	[]	ffae90be-8ac1-447d-bca1-90cace2ff429	028efde4ae8f6c01e36e91ef6baa6538107d38d6f68ade3094fdad3528153dc2	accepted	2026-06-26 04:14:08.004066+00	2026-06-19 04:18:23.891823+00	171e65d7-60c5-451b-a5b6-c174fbc842c1	2026-06-19 04:14:08.008206+00	\N	{"warehouse_ids": [], "warehouse_role": "supervisor"}
4ac31d64-799d-41e4-9453-ebc078915724	b5863590-fb53-4d22-a956-956aafc1c13e	negi.yaten+ecity_manager@gmail.com	manger	eCity	ebde1aad-a955-4c5c-bde3-3c04f59a8207	[]	ffae90be-8ac1-447d-bca1-90cace2ff429	6f721dbffb9f9eca328f51566ebf81d9dc663acce1cc56138b1a73cc794555e2	accepted	2026-06-26 04:14:47.478096+00	2026-06-19 04:19:17.522477+00	82b119e8-6a0d-41f9-9b01-0f34c3cc29b9	2026-06-19 04:14:47.479604+00	\N	{"warehouse_ids": ["8c242462-120e-46bc-83f4-a536bd8f7ea3"], "warehouse_role": "manager"}
573de646-c17f-4897-834d-295ed2ba46be	4acc19e3-fa77-463e-86e5-6838912edbf8	devnegikec+ecity_ttk_manager@gmail.com	Ecity TTK Manager	SN	22817e25-becd-4837-90cf-7e0802b5446c	[]	ca0eabd2-f796-4bd9-935a-47562d0880a4	6a57a5c9e95049f1f875e63c92936164a341cb4b12b035806a882b8ef148bf71	accepted	2026-07-02 18:07:22.194208+00	2026-06-25 18:09:12.393018+00	b9f2eb20-2fd2-4318-a67e-f8796fe1b128	2026-06-25 18:07:22.203052+00	\N	{"warehouse_ids": ["173fcf5b-f277-485c-bfa3-de4a1240ca5b"], "warehouse_role": "manager"}
\.

--
-- Data for Name: organizations; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.organizations (id, name, slug, display_name, description, email, phone, website, address_line1, address_line2, city, state, postal_code, country, organization_type, industry, tax_id, logo_url, primary_color, domain, sso_enabled, sso_provider, sso_config, status, is_active, owner_id, settings, extra_data, deleted_at, created_at, updated_at, base_currency, billing_status, subscription_start_date, subscription_end_date, seat_limit, credit_limit, trial_end_date, max_users, max_credits, billing_contact_email, billing_cycle, customer_since, last_billed_date, next_billing_date, parent_organization_id) FROM stdin;
05397b7b-95bb-4560-b3d0-dff21b3db1ee	system Org	system-org	system Org	asdfasdfasdfasdfasdfasdf	negi.yaten+Raj0078@gmail.com	+916565432562	https://www.tatasoft.com	\N	\N	\N	\N	\N	IN	business	Healthcare	\N	\N	\N	\N	f	\N	\N	active	t	20c0587a-7145-48e0-9471-caae8de8fe4d	{}	{}	\N	2026-06-07 05:20:15.623135+00	2026-06-07 05:48:43.350231+00	INR	trial	2026-06-07 00:00:00+00	\N	10	1000	2026-07-07 00:00:00	10	1000	\N	monthly	2026-06-07 05:20:15.617769+00	\N	2026-08-06 00:00:00	00000000-0000-0000-0000-000000000001
00000000-0000-0000-0000-000000000001	Master Organization	master-organization	Master Organization	Master organization for system administration and B2B billing management	master@horizonsync.com	\N	https://horizonsync.com	\N	\N	San Francisco	CA	\N	USA	master	\N	\N	\N	\N	\N	\N	\N	\N	active	t	\N	\N	\N	\N	2026-06-03 09:46:17.307054+00	2026-07-12 12:28:37.315051+00	USD	active	\N	\N	999999	999999	\N	\N	\N	\N	\N	\N	\N	\N	\N
4acc19e3-fa77-463e-86e5-6838912edbf8	TTK-Prestige_one	ttk-prestige-one	TTK-Prestige_one		TTK-prestige_ECITY@gmail.com	+919988776633	https://www.tatasoft.com	\N	\N	\N	\N	\N	IN	startup	Finance & Banking	\N	\N	\N	\N	f	\N	\N	active	t	ca0eabd2-f796-4bd9-935a-47562d0880a4	{}	{}	\N	2026-06-25 18:03:24.611313+00	2026-07-12 12:28:37.328233+00	INR	trial	2026-06-25 00:00:00+00	\N	10	1000	2026-07-25 00:00:00	10	1000	\N	monthly	2026-06-25 18:03:24.604794+00	\N	2026-08-24 00:00:00	00000000-0000-0000-0000-000000000001
b5863590-fb53-4d22-a956-956aafc1c13e	Prestige TTK	prestige-ttk	Prestige TTK	This is manufacturer company	PrestigeTTK@gmail.com	+919988776633	https://TTK@prestige.com	\N	\N	\N	\N	\N	IN	business	Manufacturing	\N	\N	\N	\N	f	\N	\N	active	t	ffae90be-8ac1-447d-bca1-90cace2ff429	{}	{}	\N	2026-06-19 04:08:29.749374+00	2026-06-19 05:43:23.784094+00	INR	trial	2026-06-19 00:00:00+00	\N	10	1000	2026-07-19 00:00:00	10	1000	\N	monthly	2026-06-19 04:08:29.745528+00	\N	2026-08-18 00:00:00	00000000-0000-0000-0000-000000000001
ddfad734-9afb-497b-81a3-ffc85caec590	WMS manager 	wms-manager	WMS manager 	asdfasdfasdfasdf	wmsTesting@gmail.com	+916622334423	https://www.flipsalt12.com	\N	\N	\N	\N	\N	IN	individual	Healthcare	\N	\N	\N	\N	f	\N	\N	active	t	fbfd7719-159d-4751-ba13-5fc9e35fa470	{}	{}	\N	2026-06-11 17:54:13.801057+00	2026-06-11 18:26:11.138011+00	INR	trial	2026-06-11 00:00:00+00	\N	10	1000	2026-07-11 00:00:00	10	1000	\N	monthly	2026-06-11 17:54:13.797086+00	\N	2026-08-10 00:00:00	00000000-0000-0000-0000-000000000001
\.

--
-- Data for Name: otp_verifications; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.otp_verifications (id, organization_id, otp_type, target, otp_code, is_verified, verified_at, expires_at, attempts, ip_address, created_at) FROM stdin;
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
eae0a88d-d74e-4c34-b4e4-0086a02b9ea6	system_admin.master	Master System Administrator	Full system access with all permissions (*.*)	all	manage	admin	system_admin	t	{}	2026-06-03 09:46:16.594465+00	2026-06-03 09:46:16.594465+00
1bd5a7dc-4da2-46eb-86bd-0c94d3d1a75c	system_admin.users	Cross-Organization User Management	User management across all organizations	user	manage	admin	system_admin	t	{}	2026-06-03 09:46:16.594465+00	2026-06-03 09:46:16.594465+00
aa92cda2-04af-47e3-a4a4-e8514a2984d4	system_admin.organizations	Organization Management	Full organization management including deactivation	organization	manage	admin	system_admin	t	{}	2026-06-03 09:46:16.594465+00	2026-06-03 09:46:16.594465+00
89e15d5b-bb0b-47cf-9e7e-e6bebe859fd2	system_admin.billing	Billing & Invoice Management	Cross-org invoice and payment management	all	manage	admin	system_admin	t	{}	2026-06-03 09:46:16.594465+00	2026-06-03 09:46:16.594465+00
7bb5df34-93cd-4da4-9822-ef0686a78535	system_admin.reporting	Analytics & Reporting	System-wide analytics and reporting access	report	manage	admin	system_admin	t	{}	2026-06-03 09:46:16.594465+00	2026-06-03 09:46:16.594465+00
046f23e3-dc38-4c84-9036-1f0192d29f90	user.invite	Invite User	Invite users to the organization	user	invite	identity	user_management	t	{}	2026-06-03 09:46:16.594465+00	2026-06-03 09:46:16.594465+00
7208ac08-6e96-4965-a5ac-80c0505039af	invitation.create	Create Invitation	Create invitation records for new users	invitation	create	identity	user_management	t	{}	2026-06-03 09:46:16.594465+00	2026-06-03 09:46:16.594465+00
6541d4db-a4d4-4a24-b2d3-1a047906972a	organization.read	Organization Read	\N	organization	read	identity	\N	t	{}	2026-06-03 09:46:27.352662+00	2026-06-03 09:46:27.352662+00
4fc1625b-8043-4011-be8c-494792476cb5	organization.create	Organization Create	\N	organization	create	identity	\N	t	{}	2026-06-03 09:46:27.352662+00	2026-06-03 09:46:27.352662+00
e344c439-3e1d-4850-83d6-0806f06b1b70	organization.update	Organization Update	\N	organization	update	identity	\N	t	{}	2026-06-03 09:46:27.352662+00	2026-06-03 09:46:27.352662+00
0131fe05-c8dc-4bf2-b74d-f9b3df48d05a	organization.delete	Organization Delete	\N	organization	delete	identity	\N	t	{}	2026-06-03 09:46:27.352662+00	2026-06-03 09:46:27.352662+00
af2cdc8f-15d8-416b-abbd-722c8e146e40	organization.manage	Organization Manage	\N	organization	manage	identity	\N	t	{}	2026-06-03 09:46:27.352662+00	2026-06-03 09:46:27.352662+00
4e857568-7e03-4f89-a068-4d83b2a57d31	system_admin.users_read	System Admin Users Read	\N	user	read	system_admin	\N	t	{}	2026-06-07 05:18:24.795137+00	2026-06-07 05:18:24.795141+00
d78e9127-8054-4367-bac2-001c485338ed	system_admin.users_create	System Admin Users Create	\N	user	create	system_admin	\N	t	{}	2026-06-07 05:18:24.800127+00	2026-06-07 05:18:24.800129+00
17f45225-074c-42a7-8ce3-ad3d40f24b56	system_admin.users_update	System Admin Users Update	\N	user	update	system_admin	\N	t	{}	2026-06-07 05:18:24.802937+00	2026-06-07 05:18:24.80294+00
587b00df-581d-4ae2-a19e-2e7da1c1c908	system_admin.users_delete	System Admin Users Delete	\N	user	delete	system_admin	\N	t	{}	2026-06-07 05:18:24.806129+00	2026-06-07 05:18:24.806133+00
3db92f5f-44a8-4c30-a889-7b6c5c15636f	system_admin.users_manage	System Admin Users Manage	\N	user	manage	system_admin	\N	t	{}	2026-06-07 05:18:24.808956+00	2026-06-07 05:18:24.808958+00
40ad9d9a-2a44-4a25-b7e8-aaf69180973d	system_admin.organizations_read	System Admin Organizations Read	\N	organization	read	system_admin	\N	t	{}	2026-06-07 05:18:24.811554+00	2026-06-07 05:18:24.811556+00
4914a0fc-4e1d-47df-9a26-6dfdcd05d6d7	system_admin.organizations_create	System Admin Organizations Create	\N	organization	create	system_admin	\N	t	{}	2026-06-07 05:18:24.814206+00	2026-06-07 05:18:24.814208+00
7a90d4d7-2a2f-4c9b-a63d-402e7200b3e8	system_admin.organizations_update	System Admin Organizations Update	\N	organization	update	system_admin	\N	t	{}	2026-06-07 05:18:24.817099+00	2026-06-07 05:18:24.817102+00
0f90e9f7-e997-4fbf-9453-854356a1d3a6	system_admin.organizations_delete	System Admin Organizations Delete	\N	organization	delete	system_admin	\N	t	{}	2026-06-07 05:18:24.819757+00	2026-06-07 05:18:24.81976+00
00d226de-caad-494e-8e1e-62e1082ab1f7	system_admin.organizations_manage	System Admin Organizations Manage	\N	organization	manage	system_admin	\N	t	{}	2026-06-07 05:18:24.822985+00	2026-06-07 05:18:24.822988+00
9427ed61-ab76-422c-aacb-f6084021fdb5	system_admin.billing_read	System Admin Billing Read	\N	billing	read	system_admin	\N	t	{}	2026-06-07 05:18:24.825739+00	2026-06-07 05:18:24.825741+00
490d109c-b126-450d-a517-7e6a1f996a60	system_admin.billing_create	System Admin Billing Create	\N	billing	create	system_admin	\N	t	{}	2026-06-07 05:18:24.828398+00	2026-06-07 05:18:24.828401+00
016ec902-3bb8-4078-83c7-ccbdc5506b87	system_admin.billing_update	System Admin Billing Update	\N	billing	update	system_admin	\N	t	{}	2026-06-07 05:18:24.831187+00	2026-06-07 05:18:24.831189+00
255b36cc-883d-415f-b816-0e561b459ed0	system_admin.billing_delete	System Admin Billing Delete	\N	billing	delete	system_admin	\N	t	{}	2026-06-07 05:18:24.833778+00	2026-06-07 05:18:24.833781+00
dc8eb2b9-9a38-417b-9660-9c87f7bf30e9	system_admin.billing_manage	System Admin Billing Manage	\N	billing	manage	system_admin	\N	t	{}	2026-06-07 05:18:24.836838+00	2026-06-07 05:18:24.836842+00
017c0632-56a1-4941-84af-17f611842d3e	system_admin.reporting_read	System Admin Reporting Read	\N	reporting	read	system_admin	\N	t	{}	2026-06-07 05:18:24.83982+00	2026-06-07 05:18:24.839822+00
dc4e8bd1-7179-4dfc-92ca-0821e0978601	system_admin.reporting_create	System Admin Reporting Create	\N	reporting	create	system_admin	\N	t	{}	2026-06-07 05:18:24.842668+00	2026-06-07 05:18:24.842671+00
06e05922-a489-4cf3-bf56-bc3b7182665d	system_admin.reporting_update	System Admin Reporting Update	\N	reporting	update	system_admin	\N	t	{}	2026-06-07 05:18:24.845231+00	2026-06-07 05:18:24.845233+00
ca7af3c2-f6be-472d-b175-8e729ea2b527	system_admin.reporting_delete	System Admin Reporting Delete	\N	reporting	delete	system_admin	\N	t	{}	2026-06-07 05:18:24.847784+00	2026-06-07 05:18:24.847786+00
fe905131-0af7-4ce3-851e-88abb5e80f2c	system_admin.reporting_manage	System Admin Reporting Manage	\N	reporting	manage	system_admin	\N	t	{}	2026-06-07 05:18:24.85034+00	2026-06-07 05:18:24.850342+00
f65f79ec-3ce4-4e98-9b08-76b3901ecb2b	user.read	User Read	\N	user	read	identity	\N	t	{}	2026-06-07 05:18:25.078977+00	2026-06-07 05:18:25.078981+00
b9c7ac87-1fd5-464d-b457-7b2c3fc2493d	user.create	User Create	\N	user	create	identity	\N	t	{}	2026-06-07 05:18:25.078992+00	2026-06-07 05:18:25.078993+00
744b0977-bb86-4ce8-845f-32212f4bfacb	user.update	User Update	\N	user	update	identity	\N	t	{}	2026-06-07 05:18:25.079033+00	2026-06-07 05:18:25.079035+00
d29b40a0-d248-472b-ab21-fadd82fbbf31	user.delete	User Delete	\N	user	delete	identity	\N	t	{}	2026-06-07 05:18:25.079045+00	2026-06-07 05:18:25.079046+00
7084e5f7-575d-43fc-ae8e-b819cc2267ad	user.manage	User Manage	\N	user	manage	identity	\N	t	{}	2026-06-07 05:18:25.079055+00	2026-06-07 05:18:25.079056+00
f49e1f8e-7594-41a7-9299-41ca9e1c98be	role.read	Role Read	\N	role	read	identity	\N	t	{}	2026-06-07 05:18:25.079065+00	2026-06-07 05:18:25.079066+00
6b4ecdcc-5500-4091-8f3e-ecb94f0b7d55	role.create	Role Create	\N	role	create	identity	\N	t	{}	2026-06-07 05:18:25.079075+00	2026-06-07 05:18:25.079076+00
2da18650-9590-40a2-9ec3-e4973a33e3ee	role.update	Role Update	\N	role	update	identity	\N	t	{}	2026-06-07 05:18:25.079084+00	2026-06-07 05:18:25.079085+00
784007a6-c81d-4234-a8bb-8a035f89c06e	role.delete	Role Delete	\N	role	delete	identity	\N	t	{}	2026-06-07 05:18:25.079094+00	2026-06-07 05:18:25.079095+00
95d9f110-e9ba-4f81-b855-882e735b2e2b	role.manage	Role Manage	\N	role	manage	identity	\N	t	{}	2026-06-07 05:18:25.079104+00	2026-06-07 05:18:25.079105+00
23053bbb-3e37-44f5-9682-44c930455fc1	permission.read	Permission Read	\N	permission	read	identity	\N	t	{}	2026-06-07 05:18:25.079113+00	2026-06-07 05:18:25.079115+00
260fc47e-2f93-4b7b-992d-724292a58bcc	permission.manage	Permission Manage	\N	permission	manage	identity	\N	t	{}	2026-06-07 05:18:25.079123+00	2026-06-07 05:18:25.079124+00
2f2e5237-c2d8-4ee8-8dec-72220be5fe51	invitation.read	Invitation Read	\N	invitation	read	identity	\N	t	{}	2026-06-07 05:18:25.079133+00	2026-06-07 05:18:25.079134+00
48c8f3f2-5429-43a4-a821-d698b4372f25	invitation.delete	Invitation Delete	\N	invitation	delete	identity	\N	t	{}	2026-06-07 05:18:25.079142+00	2026-06-07 05:18:25.079144+00
a81ee559-2472-44be-a0a0-37e6eadb3e37	invitation.manage	Invitation Manage	\N	invitation	manage	identity	\N	t	{}	2026-06-07 05:18:25.079152+00	2026-06-07 05:18:25.079153+00
963d9e80-f524-49f6-94a6-1f910578f1ce	customer.read	Customer Read	\N	customer	read	core	\N	t	{}	2026-06-07 05:18:25.079162+00	2026-06-07 05:18:25.079163+00
d2694465-7e98-426e-a6f5-c63ab69594dc	customer.create	Customer Create	\N	customer	create	core	\N	t	{}	2026-06-07 05:18:25.079172+00	2026-06-07 05:18:25.079173+00
1c49abd7-4666-4d3e-9e16-6451d5ee2da9	customer.update	Customer Update	\N	customer	update	core	\N	t	{}	2026-06-07 05:18:25.079186+00	2026-06-07 05:18:25.079188+00
e822e1fe-c906-4792-bcbe-bd68eef67b24	customer.delete	Customer Delete	\N	customer	delete	core	\N	t	{}	2026-06-07 05:18:25.079196+00	2026-06-07 05:18:25.079198+00
1eb99a31-4619-46b0-8756-949feeb6706b	customer.manage	Customer Manage	\N	customer	manage	core	\N	t	{}	2026-06-07 05:18:25.079206+00	2026-06-07 05:18:25.079207+00
5a61f6d0-2a2d-43c2-83be-74bba488860d	supplier.read	Supplier Read	\N	supplier	read	core	\N	t	{}	2026-06-07 05:18:25.079216+00	2026-06-07 05:18:25.079217+00
bd4e5b2c-5d39-4d68-bbe9-94d9096d59f8	supplier.create	Supplier Create	\N	supplier	create	core	\N	t	{}	2026-06-07 05:18:25.079226+00	2026-06-07 05:18:25.079227+00
d1913f08-d669-4f93-ae93-739e9a1dabe6	supplier.update	Supplier Update	\N	supplier	update	core	\N	t	{}	2026-06-07 05:18:25.079235+00	2026-06-07 05:18:25.079237+00
a754f927-efa8-4a93-8eb9-604606f30a53	supplier.delete	Supplier Delete	\N	supplier	delete	core	\N	t	{}	2026-06-07 05:18:25.079245+00	2026-06-07 05:18:25.079246+00
ebe6f958-1247-4f9b-a7a4-18fde80b4c1d	supplier.manage	Supplier Manage	\N	supplier	manage	core	\N	t	{}	2026-06-07 05:18:25.079255+00	2026-06-07 05:18:25.079256+00
c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	item.read	Item Read	\N	item	read	core	\N	t	{}	2026-06-07 05:18:25.079265+00	2026-06-07 05:18:25.079266+00
0290c46c-96ae-493a-873a-8c9acc403ec5	item.create	Item Create	\N	item	create	core	\N	t	{}	2026-06-07 05:18:25.079274+00	2026-06-07 05:18:25.079276+00
24104566-dc21-4fd0-b59a-9d1aa8d94ca2	item.update	Item Update	\N	item	update	core	\N	t	{}	2026-06-07 05:18:25.079284+00	2026-06-07 05:18:25.079285+00
b73c729e-93f7-43ba-b541-3893ea43b341	item.delete	Item Delete	\N	item	delete	core	\N	t	{}	2026-06-07 05:18:25.079294+00	2026-06-07 05:18:25.079295+00
adc60f1e-0b5f-49d5-b494-74c0c9e41953	item.manage	Item Manage	\N	item	manage	core	\N	t	{}	2026-06-07 05:18:25.079304+00	2026-06-07 05:18:25.079305+00
74a06ebe-aab2-47fb-99f8-3bd6c0f683c7	item_group.read	Item Group Read	\N	item_group	read	core	\N	t	{}	2026-06-07 05:18:25.079313+00	2026-06-07 05:18:25.079314+00
dec8f6a3-cca8-4285-ad43-7e2736397e09	item_group.create	Item Group Create	\N	item_group	create	core	\N	t	{}	2026-06-07 05:18:25.079323+00	2026-06-07 05:18:25.079324+00
b0585c03-76e3-4b44-8f53-4e6d12a08bb4	item_group.update	Item Group Update	\N	item_group	update	core	\N	t	{}	2026-06-07 05:18:25.079333+00	2026-06-07 05:18:25.079334+00
4332a62f-ca79-42da-b0f5-6e6a7fd4ecbc	item_group.delete	Item Group Delete	\N	item_group	delete	core	\N	t	{}	2026-06-07 05:18:25.079342+00	2026-06-07 05:18:25.079344+00
465150ba-7e91-4e1f-baa2-edf12c379fe2	item_group.manage	Item Group Manage	\N	item_group	manage	core	\N	t	{}	2026-06-07 05:18:25.079352+00	2026-06-07 05:18:25.079353+00
c565f657-72c6-4f14-9350-079a1b72b65a	warehouse.read	Warehouse Read	\N	warehouse	read	core	\N	t	{}	2026-06-07 05:18:25.079362+00	2026-06-07 05:18:25.079363+00
71558b37-b72f-4b6f-84f5-22518e8f3566	warehouse.create	Warehouse Create	\N	warehouse	create	core	\N	t	{}	2026-06-07 05:18:25.079371+00	2026-06-07 05:18:25.079372+00
9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	warehouse.update	Warehouse Update	\N	warehouse	update	core	\N	t	{}	2026-06-07 05:18:25.079381+00	2026-06-07 05:18:25.079382+00
e243100d-df88-4b91-ae70-717175d3d6aa	warehouse.delete	Warehouse Delete	\N	warehouse	delete	core	\N	t	{}	2026-06-07 05:18:25.079391+00	2026-06-07 05:18:25.079392+00
087ce167-b658-43de-bac7-155c71d30815	warehouse.manage	Warehouse Manage	\N	warehouse	manage	core	\N	t	{}	2026-06-07 05:18:25.0794+00	2026-06-07 05:18:25.079401+00
00739872-28e8-4c95-a25b-40d579702ae8	stock_entry.read	Stock Entry Read	\N	stock_entry	read	core	\N	t	{}	2026-06-07 05:18:25.07941+00	2026-06-07 05:18:25.079411+00
1ffa0d06-4202-468a-885f-23c3a84dadcf	stock_entry.create	Stock Entry Create	\N	stock_entry	create	core	\N	t	{}	2026-06-07 05:18:25.079419+00	2026-06-07 05:18:25.079421+00
9e5e8650-8af9-4ab1-b04d-049ef9b930ee	stock_entry.update	Stock Entry Update	\N	stock_entry	update	core	\N	t	{}	2026-06-07 05:18:25.079429+00	2026-06-07 05:18:25.07943+00
727d5903-9e43-4047-9274-b9722261f397	stock_entry.delete	Stock Entry Delete	\N	stock_entry	delete	core	\N	t	{}	2026-06-07 05:18:25.079439+00	2026-06-07 05:18:25.07944+00
bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	stock_entry.manage	Stock Entry Manage	\N	stock_entry	manage	core	\N	t	{}	2026-06-07 05:18:25.079448+00	2026-06-07 05:18:25.07945+00
bb561768-51b2-4cab-8079-b113796e5268	batch.read	Batch Read	\N	batch	read	core	\N	t	{}	2026-06-07 05:18:25.079465+00	2026-06-07 05:18:25.079466+00
03ccddba-ec05-43ed-a4da-8eec9a5adcf1	batch.create	Batch Create	\N	batch	create	core	\N	t	{}	2026-06-07 05:18:25.079475+00	2026-06-07 05:18:25.079476+00
8da8e17f-20dc-46d6-98bc-02b34063def6	batch.update	Batch Update	\N	batch	update	core	\N	t	{}	2026-06-07 05:18:25.079485+00	2026-06-07 05:18:25.079486+00
5ff658df-647c-4472-86e0-0e735797118a	batch.delete	Batch Delete	\N	batch	delete	core	\N	t	{}	2026-06-07 05:18:25.079495+00	2026-06-07 05:18:25.079496+00
42ec4a29-a314-4c92-a8dd-7b6e229ff469	batch.manage	Batch Manage	\N	batch	manage	core	\N	t	{}	2026-06-07 05:18:25.079504+00	2026-06-07 05:18:25.079505+00
738a1b2d-a9c4-4475-a48b-fb702515ccd3	serial.read	Serial Read	\N	serial	read	core	\N	t	{}	2026-06-07 05:18:25.079514+00	2026-06-07 05:18:25.079515+00
1c67676e-6781-43ad-8e57-408369422e74	serial.create	Serial Create	\N	serial	create	core	\N	t	{}	2026-06-07 05:18:25.079523+00	2026-06-07 05:18:25.079525+00
83962ac9-df0c-4422-a5ae-c223842c8382	serial.update	Serial Update	\N	serial	update	core	\N	t	{}	2026-06-07 05:18:25.079533+00	2026-06-07 05:18:25.079534+00
520c47da-2c82-4b18-aba7-8503f95504f9	serial.delete	Serial Delete	\N	serial	delete	core	\N	t	{}	2026-06-07 05:18:25.079543+00	2026-06-07 05:18:25.079544+00
4e69f059-314f-47e6-897f-f970eb6b6aa7	serial.manage	Serial Manage	\N	serial	manage	core	\N	t	{}	2026-06-07 05:18:25.079552+00	2026-06-07 05:18:25.079553+00
606b7604-e542-4d7e-bba8-81de709f2b71	asn_order.read	Asn Order Read	\N	asn_order	read	core	\N	t	{}	2026-06-07 05:18:25.079562+00	2026-06-07 05:18:25.079563+00
887e0fdb-494a-46aa-869f-b99740705da1	asn_order.create	Asn Order Create	\N	asn_order	create	core	\N	t	{}	2026-06-07 05:18:25.079571+00	2026-06-07 05:18:25.079573+00
801c3ff8-cd35-4286-882c-33761f4b5f87	asn_order.update	Asn Order Update	\N	asn_order	update	core	\N	t	{}	2026-06-07 05:18:25.079581+00	2026-06-07 05:18:25.079582+00
97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	asn_order.delete	Asn Order Delete	\N	asn_order	delete	core	\N	t	{}	2026-06-07 05:18:25.079591+00	2026-06-07 05:18:25.079592+00
81f2ce5a-b8c3-469f-aa40-39ac8a80d319	asn_order.manage	Asn Order Manage	\N	asn_order	manage	core	\N	t	{}	2026-06-07 05:18:25.0796+00	2026-06-07 05:18:25.079602+00
a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	pick_list.read	Pick List Read	\N	pick_list	read	core	\N	t	{}	2026-06-07 05:18:25.07961+00	2026-06-07 05:18:25.079611+00
a0e56f2b-8783-42b9-ade3-972a17063f6f	pick_list.create	Pick List Create	\N	pick_list	create	core	\N	t	{}	2026-06-07 05:18:25.079638+00	2026-06-07 05:18:25.07964+00
54dd4393-88fc-4827-9705-438e6628987a	pick_list.update	Pick List Update	\N	pick_list	update	core	\N	t	{}	2026-06-07 05:18:25.079654+00	2026-06-07 05:18:25.079655+00
62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	pick_list.delete	Pick List Delete	\N	pick_list	delete	core	\N	t	{}	2026-06-07 05:18:25.079664+00	2026-06-07 05:18:25.079665+00
9e243797-9f2a-44ed-b748-c41cd77e4d2d	pick_list.manage	Pick List Manage	\N	pick_list	manage	core	\N	t	{}	2026-06-07 05:18:25.079674+00	2026-06-07 05:18:25.079675+00
d0c33de9-098f-4cdd-8129-c9d1b228e01f	invoice.read	Invoice Read	\N	invoice	read	core	\N	t	{}	2026-06-07 05:18:25.079684+00	2026-06-07 05:18:25.079685+00
ec4c02c9-7f8e-413c-9cfe-e812755dbf3b	invoice.create	Invoice Create	\N	invoice	create	core	\N	t	{}	2026-06-07 05:18:25.079693+00	2026-06-07 05:18:25.079695+00
8c4b39cb-75d7-4a02-8bb4-e05320ef870e	invoice.update	Invoice Update	\N	invoice	update	core	\N	t	{}	2026-06-07 05:18:25.079703+00	2026-06-07 05:18:25.079704+00
ff4d8d8a-3291-4e18-a2e4-7aa126c3608a	invoice.delete	Invoice Delete	\N	invoice	delete	core	\N	t	{}	2026-06-07 05:18:25.079713+00	2026-06-07 05:18:25.079714+00
0160b70a-f910-4613-9dc3-13e4fd773404	invoice.manage	Invoice Manage	\N	invoice	manage	core	\N	t	{}	2026-06-07 05:18:25.079722+00	2026-06-07 05:18:25.079723+00
3a9291d5-3def-4546-8b9f-a2dcd22933f8	payment.read	Payment Read	\N	payment	read	core	\N	t	{}	2026-06-07 05:18:25.079732+00	2026-06-07 05:18:25.079733+00
a5bd460e-2bb5-4a7f-80ea-1c0770b4d583	payment.create	Payment Create	\N	payment	create	core	\N	t	{}	2026-06-07 05:18:25.079741+00	2026-06-07 05:18:25.079742+00
64d09c38-f333-426e-8635-7c9eb27ceed0	payment.update	Payment Update	\N	payment	update	core	\N	t	{}	2026-06-07 05:18:25.079751+00	2026-06-07 05:18:25.079752+00
b48128c1-897c-4cda-93da-6cd3f965fc23	payment.delete	Payment Delete	\N	payment	delete	core	\N	t	{}	2026-06-07 05:18:25.07976+00	2026-06-07 05:18:25.079762+00
ebd760a0-cb40-47cc-a4a1-d1b78271143c	payment.manage	Payment Manage	\N	payment	manage	core	\N	t	{}	2026-06-07 05:18:25.079785+00	2026-06-07 05:18:25.079787+00
b8992460-4387-43f1-add3-54294859d7f7	sales_order.read	Sales Order Read	\N	sales_order	read	core	\N	t	{}	2026-06-07 05:18:25.079795+00	2026-06-07 05:18:25.079797+00
71898b8a-cf52-4422-bfe0-cdbf9c8b49eb	sales_order.create	Sales Order Create	\N	sales_order	create	core	\N	t	{}	2026-06-07 05:18:25.079805+00	2026-06-07 05:18:25.079806+00
93891906-2a3e-4f7b-98ff-d2af686a2134	sales_order.update	Sales Order Update	\N	sales_order	update	core	\N	t	{}	2026-06-07 05:18:25.079815+00	2026-06-07 05:18:25.079816+00
2e09c9ee-b539-4915-bc92-cc29dd4858e3	sales_order.delete	Sales Order Delete	\N	sales_order	delete	core	\N	t	{}	2026-06-07 05:18:25.079824+00	2026-06-07 05:18:25.079825+00
e537217a-1bc2-45a3-9564-92d9bccf9d24	sales_order.manage	Sales Order Manage	\N	sales_order	manage	core	\N	t	{}	2026-06-07 05:18:25.079834+00	2026-06-07 05:18:25.079835+00
0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	purchase_order.read	Purchase Order Read	\N	purchase_order	read	core	\N	t	{}	2026-06-07 05:18:25.079843+00	2026-06-07 05:18:25.079845+00
d715a20c-1044-4579-81c1-2689cdd39847	purchase_order.create	Purchase Order Create	\N	purchase_order	create	core	\N	t	{}	2026-06-07 05:18:25.079853+00	2026-06-07 05:18:25.079854+00
e1d2717e-7f56-4800-bdaa-3e3e4e30746a	purchase_order.update	Purchase Order Update	\N	purchase_order	update	core	\N	t	{}	2026-06-07 05:18:25.079862+00	2026-06-07 05:18:25.079864+00
71c5940e-22f4-4ad9-b850-f850688069c1	purchase_order.delete	Purchase Order Delete	\N	purchase_order	delete	core	\N	t	{}	2026-06-07 05:18:25.079872+00	2026-06-07 05:18:25.079873+00
b3fcc49f-6de1-4c2c-9f7d-12a9ad85bb3c	purchase_order.manage	Purchase Order Manage	\N	purchase_order	manage	core	\N	t	{}	2026-06-07 05:18:25.079882+00	2026-06-07 05:18:25.079883+00
8f455ac4-d980-45f1-bc71-9630c031c90d	chart_of_account.read	Chart Of Account Read	\N	chart_of_account	read	core	\N	t	{}	2026-06-07 05:18:25.079891+00	2026-06-07 05:18:25.079892+00
70342008-ce16-4d30-b45d-d202a6b07820	chart_of_account.create	Chart Of Account Create	\N	chart_of_account	create	core	\N	t	{}	2026-06-07 05:18:25.079901+00	2026-06-07 05:18:25.079902+00
4621c394-fc16-4333-baf5-c50a2368948b	chart_of_account.update	Chart Of Account Update	\N	chart_of_account	update	core	\N	t	{}	2026-06-07 05:18:25.07991+00	2026-06-07 05:18:25.079912+00
32563007-1db7-49dc-a57c-0b93acbd889e	chart_of_account.delete	Chart Of Account Delete	\N	chart_of_account	delete	core	\N	t	{}	2026-06-07 05:18:25.07992+00	2026-06-07 05:18:25.079921+00
3c11905d-a7f0-4999-8362-753655b4e48b	chart_of_account.manage	Chart Of Account Manage	\N	chart_of_account	manage	core	\N	t	{}	2026-06-07 05:18:25.07993+00	2026-06-07 05:18:25.079931+00
7c3d284e-4ba4-44b6-b3ed-a7392c4c91fc	report.read	Report Read	\N	report	read	core	\N	t	{}	2026-06-07 05:18:25.079939+00	2026-06-07 05:18:25.079941+00
51226338-58c4-4623-a488-68b9ef3810b4	report.execute	Report Execute	\N	report	execute	core	\N	t	{}	2026-06-07 05:18:25.079949+00	2026-06-07 05:18:25.07995+00
8f790ad3-6ce1-4cc5-856c-4733ffeebe10	setting.read	Setting Read	\N	setting	read	core	\N	t	{}	2026-06-07 05:18:25.079958+00	2026-06-07 05:18:25.07996+00
0e8250e4-4495-4b52-8168-baf4bd3042b9	setting.update	Setting Update	\N	setting	update	core	\N	t	{}	2026-06-07 05:18:25.079968+00	2026-06-07 05:18:25.079969+00
a773d9ec-9cb7-44d7-b037-ee429787e8b4	setting.manage	Setting Manage	\N	setting	manage	core	\N	t	{}	2026-06-07 05:18:25.079978+00	2026-06-07 05:18:25.079979+00
be4c8197-9291-4b55-8214-d33662ddc7ea	*.*	Full Access (Wildcard)	Grants access to all resources and actions	all	manage	identity	\N	t	{}	2026-06-07 05:18:25.079987+00	2026-06-07 05:18:25.079989+00
\.

--
-- Data for Name: refresh_tokens; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.refresh_tokens (id, user_id, token_hash, token_family, device_id, device_name, device_type, os_info, browser_info, ip_address, user_agent, expires_at, revoked_at, revoked_reason, created_at, last_used_at) FROM stdin;
a822c99e-6370-4572-89f3-2e9cbe04711c	20c0587a-7145-48e0-9471-caae8de8fe4d	b3880b561a94465d58a875d4f7a73f5d61a540593cf19d0b26051a29bf9a589e	942cdd5d-7f74-4f03-a50b-cc79579d9eef	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-11 13:08:49+00	\N	\N	2026-06-04 13:08:49.109019+00	\N
9d89bd58-90ca-4313-9eea-5685e661f50d	20c0587a-7145-48e0-9471-caae8de8fe4d	34bb5096c3a539fc6a6b0744265b5aaf24240702aa689708481008a3965d3ea6	574ed41e-e04b-4869-954c-7a040aca3617	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-15 12:49:53+00	\N	\N	2026-06-08 12:49:53.258983+00	2026-06-08 15:20:20.939477+00
dabdc0f5-0664-4c06-a95b-72336bd4aec7	6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	58dd85a2c3d223403efb4ca2938c24e41d75b85d4540a7624091c9e0edc7451a	9b59c5d0-4318-4f8d-a941-de852c9c2827	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-18 19:22:13+00	2026-06-12 04:48:17.013458+00	user_logout	2026-06-11 19:22:13.313717+00	\N
1fbcb383-18bb-4188-a98a-7efdce1410ad	ba121f89-c767-4fdd-ab43-fd658c42a9d4	c0e2161e11eb387f40b0bc37de20de7fb49940d0bfe9b08285793a6e3b8f7277	50bdf704-ff60-453c-bbcf-1d3ad919de68	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-14 06:09:36+00	\N	\N	2026-06-07 06:09:36.199117+00	\N
9fec2d4b-17c3-4bec-b2e4-134569accac3	ba121f89-c767-4fdd-ab43-fd658c42a9d4	20d61d619bbc514e430ea8fdd9b9b6c9483c208cb6306974783b0973c69864f0	637896be-70ef-4252-b0ec-64aa64ddaf6a	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-14 06:10:42+00	\N	\N	2026-06-07 06:10:42.423289+00	\N
7b81531e-50d5-458c-b5ca-66f8bab0ca79	ba121f89-c767-4fdd-ab43-fd658c42a9d4	ccab947794c0e68ca1aa543bdb196a44378fb68845d7833eeab15029b2a2e1e6	64349dbc-e4bb-4db0-b9e0-3065ab232698	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-14 06:16:39+00	\N	\N	2026-06-07 06:16:39.245662+00	\N
bc62856e-abd8-467d-8a82-975d73d89f09	ba121f89-c767-4fdd-ab43-fd658c42a9d4	9d3d9c0eb1133ad2fab2274ee5e4afaa5964a9ee9850b53bcb089ba210692beb	bdf93711-5c89-4954-8bc8-e2bb2c8f0de0	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-14 06:25:05+00	\N	\N	2026-06-07 06:25:05.398295+00	\N
ee49ca02-a7f7-4443-94cd-5ac585df7a39	ba121f89-c767-4fdd-ab43-fd658c42a9d4	9daee4c4d708958df960514b3a4796e84ee902999884f4f3f1737e53b99977e6	357e2e0d-ee2f-4ed2-a2bd-5107ae8ff029	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-14 06:28:23+00	\N	\N	2026-06-07 06:28:23.098207+00	\N
8e82b147-8d34-44b0-89ea-fc1e3548e72c	ba121f89-c767-4fdd-ab43-fd658c42a9d4	f921500420d774464f40105ff94a32837cfe4f700480762eea94f89ba3efd776	05f5cdf3-1c30-4bf8-af5a-9e711ff8589f	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-14 06:33:53+00	\N	\N	2026-06-07 06:33:53.681936+00	\N
1802fc4b-e147-4087-9ad0-60bdbbe0aa82	ba121f89-c767-4fdd-ab43-fd658c42a9d4	3b6494bfaf4b89a8c8142da986a1d42062698d4c5067b381ac1b7138b40b9c62	8c050016-5887-4b9f-82ea-e6420b0eba16	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-14 07:03:13+00	\N	\N	2026-06-07 07:03:13.940075+00	\N
0b98e7c3-1ef7-4cbb-a418-fed49c3004a6	20c0587a-7145-48e0-9471-caae8de8fe4d	9cd3fb8f320925eb8d4313c213670b69ef220fec25583d919a1ae12bd517d9fb	2d0e10dc-2d89-461e-b2be-92a7f733ab78	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-14 05:03:30+00	\N	\N	2026-06-07 05:03:30.02327+00	2026-06-08 09:19:37.510535+00
5eb7ddfc-efd1-4a63-ae98-5aa276f0c806	20c0587a-7145-48e0-9471-caae8de8fe4d	97227cb606d908678ee21b8ab5d480926b992c9eac10af43e18c9fe27b33060c	82655f46-1944-4e5a-b881-4e0c9ce587c3	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-16 18:11:55+00	\N	\N	2026-06-09 18:11:55.504315+00	2026-06-09 18:24:28.803988+00
19036188-94d5-48da-acc3-f5ec156e16b7	20c0587a-7145-48e0-9471-caae8de8fe4d	0d61e4c2e7490d144fad2b6478fc88617ead4d8b7e34ee73df22df4817dec631	7cc43efe-bb6e-40d2-b749-bfd49446224b	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-15 12:34:49+00	2026-06-08 12:49:32.841147+00	user_logout	2026-06-08 12:34:49.865541+00	2026-06-08 12:38:27.398891+00
5794a1fc-e504-47c1-807d-2c1013b26f62	ba121f89-c767-4fdd-ab43-fd658c42a9d4	f313c3ed791c425a7f622947df18c76dafe1fe75e4bd02a682aa97c32c18b42b	03b1a5d2-f495-40ba-ab8b-347b07160e85	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-15 12:51:02+00	\N	\N	2026-06-08 12:51:02.361076+00	\N
8dbe1222-ba50-44ed-94f1-68313bac560b	ba121f89-c767-4fdd-ab43-fd658c42a9d4	5767d910f3a6451d235b4556cdcfd202aa6e119faddc0da1a8da9ca42b2aa36a	fb42c722-772c-42e2-86ae-dc5af241cc07	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-18 18:10:01+00	\N	\N	2026-06-11 18:10:01.890705+00	\N
7606520c-703a-4d8e-9b17-4d782b3b03d7	fbfd7719-159d-4751-ba13-5fc9e35fa470	ab8d7853e989ebc6b893ea805d8418c929b02bbdd99655205afcee5488a36245	ca57c403-7424-4924-97a1-e2eb6cab779d	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-18 17:53:48+00	2026-06-12 04:35:37.258043+00	user_logout	2026-06-11 17:53:48.487316+00	2026-06-11 19:20:08.197865+00
47d99a61-b8f0-4c1c-b7cc-d03057feab85	20c0587a-7145-48e0-9471-caae8de8fe4d	fef843e45811b4a8584c6bb47ad8a15e5515b65cbf388effeef40a7526434b12	3e05b115-ae36-4989-8be8-5e1e93c67a44	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-15 15:22:29+00	2026-06-09 18:10:02.558496+00	user_logout	2026-06-08 15:22:29.513781+00	2026-06-09 18:07:42.806408+00
5491bebd-2944-46c0-ae01-1f92ddf8ec87	ba121f89-c767-4fdd-ab43-fd658c42a9d4	bf869e7bfdeac87d6e1c9a05b3d7b0da6060bff91efc704dc007c31c5d07c813	b5eb2433-2850-4845-adc0-acf024789858	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36	2026-06-16 18:10:27+00	\N	\N	2026-06-09 18:10:27.124772+00	\N
42360ee2-1449-472a-bbf9-7f002db67b4b	6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	c463941b2e4af5f496b30f746228b1b96f7637f007c6b59e3685dede7ab1b6ac	e363ff56-03b3-4b6e-bcc4-acf282ea42a2	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 04:38:36+00	2026-06-12 04:42:39.820444+00	user_logout	2026-06-12 04:38:36.800982+00	\N
282cdea4-ab34-4b30-99e0-9d2794439b3d	fbfd7719-159d-4751-ba13-5fc9e35fa470	b4b5a39e764b7d2e47262eb6da8bf46fc74662e11b4f2ada4592b6d6ad2b1647	347bb16d-8353-49aa-b08b-07fb8d48f1c2	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 04:43:42+00	2026-06-12 05:01:18.363627+00	user_logout	2026-06-12 04:43:42.636436+00	2026-06-12 05:00:43.737583+00
adce4791-a41b-4605-8082-d0e5a1732c09	fbfd7719-159d-4751-ba13-5fc9e35fa470	accc2d9674142929f5bd9db6f57d9a9d10b7d6d69d5e8fc38dc63fbd6b899552	10eda741-7430-4f42-8d8c-5ed66dab4381	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 05:01:43+00	2026-06-12 05:02:10.708308+00	user_logout	2026-06-12 05:01:43.144909+00	\N
e29ad6e7-d60e-4732-ad8e-8a70ab311394	6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	2fd7ab2caa8f5ce2058382cee60fac677285c74f2b9f074423327e91eaddbc53	674e7c25-b903-46cf-a35f-fda483a8d053	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 05:02:17+00	2026-06-12 06:08:06.073126+00	user_logout	2026-06-12 05:02:17.991545+00	2026-06-12 05:27:28.829664+00
c00b5205-96ea-4526-b039-504a63ef840d	fbfd7719-159d-4751-ba13-5fc9e35fa470	d15fb2c3f73d4a83cc7065aa23293d75010b2f83701ded7300ea9aa8b0ba6b14	07ff9b51-324d-4dbd-8b76-f710cdad70e0	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 06:08:24+00	2026-06-12 06:25:19.388002+00	user_logout	2026-06-12 06:08:24.976445+00	2026-06-12 06:20:54.531076+00
222f5844-3f2f-4357-a353-ffb1174168bb	6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	c245b25c863c39bfd93c85734f22fa7cb8959e91dde1378d3e5add51be1b04a7	f4b95dad-d9e6-4070-b955-ac1d709c666a	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 06:25:27+00	2026-06-12 06:25:55.266908+00	user_logout	2026-06-12 06:25:27.485933+00	\N
0b8222fd-7797-4378-90a8-20fefe4655a1	fbfd7719-159d-4751-ba13-5fc9e35fa470	99acfae847272c6b90e582a263f521f33e99e1f3098f5f6687214d94308f3efa	a642cd07-6d4d-4e10-958a-0a434daae179	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 06:26:05+00	\N	\N	2026-06-12 06:26:05.697727+00	2026-06-15 12:06:29.13247+00
f6634275-b0e4-47ea-ad1f-bde00a3aefe2	57f8a2b2-3866-468f-b68d-d4950df43d1c	1b93e92859118e7fb571e95071a5b0f0d4960769919c8b545b32ed63ca99ae36	74095765-8a38-480a-aa9d-ef5d24659e1f	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-19 08:41:26+00	2026-06-12 12:37:59.813414+00	user_logout	2026-06-12 08:41:26.620342+00	2026-06-12 12:34:21.205995+00
83eaf2fb-0437-4419-aee6-5f4dd38e86f5	d842127f-7520-4612-987f-2faf88b8c0b9	94c761374aaa138a3e24a4760e152e0e8856f59c842027f8d03415976548f395	e05ec41d-19fd-43aa-8b8c-0013a8480a49	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-19 12:39:46+00	2026-06-12 12:40:36.407321+00	user_logout	2026-06-12 12:39:46.918333+00	\N
16adb7d0-be7f-47d0-832b-7e9aaf80eea7	f4c9c4a8-ad3f-4e90-afaf-f437b8644585	012b008904428325995bf521d1958c3cb67ea60d67a6701ace047833e177aed2	65134675-d292-4b49-93f1-fe824bcc6291	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-19 12:41:09+00	2026-06-12 12:42:41.785027+00	user_logout	2026-06-12 12:41:09.831708+00	\N
b0844f1b-030a-4c49-ad16-94606dbcf076	fbfd7719-159d-4751-ba13-5fc9e35fa470	369ac63072d35f0b0099b25efbb8a086b43d8868df53508cdf63f837e07f7246	a5894cce-3344-49c4-9ccc-03b7657f6eec	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 09:59:08+00	\N	\N	2026-06-18 09:59:08.312055+00	\N
3ce109f5-774d-4a0b-b5dc-2bcd9aba00c7	d842127f-7520-4612-987f-2faf88b8c0b9	c8df508ff0b6d3a247dd2afd30779bc365a6670cad543dd41ba26e140587efd9	70d26d25-4448-43b5-ae84-dedba282c0ea	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-19 12:42:54+00	2026-06-12 12:53:24.881801+00	user_logout	2026-06-12 12:42:54.75359+00	2026-06-12 12:51:36.400874+00
56368b47-caa1-48a5-8412-e0848518cb10	f4c9c4a8-ad3f-4e90-afaf-f437b8644585	0207e1b93b46d584521e616865632c4d2129f29bf946dec1fb74aaf2e0fcc03e	a460f761-8ea5-4377-a096-64aa0b36bbee	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-19 12:53:44+00	2026-06-12 12:54:26.220647+00	user_logout	2026-06-12 12:53:44.123345+00	\N
26d73101-282b-4689-921a-5f400a89e4be	d842127f-7520-4612-987f-2faf88b8c0b9	a55666e682fcdf136dbb37345d10d55c444b6ae314d672ed86bfd3ea2be6e91a	02cdf283-17a7-4070-9e23-8bf3b2084584	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-19 14:33:34+00	2026-06-15 12:07:41.387124+00	user_logout	2026-06-12 14:33:34.738244+00	2026-06-15 12:06:27.527558+00
3c8449a0-9388-4c78-ad47-ed030ffffc42	d842127f-7520-4612-987f-2faf88b8c0b9	2d6c7362e0a49478fde3b5133a03f2074ce617d0c902cf70fcc05f8a0fcd24e5	52ece9e3-8155-4ac6-8ec2-c9a29f5765be	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-22 13:06:37+00	2026-06-19 04:18:58.480381+00	user_logout	2026-06-15 13:06:37.161854+00	2026-06-19 04:18:45.482466+00
0089749e-2410-4749-8a54-a81900e41a7e	8a5f437f-8277-4c85-89c3-cffbafe61fa4	5116d90c093da0a5fed91593b3df9354251384fa8d962d2996554bd80954541d	7132d7cf-39f4-41fd-9bd3-4bbe586e177e	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-19 06:28:56+00	2026-06-12 08:27:27.908547+00	user_logout	2026-06-12 06:28:56.59187+00	2026-06-12 08:24:41.058289+00
610bc2e0-8d6d-4652-94e0-5318a1c197b5	04aa34fe-f4ee-4f55-8624-b7e3665fd137	cc64419673cb05de9eafdd76cea71044418f52845cd98f9db566aea3ad69a63b	e36b2bac-a412-4488-be24-a685dcf2b647	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-19 08:28:31+00	2026-06-12 08:39:42.77571+00	user_logout	2026-06-12 08:28:31.099615+00	2026-06-12 08:39:22.838731+00
1676ecab-d72d-44c5-b4ee-26187e8d522a	8a5f437f-8277-4c85-89c3-cffbafe61fa4	86636bd8a5419cfac17e2fe944173c6ac0e5bb69968ba43fcd8e9e573c95d287	bbea2f88-6c7c-4dee-a576-3953cb345cb5	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-22 12:08:19+00	\N	\N	2026-06-15 12:08:19.263214+00	\N
09f70130-a8cf-4c84-9c2f-584a747039f7	8a5f437f-8277-4c85-89c3-cffbafe61fa4	f5dd22470e8607a967132e13e2206c3486e0f5e5712e61c132ed261e7f4fb8ea	a3fea820-b6ab-4d86-b269-15362ebbb79d	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-24 11:01:54+00	\N	\N	2026-06-17 11:01:54.167155+00	2026-06-17 12:25:15.746875+00
c4266a79-a60b-4373-aeb4-d6e9831da8db	fbfd7719-159d-4751-ba13-5fc9e35fa470	de0379f3ce004d557e5183f2f105a90214549848061b2474697bb2037f7e61a1	8964c8bb-ebc9-4993-81d1-0e7d64c11443	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-24 10:59:39+00	\N	\N	2026-06-17 10:59:39.20104+00	2026-06-17 12:52:53.844787+00
33639dc4-b84c-400d-9202-dd985f0ef9aa	f4c9c4a8-ad3f-4e90-afaf-f437b8644585	49035f26330cb317f89b01099a26739c4e03a0350fb69f9d4076f7b8a3284a53	1762ac67-dd01-45c2-b09d-3fe5eca3fdd1	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-19 14:29:01+00	2026-06-15 13:05:56.744872+00	user_logout	2026-06-12 14:29:01.092518+00	2026-06-15 13:05:37.601996+00
3b8b9bb4-3cda-4858-bef1-20275f777da3	fbfd7719-159d-4751-ba13-5fc9e35fa470	6b66677d589b320899bcd7db2f09f88c71b02648bec8cab53ec553fd0940ce80	c90b65a1-782b-429d-834c-2337e40f9259	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-24 10:53:40+00	2026-06-17 10:58:45.484245+00	user_logout	2026-06-17 10:53:40.549813+00	2026-06-17 10:58:28.631813+00
3d45a8a0-b71c-41a1-ae50-05a22e9ad8b3	fbfd7719-159d-4751-ba13-5fc9e35fa470	e8421781bdc554868a87083ae3ea9104956ed22d06353e66a06a986a4412ef0e	5fd72c71-75af-4f18-a36c-d9bd5be641f8	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-25 12:34:38+00	\N	\N	2026-06-18 12:34:38.621355+00	2026-06-18 17:16:58.515403+00
966f4228-36a2-44f1-9e93-1a1bed93f6ad	fbfd7719-159d-4751-ba13-5fc9e35fa470	a7d5c098fab0080475c073b3908d7cfaba70383584ffc7869f6363233cdd19f9	ab6b0b0f-c8d2-4b99-a7b7-c8e4b6e83679	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-24 12:55:36+00	\N	\N	2026-06-17 12:55:36.69333+00	2026-06-17 16:21:54.64246+00
8e4046b5-9212-4387-9872-3a5a857e026e	fbfd7719-159d-4751-ba13-5fc9e35fa470	16bc8d75108717a8063df36aa3acd9f24175cbf88c271617703948edf5bd61b8	a003487a-73b0-4cec-8c14-40adb73973fd	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-24 17:20:20+00	\N	\N	2026-06-17 17:20:20.048091+00	2026-06-18 09:58:55.469333+00
a3fc757d-155f-4305-a948-7a82430b96c0	ffae90be-8ac1-447d-bca1-90cace2ff429	9f79014639982d56b178f04199b72768585850ef57a43321e84cc01bfcfa6069	3db2a5d1-9a29-4f64-99dc-6cf264be262b	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-26 04:07:17+00	\N	\N	2026-06-19 04:07:17.604884+00	2026-06-19 04:17:20.533281+00
36b13090-4529-4417-9796-628f85efd8e9	ffae90be-8ac1-447d-bca1-90cace2ff429	97a0a8ed149051ee6531afa9002dfa29292aeb5ca8018fa7ef2d06806d874d94	76ff1f03-674d-42eb-9c3c-3b50cb2e9231	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-26 04:46:45+00	\N	\N	2026-06-19 04:46:45.308805+00	2026-06-19 10:08:47.712589+00
26354d93-e35b-4052-a28f-b053ed089864	ffae90be-8ac1-447d-bca1-90cace2ff429	79e03a46a512ecc6d4d25de7ce4b12aab2115cf4371539c2c730527a5248d92a	df67aa4f-8681-458b-97c4-d4af1856a120	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-26 04:43:27+00	\N	\N	2026-06-19 04:43:27.335347+00	\N
cc61f339-ae73-455c-b7ee-e06e58566b45	82b119e8-6a0d-41f9-9b01-0f34c3cc29b9	e9a796ab92146425290b65a250502f5efc41e13cd93d6ab043009c8416aa1906	6e840101-8dc2-4087-869b-5a82f8461621	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0	2026-06-26 04:19:34+00	\N	\N	2026-06-19 04:19:34.521713+00	2026-06-19 11:15:03.053098+00
1e2b0229-e200-4b1e-912b-1f096cc48e19	171e65d7-60c5-451b-a5b6-c174fbc842c1	ae0433f7970ea0017ccbc2cb0e7ca6bdff70d05b5744cd4c0b6e12527fce1c1f	f80ca4fb-838c-4b6c-8706-44f6a34c86f9	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-26 04:44:35+00	2026-06-19 04:46:31.965094+00	user_logout	2026-06-19 04:44:35.478436+00	2026-06-19 04:46:00.566845+00
ab763cf8-4ed5-45a4-9308-fdafc4aae21a	ffae90be-8ac1-447d-bca1-90cace2ff429	59c16b556f4a6ca42397b1abc233ed83c1a8515cb515276a35c7232f6d158029	56f8cb71-20b1-4cf8-b969-952238e6c071	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-29 14:20:11+00	\N	\N	2026-06-22 14:20:11.26388+00	2026-06-23 08:28:27.087471+00
73ddbe7d-0590-42d6-9751-a25d40f59d9a	ffae90be-8ac1-447d-bca1-90cace2ff429	29694bc2bc17824611077e9340f20d3ec746c668299ff06f14424ca71434f2ad	19525adc-c6eb-4302-a52f-8566cc3beb65	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-26 05:46:03+00	\N	\N	2026-06-19 05:46:03.118414+00	\N
a808afda-630e-43ee-a390-a416ca89805d	ffae90be-8ac1-447d-bca1-90cace2ff429	179da285c4d29b33c5a94ab17aac4c5799a342760bb7a240e1adb3a657de8917	e76730b9-011b-46fe-b3b4-1c9d3fd50789	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-26 10:10:08+00	\N	\N	2026-06-19 10:10:08.94068+00	2026-06-19 14:09:30.656577+00
728e0318-b64f-4091-b1c4-7a7ff0936b53	ffae90be-8ac1-447d-bca1-90cace2ff429	8cc46fba05f20ecb45d71615ca32a79bd3b8374ed365dafabfc25ece81e4bb4c	991ce808-f179-4ece-bfb1-70ebf4931ca5	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-29 09:32:19+00	\N	\N	2026-06-22 09:32:19.458432+00	2026-06-22 09:42:35.831565+00
9d908983-2769-4bf7-9255-7ba2e8d149c6	ffae90be-8ac1-447d-bca1-90cace2ff429	cc766acb867768b5186f7ee6cd604cf77fcbd335f9babc7687838730bb154dae	757c5fa0-c151-4c58-9b4b-d03c599c1d3a	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-07-02 17:41:03+00	2026-06-25 18:01:01.270217+00	user_logout	2026-06-25 17:41:03.333435+00	\N
d3be55de-1d5e-429e-8f37-07a5e1786334	ffae90be-8ac1-447d-bca1-90cace2ff429	80fd9d81f93df642a32a3338b6def4c0b0137d225bec69c75d1b28cd8dc73163	53861862-7729-4705-9b65-04166353994a	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-26 14:12:46+00	\N	\N	2026-06-19 14:12:46.607448+00	2026-06-19 14:32:33.19664+00
96b5239d-4ada-43eb-8fc7-59c25b74d0b0	ffae90be-8ac1-447d-bca1-90cace2ff429	44d7e767cb5c6163201d82ba4a748e0fafc3823318ae6feeae2b2de5d411a42f	ad8372c7-e8cf-4818-99bf-30042e8ddf8d	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-29 10:10:15+00	2026-06-22 10:14:17.996825+00	user_logout	2026-06-22 10:10:15.214385+00	2026-06-22 10:12:09.332282+00
54a6af66-dccd-41ad-bf5e-ce5d16b1ffd9	171e65d7-60c5-451b-a5b6-c174fbc842c1	8a74d773e45bda3064794ee181aa5f5b1a5b7a53197d136d31e6e1078c5f2f76	fb845d86-8d34-4952-950d-5e4a2535aabd	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-26 04:18:36+00	\N	\N	2026-06-19 04:18:36.926121+00	2026-06-19 10:08:47.405908+00
23408871-d39e-48db-96ec-e61a10954b88	ffae90be-8ac1-447d-bca1-90cace2ff429	3f50c8ee19bf3330f433a4d90f2c8bc0e3354ea46b9987ccdcad9fa2acbbd88d	5c9051c2-e9b4-4e79-8172-9ffedc76de52	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-07-02 17:11:07+00	2026-06-25 17:40:52.221597+00	user_logout	2026-06-25 17:11:07.505345+00	2026-06-25 17:12:23.680284+00
b1e7d2d3-8660-42de-8154-0af5a75a8347	ffae90be-8ac1-447d-bca1-90cace2ff429	666ac72848d844989af5869d6dc1748ebbf81d30b5cf8f09e1529194707dc834	1ad280e6-66ea-4c0c-9fa7-a26f81dde899	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-26 15:26:19+00	\N	\N	2026-06-19 15:26:19.050229+00	2026-06-22 02:59:23.478927+00
ab611e4b-cc23-4aa1-a09e-4d5c5cf3deb5	ffae90be-8ac1-447d-bca1-90cace2ff429	6d84950dd323a04daf369776a5e4ccbaa9943d8bc6d20d3b65d95ce2908f9609	c2f2e043-5c7c-4751-b438-a14a24a5f861	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-26 11:15:22+00	\N	\N	2026-06-19 11:15:22.368757+00	\N
04ea1307-9421-4162-9523-48e160f14e26	ffae90be-8ac1-447d-bca1-90cace2ff429	5542e524699550a8919d39485fe0f789026e9bfe69d2378adf6688bf22cdac91	2a72c2dc-51ff-4750-b57b-3f350e6e9336	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-29 03:44:47+00	\N	\N	2026-06-22 03:44:47.791077+00	\N
b07bab91-77c9-4414-ad44-c86cf3ca803f	ffae90be-8ac1-447d-bca1-90cace2ff429	e601c0597f51b44f695587e137c6294c8f55594b287fa4c41978d35a68720e49	56f3bfb9-7512-4692-96b8-8024bd3abdef	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-29 03:53:47+00	\N	\N	2026-06-22 03:53:47.054062+00	2026-06-22 03:53:50.348589+00
6b509362-e09e-4952-9a9e-d30b730594bc	171e65d7-60c5-451b-a5b6-c174fbc842c1	34ddbd0dd06fdbad85f7a2e956cc196784a2a7defeb46617c87dd5114b54c460	d1d01b09-7060-497d-b324-9e6b28db903a	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-29 10:14:25+00	2026-06-22 14:20:03.728083+00	user_logout	2026-06-22 10:14:25.677023+00	2026-06-22 14:19:32.245817+00
cfb5d506-8efa-4e8d-a5a0-6a838b79995b	ffae90be-8ac1-447d-bca1-90cace2ff429	30f6618b1abe277e84afeb1516b48170185156a8ecab39c622707ad925c7d712	e20e04a5-9270-4001-89fd-67bf75d5413b	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-06-29 05:08:34+00	\N	\N	2026-06-22 05:08:34.144375+00	2026-06-22 09:12:05.500044+00
008ca696-9f11-46fd-ac06-545ccdad2283	bd097e86-1759-4be1-9312-94e60346dbfd	67918a7668bb3b2edb633c9f00cdd0c4080095b286e58a3d6e6bb1e3601dd3e7	1282fd11-4735-48cc-872d-b318823e237d	\N	\N	\N	\N	\N	49.207.59.41	okhttp/4.12.0	2026-06-27 09:49:57+00	\N	\N	2026-06-25 17:49:57.124787+00	\N
e1a62145-8708-4f00-ad76-78623249f31f	171e65d7-60c5-451b-a5b6-c174fbc842c1	37ea4407cc99180c370cb78fe58c81349276ec81d0d6efe001d7260ba0efa8d4	1cfa98ec-b7d8-4fcf-975f-58b110adf43d	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-07-02 17:41:26+00	2026-06-25 17:55:24.743225+00	user_logout	2026-06-25 17:41:26.753301+00	\N
d58bca9c-074e-4f18-a93e-e7ddb1b82f3f	ca0eabd2-f796-4bd9-935a-47562d0880a4	22291a2c46821afad3c30fb599cd7aca814a44e145d2c328002dfa8003fdc8fd	4e6a5dfe-7bbf-49d7-959f-35f0a9b71a3b	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-07-02 18:02:54+00	2026-06-25 18:08:06.660616+00	user_logout	2026-06-25 18:02:54.838629+00	2026-06-25 18:03:28.241176+00
b5885980-cabe-4a6e-a23f-6df87fac1cbd	82b119e8-6a0d-41f9-9b01-0f34c3cc29b9	84f75db6722b3f5a62de3e89395aa9c37e35fc608b890179046705a2ad61ddc8	499644d2-854e-43d0-a8b3-ac80e085c911	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-07-02 17:56:07+00	2026-06-25 18:09:47.933782+00	user_logout	2026-06-25 17:56:07.365633+00	\N
86718f34-3ccb-4ed3-b0ee-a7b83caf8d72	ffae90be-8ac1-447d-bca1-90cace2ff429	26b25a627227ec9956cff9b1778e045ee5fe2f4a5d4d433697794cbc38b8a860	15ccab5d-68a4-4463-ab4d-419a0e5950e2	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-07-02 18:10:19+00	2026-06-25 18:10:52.817225+00	user_logout	2026-06-25 18:10:19.931551+00	2026-06-25 18:10:33.828868+00
e4e45c01-be38-4cc5-b2ce-33234143471f	32440aa3-3413-4906-8282-bb860a838f64	0e0620ed6e5540ecac81fda7398aedaee2d43cbd4c2cc9859cad6babcdd10c09	b5c1992e-0032-4fa0-9cde-963d4c09a2e6	\N	\N	\N	\N	\N	49.207.59.41	okhttp/4.12.0	2026-06-27 10:17:09+00	\N	\N	2026-06-25 18:17:09.968743+00	\N
f1d79c64-9cf1-4522-b81a-41b49e3268df	b9f2eb20-2fd2-4318-a67e-f8796fe1b128	0e8be3f16a2519e62b413267d36e091836e7050322116bf7023735c8804abfb1	9f747999-b9ac-4e1f-99c0-b075d5e06177	\N	Mobile App	\N	\N	\N	49.207.59.41	okhttp/4.12.0	2026-09-23 18:20:29+00	\N	\N	2026-06-25 18:20:29.078621+00	\N
d8dd5443-f08d-4f13-858e-908bd0d87086	b9f2eb20-2fd2-4318-a67e-f8796fe1b128	1ca9994fbaa78c4548990f8e122c35bf8d27581033694b4cb5747ac3f2be046d	2d4528b3-9b00-4cee-b9f5-e40e96a1239a	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-07-02 18:16:13+00	2026-06-26 03:24:22.975442+00	user_logout	2026-06-25 18:16:13.005859+00	\N
b90fde95-acc7-423a-ae9a-4fde73e9ab75	ca0eabd2-f796-4bd9-935a-47562d0880a4	58fe3b284fae4e93712697cd3615798159755422c231fb540f8b49ede3cf5fc8	4acaea1e-7fc2-4b92-98f1-9943c39232c1	\N	\N	\N	\N	\N	172.18.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36	2026-07-02 18:15:36+00	2026-06-26 03:24:40.357867+00	user_logout	2026-06-25 18:15:36.137403+00	\N
\.

--
-- Data for Name: role_permissions; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.role_permissions (id, role_id, permission_id, conditions) FROM stdin;
871f92b2-e0bb-4edd-a9d5-9a379a8088e7	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	eae0a88d-d74e-4c34-b4e4-0086a02b9ea6	{}
a2a056a4-1d4d-4461-bdaa-dfc725ada6a5	3bf01d48-72fc-43b9-a86d-ca2374ec940e	4e857568-7e03-4f89-a068-4d83b2a57d31	{}
993a6561-b5b0-470f-9765-40b2250bcc28	3bf01d48-72fc-43b9-a86d-ca2374ec940e	d78e9127-8054-4367-bac2-001c485338ed	{}
3de839f5-ef33-4891-9ee8-0953597d42c2	3bf01d48-72fc-43b9-a86d-ca2374ec940e	17f45225-074c-42a7-8ce3-ad3d40f24b56	{}
45e32dcc-630c-42f5-8ca4-df026e0a7376	3bf01d48-72fc-43b9-a86d-ca2374ec940e	587b00df-581d-4ae2-a19e-2e7da1c1c908	{}
cf157fe1-77d0-4edd-a4a1-9ae7da9269d4	f74c06eb-6c0c-4144-9836-8edd90ebbd34	40ad9d9a-2a44-4a25-b7e8-aaf69180973d	{}
4d5e5c15-6a48-452c-b2b2-df5c344e65a3	f74c06eb-6c0c-4144-9836-8edd90ebbd34	4914a0fc-4e1d-47df-9a26-6dfdcd05d6d7	{}
5c31d143-1784-4b4f-a505-5b5645646bb0	f74c06eb-6c0c-4144-9836-8edd90ebbd34	7a90d4d7-2a2f-4c9b-a63d-402e7200b3e8	{}
c3728812-c21e-44ac-b71a-5232ca2b95fb	f74c06eb-6c0c-4144-9836-8edd90ebbd34	0f90e9f7-e997-4fbf-9453-854356a1d3a6	{}
ee98e389-e767-4dc3-b308-c02094b55441	6f3d530c-90b0-4788-bd88-47385026463c	9427ed61-ab76-422c-aacb-f6084021fdb5	{}
8eafd3b9-ec21-415f-9f40-5325ab8f03f8	6f3d530c-90b0-4788-bd88-47385026463c	490d109c-b126-450d-a517-7e6a1f996a60	{}
04afd0c7-81e0-4fff-8765-37725625978f	6f3d530c-90b0-4788-bd88-47385026463c	016ec902-3bb8-4078-83c7-ccbdc5506b87	{}
77adf7f9-6740-4420-aab5-a2ae26de5694	6f3d530c-90b0-4788-bd88-47385026463c	255b36cc-883d-415f-b816-0e561b459ed0	{}
2b3292d5-4fc3-4aa4-ad15-930ac9dbf16f	57543360-893d-4bcf-b6ec-ea550ca1d582	017c0632-56a1-4941-84af-17f611842d3e	{}
a91a23b1-2887-434c-a69e-33ae1fc764e9	8c372bb6-92de-4182-a77f-10604e8ab30b	be4c8197-9291-4b55-8214-d33662ddc7ea	{}
7dedd110-45a6-435e-bab4-b6761d0a9197	8332777d-a6cd-4a8d-90e9-9db022775fbd	f65f79ec-3ce4-4e98-9b08-76b3901ecb2b	{}
2672eb5e-aefa-497e-affb-00052f1c1500	8332777d-a6cd-4a8d-90e9-9db022775fbd	b9c7ac87-1fd5-464d-b457-7b2c3fc2493d	{}
5378561b-6957-4257-a549-4b014450abcb	8332777d-a6cd-4a8d-90e9-9db022775fbd	744b0977-bb86-4ce8-845f-32212f4bfacb	{}
2533623a-4ef6-4967-a36d-54858ee1061c	8332777d-a6cd-4a8d-90e9-9db022775fbd	d29b40a0-d248-472b-ab21-fadd82fbbf31	{}
c9800839-ba57-4238-9500-6155451278f9	8332777d-a6cd-4a8d-90e9-9db022775fbd	7084e5f7-575d-43fc-ae8e-b819cc2267ad	{}
797116a0-2604-4753-afe3-b2ce87456507	8332777d-a6cd-4a8d-90e9-9db022775fbd	046f23e3-dc38-4c84-9036-1f0192d29f90	{}
d9a21f6b-269f-4d18-81f3-936c769144dd	8332777d-a6cd-4a8d-90e9-9db022775fbd	f49e1f8e-7594-41a7-9299-41ca9e1c98be	{}
24a6304d-bf02-4ab4-8336-0b2e48f2aa33	8332777d-a6cd-4a8d-90e9-9db022775fbd	6b4ecdcc-5500-4091-8f3e-ecb94f0b7d55	{}
e34a5e34-7945-4b83-a37c-9b8cfa8d542b	8332777d-a6cd-4a8d-90e9-9db022775fbd	2da18650-9590-40a2-9ec3-e4973a33e3ee	{}
d594cadb-c0cc-4ef9-a4d3-c458feb9ab70	8332777d-a6cd-4a8d-90e9-9db022775fbd	784007a6-c81d-4234-a8bb-8a035f89c06e	{}
785039b8-7817-4b4c-b194-2fff3b1cb7fe	8332777d-a6cd-4a8d-90e9-9db022775fbd	95d9f110-e9ba-4f81-b855-882e735b2e2b	{}
cce8be5c-645b-48cc-9501-73e73aa2d87a	8332777d-a6cd-4a8d-90e9-9db022775fbd	7208ac08-6e96-4965-a5ac-80c0505039af	{}
39dfcaa0-a7e5-4c7b-9213-7bad4e20c707	8332777d-a6cd-4a8d-90e9-9db022775fbd	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
b76e51fc-dd72-479d-a476-813cc2852567	8332777d-a6cd-4a8d-90e9-9db022775fbd	b8992460-4387-43f1-add3-54294859d7f7	{}
2bf43d07-a79e-42a1-beca-f036f16b13df	8332777d-a6cd-4a8d-90e9-9db022775fbd	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
c7131cb0-15b2-4823-8946-3884d22d33c5	8332777d-a6cd-4a8d-90e9-9db022775fbd	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
47d35573-311a-4253-b90c-7efba6f18be2	8332777d-a6cd-4a8d-90e9-9db022775fbd	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
b5ac86f1-7bb8-4c23-b837-a3ac45c33356	8332777d-a6cd-4a8d-90e9-9db022775fbd	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
35dbbf62-3077-4dc8-ba19-9c5c0b074e54	8332777d-a6cd-4a8d-90e9-9db022775fbd	c565f657-72c6-4f14-9350-079a1b72b65a	{}
0658bcc0-506f-459b-9a1f-947e11950b57	8332777d-a6cd-4a8d-90e9-9db022775fbd	00739872-28e8-4c95-a25b-40d579702ae8	{}
08e66b4b-e7a5-48d5-b983-80e95ae045b4	8332777d-a6cd-4a8d-90e9-9db022775fbd	bb561768-51b2-4cab-8079-b113796e5268	{}
d221999b-b8df-4a84-adbf-ca5e5a1e1038	8332777d-a6cd-4a8d-90e9-9db022775fbd	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
77fc5d69-0366-4aeb-91ea-49b5dc42d4ec	8332777d-a6cd-4a8d-90e9-9db022775fbd	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
b80438cb-339e-4de6-98b6-bc8538dc58f7	8332777d-a6cd-4a8d-90e9-9db022775fbd	606b7604-e542-4d7e-bba8-81de709f2b71	{}
f77647b8-738a-44b4-bbca-470b30b24e45	8332777d-a6cd-4a8d-90e9-9db022775fbd	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
f84da3e1-6c64-4590-98e7-065f30eb8cb1	8332777d-a6cd-4a8d-90e9-9db022775fbd	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
76c58f59-5a6d-4e22-be18-61c469c1671b	412fbd53-2d9a-471d-82e3-8af2a60f452a	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
78251d73-b7a5-4f2f-a8ad-ab6057674e9a	412fbd53-2d9a-471d-82e3-8af2a60f452a	d2694465-7e98-426e-a6f5-c63ab69594dc	{}
b91608c9-1c5e-46c9-99cd-c907501b2f7d	412fbd53-2d9a-471d-82e3-8af2a60f452a	1c49abd7-4666-4d3e-9e16-6451d5ee2da9	{}
028fe7a5-0d88-4c46-95e7-dc14f913679c	412fbd53-2d9a-471d-82e3-8af2a60f452a	e822e1fe-c906-4792-bcbe-bd68eef67b24	{}
3b591277-f970-4d13-9450-0e924be07089	412fbd53-2d9a-471d-82e3-8af2a60f452a	b8992460-4387-43f1-add3-54294859d7f7	{}
2f365dc1-2786-47e3-b56e-8df5c09eebef	412fbd53-2d9a-471d-82e3-8af2a60f452a	71898b8a-cf52-4422-bfe0-cdbf9c8b49eb	{}
132b2e8d-1ca5-4527-b2d9-c96f93563da4	412fbd53-2d9a-471d-82e3-8af2a60f452a	93891906-2a3e-4f7b-98ff-d2af686a2134	{}
eef4bdc4-aa07-400b-ba5c-da020905191f	412fbd53-2d9a-471d-82e3-8af2a60f452a	2e09c9ee-b539-4915-bc92-cc29dd4858e3	{}
b7639c27-4d65-4ad9-8e7b-6207299c730b	412fbd53-2d9a-471d-82e3-8af2a60f452a	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
c8b4f4e1-1146-419f-a8d6-8807096167d1	412fbd53-2d9a-471d-82e3-8af2a60f452a	ec4c02c9-7f8e-413c-9cfe-e812755dbf3b	{}
e03c762a-b150-4a78-8915-faab118ae03e	412fbd53-2d9a-471d-82e3-8af2a60f452a	8c4b39cb-75d7-4a02-8bb4-e05320ef870e	{}
1ed9d397-2131-4f69-a750-501654157961	412fbd53-2d9a-471d-82e3-8af2a60f452a	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
8739b15d-e45a-4389-b017-768fbf52e55d	412fbd53-2d9a-471d-82e3-8af2a60f452a	c565f657-72c6-4f14-9350-079a1b72b65a	{}
76d25344-8e55-4b56-8d99-be1631eca25a	412fbd53-2d9a-471d-82e3-8af2a60f452a	00739872-28e8-4c95-a25b-40d579702ae8	{}
9a38959b-4695-4611-8d2c-45f1cc10c4f5	412fbd53-2d9a-471d-82e3-8af2a60f452a	bb561768-51b2-4cab-8079-b113796e5268	{}
a4043e72-e6cb-4310-af83-3d3124c261c7	412fbd53-2d9a-471d-82e3-8af2a60f452a	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
789328b5-43f8-4d06-9837-e1a8f2f8af06	412fbd53-2d9a-471d-82e3-8af2a60f452a	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
20d3cde5-f1d4-4e6e-a772-93c14d89b21d	412fbd53-2d9a-471d-82e3-8af2a60f452a	606b7604-e542-4d7e-bba8-81de709f2b71	{}
d088e22e-ef75-444c-843d-89e721d8c5b8	ee481431-7fef-4d59-a208-94cccfd7b735	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
ae5df81d-2c79-481b-80e5-da397fe6c18a	ee481431-7fef-4d59-a208-94cccfd7b735	bd4e5b2c-5d39-4d68-bbe9-94d9096d59f8	{}
4bedea81-9435-42f3-9d56-3e39c39bdadb	ee481431-7fef-4d59-a208-94cccfd7b735	d1913f08-d669-4f93-ae93-739e9a1dabe6	{}
48dbd6a5-9608-4505-959c-3691f50b6869	ee481431-7fef-4d59-a208-94cccfd7b735	a754f927-efa8-4a93-8eb9-604606f30a53	{}
b50828c7-1fb5-4da5-8c0c-5cf8ae61a1f9	ee481431-7fef-4d59-a208-94cccfd7b735	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
5d0476b0-1b12-4da6-9c87-d2277c88030c	ee481431-7fef-4d59-a208-94cccfd7b735	d715a20c-1044-4579-81c1-2689cdd39847	{}
62f799ff-38cc-4766-b455-a112b373358d	ee481431-7fef-4d59-a208-94cccfd7b735	e1d2717e-7f56-4800-bdaa-3e3e4e30746a	{}
d30c384d-c8a7-427a-bf08-5f6184d80b8a	ee481431-7fef-4d59-a208-94cccfd7b735	71c5940e-22f4-4ad9-b850-f850688069c1	{}
0813c8b8-2e38-4c90-9d67-f42e71401ac8	ee481431-7fef-4d59-a208-94cccfd7b735	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
8e084b92-330c-4046-bfae-b8a99c671d08	ee481431-7fef-4d59-a208-94cccfd7b735	c565f657-72c6-4f14-9350-079a1b72b65a	{}
13cfdfc3-0261-459c-a7d9-0b56b266b8e5	ee481431-7fef-4d59-a208-94cccfd7b735	00739872-28e8-4c95-a25b-40d579702ae8	{}
98095c25-cb26-4f02-b2ce-98f4c494254b	ee481431-7fef-4d59-a208-94cccfd7b735	bb561768-51b2-4cab-8079-b113796e5268	{}
f4932556-9c80-4a06-a380-46d29c0bfb67	ee481431-7fef-4d59-a208-94cccfd7b735	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
b9b11e38-72af-4541-bf65-d6726b5ecaeb	ee481431-7fef-4d59-a208-94cccfd7b735	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
5ff3c38e-369e-4cab-91cb-0a2eb1e6d850	ee481431-7fef-4d59-a208-94cccfd7b735	606b7604-e542-4d7e-bba8-81de709f2b71	{}
3d2e12e8-2ea9-4c2b-a576-d90b5734fc26	b09c25ec-5ddf-4420-b9c9-26ac46ff8095	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
cc918f8e-e281-4cfb-a869-1c00ef2aa2d1	b09c25ec-5ddf-4420-b9c9-26ac46ff8095	70342008-ce16-4d30-b45d-d202a6b07820	{}
4fa2a7dd-b891-45ae-afcd-5c6b8bd30212	b09c25ec-5ddf-4420-b9c9-26ac46ff8095	4621c394-fc16-4333-baf5-c50a2368948b	{}
98437c24-c019-44da-be40-534fbc8bb4dc	b09c25ec-5ddf-4420-b9c9-26ac46ff8095	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
194134ff-e52c-48ec-9bb2-4a18dd4e4261	b09c25ec-5ddf-4420-b9c9-26ac46ff8095	a5bd460e-2bb5-4a7f-80ea-1c0770b4d583	{}
69445b79-a374-4cbd-a605-6b307831dcb6	b09c25ec-5ddf-4420-b9c9-26ac46ff8095	64d09c38-f333-426e-8635-7c9eb27ceed0	{}
b0f7860e-2cfe-49ec-83ad-71a8874e2e02	b09c25ec-5ddf-4420-b9c9-26ac46ff8095	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
20e7edeb-35c0-4111-93d0-75d0c6dd8ea1	3f54447f-f2e3-42b9-b82e-3ea81fec9320	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
09bf4720-be0b-44c3-8263-1f689a3d85ac	3f54447f-f2e3-42b9-b82e-3ea81fec9320	0290c46c-96ae-493a-873a-8c9acc403ec5	{}
9c174a7e-01dc-4895-b50f-ffa5ed51b523	3f54447f-f2e3-42b9-b82e-3ea81fec9320	24104566-dc21-4fd0-b59a-9d1aa8d94ca2	{}
59b138d5-1c4a-4a7d-b587-c4f54086219e	3f54447f-f2e3-42b9-b82e-3ea81fec9320	b73c729e-93f7-43ba-b541-3893ea43b341	{}
622dae0d-9cc1-4cf8-9392-a3450df3c866	3f54447f-f2e3-42b9-b82e-3ea81fec9320	c565f657-72c6-4f14-9350-079a1b72b65a	{}
d87c43c5-f16e-42da-b999-f9b4005f52c3	3f54447f-f2e3-42b9-b82e-3ea81fec9320	71558b37-b72f-4b6f-84f5-22518e8f3566	{}
822a67d5-17e9-4520-a428-16724c91eb2a	3f54447f-f2e3-42b9-b82e-3ea81fec9320	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
73868d7b-3f89-4aae-a207-46967006796f	3f54447f-f2e3-42b9-b82e-3ea81fec9320	e243100d-df88-4b91-ae70-717175d3d6aa	{}
1079ae4e-86be-4b6c-ade2-741da018bfe6	3f54447f-f2e3-42b9-b82e-3ea81fec9320	087ce167-b658-43de-bac7-155c71d30815	{}
8eca4449-bd5a-4c21-aa91-fc1216c90471	3f54447f-f2e3-42b9-b82e-3ea81fec9320	00739872-28e8-4c95-a25b-40d579702ae8	{}
1754b8a8-380e-4db4-865b-c8380f1be3d1	3f54447f-f2e3-42b9-b82e-3ea81fec9320	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
9fd704f9-a58a-4c09-81c4-7e0814490619	3f54447f-f2e3-42b9-b82e-3ea81fec9320	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
2f56ce8d-becd-4e86-9b36-aa637408eaa5	3f54447f-f2e3-42b9-b82e-3ea81fec9320	727d5903-9e43-4047-9274-b9722261f397	{}
4f8b30ec-fbe1-4230-87dd-6328fab33ea8	3f54447f-f2e3-42b9-b82e-3ea81fec9320	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
b7473cca-73f0-4831-8679-49f3ac674635	3f54447f-f2e3-42b9-b82e-3ea81fec9320	bb561768-51b2-4cab-8079-b113796e5268	{}
59225a4b-f8cf-4f3a-a038-bcf512b87c41	3f54447f-f2e3-42b9-b82e-3ea81fec9320	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
7a6c8d6a-3006-418b-8aee-7c678050a97b	3f54447f-f2e3-42b9-b82e-3ea81fec9320	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
9a242bd7-ee12-45a6-a054-2b176f5a669e	3f54447f-f2e3-42b9-b82e-3ea81fec9320	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
579e2fd9-f76e-4b79-bbfe-e086faea3385	3f54447f-f2e3-42b9-b82e-3ea81fec9320	54dd4393-88fc-4827-9705-438e6628987a	{}
3ba0ee4b-4c10-4ce1-9bef-4688a0322148	3f54447f-f2e3-42b9-b82e-3ea81fec9320	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
dfd6245f-2307-4297-b449-1eafd778be50	3f54447f-f2e3-42b9-b82e-3ea81fec9320	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
c9390bdf-06a6-4c34-bd8a-94a191f94529	3f54447f-f2e3-42b9-b82e-3ea81fec9320	606b7604-e542-4d7e-bba8-81de709f2b71	{}
9180c323-cd14-4c98-8040-a332c141cb06	3f54447f-f2e3-42b9-b82e-3ea81fec9320	887e0fdb-494a-46aa-869f-b99740705da1	{}
11b53644-e588-4b25-9904-1f17e68fe057	3f54447f-f2e3-42b9-b82e-3ea81fec9320	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
9adb1fd8-079e-4066-8b28-01de1daa567a	3f54447f-f2e3-42b9-b82e-3ea81fec9320	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
f7bcef9a-170b-4c56-96e3-f635119d35bd	3f54447f-f2e3-42b9-b82e-3ea81fec9320	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
f3715d53-10cf-4ec9-8b69-9b7162a89445	621a2385-cb10-4f42-a04b-0524992d11f9	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
7861dcd7-9e52-453a-839c-7b5741c75936	621a2385-cb10-4f42-a04b-0524992d11f9	b8992460-4387-43f1-add3-54294859d7f7	{}
fd365882-dd70-4795-8268-6afc30a0e8e6	621a2385-cb10-4f42-a04b-0524992d11f9	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
88907ccc-93ce-48c5-81e6-cf87b7518808	621a2385-cb10-4f42-a04b-0524992d11f9	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
fff0834f-aecb-4e91-9e0f-ceb3eea893a5	621a2385-cb10-4f42-a04b-0524992d11f9	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
89e299dc-3426-4791-bbd1-c0e7aa34d00f	621a2385-cb10-4f42-a04b-0524992d11f9	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
3e8b29cf-6ff2-4ae6-96a8-7bf73f65ed21	621a2385-cb10-4f42-a04b-0524992d11f9	c565f657-72c6-4f14-9350-079a1b72b65a	{}
fc7ec7ed-aa3c-4ff2-ad68-0eb0ad910809	621a2385-cb10-4f42-a04b-0524992d11f9	00739872-28e8-4c95-a25b-40d579702ae8	{}
d3447648-d822-49cd-a9cc-71482afe8736	621a2385-cb10-4f42-a04b-0524992d11f9	bb561768-51b2-4cab-8079-b113796e5268	{}
92bb30a8-49e1-4e9c-8ede-52e984e14db8	621a2385-cb10-4f42-a04b-0524992d11f9	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
aac4ee92-7e24-4f8d-8b08-6bc77c82621b	621a2385-cb10-4f42-a04b-0524992d11f9	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
50608781-ba77-42b9-b56e-39a9d3b67c30	621a2385-cb10-4f42-a04b-0524992d11f9	606b7604-e542-4d7e-bba8-81de709f2b71	{}
42b28a91-3b73-4699-b12b-25daceab1485	621a2385-cb10-4f42-a04b-0524992d11f9	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
ce84af15-cc19-4b11-85f5-db8c43414f74	621a2385-cb10-4f42-a04b-0524992d11f9	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
1d258237-61e9-4f4f-9091-f1a3a1e74da8	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	c565f657-72c6-4f14-9350-079a1b72b65a	{}
28b7274c-533d-4f63-9d6c-a8e26a87309d	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	71558b37-b72f-4b6f-84f5-22518e8f3566	{}
6dc1298c-183b-4e55-8634-7bb90793346b	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
9ba64683-0efe-4e95-8573-44fde2309394	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	e243100d-df88-4b91-ae70-717175d3d6aa	{}
32b8f290-1365-4918-875b-01eef0bf1479	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	087ce167-b658-43de-bac7-155c71d30815	{}
5767b622-6035-4dc6-9ab4-1a05c8d3e8d2	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
3ff9c22d-1f9c-4818-b90e-6381303e88ab	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
390993c2-4e2d-4dcc-9c6b-b06b9620afee	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	54dd4393-88fc-4827-9705-438e6628987a	{}
2e2fa576-4b8b-477e-ab18-a4050c47fd3f	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
bc86c72d-1310-4403-a6bb-7a7de7696e4d	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
e5e975aa-ba0c-47a3-98e7-94c716c89ccf	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	606b7604-e542-4d7e-bba8-81de709f2b71	{}
c4fa70f0-97d7-4dce-9d2a-1d133743431d	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	887e0fdb-494a-46aa-869f-b99740705da1	{}
11777710-4077-43c5-a01d-5645f0c5ff46	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
e4f3e265-6f71-4261-9ded-99e92a7c3d27	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
9da85749-ba89-4cfd-9bd3-e53a553542ec	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
3b6adf4e-40a6-435f-b01c-0320c3a40ec6	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	00739872-28e8-4c95-a25b-40d579702ae8	{}
cbd68e14-4a8a-475f-a639-8668f5d033ec	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
83d07130-dc4b-4ccc-b2fc-3396680043bf	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
7791a80c-c216-4072-92f3-228d0114d137	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	727d5903-9e43-4047-9274-b9722261f397	{}
b6cfc61f-d390-4f09-80c7-aebdce118bc8	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
c012ecdc-9eb6-4505-bb45-d5120679c494	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
5ea4476d-4f4d-4603-af8a-c6c45bdacaa0	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	bb561768-51b2-4cab-8079-b113796e5268	{}
d84abf35-2f12-49f1-80ea-ddf9598061ca	59e7ad24-3870-48fd-8e9e-ffb5eb46e444	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
38ae31c7-5b5d-4a52-8538-8eda19a72c7d	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	c565f657-72c6-4f14-9350-079a1b72b65a	{}
56183f0a-3310-4a34-b999-40a26b6b5e61	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
dfaa9866-446c-4d6a-94a7-7f0a06a61d59	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
3544451e-ffa6-40ff-a3a7-c36d2795bc6a	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
2cf37d2b-adfb-492e-a9f1-3e6281a899c6	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	54dd4393-88fc-4827-9705-438e6628987a	{}
13298816-a89d-4e99-a443-267eac3982a8	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
2aa99b86-37cc-4a92-a207-c31533788b95	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
dd48ee40-3ab2-4260-af1d-fca3fdbf5412	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	606b7604-e542-4d7e-bba8-81de709f2b71	{}
efb3a5bf-60df-42d5-a91b-093750d50306	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	887e0fdb-494a-46aa-869f-b99740705da1	{}
ed66f8e8-06a0-47c6-8059-c84177078abb	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
06f5e5b0-9626-41f0-97bc-671700806e45	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
628fba57-fc0f-4792-96cc-e8ed8c9584a9	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
5e57703e-56cb-49b6-83b2-314c02f93e82	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	00739872-28e8-4c95-a25b-40d579702ae8	{}
fd86ce4f-53c0-4c6c-8782-d71ed0885453	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
61f1154b-245a-44e5-aaac-ca9d1a4e7e06	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
a5c46b6e-620a-42aa-9d9f-503e1d6a2640	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	727d5903-9e43-4047-9274-b9722261f397	{}
5cf409a8-db9d-482d-8aed-48da536c1ab8	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
ca933237-474b-4995-aa80-df5458f798c3	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
07aaab4e-bf91-4cb3-ae52-543fb5aea79c	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	bb561768-51b2-4cab-8079-b113796e5268	{}
00466b6e-b024-453d-be3a-c4098f6a0d12	f7dd3228-bf2b-4859-9b19-3a55b577ae4b	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
73d6a84c-e3db-4554-806d-94e53efeaa7b	0d635dab-00fe-4790-9577-5b4c15109439	c565f657-72c6-4f14-9350-079a1b72b65a	{}
158a9a00-8d54-446c-8cf7-4ebacb672917	0d635dab-00fe-4790-9577-5b4c15109439	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
814a98c7-a9dc-416f-8050-02ecb62b9d19	0d635dab-00fe-4790-9577-5b4c15109439	54dd4393-88fc-4827-9705-438e6628987a	{}
956044a3-4762-4edb-a0ca-77403bf582f3	0d635dab-00fe-4790-9577-5b4c15109439	00739872-28e8-4c95-a25b-40d579702ae8	{}
8de8c339-815b-4280-a2bc-a45011eb0db5	0d635dab-00fe-4790-9577-5b4c15109439	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
8a03fb19-d244-4de6-a3cf-cb4658118c03	0d635dab-00fe-4790-9577-5b4c15109439	bb561768-51b2-4cab-8079-b113796e5268	{}
4736f3fd-e885-40bc-a861-be6bc1ec222f	0d635dab-00fe-4790-9577-5b4c15109439	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
15a90e3d-2dbd-49db-8a35-49a646da76a7	7355c4b4-4871-4836-95a6-5d3c64c1c1c7	606b7604-e542-4d7e-bba8-81de709f2b71	{}
a6824630-9528-414f-ad82-d437e1d13868	7355c4b4-4871-4836-95a6-5d3c64c1c1c7	887e0fdb-494a-46aa-869f-b99740705da1	{}
3bc9a9f5-8802-4712-afbf-20fc778bbfde	7355c4b4-4871-4836-95a6-5d3c64c1c1c7	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
065f9bde-886f-486b-aa1a-5d15e84d3567	7355c4b4-4871-4836-95a6-5d3c64c1c1c7	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
b6b35365-8a22-4ecc-8d0f-f3b393ab5635	7355c4b4-4871-4836-95a6-5d3c64c1c1c7	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
f45ee875-91b0-4a81-995c-a4441778ed7f	7355c4b4-4871-4836-95a6-5d3c64c1c1c7	c565f657-72c6-4f14-9350-079a1b72b65a	{}
07ee3cf8-4f1b-4f08-abf0-ead3f0870adc	7355c4b4-4871-4836-95a6-5d3c64c1c1c7	00739872-28e8-4c95-a25b-40d579702ae8	{}
435ee83f-b71f-4905-8ee0-662b9c7a004f	7355c4b4-4871-4836-95a6-5d3c64c1c1c7	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
66c7f24b-43f2-4459-bb6d-2f5919a10086	7355c4b4-4871-4836-95a6-5d3c64c1c1c7	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
f77f8fb4-07f5-4281-955b-070624aed31c	9ca9ca74-227f-4827-b087-de80bbb4e24d	be4c8197-9291-4b55-8214-d33662ddc7ea	{}
696b6c64-7a35-41cf-9186-e88b451add6f	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	1bd5a7dc-4da2-46eb-86bd-0c94d3d1a75c	{}
a393479f-7119-42b1-8d56-771f49edd261	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	aa92cda2-04af-47e3-a4a4-e8514a2984d4	{}
df46b733-211c-4875-9808-477297bac7aa	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	89e15d5b-bb0b-47cf-9e7e-e6bebe859fd2	{}
3a9fac27-2341-4af9-8336-164fb163fd58	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	7bb5df34-93cd-4da4-9822-ef0686a78535	{}
bffaf60d-9937-4bb1-8452-17ab60d896f0	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	046f23e3-dc38-4c84-9036-1f0192d29f90	{}
121e3047-bd6d-41f1-8105-21a1c28eda8a	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	7208ac08-6e96-4965-a5ac-80c0505039af	{}
cab5e061-cfba-4a06-92c4-23878c5e31e5	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	6541d4db-a4d4-4a24-b2d3-1a047906972a	{}
fb7212d1-a045-461c-a6c6-bb4e59babc8c	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	4fc1625b-8043-4011-be8c-494792476cb5	{}
562ab9f6-a80a-4de2-90f7-e24b59d99f89	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	e344c439-3e1d-4850-83d6-0806f06b1b70	{}
697a76f7-62a0-4fe0-84d5-e99e4f2b1e14	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	0131fe05-c8dc-4bf2-b74d-f9b3df48d05a	{}
292ed4cf-8bc4-4705-bc97-1b82f30985ce	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	af2cdc8f-15d8-416b-abbd-722c8e146e40	{}
ce4629ef-72ad-4f2a-82b8-51b1a08d4305	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	4e857568-7e03-4f89-a068-4d83b2a57d31	{}
48fbd898-58d7-47a4-98c6-112ab758c57f	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	d78e9127-8054-4367-bac2-001c485338ed	{}
89d1fef3-cce3-450a-8e98-9d0d48ed0c28	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	17f45225-074c-42a7-8ce3-ad3d40f24b56	{}
0797812b-89cc-4f4f-b9a2-dc0e25170955	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	587b00df-581d-4ae2-a19e-2e7da1c1c908	{}
e8408fa2-a792-4711-b115-7314f10b49b9	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	3db92f5f-44a8-4c30-a889-7b6c5c15636f	{}
c6d134b9-2a93-431a-b24f-638251d70c9a	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	40ad9d9a-2a44-4a25-b7e8-aaf69180973d	{}
dc710781-8484-4a02-8623-34ecee49cd60	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	4914a0fc-4e1d-47df-9a26-6dfdcd05d6d7	{}
5233a53a-57b2-4673-8c8d-756df5c4de10	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	7a90d4d7-2a2f-4c9b-a63d-402e7200b3e8	{}
70163671-cb31-47fa-b150-ee0d561f20a6	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	0f90e9f7-e997-4fbf-9453-854356a1d3a6	{}
0404cd69-19b3-4a8c-85a8-aeb96cd521bd	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	00d226de-caad-494e-8e1e-62e1082ab1f7	{}
eb29466e-06a3-49e6-8301-e6a6478106bc	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	9427ed61-ab76-422c-aacb-f6084021fdb5	{}
20481fae-7aae-4ff2-887a-77590e81a4b6	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	490d109c-b126-450d-a517-7e6a1f996a60	{}
9ff8d068-aaf1-4de9-80d1-38d7b03e9a45	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	016ec902-3bb8-4078-83c7-ccbdc5506b87	{}
4d599dba-d881-4703-82e7-d795c4a6bf43	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	255b36cc-883d-415f-b816-0e561b459ed0	{}
5d7f3720-61d2-4ea4-8b8f-5f34c6b49152	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	dc8eb2b9-9a38-417b-9660-9c87f7bf30e9	{}
7ce9ae84-fcfc-4f36-9220-ef062e21b350	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	017c0632-56a1-4941-84af-17f611842d3e	{}
c38f8ea1-129d-4920-acb6-d5f96e06f6b6	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	dc4e8bd1-7179-4dfc-92ca-0821e0978601	{}
43679138-6dd8-4b56-ac75-87e08b23183a	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	06e05922-a489-4cf3-bf56-bc3b7182665d	{}
c507f72e-1903-473d-85e7-f701ffd0058d	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	ca7af3c2-f6be-472d-b175-8e729ea2b527	{}
16cc2a95-867f-4b1f-8e3a-17e6705f14dd	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	fe905131-0af7-4ce3-851e-88abb5e80f2c	{}
9832d915-d240-43f7-90f9-7dc075925a10	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	f65f79ec-3ce4-4e98-9b08-76b3901ecb2b	{}
5b9f0071-ab81-48b9-9d3c-80b7edffa95a	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	b9c7ac87-1fd5-464d-b457-7b2c3fc2493d	{}
6a5c353d-b926-40ac-b0a7-d5c95548b69f	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	744b0977-bb86-4ce8-845f-32212f4bfacb	{}
fc30198b-8600-411c-91ce-6cc28909be57	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	d29b40a0-d248-472b-ab21-fadd82fbbf31	{}
20b365b9-0baa-4d0f-919c-548da7bff7f7	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	7084e5f7-575d-43fc-ae8e-b819cc2267ad	{}
7c11bacd-f0fc-4e58-9d2c-739e9f774703	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	f49e1f8e-7594-41a7-9299-41ca9e1c98be	{}
f66b1fab-8e02-424f-aaf3-042b55c29766	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	6b4ecdcc-5500-4091-8f3e-ecb94f0b7d55	{}
7427e36c-a434-41f3-b1e4-566d5762c645	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	2da18650-9590-40a2-9ec3-e4973a33e3ee	{}
c352b711-d7a8-4c95-8e4c-09bac57ae134	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	784007a6-c81d-4234-a8bb-8a035f89c06e	{}
2214b788-1262-4e6b-80cd-9a4fe5cd2f91	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	95d9f110-e9ba-4f81-b855-882e735b2e2b	{}
9a9d3589-e264-47be-bbb3-ce08b8a8b6e3	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	23053bbb-3e37-44f5-9682-44c930455fc1	{}
f2dcf781-9664-47c0-ab07-fbc775bb5fe9	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	260fc47e-2f93-4b7b-992d-724292a58bcc	{}
57778baa-6278-4495-9de6-d458913c9ac1	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	2f2e5237-c2d8-4ee8-8dec-72220be5fe51	{}
f53fc4cc-4fb5-4957-9c58-bd0b10f6257c	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	48c8f3f2-5429-43a4-a821-d698b4372f25	{}
a1ca7f02-7944-4ce5-94eb-8c55e08f855c	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	a81ee559-2472-44be-a0a0-37e6eadb3e37	{}
f20cef94-4c76-4811-b21f-d55597e33f0d	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
5bc84861-cc79-44a7-9469-f19b7113e426	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	d2694465-7e98-426e-a6f5-c63ab69594dc	{}
1c0115d8-8a20-4cbd-881d-b623b53e5980	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	1c49abd7-4666-4d3e-9e16-6451d5ee2da9	{}
68c48e2d-663c-4b13-91ac-9a24fb2d65fb	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	e822e1fe-c906-4792-bcbe-bd68eef67b24	{}
63d8a0d0-d6ec-498b-9243-d0c7d1d90375	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	1eb99a31-4619-46b0-8756-949feeb6706b	{}
56a20f4e-5f9d-4aaa-8bab-2926df008f45	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
61acf61b-2fb1-4d4d-8b68-af27a9fec576	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	bd4e5b2c-5d39-4d68-bbe9-94d9096d59f8	{}
04dcabf9-9fdd-40d4-96d4-bbe51e7a5182	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	d1913f08-d669-4f93-ae93-739e9a1dabe6	{}
f86e092c-87ce-482c-84de-d66c33d2bd72	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	a754f927-efa8-4a93-8eb9-604606f30a53	{}
04caee1d-a62c-4676-af96-b15e2c522856	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	ebe6f958-1247-4f9b-a7a4-18fde80b4c1d	{}
4a99bb54-b486-4815-b673-96fe7dcb65c1	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
c8468eeb-10e9-4639-9d6c-4b6ef6bf3a55	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	0290c46c-96ae-493a-873a-8c9acc403ec5	{}
532728d7-3c3d-415a-85a4-13321b2f068d	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	24104566-dc21-4fd0-b59a-9d1aa8d94ca2	{}
a75db287-ee82-44e2-9255-f5105aecb665	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	b73c729e-93f7-43ba-b541-3893ea43b341	{}
5c027d3d-1242-44da-b039-baacaae17167	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	adc60f1e-0b5f-49d5-b494-74c0c9e41953	{}
955407fa-ecd1-41ab-9b17-5203c222fb65	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	74a06ebe-aab2-47fb-99f8-3bd6c0f683c7	{}
236fbbf8-51e6-43ca-9512-bb6a084f4b14	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	dec8f6a3-cca8-4285-ad43-7e2736397e09	{}
0ae39542-2492-4b63-9a88-5b1840b88a34	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	b0585c03-76e3-4b44-8f53-4e6d12a08bb4	{}
8292e116-7e5d-4cfc-b584-d8819718cecd	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	4332a62f-ca79-42da-b0f5-6e6a7fd4ecbc	{}
23cb0661-9d29-48d9-9ceb-7de33a699c33	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	465150ba-7e91-4e1f-baa2-edf12c379fe2	{}
2738129a-c50c-4844-83bb-4844ccfb7c9f	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	c565f657-72c6-4f14-9350-079a1b72b65a	{}
7dca9396-2648-46fd-887f-6b43b597c2fe	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	71558b37-b72f-4b6f-84f5-22518e8f3566	{}
582b4378-acf0-468c-82bd-9250fa948754	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
0dab31ee-5158-4c53-98ae-9870a01e63c2	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	e243100d-df88-4b91-ae70-717175d3d6aa	{}
b32306ce-9d10-4907-910e-e383dbba591c	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	087ce167-b658-43de-bac7-155c71d30815	{}
904ce551-dc27-43ad-8641-d5db4d9f7524	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	00739872-28e8-4c95-a25b-40d579702ae8	{}
86a7875a-f8db-491d-b17c-972ca9600c2d	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
9d811356-7d05-4fa2-b367-860f5298119c	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
a093e491-5d74-48b8-9251-ceb487fb6872	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	727d5903-9e43-4047-9274-b9722261f397	{}
bad22492-406b-48ab-94c2-b36851f981fb	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
0f746da6-b8f6-4b5c-bdfa-5a55d5375571	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	bb561768-51b2-4cab-8079-b113796e5268	{}
c0dc0253-0bab-4ec2-8fee-85a8c90a4714	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	03ccddba-ec05-43ed-a4da-8eec9a5adcf1	{}
6d50b4ee-2778-4856-b894-59cad3411bf6	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	8da8e17f-20dc-46d6-98bc-02b34063def6	{}
5130fce2-32dc-48bf-a839-019ab58e9ac1	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	5ff658df-647c-4472-86e0-0e735797118a	{}
a450b004-e6b5-4caf-9fbb-f438bd2a0854	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	42ec4a29-a314-4c92-a8dd-7b6e229ff469	{}
d2e0cb7d-623a-4de5-aa9c-2cc75c543090	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
124e980c-4ff1-4621-a2e9-a6bbb092b8b7	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	1c67676e-6781-43ad-8e57-408369422e74	{}
cf709512-5da5-4018-940f-7496c5601d30	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	83962ac9-df0c-4422-a5ae-c223842c8382	{}
5708f232-75b7-4f0d-95e4-1e78aac901ea	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	520c47da-2c82-4b18-aba7-8503f95504f9	{}
bcbebc94-8fef-4ca8-b8a5-58e72f2e8339	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	4e69f059-314f-47e6-897f-f970eb6b6aa7	{}
bf002d13-8f7c-4c9e-84d4-913aeea10842	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	606b7604-e542-4d7e-bba8-81de709f2b71	{}
9a2b89aa-7699-4110-a8d6-fc87f36fa792	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	887e0fdb-494a-46aa-869f-b99740705da1	{}
26698247-9f8c-49fc-b81b-1280da42974f	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
dff98940-c40c-44c1-882a-f31b80bb2c8b	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
7eca8839-e5d4-4b95-a63b-888807efd417	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
a12e7592-aa5f-4176-8faa-6855c36c6ba5	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
8edd7615-fac3-4a3c-a216-2d68e9d87b85	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
158b8105-31a1-44fb-bb37-e4f3b6f6b2d4	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	54dd4393-88fc-4827-9705-438e6628987a	{}
1c4b0a6d-b039-446d-805a-dbcbcf60b67d	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
faf6419d-be8a-4588-a38e-a09389e57b59	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
2182fb23-80d9-48cb-9c91-e35548151698	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
b8172906-1e1f-4145-b2f8-b8f9c6ca6c29	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	ec4c02c9-7f8e-413c-9cfe-e812755dbf3b	{}
cc1ac249-f2b8-4f57-9446-b4c5249d7118	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	8c4b39cb-75d7-4a02-8bb4-e05320ef870e	{}
7d749e8b-3e48-4849-bd25-bfef5aec6b14	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	ff4d8d8a-3291-4e18-a2e4-7aa126c3608a	{}
b5821ebe-c519-46e0-bf4d-34eed906a2ff	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	0160b70a-f910-4613-9dc3-13e4fd773404	{}
286c96d2-e384-4e04-bb67-8ebfcc705509	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
37d2da70-f82e-4bbc-b9e2-6d610f6cd535	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	a5bd460e-2bb5-4a7f-80ea-1c0770b4d583	{}
5c15a06a-62b5-4877-a9fd-c967dabeaa21	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	64d09c38-f333-426e-8635-7c9eb27ceed0	{}
5a2f24b9-9f0d-4e27-97f8-db966f6e8613	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	b48128c1-897c-4cda-93da-6cd3f965fc23	{}
17155ce8-ff15-4ede-8fa0-091cc10f9bb2	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	ebd760a0-cb40-47cc-a4a1-d1b78271143c	{}
831b7d57-ed97-4438-84de-f64f15d7c587	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	b8992460-4387-43f1-add3-54294859d7f7	{}
cc6874df-f33c-4b58-8908-0c91467eacba	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	71898b8a-cf52-4422-bfe0-cdbf9c8b49eb	{}
ba79cc34-e4a1-4d1e-822b-abe5cd5db457	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	93891906-2a3e-4f7b-98ff-d2af686a2134	{}
36f4c3af-eafe-4a1a-8bd9-5fdd7e97efa6	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	2e09c9ee-b539-4915-bc92-cc29dd4858e3	{}
9326822d-4f6d-4dee-8b7a-d3a64bb0dac8	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	e537217a-1bc2-45a3-9564-92d9bccf9d24	{}
f36bee04-879b-40a0-a553-2a48c0c1fde6	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
b21d7497-1f29-4d5d-b343-edb354be334a	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	d715a20c-1044-4579-81c1-2689cdd39847	{}
13a754ec-9ddd-432d-8178-3c411ca52e34	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	e1d2717e-7f56-4800-bdaa-3e3e4e30746a	{}
68948e53-cbd1-49c2-8c6f-704fd5ab5405	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	71c5940e-22f4-4ad9-b850-f850688069c1	{}
a97b9b63-1816-4896-834e-eed367956d04	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	b3fcc49f-6de1-4c2c-9f7d-12a9ad85bb3c	{}
1528fede-840b-473f-ba39-68d094490742	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
309f1085-0977-4b2b-921d-b3ff7d41a477	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	70342008-ce16-4d30-b45d-d202a6b07820	{}
922c5ffe-3c91-47c7-acec-2f0a4ecd95d8	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	4621c394-fc16-4333-baf5-c50a2368948b	{}
b2ccd9ce-ea19-433f-ba3d-8e623223d3d9	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	32563007-1db7-49dc-a57c-0b93acbd889e	{}
2d27bba4-b5c5-4ab9-996e-8297cf0d80a6	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	3c11905d-a7f0-4999-8362-753655b4e48b	{}
d085a53a-909f-4397-a6c2-0b0538170604	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	7c3d284e-4ba4-44b6-b3ed-a7392c4c91fc	{}
a04f3c2a-6a78-4e2f-b359-358d5bdfcf4d	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	51226338-58c4-4623-a488-68b9ef3810b4	{}
b1561784-301d-431e-8ad8-7087f5986afc	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	8f790ad3-6ce1-4cc5-856c-4733ffeebe10	{}
f431d922-6829-44d4-b0ac-2df310aa3e8a	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	0e8250e4-4495-4b52-8168-baf4bd3042b9	{}
68b5d06c-238f-4deb-873e-09a3e03592d7	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	a773d9ec-9cb7-44d7-b037-ee429787e8b4	{}
64b4cc78-9a59-4d52-94ad-d6998e3d9908	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	be4c8197-9291-4b55-8214-d33662ddc7ea	{}
b668ad26-bb37-4913-a90f-fd5728b105c8	b85d7824-a86f-4022-a5f7-cbcde4513708	be4c8197-9291-4b55-8214-d33662ddc7ea	{}
42d0bf10-0ad4-4bc0-9d38-158fd7b30b02	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	f65f79ec-3ce4-4e98-9b08-76b3901ecb2b	{}
ccefee1d-e09a-459c-be87-6d2813c8fb76	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	b9c7ac87-1fd5-464d-b457-7b2c3fc2493d	{}
7c62157e-6758-477b-97b3-85f784b9fb06	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	744b0977-bb86-4ce8-845f-32212f4bfacb	{}
988e6616-057c-4815-91e8-2cba9f722716	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	d29b40a0-d248-472b-ab21-fadd82fbbf31	{}
6897d608-5625-47f6-a44e-6ebff1bd6de6	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	7084e5f7-575d-43fc-ae8e-b819cc2267ad	{}
90063419-2999-4a15-9ba1-2823ee6d4255	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	046f23e3-dc38-4c84-9036-1f0192d29f90	{}
e73ed49e-bc6d-419e-87b1-fdf9c6f62c49	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	f49e1f8e-7594-41a7-9299-41ca9e1c98be	{}
0c03b61f-3310-43d3-95f5-7c4f8eefc8ca	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	6b4ecdcc-5500-4091-8f3e-ecb94f0b7d55	{}
2b519f83-8a39-4089-9152-5f315ecaae7b	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	2da18650-9590-40a2-9ec3-e4973a33e3ee	{}
32977a63-7070-492e-b74d-ff69edd8d733	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	784007a6-c81d-4234-a8bb-8a035f89c06e	{}
95c677e1-2eb4-4622-8a81-16d7e6750ff5	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	95d9f110-e9ba-4f81-b855-882e735b2e2b	{}
7a10faf5-8b0e-42a0-ba98-6eaf2c9175c2	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	7208ac08-6e96-4965-a5ac-80c0505039af	{}
5cb9ea29-144b-42fc-91c6-42e8286a7cb5	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
08c45a2f-f698-482e-b1e2-cab54cfc4d4e	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	b8992460-4387-43f1-add3-54294859d7f7	{}
fa7cea14-c998-46ab-81c0-ea35694b0584	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
0919c17c-0b11-4e4e-87f6-bf10164443d6	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
851d8a3e-e52e-476f-830a-bf6bf1d14be1	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
50366aba-7f13-41ff-99bb-feef0375df9d	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
b2857fe4-f239-46a3-ba0b-9d70697ba12f	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	c565f657-72c6-4f14-9350-079a1b72b65a	{}
32ff10a9-18cd-4668-a5e5-ddd667328560	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	00739872-28e8-4c95-a25b-40d579702ae8	{}
58e493bf-16a3-46d4-9e33-3b9fffc8f117	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	bb561768-51b2-4cab-8079-b113796e5268	{}
da3fb59c-c075-4d41-86f9-c46da63da067	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
805ba8e8-a521-4ea4-acbe-fcd5d1f71472	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
ce79cb5a-69f8-4cb9-881a-eae597529802	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	606b7604-e542-4d7e-bba8-81de709f2b71	{}
e78d0dd1-adb7-4b56-8991-ececbc73aa60	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
e9759df7-53fe-4b3d-87cb-5a6092b9154d	f1e77899-8cbc-4a78-9dfa-32e6254e07b5	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
ac24d5b3-3849-475d-81f2-7e9b639ad1f4	a9e1e94e-4784-4717-814f-e83321c2140f	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
06df6d70-23cd-4424-8c5a-9802d1ff6d74	a9e1e94e-4784-4717-814f-e83321c2140f	d2694465-7e98-426e-a6f5-c63ab69594dc	{}
10fcd12e-5039-4e50-8109-23cd0b537761	a9e1e94e-4784-4717-814f-e83321c2140f	1c49abd7-4666-4d3e-9e16-6451d5ee2da9	{}
75083b1a-d25d-47d9-8a28-2d8bb3759ea3	a9e1e94e-4784-4717-814f-e83321c2140f	e822e1fe-c906-4792-bcbe-bd68eef67b24	{}
704e3e89-6f19-472d-bc9d-d30224ec32e3	a9e1e94e-4784-4717-814f-e83321c2140f	b8992460-4387-43f1-add3-54294859d7f7	{}
ff008ecf-6b0d-4727-bace-5a5dfd6f0822	a9e1e94e-4784-4717-814f-e83321c2140f	71898b8a-cf52-4422-bfe0-cdbf9c8b49eb	{}
76de950d-fffb-4659-bd34-abb688fdf67a	a9e1e94e-4784-4717-814f-e83321c2140f	93891906-2a3e-4f7b-98ff-d2af686a2134	{}
43ef55bf-9c20-4c16-9690-0b89f4f6b2fc	a9e1e94e-4784-4717-814f-e83321c2140f	2e09c9ee-b539-4915-bc92-cc29dd4858e3	{}
1cef3572-1796-427b-8800-2c4b62880d8a	a9e1e94e-4784-4717-814f-e83321c2140f	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
fba1ec1e-0e42-470b-968b-043148d14a0a	a9e1e94e-4784-4717-814f-e83321c2140f	ec4c02c9-7f8e-413c-9cfe-e812755dbf3b	{}
10e2358d-74d5-436f-82b6-a9a37e0b413f	a9e1e94e-4784-4717-814f-e83321c2140f	8c4b39cb-75d7-4a02-8bb4-e05320ef870e	{}
8fb0e7bb-6b03-4630-adfc-8e95dabc24c4	a9e1e94e-4784-4717-814f-e83321c2140f	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
e23fa2bb-a994-4c49-8c41-625e64a29fed	a9e1e94e-4784-4717-814f-e83321c2140f	c565f657-72c6-4f14-9350-079a1b72b65a	{}
e8e8aae9-650c-4067-8a8b-9ef9213c7e03	a9e1e94e-4784-4717-814f-e83321c2140f	00739872-28e8-4c95-a25b-40d579702ae8	{}
66b1e3cd-1e47-4b4b-9ee4-80fcd87a4ef3	a9e1e94e-4784-4717-814f-e83321c2140f	bb561768-51b2-4cab-8079-b113796e5268	{}
a384505c-5d19-483f-8451-93aa6bddae3d	a9e1e94e-4784-4717-814f-e83321c2140f	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
e0c3aad5-8d45-4d2b-bf4f-4a1fd9f7d1e6	a9e1e94e-4784-4717-814f-e83321c2140f	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
e2d521a8-394d-4e5b-b2ca-b3bfa1b828e0	a9e1e94e-4784-4717-814f-e83321c2140f	606b7604-e542-4d7e-bba8-81de709f2b71	{}
30052ade-eb61-469c-9cfc-61fd61b3869d	ab3a1aa6-8848-4552-8b29-21caff47549c	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
680593cc-ba9e-4b07-acbc-cb8cde219c0e	ab3a1aa6-8848-4552-8b29-21caff47549c	bd4e5b2c-5d39-4d68-bbe9-94d9096d59f8	{}
782881ec-e6da-4079-b1d9-489a04098315	ab3a1aa6-8848-4552-8b29-21caff47549c	d1913f08-d669-4f93-ae93-739e9a1dabe6	{}
8be9d20d-7f28-4c79-a27a-5ff340f25bd2	ab3a1aa6-8848-4552-8b29-21caff47549c	a754f927-efa8-4a93-8eb9-604606f30a53	{}
36882574-4cc7-486a-873a-5cddbf33c6c4	ab3a1aa6-8848-4552-8b29-21caff47549c	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
1fc07f40-0701-4a4b-bbee-474cd6dd0986	ab3a1aa6-8848-4552-8b29-21caff47549c	d715a20c-1044-4579-81c1-2689cdd39847	{}
2795c221-8802-420f-bcaa-fb74b6b4262e	ab3a1aa6-8848-4552-8b29-21caff47549c	e1d2717e-7f56-4800-bdaa-3e3e4e30746a	{}
2d6f2b9e-e339-4d55-a5b9-029b0e40eec8	ab3a1aa6-8848-4552-8b29-21caff47549c	71c5940e-22f4-4ad9-b850-f850688069c1	{}
a67faef1-fd23-4fe0-b46c-eed9a0f9e9a8	ab3a1aa6-8848-4552-8b29-21caff47549c	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
6cb59432-b9f0-4a5d-a1c8-5ee64751c825	ab3a1aa6-8848-4552-8b29-21caff47549c	c565f657-72c6-4f14-9350-079a1b72b65a	{}
fdadb067-42a6-4c91-b5ad-e3a01475c8cc	ab3a1aa6-8848-4552-8b29-21caff47549c	00739872-28e8-4c95-a25b-40d579702ae8	{}
28a485e8-33f2-448d-85a1-576482a1709f	ab3a1aa6-8848-4552-8b29-21caff47549c	bb561768-51b2-4cab-8079-b113796e5268	{}
bde26bf9-4bca-49bb-b86e-dec6fa953d8a	ab3a1aa6-8848-4552-8b29-21caff47549c	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
ff920c3e-9c99-41e8-bc81-d0406d91fe05	ab3a1aa6-8848-4552-8b29-21caff47549c	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
4224f24e-2860-40c8-90a6-7a869b909089	ab3a1aa6-8848-4552-8b29-21caff47549c	606b7604-e542-4d7e-bba8-81de709f2b71	{}
3056be76-9c40-4509-afe7-4caedff29a72	351e367e-4947-4fed-abf2-7e4b20d23e79	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
1d73941e-7867-4951-bba2-1efecd44a1d4	351e367e-4947-4fed-abf2-7e4b20d23e79	70342008-ce16-4d30-b45d-d202a6b07820	{}
cb816a9c-c807-405c-bcc6-909b63911f0b	351e367e-4947-4fed-abf2-7e4b20d23e79	4621c394-fc16-4333-baf5-c50a2368948b	{}
800fd437-c153-4abf-ac8f-ff4e52aaf282	351e367e-4947-4fed-abf2-7e4b20d23e79	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
2ff207d7-61d9-4657-8608-a5f173f0eff3	351e367e-4947-4fed-abf2-7e4b20d23e79	a5bd460e-2bb5-4a7f-80ea-1c0770b4d583	{}
c00fe85e-ac9f-4bc9-b321-a64799d19218	351e367e-4947-4fed-abf2-7e4b20d23e79	64d09c38-f333-426e-8635-7c9eb27ceed0	{}
e31c7cee-059b-4c02-8578-aaf020e4ebc8	351e367e-4947-4fed-abf2-7e4b20d23e79	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
f32bf268-6fac-4bfa-9375-9674fbac862e	39c33874-ce0f-46b6-9f61-0a872b6d1d97	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
59b13638-535a-4a5d-9f6f-01729ef75935	39c33874-ce0f-46b6-9f61-0a872b6d1d97	0290c46c-96ae-493a-873a-8c9acc403ec5	{}
b55e33c7-90e9-4f68-acf7-befbf5a008c0	39c33874-ce0f-46b6-9f61-0a872b6d1d97	24104566-dc21-4fd0-b59a-9d1aa8d94ca2	{}
15b11bc8-01b3-4a83-b820-7e67c347fc11	39c33874-ce0f-46b6-9f61-0a872b6d1d97	b73c729e-93f7-43ba-b541-3893ea43b341	{}
76200bf4-7b55-4f4c-a92c-897625a36946	39c33874-ce0f-46b6-9f61-0a872b6d1d97	c565f657-72c6-4f14-9350-079a1b72b65a	{}
5b1cbefc-121c-4533-81bb-2d9cf61f808f	39c33874-ce0f-46b6-9f61-0a872b6d1d97	71558b37-b72f-4b6f-84f5-22518e8f3566	{}
2852964c-b17f-484f-b199-cc02a35bff36	39c33874-ce0f-46b6-9f61-0a872b6d1d97	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
4bc06349-993d-4199-a3f4-cbded2f4be99	39c33874-ce0f-46b6-9f61-0a872b6d1d97	e243100d-df88-4b91-ae70-717175d3d6aa	{}
9fbf3dea-3b45-4bc5-884c-f1c5ac86cee6	39c33874-ce0f-46b6-9f61-0a872b6d1d97	087ce167-b658-43de-bac7-155c71d30815	{}
1d194d0a-a272-4441-80e6-5faf699f9ef5	39c33874-ce0f-46b6-9f61-0a872b6d1d97	00739872-28e8-4c95-a25b-40d579702ae8	{}
9b14b664-2ede-4c7f-8dc5-d30650779f05	39c33874-ce0f-46b6-9f61-0a872b6d1d97	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
1fad1929-1a0f-4603-94c0-e64922937339	39c33874-ce0f-46b6-9f61-0a872b6d1d97	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
bf3be680-0d46-4eae-bd93-910c13e63ba6	39c33874-ce0f-46b6-9f61-0a872b6d1d97	727d5903-9e43-4047-9274-b9722261f397	{}
98f5ce60-3445-4946-a6cb-97395318376a	39c33874-ce0f-46b6-9f61-0a872b6d1d97	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
7479f847-21e2-4151-b271-68af4d3359c3	39c33874-ce0f-46b6-9f61-0a872b6d1d97	bb561768-51b2-4cab-8079-b113796e5268	{}
a2d7c305-e031-4933-8558-2dbc9ea1eb36	39c33874-ce0f-46b6-9f61-0a872b6d1d97	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
5a95ea01-d2a6-4128-ac3f-01496e70b86e	39c33874-ce0f-46b6-9f61-0a872b6d1d97	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
95c399ec-84f6-46ba-a020-11752d5b54b5	39c33874-ce0f-46b6-9f61-0a872b6d1d97	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
13905cc0-7b48-4d72-a57a-c014b95e89b5	39c33874-ce0f-46b6-9f61-0a872b6d1d97	54dd4393-88fc-4827-9705-438e6628987a	{}
2ded8218-27ba-4e23-83af-cdecd38c476d	39c33874-ce0f-46b6-9f61-0a872b6d1d97	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
2b348565-fe0e-4284-a5d5-ba57912360b7	39c33874-ce0f-46b6-9f61-0a872b6d1d97	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
b396d5e6-c261-4da9-a197-49264ad4fc66	39c33874-ce0f-46b6-9f61-0a872b6d1d97	606b7604-e542-4d7e-bba8-81de709f2b71	{}
cbbc05b6-bd5e-4229-800d-8be156ebe296	39c33874-ce0f-46b6-9f61-0a872b6d1d97	887e0fdb-494a-46aa-869f-b99740705da1	{}
be6312ce-c816-4360-8e57-d6d3ad6dd828	39c33874-ce0f-46b6-9f61-0a872b6d1d97	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
7d0a185a-5482-4101-88b6-c0768d6258b7	39c33874-ce0f-46b6-9f61-0a872b6d1d97	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
957cbfb2-3cf1-4a40-a21f-640ec13044e7	39c33874-ce0f-46b6-9f61-0a872b6d1d97	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
249def85-e27f-4b81-8e82-2bee6dc01d00	93f68d93-c156-408c-a5dc-23ba510051f2	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
dc722393-dd0c-458a-87ad-dc0cd1d76ac2	93f68d93-c156-408c-a5dc-23ba510051f2	b8992460-4387-43f1-add3-54294859d7f7	{}
cbc43b53-54be-44b9-84a4-cad08d901579	93f68d93-c156-408c-a5dc-23ba510051f2	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
679b213e-31bd-43de-bc3c-f74b84b65c23	93f68d93-c156-408c-a5dc-23ba510051f2	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
e4fce58b-306b-48c5-9bb6-4a53742f24cd	93f68d93-c156-408c-a5dc-23ba510051f2	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
e0d43934-6487-4f6c-a3a9-2bc94bd240e9	93f68d93-c156-408c-a5dc-23ba510051f2	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
8c7fd1a7-9f15-4aaa-8431-063762baa309	93f68d93-c156-408c-a5dc-23ba510051f2	c565f657-72c6-4f14-9350-079a1b72b65a	{}
65fc44b6-11ac-4812-9a1c-50ca438a973f	93f68d93-c156-408c-a5dc-23ba510051f2	00739872-28e8-4c95-a25b-40d579702ae8	{}
272fd251-ac95-4f6e-9445-95f58c8c104a	93f68d93-c156-408c-a5dc-23ba510051f2	bb561768-51b2-4cab-8079-b113796e5268	{}
de02ba9f-37ac-493c-8d6f-712dec68ffd4	93f68d93-c156-408c-a5dc-23ba510051f2	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
5ef71e51-fb6a-4e1b-bd59-421f0148c122	93f68d93-c156-408c-a5dc-23ba510051f2	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
d9dafe36-2c08-4af0-b1df-3afb7b11224f	93f68d93-c156-408c-a5dc-23ba510051f2	606b7604-e542-4d7e-bba8-81de709f2b71	{}
58c1b1e5-371e-483a-b251-91673435ad14	93f68d93-c156-408c-a5dc-23ba510051f2	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
8a79c55d-c6e3-40cb-8c72-e21b8b0791b8	93f68d93-c156-408c-a5dc-23ba510051f2	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
9cee03ad-c395-4c9e-be61-048066a8e9fd	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	c565f657-72c6-4f14-9350-079a1b72b65a	{}
0f4e99bf-d254-4220-898f-d2a0d74a801c	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	71558b37-b72f-4b6f-84f5-22518e8f3566	{}
7d759632-b639-4c8e-8b93-a1b626a42122	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
770fa93a-18fb-45f6-a19f-c3f37355bdb6	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	e243100d-df88-4b91-ae70-717175d3d6aa	{}
5c602357-d973-4e88-bec1-11f2087d8044	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	087ce167-b658-43de-bac7-155c71d30815	{}
78a16339-e67c-47a2-aabb-c6a9b0c6bdb4	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
65edb76e-2fb9-4876-9b33-7d06d85b6924	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
0ff0d624-6e0e-4265-b08a-ea186a3e27b5	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	54dd4393-88fc-4827-9705-438e6628987a	{}
d6d6c5e9-863c-4fff-bb0d-dc317d3e9b40	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
552862ab-2e0a-4349-9823-ae9e970aa580	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
efaf9eca-aa0e-4750-a23f-b819ca1bc00e	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	606b7604-e542-4d7e-bba8-81de709f2b71	{}
658c7aa9-2cbd-4b58-8feb-2e8bc9bf9585	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	887e0fdb-494a-46aa-869f-b99740705da1	{}
d6e36ee3-2dc6-4ea8-b6e7-69ac6f1dc066	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
81805911-a900-4c00-a307-e2e078fd063e	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
42794cd9-f8c6-492c-8be8-e8a8c3c30afd	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
aa0604ee-b272-40e2-82b0-97ab94865ef4	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	00739872-28e8-4c95-a25b-40d579702ae8	{}
0f7ef500-65d2-4425-a310-88c813d23923	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
f3d780a3-6124-42e1-8bc2-b119cf2200ce	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
7f0bdf01-4fbd-43f8-b77c-c21847702a16	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	727d5903-9e43-4047-9274-b9722261f397	{}
f920b76b-a234-4705-a90b-01cbdab8b514	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
8214a7e4-1d68-429d-a7e3-8d73e338f190	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
aa006df1-c598-4127-a85b-85aaf1e78791	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	bb561768-51b2-4cab-8079-b113796e5268	{}
3f336778-6083-4396-a6ec-3f257b558647	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
ec1ade02-e607-4ad9-82d0-55db74d261b7	42146f28-9b13-4af1-acd7-9d3da69b15d0	c565f657-72c6-4f14-9350-079a1b72b65a	{}
de5d32c5-2d48-4136-9a68-cc84c3f716f8	42146f28-9b13-4af1-acd7-9d3da69b15d0	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
99299312-4f57-48b5-b526-26e536775e5c	42146f28-9b13-4af1-acd7-9d3da69b15d0	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
cd19fbac-762a-46aa-a67d-a50d3d59a66a	42146f28-9b13-4af1-acd7-9d3da69b15d0	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
9ab6d796-9106-4649-bac7-b2ac9fc342f2	42146f28-9b13-4af1-acd7-9d3da69b15d0	54dd4393-88fc-4827-9705-438e6628987a	{}
f570c589-5045-4992-953b-d9d76bde9555	42146f28-9b13-4af1-acd7-9d3da69b15d0	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
1130510c-dcc1-4bdd-83df-2e4977d24fdd	42146f28-9b13-4af1-acd7-9d3da69b15d0	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
5943a3fe-97ab-4708-a097-691c97713b01	42146f28-9b13-4af1-acd7-9d3da69b15d0	606b7604-e542-4d7e-bba8-81de709f2b71	{}
0e3b249b-4aab-4a37-a596-6181f2ba7f82	42146f28-9b13-4af1-acd7-9d3da69b15d0	887e0fdb-494a-46aa-869f-b99740705da1	{}
846fda76-cb5c-4b36-85c6-c30bbbf59527	42146f28-9b13-4af1-acd7-9d3da69b15d0	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
6e1f6c75-9a3a-45d1-903c-09a7ff5bfba4	42146f28-9b13-4af1-acd7-9d3da69b15d0	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
5c483363-a323-474d-8fae-040b49bee9fe	42146f28-9b13-4af1-acd7-9d3da69b15d0	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
8cc54a01-b066-4b53-acd6-cb014325014c	42146f28-9b13-4af1-acd7-9d3da69b15d0	00739872-28e8-4c95-a25b-40d579702ae8	{}
f7ca9872-2e51-4148-90e5-6ac7b81c23a3	42146f28-9b13-4af1-acd7-9d3da69b15d0	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
689e73e1-df21-4f35-9f52-5645bf0fdb44	42146f28-9b13-4af1-acd7-9d3da69b15d0	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
9d59e7fe-7491-4bdc-8f7c-9409b2986908	42146f28-9b13-4af1-acd7-9d3da69b15d0	727d5903-9e43-4047-9274-b9722261f397	{}
7fba0c80-0715-40bb-a41f-8ca207247310	42146f28-9b13-4af1-acd7-9d3da69b15d0	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
e69a00bc-72a5-4f29-a619-826e5e41d6a5	42146f28-9b13-4af1-acd7-9d3da69b15d0	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
e335f60b-02cc-495e-ac5b-479324553a2d	42146f28-9b13-4af1-acd7-9d3da69b15d0	bb561768-51b2-4cab-8079-b113796e5268	{}
f3a8f23b-8a02-4be5-b194-f3a6d67d0cea	42146f28-9b13-4af1-acd7-9d3da69b15d0	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
c6ea238b-9131-40ea-bdd6-7e1b252730b8	e8c6a44d-8395-47f4-bea1-043c379b3560	c565f657-72c6-4f14-9350-079a1b72b65a	{}
8953976c-98df-4010-a029-d988cee7c31b	e8c6a44d-8395-47f4-bea1-043c379b3560	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
63221d8f-bfe3-4ce8-b976-f16f1032b74c	e8c6a44d-8395-47f4-bea1-043c379b3560	54dd4393-88fc-4827-9705-438e6628987a	{}
1d3abcef-fc04-47bd-b1d0-dabefa1c27a7	e8c6a44d-8395-47f4-bea1-043c379b3560	00739872-28e8-4c95-a25b-40d579702ae8	{}
1d6d6a39-a1d4-4c7e-b8b0-d690c196d8b1	e8c6a44d-8395-47f4-bea1-043c379b3560	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
0897d8c1-8bb8-493e-851a-cdaeae3688cc	e8c6a44d-8395-47f4-bea1-043c379b3560	bb561768-51b2-4cab-8079-b113796e5268	{}
449354c7-b7f1-4e35-b175-c44b113f85ed	e8c6a44d-8395-47f4-bea1-043c379b3560	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
82cbef45-d113-4b61-a5e7-271cee9fec85	4cfde21e-b474-4f74-9933-662c4f34863a	606b7604-e542-4d7e-bba8-81de709f2b71	{}
a1dfb7a4-6ce3-4be9-a495-234bfd95f7e5	4cfde21e-b474-4f74-9933-662c4f34863a	887e0fdb-494a-46aa-869f-b99740705da1	{}
b59c12c4-d2eb-47c3-821e-e19076306893	4cfde21e-b474-4f74-9933-662c4f34863a	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
7f6279fa-5915-4d99-801c-93034db5a464	4cfde21e-b474-4f74-9933-662c4f34863a	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
db18f51a-aa20-4351-8784-a3e7acd22090	4cfde21e-b474-4f74-9933-662c4f34863a	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
ca3704eb-62b4-411a-ae09-3dbf5ed12723	4cfde21e-b474-4f74-9933-662c4f34863a	c565f657-72c6-4f14-9350-079a1b72b65a	{}
f531b8e3-9542-4edc-986c-c6029762d226	4cfde21e-b474-4f74-9933-662c4f34863a	00739872-28e8-4c95-a25b-40d579702ae8	{}
2872afd3-6b1a-4b0b-9ade-f442eba54fee	4cfde21e-b474-4f74-9933-662c4f34863a	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
800d82fa-a6a4-4f15-855b-8a6adcba4859	4cfde21e-b474-4f74-9933-662c4f34863a	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
a09992fb-2cda-4446-8647-0e3a393adbb7	b09987b7-850d-40cb-b545-395cef1a27fe	be4c8197-9291-4b55-8214-d33662ddc7ea	{}
15c11369-fd19-4d01-8935-3516902f2166	26e95172-da8c-42f4-be74-6b2a911dd002	be4c8197-9291-4b55-8214-d33662ddc7ea	{}
47b53243-9183-4eec-8bc1-7f6af8f9468a	ab071494-85c9-46de-adca-a092077ffa4d	f65f79ec-3ce4-4e98-9b08-76b3901ecb2b	{}
ca732b29-3163-4c76-9382-f8b8ef84459a	ab071494-85c9-46de-adca-a092077ffa4d	b9c7ac87-1fd5-464d-b457-7b2c3fc2493d	{}
dbb75f92-2e4c-4a07-af36-cbcd03116d1b	ab071494-85c9-46de-adca-a092077ffa4d	744b0977-bb86-4ce8-845f-32212f4bfacb	{}
c9296004-0bf4-4771-97da-cf594acce874	ab071494-85c9-46de-adca-a092077ffa4d	d29b40a0-d248-472b-ab21-fadd82fbbf31	{}
3608b8a9-0970-4aa5-970d-0134479a0e69	ab071494-85c9-46de-adca-a092077ffa4d	7084e5f7-575d-43fc-ae8e-b819cc2267ad	{}
916789a3-91b5-48f0-a178-86710323df6b	ab071494-85c9-46de-adca-a092077ffa4d	046f23e3-dc38-4c84-9036-1f0192d29f90	{}
856fb628-f414-4fa4-8ece-be7abf6e5035	ab071494-85c9-46de-adca-a092077ffa4d	f49e1f8e-7594-41a7-9299-41ca9e1c98be	{}
0df6ab41-8856-41fc-8c3b-1136f6298053	ab071494-85c9-46de-adca-a092077ffa4d	6b4ecdcc-5500-4091-8f3e-ecb94f0b7d55	{}
1cb3ef95-2f30-4a86-a339-a154746476ca	ab071494-85c9-46de-adca-a092077ffa4d	2da18650-9590-40a2-9ec3-e4973a33e3ee	{}
628a9b9e-9790-4b2b-8f61-9120a08c2ddd	ab071494-85c9-46de-adca-a092077ffa4d	784007a6-c81d-4234-a8bb-8a035f89c06e	{}
4614fd90-bb67-427c-a1ec-9cc8c99cfa54	ab071494-85c9-46de-adca-a092077ffa4d	95d9f110-e9ba-4f81-b855-882e735b2e2b	{}
5b1fd921-0310-481e-a88e-719f5d55c328	ab071494-85c9-46de-adca-a092077ffa4d	7208ac08-6e96-4965-a5ac-80c0505039af	{}
d7e06bfb-c1c3-4e0c-8896-323cb56a4b70	ab071494-85c9-46de-adca-a092077ffa4d	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
b624df71-c36b-4c13-b1f5-9ad14fb4546f	ab071494-85c9-46de-adca-a092077ffa4d	b8992460-4387-43f1-add3-54294859d7f7	{}
ffe4ef7c-8aca-4964-bb75-4d60586013b8	ab071494-85c9-46de-adca-a092077ffa4d	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
a14e59c0-a7b0-4f89-ad8e-f6fd40ef5dca	ab071494-85c9-46de-adca-a092077ffa4d	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
6dd0f67e-0b26-40ac-89a0-d7080f98627a	ab071494-85c9-46de-adca-a092077ffa4d	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
1d0c6d7c-81c5-4a96-9369-7a04a8e14571	ab071494-85c9-46de-adca-a092077ffa4d	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
3c1d3814-90c1-430d-9c42-1d1993e0625c	ab071494-85c9-46de-adca-a092077ffa4d	c565f657-72c6-4f14-9350-079a1b72b65a	{}
594a60d6-e543-401b-887a-81fbd0db275f	ab071494-85c9-46de-adca-a092077ffa4d	00739872-28e8-4c95-a25b-40d579702ae8	{}
4fa378a7-394a-4ccd-bae5-5ea9dc4253cf	ab071494-85c9-46de-adca-a092077ffa4d	bb561768-51b2-4cab-8079-b113796e5268	{}
e0eed339-4ddc-493b-a11d-69a09c5f6dbc	ab071494-85c9-46de-adca-a092077ffa4d	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
d00e752f-f917-4bac-8a4d-0b179d495d83	ab071494-85c9-46de-adca-a092077ffa4d	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
253f4351-eb6f-4004-bf9b-42ef1f7d645c	ab071494-85c9-46de-adca-a092077ffa4d	606b7604-e542-4d7e-bba8-81de709f2b71	{}
a647d5f2-6a5b-4f2a-a260-c29d59b0a869	ab071494-85c9-46de-adca-a092077ffa4d	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
cacf6c5f-3307-4b7a-9f06-7d1229b107c7	ab071494-85c9-46de-adca-a092077ffa4d	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
e53b30c2-0c46-4a75-9159-0bdccb85041a	2c923ed8-faae-498f-b65f-f695cdbd7282	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
36c3e02c-297f-4db3-baae-46da5a148077	2c923ed8-faae-498f-b65f-f695cdbd7282	d2694465-7e98-426e-a6f5-c63ab69594dc	{}
5fdfbec4-4676-4a9e-8b0e-9f7f127fe40b	2c923ed8-faae-498f-b65f-f695cdbd7282	1c49abd7-4666-4d3e-9e16-6451d5ee2da9	{}
42f833d8-51bd-4a43-9124-fd09eedcddf8	2c923ed8-faae-498f-b65f-f695cdbd7282	e822e1fe-c906-4792-bcbe-bd68eef67b24	{}
44f5a3cf-7f70-4451-8838-98b7567c57fa	2c923ed8-faae-498f-b65f-f695cdbd7282	b8992460-4387-43f1-add3-54294859d7f7	{}
0a81b7a4-7c27-4d5f-9119-cf00d4c19445	2c923ed8-faae-498f-b65f-f695cdbd7282	71898b8a-cf52-4422-bfe0-cdbf9c8b49eb	{}
e62aca29-4f21-4a0b-be26-46d0cc749872	2c923ed8-faae-498f-b65f-f695cdbd7282	93891906-2a3e-4f7b-98ff-d2af686a2134	{}
7f7948a1-7d41-4b31-a9c3-bcf735f9ac08	2c923ed8-faae-498f-b65f-f695cdbd7282	2e09c9ee-b539-4915-bc92-cc29dd4858e3	{}
b457beb5-9c6a-49a6-a5f6-5df555722810	2c923ed8-faae-498f-b65f-f695cdbd7282	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
cf82dd54-b66c-4828-8c78-0b0ed91c19e4	2c923ed8-faae-498f-b65f-f695cdbd7282	ec4c02c9-7f8e-413c-9cfe-e812755dbf3b	{}
69703e5a-1a65-423e-aa88-804dbddd9960	2c923ed8-faae-498f-b65f-f695cdbd7282	8c4b39cb-75d7-4a02-8bb4-e05320ef870e	{}
1342772e-44ad-4298-a102-d179707c066b	2c923ed8-faae-498f-b65f-f695cdbd7282	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
0dc9a706-1ea5-47e3-a781-7b5991715dcb	2c923ed8-faae-498f-b65f-f695cdbd7282	c565f657-72c6-4f14-9350-079a1b72b65a	{}
adf7cd34-3d1e-453e-b59f-915a9f6ceaf3	2c923ed8-faae-498f-b65f-f695cdbd7282	00739872-28e8-4c95-a25b-40d579702ae8	{}
7eb477e9-c502-48c7-ae85-eda8ff20d355	2c923ed8-faae-498f-b65f-f695cdbd7282	bb561768-51b2-4cab-8079-b113796e5268	{}
da5de240-84f7-4feb-a79c-daf221641f0e	2c923ed8-faae-498f-b65f-f695cdbd7282	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
ac9e0cc0-bf4f-4734-ad4a-3a495cf115b2	2c923ed8-faae-498f-b65f-f695cdbd7282	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
ec2da1c9-f9c8-465a-bf45-25462f249e99	2c923ed8-faae-498f-b65f-f695cdbd7282	606b7604-e542-4d7e-bba8-81de709f2b71	{}
49213ae7-7952-4a77-9aeb-9a4f2d7170c4	d06ba299-c4cc-4da8-ae83-35153b422082	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
8ad4757b-c8fb-45e9-8cfe-b620e78081bd	d06ba299-c4cc-4da8-ae83-35153b422082	bd4e5b2c-5d39-4d68-bbe9-94d9096d59f8	{}
804cc41a-eb62-460e-9605-ba5aed3f9326	d06ba299-c4cc-4da8-ae83-35153b422082	d1913f08-d669-4f93-ae93-739e9a1dabe6	{}
3c3192bc-add4-4ed8-b72e-fec01a474659	d06ba299-c4cc-4da8-ae83-35153b422082	a754f927-efa8-4a93-8eb9-604606f30a53	{}
5284e76c-7e7f-4179-a1bd-bf52f25f5ba5	d06ba299-c4cc-4da8-ae83-35153b422082	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
8c680b4e-cdd5-4050-aa80-17b559e73f2f	d06ba299-c4cc-4da8-ae83-35153b422082	d715a20c-1044-4579-81c1-2689cdd39847	{}
31ab9470-2725-4f25-8b2e-80537e54d3f1	d06ba299-c4cc-4da8-ae83-35153b422082	e1d2717e-7f56-4800-bdaa-3e3e4e30746a	{}
25d7e8ea-fa0e-4489-8453-dbf8fdb9805c	d06ba299-c4cc-4da8-ae83-35153b422082	71c5940e-22f4-4ad9-b850-f850688069c1	{}
d484564a-958e-4d80-9437-99ae782304ad	d06ba299-c4cc-4da8-ae83-35153b422082	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
65aef0a9-7e67-4d10-9f10-85bcea0d9b7e	d06ba299-c4cc-4da8-ae83-35153b422082	c565f657-72c6-4f14-9350-079a1b72b65a	{}
60c41113-dfa7-4cfd-b7d3-a88f46c4d878	d06ba299-c4cc-4da8-ae83-35153b422082	00739872-28e8-4c95-a25b-40d579702ae8	{}
5946a5e8-8496-464a-9a0c-bb5b63df0750	d06ba299-c4cc-4da8-ae83-35153b422082	bb561768-51b2-4cab-8079-b113796e5268	{}
e7a1f46a-212e-43b6-a6ec-674495289d22	d06ba299-c4cc-4da8-ae83-35153b422082	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
31a906af-ccab-42a0-94df-f311f3100cf1	d06ba299-c4cc-4da8-ae83-35153b422082	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
d1665ef3-2d0c-4fcb-81bc-2f0701de767b	d06ba299-c4cc-4da8-ae83-35153b422082	606b7604-e542-4d7e-bba8-81de709f2b71	{}
89555ea4-d6b8-4eff-978a-0d8eaaff8136	e4192c84-8700-4949-8f9c-3b642954cb21	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
47ef3638-6fba-48ef-970a-8fa109cecbf7	e4192c84-8700-4949-8f9c-3b642954cb21	70342008-ce16-4d30-b45d-d202a6b07820	{}
133431c9-3275-4633-b998-a5bcdeb93e15	e4192c84-8700-4949-8f9c-3b642954cb21	4621c394-fc16-4333-baf5-c50a2368948b	{}
5b138bae-7483-4e7d-a987-6bd41755c1d3	e4192c84-8700-4949-8f9c-3b642954cb21	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
889b768c-9a87-46dc-a6a2-c20ca81c6974	e4192c84-8700-4949-8f9c-3b642954cb21	a5bd460e-2bb5-4a7f-80ea-1c0770b4d583	{}
af1b25bc-d683-4f79-8abb-8a428731bafe	e4192c84-8700-4949-8f9c-3b642954cb21	64d09c38-f333-426e-8635-7c9eb27ceed0	{}
a59709df-7119-4b1e-b1c0-fa6f8d7e1d1c	e4192c84-8700-4949-8f9c-3b642954cb21	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
4eb1d9a0-850a-415c-b708-2aba89d352e0	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
34623ba6-5835-4177-8a2d-755aebf4ef49	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	0290c46c-96ae-493a-873a-8c9acc403ec5	{}
f10fcf16-baa7-4b22-b6cc-6e455fbfff88	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	24104566-dc21-4fd0-b59a-9d1aa8d94ca2	{}
a2f8934c-54bc-4c3a-834f-e2fb8c8aa111	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	b73c729e-93f7-43ba-b541-3893ea43b341	{}
49553327-e271-44bb-ba25-96fc966fffd1	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	c565f657-72c6-4f14-9350-079a1b72b65a	{}
68fb6302-a83e-4281-aba4-3f1bed9d130a	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	71558b37-b72f-4b6f-84f5-22518e8f3566	{}
5685294e-e836-48fd-aa6e-aa3021e89cbb	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
b77d5050-792b-4784-804b-359f0cc3d499	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	e243100d-df88-4b91-ae70-717175d3d6aa	{}
5c66eefd-15f6-4acf-a21d-9ed0d924b0c7	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	087ce167-b658-43de-bac7-155c71d30815	{}
f9dc2132-c383-44e5-a77d-17e17a789e7c	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	00739872-28e8-4c95-a25b-40d579702ae8	{}
2499b495-7b20-4aa3-9c5b-eaf56772314f	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
9b84a225-3eb9-4e96-bfe9-d8cd2808655d	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
ecabeb4d-27cd-4125-83a3-34e8cc074192	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	727d5903-9e43-4047-9274-b9722261f397	{}
286f8ce9-1721-4a95-bdd0-09d222f97117	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
08007879-276e-4eeb-a52e-1d09c838ddb6	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	bb561768-51b2-4cab-8079-b113796e5268	{}
7408720f-86a8-46d5-ac63-0003d0f36f7c	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
010d2438-5656-4dd3-8fb9-1c273b712ea2	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
8996a19d-2f18-46d6-8524-c1eff25c1c88	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
3422617d-b6de-437f-b0bc-c76753d82f05	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	54dd4393-88fc-4827-9705-438e6628987a	{}
bd0e16c2-8e98-4583-ad6b-acf86c6712ad	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
ac4f3b92-cd93-453b-b6e0-534337f205f9	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
75698031-fa88-4642-a2e4-2ea96b71c49b	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	606b7604-e542-4d7e-bba8-81de709f2b71	{}
1b343ff0-12a4-43ef-8d7a-82833355b9fb	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	887e0fdb-494a-46aa-869f-b99740705da1	{}
788fa5ec-e52d-432a-b21d-4a33b30050c0	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
784c8dd9-06c3-40a8-83ac-0b60512c433c	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
ce1083e7-852a-4756-9bfb-45347e21a6db	fdc0aba9-365b-4cf3-bce6-cd9b554579e5	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
6fcc646d-5f75-475e-83f4-38dd355197cd	4fe02094-9504-430b-ae3c-cf28260a3bb4	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
88fd4ba0-3820-4714-90a1-c626b4ac1f70	4fe02094-9504-430b-ae3c-cf28260a3bb4	b8992460-4387-43f1-add3-54294859d7f7	{}
59fc56c3-bc0c-4c10-ac66-0b28dfa30783	4fe02094-9504-430b-ae3c-cf28260a3bb4	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
6c111e01-f79f-4fa6-9c13-027304ef9db4	4fe02094-9504-430b-ae3c-cf28260a3bb4	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
1caa6d6a-fb65-4187-97dc-867e5becfcc2	4fe02094-9504-430b-ae3c-cf28260a3bb4	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
397a6b66-1d2e-4e5a-887d-6d10e23a3d09	4fe02094-9504-430b-ae3c-cf28260a3bb4	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
7bbdd8c2-f789-46a7-9733-ab3efb730542	4fe02094-9504-430b-ae3c-cf28260a3bb4	c565f657-72c6-4f14-9350-079a1b72b65a	{}
c5edc80d-57ac-4c48-98ce-ae8c7b01fc1e	4fe02094-9504-430b-ae3c-cf28260a3bb4	00739872-28e8-4c95-a25b-40d579702ae8	{}
2ec7fb6f-a787-40b0-a7fb-a6b09f4e934f	4fe02094-9504-430b-ae3c-cf28260a3bb4	bb561768-51b2-4cab-8079-b113796e5268	{}
dd3fcc64-1752-43df-b89b-cdfb1bd92671	4fe02094-9504-430b-ae3c-cf28260a3bb4	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
5e394c35-2036-4972-be7a-ddceeafb2a31	4fe02094-9504-430b-ae3c-cf28260a3bb4	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
77df793e-39c1-47d4-b12a-b575bef3cfef	4fe02094-9504-430b-ae3c-cf28260a3bb4	606b7604-e542-4d7e-bba8-81de709f2b71	{}
f46d1fba-03ef-4c9c-895d-72edbd72c910	4fe02094-9504-430b-ae3c-cf28260a3bb4	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
f68d813c-9684-4cb4-9567-b99f5c97a0b3	4fe02094-9504-430b-ae3c-cf28260a3bb4	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
a47d219b-7bfd-4c4d-a903-7c2ebf1c3522	d51883b9-2184-4390-8cf7-26e4dfd4acde	c565f657-72c6-4f14-9350-079a1b72b65a	{}
d4349b0b-1338-47eb-913d-fabdfc009c66	d51883b9-2184-4390-8cf7-26e4dfd4acde	71558b37-b72f-4b6f-84f5-22518e8f3566	{}
d9acf29a-102f-48b0-bc96-727029153394	d51883b9-2184-4390-8cf7-26e4dfd4acde	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
bba14936-1be9-4b9a-a461-6b071ed5673a	d51883b9-2184-4390-8cf7-26e4dfd4acde	e243100d-df88-4b91-ae70-717175d3d6aa	{}
0b36e9e7-19de-4c2a-b83e-40956698b493	d51883b9-2184-4390-8cf7-26e4dfd4acde	087ce167-b658-43de-bac7-155c71d30815	{}
115f3c25-3514-4cc1-aeb6-44082bcca281	d51883b9-2184-4390-8cf7-26e4dfd4acde	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
2482b3d1-a5f0-4da2-a80a-6d4382024a1b	d51883b9-2184-4390-8cf7-26e4dfd4acde	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
faeca93e-4b8e-426a-99a4-9d3fd8f1b7ac	d51883b9-2184-4390-8cf7-26e4dfd4acde	54dd4393-88fc-4827-9705-438e6628987a	{}
cccb18a4-8b21-48a5-a032-54ef49fa90ca	d51883b9-2184-4390-8cf7-26e4dfd4acde	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
97139b62-2b3f-482c-9dd2-774c52163dcc	d51883b9-2184-4390-8cf7-26e4dfd4acde	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
dc9eb997-70ef-4b43-9e0e-376b6faacb6e	d51883b9-2184-4390-8cf7-26e4dfd4acde	606b7604-e542-4d7e-bba8-81de709f2b71	{}
d50b863a-4a3a-414a-bf67-517121d04b41	d51883b9-2184-4390-8cf7-26e4dfd4acde	887e0fdb-494a-46aa-869f-b99740705da1	{}
e9edccd7-d9a8-4b5d-aa2c-2e14c6696647	d51883b9-2184-4390-8cf7-26e4dfd4acde	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
30485094-12b9-4031-8582-c8ad7b0cb249	d51883b9-2184-4390-8cf7-26e4dfd4acde	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
f4791fc3-17b6-4544-86d4-99efdeeb25ea	d51883b9-2184-4390-8cf7-26e4dfd4acde	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
00f8c126-edbd-44a1-8535-fd3f4a796050	d51883b9-2184-4390-8cf7-26e4dfd4acde	00739872-28e8-4c95-a25b-40d579702ae8	{}
71e5234e-507f-471b-a081-383b065c3ff8	d51883b9-2184-4390-8cf7-26e4dfd4acde	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
096e3c20-5885-4b2e-9a08-3b30355663ec	d51883b9-2184-4390-8cf7-26e4dfd4acde	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
8b394c54-bd9a-4a37-86f9-6288385cd607	d51883b9-2184-4390-8cf7-26e4dfd4acde	727d5903-9e43-4047-9274-b9722261f397	{}
f9620cf4-8a18-4012-8816-7c472fcd602b	d51883b9-2184-4390-8cf7-26e4dfd4acde	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
9718aac8-8c42-4258-b1c3-4a02472f2a9c	d51883b9-2184-4390-8cf7-26e4dfd4acde	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
3d0f2b78-62c9-4816-ace5-4260aa0c353e	d51883b9-2184-4390-8cf7-26e4dfd4acde	bb561768-51b2-4cab-8079-b113796e5268	{}
810d04d5-da7e-4573-892b-4824a5d12adf	d51883b9-2184-4390-8cf7-26e4dfd4acde	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
8344c376-4890-4b9f-9d0a-b591a6713c40	ebde1aad-a955-4c5c-bde3-3c04f59a8207	c565f657-72c6-4f14-9350-079a1b72b65a	{}
d3f968b8-988e-47fc-a3f5-32fa1872734d	ebde1aad-a955-4c5c-bde3-3c04f59a8207	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
ff86e200-9d5a-457a-9aab-fb7dedd591d2	ebde1aad-a955-4c5c-bde3-3c04f59a8207	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
c2b2dc27-263e-4453-a532-5295c161fe7d	ebde1aad-a955-4c5c-bde3-3c04f59a8207	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
c83763a8-e232-4697-9e16-d5ac966667cf	ebde1aad-a955-4c5c-bde3-3c04f59a8207	54dd4393-88fc-4827-9705-438e6628987a	{}
8982af8c-702f-44cb-938c-4fca41b4a7cb	ebde1aad-a955-4c5c-bde3-3c04f59a8207	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
ec4af65c-daff-4dee-b914-d3b4467f75fe	ebde1aad-a955-4c5c-bde3-3c04f59a8207	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
c4793a7f-e8a5-426b-ae61-6b272b04fa83	ebde1aad-a955-4c5c-bde3-3c04f59a8207	606b7604-e542-4d7e-bba8-81de709f2b71	{}
c6fc3fca-d60c-4c10-a099-8938a92f8273	ebde1aad-a955-4c5c-bde3-3c04f59a8207	887e0fdb-494a-46aa-869f-b99740705da1	{}
49147389-296f-4b84-9252-71cf277d99ef	ebde1aad-a955-4c5c-bde3-3c04f59a8207	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
2ea5567e-ea4b-49e4-9cb4-b4f95a28b087	ebde1aad-a955-4c5c-bde3-3c04f59a8207	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
26947f7d-305d-4e3b-8c2d-6ad57e732307	ebde1aad-a955-4c5c-bde3-3c04f59a8207	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
dc57a80f-8627-4a6c-8586-f14afdedc91c	ebde1aad-a955-4c5c-bde3-3c04f59a8207	00739872-28e8-4c95-a25b-40d579702ae8	{}
01c9b76a-282a-4ba9-8241-08064b326a4e	ebde1aad-a955-4c5c-bde3-3c04f59a8207	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
a0ee87b3-9903-4f17-acb1-34df5d4b5003	ebde1aad-a955-4c5c-bde3-3c04f59a8207	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
d6b40a84-07e8-440b-817a-79c6b0fa5fbf	ebde1aad-a955-4c5c-bde3-3c04f59a8207	727d5903-9e43-4047-9274-b9722261f397	{}
71edfd40-d4f8-4b46-a4bd-13063dceaf99	ebde1aad-a955-4c5c-bde3-3c04f59a8207	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
7600da59-d76d-4c78-a937-1372ae32253e	ebde1aad-a955-4c5c-bde3-3c04f59a8207	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
57242f82-bf6f-4578-9aba-30f5d09a26ba	ebde1aad-a955-4c5c-bde3-3c04f59a8207	bb561768-51b2-4cab-8079-b113796e5268	{}
b139b061-eeaa-49c2-a1e8-51100042e445	ebde1aad-a955-4c5c-bde3-3c04f59a8207	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
5bfdc8f3-78e3-45a4-9ac5-e5a67bf9d639	a322003d-70cd-42d3-aaab-e4b8b97f2702	c565f657-72c6-4f14-9350-079a1b72b65a	{}
08de6fe1-01aa-4069-8483-5170846b996b	a322003d-70cd-42d3-aaab-e4b8b97f2702	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
8f021171-43d2-4cea-a074-33793343e339	a322003d-70cd-42d3-aaab-e4b8b97f2702	54dd4393-88fc-4827-9705-438e6628987a	{}
a4645c92-868f-40d0-a4b1-665371f5336b	a322003d-70cd-42d3-aaab-e4b8b97f2702	00739872-28e8-4c95-a25b-40d579702ae8	{}
9dfc0612-3a30-425f-b02a-34b6a0626403	a322003d-70cd-42d3-aaab-e4b8b97f2702	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
1e1834e3-dde2-4fd2-a7ff-2e13410e54e6	a322003d-70cd-42d3-aaab-e4b8b97f2702	bb561768-51b2-4cab-8079-b113796e5268	{}
718df7bb-d2d1-408d-8530-a71f506219bc	a322003d-70cd-42d3-aaab-e4b8b97f2702	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
fe6bf619-b35f-44f9-ad5a-c7e89569ccbe	4b428d72-d75e-4345-baa8-8cbe39bff9f5	606b7604-e542-4d7e-bba8-81de709f2b71	{}
15da5410-7e22-497c-ab83-18ff1b825662	4b428d72-d75e-4345-baa8-8cbe39bff9f5	887e0fdb-494a-46aa-869f-b99740705da1	{}
33ec5120-8bbf-410f-904c-90083d1e02a5	4b428d72-d75e-4345-baa8-8cbe39bff9f5	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
e53ec6a8-2cfd-465f-8385-e956c0c747f1	4b428d72-d75e-4345-baa8-8cbe39bff9f5	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
a79cf87d-4cd6-413f-9ed0-a036dff39b1e	4b428d72-d75e-4345-baa8-8cbe39bff9f5	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
90636e39-12ff-4565-bcb7-9034bdb39a52	4b428d72-d75e-4345-baa8-8cbe39bff9f5	c565f657-72c6-4f14-9350-079a1b72b65a	{}
25669cc4-7027-415d-acbe-bb264e544af0	4b428d72-d75e-4345-baa8-8cbe39bff9f5	00739872-28e8-4c95-a25b-40d579702ae8	{}
442cdf91-c16d-4ca4-b9da-190b928a52d4	4b428d72-d75e-4345-baa8-8cbe39bff9f5	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
66e5cc83-f7ba-4282-a14b-935eaefa371c	4b428d72-d75e-4345-baa8-8cbe39bff9f5	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
82004186-9a5a-4fc8-973c-76209aad346b	17e4507a-a4ea-4145-ad53-53b9fcb70dc7	be4c8197-9291-4b55-8214-d33662ddc7ea	{}
a8f9bcd9-465f-4c80-a34c-c1133a5fef2f	c5c5e398-54e3-4502-96aa-b47bee2e67b1	be4c8197-9291-4b55-8214-d33662ddc7ea	{}
e4191320-8ca0-41df-a4a4-cb8f40defb16	6b6e658f-af1b-4609-8b82-487c8d753ff5	f65f79ec-3ce4-4e98-9b08-76b3901ecb2b	{}
036358aa-59f8-4fc7-9236-970f959726bd	6b6e658f-af1b-4609-8b82-487c8d753ff5	b9c7ac87-1fd5-464d-b457-7b2c3fc2493d	{}
3a424a7d-25e3-4314-b664-2f8ea7f97232	6b6e658f-af1b-4609-8b82-487c8d753ff5	744b0977-bb86-4ce8-845f-32212f4bfacb	{}
61d12b5a-149b-4edf-a794-f99f7f6cb482	6b6e658f-af1b-4609-8b82-487c8d753ff5	d29b40a0-d248-472b-ab21-fadd82fbbf31	{}
5c492aa6-c008-48ce-86c7-df61be25ccb5	6b6e658f-af1b-4609-8b82-487c8d753ff5	7084e5f7-575d-43fc-ae8e-b819cc2267ad	{}
3e89d391-13e8-476e-ad56-aba87170b158	6b6e658f-af1b-4609-8b82-487c8d753ff5	046f23e3-dc38-4c84-9036-1f0192d29f90	{}
86e10156-86e0-48b0-98b5-16b97a2a14ae	6b6e658f-af1b-4609-8b82-487c8d753ff5	f49e1f8e-7594-41a7-9299-41ca9e1c98be	{}
cfd4290c-3bf8-4512-a6fc-8b6c030caa7a	6b6e658f-af1b-4609-8b82-487c8d753ff5	6b4ecdcc-5500-4091-8f3e-ecb94f0b7d55	{}
269c6c7a-e420-4137-a398-fb6596059a7e	6b6e658f-af1b-4609-8b82-487c8d753ff5	2da18650-9590-40a2-9ec3-e4973a33e3ee	{}
b5341c6f-2aad-4fbc-93f3-1a49f4ff8fd6	6b6e658f-af1b-4609-8b82-487c8d753ff5	784007a6-c81d-4234-a8bb-8a035f89c06e	{}
85630946-7116-4e89-866f-1fd20ef3cb0f	6b6e658f-af1b-4609-8b82-487c8d753ff5	95d9f110-e9ba-4f81-b855-882e735b2e2b	{}
82792e17-7520-4ff1-af27-fd8e9191c96e	6b6e658f-af1b-4609-8b82-487c8d753ff5	7208ac08-6e96-4965-a5ac-80c0505039af	{}
42d6ed77-0915-4bae-9ed9-e28f66b08e3a	6b6e658f-af1b-4609-8b82-487c8d753ff5	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
93bb4572-777d-468b-b6e2-b565cf0742f9	6b6e658f-af1b-4609-8b82-487c8d753ff5	b8992460-4387-43f1-add3-54294859d7f7	{}
ce6044c0-dcee-4665-9c83-1185bde5e746	6b6e658f-af1b-4609-8b82-487c8d753ff5	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
cfeb2af1-ceb3-4670-a2ef-28209485e867	6b6e658f-af1b-4609-8b82-487c8d753ff5	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
e92ae698-4145-43bf-b527-b9f6ddb9e06f	6b6e658f-af1b-4609-8b82-487c8d753ff5	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
219b1449-4b4f-46bd-ac6e-9d4d42714b6c	6b6e658f-af1b-4609-8b82-487c8d753ff5	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
5060073a-cb8a-4f30-8f37-ff4c817268da	6b6e658f-af1b-4609-8b82-487c8d753ff5	c565f657-72c6-4f14-9350-079a1b72b65a	{}
5fc190b9-2670-4e25-a935-1afb06c10305	6b6e658f-af1b-4609-8b82-487c8d753ff5	00739872-28e8-4c95-a25b-40d579702ae8	{}
2b57e46f-e6c1-4358-88af-1e35bc1bf641	6b6e658f-af1b-4609-8b82-487c8d753ff5	bb561768-51b2-4cab-8079-b113796e5268	{}
45afe302-5fc3-4c0b-aa38-a3462d258933	6b6e658f-af1b-4609-8b82-487c8d753ff5	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
59aedb55-d26d-45fb-ad79-8869cc16df6b	6b6e658f-af1b-4609-8b82-487c8d753ff5	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
52cbafb0-6311-4486-acfb-676f2422ef09	6b6e658f-af1b-4609-8b82-487c8d753ff5	606b7604-e542-4d7e-bba8-81de709f2b71	{}
370d9e48-b078-4140-b5ed-84dcfa7193ac	6b6e658f-af1b-4609-8b82-487c8d753ff5	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
12d17380-28d8-4f65-ad42-9072f8762da8	6b6e658f-af1b-4609-8b82-487c8d753ff5	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
756174f2-d4c9-46b4-b5b2-9664b11b7bdf	9cd6512c-98a7-43bb-bf08-9544b667fb4c	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
e6323edb-ee80-42b5-8759-517d96fc5c91	9cd6512c-98a7-43bb-bf08-9544b667fb4c	d2694465-7e98-426e-a6f5-c63ab69594dc	{}
d403d280-f36c-4727-9d83-caadc4c09b57	9cd6512c-98a7-43bb-bf08-9544b667fb4c	1c49abd7-4666-4d3e-9e16-6451d5ee2da9	{}
e200148b-c40e-4764-8571-549c86f800e5	9cd6512c-98a7-43bb-bf08-9544b667fb4c	e822e1fe-c906-4792-bcbe-bd68eef67b24	{}
ba2d9f7b-61d4-49bd-8d0f-5269ff3fd81e	9cd6512c-98a7-43bb-bf08-9544b667fb4c	b8992460-4387-43f1-add3-54294859d7f7	{}
3c73da6c-3b9e-4919-b0b5-aefbffafa0cd	9cd6512c-98a7-43bb-bf08-9544b667fb4c	71898b8a-cf52-4422-bfe0-cdbf9c8b49eb	{}
ef985659-ae47-4024-95a5-f68e74d9ad8c	9cd6512c-98a7-43bb-bf08-9544b667fb4c	93891906-2a3e-4f7b-98ff-d2af686a2134	{}
927b53ba-11a3-4d51-91e1-ee444a8d3559	9cd6512c-98a7-43bb-bf08-9544b667fb4c	2e09c9ee-b539-4915-bc92-cc29dd4858e3	{}
9d747f68-4755-4b96-86fc-061901d829e1	9cd6512c-98a7-43bb-bf08-9544b667fb4c	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
8c755638-82f4-47cb-a6d4-d658be79efa1	9cd6512c-98a7-43bb-bf08-9544b667fb4c	ec4c02c9-7f8e-413c-9cfe-e812755dbf3b	{}
cc176a75-929b-42f4-acb2-95ad92ba8221	9cd6512c-98a7-43bb-bf08-9544b667fb4c	8c4b39cb-75d7-4a02-8bb4-e05320ef870e	{}
c141fe1b-b10b-4902-86d5-b34ad79a3609	9cd6512c-98a7-43bb-bf08-9544b667fb4c	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
be90d8bf-4aba-4a9d-be0e-c744cc7c1525	9cd6512c-98a7-43bb-bf08-9544b667fb4c	c565f657-72c6-4f14-9350-079a1b72b65a	{}
be7a9440-d033-4c73-ba4a-33b548cc31d5	9cd6512c-98a7-43bb-bf08-9544b667fb4c	00739872-28e8-4c95-a25b-40d579702ae8	{}
e0d7686b-a604-4208-989e-3eef180c0b82	9cd6512c-98a7-43bb-bf08-9544b667fb4c	bb561768-51b2-4cab-8079-b113796e5268	{}
46dd12dc-fcc8-478b-ae54-c70dad9f556b	9cd6512c-98a7-43bb-bf08-9544b667fb4c	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
a9197b6e-3cea-4358-9eb9-bcf381f13b08	9cd6512c-98a7-43bb-bf08-9544b667fb4c	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
57e6cc33-ec02-4a1b-a213-d4dec0601142	9cd6512c-98a7-43bb-bf08-9544b667fb4c	606b7604-e542-4d7e-bba8-81de709f2b71	{}
03667ebb-68d0-4aed-91ba-4644a51bb231	03e2183c-99ab-40e4-86e2-ec6da611c36e	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
7e12a7f7-5336-4984-b950-e0c6a83dcc40	03e2183c-99ab-40e4-86e2-ec6da611c36e	bd4e5b2c-5d39-4d68-bbe9-94d9096d59f8	{}
e2b6bcf5-96f6-4c19-a5ab-4601596bc51e	03e2183c-99ab-40e4-86e2-ec6da611c36e	d1913f08-d669-4f93-ae93-739e9a1dabe6	{}
e5055188-50c1-4b87-8d18-da69ac5e37de	03e2183c-99ab-40e4-86e2-ec6da611c36e	a754f927-efa8-4a93-8eb9-604606f30a53	{}
f234004a-97c9-44ab-84b4-eb73348386cd	03e2183c-99ab-40e4-86e2-ec6da611c36e	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
4713a739-a913-435e-8dbe-1f1446372f82	03e2183c-99ab-40e4-86e2-ec6da611c36e	d715a20c-1044-4579-81c1-2689cdd39847	{}
6144a2a6-8e9d-4f9a-a4f5-5fc898deb060	03e2183c-99ab-40e4-86e2-ec6da611c36e	e1d2717e-7f56-4800-bdaa-3e3e4e30746a	{}
eabfe253-2103-48b9-a21b-f1ca27d08364	03e2183c-99ab-40e4-86e2-ec6da611c36e	71c5940e-22f4-4ad9-b850-f850688069c1	{}
e1c3b35a-7dec-47f5-ade1-034bb3671aa5	03e2183c-99ab-40e4-86e2-ec6da611c36e	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
0eeacffc-37b6-4ca2-a199-8499d6a39777	03e2183c-99ab-40e4-86e2-ec6da611c36e	c565f657-72c6-4f14-9350-079a1b72b65a	{}
1133c265-c4b5-4c62-95ed-17e057a4e1ef	03e2183c-99ab-40e4-86e2-ec6da611c36e	00739872-28e8-4c95-a25b-40d579702ae8	{}
f9c5d138-4481-47ef-a699-0a47d431c6d9	03e2183c-99ab-40e4-86e2-ec6da611c36e	bb561768-51b2-4cab-8079-b113796e5268	{}
b274decb-28e3-44a5-bf71-99f36a4f0ac1	03e2183c-99ab-40e4-86e2-ec6da611c36e	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
1380ea66-9d2e-4b10-8b74-f6fdb0024f2e	03e2183c-99ab-40e4-86e2-ec6da611c36e	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
f22db1b4-d03d-4299-930d-1c41c5459410	03e2183c-99ab-40e4-86e2-ec6da611c36e	606b7604-e542-4d7e-bba8-81de709f2b71	{}
b2b75a5d-66a9-4b6f-962c-0d6622914024	0133bf63-480c-47b4-b129-9bc4f84e60e2	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
40dff427-366a-4778-9a02-21176ef82140	0133bf63-480c-47b4-b129-9bc4f84e60e2	70342008-ce16-4d30-b45d-d202a6b07820	{}
544cdff6-cf6b-49d4-bdc4-75752db1c28f	0133bf63-480c-47b4-b129-9bc4f84e60e2	4621c394-fc16-4333-baf5-c50a2368948b	{}
19a95cb7-ca02-4d8e-83c7-4d68117a928f	0133bf63-480c-47b4-b129-9bc4f84e60e2	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
67dff53b-463f-4137-8f5c-706af82b3c18	0133bf63-480c-47b4-b129-9bc4f84e60e2	a5bd460e-2bb5-4a7f-80ea-1c0770b4d583	{}
6b782048-5822-4cec-860b-26f5ef6fe7d8	0133bf63-480c-47b4-b129-9bc4f84e60e2	64d09c38-f333-426e-8635-7c9eb27ceed0	{}
d5c94d60-4271-4d51-88d9-d5dc8b40e9c4	0133bf63-480c-47b4-b129-9bc4f84e60e2	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
b4a8669d-51f0-472c-a0a5-7fbb6e65c34d	3855fcb2-225e-44d9-aa30-30e69f10ff36	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
87e3551e-9359-4ca1-a4b8-1ccb298a675f	3855fcb2-225e-44d9-aa30-30e69f10ff36	0290c46c-96ae-493a-873a-8c9acc403ec5	{}
7fd2a75a-fe57-4f79-96b4-83abf48eaac0	3855fcb2-225e-44d9-aa30-30e69f10ff36	24104566-dc21-4fd0-b59a-9d1aa8d94ca2	{}
478c60e3-5431-4cd8-ba34-66785a33071d	3855fcb2-225e-44d9-aa30-30e69f10ff36	b73c729e-93f7-43ba-b541-3893ea43b341	{}
60deef8f-2a3e-411c-b0f9-3a75c972ddff	3855fcb2-225e-44d9-aa30-30e69f10ff36	c565f657-72c6-4f14-9350-079a1b72b65a	{}
aaf712f3-c6be-44c5-bba7-6dc05a6b0755	3855fcb2-225e-44d9-aa30-30e69f10ff36	71558b37-b72f-4b6f-84f5-22518e8f3566	{}
c1e9c856-c78a-4ebd-96a4-b19b16ca08ee	3855fcb2-225e-44d9-aa30-30e69f10ff36	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
6e19f84e-9698-44d4-9cbf-86212da7fbf1	3855fcb2-225e-44d9-aa30-30e69f10ff36	e243100d-df88-4b91-ae70-717175d3d6aa	{}
e6e4512c-5fa0-4b54-8fe3-5359fa741d94	3855fcb2-225e-44d9-aa30-30e69f10ff36	087ce167-b658-43de-bac7-155c71d30815	{}
e77a6bae-7933-430e-9154-84a7fdce397e	3855fcb2-225e-44d9-aa30-30e69f10ff36	00739872-28e8-4c95-a25b-40d579702ae8	{}
352cc0eb-d0c2-467a-ac5f-43471b95fa95	3855fcb2-225e-44d9-aa30-30e69f10ff36	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
3580ef71-1f48-4ff6-ae43-1fbd5c8fe509	3855fcb2-225e-44d9-aa30-30e69f10ff36	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
71884b6f-900e-4036-a87d-7ae3fc56eb8b	3855fcb2-225e-44d9-aa30-30e69f10ff36	727d5903-9e43-4047-9274-b9722261f397	{}
a6d7f176-2d5a-492a-9555-c7623d7219ed	3855fcb2-225e-44d9-aa30-30e69f10ff36	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
f58e0985-8f0b-49c0-ab74-ceab8a7a30f3	3855fcb2-225e-44d9-aa30-30e69f10ff36	bb561768-51b2-4cab-8079-b113796e5268	{}
b75cc6e0-e97f-45ad-9da1-132c6047bbca	3855fcb2-225e-44d9-aa30-30e69f10ff36	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
6b5b14ef-1ed5-472d-852a-7c5011ff8e14	3855fcb2-225e-44d9-aa30-30e69f10ff36	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
c6836799-35a1-4801-bc30-0ca14e1aed08	3855fcb2-225e-44d9-aa30-30e69f10ff36	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
3748234c-e6c6-4c34-a574-4767454f494f	3855fcb2-225e-44d9-aa30-30e69f10ff36	54dd4393-88fc-4827-9705-438e6628987a	{}
c7436077-a385-4041-a0f5-b4a4b3105b6a	3855fcb2-225e-44d9-aa30-30e69f10ff36	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
7395a4a3-22e0-4695-8eb9-41abc22e19c4	3855fcb2-225e-44d9-aa30-30e69f10ff36	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
607c353e-1a7b-4724-8f04-ef987af75778	3855fcb2-225e-44d9-aa30-30e69f10ff36	606b7604-e542-4d7e-bba8-81de709f2b71	{}
93aafad1-4994-48a9-8f50-1383c8e8b9bb	3855fcb2-225e-44d9-aa30-30e69f10ff36	887e0fdb-494a-46aa-869f-b99740705da1	{}
3ec37d94-2cd9-4396-b465-fe1a0fd59298	3855fcb2-225e-44d9-aa30-30e69f10ff36	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
5bc3b804-3549-4cf1-b448-dc3c0cbd232b	3855fcb2-225e-44d9-aa30-30e69f10ff36	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
6596e222-e614-46a2-ae67-7929ab340940	3855fcb2-225e-44d9-aa30-30e69f10ff36	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
261dddc3-4997-41ed-a53d-81ae8c6ac289	57cedf7f-13e5-47a7-8729-2df0d2fde336	963d9e80-f524-49f6-94a6-1f910578f1ce	{}
af8e5559-10de-4d7e-abe4-d38f365b587f	57cedf7f-13e5-47a7-8729-2df0d2fde336	b8992460-4387-43f1-add3-54294859d7f7	{}
b925ea66-f464-4910-8ed2-44e14518cdc9	57cedf7f-13e5-47a7-8729-2df0d2fde336	d0c33de9-098f-4cdd-8129-c9d1b228e01f	{}
2db5b796-454e-47e8-bc35-2e1e032f2484	57cedf7f-13e5-47a7-8729-2df0d2fde336	5a61f6d0-2a2d-43c2-83be-74bba488860d	{}
d0233696-a5fd-4d23-89fe-6cf99aa1046a	57cedf7f-13e5-47a7-8729-2df0d2fde336	0a966bfa-b9cf-4bbd-9f1a-e79551b328c2	{}
d7571a10-eab8-4b91-a9c0-28d178229d23	57cedf7f-13e5-47a7-8729-2df0d2fde336	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
4533e2d9-81c9-4738-86d1-9fe137dbeaac	57cedf7f-13e5-47a7-8729-2df0d2fde336	c565f657-72c6-4f14-9350-079a1b72b65a	{}
c1be29ba-1f40-48bd-926a-5cf776799c16	57cedf7f-13e5-47a7-8729-2df0d2fde336	00739872-28e8-4c95-a25b-40d579702ae8	{}
7a01097f-5fe3-4fa4-b6e7-2f99127e70ba	57cedf7f-13e5-47a7-8729-2df0d2fde336	bb561768-51b2-4cab-8079-b113796e5268	{}
99f3b6c6-9b80-4294-86f7-64846ea06b97	57cedf7f-13e5-47a7-8729-2df0d2fde336	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
4b7ff828-a0dc-4c2b-86c5-065bdf0b578f	57cedf7f-13e5-47a7-8729-2df0d2fde336	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
45ecdf1a-b970-4996-8c6f-d0e6bc5cc2d3	57cedf7f-13e5-47a7-8729-2df0d2fde336	606b7604-e542-4d7e-bba8-81de709f2b71	{}
9e84760d-be9a-40d2-8339-a9c4d11357c4	57cedf7f-13e5-47a7-8729-2df0d2fde336	8f455ac4-d980-45f1-bc71-9630c031c90d	{}
30436427-7f44-455b-ada0-a03fa05b367f	57cedf7f-13e5-47a7-8729-2df0d2fde336	3a9291d5-3def-4546-8b9f-a2dcd22933f8	{}
c5d7d2d1-8211-4b10-ab13-5f5e4196c748	604cb142-29d2-4c18-b45c-4588e74d16c9	c565f657-72c6-4f14-9350-079a1b72b65a	{}
5acb596e-27dd-40b6-8726-66666dcbf584	604cb142-29d2-4c18-b45c-4588e74d16c9	71558b37-b72f-4b6f-84f5-22518e8f3566	{}
764f6013-89e9-4c77-b6c8-e3ce221833f0	604cb142-29d2-4c18-b45c-4588e74d16c9	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
97736c17-5779-4dd9-afc7-093ac61cbf65	604cb142-29d2-4c18-b45c-4588e74d16c9	e243100d-df88-4b91-ae70-717175d3d6aa	{}
9a8d9a00-6a99-47ba-bec7-4c7de04b75fa	604cb142-29d2-4c18-b45c-4588e74d16c9	087ce167-b658-43de-bac7-155c71d30815	{}
ece48b56-0c62-402c-ab75-081f30efa286	604cb142-29d2-4c18-b45c-4588e74d16c9	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
70a2a96b-eb70-448b-87f9-ffaa4365309d	604cb142-29d2-4c18-b45c-4588e74d16c9	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
1e9e1022-3272-4a79-82d9-7e17bac5ae11	604cb142-29d2-4c18-b45c-4588e74d16c9	54dd4393-88fc-4827-9705-438e6628987a	{}
41f9018c-e6a5-49df-95a6-31d53210765a	604cb142-29d2-4c18-b45c-4588e74d16c9	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
0f09f49d-41dc-445f-b2ab-b8bb87c7923a	604cb142-29d2-4c18-b45c-4588e74d16c9	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
4f263b54-5911-44b2-82f8-f7da2f6baf18	604cb142-29d2-4c18-b45c-4588e74d16c9	606b7604-e542-4d7e-bba8-81de709f2b71	{}
b1a804b5-afbe-4681-873b-d4862820c436	604cb142-29d2-4c18-b45c-4588e74d16c9	887e0fdb-494a-46aa-869f-b99740705da1	{}
b62fd762-073a-4a45-942d-54841d416718	604cb142-29d2-4c18-b45c-4588e74d16c9	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
854c404f-6411-4a15-a7d7-c3b69559ac4c	604cb142-29d2-4c18-b45c-4588e74d16c9	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
e27c1e33-371b-47d7-a2d2-d7eec0c06db4	604cb142-29d2-4c18-b45c-4588e74d16c9	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
ad94da51-8a88-4b66-b6e4-73ed16345b44	604cb142-29d2-4c18-b45c-4588e74d16c9	00739872-28e8-4c95-a25b-40d579702ae8	{}
2e84e44d-71b8-4619-9bf3-028f32845504	604cb142-29d2-4c18-b45c-4588e74d16c9	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
7bb511a7-e0cc-4d10-a988-722bde428b68	604cb142-29d2-4c18-b45c-4588e74d16c9	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
43dcbf6d-99fe-4de5-a329-dea0b4650ef6	604cb142-29d2-4c18-b45c-4588e74d16c9	727d5903-9e43-4047-9274-b9722261f397	{}
38844664-1c6a-4521-8f23-2b6322481970	604cb142-29d2-4c18-b45c-4588e74d16c9	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
d11dbe37-eb44-4ddb-9625-8a1a6e7eb2d2	604cb142-29d2-4c18-b45c-4588e74d16c9	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
86937c70-c416-456a-95a8-73a2f6a8bc6e	604cb142-29d2-4c18-b45c-4588e74d16c9	bb561768-51b2-4cab-8079-b113796e5268	{}
cc813d00-24d7-4859-92ad-3001ec3be4cf	604cb142-29d2-4c18-b45c-4588e74d16c9	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
143ffb82-2546-4381-a367-c7ee76f45ac8	22817e25-becd-4837-90cf-7e0802b5446c	c565f657-72c6-4f14-9350-079a1b72b65a	{}
7e756981-aa10-4294-86c5-866c0c290d64	22817e25-becd-4837-90cf-7e0802b5446c	9bbd78de-3cfe-4bf1-afc9-8c860349bdb4	{}
f42c385a-9823-4d0a-825f-2cf476e2379d	22817e25-becd-4837-90cf-7e0802b5446c	087ce167-b658-43de-bac7-155c71d30815	{}
3abcff4e-2912-4159-83a4-52ca71ee97df	22817e25-becd-4837-90cf-7e0802b5446c	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
e882aedb-5668-4891-850d-5ee963849281	22817e25-becd-4837-90cf-7e0802b5446c	a0e56f2b-8783-42b9-ade3-972a17063f6f	{}
df46daad-f45a-4042-a4c5-60bc916c98f4	22817e25-becd-4837-90cf-7e0802b5446c	54dd4393-88fc-4827-9705-438e6628987a	{}
633f5a42-7652-429a-8962-9aec7fb78e81	22817e25-becd-4837-90cf-7e0802b5446c	62e773ef-cf48-4ef9-a8a2-6cd4f0eac5e4	{}
752fa6ad-b01e-438a-b79a-d49a25e2c178	22817e25-becd-4837-90cf-7e0802b5446c	9e243797-9f2a-44ed-b748-c41cd77e4d2d	{}
32721c47-c566-4e07-bc16-20dd070050f7	22817e25-becd-4837-90cf-7e0802b5446c	606b7604-e542-4d7e-bba8-81de709f2b71	{}
634c033b-1bcd-4026-ac62-72e2b158ccf9	22817e25-becd-4837-90cf-7e0802b5446c	887e0fdb-494a-46aa-869f-b99740705da1	{}
503231de-bd3c-4882-bc27-7bbac97266d9	22817e25-becd-4837-90cf-7e0802b5446c	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
77991b57-aa99-4a8e-9712-a9147de3910b	22817e25-becd-4837-90cf-7e0802b5446c	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
703db892-f7b1-45fe-abe3-b5ae33855da0	22817e25-becd-4837-90cf-7e0802b5446c	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
50b9b8f0-7c0b-4bf3-a16f-1c060aee9c65	22817e25-becd-4837-90cf-7e0802b5446c	00739872-28e8-4c95-a25b-40d579702ae8	{}
d8e0c57e-cba5-4fc8-b1fc-dd700dfb2510	22817e25-becd-4837-90cf-7e0802b5446c	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
f8c6b414-6fb4-4d04-8474-1126fe6b4258	22817e25-becd-4837-90cf-7e0802b5446c	9e5e8650-8af9-4ab1-b04d-049ef9b930ee	{}
c7f5fc44-b3b5-4201-919a-b9831579b6c6	22817e25-becd-4837-90cf-7e0802b5446c	727d5903-9e43-4047-9274-b9722261f397	{}
9cd7ca28-f71d-4940-a729-336e8856db19	22817e25-becd-4837-90cf-7e0802b5446c	bf07b0c7-ec53-4c98-9bcd-e9f7888e22c0	{}
992f819c-fe0b-495b-b66c-0ec1fcc713fe	22817e25-becd-4837-90cf-7e0802b5446c	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
b29301ac-12f6-413e-9e3f-27b2bad23494	22817e25-becd-4837-90cf-7e0802b5446c	bb561768-51b2-4cab-8079-b113796e5268	{}
e5b11759-9a78-4400-b964-8b657e0a7067	22817e25-becd-4837-90cf-7e0802b5446c	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
87f53285-bb4c-4d8e-9d62-6976f81e5fb2	5e7c9503-385a-46e0-843b-646eb9a35f81	c565f657-72c6-4f14-9350-079a1b72b65a	{}
1caef685-22e2-4f80-af56-9e3848edfc93	5e7c9503-385a-46e0-843b-646eb9a35f81	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
8fa8a5d9-81df-4dfd-902f-4ad953a13e81	5e7c9503-385a-46e0-843b-646eb9a35f81	54dd4393-88fc-4827-9705-438e6628987a	{}
484dd1bc-b1d3-441f-b0e8-9e108d7b96fc	5e7c9503-385a-46e0-843b-646eb9a35f81	00739872-28e8-4c95-a25b-40d579702ae8	{}
48127625-2c13-46bb-8da3-00067c932e02	5e7c9503-385a-46e0-843b-646eb9a35f81	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
041c1b24-d621-4851-8696-0be28f151235	5e7c9503-385a-46e0-843b-646eb9a35f81	bb561768-51b2-4cab-8079-b113796e5268	{}
807a1ab2-d14f-4b34-8525-dbbc2fdbc602	5e7c9503-385a-46e0-843b-646eb9a35f81	738a1b2d-a9c4-4475-a48b-fb702515ccd3	{}
f9b4549d-2814-4565-98f8-f73a1642f325	65b8d6b5-9a80-42ef-abd8-5cff70edea44	606b7604-e542-4d7e-bba8-81de709f2b71	{}
e7a23d07-dd3e-46c8-bc5b-d5e0e8657315	65b8d6b5-9a80-42ef-abd8-5cff70edea44	887e0fdb-494a-46aa-869f-b99740705da1	{}
b6fa1074-436e-44a9-85e6-458fff3f3581	65b8d6b5-9a80-42ef-abd8-5cff70edea44	801c3ff8-cd35-4286-882c-33761f4b5f87	{}
9367a2a2-cd5a-4857-942d-720a544f495c	65b8d6b5-9a80-42ef-abd8-5cff70edea44	97ca21cf-8b7f-4070-a315-92d6a9a9a2a9	{}
6040ad9a-9c9f-4cc7-846b-c60bf467e8e9	65b8d6b5-9a80-42ef-abd8-5cff70edea44	81f2ce5a-b8c3-469f-aa40-39ac8a80d319	{}
18dc3371-a5d2-4e5c-a505-31dbdd7af4b6	65b8d6b5-9a80-42ef-abd8-5cff70edea44	c565f657-72c6-4f14-9350-079a1b72b65a	{}
2364c001-936d-4291-b5b2-14d2bc5cc3de	65b8d6b5-9a80-42ef-abd8-5cff70edea44	00739872-28e8-4c95-a25b-40d579702ae8	{}
7cc459bc-df87-40f0-89e1-0006e96d312d	65b8d6b5-9a80-42ef-abd8-5cff70edea44	c40cfdcd-ef9e-4d9d-9223-2b90778e60fe	{}
9d864e4b-38b4-4ffd-9d0d-2bba50963ef3	65b8d6b5-9a80-42ef-abd8-5cff70edea44	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
22a9db55-cb22-4b1a-a23f-ffc7eea7d7d4	e6fd493a-17f2-4b99-93c0-1dfb2bb41f3e	c565f657-72c6-4f14-9350-079a1b72b65a	{}
6d3c5e2a-87ed-4723-a4ed-5112f5a401da	e6fd493a-17f2-4b99-93c0-1dfb2bb41f3e	a8369c24-84d5-4e3b-a6fa-ae6deb5b6c8a	{}
5d8ab731-53e5-49f0-beab-dbaac7291e52	e6fd493a-17f2-4b99-93c0-1dfb2bb41f3e	54dd4393-88fc-4827-9705-438e6628987a	{}
28bbe649-425e-4b3b-bacd-05ea7b2b83ea	e6fd493a-17f2-4b99-93c0-1dfb2bb41f3e	1ffa0d06-4202-468a-885f-23c3a84dadcf	{}
82650c08-749f-4423-8063-701ae16b3393	e6fd493a-17f2-4b99-93c0-1dfb2bb41f3e	00739872-28e8-4c95-a25b-40d579702ae8	{}
2c891377-ae85-4665-8c07-5c696962685a	07ffcc1b-16d7-464e-b6da-83cb93474d84	be4c8197-9291-4b55-8214-d33662ddc7ea	{}
\.

--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.roles (id, organization_id, name, code, description, is_system, is_default, hierarchy_level, is_active, extra_data, created_at, updated_at) FROM stdin;
b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	00000000-0000-0000-0000-000000000001	Super Admin	super_admin	Full system admin access — grants all system_admin permissions	t	f	100	t	{}	2026-06-07 05:18:24.863495+00	2026-06-07 05:18:24.863499+00
3bf01d48-72fc-43b9-a86d-ca2374ec940e	00000000-0000-0000-0000-000000000001	System User Manager	system_user_manager	Manage system admin users (read, create, update, delete)	t	f	80	t	{}	2026-06-07 05:18:24.874963+00	2026-06-07 05:18:24.874966+00
f74c06eb-6c0c-4144-9836-8edd90ebbd34	00000000-0000-0000-0000-000000000001	System Org Manager	system_org_manager	Manage organizations (read, create, update, delete)	t	f	80	t	{}	2026-06-07 05:18:24.887751+00	2026-06-07 05:18:24.887755+00
6f3d530c-90b0-4788-bd88-47385026463c	00000000-0000-0000-0000-000000000001	System Billing Manager	system_billing_manager	Manage billing (read, create, update, delete)	t	f	80	t	{}	2026-06-07 05:18:24.900907+00	2026-06-07 05:18:24.900911+00
57543360-893d-4bcf-b6ec-ea550ca1d582	00000000-0000-0000-0000-000000000001	System Reports Viewer	system_reports_viewer	View system reports and dashboards	t	f	50	t	{}	2026-06-07 05:18:24.911603+00	2026-06-07 05:18:24.911606+00
8c372bb6-92de-4182-a77f-10604e8ab30b	05397b7b-95bb-4560-b3d0-dff21b3db1ee	Organization Owner	owner	Full access to all features. Automatically assigned to the user who created the organization.	t	f	100	t	{}	2026-06-07 05:20:16.109174+00	2026-06-07 05:20:16.109189+00
8332777d-a6cd-4a8d-90e9-9db022775fbd	05397b7b-95bb-4560-b3d0-dff21b3db1ee	Administrator	org_admin	Full access to identity management plus read-only access to all business modules.	t	f	80	t	{}	2026-06-07 05:20:16.126921+00	2026-06-07 05:20:16.126932+00
412fbd53-2d9a-471d-82e3-8af2a60f452a	05397b7b-95bb-4560-b3d0-dff21b3db1ee	Sales Agent	sales_agent	Full access to Sales & Orders module plus read-only Inventory.	t	f	40	t	{}	2026-06-07 05:20:16.165998+00	2026-06-07 05:20:16.166004+00
ee481431-7fef-4d59-a208-94cccfd7b735	05397b7b-95bb-4560-b3d0-dff21b3db1ee	Procurement Officer	procurement_officer	Full access to Procurement module plus read-only Inventory.	t	f	40	t	{}	2026-06-07 05:20:16.213573+00	2026-06-07 05:20:16.213584+00
b09c25ec-5ddf-4420-b9c9-26ac46ff8095	05397b7b-95bb-4560-b3d0-dff21b3db1ee	Accountant	accountant	Full access to Accounting module plus read-only access to Sales invoices.	t	f	40	t	{}	2026-06-07 05:20:16.274314+00	2026-06-07 05:20:16.274325+00
3f54447f-f2e3-42b9-b82e-3ea81fec9320	05397b7b-95bb-4560-b3d0-dff21b3db1ee	Warehouse Staff	warehouse_staff	Full access to Inventory module only.	t	f	20	t	{}	2026-06-07 05:20:16.348843+00	2026-06-07 05:20:16.348852+00
621a2385-cb10-4f42-a04b-0524992d11f9	05397b7b-95bb-4560-b3d0-dff21b3db1ee	Viewer	viewer	Read-only access across all modules. Cannot create, edit, or delete anything.	t	f	10	t	{}	2026-06-07 05:20:16.369182+00	2026-06-07 05:20:16.369188+00
f7dd3228-bf2b-4859-9b19-3a55b577ae4b	05397b7b-95bb-4560-b3d0-dff21b3db1ee	WMS Manager	wms_manager	Warehouse manager for assigned warehouse(s) — inbound, put-away, outbound, picking, and ASN coordination	f	f	70	t	{}	2026-06-07 05:20:16.409921+00	2026-06-07 05:20:16.409926+00
0d635dab-00fe-4790-9577-5b4c15109439	05397b7b-95bb-4560-b3d0-dff21b3db1ee	WMS Operator	wms_operator	Floor worker — dock scanning, put-away execution, picking, and gate verification	f	f	50	t	{}	2026-06-07 05:20:16.430426+00	2026-06-07 05:20:16.430431+00
7355c4b4-4871-4836-95a6-5d3c64c1c1c7	05397b7b-95bb-4560-b3d0-dff21b3db1ee	ASN Coordinator	asn_coordinator	Manages advance stock notices (ASN) and inter-warehouse transfers — create, confirm, and track fulfillment	f	f	65	t	{}	2026-06-07 05:20:16.447458+00	2026-06-07 05:20:16.447468+00
9ca9ca74-227f-4827-b087-de80bbb4e24d	05397b7b-95bb-4560-b3d0-dff21b3db1ee	Organization Admin	organization_admin	Full access to all resources within this organization	t	f	90	t	{}	2026-06-07 05:38:15.292974+00	2026-06-07 05:38:15.292979+00
b85d7824-a86f-4022-a5f7-cbcde4513708	ddfad734-9afb-497b-81a3-ffc85caec590	Organization Owner	owner	Full access to all features. Automatically assigned to the user who created the organization.	t	f	100	t	{}	2026-06-11 17:54:14.128668+00	2026-06-11 17:54:14.128671+00
f1e77899-8cbc-4a78-9dfa-32e6254e07b5	ddfad734-9afb-497b-81a3-ffc85caec590	Administrator	org_admin	Full access to identity management plus read-only access to all business modules.	t	f	80	t	{}	2026-06-11 17:54:14.133391+00	2026-06-11 17:54:14.133394+00
a9e1e94e-4784-4717-814f-e83321c2140f	ddfad734-9afb-497b-81a3-ffc85caec590	Sales Agent	sales_agent	Full access to Sales & Orders module plus read-only Inventory.	t	f	40	t	{}	2026-06-11 17:54:14.143556+00	2026-06-11 17:54:14.143559+00
ab3a1aa6-8848-4552-8b29-21caff47549c	ddfad734-9afb-497b-81a3-ffc85caec590	Procurement Officer	procurement_officer	Full access to Procurement module plus read-only Inventory.	t	f	40	t	{}	2026-06-11 17:54:14.157266+00	2026-06-11 17:54:14.157269+00
351e367e-4947-4fed-abf2-7e4b20d23e79	ddfad734-9afb-497b-81a3-ffc85caec590	Accountant	accountant	Full access to Accounting module plus read-only access to Sales invoices.	t	f	40	t	{}	2026-06-11 17:54:14.166132+00	2026-06-11 17:54:14.166134+00
39c33874-ce0f-46b6-9f61-0a872b6d1d97	ddfad734-9afb-497b-81a3-ffc85caec590	Warehouse Staff	warehouse_staff	Full access to Inventory module only.	t	f	20	t	{}	2026-06-11 17:54:14.173867+00	2026-06-11 17:54:14.173869+00
93f68d93-c156-408c-a5dc-23ba510051f2	ddfad734-9afb-497b-81a3-ffc85caec590	Viewer	viewer	Read-only access across all modules. Cannot create, edit, or delete anything.	t	f	10	t	{}	2026-06-11 17:54:14.181402+00	2026-06-11 17:54:14.181405+00
42146f28-9b13-4af1-acd7-9d3da69b15d0	ddfad734-9afb-497b-81a3-ffc85caec590	WMS Manager	wms_manager	Warehouse manager for assigned warehouse(s) — inbound, put-away, outbound, picking, and ASN coordination	f	f	70	t	{}	2026-06-11 17:54:14.200439+00	2026-06-11 17:54:14.200442+00
e8c6a44d-8395-47f4-bea1-043c379b3560	ddfad734-9afb-497b-81a3-ffc85caec590	WMS Operator	wms_operator	Floor worker — dock scanning, put-away execution, picking, and gate verification	f	f	50	t	{}	2026-06-11 17:54:14.211394+00	2026-06-11 17:54:14.211397+00
4cfde21e-b474-4f74-9933-662c4f34863a	ddfad734-9afb-497b-81a3-ffc85caec590	ASN Coordinator	asn_coordinator	Manages advance stock notices (ASN) and inter-warehouse transfers — create, confirm, and track fulfillment	f	f	65	t	{}	2026-06-11 17:54:14.221005+00	2026-06-11 17:54:14.221008+00
b09987b7-850d-40cb-b545-395cef1a27fe	ddfad734-9afb-497b-81a3-ffc85caec590	Organization Admin	organization_admin	Full access to all resources within this organization	t	f	90	t	{}	2026-06-11 18:25:25.015462+00	2026-06-11 18:25:25.015476+00
59e7ad24-3870-48fd-8e9e-ffb5eb46e444	05397b7b-95bb-4560-b3d0-dff21b3db1ee	WMS Admin	wms_admin	Full warehouse administration — global access to all warehouses, layout, inbound, put-away, outbound, gate, ASN, dispatches, and worker/device management	f	f	75	t	{}	2026-06-07 05:20:16.391375+00	2026-06-07 05:20:16.39138+00
2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	ddfad734-9afb-497b-81a3-ffc85caec590	WMS Admin	wms_admin	Full warehouse administration — global access to all warehouses, layout, inbound, put-away, outbound, gate, ASN, dispatches, and worker/device management	f	f	75	t	{}	2026-06-11 17:54:14.19178+00	2026-06-11 17:54:14.191783+00
26e95172-da8c-42f4-be74-6b2a911dd002	b5863590-fb53-4d22-a956-956aafc1c13e	Organization Owner	owner	Full access to all features. Automatically assigned to the user who created the organization.	t	f	100	t	{}	2026-06-19 04:08:29.807506+00	2026-06-19 04:08:29.807508+00
ab071494-85c9-46de-adca-a092077ffa4d	b5863590-fb53-4d22-a956-956aafc1c13e	Administrator	org_admin	Full access to identity management plus read-only access to all business modules.	t	f	80	t	{}	2026-06-19 04:08:29.811555+00	2026-06-19 04:08:29.811561+00
2c923ed8-faae-498f-b65f-f695cdbd7282	b5863590-fb53-4d22-a956-956aafc1c13e	Sales Agent	sales_agent	Full access to Sales & Orders module plus read-only Inventory.	t	f	40	t	{}	2026-06-19 04:08:29.822866+00	2026-06-19 04:08:29.822869+00
d06ba299-c4cc-4da8-ae83-35153b422082	b5863590-fb53-4d22-a956-956aafc1c13e	Procurement Officer	procurement_officer	Full access to Procurement module plus read-only Inventory.	t	f	40	t	{}	2026-06-19 04:08:29.836615+00	2026-06-19 04:08:29.83662+00
e4192c84-8700-4949-8f9c-3b642954cb21	b5863590-fb53-4d22-a956-956aafc1c13e	Accountant	accountant	Full access to Accounting module plus read-only access to Sales invoices.	t	f	40	t	{}	2026-06-19 04:08:29.846669+00	2026-06-19 04:08:29.846672+00
fdc0aba9-365b-4cf3-bce6-cd9b554579e5	b5863590-fb53-4d22-a956-956aafc1c13e	Warehouse Staff	warehouse_staff	Full access to Inventory module only.	t	f	20	t	{}	2026-06-19 04:08:29.854568+00	2026-06-19 04:08:29.854571+00
4fe02094-9504-430b-ae3c-cf28260a3bb4	b5863590-fb53-4d22-a956-956aafc1c13e	Viewer	viewer	Read-only access across all modules. Cannot create, edit, or delete anything.	t	f	10	t	{}	2026-06-19 04:08:29.863717+00	2026-06-19 04:08:29.86372+00
d51883b9-2184-4390-8cf7-26e4dfd4acde	b5863590-fb53-4d22-a956-956aafc1c13e	WMS Admin	wms_admin	Full warehouse administration — global access to all warehouses, layout, inbound, put-away, outbound, gate, ASN, dispatches, and worker/device management	f	f	75	t	{}	2026-06-19 04:08:29.873711+00	2026-06-19 04:08:29.873714+00
ebde1aad-a955-4c5c-bde3-3c04f59a8207	b5863590-fb53-4d22-a956-956aafc1c13e	WMS Manager	wms_manager	Warehouse manager for assigned warehouse(s) — inbound, put-away, outbound, picking, and ASN coordination	f	f	70	t	{}	2026-06-19 04:08:29.88459+00	2026-06-19 04:08:29.884601+00
a322003d-70cd-42d3-aaab-e4b8b97f2702	b5863590-fb53-4d22-a956-956aafc1c13e	WMS Operator	wms_operator	Floor worker — dock scanning, put-away execution, picking, and gate verification	f	f	50	t	{}	2026-06-19 04:08:29.897259+00	2026-06-19 04:08:29.897262+00
4b428d72-d75e-4345-baa8-8cbe39bff9f5	b5863590-fb53-4d22-a956-956aafc1c13e	ASN Coordinator	asn_coordinator	Manages advance stock notices (ASN) and inter-warehouse transfers — create, confirm, and track fulfillment	f	f	65	t	{}	2026-06-19 04:08:29.907347+00	2026-06-19 04:08:29.90735+00
17e4507a-a4ea-4145-ad53-53b9fcb70dc7	b5863590-fb53-4d22-a956-956aafc1c13e	Organization Admin	organization_admin	Full access to all resources within this organization	t	f	90	t	{}	2026-06-19 05:42:20.36853+00	2026-06-19 05:42:20.368542+00
ebf3aa07-026e-4cf4-a433-2a0f7f31e21f	05397b7b-95bb-4560-b3d0-dff21b3db1ee	Warehouse Work User	warehouse_work_user	Limited warehouse worker access — QR login only, scan/read/update receiving slips and pick lists	t	f	5	t	{}	2026-06-22 10:39:29.592879+00	2026-06-22 10:39:29.592883+00
c5c5e398-54e3-4502-96aa-b47bee2e67b1	4acc19e3-fa77-463e-86e5-6838912edbf8	Organization Owner	owner	Full access to all features. Automatically assigned to the user who created the organization.	t	f	100	t	{}	2026-06-25 18:03:24.656428+00	2026-06-25 18:03:24.656432+00
6b6e658f-af1b-4609-8b82-487c8d753ff5	4acc19e3-fa77-463e-86e5-6838912edbf8	Administrator	org_admin	Full access to identity management plus read-only access to all business modules.	t	f	80	t	{}	2026-06-25 18:03:24.663446+00	2026-06-25 18:03:24.66345+00
9cd6512c-98a7-43bb-bf08-9544b667fb4c	4acc19e3-fa77-463e-86e5-6838912edbf8	Sales Agent	sales_agent	Full access to Sales & Orders module plus read-only Inventory.	t	f	40	t	{}	2026-06-25 18:03:24.678316+00	2026-06-25 18:03:24.67832+00
03e2183c-99ab-40e4-86e2-ec6da611c36e	4acc19e3-fa77-463e-86e5-6838912edbf8	Procurement Officer	procurement_officer	Full access to Procurement module plus read-only Inventory.	t	f	40	t	{}	2026-06-25 18:03:24.697781+00	2026-06-25 18:03:24.697786+00
0133bf63-480c-47b4-b129-9bc4f84e60e2	4acc19e3-fa77-463e-86e5-6838912edbf8	Accountant	accountant	Full access to Accounting module plus read-only access to Sales invoices.	t	f	40	t	{}	2026-06-25 18:03:24.713524+00	2026-06-25 18:03:24.713528+00
3855fcb2-225e-44d9-aa30-30e69f10ff36	4acc19e3-fa77-463e-86e5-6838912edbf8	Warehouse Staff	warehouse_staff	Full access to Inventory module only.	t	f	20	t	{}	2026-06-25 18:03:24.72843+00	2026-06-25 18:03:24.728437+00
57cedf7f-13e5-47a7-8729-2df0d2fde336	4acc19e3-fa77-463e-86e5-6838912edbf8	Viewer	viewer	Read-only access across all modules. Cannot create, edit, or delete anything.	t	f	10	t	{}	2026-06-25 18:03:24.74837+00	2026-06-25 18:03:24.748378+00
604cb142-29d2-4c18-b45c-4588e74d16c9	4acc19e3-fa77-463e-86e5-6838912edbf8	WMS Admin	wms_admin	Full warehouse administration — global access to all warehouses, layout, inbound, put-away, outbound, gate, ASN, dispatches, and worker/device management	f	f	75	t	{}	2026-06-25 18:03:24.769766+00	2026-06-25 18:03:24.76977+00
22817e25-becd-4837-90cf-7e0802b5446c	4acc19e3-fa77-463e-86e5-6838912edbf8	WMS Manager	wms_manager	Warehouse manager for assigned warehouse(s) — inbound, put-away, outbound, picking, and ASN coordination	f	f	70	t	{}	2026-06-25 18:03:24.794668+00	2026-06-25 18:03:24.794675+00
5e7c9503-385a-46e0-843b-646eb9a35f81	4acc19e3-fa77-463e-86e5-6838912edbf8	WMS Operator	wms_operator	Floor worker — dock scanning, put-away execution, picking, and gate verification	f	f	50	t	{}	2026-06-25 18:03:24.821894+00	2026-06-25 18:03:24.821901+00
65b8d6b5-9a80-42ef-abd8-5cff70edea44	4acc19e3-fa77-463e-86e5-6838912edbf8	ASN Coordinator	asn_coordinator	Manages advance stock notices (ASN) and inter-warehouse transfers — create, confirm, and track fulfillment	f	f	65	t	{}	2026-06-25 18:03:24.846005+00	2026-06-25 18:03:24.846009+00
e6fd493a-17f2-4b99-93c0-1dfb2bb41f3e	4acc19e3-fa77-463e-86e5-6838912edbf8	Warehouse Work User	warehouse_work_user	Limited warehouse worker — QR login only. Can scan, create/read/update receiving slips, and read/update pick lists.	t	f	5	t	{}	2026-06-25 18:03:24.857058+00	2026-06-25 18:03:24.857063+00
07ffcc1b-16d7-464e-b6da-83cb93474d84	4acc19e3-fa77-463e-86e5-6838912edbf8	Organization Admin	organization_admin	Full access to all resources within this organization	t	f	90	t	{}	2026-07-12 12:28:03.742142+00	2026-07-12 12:28:03.742145+00
\.

--
-- Data for Name: service_credentials; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.service_credentials (id, client_id, client_secret_hash, service_name, permissions, scopes, is_active, created_at, updated_at, last_used_at) FROM stdin;
\.

--
-- Data for Name: system_admin_audit_logs; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.system_admin_audit_logs (id, action_id, action_type, admin_user_id, admin_username, target_user_id, target_username, target_organization_id, target_organization_name, changes_made, performed_by, notes, performed_date, created_at, updated_at) FROM stdin;
\.

--
-- Data for Name: user_organization_roles; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.user_organization_roles (id, user_id, organization_id, role_id, is_primary, is_active, status, invited_by_id, invited_at, joined_at, extra_data, created_at, updated_at) FROM stdin;
427e6a8b-ac2b-4708-b378-14652ff94b39	20c0587a-7145-48e0-9471-caae8de8fe4d	05397b7b-95bb-4560-b3d0-dff21b3db1ee	8c372bb6-92de-4182-a77f-10604e8ab30b	t	t	active	\N	\N	2026-06-07 05:20:16.457128+00	{}	2026-06-07 05:20:16.470624+00	2026-06-07 05:20:16.470633+00
bbbb8d23-e057-4afc-bf2b-c1bd1042cf52	ba121f89-c767-4fdd-ab43-fd658c42a9d4	00000000-0000-0000-0000-000000000001	b0a6410b-fee0-410c-ab0e-ae4c9bb39dd3	t	t	active	\N	\N	2026-06-07 06:08:14.684716+00	{}	2026-06-07 06:08:14.686846+00	2026-06-07 06:08:14.68685+00
94945e19-4967-43b3-bbc6-9dc79797306b	fbfd7719-159d-4751-ba13-5fc9e35fa470	ddfad734-9afb-497b-81a3-ffc85caec590	b85d7824-a86f-4022-a5f7-cbcde4513708	t	t	active	\N	\N	2026-06-11 17:54:14.22608+00	{}	2026-06-11 17:54:14.231309+00	2026-06-11 17:54:14.231312+00
0b6ebbcb-41b0-497a-85f3-0982b2271e8c	6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	ddfad734-9afb-497b-81a3-ffc85caec590	42146f28-9b13-4af1-acd7-9d3da69b15d0	t	t	active	\N	\N	2026-06-11 19:21:37.772376+00	{}	2026-06-11 19:21:37.79809+00	2026-06-11 19:21:37.798098+00
54f4b259-81ec-446e-b24f-42a982ad8093	c0bf7fb1-687d-47cf-b020-b5c6007b589d	ddfad734-9afb-497b-81a3-ffc85caec590	42146f28-9b13-4af1-acd7-9d3da69b15d0	t	t	active	\N	\N	2026-06-12 04:49:52.628831+00	{}	2026-06-12 04:49:52.633057+00	2026-06-12 04:49:52.63306+00
67fbd54f-6aff-4319-8c19-872d08100177	8a5f437f-8277-4c85-89c3-cffbafe61fa4	ddfad734-9afb-497b-81a3-ffc85caec590	42146f28-9b13-4af1-acd7-9d3da69b15d0	t	t	active	\N	\N	2026-06-12 06:28:39.357077+00	{}	2026-06-12 06:28:39.363861+00	2026-06-12 06:28:39.363864+00
f8edd4e3-578d-4a0b-9842-d503e4b4c251	04aa34fe-f4ee-4f55-8624-b7e3665fd137	ddfad734-9afb-497b-81a3-ffc85caec590	42146f28-9b13-4af1-acd7-9d3da69b15d0	t	t	active	\N	\N	2026-06-12 08:28:00.735847+00	{}	2026-06-12 08:28:00.744543+00	2026-06-12 08:28:00.744546+00
b3cb93fe-a954-452b-b610-86c3635667df	57f8a2b2-3866-468f-b68d-d4950df43d1c	ddfad734-9afb-497b-81a3-ffc85caec590	42146f28-9b13-4af1-acd7-9d3da69b15d0	t	t	active	\N	\N	2026-06-12 08:41:09.139947+00	{}	2026-06-12 08:41:09.145203+00	2026-06-12 08:41:09.145207+00
69e5996a-e0cb-452f-8a18-009e7e01d75d	d842127f-7520-4612-987f-2faf88b8c0b9	ddfad734-9afb-497b-81a3-ffc85caec590	2cf8cc44-2f17-4c0a-a740-b6e4d6b5b411	t	t	active	\N	\N	2026-06-12 12:39:23.876988+00	{}	2026-06-12 12:39:23.887644+00	2026-06-12 12:39:23.887648+00
f25f5460-2683-42eb-990c-473fbc0635ec	f4c9c4a8-ad3f-4e90-afaf-f437b8644585	ddfad734-9afb-497b-81a3-ffc85caec590	42146f28-9b13-4af1-acd7-9d3da69b15d0	t	t	active	\N	\N	2026-06-12 12:40:57.095766+00	{}	2026-06-12 12:40:57.099354+00	2026-06-12 12:40:57.099357+00
d190251d-947c-48f7-8636-6f127bded899	ffae90be-8ac1-447d-bca1-90cace2ff429	b5863590-fb53-4d22-a956-956aafc1c13e	26e95172-da8c-42f4-be74-6b2a911dd002	t	t	active	\N	\N	2026-06-19 04:08:29.912359+00	{}	2026-06-19 04:08:29.919842+00	2026-06-19 04:08:29.919845+00
c8d2dbae-e63c-4bf3-b389-d1d6995b454e	171e65d7-60c5-451b-a5b6-c174fbc842c1	b5863590-fb53-4d22-a956-956aafc1c13e	d51883b9-2184-4390-8cf7-26e4dfd4acde	t	t	active	\N	\N	2026-06-19 04:18:23.891344+00	{}	2026-06-19 04:18:23.898643+00	2026-06-19 04:18:23.898647+00
c5ac772b-c862-4f10-8157-3cc5fa5ee11d	f2d43104-b97c-4554-a68a-b8ef9bb11dd1	b5863590-fb53-4d22-a956-956aafc1c13e	ebf3aa07-026e-4cf4-a433-2a0f7f31e21f	t	t	active	\N	\N	\N	{}	2026-06-22 10:47:26.095661+00	2026-06-22 10:47:26.095664+00
b22e7274-2a4a-4075-9cf8-3d7299653061	bd097e86-1759-4be1-9312-94e60346dbfd	b5863590-fb53-4d22-a956-956aafc1c13e	ebf3aa07-026e-4cf4-a433-2a0f7f31e21f	t	t	active	\N	\N	\N	{}	2026-06-25 17:42:37.026794+00	2026-06-25 17:42:37.026797+00
afcca97b-7052-44fa-90a9-b0bb7714d793	82b119e8-6a0d-41f9-9b01-0f34c3cc29b9	b5863590-fb53-4d22-a956-956aafc1c13e	ebde1aad-a955-4c5c-bde3-3c04f59a8207	t	t	active	\N	\N	2026-06-19 04:19:17.521998+00	{}	2026-06-19 04:19:17.53191+00	2026-06-25 17:57:14.46896+00
22ba5ffa-a6bb-4e04-ab03-bcf0a229d020	ca0eabd2-f796-4bd9-935a-47562d0880a4	4acc19e3-fa77-463e-86e5-6838912edbf8	c5c5e398-54e3-4502-96aa-b47bee2e67b1	t	t	active	\N	\N	2026-06-25 18:03:24.865892+00	{}	2026-06-25 18:03:24.873734+00	2026-06-25 18:03:24.873739+00
06d5a8f3-4cce-491f-818d-b25770e6b321	b9f2eb20-2fd2-4318-a67e-f8796fe1b128	4acc19e3-fa77-463e-86e5-6838912edbf8	22817e25-becd-4837-90cf-7e0802b5446c	t	t	active	\N	\N	2026-06-25 18:09:12.392749+00	{}	2026-06-25 18:09:12.398809+00	2026-06-25 18:09:12.398813+00
afd1d1c2-81f3-4cbc-92b6-c18958c8abb3	32440aa3-3413-4906-8282-bb860a838f64	4acc19e3-fa77-463e-86e5-6838912edbf8	ebf3aa07-026e-4cf4-a433-2a0f7f31e21f	t	t	active	\N	\N	\N	{}	2026-06-25 18:16:55.757728+00	2026-06-25 18:16:55.757731+00
\.

--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: horizon_user
--


COPY public.users (id, email, password_hash, first_name, last_name, display_name, phone, avatar_url, user_type, status, is_active, email_verified, email_verified_at, mfa_enabled, mfa_secret, mfa_backup_codes, last_login_at, last_login_ip, failed_login_attempts, locked_until, preferences, timezone, language, extra_data, deleted_at, created_at, updated_at, qr_code) FROM stdin;
ffae90be-8ac1-447d-bca1-90cace2ff429	PrestigeTTK@gmail.com	$2b$12$runKiXlgQFKRmFU1da8FQeFqdE.pRsCfeVKgz9URA1EBRIk0VYj52	Prestige	TTK	Prestige TTK	+919988776633	\N	user	active	t	f	\N	f	\N	\N	2026-06-25 18:10:19.90248+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-19 04:07:17.543297+00	2026-06-25 18:10:19.906849+00	\N
6b5f5d1c-28e8-4253-ae1c-acdded9e88c1	negi.yaten+wms_manager_01@gmail.com	$2b$12$LhxGPGlrHLfewGVdLhb3EuReOrxLph5gKTQ.h0J9AxAAYCHcrzChy	Prestige	Manager	\N	\N	\N	user	active	t	t	2026-06-11 19:21:37.676535+00	f	\N	\N	2026-06-12 06:25:27.177237+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-11 19:21:37.687439+00	2026-06-12 06:25:27.182316+00	\N
fbfd7719-159d-4751-ba13-5fc9e35fa470	wmsTesting@gmail.com	$2b$12$A6TCAhvG/qM3gZeSt2c20OzUzqus74dfmzYVCTt3hc9ieSGkjUqha	wmsTesting	SN	wmsTesting SN	+916622334423	\N	user	active	t	f	\N	f	\N	\N	2026-06-18 12:34:38.530761+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-11 17:53:48.184554+00	2026-06-18 12:34:38.544303+00	\N
04aa34fe-f4ee-4f55-8624-b7e3665fd137	negi.yaten+wms_manager_03@gmail.com	$2b$12$twG7AsXFBZIpqI6pSbJpk.bnod8yzo4GpOWmAOoefJslWBIpJbUHu	wms manager	transit	\N	\N	\N	user	active	t	t	2026-06-12 08:28:00.699345+00	f	\N	\N	2026-06-12 08:28:31.081128+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-12 08:28:00.704095+00	2026-06-12 08:28:31.084034+00	\N
57f8a2b2-3866-468f-b68d-d4950df43d1c	negi.yaten+wms_manager_04@gmail.com	$2b$12$qVdAJC/t5aGZtrTm4zqjjeYugrRpg5Sj1pHB82BPauCRaplUba7kG	wms Manager four	transit	\N	\N	\N	user	active	t	t	2026-06-12 08:41:09.116143+00	f	\N	\N	2026-06-12 08:41:26.607044+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-12 08:41:09.119744+00	2026-06-12 08:41:26.608186+00	\N
ca0eabd2-f796-4bd9-935a-47562d0880a4	TTK-prestige_ECITY@gmail.com	$2b$12$zM6DKk574FIAyM.Z4gVX6OtLJxFI5khHASOmIRW8/qoHx9Ace5hfa	TTK	eCITY	TTK eCITY	+919988776633	\N	user	active	t	f	\N	f	\N	\N	2026-06-25 18:15:36.105821+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-25 18:02:54.815638+00	2026-06-25 18:15:36.109023+00	\N
f4c9c4a8-ad3f-4e90-afaf-f437b8644585	negi.yaten+wms_ppt_manager_01@gmail.com	$2b$12$YlZOC8bunyWQswWt6zyDSuQlTzfMHG0pygqcrUasuTZUNrRr/80YC	PPT Wms one	Manager	\N	\N	\N	user	active	t	t	2026-06-12 12:40:57.077147+00	f	\N	\N	2026-06-12 14:29:01.076255+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-12 12:40:57.079746+00	2026-06-12 14:29:01.077739+00	\N
20c0587a-7145-48e0-9471-caae8de8fe4d	negi.yaten+Raj0078@gmail.com	$2b$12$KKD3R0fen4uE0TLPU5vpyOZ.Z/Jg4tWsnw11MHeqdnrYwdkL7Ca06	Raj	SN	Raj SN	+916565432562	\N	user	active	t	f	\N	f	\N	\N	2026-06-09 18:11:55.481858+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-04 13:08:49.067324+00	2026-06-09 18:11:55.485948+00	\N
ba121f89-c767-4fdd-ab43-fd658c42a9d4	superadmin@horizonsync.com	$2b$12$gLANE5dIxbaETan9DPeVw.nNuzjaH4aR4oGLmPWUwmc5y6E5un5te	Super	Admin	Super Admin	\N	\N	system_admin	active	t	t	2026-06-07 07:04:28.026537+00	f	\N	\N	2026-06-11 18:10:01.865416+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-07 06:08:14.672898+00	2026-06-11 18:10:01.870501+00	\N
d842127f-7520-4612-987f-2faf88b8c0b9	negi.yaten+wms_ppt_admin_01@gmail.com	$2b$12$SMe.5kLA1JoWnrIiTrhsreeQNgzo2ejvekDgEMnt5Tc3C0jz0.TWa	PPT Wms one	Admin	\N	\N	\N	user	active	t	t	2026-06-12 12:39:23.810899+00	f	\N	\N	2026-06-15 13:06:37.105201+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-12 12:39:23.817698+00	2026-06-15 13:06:37.11299+00	\N
32440aa3-3413-4906-8282-bb860a838f64	ram.lal@gmail.com	$2b$12$aRxEZWUCRmwvAW1Dr7yAAeo1fZAGaKHOnPSPiAVr/tJg5x9Bfo6T6	Ram	Lal	Ram Lal	0000000000	\N	warehouse_worker	active	t	t	\N	f	\N	\N	2026-06-25 18:17:09.94736+00	49.207.59.41	0	\N	{}	UTC	en	{"employee_id": "W-MQTTQI5N", "login_username": "ram.lal"}	\N	2026-06-25 18:16:55.751377+00	2026-06-25 18:17:09.948679+00	WRK-ZHH0RV0D6TEM
c0bf7fb1-687d-47cf-b020-b5c6007b589d	negi.yaten+user1@gmail.com	$2b$12$zb7iUJw0bt9GAIwFoWGNTOPfHFlNQZblK4gycaA4xYx4OyzfeHV/2	Lovleen	Rawat	\N	\N	\N	user	inactive	f	t	2026-06-12 04:49:52.614827+00	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{}	\N	2026-06-12 04:49:52.616148+00	2026-06-12 05:01:56.426841+00	\N
b9f2eb20-2fd2-4318-a67e-f8796fe1b128	devnegikec+ecity_ttk_manager@gmail.com	$2b$12$ZTsLFzlos0NwGUhuRqBuy.2U8YYEYAT8/RV/xhoonKnOxFbcc4Kfu	Ecity TTK Manager	SN	\N	\N	\N	user	active	t	t	2026-06-25 18:09:12.363536+00	f	\N	\N	2026-06-25 18:20:29.058075+00	49.207.59.41	0	\N	{}	UTC	en	{}	\N	2026-06-25 18:09:12.369981+00	2026-06-25 18:20:29.059485+00	\N
8a5f437f-8277-4c85-89c3-cffbafe61fa4	negi.yaten+wms_manager_02@gmail.com	$2b$12$TmYT1TUsqSbILAjJbf8Z4.1n0sYIxJemgGsFDERzq7TaZShfgnplS	wms manger	two	\N	\N	\N	user	active	t	t	2026-06-12 06:28:39.335775+00	f	\N	\N	2026-06-17 11:01:54.153258+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-12 06:28:39.340587+00	2026-06-17 11:01:54.154338+00	\N
171e65d7-60c5-451b-a5b6-c174fbc842c1	negi.yaten+ecity_admin@gmail.com	$2b$12$U91asp0SaXHx1XLRyWDcYOiWRJCDSy1u/20ENX64Io3ABGebXbMem	Admin	eCity	\N	\N	\N	user	active	t	t	2026-06-19 04:18:23.867855+00	f	\N	\N	2026-06-25 17:41:26.735228+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-19 04:18:23.871323+00	2026-06-25 17:41:26.736675+00	\N
f2d43104-b97c-4554-a68a-b8ef9bb11dd1	yaten@gmail.com	$2b$12$EIuo81L1D0ZmkIzYc3QH.eFHTy0Fhe7KNMO3VDQh0LtdkGvgdgAMq	yaten	singh	yaten singh	0000000000	\N	warehouse_worker	inactive	f	t	\N	f	\N	\N	\N	\N	0	\N	{}	UTC	en	{"employee_id": "W-MQP3CWM6", "login_username": "yaten.singh"}	\N	2026-06-22 10:47:26.078723+00	2026-06-25 17:42:15.392755+00	WRK-5LYXXIH0Q46E
bd097e86-1759-4be1-9312-94e60346dbfd	Ram.singh@gmail.com	$2b$12$MApxOg/So1K8jsLRNk2wzeMiuZ/0EVBaexUcHMhPrt/f3nk7E9IFS	Ram	Singh	Ram Singh	0000000000	\N	warehouse_worker	active	t	t	\N	f	\N	\N	2026-06-25 17:49:57.096564+00	49.207.59.41	0	\N	{}	UTC	en	{"employee_id": "W-MQTSIDP2", "login_username": "ram.singh"}	\N	2026-06-25 17:42:37.021154+00	2026-06-25 17:49:57.102564+00	WRK-V8KJFPBZHZ52
82b119e8-6a0d-41f9-9b01-0f34c3cc29b9	negi.yaten+ecity_manager@gmail.com	$2b$12$j1kRSyCW7VeeS9GaBurKfuyLAdue5q9fKnQdNSbQSVYNRGz29.Hhu	manger	eCity	\N	\N	\N	user	active	t	t	2026-06-19 04:19:17.489847+00	f	\N	\N	2026-06-25 17:56:07.340831+00	172.18.0.1	0	\N	{}	UTC	en	{}	\N	2026-06-19 04:19:17.494072+00	2026-06-25 17:56:07.344027+00	\N
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
-- Name: entity_audit_logs entity_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.entity_audit_logs
ADD CONSTRAINT entity_audit_logs_pkey PRIMARY KEY (id);

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
-- Name: otp_verifications otp_verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.otp_verifications
ADD CONSTRAINT otp_verifications_pkey PRIMARY KEY (id);

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
-- Name: service_credentials service_credentials_client_id_key; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.service_credentials
ADD CONSTRAINT service_credentials_client_id_key UNIQUE (client_id);

--
-- Name: service_credentials service_credentials_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.service_credentials
ADD CONSTRAINT service_credentials_pkey PRIMARY KEY (id);

--
-- Name: system_admin_audit_logs system_admin_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.system_admin_audit_logs
ADD CONSTRAINT system_admin_audit_logs_pkey PRIMARY KEY (id);

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
-- Name: idx_audit_logs_action_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_audit_logs_action_type ON public.system_admin_audit_logs USING btree (action_type, performed_date);

--
-- Name: idx_audit_logs_admin_user; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_audit_logs_admin_user ON public.system_admin_audit_logs USING btree (admin_user_id, performed_date);

--
-- Name: idx_audit_logs_performed_date; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_audit_logs_performed_date ON public.system_admin_audit_logs USING btree (performed_date);

--
-- Name: idx_audit_logs_target_org; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_audit_logs_target_org ON public.system_admin_audit_logs USING btree (
    target_organization_id,
    performed_date
);

--
-- Name: idx_entity_audit_action; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_entity_audit_action ON public.entity_audit_logs USING btree (action);

--
-- Name: idx_entity_audit_created_at; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_entity_audit_created_at ON public.entity_audit_logs USING btree (created_at);

--
-- Name: idx_entity_audit_table_record; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_entity_audit_table_record ON public.entity_audit_logs USING btree (table_name, record_id);

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

CREATE INDEX idx_invitations_org_created ON public.invitations USING btree (
    organization_id,
    created_at DESC
);

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
-- Name: idx_permissions_system_admin; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_permissions_system_admin ON public.permissions USING btree (code)
WHERE (
        (
            (code)::text ~~ 'system_admin.%'::text
        )
        OR ((code)::text = '*.*'::text)
        OR (
            (code)::text = 'system.admin'::text
        )
    );

--
-- Name: idx_role_permissions_role_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX idx_role_permissions_role_id ON public.role_permissions USING btree (role_id);

--
-- Name: idx_unique_master_org_name; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX idx_unique_master_org_name ON public.organizations USING btree (name)
WHERE (
        (name)::text = 'Master Organization'::text
    );

--
-- Name: idx_unique_master_org_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX idx_unique_master_org_type ON public.organizations USING btree (organization_type)
WHERE (
        organization_type = 'master'::public.organizationtype
    );

--
-- Name: ix_email_verifications_token_hash; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX ix_email_verifications_token_hash ON public.email_verifications USING btree (token_hash);

--
-- Name: ix_entity_audit_logs_organization_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_entity_audit_logs_organization_id ON public.entity_audit_logs USING btree (organization_id);

--
-- Name: ix_entity_audit_logs_user_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_entity_audit_logs_user_id ON public.entity_audit_logs USING btree (user_id);

--
-- Name: ix_organizations_billing_status; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_organizations_billing_status ON public.organizations USING btree (billing_status);

--
-- Name: ix_organizations_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_organizations_id ON public.organizations USING btree (id);

--
-- Name: ix_organizations_slug; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX ix_organizations_slug ON public.organizations USING btree (slug);

--
-- Name: ix_organizations_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_organizations_type ON public.organizations USING btree (organization_type);

--
-- Name: ix_otp_verifications_otp_type; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_otp_verifications_otp_type ON public.otp_verifications USING btree (otp_type);

--
-- Name: ix_otp_verifications_target; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_otp_verifications_target ON public.otp_verifications USING btree (target);

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
-- Name: ix_service_credentials_active; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_service_credentials_active ON public.service_credentials USING btree (is_active, client_id);

--
-- Name: ix_service_credentials_client_id; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE INDEX ix_service_credentials_client_id ON public.service_credentials USING btree (client_id);

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
-- Name: ix_users_qr_code; Type: INDEX; Schema: public; Owner: horizon_user
--

CREATE UNIQUE INDEX ix_users_qr_code ON public.users USING btree (qr_code);

--
-- Name: organizations single_master_org_trigger; Type: TRIGGER; Schema: public; Owner: horizon_user
--

CREATE TRIGGER single_master_org_trigger BEFORE INSERT OR UPDATE ON public.organizations FOR EACH ROW EXECUTE FUNCTION public.check_single_master_org();

--
-- Name: user_organization_roles trigger_validate_system_admin_role_assignment; Type: TRIGGER; Schema: public; Owner: horizon_user
--

CREATE TRIGGER trigger_validate_system_admin_role_assignment BEFORE INSERT OR UPDATE ON public.user_organization_roles FOR EACH ROW EXECUTE FUNCTION public.validate_system_admin_role_assignment();

--
-- Name: email_verifications email_verifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.email_verifications
ADD CONSTRAINT email_verifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users (id) ON DELETE CASCADE;

--
-- Name: organizations fk_organizations_parent_organization_id; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.organizations
ADD CONSTRAINT fk_organizations_parent_organization_id FOREIGN KEY (parent_organization_id) REFERENCES public.organizations (id) ON DELETE SET NULL;

--
-- Name: invitations invitations_accepted_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invitations
ADD CONSTRAINT invitations_accepted_user_id_fkey FOREIGN KEY (accepted_user_id) REFERENCES public.users (id) ON DELETE SET NULL;

--
-- Name: invitations invitations_invited_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invitations
ADD CONSTRAINT invitations_invited_by_id_fkey FOREIGN KEY (invited_by_id) REFERENCES public.users (id) ON DELETE SET NULL;

--
-- Name: invitations invitations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invitations
ADD CONSTRAINT invitations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE;

--
-- Name: invitations invitations_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.invitations
ADD CONSTRAINT invitations_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles (id) ON DELETE SET NULL;

--
-- Name: password_resets password_resets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.password_resets
ADD CONSTRAINT password_resets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users (id) ON DELETE CASCADE;

--
-- Name: refresh_tokens refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.refresh_tokens
ADD CONSTRAINT refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users (id) ON DELETE CASCADE;

--
-- Name: role_permissions role_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.role_permissions
ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions (id) ON DELETE CASCADE;

--
-- Name: role_permissions role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.role_permissions
ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles (id) ON DELETE CASCADE;

--
-- Name: roles roles_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.roles
ADD CONSTRAINT roles_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE;

--
-- Name: user_organization_roles user_organization_roles_invited_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.user_organization_roles
ADD CONSTRAINT user_organization_roles_invited_by_id_fkey FOREIGN KEY (invited_by_id) REFERENCES public.users (id);

--
-- Name: user_organization_roles user_organization_roles_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.user_organization_roles
ADD CONSTRAINT user_organization_roles_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations (id) ON DELETE CASCADE;

--
-- Name: user_organization_roles user_organization_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.user_organization_roles
ADD CONSTRAINT user_organization_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles (id) ON DELETE CASCADE;

--
-- Name: user_organization_roles user_organization_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: horizon_user
--

ALTER TABLE ONLY public.user_organization_roles
ADD CONSTRAINT user_organization_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users (id) ON DELETE CASCADE;

--
-- PostgreSQL database dump complete
--

\unrestrict qHOpkViatHyjNbyDQEHHVT3erdiD6FM5r8GYiD48WSFdonVH3124trC4li9QfDv
