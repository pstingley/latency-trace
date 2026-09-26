# Network Latency Tracer --- SPEC.md

**Project:** Network Latency Tracer\
**Author:** Patrick Stingley\
**Status:** Completed baseline\
**Baseline date:** 2026-09-26\
**Primary implementation:** `latency_trace.py`\
**Generated outputs:** timestamped HTML report and CSV data file

## 1. Purpose

Network Latency Tracer is a lightweight macOS network-diagnostic utility
designed to identify intermittent network latency and packet-loss
problems, particularly unstable Wi-Fi behavior.

The program repeatedly traces the path from the local computer to a
selected destination, measures local and end-to-end packet loss, and
presents the observations as a continuously refreshed HTML
visualization.

The tool is intended to distinguish, as far as the available
measurements permit, among:

-   problems between the computer and its local router/Wi-Fi access
    point;
-   latency changes appearing at different traceroute hops;
-   end-to-end packet loss;
-   traceroute/ICMP filtering by remote networks; and
-   a destination that still responds over HTTPS even when traceroute
    cannot complete.

The program deliberately remains a simple local Python/HTML application.
It does **not** require a web server.

## 2. User Experience

The program is started from a terminal:

``` bash
/usr/bin/python3 latency_trace.py
```

At startup it displays:

``` text
Network Latency Tracer
----------------------
Enter to trace to 1.1.1.1 or provide alternate URL:
```

Pressing **Enter** selects the default target `1.1.1.1`.

The user may instead enter a hostname or URL, for example:

``` text
lds.org
```

or:

``` text
https://lds.org/
```

The program normalizes a URL to the hostname required by traceroute.

The selected target is validated with DNS resolution before measurements
begin.

The program creates a new timestamped CSV and HTML file for every run
and automatically opens the HTML report in Google Chrome.

The program runs continuously until the user presses **Control-C**.

## 3. Runtime Environment

The completed baseline was developed for macOS on an Intel Mac.

The required Python interpreter is:

``` bash
/usr/bin/python3
```

The tested interpreter is Python 3.9.6.

Before execution, the program may be syntax-checked with:

``` bash
/usr/bin/python3 -m py_compile latency_trace.py
```

No output from that command indicates that compilation succeeded.

The implementation uses Python standard-library modules and macOS
command-line utilities. It does not require Homebrew, `mtr`, a Python
package installation, or an HTTP server.

External operating-system commands used are:

-   `traceroute`
-   `ping`
-   `open`

The `open` command is used to launch the generated report in Google
Chrome.

## 4. Output Files

Every execution receives its own timestamp.

Output filenames have the form:

``` text
latency_trace_YYYY-MM-DD_HHMMSS.csv
latency_trace_YYYY-MM-DD_HHMMSS.html
```

Example:

``` text
latency_trace_2026-09-26_171806.csv
latency_trace_2026-09-26_171806.html
```

A new run therefore does not overwrite a previous run.

## 5. Measurement Cycle

For each measurement cycle, the program:

1.  records the cycle timestamp;
2.  runs traceroute to the selected target;
3.  parses the responding and nonresponding hops;
4.  resolves useful identifying information for responding hop
    addresses;
5.  measures packet loss to Hop 1;
6.  measures packet loss to the selected destination;
7.  records the result in the CSV;
8.  regenerates the HTML report; and
9.  waits for the configured interval before beginning the next cycle.

The configured pause is:

``` text
INTERVAL_SECONDS = 10
```

This is a pause after a measurement cycle, not a guaranteed ten-second
start-to-start sampling period. Traceroute, DNS/RDAP lookups, and ping
tests themselves consume time.

## 6. Traceroute

Traceroute is executed as:

``` text
traceroute -n -q 3 -w 2 TARGET
```

The `-n` option prevents traceroute itself from performing DNS lookups.

Three probes are requested for each hop.

The program imposes a 60-second overall traceroute timeout.

For each parsed hop, the program records:

