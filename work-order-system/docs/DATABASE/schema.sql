-- SQLite schema dump of db.sqlite3 (generated from Django migrations)
CREATE TABLE "service_attachment" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "original_name" varchar(255) NOT NULL, "uploaded_at" datetime NOT NULL, "uploaded_by_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "work_order_id" bigint NOT NULL REFERENCES "service_workorder" ("id") DEFERRABLE INITIALLY DEFERRED, "file" varchar(100) NOT NULL);

CREATE TABLE "service_comment" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "body" text NOT NULL, "is_internal" bool NOT NULL, "created_at" datetime NOT NULL, "author_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "work_order_id" bigint NOT NULL REFERENCES "service_workorder" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "service_profile" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "role" varchar(12) NOT NULL, "phone" varchar(32) NOT NULL, "company" varchar(120) NOT NULL, "created_at" datetime NOT NULL, "user_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "service_workorder" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "title" varchar(180) NOT NULL, "description" text NOT NULL, "priority" varchar(8) NOT NULL, "status" varchar(12) NOT NULL, "location" varchar(240) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "completed_at" datetime NULL, "closed_at" datetime NULL, "customer_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "technician_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "service_workorderevent" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "event_type" varchar(24) NOT NULL, "from_value" varchar(180) NOT NULL, "to_value" varchar(180) NOT NULL, "note" text NOT NULL, "created_at" datetime NOT NULL, "actor_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "work_order_id" bigint NOT NULL REFERENCES "service_workorder" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE INDEX "service_attachment_uploaded_by_id_a403d5e7" ON "service_attachment" ("uploaded_by_id");

CREATE INDEX "service_attachment_work_order_id_ce380e67" ON "service_attachment" ("work_order_id");

CREATE INDEX "service_comment_author_id_d80635e8" ON "service_comment" ("author_id");

CREATE INDEX "service_comment_work_order_id_9f3a812b" ON "service_comment" ("work_order_id");

CREATE INDEX "service_wor_custome_bda7db_idx" ON "service_workorder" ("customer_id", "created_at");

CREATE INDEX "service_wor_status_f185b0_idx" ON "service_workorder" ("status", "priority");

CREATE INDEX "service_wor_technic_0af8f9_idx" ON "service_workorder" ("technician_id", "status");

CREATE INDEX "service_workorder_customer_id_8d93913a" ON "service_workorder" ("customer_id");

CREATE INDEX "service_workorder_technician_id_f8c5044c" ON "service_workorder" ("technician_id");

CREATE INDEX "service_workorderevent_actor_id_89ae19a1" ON "service_workorderevent" ("actor_id");

CREATE INDEX "service_workorderevent_work_order_id_f35a44a1" ON "service_workorderevent" ("work_order_id");

