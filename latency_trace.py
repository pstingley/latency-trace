import subprocess
import re
import csv
import time
import os
import socket
import urllib.request
import urllib.error
import json
import ipaddress
from datetime import datetime


# ============================================================
# 1. CONFIGURATION
# ============================================================

DEFAULT_TARGET = "1.1.1.1"

INTERVAL_SECONDS = 10
PING_COUNT = 10
MIN_SCALE_MS = 20

TRACEROUTE_TIMEOUT_SECONDS = 60
HTTPS_TIMEOUT_SECONDS = 15
RDAP_TIMEOUT_SECONDS = 10

COLORS = [
    "#4E79A7",  # Hop 1 - blue
    "#F28E2B",  # Hop 2 - orange
    "#59A14F",  # Hop 3 - green
    "#E15759",  # Hop 4 - red
    "#B07AA1",  # Hop 5 - purple
    "#00A6D6",  # Hop 6 - light blue
    "#EDC948",  # Hop 7 - yellow
    "#FF9DA7",  # Hop 8 - pink
    "#9C755F",  # Hop 9 - brown
    "#BAB0AC",  # Hop 10 - gray
]

DNS_CACHE = {}

# Cache registered organizations so that the program does not
# repeatedly perform RDAP lookups for the same IP address.
OWNER_CACHE = {}


# ============================================================
# 2. GET TARGET FROM USER
# ============================================================

def get_target():

    entered = input(
        "Enter to trace to 1.1.1.1 or provide alternate URL: "
    ).strip()

    if not entered:
        return DEFAULT_TARGET

    # Allow:
    #
    # https://lds.org/
    #
    # and reduce it to:
    #
    # lds.org

    entered = re.sub(
        r"^[a-zA-Z]+://",
        "",
        entered
    )

    entered = entered.split("/")[0]

    # Remove a port number if supplied.

    if (
        ":" in entered
        and
        entered.count(":") == 1
    ):

        possible_host, possible_port = (
            entered.rsplit(":", 1)
        )

        if possible_port.isdigit():
            entered = possible_host

    return entered


# ============================================================
# 3. VALIDATE TARGET
# ============================================================

def validate_target(target):

    try:

        socket.getaddrinfo(
            target,
            None
        )

        return True

    except socket.gaierror:

        return False


# ============================================================
# 4. REVERSE DNS LOOKUP
# ============================================================

def get_fqdn(address):

    if not address or address == "*":
        return None

    if address in DNS_CACHE:
        return DNS_CACHE[address]

    try:

        hostname = socket.gethostbyaddr(
            address
        )[0].rstrip(".")

        if hostname == address:
            hostname = None

        DNS_CACHE[address] = hostname

        return hostname

    except (
        socket.herror,
        socket.gaierror,
        OSError
    ):

        DNS_CACHE[address] = None

        return None


# ============================================================
# 5. CHECK WHETHER IP IS PUBLIC
# ============================================================

def is_public_ip(address):

    try:

        ip = ipaddress.ip_address(
            address
        )

        return ip.is_global

    except ValueError:

        return False


# ============================================================
# 6. EXTRACT ORGANIZATION FROM RDAP ENTITY
# ============================================================

def extract_entity_name(entity):

    # --------------------------------------------------------
    # RDAP entities commonly contain a jCard.
    #
    # We look for:
    #
    # fn   = formatted name
    # org  = organization
    #
    # and prefer organization when available.
    # --------------------------------------------------------

    vcard = entity.get(
        "vcardArray"
    )

    if not vcard:
        return None

    if (
        not isinstance(vcard, list)
        or
        len(vcard) < 2
    ):
        return None

    properties = vcard[1]

    organization = None
    formatted_name = None

    for item in properties:

        if (
            not isinstance(item, list)
            or
            len(item) < 4
        ):
            continue

        property_name = item[0]
        property_value = item[3]

        if property_name == "org":

            if isinstance(
                property_value,
                list
            ):

                organization = " ".join(
                    str(x)
                    for x in property_value
                    if x
                )

            else:

                organization = str(
                    property_value
                )

        elif property_name == "fn":

            formatted_name = str(
                property_value
            )

    if organization:
        return organization.strip()

    if formatted_name:
        return formatted_name.strip()

    return None


# ============================================================
# 7. FIND BEST REGISTERED ORGANIZATION IN RDAP DATA
# ============================================================

