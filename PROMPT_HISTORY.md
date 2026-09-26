# PROMPT_HISTORY.md

# Network Latency Tracer --- Prompt and Change History

**Project:** Network Latency Tracer\
**Date of completed baseline:** 2026-09-26\
**Author / user:** Patrick Stingley\
**Purpose of this document:** Preserve the requirements-discovery
history that produced the completed `SPEC.md` and `latency_trace.py`.

> **Important:** This is a reconstructed engineering history, not a
> verbatim export of the ChatGPT conversation. It captures the
> substantive prompts, observations, decisions, revisions, and accepted
> behaviors preserved in the project conversation/context. The original
> conversation remains the authoritative source for exact wording.

------------------------------------------------------------------------

## 1. Why This File Exists

The Network Latency Tracer did not begin with a complete specification.

It began with a practical problem: unstable network performance.
Requirements emerged as the user observed results, challenged
assumptions, inspected screenshots, tested intermediate versions, and
requested changes.

The development pattern was therefore approximately:

``` text
problem
  ↓
prompt / requirement
  ↓
working implementation
  ↓
observation or failure
  ↓
new prompt / refinement
  ↓
revised implementation
  ↓
accepted behavior
  ↓
SPEC.md baseline
```

This history is preserved because the prompts themselves are part of the
provenance of the resulting system.

For configuration-management purposes, significant prompts can be
treated as **Configuration Items (CIs)**: versionable artifacts that
explain why a requirement, design decision, test, or implementation
change exists.

------------------------------------------------------------------------

## 2. Initial Problem --- Diagnose Intermittent Network Performance

### Prompt / observation

The project began with an unstable network connection, particularly
Wi-Fi at church. Speed tests varied dramatically, including results
around:

``` text
0 Mbps
7 Mbps
14 Mbps
70 Mbps
```

The objective was not merely to obtain another speed-test number. The
user wanted to determine **where the instability was occurring**.

### Requirement that emerged

Create a diagnostic tool capable of repeatedly observing the path
through the network so that behavior at home could be compared with
behavior at church.

### Resulting design direction

Use repeated traceroute measurements rather than relying only on
throughput testing.

------------------------------------------------------------------------

## 3. Home Baseline

A home traceroute to `1.1.1.1` produced a healthy baseline with a local
router followed by Verizon and Cloudflare infrastructure.

Representative observations included:

``` text
Hop 1: 192.168.0.1
Hop 2: Verizon
Intermediate hops: * * *
Destination: 1.1.1.1
```

The final destination response was only several milliseconds.

### Important observation

Intermediate `*` responses did **not** necessarily mean packet loss or a
broken route.

This became an important semantic rule later in the project:

> A nonresponding traceroute hop must remain distinguishable from
> measured packet loss.

------------------------------------------------------------------------

## 4. First Visualization Requirement

### Prompt / requirement

The user wanted repeated traceroutes represented as horizontal bars.

The key requirement was:

> **The length of the bar should represent latency.**

The bar should also be divided into differently colored sections
representing the hops or network portions traversed.

### Accepted visual principle

``` text
short bar = lower latency
long bar  = greater latency
```

Hop colors should remain consistent so that changes can be visually
compared across repeated measurements.

### Implementation direction

A stacked horizontal latency visualization was adopted.

------------------------------------------------------------------------

## 5. Avoid Additional Package Dependencies

### Development issue

An early possibility involved `mtr`, but installing it through Homebrew
was problematic on the Intel Mac being used for testing.

### Requirement / decision

Avoid depending on Homebrew or extra packages.

### Result

The project moved toward a Python implementation using standard macOS
commands:

``` text
traceroute
ping
open
```

and Python's standard library.

------------------------------------------------------------------------

## 6. Python Environment Discovery

### Observation

The Mac had multiple Python situations:

-   `python` invoked an old Python 2 environment;
-   a non-system `python3` path pointed at a broken Python 3.6
    installation;
-   `/usr/bin/python3` initially required Apple's Command Line Tools.

### Resolution

Apple Command Line Tools were installed.

The working interpreter became:

``` bash
/usr/bin/python3
```

with Python 3.9.6.

### Accepted operating procedure

Compile check:

``` bash
/usr/bin/python3 -m py_compile latency_trace.py
```

Run:

``` bash
/usr/bin/python3 latency_trace.py
```

