# vLLM CPU smoke test on Jetstream2

This deployment is for testing the OpenAI-compatible vLLM API on `minerva-inference-test`.
It does not make the VM public. The Compose port is bound to the VM's private IP, and Jetstream
security rules should allow TCP 8000 only from the LangGraph VM. For workstation testing, use the
SSH tunnel in step 7 rather than allowing port 8000 from the jump host.

## Hardware caveat

The VM reports an AMD EPYC Milan (Zen 3) CPU. Current vLLM CPU documentation recommends AVX-512
for x86_64 and lists AVX2 as limited-feature support. The generic `x86_64` CPU image is therefore
a best-effort smoke test on Milan, not a supported performance target. vLLM's separate AMD Zen
optimized Docker target is for Zen 4 / Zen 5 and is not intended for Milan.

## 1. Confirm network and VM details

Connect through the existing public jump host or from another VM on the same Jetstream private
network. Use the Linux account configured for the instance (the Exosphere example uses
`exouser`).

From your workstation, an SSH jump example is:

```bash
ssh -J exouser@minerva_main_ip_addr exouser@vllm_vm_ip_addr
```

*Optional:* On `minerva-inference-test`, confirm the private IP, CPU, RAM, disk, and Docker:

```bash
ip -4 addr show
lscpu | grep -E 'Model name|CPU\(s\)|Flags'
free -h
df -h
docker --version
docker compose version
```

The `vllm.env.example` assumes the private IP is still `10.4.36.241`. Change it if `ip -4 addr show`
reports another address. Ensure there is enough free disk for the image and model cache; the
model-cache volume persists across container restarts.

## 2. Check Jetstream network rules

Keep the inference VM without a public IP. Allow inbound TCP port 8000 to this VM only from the
LangGraph VM's private IP. For administration and workstation tunneling, allow SSH TCP port 22
from the approved jump host. The SSH tunnel in step 7 reaches the private API through that SSH
connection, so it does not require opening port 8000 to the jump host or workstation.

The VM needs outbound access to pull the Docker image and download model files from Hugging Face.
No public IP does not itself guarantee that outbound access is available; it depends on the
Jetstream network route and egress policy.

## 3. Put the deployment files on the VM

Place `vllm.compose.cpu.yaml` and `vllm.env.example` in `~/deploy/vllm`, then run:

```bash
cd ~/deploy/vllm
cp vllm.env.example .env
chmod 600 .env
nano .env
```

Edit these values:

- `VLLM_BIND_IP`: `10.4.36.241` or the actual private IP from step 1.
- `VLLM_API_KEY`: replace the example with a long random secret. Keep `.env` private and out of Git.
- `HF_TOKEN`: leave blank for public models. Set it only if the model requires Hugging Face access.
- `VLLM_IMAGE`: `latest-x86_64` is convenient for a first smoke test. For a repeatable deployment,
  use a specific version tag available on the vLLM CPU image repository.

The API key does not authenticate every vLLM endpoint, so keep port 8000 restricted to trusted
private callers even when the key is configured.

The example uses Qwen3 0.6B, float32, a 2,048-token context, one active sequence, and a 2 GiB CPU
KV cache. These small settings limit memory use for the test VM; CPU generation may still be slow.
You can create a random key with `openssl rand -hex 32`, then paste the result into `.env`.

## 4. Check Compose expansion and pull the image

From `~/deploy/vllm`, validate the rendered Compose configuration:

```bash
docker compose --env-file .env -f vllm.compose.cpu.yaml config --quiet
```

No output and a successful exit indicate that the Compose configuration is valid. This avoids
printing the expanded configuration, which contains the API key. Then pull the image:

```bash
docker compose --env-file .env -f vllm.compose.cpu.yaml pull
```

## 5. Start vLLM and watch startup

Start in the foreground for the first attempt so any CPU instruction error is visible immediately:

```bash
docker compose --env-file .env -f vllm.compose.cpu.yaml up
```

The first start downloads the model and can take several minutes. Wait for the API server to report
that it is ready. If it starts successfully, press `Ctrl-C` to stop the foreground attachment; this
stops the container but keeps the model-cache volume.

The message `No available shared memory broadcast block found in 60 seconds` is a periodic wait
warning, not necessarily a fatal error or evidence that `/dev/shm` is full. If startup continues,
give it more time. If it repeats without progress, inspect the surrounding logs for a stuck or
failed worker before deciding whether to stop the service.

Then start it in the background:

```bash
docker compose --env-file .env -f vllm.compose.cpu.yaml up -d
docker compose --env-file .env -f vllm.compose.cpu.yaml ps
docker compose --env-file .env -f vllm.compose.cpu.yaml logs --tail=100 vllm
```

If the process reports `Illegal instruction` / exit code 132, or the CPU backend rejects the Milan
CPU features, this image/build is not compatible with the VM. Do not keep restarting it; use a
CPU VM with supported AVX-512 features (such as Zen 4+), a GPU VM, or a CPU inference server that
supports Zen 3.

Again, this may take a few minutes.

## 6. Test the API locally on the VM

Check readiness from the inference VM:

```bash
set -a
. ./.env
set +a

curl -sS -o /dev/null -w 'HTTP %{http_code}\n'  "http://10.4.36.241:8000/health"
```

It will return ```HTTP 200``` if all is well.

Submit a small chat request using the API key from `.env`:

```bash
curl -sS "http://10.4.36.241:8000/v1/chat/completions" \
  -H "Authorization: Bearer ${VLLM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-0.6B","messages":[{"role":"user","content":"Reply with one short hello."}],"max_tokens":32}'
```

## 7. Test from another private VM

From another VM, test the inference VM private endpoint:

```bash
curl -sS -o /dev/null -w 'HTTP %{http_code}\n'  "http://10.4.36.241:8000/health"
```

For LangGraph's OpenAI-compatible model client, use:

```text
Base URL: http://10.4.36.241:8000/v1
Model: Qwen/Qwen3-0.6B
API key: the VLLM_API_KEY value from this VM's .env
```

Here is an example. Enter the exact API key from the inference VM's `.env` when prompted:

```bash
read -rsp 'vLLM API key: ' VLLM_API_KEY
printf '\n'

curl -sS "http://10.4.36.241:8000/v1/chat/completions" \
  -H "Authorization: Bearer ${VLLM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-0.6B","messages":[{"role":"user","content":"Reply with one short hello."}],"max_tokens":32}'

unset VLLM_API_KEY
```

The variable is read locally on the client VM; it is not automatically copied from the inference
VM's `/home/exouser/deploy/vllm/.env` file.

Store the same API key securely in the LangGraph environment. Restrict Jetstream inbound TCP 8000
to the LangGraph VM's private IP. Do not open 8000 to the public internet.

To test from your workstation without a public IP on the inference VM, use SSH ProxyJump through
the approved public jump host (leave the SSH session open):

```bash
ssh -J exouser@<JUMP_HOST_PUBLIC_IP> \
  -L 8000:10.4.36.241:8000 \
  exouser@10.4.36.241
```

Then in another local terminal, call `http://127.0.0.1:8000/health` or the chat endpoint. Do not
bind the Compose port to `0.0.0.0` for this test.

## 8. Stop the service and preserve the model cache

From `~/deploy/vllm`:

```bash
docker compose --env-file .env -f vllm.compose.cpu.yaml down
```

This stops and removes the container and Compose network but keeps the named model-cache volume.
Do not add `-v` unless you also intend to delete the cached model.