-   hop number;
-   first IPv4 address found on the hop line;
-   available traceroute round-trip-time measurements;
-   representative latency; and
-   whether the hop failed to respond.

When multiple latency values are available, the program sorts them and
uses the middle value as the representative hop latency.

A nonresponding hop is represented by `*`.

### 6.1 Traceroute interpretation limitation

Traceroute round-trip times are independent measurements from the
computer to each router. They are **not** measurements of the latency of
the individual physical link between two adjacent routers.

Consequently, a later hop may report a lower round-trip time than an
earlier hop. Routers may also deprioritize or filter
traceroute/ICMP-related traffic.

The visualization therefore must not claim that its colored sections are
exact physical per-link latency measurements.

## 7. Latency Visualization

Each successful measurement is rendered as a horizontal stacked bar.

The design rule is:

> **Long bar = greater measured latency; short bar = lower measured
> latency.**

Each traceroute hop has a consistent color.

The baseline palette is:

  Hop   Color
  ----- ---------------------------
  1     Blue `#4E79A7`
  2     Orange `#F28E2B`
  3     Green `#59A14F`
  4     Red `#E15759`
  5     Purple `#B07AA1`
  6     Light blue/cyan `#00A6D6`
  7     Yellow `#EDC948`
  8     Pink `#FF9DA7`
  9     Brown `#9C755F`
  10    Gray `#BAB0AC`

The palette was selected with visual distinguishability in mind,
including color-vision accessibility.

### 7.1 Monotonic display envelope

The graph maintains an accumulated maximum latency.

If a responding hop has a latency greater than the accumulated maximum,
the additional amount is drawn as that hop's colored section.

Conceptually:

``` text
segment width = hop RTT - accumulated maximum RTT
```

The accumulated maximum is then updated.

The displayed total is therefore the maximum responding traceroute
round-trip time represented by the monotonic envelope. It is **not
necessarily the final destination's RTT**.

### 7.2 Responding hop with no additional displayed latency

If a hop responds but its measured RTT is less than or equal to the
accumulated displayed latency, it must remain visible.

It is shown as a colored:

``` text
|
```

at the right-hand end of the accumulated bar.

The report describes this convention as:

``` text
Colored | = latency delay = 0.
```

This is a **display convention** indicating that the hop adds no width
to the monotonic visualization. It must not be interpreted as proof that
the actual network hop took exactly zero milliseconds.

If multiple such markers occupy the same position, they are offset
horizontally so they remain visible.

### 7.3 Nonresponding hop

A traceroute hop that returns no response is shown with a colored:

``` text
*
```

at the current accumulated latency position.

The star adds no invented latency and does not increase the bar width.

The report describes this as:

``` text
Colored * = hop did not respond.
```

Multiple stars at the same position are offset so they remain
distinguishable.

## 8. Packet-Loss Measurements

Each successful traceroute cycle performs two independent ping tests.

### 8.1 Wi-Fi/local packet loss

The first responding traceroute hop is treated as the local router.

Ten pings are sent to Hop 1.

The HTML report labels this measurement:

``` text
Wi-Fi loss
```

and explains:

``` text
Wi-Fi loss = packet loss between this computer and Hop 1.
```

This is intended to help identify instability on the local
Wi-Fi/local-network path.

### 8.2 End-to-end packet loss

Ten pings are also sent to the selected target.

The HTML report labels this:

``` text
Net loss
```

and explains:

``` text
Net loss = packet loss between this computer and TARGET.
```

A `*` from an intermediate traceroute router is **not** itself counted
as packet loss. Some routers intentionally do not respond to traceroute
probes.

## 9. Traceroute Failure and HTTPS Fallback

A remote site may filter or ignore traceroute traffic while remaining
fully reachable as a web service.

Therefore, failure of traceroute must not automatically be presented as
failure of the destination.

If traceroute fails or returns no usable hop data, the program performs
an HTTPS GET request to:

``` text
https://TARGET/
```

The request uses a 15-second timeout.

Elapsed time is measured with Python's high-resolution monotonic
`perf_counter()`.