No output from `py_compile` means the syntax check passed.

------------------------------------------------------------------------

## 7. Repeated Measurement and CSV Logging

### Requirement

The diagnostic needed to run continuously rather than produce a single
traceroute.

### Result

The program repeatedly:

1.  runs traceroute;
2.  parses hop data;
3.  records the measurement;
4.  updates the visualization; and
5.  waits before beginning another cycle.

The configured pause became:

``` text
10 seconds
```

CSV logging was added so that observations would survive after the
graphical session ended.

------------------------------------------------------------------------

## 8. Timestamped Output Files

### Problem

Repeated runs should not overwrite earlier diagnostic results.

### Requirement

Automatically date/time stamp each run.

### Result

Each execution creates:

``` text
latency_trace_YYYY-MM-DD_HHMMSS.csv
latency_trace_YYYY-MM-DD_HHMMSS.html
```

This turned each run into a separate diagnostic artifact.

------------------------------------------------------------------------

## 9. HTML Rather Than a GUI-Only Display

The visualization evolved into a generated HTML report that could be
viewed in Chrome.

### Accepted behavior

The Python process generates the report and opens it using macOS:

``` text
open -a "Google Chrome" file://...
```

The HTML refreshes periodically so that newly collected measurements
appear without manually reopening the file.

The report is explicitly flushed to disk after updates.

------------------------------------------------------------------------

## 10. Local Versus End-to-End Packet Loss

### Prompt / reasoning

Traceroute alone could not distinguish a weak local Wi-Fi connection
from loss farther out on the Internet.

### Requirement

Measure packet loss independently in two places.

### Result

For every successful traceroute cycle:

``` text
10 pings → Hop 1
10 pings → target
```

The report labels these:

``` text
Wi-Fi loss
Net loss
```

with definitions:

``` text
Wi-Fi loss = packet loss between this computer and Hop 1.
Net loss = packet loss between this computer and TARGET.
```

### Important semantic decision

A traceroute `*` is not treated as packet loss.

------------------------------------------------------------------------

## 11. Bars Must Touch Vertically

### Visual refinement

The user wanted the repeated measurement bars to form a compact visual
history rather than appear as widely separated rows.

### Result

Bar/row heights were tightened so successive bars touch vertically.

This made latency changes easier to see as a temporal pattern.

------------------------------------------------------------------------

## 12. Hop Legend

### Requirement

The user needed to know what each color represented.

### Result

A `Hop colors:` legend was added below the graph.

Each hop appears on its own line with a colored square.

Hop 1 is explicitly identified as:

``` text
Hop 1 (Wi-Fi/router)
```

Nonresponding hops remain present:

``` text
Hop 3: No response (*)
```

------------------------------------------------------------------------

## 13. Color Distinguishability

### Observation

Some hop colors were difficult to distinguish, particularly Hop 5 versus
Hop 6.

### Requirement

Improve visual separation.

### Result

Hop 6 became a lighter cyan/blue:

``` text
#00A6D6
```

The final palette was retained consistently across the graph and legend.

------------------------------------------------------------------------

## 14. FQDN Identification

### Prompt

IP addresses alone were not sufficiently informative.

The user wanted hop names where they could be determined.

### Requirement

Perform reverse DNS and show a **Fully Qualified Domain Name (FQDN)**
when one exists.

### Result

Reverse DNS was added using:

``` python
socket.gethostbyaddr()
```

Example:

``` text
71.114.105.1
(lo0-100.washdc-vfttp-332.verizon-gni.net)
```

Reverse-DNS results are cached so the same lookup is not repeatedly
performed.

FQDN information was also added to the CSV and mouse-over information.

------------------------------------------------------------------------

## 15. Compact Legend Spacing

### Observation

The hop legend contained more vertical whitespace than the explanatory
text above it.

### Prompt

Tighten the spacing so the hop lines match the compact line spacing of
the surrounding report.

### Result

Legend margins, line height, and colored-square dimensions were reduced.

This became part of the accepted report appearance.

------------------------------------------------------------------------

## 16. Every Responding Hop Must Remain Visible

### Problem discovered

Traceroute RTTs do not necessarily increase monotonically.

For example, an intermediate router can report a larger RTT than a later
router.

If a stacked bar simply uses positive increases, a responding hop whose
RTT is below the current accumulated maximum can disappear from the
graph.

