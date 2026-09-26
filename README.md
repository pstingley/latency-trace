# Network Latency Tracer

A lightweight network diagnostic tool that continuously measures and visualizes traceroute latency, local Wi-Fi packet loss, end-to-end packet loss, and HTTPS responsiveness.

The project is also an experiment in **iterative human-AI systems engineering**: the final specification was not written completely *a priori*. It emerged through repeated cycles of observation, prompting, implementation, testing, failure, refinement, and acceptance.

## Why This Project Exists

The project began with a practical problem: Wi-Fi performance at a location varied dramatically, with measured throughput ranging from essentially zero to normal broadband speeds.

The original question was simply:

> Where is the problem occurring?

That led to a progressively more capable diagnostic tool.

Rather than relying on a single speed test, Network Latency Tracer attempts to distinguish among:

- latency between the computer and its local router;
- latency appearing farther along the network path;
- local Wi-Fi packet loss;
- end-to-end packet loss;
- routers that do not respond to traceroute;
- destinations that block traceroute but remain reachable by HTTPS;
- DNS identities of intermediate routers; and
- registered organizations associated with IP address blocks.

## What It Does

The program repeatedly runs traceroute to a selected destination and generates a live HTML visualization.

At startup:

```text
Network Latency Tracer
----------------------
Enter to trace to 1.1.1.1 or provide alternate URL:
```

Press **Enter** to use the default Cloudflare destination:

```text
1.1.1.1
```

Or enter another hostname, such as:

```text
lds.org
```

The program then continuously:

1. Runs traceroute to the destination.
2. Measures traceroute round-trip times.
3. Measures packet loss between the computer and Hop 1.
4. Measures packet loss between the computer and the destination.
5. Resolves reverse-DNS names where available.
6. Uses Registration Data Access Protocol (RDAP) registration information when no Fully Qualified Domain Name (FQDN) is available.
7. Falls back to an HTTPS GET request when traceroute fails.
8. Writes the measurements to a timestamped CSV file.
9. Generates a timestamped HTML visualization.
10. Automatically refreshes the HTML report as new measurements arrive.

No web server is required.

## Visualization

Each measurement is represented by a horizontal latency bar.

**Longer bar = greater measured traceroute latency.**

Different colors identify different traceroute hops.

A colored:

```text
*
```

means that the hop did not respond to traceroute.

A colored:

```text
|
```

means that the hop responded but did not extend the accumulated latency visualization.

The program does **not** invent latency for nonresponding hops.

### Important Interpretation

Traceroute round-trip times are independent measurements from the originating computer to each router.

They are **not direct measurements of the latency between adjacent routers**.

For that reason, the colored sections should be understood as a diagnostic visualization of traceroute observations rather than a literal decomposition of physical link latency.

See [`SPEC.md`](SPEC.md) for the precise visualization semantics and limitations.

## Packet Loss

Two independent packet-loss measurements are taken during each successful cycle.

### Wi-Fi loss

Packet loss between the computer and the first responding hop:

```text
Wi-Fi loss = packet loss between this computer and Hop 1.
```

This is intended to expose problems on the local network or Wi-Fi path.

### Net loss

Packet loss between the computer and the selected destination:

```text
Net loss = packet loss between this computer and TARGET.
```

An intermediate traceroute `*` is **not** automatically interpreted as packet loss because routers commonly filter or deprioritize traceroute traffic.

## When Traceroute Is Blocked

Some networks and destinations do not respond to traceroute even though their web services are operating normally.

When traceroute fails, Network Latency Tracer performs an HTTPS GET request instead.

For example:

```text
Traceroute failed — HTML response: 633.8 ms
```

This establishes that an HTTPS server responded and records the elapsed request/response time.

An HTTP error such as `403` or `404` still demonstrates that the remote HTTPS server was reached and responded.

HTTPS response time is kept separate from traceroute measurements and is not drawn as though it were another traceroute hop.

## Identifying Network Hops

The program identifies responding IP addresses using the following hierarchy:

```text
Fully Qualified Domain Name (FQDN)
              ↓
       if unavailable
              ↓
Registered organization from RDAP
              ↓
       if unavailable
              ↓
        IP address only
```

This can produce hop descriptions such as:

```text
Hop 2: 71.114.105.1 (lo0-100.washdc-vfttp-332.verizon-gni.net)
Hop 5: 204.148.170.122 (Verizon Business)
Hop 6: 173.245.63.145 (Cloudflare, Inc.)
Hop 8: 1.1.1.1 (one.one.one.one)
```

RDAP information identifies registration associated with an IP address block. It does not necessarily identify the owner or operator of the particular physical router.

DNS and RDAP results are cached during execution.

## Output

Each execution creates its own timestamped files:

```text
latency_trace_YYYY-MM-DD_HHMMSS.csv
latency_trace_YYYY-MM-DD_HHMMSS.html
```

For example:

```text
latency_trace_2026-09-26_171806.csv
latency_trace_2026-09-26_171806.html
```

The HTML report opens automatically in Google Chrome and refreshes as measurements accumulate.

## Running the Program

The current baseline was developed on macOS.

Run:

```bash
/usr/bin/python3 latency_trace.py
```

Optionally check the program for Python syntax errors first:

```bash
/usr/bin/python3 -m py_compile latency_trace.py
```

If that command produces no output, the syntax check succeeded.

Stop the measurement loop with:

```text
Control-C
```

The program then reports the locations of the generated CSV and HTML files.

## Repository Contents

### `latency_trace.py`

The working Network Latency Tracer implementation.

### `SPEC.md`

The specification of the completed baseline, including:

- functional behavior;
- visualization semantics;
- measurement methods;
- output formats;
- design decisions;
- known limitations; and
- acceptance criteria.

### `PROMPT_HISTORY.md`

A reconstructed engineering history showing how the requirements and design evolved through the human-AI interaction.

It is **not presented as a verbatim transcript**. It records the significant prompts, observations, decisions, changes, and resulting requirements.

## An Experiment in Emergent Specification

An important secondary result of this project is the development process itself.

The final system could not realistically have been specified in complete detail before development began.

Requirements emerged because the user could observe intermediate implementations and say things such as:

- the graph should represent latency through its physical length;
- a nonresponding router should be represented without inventing latency;
- a responding hop still needs to remain visible when its RTT is lower than an earlier hop;
- local packet loss and end-to-end packet loss should be distinguished;
- traceroute failure does not imply application-layer failure;
- an HTTPS request can provide a useful fallback measurement;
- the HTTPS measurement should show elapsed time rather than a wall-clock response timestamp;
- reverse DNS can make hops understandable;
- IP registration information can provide useful context when reverse DNS is unavailable; and
- presentation details matter to the usability of the diagnostic display.

Many of these requirements became apparent **only after an earlier implementation was seen and evaluated**.

The development process therefore resembled:

```text
Problem
   ↓
Prompt
   ↓
Implementation
   ↓
Observation
   ↓
New or refined requirement
   ↓
Prompt
   ↓
Implementation
   ↓
Test
   ↓
Acceptance or further refinement
   ↓
Updated specification
```

The specification was therefore both an input to and an **output of** engineering.

## Prompts as Configuration Items

This project raises a broader configuration-management question for agentic software engineering:

> If prompts materially cause requirements, design decisions, source-code changes, tests, and documentation to be created or modified, should significant prompts themselves be managed as Configuration Items (CIs)?

For this project, a useful traceability model is:

```text
Prompt CI
   ↓
Requirement / Design Decision
   ↓
Implementation Change
   ↓
Observed Result
   ↓
Acceptance / Rejection / Refinement
   ↓
Specification Baseline
```

Under this model, preserving only the final source code and final specification loses part of the engineering provenance.

`PROMPT_HISTORY.md` is an initial attempt to preserve that provenance.

## Project Artifacts and Traceability

The repository intentionally preserves three different views of the system:

```text
PROMPT_HISTORY.md
        ↓
Why and how did the requirements evolve?

SPEC.md
        ↓
What is the accepted system baseline?

latency_trace.py
        ↓
How is that baseline implemented?
```

Together they provide substantially more engineering context than the source code alone.

## Current Status

The repository represents the accepted **September 26, 2026 baseline** of Network Latency Tracer.

The baseline was reached when the resulting visualization, hop identification, packet-loss measurements, HTTPS fallback, and report presentation were tested interactively and accepted by the user.

Further development should preserve the distinction between:

- measured data;
- visualization conventions;
- inferred information; and
- registration/identification metadata.

That distinction is fundamental to the diagnostic integrity of the tool.