def extract_registered_organization(data):

    entities = data.get(
        "entities",
        []
    )

    # --------------------------------------------------------
    # Prefer entities whose roles suggest that they represent
    # the registered organization rather than an abuse,
    # technical, or administrative contact.
    # --------------------------------------------------------

    preferred_roles = [
        "registrant",
        "registrar"
    ]

    for preferred_role in preferred_roles:

        for entity in entities:

            roles = entity.get(
                "roles",
                []
            )

            if preferred_role in roles:

                name = extract_entity_name(
                    entity
                )

                if name:
                    return name


    # --------------------------------------------------------
    # If no explicitly identified registrant was available,
    # try any entity containing an organization/name.
    # --------------------------------------------------------

    for entity in entities:

        name = extract_entity_name(
            entity
        )

        if name:
            return name


    # --------------------------------------------------------
    # Some RDAP servers put a useful network name directly
    # in the network object.
    # --------------------------------------------------------

    network_name = data.get(
        "name"
    )

    if network_name:

        network_name = str(
            network_name
        ).strip()

        if network_name:
            return network_name


    # --------------------------------------------------------
    # Handle is a final fallback.
    # --------------------------------------------------------

    handle = data.get(
        "handle"
    )

    if handle:

        handle = str(
            handle
        ).strip()

        if handle:
            return handle

    return None


# ============================================================
# 8. REGISTERED IP ORGANIZATION LOOKUP
# ============================================================

def get_registered_organization(address):

    if not address or address == "*":
        return None

    if address in OWNER_CACHE:
        return OWNER_CACHE[address]

    # --------------------------------------------------------
    # Don't query RDAP for private/local addresses such as:
    #
    # 192.168.x.x
    # 10.x.x.x
    # 172.16.x.x - 172.31.x.x
    # --------------------------------------------------------

    if not is_public_ip(
        address
    ):

        OWNER_CACHE[address] = None

        return None


    # --------------------------------------------------------
    # rdap.org provides an RDAP bootstrap endpoint.
    #
    # It redirects the request to the appropriate Regional
    # Internet Registry for the IP address.
    # --------------------------------------------------------

    url = (
        "https://rdap.org/ip/"
        + address
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Network-Latency-Tracer/1.0",
            "Accept":
                "application/rdap+json, "
                "application/json"
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=RDAP_TIMEOUT_SECONDS
        ) as response:

            raw = response.read()

            data = json.loads(
                raw.decode(
                    "utf-8",
                    errors="replace"
                )
            )

            organization = (
                extract_registered_organization(
                    data
                )
            )

            OWNER_CACHE[address] = (
                organization
            )

            return organization

    except Exception:

        OWNER_CACHE[address] = None

        return None


# ============================================================
# 9. FORMAT ADDRESS
#
# Priority:
#
# 1. FQDN
# 2. Registered organization
# 3. IP address alone
# ============================================================

def format_address(address):

    if not address or address == "*":
        return "No response (*)"

    fqdn = get_fqdn(
        address
    )

    if fqdn:

        return "%s (%s)" % (
            address,
            fqdn
        )

    organization = (
        get_registered_organization(
            address
        )
    )

    if organization:

        return "%s (%s)" % (
            address,
            organization
        )

    return address


# ============================================================
# 10. OPEN GRAPH IN CHROME
# ============================================================

def open_in_chrome(filename):

    full_path = os.path.abspath(
        filename
    )

    try:

        subprocess.run([
            "open",
            "-a",
            "Google Chrome",
            "file://" + full_path
        ])

    except Exception as e:

        print(
            "Could not open Chrome:",
            e
        )

        print(
            "Open manually:",
            full_path
        )


# ============================================================
# 11. RUN TRACEROUTE
# ============================================================

def run_traceroute(target):

    try:

        result = subprocess.run(
            [
                "traceroute",
                "-n",
                "-q", "3",
                "-w", "2",
                target
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=TRACEROUTE_TIMEOUT_SECONDS
        )

        return {
            "success": True,
            "text": result.stdout,
            "reason": ""
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "text": "",
            "reason": (
                "Traceroute timed out after %d seconds"
                % TRACEROUTE_TIMEOUT_SECONDS
            )
        }

    except Exception as e:

        return {
            "success": False,
            "text": "",
            "reason":
                "Traceroute failed: %s"
                % e
        }


# ============================================================
# 12. HTTPS FALLBACK TEST
# ============================================================

def test_https(target):

    url = (
        "https://"
        + target
        + "/"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Network-Latency-Tracer/1.0"
        },
        method="GET"
    )

    start = time.perf_counter()

    try:

        with urllib.request.urlopen(
            request,
            timeout=HTTPS_TIMEOUT_SECONDS
        ) as response:

            # Read one byte so that response data has actually
            # begun arriving.

            response.read(1)

            elapsed_ms = (
                time.perf_counter()
                - start
            ) * 1000.0

            return {
                "responded": True,
                "elapsed_ms":
                    elapsed_ms,
                "status":
                    response.getcode()
            }


    # --------------------------------------------------------
    # 403, 404, etc. still prove that an HTTPS server
    # responded.
    # --------------------------------------------------------

    except urllib.error.HTTPError as e:

        elapsed_ms = (
            time.perf_counter()
            - start
        ) * 1000.0

        return {
            "responded": True,
            "elapsed_ms":
                elapsed_ms,
            "status":
                e.code
        }

    except Exception:

        return {
            "responded": False,
            "elapsed_ms": None,
            "status": None
        }