### Initial experiment

A very thin one-pixel representation was considered.

### User observation

One pixel was too difficult to see on a modern display.

### Revised requirement

Use a pipe character:

``` text
|
```

and place it at the end of the preceding accumulated bar.

### Result

A responding hop that adds no width to the monotonic visualization is
shown as a colored `|`.

The report wording became:

``` text
Colored | = latency delay = 0.
```

### Important limitation

The marker is a visualization convention. It does not prove that the
actual network hop took literally zero milliseconds.

------------------------------------------------------------------------

## 17. Nonresponding Hops Must Be Visible Without Inventing Latency

### Requirement

A hop returning `* * *` must remain visible in the graph but must not be
assigned artificial latency.

### Result

A colored:

``` text
*
```

is placed at the current accumulated latency position.

It contributes no bar width.

If multiple nonresponding hops occupy the same position, their markers
are offset so they remain visible.

------------------------------------------------------------------------

## 18. Recognition of the Traceroute Decomposition Limitation

### Observation

An intermediate router might report, for example, 40+ ms while the final
destination reports only approximately 8 ms.

### Engineering conclusion

Traceroute RTT values cannot be interpreted as literal latency between
adjacent routers.

The graph therefore uses a **monotonic latency envelope** for
visualization.

### Resulting specification rule

The displayed total is the maximum responding RTT represented by the
accumulated envelope, not necessarily the final destination RTT.

This limitation was explicitly preserved in the final `SPEC.md` rather
than hidden.

------------------------------------------------------------------------

## 19. Add User Identity to the Report

### Requirement

The report should identify its author/user.

### Result

Directly under the title:

``` text
Patrick Stingley (Covertchannel@yahoo.com)
```

The line uses normal font weight.

------------------------------------------------------------------------

## 20. Wording Refinements

Several report labels were refined during inspection.

Accepted wording included:

``` text
Target: TARGET
Bar length = measured traceroute latency.
Colored sections = traceroute hops.
Colored | = latency delay = 0.
Colored * = hop did not respond.
Run started: ...
Wi-Fi loss = packet loss between this computer and Hop 1.
Net loss = packet loss between this computer and TARGET.
```

The wording changed from references to "this Mac" to the more general:

``` text
this computer
```

Unnecessary explanatory lines and blank spacing were removed to keep the
report compact.

------------------------------------------------------------------------

## 21. User-Selectable Target

### Initial state

The target was fixed in the source as:

``` text
1.1.1.1
```

### Prompt

Could the destination be changed to something such as:

``` text
lds.org
```

### First design idea

An HTML text box and button were considered.

### Architectural consequence

A browser form that directly changes a running Python process would
normally require browser-to-process communication, such as a local web
server.

### User decision

Do **not** start a web server.

Keep the architecture as a simple Python/HTML program.

### Final interaction design

At Python startup:

``` text
Network Latency Tracer
----------------------
Enter to trace to 1.1.1.1 or provide alternate URL:
```

Pressing Enter uses:

``` text
1.1.1.1
```

The user may instead enter a hostname or URL.

This is an important example of a requirement changing after the
architectural implications became visible.

------------------------------------------------------------------------

## 22. Traceroute Failure Against Web Sites

### Observation

Tests against several web destinations showed that many did not produce
a usable traceroute. One example that did work was `www.mci.com`.

A test against `lds.org` produced a traceroute timeout.

### User hypothesis

The remote networks appeared to be blocking or filtering the traffic
used by traceroute.

### Requirement

A failed traceroute should appear **in the HTML report where the bar
would have appeared**, rather than merely producing a terminal error.

------------------------------------------------------------------------

## 23. HTTPS Fallback

### Prompt

When traceroute fails:

1.  record the measurement timestamp;
2.  perform an HTTPS GET request;
3.  if a web server responds, record that fact in the HTML.

### Initial display concept

The first version displayed the wall-clock response time.

Example concept:

``` text
Traceroute failed — HTML response: 17:06:37.918
```

### User correction

The desired value was not the time of day.

The user wanted the **elapsed time between sending the HTTPS request and
receiving the response**.

### Final accepted form

``` text
Traceroute failed — HTML response: 633.8 ms
```

### Additional presentation requirement

The fallback line must **not be bold**.

### Implementation

Elapsed time is measured with Python's high-resolution monotonic:

``` python
time.perf_counter()
```