The timer starts immediately before the HTTPS request and stops after
the response begins arriving.

If the server returns a normal HTTP response, the HTML measurement row
displays:

``` text
Traceroute failed — HTML response: 633.8 ms
```

The value following `HTML response:` is the **elapsed HTTPS
request/response time**, not a wall-clock timestamp.

This line is displayed in normal font weight, not bold.

HTTP error responses such as `403` or `404` still count as a response
because they demonstrate that an HTTPS server was reached and answered.

If no HTTPS response can be obtained, the report displays:

``` text
Traceroute failed — No HTML response
```

The CSV additionally records the HTTPS status code when available.

## 10. Hop Identification

Responding hops are identified using the following hierarchy:

1.  Fully Qualified Domain Name (FQDN), if reverse DNS succeeds;
2.  registered IP organization, if no FQDN exists;
3.  IP address alone, if neither lookup succeeds.

Examples:

``` text
Hop 2: 71.114.105.1 (lo0-100.washdc-vfttp-332.verizon-gni.net)
Hop 5: 204.148.170.122 (Verizon Business)
Hop 6: 173.245.63.145 (Cloudflare, Inc.)
Hop 8: 1.1.1.1 (one.one.one.one)
```

The parenthetical organization is registration information for the
address block. It should not be interpreted as proof of ownership of the
particular router or device.

### 10.1 Reverse DNS

Reverse DNS is performed with:

``` python
socket.gethostbyaddr()
```

Results, including unsuccessful lookups, are cached for the duration of
the run.

### 10.2 Registration Data Access Protocol

If no FQDN is available for a public IP address, the program performs a
Registration Data Access Protocol (RDAP) lookup.

The lookup uses:

``` text
https://rdap.org/ip/IP_ADDRESS
```

The response is parsed for a useful registered organization/entity name.

RDAP is not attempted for private/local addresses such as the local
`192.168.x.x` router address.

Successful and unsuccessful RDAP results are cached for the duration of
the run.

The lookup hierarchy is therefore:

``` text
FQDN
  ↓ if unavailable
registered organization
  ↓ if unavailable
IP address only
```

## 11. HTML Report

The HTML report is regenerated after each measurement and contains:

``` text
Network Latency Tracer
Patrick Stingley (Covertchannel@yahoo.com)
Target: TARGET
Bar length = measured traceroute latency.
Colored sections = traceroute hops.
Colored | = latency delay = 0.
Colored * = hop did not respond.
Run started: YYYY-MM-DD HH:MM:SS
Wi-Fi loss = packet loss between this computer and Hop 1.
Net loss = packet loss between this computer and TARGET.
If traceroute fails, an HTTPS GET request tests whether a web server responds.
```

The HTML page automatically refreshes every five seconds.

Successful traceroute rows contain:

-   measurement time;
-   latency bar;
-   total displayed latency;
-   Wi-Fi packet loss; and
-   Net packet loss.

Failed traceroute rows place the HTTPS fallback result in the area where
the bar normally appears.

The report is written and explicitly flushed to disk so Chrome receives
the updated content.

## 12. Hop Legend

A `Hop colors:` legend appears beneath the measurements.

Each hop occupies one compact line.

Every hop has a colored square, including a hop that never responded.

Examples:

``` text
Hop 1 (Wi-Fi/router): 192.168.0.1
Hop 2: 71.114.105.1 (lo0-100.washdc-vfttp-332.verizon-gni.net)
Hop 3: No response (*)
Hop 4: No response (*)
Hop 5: 204.148.170.122 (Verizon Business)
Hop 6: 173.245.63.145 (Cloudflare, Inc.)
Hop 7: 173.245.63.207 (Cloudflare, Inc.)
Hop 8: 1.1.1.1 (one.one.one.one)
```

Legend line spacing is intentionally compact and approximately matches
the explanatory text above the graph.

## 13. Mouse-Over Information

Colored latency sections and `|` markers provide browser tooltips.

Where available, the tooltip identifies:

-   hop number;
-   IP address;
-   FQDN or registered organization; and
-   measured traceroute RTT.

A `*` tooltip identifies the hop as having no traceroute response.

## 14. CSV Data

The current CSV schema is:

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

For a normal traceroute result, a record is written for each hop.

For an HTTPS fallback result, a failure/fallback record is written with:

-   timestamp;
-   target;
-   result type;
-   traceroute failure indication;
-   HTTPS elapsed time, if available; and
-   HTTP status, if available.

FQDN and registered organization are deliberately separate fields
because they represent different kinds of information.

## 15. Caching

The application maintains in-memory caches for:

-   reverse-DNS results; and
-   RDAP registered-organization results.

Both successful and unsuccessful lookups are cached.

This prevents repeated external lookup delays for the same hop addresses
during a run.

The cache lasts only for the current program execution.

## 16. Browser Behavior

The report is opened with macOS:

``` text
open -a "Google Chrome" file://ABSOLUTE_HTML_PATH
```

No web server is started.

The browser therefore reads the report directly from the local
filesystem.

The HTML meta-refresh causes Chrome to reload the regenerated report
periodically.

## 17. Console Behavior

During operation, the terminal identifies the target and generated files
and reports each measurement cycle.

A successful cycle produces information conceptually like:

``` text
2026-09-26 17:18:06 - running traceroute to 1.1.1.1 ...
  Measuring packet loss...
  8 hops, 20.6 ms | Wi-Fi loss: 0% | Internet loss: 0% | * hops: 3, 4
```

A traceroute failure produces information conceptually like:

``` text
Traceroute failed.
Trying HTTPS GET...
HTML response: 633.8 ms
```

Control-C terminates the loop cleanly and prints the CSV and HTML
filenames.

## 18. Design Decisions

### 18.1 No `mtr`

An early approach considered `mtr`, but the target Intel Mac/Homebrew
environment created installation problems. The completed design
therefore relies on standard macOS utilities and Python.

### 18.2 No local web server

An interactive browser/server design was considered but rejected in
favor of a simpler architecture:

``` text
Python measurement process
        ↓
local CSV + regenerated HTML
        ↓
Chrome file:// page with automatic refresh
```

This reduces dependencies and makes the utility easy to carry and
execute.

### 18.3 User-selectable target at startup

The original implementation used a fixed `1.1.1.1` target.

The completed design asks for the target when the Python program starts
while retaining `1.1.1.1` as the default.

This provides the desired flexibility without requiring
browser-to-Python communication or a web server.

### 18.4 HTTPS is a fallback, not traceroute data

HTTPS response time is not drawn as if it were a traceroute hop.

It is explicitly identified as an application-layer fallback measurement
after traceroute failure.

### 18.5 Identification does not imply router ownership

Reverse DNS and RDAP registration information are diagnostic labels.

RDAP in particular identifies registration associated with an IP address
block; it does not necessarily identify the owner or operator of the
physical router that answered the traceroute probe.

## 19. Known Limitations

1.  **Traceroute is not per-link telemetry.** Independent hop RTTs
    cannot be subtracted reliably to obtain true router-to-router link
    delay.

2.  **The displayed total is a monotonic-envelope value.** A slow
    response from an intermediate router can make the displayed bar
    longer than the final destination's measured RTT.

3.  **ICMP/traceroute filtering is common.** A `*` does not establish
    packet loss.

4.  **Ping may also be filtered.** Lack of a ping response does not
    necessarily mean application traffic is unavailable.

5.  **HTTPS fallback applies only to HTTPS-capable targets.** A
    reachable non-web host may correctly produce no HTML response.

6.  **HTTPS elapsed time includes more than network propagation.**
    Depending on connection state it can include DNS, TCP connection
    establishment, TLS negotiation, server processing, and the beginning
    of response transfer.

7.  **RDAP information describes registration.** It may not identify the
    organization physically operating a particular router.