# ============================================================
# 13. PARSE TRACEROUTE
# ============================================================

def parse_traceroute(text):

    hops = []

    for line in text.splitlines():

        match = re.match(
            r"\s*(\d+)\s+(.*)",
            line
        )

        if not match:
            continue

        hop_number = int(
            match.group(1)
        )

        remainder = match.group(2)

        ip_match = re.search(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            remainder
        )

        if ip_match:

            address = (
                ip_match.group(0)
            )

        else:

            address = "*"

        times = re.findall(
            r"([\d.]+)\s*ms",
            remainder
        )

        if times:

            values = sorted(
                float(x)
                for x in times
            )

            latency = values[
                len(values) // 2
            ]

        else:

            latency = None

        hops.append({
            "hop":
                hop_number,
            "address":
                address,
            "latency":
                latency,
            "no_response":
                latency is None
        })

    return hops


# ============================================================
# 14. CALCULATE DISPLAY SEGMENTS
# ============================================================

def calculate_segments(hops):

    segments = []

    accumulated_latency = 0.0

    for hop in hops:

        latency = hop[
            "latency"
        ]

        if latency is None:

            segments.append({
                "hop":
                    hop["hop"],
                "address":
                    hop["address"],
                "latency":
                    None,
                "segment":
                    0.0,
                "no_response":
                    True,
                "zero_delay":
                    False,
                "marker_position":
                    accumulated_latency
            })

            continue

        if latency > accumulated_latency:

            segment_width = (
                latency
                - accumulated_latency
            )

            accumulated_latency = (
                latency
            )

            segments.append({
                "hop":
                    hop["hop"],
                "address":
                    hop["address"],
                "latency":
                    latency,
                "segment":
                    segment_width,
                "no_response":
                    False,
                "zero_delay":
                    False,
                "marker_position":
                    accumulated_latency
            })

        else:

            segments.append({
                "hop":
                    hop["hop"],
                "address":
                    hop["address"],
                "latency":
                    latency,
                "segment":
                    0.0,
                "no_response":
                    False,
                "zero_delay":
                    True,
                "marker_position":
                    accumulated_latency
            })

    return segments


# ============================================================
# 15. MEASURE PACKET LOSS
# ============================================================