A `403`, `404`, or similar HTTP error still counts as an HTML/HTTP
response because it demonstrates that an HTTPS server was reached and
answered.

If no HTTPS response occurs:

``` text
Traceroute failed — No HTML response
```

------------------------------------------------------------------------

## 24. FQDN Was Not Enough

### Observation from the report

Some public hops had no reverse-DNS name.

Examples included addresses in the paths associated with Verizon
Business and Cloudflare.

### Prompt

Because these addresses belong to registered IP networks, show the
registered organization in parentheses when an FQDN is unavailable.

### Requirement hierarchy

The user explicitly accepted:

``` text
FQDN
  ↓ if unavailable
registered organization
  ↓ if unavailable
IP address only
```

------------------------------------------------------------------------

## 25. RDAP Registered-Organization Fallback

### Implementation decision

Use **Registration Data Access Protocol (RDAP)** data for public IP
addresses that lack reverse DNS.

The implementation queries:

``` text
https://rdap.org/ip/IP_ADDRESS
```

and extracts an appropriate registered organization/entity name.

### Examples observed in the accepted report

``` text
Hop 5: 204.148.170.122 (Verizon Business)
Hop 6: 173.245.63.145 (Cloudflare, Inc.)
Hop 7: 173.245.63.112 (Cloudflare, Inc.)
Hop 8: 1.1.1.1 (one.one.one.one)
```

### Important semantic distinction

The registered organization describes registration of the address block.

It does **not** necessarily prove ownership or physical operation of the
individual router.

### Caching

RDAP results are cached during the run.

Private addresses such as `192.168.0.1` are not submitted for RDAP
lookup.

------------------------------------------------------------------------

## 26. CSV Provenance Improvements

As the diagnostic became richer, the CSV schema evolved.

The final baseline keeps FQDN and registered organization as separate
fields because they are different kinds of evidence.

The completed schema is:

``` text
timestamp
target
result_type
hop
address
fqdn
registered_organization
latency_ms
traceroute_response
router_packet_loss_percent
internet_packet_loss_percent
https_elapsed_ms
https_status
```

This preserves enough information to distinguish traceroute results from
HTTPS fallback results and DNS identity from registration identity.

------------------------------------------------------------------------

## 27. Complete Replacement Code as a Working Rule

### User requirement

During iterative development, partial patches became undesirable.

The user established the rule:

> **Always provide the complete replacement program when code changes
> are requested.**

### Rationale in practice

This reduced the chance of:

-   inserting code into the wrong location;
-   missing a related change;
-   creating inconsistent versions; or
-   having to reconstruct the intended program from several snippets.

This became a process requirement for the project, not a runtime
feature.

------------------------------------------------------------------------

## 28. Final Acceptance

After the FQDN/RDAP hierarchy was implemented, the user inspected the
running report and stated:

> **"This is perfect!"**

At that point the running baseline visibly included:

-   repeated traceroute measurements;
-   latency-scaled horizontal bars;
-   consistent hop colors;
-   `*` nonresponse markers;
-   `|` no-additional-width markers;
-   Wi-Fi and Internet packet-loss measurements;
-   compact hop legend;
-   FQDNs where available;
-   registered organizations where FQDNs were unavailable;
-   timestamped CSV/HTML outputs; and
-   the simple Python/local-HTML architecture.

That accepted implementation became the basis for `SPEC.md`.

------------------------------------------------------------------------

## 29. Specification Created After the Working System

### Prompt

After the program was accepted, the user asked to review the prompts and
changes and create:

``` text
SPEC.md
```

### Result

`SPEC.md` was produced from the completed design and the accumulated
decisions.

This is significant because the final specification contains
requirements that were not known at project inception, including:

-   `|` markers;
-   `*` semantics;
-   local versus end-to-end packet loss;
-   startup target selection;
-   rejection of a local web server;
-   HTTPS fallback;
-   elapsed HTTPS response timing;
-   non-bold fallback rows;
-   FQDN identification;
-   RDAP registration fallback;
-   caching;
-   compact legend spacing; and
-   explicit limitations of traceroute latency decomposition.

------------------------------------------------------------------------

## 30. Prompt History as a Configuration-Management Artifact

### Prompt / conclusion

The user then raised the broader engineering question: if the system
specification emerged from the prompt/implementation/test cycle, the
prompts themselves should be preserved as **Configuration Items (CIs)**.