8.  **The traceroute parser is intentionally simple.** It parses lines
    beginning with a hop number, selects the first IPv4 address on that
    line, and does not fully model alternate addresses printed on
    continuation lines or load-balanced paths.

9.  **IPv4 visualization is the implemented baseline.** The traceroute
    parser specifically recognizes IPv4 address notation.

10. **Sampling is sequential.** Traceroute, lookups, and pings occur
    sequentially, so the configured ten-second interval is not the
    complete cycle duration.

## 20. Acceptance Criteria

The completed baseline is acceptable when all of the following are true:

-   Running `/usr/bin/python3 latency_trace.py` starts without
    third-party Python dependencies.
-   Pressing Enter at the target prompt selects `1.1.1.1`.
-   A hostname such as `lds.org` can be entered instead.
-   A URL can be normalized to its hostname.
-   Each run creates unique timestamped CSV and HTML files.
-   Chrome opens the generated local HTML report automatically.
-   Successful traceroutes produce horizontally scaled, colored hop
    bars.
-   Longer measured latency produces a longer bar.
-   Nonresponding hops are represented by colored `*` markers without
    invented bar width.
-   Responding hops that do not extend the monotonic envelope are
    represented by colored `|` markers.
-   Hop colors remain consistent within the report.
-   Hop 1 packet loss is shown as Wi-Fi loss.
-   Target packet loss is shown as Net loss.
-   A failed traceroute triggers an HTTPS GET fallback.
-   A successful HTTPS fallback displays elapsed milliseconds, not a
    response timestamp.
-   The HTTPS fallback line is not bold.
-   Reverse DNS names are displayed when available.
-   When reverse DNS is unavailable, the registered organization is
    displayed when RDAP provides one.
-   Private IP addresses are not sent for RDAP registration lookup.
-   DNS and RDAP results are cached.
-   FQDN and registered organization are stored separately in the CSV.
-   The HTML refreshes as measurements accumulate.
-   Control-C stops the program cleanly and preserves the generated
    output files.

## 21. Completed Baseline Architecture

``` text
                 +-------------------------+
                 |   latency_trace.py      |
                 +------------+------------+
                              |
                 Startup target selection
                              |
                              v
                     DNS target validation
                              |
                              v
                    +-------------------+
                    |    traceroute     |
                    +---------+---------+
                              |
                 +------------+-------------+
                 |                          |
             succeeds                    fails
                 |                          |
                 v                          v
          Parse hop RTTs              HTTPS GET
                 |                          |
        +--------+--------+                 |
        |                 |                 |
        v                 v                 v
   Reverse DNS       RDAP fallback     elapsed time
   when possible     when no FQDN      + HTTP status
        |                 |                 |
        +--------+--------+-----------------+
                 |
                 v
          Ping local Hop 1
          Ping target host
                 |
                 v
       +---------+----------+
       |                    |
       v                    v
 Timestamped CSV     Regenerated HTML
                            |
                            v
                   Chrome local file
                   automatic refresh
```

## 22. Baseline Configuration

``` text
Default target:              1.1.1.1
Measurement pause:           10 seconds
Ping count:                  10
Minimum graph scale:         20 ms
Traceroute overall timeout:  60 seconds
HTTPS timeout:               15 seconds
RDAP timeout:                10 seconds
HTML refresh:                5 seconds
```

## 23. Project Result

The completed Network Latency Tracer is a portable diagnostic utility
that combines traceroute visualization, local and end-to-end packet-loss
measurements, reverse-DNS identification, registered-network
identification, and an HTTPS fallback for destinations that do not
permit traceroute.

Its central diagnostic principle is to preserve the distinction between
what was actually measured and what is merely inferred or used for
display:

-   traceroute RTT is reported as traceroute RTT;
-   nonresponses remain nonresponses;
-   the stacked graph is explicitly a visualization rather than exact
    link-delay decomposition;
-   packet loss is measured independently;
-   HTTPS reachability is kept distinct from traceroute reachability;
    and
-   FQDN identity is kept distinct from IP-registration organization.

This document defines the completed 2026-09-26 baseline.