def measure_packet_loss(address):

    if not address or address == "*":
        return None

    try:

        result = subprocess.run(
            [
                "ping",
                "-c",
                str(PING_COUNT),
                "-W",
                "1000",
                address
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=20
        )

        output = (
            result.stdout
            + result.stderr
        )

        match = re.search(
            r"([\d.]+)% packet loss",
            output
        )

        if match:

            return float(
                match.group(1)
            )

    except Exception as e:

        print(
            "Ping error for",
            address,
            ":",
            e
        )

    return None


# ============================================================
# 16. PACKET LOSS DISPLAY
# ============================================================

def loss_text(value):

    if value is None:
        return "N/A"

    return "%.0f%%" % value


def loss_class(value):

    if value is None:
        return "loss-unknown"

    if value == 0:
        return "loss-good"

    if value < 10:
        return "loss-warning"

    return "loss-bad"


# ============================================================
# 17. CSV HEADER
# ============================================================

def write_csv_header(writer):

    writer.writerow([
        "timestamp",
        "target",
        "result_type",
        "hop",
        "address",
        "fqdn",
        "registered_organization",
        "latency_ms",
        "traceroute_response",
        "router_packet_loss_percent",
        "internet_packet_loss_percent",
        "https_elapsed_ms",
        "https_status"
    ])


# ============================================================
# 18. SAVE SUCCESSFUL TRACEROUTE TO CSV
# ============================================================

def save_csv(
    csv_file,
    timestamp,
    target,
    hops,
    router_loss,
    internet_loss
):

    new_file = not os.path.exists(
        csv_file
    )

    with open(
        csv_file,
        "a",
        newline=""
    ) as f:

        writer = csv.writer(
            f
        )

        if new_file:

            write_csv_header(
                writer
            )

        for hop in hops:

            fqdn = None
            organization = None

            if hop["address"] != "*":

                fqdn = get_fqdn(
                    hop["address"]
                )

                # Only use registered organization as the
                # fallback when no FQDN exists.

                if not fqdn:

                    organization = (
                        get_registered_organization(
                            hop["address"]
                        )
                    )

            writer.writerow([
                timestamp,
                target,
                "traceroute",
                hop["hop"],
                hop["address"],
                fqdn if fqdn else "",
                (
                    organization
                    if organization
                    else ""
                ),
                (
                    ""
                    if hop["latency"] is None
                    else hop["latency"]
                ),
                (
                    "*"
                    if hop["no_response"]
                    else "response"
                ),
                (
                    ""
                    if router_loss is None
                    else router_loss
                ),
                (
                    ""
                    if internet_loss is None
                    else internet_loss
                ),
                "",
                ""
            ])

        f.flush()

        try:

            os.fsync(
                f.fileno()
            )

        except OSError:

            pass


# ============================================================
# 19. SAVE FAILED TRACEROUTE / HTTPS FALLBACK TO CSV
# ============================================================

def save_failure_csv(
    csv_file,
    timestamp,
    target,
    https_result
):

    new_file = not os.path.exists(
        csv_file
    )

    with open(
        csv_file,
        "a",
        newline=""
    ) as f:

        writer = csv.writer(
            f
        )

        if new_file:

            write_csv_header(
                writer
            )

        writer.writerow([
            timestamp,
            target,
            "https_fallback",
            "",
            "",
            "",
            "",
            "",
            "traceroute_failed",
            "",
            "",
            (
                "%.1f"
                % https_result["elapsed_ms"]
                if https_result["responded"]
                else ""
            ),
            (
                https_result["status"]
                if https_result["responded"]
                else ""
            )
        ])

        f.flush()

        try:

            os.fsync(
                f.fileno()
            )

        except OSError:

            pass


# ============================================================
# 20. WRITE HTML
# ============================================================

def write_html(
    rows,
    target,
    run_start,
    html_file
):

    largest = MIN_SCALE_MS

    for row in rows:

        if row["type"] == "trace":

            largest = max(
                largest,
                row["total"]
            )

    scale_max = (
        largest * 1.10
    )

    html = []

    html.append("""<!DOCTYPE html>
<html>

<head>

<meta charset="utf-8">
<meta http-equiv="refresh" content="5">

<title>Network Latency Tracer</title>

<style>

body {
    font-family: Arial, sans-serif;
    margin: 25px;
    background: white;
    color: #222;
}

h1 {
    font-size: 30px;
    line-height: 31px;
    margin: 0;
    padding: 0;
}

.author {
    font-size: 16px;
    line-height: 17px;
    margin: 0;
    padding: 0;
}

.info {
    font-size: 15px;
    line-height: 16px;
    margin: 0;
    padding: 0;
}

.run-info {
    font-family: monospace;
    font-size: 13px;
    line-height: 14px;
    margin: 0;
    padding: 0;
}


/* =========================================================
   GRAPH
   ========================================================= */

.graph {
    width: 96%;
    min-width: 900px;
    margin: 0;
    padding: 0;
}

.header-row {
    display: flex;
    align-items: flex-end;
    height: 22px;
    font-size: 12px;
    color: #555;
}

.header-time {
    width: 90px;
    flex-shrink: 0;
}

.axis {
    flex: 1;
    height: 20px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}

.header-total {
    width: 85px;
    flex-shrink: 0;
    padding-left: 8px;
}

.packet-loss-heading {
    width: 235px;
    flex-shrink: 0;
    font-family: monospace;
    font-size: 13px;
    font-weight: bold;
}


/* =========================================================
   MEASUREMENT ROWS
   ========================================================= */

.row {
    display: flex;
    align-items: center;
    height: 20px;
}

.time {
    width: 90px;
    flex-shrink: 0;
    font-family: monospace;
    font-size: 13px;
}

.bar-area {
    position: relative;
    flex: 1;
    height: 20px;
    overflow: visible;

    background:
        repeating-linear-gradient(
            to right,
            #eeeeee 0,
            #eeeeee 1px,
            transparent 1px,
            transparent 10%
        );
}

.bar {
    display: flex;
    height: 20px;
}

.segment {
    height: 20px;
    flex-shrink: 0;
}


/* =========================================================
   TRACEROUTE FAILURE / HTTPS FALLBACK
   ========================================================= */

.failure-area {
    position: relative;
    flex: 1;
    height: 20px;
    line-height: 20px;
    font-family: monospace;
    font-size: 13px;
    font-weight: normal;
    white-space: nowrap;
}

.failure-text {
    display: inline-block;
    padding-left: 4px;
    font-weight: normal;
}


/* =========================================================
   ZERO-DELAY MARKER
   ========================================================= */

.response-marker {
    position: absolute;
    top: -4px;

    font-family: Arial, sans-serif;
    font-size: 25px;
    line-height: 25px;
    font-weight: bold;

    z-index: 200;

    text-shadow:
        0 0 2px white,
        0 0 2px white;
}


/* =========================================================
   NONRESPONDING HOP
   ========================================================= */

.star-marker {
    position: absolute;
    top: -2px;

    transform:
        translateX(-50%);

    font-family: Arial, sans-serif;
    font-size: 22px;
    line-height: 20px;
    font-weight: bold;

    z-index: 300;

    text-shadow:
        0 0 2px white,
        0 0 2px white;
}


/* =========================================================
   LATENCY AND PACKET LOSS
   ========================================================= */

.total {
    width: 85px;
    flex-shrink: 0;
    padding-left: 8px;
    font-family: monospace;
    font-size: 13px;
}

.loss {
    width: 235px;
    flex-shrink: 0;
    font-family: monospace;
    font-size: 13px;
    white-space: nowrap;
}

.loss-good {
    font-weight: normal;
}

.loss-warning {
    font-weight: bold;
    text-decoration: underline;
}

.loss-bad {
    font-weight: bold;
    border: 2px solid #222;
    padding: 1px 3px;
}

.loss-unknown {
    font-style: italic;
}


/* =========================================================
   HOP LEGEND
   ========================================================= */

.legend {
    margin-top: 14px;
    font-size: 15px;
    line-height: 16px;
}

.legend-title {
    margin: 0;
    padding: 0;
    line-height: 16px;
}

.legend-item {
    display: block;
    margin: 0;
    padding: 0;
    line-height: 16px;
    white-space: nowrap;
}

.color-box {
    display: inline-block;
    width: 13px;
    height: 13px;
    margin-right: 7px;
    vertical-align: -1px;
    border: 1px solid #555;
}

</style>

</head>

<body>
""")


    # ========================================================
    # HEADING
    # ========================================================

    html.append(
        "<h1>Network Latency Tracer</h1>"
    )

    html.append(
        '<div class="author">'
        'Patrick Stingley '
        '(Covertchannel@yahoo.com)'
        '</div>'
    )

    html.append(
        '<div class="info">'
        'Target: %s<br>'
        'Bar length = measured traceroute latency.<br>'
        'Colored sections = traceroute hops.<br>'
        'Colored | = latency delay = 0.<br>'
        'Colored * = hop did not respond.'
        '</div>'
        % target
    )

    html.append(
        '<div class="run-info">'
        'Run started: %s<br>'
        'Wi-Fi loss = packet loss between '
        'this computer and Hop 1.<br>'
        'Net loss = packet loss between '
        'this computer and %s.<br>'
        'If traceroute fails, an HTTPS GET request '
        'tests whether a web server responds.'
        '</div>'
        % (
            run_start.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            target
        )
    )


    # ========================================================
    # GRAPH
    # ========================================================

    html.append(
        '<div class="graph">'
    )


    # ========================================================
    # SCALE HEADER
    # ========================================================

    html.append(
        '<div class="header-row">'
    )

    html.append(
        '<div class="header-time"></div>'
    )

    html.append(
        '<div class="axis">'
    )

    for i in range(11):

        value = (
            scale_max
            * i
            / 10.0
        )

        html.append(
            "<span>%.0f</span>"
            % value
        )

    html.append(
        "</div>"
    )

    html.append(
        '<div class="header-total"></div>'
    )

    html.append(
        '<div class="packet-loss-heading">'
        'Packet Loss'
        '</div>'
    )

    html.append(
        "</div>"
    )


    # ========================================================
    # MEASUREMENT ROWS
    # ========================================================

    for row in rows:

        html.append(
            '<div class="row">'
        )

        html.append(
            '<div class="time">'
            '%s'
            '</div>'
            % row["time"]
        )


        # ====================================================
        # FAILED TRACEROUTE
        # ====================================================

        if row["type"] == "failure":

            https_result = row[
                "https_result"
            ]

            if https_result["responded"]:

                failure_text = (
                    "Traceroute failed — "
                    "HTML response: %.1f ms"
                    % https_result["elapsed_ms"]
                )

            else:

                failure_text = (
                    "Traceroute failed — "
                    "No HTML response"
                )

            html.append(
                '<div class="failure-area">'
                '<span class="failure-text">'
                '%s'
                '</span>'
                '</div>'
                % failure_text
            )

            html.append(
                '<div class="total"></div>'
            )

            html.append(
                '<div class="loss"></div>'
            )

            html.append(
                "</div>"
            )

            continue


        # ====================================================
        # SUCCESSFUL TRACEROUTE
        # ====================================================

        html.append(
            '<div class="bar-area">'
        )

        html.append(
            '<div class="bar">'
        )


        # ----------------------------------------------------
        # NORMAL COLORED SEGMENTS
        # ----------------------------------------------------

        for segment in row["segments"]:

            if segment["no_response"]:
                continue

            if segment["zero_delay"]:
                continue

            if segment["segment"] <= 0:
                continue

            percent = (
                segment["segment"]
                / scale_max
                * 100.0
            )

            color = COLORS[
                (
                    segment["hop"] - 1
                )
                % len(COLORS)
            ]

            address_text = format_address(
                segment["address"]
            )

            tooltip = (
                "Hop %d | %s | "
                "%.1f ms traceroute RTT"
                % (
                    segment["hop"],
                    address_text,
                    segment["latency"]
                )
            )

            html.append(
                '<div '
                'class="segment" '
                'style="'
                'width: %.6f%%; '
                'background: %s;" '
                'title="%s">'
                '</div>'
                % (
                    percent,
                    color,
                    tooltip
                )
            )

        html.append(
            "</div>"
        )


        # ----------------------------------------------------
        # ZERO-DELAY | MARKERS
        # ----------------------------------------------------

        marker_counts = {}

        for segment in row["segments"]:

            if segment["no_response"]:
                continue

            if not segment["zero_delay"]:
                continue

            marker_position = (
                segment["marker_position"]
            )

            marker_percent = (
                marker_position
                / scale_max
                * 100.0
            )

            marker_percent = max(
                0.0,
                min(
                    99.0,
                    marker_percent
                )
            )

            marker_key = round(
                marker_position,
                3
            )

            marker_number = (
                marker_counts.get(
                    marker_key,
                    0
                )
            )

            marker_counts[
                marker_key
            ] = marker_number + 1

            pixel_offset = (
                marker_number * 6
            )

            color = COLORS[
                (
                    segment["hop"] - 1
                )
                % len(COLORS)
            ]

            address_text = format_address(
                segment["address"]
            )

            tooltip = (
                "Hop %d | %s | "
                "%.1f ms traceroute RTT | "
                "latency delay = 0"
                % (
                    segment["hop"],
                    address_text,
                    segment["latency"]
                )
            )

            html.append(
                '<span '
                'class="response-marker" '
                'style="'
                'left: calc(%.6f%% + %dpx); '
                'color: %s;" '
                'title="%s">'
                '|'
                '</span>'
                % (
                    marker_percent,
                    pixel_offset,
                    color,
                    tooltip
                )
            )


        # ----------------------------------------------------
        # NONRESPONDING * MARKERS
        # ----------------------------------------------------

        star_counts = {}

        for segment in row["segments"]:

            if not segment["no_response"]:
                continue

            marker_position = (
                segment["marker_position"]
            )

            marker_percent = (
                marker_position
                / scale_max
                * 100.0
            )

            marker_percent = max(
                0.8,
                min(
                    99.0,
                    marker_percent
                )
            )

            marker_key = round(
                marker_position,
                3
            )

            star_number = (
                star_counts.get(
                    marker_key,
                    0
                )
            )

            star_counts[
                marker_key
            ] = star_number + 1

            star_offset = (
                star_number * 10
            )

            color = COLORS[
                (
                    segment["hop"] - 1
                )
                % len(COLORS)
            ]

            tooltip = (
                "Hop %d | "
                "no traceroute response (*)"
                % segment["hop"]
            )

            html.append(
                '<span '
                'class="star-marker" '
                'style="'
                'left: calc(%.6f%% + %dpx); '
                'color: %s;" '
                'title="%s">'
                '*'
                '</span>'
                % (
                    marker_percent,
                    star_offset,
                    color,
                    tooltip
                )
            )


        html.append(
            "</div>"
        )


        # ----------------------------------------------------
        # TOTAL
        # ----------------------------------------------------

        html.append(
            '<div class="total">'
            '%.1f ms'
            '</div>'
            % row["total"]
        )


        # ----------------------------------------------------
        # PACKET LOSS
        # ----------------------------------------------------

        router_loss = row[
            "router_loss"
        ]

        internet_loss = row[
            "internet_loss"
        ]

        html.append(
            '<div class="loss">'
            'Wi-Fi: '
            '<span class="%s">%s</span>'
            '&nbsp;&nbsp;'
            'Net: '
            '<span class="%s">%s</span>'
            '</div>'
            % (
                loss_class(
                    router_loss
                ),
                loss_text(
                    router_loss
                ),
                loss_class(
                    internet_loss
                ),
                loss_text(
                    internet_loss
                )
            )
        )

        html.append(
            "</div>"
        )


    html.append(
        "</div>"
    )


    # ========================================================
    # HOP LEGEND
    # ========================================================

    known_hops = {}
    max_hop = 0

    for row in rows:

        if row["type"] != "trace":
            continue

        for segment in row["segments"]:

            hop = segment["hop"]

            max_hop = max(
                max_hop,
                hop
            )

            if (
                segment["address"] != "*"
                and
                hop not in known_hops
            ):

                known_hops[hop] = (
                    segment["address"]
                )


    if max_hop > 0:

        html.append(
            '<div class="legend">'
        )

        html.append(
            '<div class="legend-title">'
            '<b>Hop colors:</b>'
            '</div>'
        )

        for hop in range(
            1,
            max_hop + 1
        ):

            color = COLORS[
                (
                    hop - 1
                )
                % len(COLORS)
            ]

            if hop in known_hops:

                address = (
                    known_hops[
                        hop
                    ]
                )

                address_text = (
                    format_address(
                        address
                    )
                )

                if hop == 1:

                    label = (
                        "Hop 1 "
                        "(Wi-Fi/router): "
                        + address_text
                    )

                else:

                    label = (
                        "Hop %d: %s"
                        % (
                            hop,
                            address_text
                        )
                    )

            else:

                label = (
                    "Hop %d: No response (*)"
                    % hop
                )

            html.append(
                '<div '
                'class="legend-item">'
                '<span '
                'class="color-box" '
                'style="background: %s;">'
                '</span>'
                '%s'
                '</div>'
                % (
                    color,
                    label
                )
            )

        html.append(
            "</div>"
        )


    html.append(
        "</body></html>"
    )


    # ========================================================
    # WRITE HTML FILE
    # ========================================================

    with open(
        html_file,
        "w"
    ) as f:

        f.write(
            "\n".join(
                html
            )
        )

        f.flush()

        try:

            os.fsync(
                f.fileno()
            )

        except OSError:

            pass


# ============================================================
# 21. MAIN PROGRAM
# ============================================================

def main():

    print(
        "Network Latency Tracer"
    )

    print(
        "----------------------"
    )

    target = get_target()

    if not validate_target(
        target
    ):

        print()

        print(
            "Unable to resolve:",
            target
        )

        print(
            "Please check the address "
            "and run the program again."
        )

        return


    # ========================================================
    # CREATE TIMESTAMPED OUTPUT FILES
    # ========================================================

    run_start = datetime.now()

    run_stamp = run_start.strftime(
        "%Y-%m-%d_%H%M%S"
    )

    csv_file = (
        "latency_trace_"
        + run_stamp
        + ".csv"
    )

    html_file = (
        "latency_trace_"
        + run_stamp
        + ".html"
    )

    rows = []


    # ========================================================
    # DISPLAY CONFIGURATION
    # ========================================================

    print()

    print(
        "Tracing:",
        target
    )

    print(
        "Interval:",
        INTERVAL_SECONDS,
        "seconds"
    )

    print(
        "Pings per measurement:",
        PING_COUNT
    )

    print(
        "CSV:",
        csv_file
    )

    print(
        "Graph:",
        html_file
    )

    print()

    print(
        "Press Control-C to stop."
    )

    print()


    # ========================================================
    # CREATE INITIAL GRAPH
    # ========================================================

    write_html(
        rows,
        target,
        run_start,
        html_file
    )


    # ========================================================
    # OPEN GRAPH IN CHROME
    # ========================================================

    open_in_chrome(
        html_file
    )


    # ========================================================
    # MEASUREMENT LOOP
    # ========================================================

    try:

        while True:

            timestamp = (
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

            display_time = (
                timestamp.split()[1]
            )

            print(
                timestamp,
                "- running traceroute to",
                target,
                "..."
            )


            # ------------------------------------------------
            # TRACEROUTE
            # ------------------------------------------------

            trace_result = (
                run_traceroute(
                    target
                )
            )

            hops = []

            if trace_result[
                "success"
            ]:

                hops = (
                    parse_traceroute(
                        trace_result[
                            "text"
                        ]
                    )
                )


            # =================================================
            # TRACEROUTE FAILED
            # =================================================

            if (
                not trace_result[
                    "success"
                ]
                or
                not hops
            ):

                print(
                    "  Traceroute failed."
                )

                print(
                    "  Trying HTTPS GET..."
                )

                https_result = (
                    test_https(
                        target
                    )
                )


                if https_result[
                    "responded"
                ]:

                    print(
                        "  HTML response: %.1f ms"
                        % https_result[
                            "elapsed_ms"
                        ]
                    )

                else:

                    print(
                        "  No HTML response."
                    )


                rows.append({
                    "type":
                        "failure",
                    "time":
                        display_time,
                    "https_result":
                        https_result
                })


                save_failure_csv(
                    csv_file,
                    timestamp,
                    target,
                    https_result
                )


                write_html(
                    rows,
                    target,
                    run_start,
                    html_file
                )


            # =================================================
            # TRACEROUTE SUCCEEDED
            # =================================================

            else:

                segments = (
                    calculate_segments(
                        hops
                    )
                )

                total = sum(
                    segment[
                        "segment"
                    ]
                    for segment
                    in segments
                )


                # --------------------------------------------
                # FIND HOP 1
                # --------------------------------------------

                router_address = None

                for hop in hops:

                    if (
                        hop["hop"] == 1
                        and
                        hop["address"] != "*"
                    ):

                        router_address = (
                            hop["address"]
                        )

                        break


                # --------------------------------------------
                # RESOLVE HOP NAMES / OWNERS
                #
                # FQDN first.
                # RDAP registered organization second.
                # Results are cached.
                # --------------------------------------------

                for hop in hops:

                    address = (
                        hop["address"]
                    )

                    if address == "*":
                        continue

                    fqdn = get_fqdn(
                        address
                    )

                    if not fqdn:

                        get_registered_organization(
                            address
                        )


                # --------------------------------------------
                # PACKET LOSS
                # --------------------------------------------

                print(
                    "  Measuring packet loss..."
                )

                router_loss = (
                    measure_packet_loss(
                        router_address
                    )
                )

                internet_loss = (
                    measure_packet_loss(
                        target
                    )
                )


                # --------------------------------------------
                # STORE MEASUREMENT
                # --------------------------------------------

                rows.append({
                    "type":
                        "trace",
                    "time":
                        display_time,
                    "segments":
                        segments,
                    "total":
                        total,
                    "router_loss":
                        router_loss,
                    "internet_loss":
                        internet_loss
                })


                # --------------------------------------------
                # SAVE CSV
                # --------------------------------------------

                save_csv(
                    csv_file,
                    timestamp,
                    target,
                    hops,
                    router_loss,
                    internet_loss
                )


                # --------------------------------------------
                # UPDATE HTML
                # --------------------------------------------

                write_html(
                    rows,
                    target,
                    run_start,
                    html_file
                )


                # --------------------------------------------
                # CONSOLE SUMMARY
                # --------------------------------------------

                no_response_hops = [
                    str(
                        hop["hop"]
                    )
                    for hop in hops
                    if hop[
                        "no_response"
                    ]
                ]

                if no_response_hops:

                    star_text = (
                        " | * hops: "
                        + ", ".join(
                            no_response_hops
                        )
                    )

                else:

                    star_text = ""

                print(
                    "  %d hops, %.1f ms | "
                    "Wi-Fi loss: %s | "
                    "Internet loss: %s%s"
                    % (
                        len(hops),
                        total,
                        loss_text(
                            router_loss
                        ),
                        loss_text(
                            internet_loss
                        ),
                        star_text
                    )
                )


            # ------------------------------------------------
            # WAIT
            # ------------------------------------------------

            time.sleep(
                INTERVAL_SECONDS
            )


    except KeyboardInterrupt:

        print()

        print(
            "Stopped."
        )

        print()

        print(
            "Measurements saved in:",
            csv_file
        )

        print(
            "Graph saved in:",
            html_file
        )


# ============================================================
# 22. PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