This led to the creation of this file.

### Proposed configuration chain

``` text
Prompt CI
   ↓
Requirement / clarification
   ↓
Design decision
   ↓
Implementation
   ↓
Observed result / test
   ↓
Corrective or refining Prompt CI
   ↓
New implementation baseline
   ↓
SPEC.md
```

This preserves not only **what the system is**, but **why it became that
system**.

------------------------------------------------------------------------

# 31. Condensed Prompt-to-Requirement Traceability

  --------------------------------------------------------------------------------------
  CI                Prompt / observation     Requirement or      Result
                                             decision            
  ----------------- ------------------------ ------------------- -----------------------
  P01               Network speed varies     Diagnose            Repeated path
                    dramatically             location/source of  measurements
                                             instability         

  P02               Need visual comparison   Bar length          Horizontal latency
                                             represents latency  graph

  P03               Need path detail         Different colors    Stacked colored
                                             for hops            segments

  P04               `mtr`/Homebrew           Avoid added         Standard macOS
                    problematic              dependencies        commands + Python

  P05               Need repeated evidence   Continuous sampling Measurement loop

  P06               Preserve results         Log measurements    CSV output

  P07               Don't overwrite prior    Timestamp output    Unique CSV/HTML per run
                    runs                     files               

  P08               Need readable live       Generate browser    Auto-refreshing HTML
                    display                  report              

  P09               Need to distinguish      Ping Hop 1 and      Wi-Fi loss / Net loss
                    Wi-Fi from Internet      target              
                                             independently       

  P10               `*` hops appear on       Do not equate `*`   Separate nonresponse
                    healthy path             with packet loss    semantics

  P11               Need color meaning       Add hop legend      Compact color legend

  P12               Colors difficult to      Improve palette     Hop 6 changed to cyan
                    distinguish                                  

  P13               IP alone not informative Add reverse DNS     FQDN display/cache

  P14               Later RTT can be lower   Keep every          `|` marker
                                             responding hop      
                                             visible             

  P15               One pixel too small      Use visible         Colored `|` at bar end
                                             character           

  P16               Nonresponding hop needs  Show without        Colored `*` marker
                    visibility               invented latency    

  P17               Intermediate RTT can     Don't claim exact   Monotonic-envelope
                    exceed destination RTT   per-link delay      interpretation

  P18               Report should identify   Add author line     Patrick Stingley/email
                    author                                       

  P19               "this Mac" too specific  Generalize wording  "this computer"

  P20               Want arbitrary target    Make target         Startup target prompt
                                             selectable          

  P21               HTML textbox implies     Avoid server        Keep Python + static
                    server                   architecture        HTML

  P22               `lds.org` traceroute     Failure belongs in  Failure row in graph
                    times out                report              area

  P23               Web site may answer      Add                 HTTPS GET
                    despite traceroute       application-layer   
                    failure                  fallback            

  P24               Wall-clock response time Measure request     `HTML response: N ms`
                    isn't desired            duration            

  P25               Failure line too         Don't bold it       Normal-weight failure
                    visually strong                              row

  P26               Some hops lack FQDN      Identify registered RDAP fallback
                                             network             

  P27               Registration is not FQDN Preserve provenance Separate CSV fields

  P28               Repeated DNS/RDAP is     Cache lookups       In-memory caches
                    wasteful                                     

  P29               Patches are              Always supply full  Process rule
                    cumbersome/error-prone   replacement program 

  P30               Final implementation     Establish baseline  `"This is perfect!"`
                    accepted                                     

  P31               Need completed           Capture final       `SPEC.md`
                    specification            system              

  P32               Specification emerged    Preserve prompts as `PROMPT_HISTORY.md`
                    through prompts          engineering         
                                             artifacts           
  --------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 32. Requirements That Could Not Reasonably Have Been Fully Specified at the Beginning

The project history demonstrates several requirements that emerged only
after interacting with real behavior.

### 32.1 Intermediate routers did not respond

This produced the need for `*` semantics.

### 32.2 Hop RTTs were not monotonically increasing

This produced the monotonic envelope and later the `|` marker.

### 32.3 A one-pixel marker was not visually adequate

This could only be judged after seeing it rendered.

### 32.4 Hop colors were insufficiently distinguishable

This emerged from actual visual inspection.

