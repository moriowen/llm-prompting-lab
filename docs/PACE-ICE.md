# Running inference on PACE ICE

The 8 GB M2 Air is the bottleneck for this project: CoT arms (a 1536-token budget on
task 2) and the 7B slot are slow enough that a full sweep does not finish. Georgia
Tech's PACE ICE cluster provides the GPU. **Only inference moves.** Prompt building,
grading, traces and analysis stay on the Mac, and ICE serves nothing but ollama.

This document is the runbook. It records what worked, and — more usefully — the four
things that went wrong the first time, since each one produces a misleading error.

## The shape of it

```
Mac                              ICE login node            ICE compute node
main.py run  ──HTTP──> localhost:11434 ──ssh -L──> :11434  ollama serve (A100)
  prompts, grading,                                          gemma3:4b, mistral:7b, …
  runs/*.jsonl
```

The tunnel puts the remote server on the Mac's own `localhost:11434`, so no code path
changes between backends. `src/utils/constants.py` reads `BDS_OLLAMA_HOST` only for a
non-default port.

## Runbook

### 0. VPN

Connect GlobalProtect to `vpn.gatech.edu`. The PACE hostnames do not resolve off the GT
network.

### 1. Log in

```sh
ssh amohite8@login-ice.pace.gatech.edu
```

The login node is for Slurm commands only — never run inference on it.

### 2. Allocate a GPU

```sh
salloc -p ice-gpu --gres=gpu:a100:1 --cpus-per-task=8 --mem=64G --time=05:00:00
```

`ice-gpu` carries V100, A40, A100, L40S, H100 and H200; the partition limit is 16 hours.
The shell moves to a compute node. Confirm with `hostname` and `nvidia-smi` — an A100
80 GB PCIe reports ~79.2 GiB free, which is far more than any model here needs.

**The node name changes with every allocation.** Nothing should hardcode it.

### 3. Serve ollama on the node

```sh
module load ollama/0.12.11              # not available on the login node
OLLAMA_HOST=0.0.0.0:11434 ollama serve > ~/ollama.log 2>&1 &
ollama pull gemma3:4b                   # each node has its own model store
```

`0.0.0.0` rather than the default loopback is what makes the node reachable from the
tunnel. Verify the binding — `curl localhost:11434` succeeds either way and proves
nothing:

```sh
curl -s http://$(hostname -s):11434/api/tags
```

Fetching by node name is exactly what the tunnel does, so a JSON reply here means the
tunnel will work.

### 4. Tunnel, from the Mac

Stop any local `ollama serve` first — it holds port 11434 — then:

```sh
./scripts/ice-tunnel.sh
```

It resolves the current node from `squeue`, opens `ssh -L 11434:<node>:11434`, and curls
`/api/tags` through the forward so you get `tunnel up: … ollama answering.` rather than a
silent terminal. Leave the window open for the whole run; Ctrl-C closes it.

To stop being prompted for a password: `ssh-copy-id amohite8@login-ice.pace.gatech.edu`.

### 5. Run, from the Mac

```sh
BDS_BACKEND=pace-ice-a100 python3 -m src.main ping
BDS_BACKEND=pace-ice-a100 python3 -m src.main run --models mistral-7b --arms cot --temps grid --k 5
```

`ping` lists what is pulled on whichever host is configured and flags ladder models
missing there. `BDS_BACKEND` is provenance: it goes into every cell's trace header,
because a tunnel makes both backends look identical from the client, and `wall_ms` from
an A100 is not `wall_ms` from a fanless laptop. Export it for the session if you would
rather not prefix each command.

### 6. Reconnecting after a dropped SSH

```sh
squeue -u $USER                                   # find the job
srun --jobid=<JOB_ID> --overlap --pty bash        # note --overlap, see below
```

The allocation and the `ollama serve` on it survive your SSH dropping. The tunnel does
not — re-run `ice-tunnel.sh`, which re-reads the node name.

## Gotchas

Each of these cost time, and each reports something other than its actual cause.

**The login hostname is `login-ice.pace.gatech.edu`, not `pace-ice…`.** The wrong name
gives `ssh: Could not resolve hostname`, which reads like a VPN failure. Tell them apart
by which nameserver answers: a reply from `130.207.x` is a GT resolver, so the VPN is up
and the name is simply wrong. `scripts/ice-tunnel.sh` now pre-checks this with `dig`.

**`srun --jobid=… --pty bash` hangs without `--overlap`.** PACE's `salloc` launches your
shell as step 0, which holds the whole allocation, so a second `srun` waits behind it
forever. Ctrl-C then prints `Unable to create step for job …: Job/step already completing
or completed`, which looks like the job died — it has not; check `squeue` before
reacting. `--overlap` permits sharing resources with the existing step.

**An interactive `salloc` job is tied to the shell that launched it.** Close that shell
and the allocation tears down, taking the backgrounded `ollama serve` with it. For long
unattended sweeps prefer a batch job (below).

**Model stores are per node.** A new allocation usually means a new node with nothing
pulled. `main.py ping` reports exactly which ladder models are missing on the current
backend, with the `ollama pull` commands to fix it.

## Comparability

The point of the cluster is speed, not different results, so nothing about sampling
changes when the backend does:

- Sampling options in `src/utils/config.py` stay pinned exactly as they are, including
  `num_thread: 4`, which is inert on a GPU. Only hardware moves.
- Check the digest matches the laptop's before mixing backends within one model.
  `gemma3:4b` was verified identical (`a2af6cc3eb7fa8be850…`) on 2026-09-03.
- The ICE ollama is `0.12.11`; the Mac's may differ. Re-run `main.py models` after
  switching so `data/models.json` records the digests actually used.
- Timings are not comparable across backends. That is why `backend` and `host` are in
  every trace header rather than assumed.

## Batch alternative (not yet used)

`salloc` dies with its shell, which makes it a poor host for a multi-hour sweep. A batch
job does not. Untested here, recorded as the next thing to try if disconnects become a
problem:

```sh
#!/bin/bash
#SBATCH -p ice-gpu --gres=gpu:a100:1 -c 8 --mem=64G -t 08:00:00 -J ollama-serve
module load ollama/0.12.11
hostname > ~/ollama-node.txt            # so the tunnel can read the node back
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

Submit with `sbatch`, then tunnel to the node named in `~/ollama-node.txt`. It survives
SSH drops, VPN drops and a closed laptop for the full wall time.
