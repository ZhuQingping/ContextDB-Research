-- Reference only. Caller sets a new dedicated schema search_path in an existing test DB.
-- Not a production migration; no production RLS, role provisioning or HA validation.
CREATE TABLE model_profiles (
 id text PRIMARY KEY, version integer NOT NULL CHECK(version>0),
 llm_model text NOT NULL, embedding_model text NOT NULL,
 embedding_dimension integer NOT NULL CHECK(embedding_dimension>0),
 reranker_model text NOT NULL, config_hash text NOT NULL
);
CREATE TABLE workspaces (
 id text PRIMARY KEY, cloud_project_id text NOT NULL, region text NOT NULL,
 state text NOT NULL CHECK(state IN ('PROVISIONING','READY','FROZEN','DELETING')),
 auth_epoch bigint NOT NULL DEFAULT 1 CHECK(auth_epoch>0)
);
CREATE TABLE memberships (
 workspace_id text REFERENCES workspaces(id), subject_id text,
 role text NOT NULL, state text NOT NULL, PRIMARY KEY(workspace_id,subject_id)
);
CREATE TABLE cells (
 id text PRIMARY KEY, region text NOT NULL, model_profile_id text NOT NULL REFERENCES model_profiles(id),
 internal_endpoint text NOT NULL, state text NOT NULL,
 upstream_sha text NOT NULL, image_digest text NOT NULL, schema_version text NOT NULL
);
CREATE TABLE placements (
 workspace_id text PRIMARY KEY REFERENCES workspaces(id), cell_id text NOT NULL REFERENCES cells(id),
 schema_name text NOT NULL, route_epoch bigint NOT NULL CHECK(route_epoch>0), state text NOT NULL,
 UNIQUE(cell_id,schema_name)
);
CREATE TABLE banks (
 id text PRIMARY KEY, workspace_id text NOT NULL REFERENCES workspaces(id), public_bank_id text NOT NULL,
 native_bank_id text NOT NULL, kind text NOT NULL CHECK(kind IN ('memory','kb')),
 owner_subject text NOT NULL, state text NOT NULL, content_epoch bigint NOT NULL DEFAULT 1,
 UNIQUE(workspace_id,id), UNIQUE(workspace_id,public_bank_id), UNIQUE(workspace_id,native_bank_id),
 FOREIGN KEY(workspace_id,owner_subject) REFERENCES memberships(workspace_id,subject_id)
);
CREATE TABLE bank_grants (
 workspace_id text, bank_id text, subject_id text, actions text[] NOT NULL,
 PRIMARY KEY(workspace_id,bank_id,subject_id),
 FOREIGN KEY(workspace_id,bank_id) REFERENCES banks(workspace_id,id),
 FOREIGN KEY(workspace_id,subject_id) REFERENCES memberships(workspace_id,subject_id)
);
CREATE TABLE api_keys (
 key_id text PRIMARY KEY, digest bytea NOT NULL CHECK(octet_length(digest)=32),
 pepper_version integer NOT NULL CHECK(pepper_version>0), workspace_id text NOT NULL, subject_id text NOT NULL,
 scopes text[] NOT NULL CHECK(cardinality(scopes)>0), bank_constraints jsonb NOT NULL DEFAULT '{}'::jsonb,
 created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL,
 revoked_at timestamptz, CHECK(expires_at>created_at),
 UNIQUE(workspace_id,subject_id,key_id),
 FOREIGN KEY(workspace_id,subject_id) REFERENCES memberships(workspace_id,subject_id)
);
CREATE TABLE request_ledger (
 workspace_id text NOT NULL, bank_id text NOT NULL, action text NOT NULL, idempotency_key text NOT NULL,
 payload_hash text NOT NULL, operation_id uuid NOT NULL UNIQUE, state text NOT NULL,
 subject_id text NOT NULL, key_id text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(workspace_id,bank_id,action,idempotency_key),
 FOREIGN KEY(workspace_id,subject_id) REFERENCES memberships(workspace_id,subject_id),
 FOREIGN KEY(workspace_id,subject_id,key_id) REFERENCES api_keys(workspace_id,subject_id,key_id),
 FOREIGN KEY(workspace_id,bank_id) REFERENCES banks(workspace_id,id)
);
CREATE TABLE jobs (
 job_id text PRIMARY KEY, workspace_id text NOT NULL REFERENCES workspaces(id), kind text NOT NULL,
 resource_id text NOT NULL, phase text NOT NULL, attempt integer NOT NULL DEFAULT 0 CHECK(attempt>=0),
 next_retry_at timestamptz, payload_ref text, UNIQUE(workspace_id,job_id)
);
CREATE TABLE source_revisions (
 workspace_id text NOT NULL REFERENCES workspaces(id), source_id text NOT NULL, revision integer NOT NULL CHECK(revision>0),
 content_hash text NOT NULL, raw_ref text NOT NULL, author text NOT NULL, state text NOT NULL,
 PRIMARY KEY(workspace_id,source_id,revision),
 FOREIGN KEY(workspace_id,author) REFERENCES memberships(workspace_id,subject_id)
);
CREATE TABLE publications (
 id text PRIMARY KEY, workspace_id text NOT NULL, kb_id text NOT NULL,
 source_id text NOT NULL, source_revision integer NOT NULL, reviewer text NOT NULL,
 native_document_id text NOT NULL, state text NOT NULL, job_id text NOT NULL,
 FOREIGN KEY(workspace_id,kb_id) REFERENCES banks(workspace_id,id),
 FOREIGN KEY(workspace_id,source_id,source_revision) REFERENCES source_revisions(workspace_id,source_id,revision),
 FOREIGN KEY(workspace_id,reviewer) REFERENCES memberships(workspace_id,subject_id),
 FOREIGN KEY(workspace_id,job_id) REFERENCES jobs(workspace_id,job_id)
);
CREATE TABLE usage_events (
 event_id text PRIMARY KEY, workspace_id text NOT NULL REFERENCES workspaces(id), operation_id uuid,
 attempt_id text NOT NULL, provider text NOT NULL, units jsonb, status text NOT NULL
);
-- resource_id/payload_ref/bank_constraints are app-validated references or structured policies.
-- revoked/expired keys require live authorization checks; CHECK constraints do not expire keys over time.
-- Cross-region placements and bank.kind=kb publication requirements need service-level checks.