### 32.5 Some destinations filtered traceroute

This produced the HTTPS fallback.

### 32.6 The first HTTPS representation used the wrong notion of "time"

Seeing the report clarified that elapsed duration, rather than
wall-clock response time, was required.

### 32.7 Some hops had reverse DNS and others did not

This produced the RDAP fallback.

### 32.8 An HTML target control changed the architecture

Considering a browser text box exposed the requirement for
browser-to-Python communication. The simpler startup prompt was selected
only after that architectural consequence was understood.

These are examples of requirements discovery through implementation and
observation rather than simple execution of a complete a priori
specification.

------------------------------------------------------------------------

# 33. Configuration-Item Model Suggested by This Project

A future agentic engineering repository could treat the following as
first-class Configuration Items:

``` text
CI-001  Original problem statement
CI-002  Significant user prompts
CI-003  Clarifications and requirement changes
CI-004  Screenshots / observed outputs
CI-005  Test results and failures
CI-006  Design decisions
CI-007  Source-code baselines
CI-008  Generated diagnostic artifacts
CI-009  SPEC.md
CI-010  PROMPT_HISTORY.md
```

A prompt should receive a new CI/version when it materially changes:

-   required behavior;
-   architecture;
-   interfaces;
-   data representation;
-   diagnostics;
-   acceptance criteria; or
-   interpretation of results.

Minor conversational exchanges need not necessarily become independent
CIs.

------------------------------------------------------------------------

# 34. Suggested Traceability Relationship

A mature version of this workflow could explicitly maintain:

``` text
Prompt CI
   ↕
Requirement ID
   ↕
Design decision
   ↕
Source commit
   ↕
Test evidence
   ↕
Specification section
```

For example:

``` text
Prompt CI:
"When traceroute fails, try HTTPS."

        ↓

Requirement:
NET-FAIL-001

        ↓

Implementation:
test_https()

        ↓

Evidence:
lds.org traceroute timeout +
successful HTTPS response

        ↓

SPEC.md:
Section 9 — Traceroute Failure and HTTPS Fallback
```

This makes the human/agent conversation auditable rather than ephemeral.

------------------------------------------------------------------------

# 35. Engineering Lesson Captured by the Project

The project provides a concrete example of a distinction between:

``` text
specification as prophecy
```

and:

``` text
specification as controlled, evolving engineering knowledge
```

An initial specification could have stated the problem, constraints, and
first proposed behavior.

It could not, however, have accurately predicted every requirement that
emerged from:

-   the actual Mac environment;
-   real traceroute behavior;
-   real router response policies;
-   actual visual perception of the graph;
-   actual DNS data;
-   actual IP registration data;
-   remote ICMP/traceroute filtering; and
-   the user's evaluation of intermediate implementations.

The resulting workflow was therefore iterative:

``` text
Specify
   ↓
Build
   ↓
Observe
   ↓
Learn
   ↓
Revise
   ↓
Re-baseline
```

The prompt history is evidence of those transitions.

------------------------------------------------------------------------

# 36. Relationship to SPEC.md

`SPEC.md` answers:

> **What is the accepted Network Latency Tracer baseline?**

`PROMPT_HISTORY.md` answers:

> **How and why did that baseline emerge?**

The two files serve different configuration-management purposes.

`SPEC.md` is the current-state specification.

`PROMPT_HISTORY.md` is the requirements and design provenance.

Together with `latency_trace.py`, they form a stronger engineering
record than any one of the three artifacts alone.

------------------------------------------------------------------------

# 37. Recommended Repository Baseline

``` text
network-latency-tracer/
├── latency_trace.py
├── SPEC.md
├── PROMPT_HISTORY.md
└── README.md
```

If the project is placed under Git, changes to prompts/requirements,
specification, and implementation can be correlated through commits.

A future extension could assign stable IDs to significant Prompt CIs and
reference those IDs in commits and specification sections.

------------------------------------------------------------------------

# 38. Final Project Thesis

The Network Latency Tracer project supports the following engineering
proposition:

> **In an agentic development process, significant prompts are not
> merely transient instructions to a model. They can function as
> requirements, change requests, design decisions, test reactions, and
> acceptance statements. When they materially affect the engineered
> baseline, they are candidates for treatment as Configuration Items.**

The final specification is therefore not separate from the prompt
history.

It is the consolidated baseline that emerged from it.
