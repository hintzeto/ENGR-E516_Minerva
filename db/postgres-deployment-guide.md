# PostgreSQL + pgvector on Jetstream2

This deployment runs the Minerva database on its own VM, separate from the UI and inference VMs.
It does not make the VM public. The Compose port is bound to the VM's private IP, and Jetstream
security rules should allow TCP 5432 only from the VM that runs the application.

The container uses the `pgvector/pgvector` image, which is PostgreSQL with the pgvector extension
already installed. `init.sql` enables the extension the first time the database is created. The
application creates its own tables.

## 1. Confirm network and VM details

Connect through the existing public jump host or from another VM on the same Jetstream private
network. Use the Linux account configured for the instance (the Exosphere example uses
`exouser`).

From your workstation, an SSH jump example is:

```bash
ssh -J exouser@<JUMP_HOST_PUBLIC_IP> exouser@<DB_VM_PRIVATE_IP>
```

On the database VM, confirm the private IP, free disk, and Docker:

```bash
ip -4 addr show
df -h
docker --version
docker compose version
```

Note the private IP; it is needed for `POSTGRES_BIND_IP` in step 3 and for the application's
connection string in step 7.

## 2. Check Jetstream network rules

Keep the database VM without a public IP. Allow inbound TCP port 5432 to this VM only from the
private IP of the VM that runs the application. For administration, allow SSH TCP port 22 from the
approved jump host.

The VM needs outbound access to pull the Docker image.

## 3. Put the deployment files on the VM

Place `postgres.compose.yaml`, `postgres.env.example`, and `init.sql` together in
`~/deploy/postgres`, then run:

```bash
cd ~/deploy/postgres
cp postgres.env.example .env
chmod 600 .env
nano .env
```

Edit these values:

- `POSTGRES_PASSWORD`: replace the example with a long random secret. Create one with
  `openssl rand -hex 32`.
- `POSTGRES_BIND_IP`: the private IP from step 1.
- `POSTGRES_IMAGE`: `pgvector/pgvector:pg16` follows the latest PostgreSQL 16 release. For a
  repeatable deployment, use a specific version tag from the image's tag list.

`POSTGRES_USER` and `POSTGRES_DB` can stay as `minerva`. Keep `.env` private and out of Git.

The user, password, and database name are applied only when the data volume is first created.
Changing them in `.env` afterwards does not change the existing database.

## 4. Check Compose expansion and pull the image

Validate the rendered Compose configuration:

```bash
docker compose --env-file .env -f postgres.compose.yaml config --quiet
```

No output and a successful exit indicate that the configuration is valid. This avoids printing
the expanded configuration, which contains the password. Then pull the image:

```bash
docker compose --env-file .env -f postgres.compose.yaml pull
```

## 5. Start PostgreSQL

```bash
docker compose --env-file .env -f postgres.compose.yaml up -d
docker compose --env-file .env -f postgres.compose.yaml ps
docker compose --env-file .env -f postgres.compose.yaml logs --tail=50 postgres
```

The status should become `healthy` within a few seconds. The logs should end with
`database system is ready to accept connections`.

## 6. Test locally on the VM

Confirm the pgvector extension is enabled:

```bash
docker compose --env-file .env -f postgres.compose.yaml exec postgres \
  psql -U minerva -d minerva -c '\dx'
```

The output should list `vector`. If the database was created before `init.sql` was in place, enable
it manually:

```bash
docker compose --env-file .env -f postgres.compose.yaml exec postgres \
  psql -U minerva -d minerva -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

## 7. Test from the application VM

From the application VM, check that the private endpoint accepts connections:

```bash
docker run --rm pgvector/pgvector:pg16 pg_isready -h <DB_VM_PRIVATE_IP> -p 5432
```

It should print `accepting connections`. To log in, enter the password from the database VM's
`.env` when prompted:

```bash
docker run --rm -it pgvector/pgvector:pg16 \
  psql -h <DB_VM_PRIVATE_IP> -U minerva -d minerva
```

The application reads its connection string from `DATABASE_URI`. Set it in the application's
environment (for the UI, `ui/.env`):

```text
DATABASE_URI=postgresql+psycopg://minerva:<POSTGRES_PASSWORD>@<DB_VM_PRIVATE_IP>:5432/minerva
```

The password is not copied automatically from the database VM. If it contains characters other
than letters and digits, URL-encode them; the value from `openssl rand -hex 32` needs no encoding.

## 8. Stop the service and preserve the data

From `~/deploy/postgres`:

```bash
docker compose --env-file .env -f postgres.compose.yaml down
```

This stops and removes the container and Compose network but keeps the named `pgdata` volume, so
users and stored documents survive a restart. Do not add `-v` unless you intend to delete the
database.

To back up the database to a file on the VM:

```bash
docker compose --env-file .env -f postgres.compose.yaml exec -T postgres \
  pg_dump -U minerva minerva > minerva-backup.sql
```
