import tkinter as tk
from tkinter import ttk, messagebox
import platform, socket, subprocess, psutil, os, time
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab

APP_NAME = "Windows IT Toolkit"
APP_VERSION = "v1.2"
BG_MAIN, BG_SIDEBAR, BG_HEADER, BG_CARD = "#F4F6F8", "#1F2937", "#FFFFFF", "#FFFFFF"
TEXT_PRIMARY, TEXT_SECONDARY, TEXT_LIGHT = "#111827", "#6B7280", "#F9FAFB"
ACCENT, SUCCESS, WARNING, ERROR = "#2563EB", "#15803D", "#D97706", "#B91C1C"


# PDF fonts: ReportLab ships Bitstream Vera with the package.
# Vera supports Turkish characters such as İ, ı, Ş, ş, Ğ, ğ, Ç, ç, Ö, ö, Ü, ü.
_REPORTLAB_FONT_DIR = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
pdfmetrics.registerFont(TTFont("Vera", os.path.join(_REPORTLAB_FONT_DIR, "Vera.ttf")))
pdfmetrics.registerFont(TTFont("Vera-Bold", os.path.join(_REPORTLAB_FONT_DIR, "VeraBd.ttf")))


def clear_output():
    output_text.delete("1.0", tk.END)


def set_status(status):
    mapping = {
        "OK": ("● LAST TEST STATUS: OK", SUCCESS),
        "WARNING": ("● LAST TEST STATUS: WARNING", WARNING),
        "ERROR": ("● LAST TEST STATUS: ERROR", ERROR),
    }
    text, color = mapping.get(status, ("● LAST TEST STATUS: READY", ACCENT))
    status_label.config(text=text, fg=color)


def show_result(title, result, status="INFO"):
    clear_output()
    output_text.insert(tk.END, f"{title}\n{'=' * 70}\n\n{result}")
    set_status(status)


def progress_begin(task_name):
    progress_bar["value"] = 0
    progress_percent_label.config(text="0%")
    progress_stage_label.config(text=f"{task_name}: starting...")
    root.update_idletasks()


def progress_update(value, stage):
    value = max(0, min(100, int(value)))
    progress_bar["value"] = value
    progress_percent_label.config(text=f"{value}%")
    progress_stage_label.config(text=stage)
    root.update_idletasks()


def progress_complete(stage="Completed"):
    progress_update(100, stage)


def progress_fail(stage="Operation failed"):
    progress_bar["value"] = 100
    progress_percent_label.config(text="FAILED")
    progress_stage_label.config(text=stage)
    root.update_idletasks()


def progress_mapper(start, end):
    span = end - start
    def mapped(value, stage):
        progress_update(start + (span * value / 100), stage)
    return mapped


def percent_status(value):
    if value >= 90:
        return "CRITICAL"
    if value >= 80:
        return "WARNING"
    return "OK"


def combine_statuses(*statuses):
    if any(s in ("CRITICAL", "ERROR", "FAILED") for s in statuses):
        return "ERROR"
    if any(s == "WARNING" for s in statuses):
        return "WARNING"
    return "OK"


def ping_host(target, count=2):
    try:
        result = subprocess.run(
            ["ping", "-n", str(count), "-w", "1500", target],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=max(6, count * 3)
        )
        return result.returncode == 0
    except Exception:
        return False


def get_default_gateway():
    try:
        result = subprocess.run(
            ["route", "print", "-4"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=8
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                return parts[2]
    except Exception:
        pass
    return "Not detected"


def dns_lookup(target):
    try:
        addresses = socket.getaddrinfo(target, None)
        ips = []
        for item in addresses:
            ip = item[4][0]
            if ip not in ips:
                ips.append(ip)
        return True, ips
    except socket.gaierror:
        return False, []


def system_info():
    progress_begin("System Information")
    progress_update(20, "Reading Windows and hardware information...")
    memory = psutil.virtual_memory()
    progress_update(55, "Reading memory information...")
    disk = psutil.disk_usage("C:\\")
    progress_update(80, "Preparing system summary...")
    info = (
        f"Computer Name     : {socket.gethostname()}\n"
        f"Operating System  : {platform.system()}\n"
        f"Windows Version   : {platform.release()}\n"
        f"Architecture      : {platform.machine()}\n"
        f"Processor         : {platform.processor()}\n\n"
        f"RAM Total         : {memory.total / (1024 ** 3):.1f} GB\n"
        f"Disk Total        : {disk.total / (1024 ** 3):.1f} GB\n"
    )
    show_result("SYSTEM INFORMATION", info, "OK")
    progress_complete("System information completed")

def network_info():
    progress_begin("Network Information")
    try:
        progress_update(20, "Starting Windows network query...")
        result = subprocess.run(
            ["ipconfig", "/all"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10
        )
        progress_update(85, "Formatting network information...")
        show_result("NETWORK INFORMATION", result.stdout)
        progress_complete("Network information completed")
    except Exception as exc:
        progress_fail("Network information failed")
        messagebox.showerror("Error", str(exc))

def ping_test():
    progress_begin("Ping Test")
    target = target_entry.get().strip()
    if not target:
        progress_fail("Ping test cancelled: target is missing")
        messagebox.showwarning("Missing Target", "Enter an IP address or hostname.")
        return
    try:
        progress_update(15, f"Preparing ICMP test for {target}...")
        progress_update(30, "Sending 4 ICMP echo requests...")
        result = subprocess.run(
            ["ping", "-n", "4", target], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15
        )
        progress_update(85, "Analyzing ping responses...")
        if result.returncode == 0:
            status = "OK"
            note = "ICMP replies were received from the target."
        else:
            status = "WARNING"
            note = (
                "No successful ICMP reply was received. This does NOT prove that the host or "
                "Internet connection is unavailable; ICMP may be blocked. Confirm with DNS, "
                "TCP Port Test, or application-specific checks."
            )
        show_result(f"PING TEST - {target}", result.stdout + "\n\nINTERPRETATION\n---------------------------------\n" + note, status)
        progress_complete("Ping test completed")
    except Exception as exc:
        progress_fail("Ping test failed")
        messagebox.showerror("Error", str(exc))

def dns_test():
    progress_begin("DNS Test")
    target = target_entry.get().strip()
    if not target:
        progress_fail("DNS test cancelled: target is missing")
        messagebox.showwarning("Missing Target", "Enter a domain name.")
        return
    progress_update(20, f"Preparing DNS lookup for {target}...")
    progress_update(45, "Resolving hostname...")
    ok, ips = dns_lookup(target)
    progress_update(85, "Analyzing DNS result...")
    if ok:
        result = f"DNS Resolution Successful\n\nDomain : {target}\n\nResolved Addresses:\n"
        result += "".join(f"- {ip}\n" for ip in ips)
        result += ("\nINTERPRETATION\n---------------------------------\n"
                   "The configured DNS path can resolve this hostname. This does not guarantee that the related website or service is reachable.")
        show_result("DNS TEST", result, "OK")
    else:
        show_result("DNS TEST", f"DNS resolution failed for: {target}\n\nCheck the hostname, DNS configuration, network path, and security filtering.", "ERROR")
    progress_complete("DNS test completed")

def tcp_port_test():
    progress_begin("TCP Port Test")
    host = tcp_host_entry.get().strip()
    try:
        port = int(tcp_port_entry.get().strip())
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        progress_fail("TCP test cancelled: invalid port")
        messagebox.showerror("Invalid Port", "Port must be between 1 and 65535.")
        return
    if not host:
        progress_fail("TCP test cancelled: host is missing")
        messagebox.showwarning("Missing Host", "Enter a hostname or IP address.")
        return

    services = {22: "SSH", 53: "DNS", 80: "HTTP", 443: "HTTPS", 445: "SMB", 3389: "RDP"}
    service = services.get(port, "Unknown / Custom Service")
    try:
        progress_update(20, f"Preparing TCP connection to {host}:{port}...")
        progress_update(45, "Resolving host and opening TCP socket...")
        start = time.perf_counter()
        sock = socket.create_connection((host, port), timeout=3)
        progress_update(75, "TCP connection established; measuring response...")
        elapsed = (time.perf_counter() - start) * 1000
        peer_ip = sock.getpeername()[0]
        sock.close()
        progress_update(90, "Preparing TCP diagnostic result...")
        result = (
            f"Host       : {host}\nIP Address : {peer_ip}\nPort       : {port}\n"
            f"Service    : {service}\nStatus     : OPEN\nTime       : {elapsed:.1f} ms\n\n"
            "DIAGNOSIS\n---------------------------------\n"
            "OK: A TCP connection was established. The target service is reachable on this port."
        )
        show_result("TCP PORT TEST", result, "OK")
        progress_complete("TCP port test completed")
    except socket.gaierror:
        show_result("TCP PORT TEST", f"Hostname could not be resolved: {host}", "ERROR")
        progress_complete("TCP port test completed with DNS failure")
    except (ConnectionRefusedError, TimeoutError, OSError) as exc:
        result = (
            f"Host    : {host}\nPort    : {port}\nService : {service}\n"
            "Status  : CLOSED / FILTERED / UNREACHABLE\n\n"
            "Possible causes:\n- Service is not running\n- Port is closed\n"
            "- Firewall may be blocking access\n- Host may be unreachable\n\n"
            f"Technical detail: {exc}"
        )
        show_result("TCP PORT TEST", result, "WARNING")
        progress_complete("TCP port test completed with warning")

def collect_health_data(progress=None):
    if progress: progress(10, "Reading computer identity...")
    hostname = socket.gethostname()
    try:
        ip_address = socket.gethostbyname(hostname)
    except Exception:
        ip_address = "Unknown"
    if progress: progress(30, "Measuring CPU usage...")
    cpu = psutil.cpu_percent(interval=1)
    if progress: progress(55, "Reading memory usage...")
    memory = psutil.virtual_memory()
    if progress: progress(75, "Reading disk usage...")
    disk = psutil.disk_usage("C:\\")
    if progress: progress(90, "Calculating health status...")
    data = {
        "hostname": hostname, "ip": ip_address, "windows": platform.release(),
        "cpu": cpu, "cpu_status": percent_status(cpu),
        "ram": memory.percent, "ram_status": percent_status(memory.percent),
        "ram_total": memory.total / (1024 ** 3), "ram_free": memory.available / (1024 ** 3),
        "disk": disk.percent, "disk_status": percent_status(disk.percent),
        "disk_total": disk.total / (1024 ** 3), "disk_free": disk.free / (1024 ** 3),
    }
    data["overall"] = combine_statuses(data["cpu_status"], data["ram_status"], data["disk_status"])
    if progress: progress(100, "System health data collected")
    return data

def health_check():
    progress_begin("PC Health Check")
    d = collect_health_data(progress_mapper(5, 90))
    progress_update(95, "Preparing health report...")
    report = (
        f"Computer Name : {d['hostname']}\nIP Address    : {d['ip']}\nWindows       : {d['windows']}\n\n"
        f"CPU Usage     : {d['cpu']:.1f}%    [{d['cpu_status']}]\n"
        f"RAM Usage     : {d['ram']:.1f}%    [{d['ram_status']}]\n"
        f"RAM Available : {d['ram_free']:.1f} GB / {d['ram_total']:.1f} GB\n"
        f"Disk Usage    : {d['disk']:.1f}%    [{d['disk_status']}]\n"
        f"Disk Free     : {d['disk_free']:.1f} GB / {d['disk_total']:.1f} GB\n\n"
        "SCOPE NOTE\n---------------------------------\n"
        "This is a point-in-time resource check. It does not replace hardware diagnostics, SMART analysis, performance monitoring, or malware investigation."
    )
    show_result("PC HEALTH CHECK", report, d["overall"])
    progress_complete("PC health check completed")

def collect_network_data(progress=None):
    if progress: progress(10, "Detecting default gateway...")
    gateway = get_default_gateway()
    gateway_found = gateway != "Not detected"
    if progress: progress(30, "Testing default gateway with ICMP...")
    gateway_ok = ping_host(gateway) if gateway_found else False
    if progress: progress(50, "Testing Internet ICMP reachability...")
    internet_icmp_ok = ping_host("8.8.8.8")
    if progress: progress(68, "Testing DNS resolution...")
    dns_ok, dns_ips = dns_lookup("google.com")
    if progress: progress(82, "Testing HTTPS TCP/443 reachability...")
    https_ok = False
    try:
        sock = socket.create_connection(("google.com", 443), timeout=3)
        sock.close()
        https_ok = True
    except Exception:
        pass
    if progress: progress(100, "Network data collected")
    return {
        "gateway": gateway, "gateway_found": gateway_found, "gateway_ok": gateway_ok,
        "internet_icmp_ok": internet_icmp_ok, "dns_ok": dns_ok,
        "dns_ip": dns_ips[0] if dns_ips else "Resolution failed", "https_ok": https_ok
    }

def diagnose_network(d):
    diagnosis, actions = [], []
    if not d["gateway_found"]:
        diagnosis.append("No IPv4 default gateway was detected.")
        actions.append("Check IP address, subnet mask, DHCP, and adapter configuration.")
        return diagnosis, actions, "ERROR"
    if not d["gateway_ok"]:
        diagnosis.append("The gateway did not answer ICMP. This may be a local issue, but some gateways block ping.")
        actions += ["Check Wi-Fi/Ethernet link and adapter status.", "Verify IP configuration and gateway address."]
        return diagnosis, actions, "WARNING"
    if not d["internet_icmp_ok"] and d["https_ok"]:
        diagnosis.append("Internet ICMP failed, but HTTPS succeeded. ICMP is probably filtered.")
        actions.append("Use application-specific tests rather than ping alone.")
        return diagnosis, actions, "OK"
    if not d["internet_icmp_ok"] and not d["https_ok"]:
        diagnosis.append("Both Internet ICMP and HTTPS reachability tests failed.")
        actions.append("Check router/modem, firewall policy, upstream routing, and ISP connectivity.")
        return diagnosis, actions, "WARNING"
    if not d["dns_ok"]:
        diagnosis.append("IP connectivity appears available, but DNS resolution failed.")
        actions += ["Check configured DNS servers.", "Run ipconfig /flushdns and retry."]
        return diagnosis, actions, "WARNING"
    diagnosis.append("No obvious basic connectivity problem was detected.")
    actions.append("If the problem continues, test the affected website, application, VPN, server, or TCP service directly.")
    return diagnosis, actions, "OK"


def network_diagnostics():
    progress_begin("Smart Network Diagnostics")
    d = collect_network_data(progress_mapper(5, 85))
    progress_update(90, "Interpreting network test results...")
    diagnosis, actions, status = diagnose_network(d)
    progress_update(95, "Preparing diagnostic recommendations...")
    report = (
        f"Default Gateway : {d['gateway']}\nGateway ICMP    : {'OK' if d['gateway_ok'] else 'NO REPLY'}\n\n"
        f"Internet ICMP   : {'OK' if d['internet_icmp_ok'] else 'NO REPLY'} (8.8.8.8)\n"
        f"DNS Resolution  : {'OK' if d['dns_ok'] else 'FAILED'} (google.com -> {d['dns_ip']})\n"
        f"HTTPS 443 Test  : {'OK' if d['https_ok'] else 'FAILED'} (google.com:443)\n\n"
        "SMART DIAGNOSIS\n---------------------------------\n" + "".join(f"- {x}\n" for x in diagnosis) +
        "\nRECOMMENDED NEXT STEPS\n---------------------------------\n" + "".join(f"{i}. {x}\n" for i, x in enumerate(actions, 1)) +
        "\nSCOPE NOTE\n---------------------------------\nPing/ICMP failures are not definitive because ICMP can be intentionally filtered."
    )
    show_result("SMART NETWORK DIAGNOSTICS", report, status)
    progress_complete("Smart network diagnostics completed")

def quick_diagnostic():
    progress_begin("Quick Diagnostic")
    try:
        progress_update(5, "Starting combined diagnostic workflow...")
        h = collect_health_data(progress_mapper(5, 38))
        n = collect_network_data(progress_mapper(38, 82))
        progress_update(86, "Combining system and network findings...")
        diagnosis, actions, network_status = diagnose_network(n)

        quick_actions = []
        if h["cpu_status"] == "CRITICAL":
            quick_actions.append("CPU usage is critically high. Review processes consuming excessive CPU resources.")
        elif h["cpu_status"] == "WARNING":
            quick_actions.append("CPU usage is high. Review active processes and applications.")

        if h["ram_status"] == "CRITICAL":
            quick_actions.append("RAM usage is critically high. Review running applications, background tasks, and startup programs.")
        elif h["ram_status"] == "WARNING":
            quick_actions.append("RAM usage is high. Review running applications, background tasks, and startup programs.")

        if h["disk_status"] == "CRITICAL":
            quick_actions.append("Disk usage is critically high. Free disk space as soon as possible.")
        elif h["disk_status"] == "WARNING":
            quick_actions.append("Disk usage is high. Consider removing unnecessary files.")

        quick_actions.extend(actions)
        actions = quick_actions

        overall = combine_statuses(h["overall"], network_status)
        if overall == "OK":
            summary = "No obvious basic system-resource or network-connectivity problem was detected."
        elif overall == "WARNING":
            summary = "One or more checks require attention or confirmation."
        else:
            summary = "One or more checks indicate a significant problem that should be investigated."
        result = (
            "SYSTEM HEALTH\n---------------------------------\n"
            f"CPU Usage       : {h['cpu']:.1f}%    [{h['cpu_status']}]\n"
            f"RAM Usage       : {h['ram']:.1f}%    [{h['ram_status']}]\n"
            f"Disk Usage      : {h['disk']:.1f}%    [{h['disk_status']}]\n\n"
            "NETWORK HEALTH\n---------------------------------\n"
            f"Default Gateway : {n['gateway']}\nGateway ICMP    : {'OK' if n['gateway_ok'] else 'NO REPLY'}\n"
            f"Internet ICMP   : {'OK' if n['internet_icmp_ok'] else 'NO REPLY'}\n"
            f"DNS Resolution  : {'OK' if n['dns_ok'] else 'FAILED'}\nHTTPS 443 Test  : {'OK' if n['https_ok'] else 'FAILED'}\n\n"
            "OVERALL RESULT\n---------------------------------\n"
            f"{overall}: {summary}\n\nRECOMMENDED NEXT STEPS\n---------------------------------\n" +
            "".join(f"{i}. {x}\n" for i, x in enumerate(actions, 1)) +
            "\nSCOPE & LIMITATIONS\n---------------------------------\n"
            "Windows IT Toolkit is a Windows-focused first-line diagnostic assistant. It does not replace "
            "packet capture, advanced monitoring, endpoint security, hardware diagnostics, or enterprise tools."
        )
        progress_update(95, "Preparing quick diagnostic summary...")
        show_result("QUICK DIAGNOSTIC", result, overall)
        progress_complete("Quick diagnostic completed")
    except Exception as exc:
        progress_fail("Quick diagnostic failed")
        messagebox.showerror("Quick Diagnostic Error", str(exc))
        set_status("ERROR")


def about_tool():
    progress_begin("About / Tool Scope")
    progress_update(45, "Loading tool scope information...")
    text = (
        f"{APP_NAME} {APP_VERSION}\n\nPURPOSE\n---------------------------------\n"
        "A Windows-focused first-line diagnostic assistant for helpdesk technicians, IT support staff, small-business support, and troubleshooting workflows.\n\n"
        "WHAT IT DOES\n---------------------------------\n"
        "- Basic Windows system information\n- Ping/ICMP checks\n- DNS resolution\n- Single TCP host/port test\n"
        "- CPU, RAM, and disk utilization\n- Combined network diagnostics\n- IT Health PDF reports\n\n"
        "WHAT IT DOES NOT DO\n---------------------------------\n"
        "- It is not a port scanner or vulnerability scanner\n- It is not a packet analyzer or malware scanner\n"
        "- It does not replace PowerShell, Linux tools, Wireshark, Nmap, SIEM, RMM, or enterprise monitoring\n\n"
        "INTERPRETING RESULTS\n---------------------------------\n"
        "Results are diagnostic indicators, not absolute conclusions. A failed ping may simply mean ICMP is blocked."
    )
    progress_update(85, "Rendering scope information...")
    show_result("ABOUT / TOOL SCOPE", text)
    progress_complete("Tool scope information displayed")

def generate_report():
    progress_begin("Generate PDF Report")
    h = collect_health_data(progress_mapper(5, 30))
    n = collect_network_data(progress_mapper(30, 62))
    progress_update(66, "Evaluating overall report status...")
    diagnosis, actions, network_status = diagnose_network(n)
    overall = combine_statuses(h["overall"], network_status)

    progress_update(70, "Reading report information...")
    customer = customer_entry.get().strip()
    technician = technician_entry.get().strip()
    if not customer or customer == "Customer Name": customer = "Not specified"
    if not technician or technician == "Technician Name": technician = "Not specified"

    now = datetime.now()
    report_id = "WIT-" + now.strftime("%Y%m%d-%H%M%S")
    report_date = now.strftime("%d/%m/%Y %H:%M:%S")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    filename = f"IT_Health_Report_{h['hostname']}_{now.strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    file_path = os.path.join(desktop, filename)

    recommendations = []
    if h["cpu_status"] != "OK": recommendations.append("Review processes consuming CPU resources.")
    if h["ram_status"] != "OK": recommendations.append("Review running applications, background tasks, and startup programs.")
    if h["disk_status"] != "OK": recommendations.append("Review disk capacity and remove unnecessary files where appropriate.")
    recommendations.extend(actions)
    if not recommendations:
        recommendations.append("No major basic system-resource or network-connectivity problem was detected.")

    progress_update(78, "Building PDF document structure...")
    doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleX", parent=styles["Title"], fontName="Vera-Bold", fontSize=22, alignment=TA_CENTER, spaceAfter=8)
    subtitle = ParagraphStyle("SubtitleX", parent=styles["Normal"], fontName="Vera", fontSize=10, textColor=colors.HexColor("#6B7280"), alignment=TA_CENTER, spaceAfter=18)
    section = ParagraphStyle("SectionX", parent=styles["Heading2"], fontName="Vera-Bold", fontSize=13, textColor=colors.HexColor("#1F2937"), spaceBefore=12, spaceAfter=8)
    normal = ParagraphStyle("NormalX", parent=styles["Normal"], fontName="Vera", fontSize=9, leading=13)
    items = [Paragraph("WINDOWS IT TOOLKIT", title), Paragraph("IT HEALTH REPORT", subtitle)]

    device_data = [
        ["Customer / Company", customer], ["Technician", technician], ["Report ID", report_id],
        ["Report Date", report_date], ["Computer", h["hostname"]], ["IP Address", h["ip"]],
        ["Windows", h["windows"]], ["Overall Status", overall]
    ]
    device = Table(device_data, colWidths=[130, 330])
    device.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#F3F4F6")), ("FONTNAME", (0,0), (-1,-1), "Vera"), ("FONTNAME", (0,0), (0,-1), "Vera-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9), ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7)
    ]))
    overall_color = colors.HexColor("#15803D" if overall == "OK" else "#D97706" if overall == "WARNING" else "#B91C1C")
    device.setStyle(TableStyle([("TEXTCOLOR", (1,7), (1,7), overall_color), ("FONTNAME", (1,7), (1,7), "Vera-Bold")]))
    items += [device, Spacer(1, 16), Paragraph("EXECUTIVE SUMMARY", section)]

    summary = {
        "OK": "No obvious basic system-resource or network-connectivity problem was detected during this automated check.",
        "WARNING": "One or more diagnostic indicators require attention or confirmation.",
        "ERROR": "One or more diagnostic indicators suggest a significant problem that should be investigated."
    }[overall]
    items += [Paragraph(f"<b>Overall Status: {overall}</b><br/><br/>{summary}", normal), Spacer(1, 14)]

    system_data = [
        ["Component", "Value", "Status"], ["CPU Usage", f"{h['cpu']:.1f}%", h["cpu_status"]],
        ["RAM Usage", f"{h['ram']:.1f}%", h["ram_status"]], ["RAM Available", f"{h['ram_free']:.1f} GB / {h['ram_total']:.1f} GB", h["ram_status"]],
        ["Disk Usage", f"{h['disk']:.1f}%", h["disk_status"]], ["Disk Free", f"{h['disk_free']:.1f} GB / {h['disk_total']:.1f} GB", h["disk_status"]]
    ]
    system_table = Table(system_data, colWidths=[150,190,120])
    system_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1F2937")), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,-1), "Vera"), ("FONTNAME", (0,0), (-1,0), "Vera-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7)
    ]))
    for r, row in enumerate(system_data[1:], 1):
        c = colors.HexColor("#15803D" if row[2] == "OK" else "#D97706" if row[2] == "WARNING" else "#B91C1C")
        system_table.setStyle(TableStyle([("TEXTCOLOR", (2,r), (2,r), c), ("FONTNAME", (2,r), (2,r), "Vera-Bold")]))
    items += [Paragraph("SYSTEM HEALTH", section), system_table, Spacer(1, 14)]

    network_data = [
        ["Test", "Target", "Result"], ["Default Gateway ICMP", n["gateway"], "OK" if n["gateway_ok"] else "NO REPLY"],
        ["Internet ICMP", "8.8.8.8", "OK" if n["internet_icmp_ok"] else "NO REPLY"],
        ["DNS Resolution", "google.com", "OK" if n["dns_ok"] else "FAILED"], ["HTTPS Reachability", "google.com:443", "OK" if n["https_ok"] else "FAILED"]
    ]
    network_table = Table(network_data, colWidths=[160,180,120])
    network_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1F2937")), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,-1), "Vera"), ("FONTNAME", (0,0), (-1,0), "Vera-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7)
    ]))
    items += [Paragraph("NETWORK HEALTH", section), network_table, Spacer(1, 14), Paragraph("RECOMMENDATIONS", section)]
    for i, rec in enumerate(recommendations, 1): items.append(Paragraph(f"{i}. {rec}", normal))
    items += [Spacer(1, 12), Paragraph("SCOPE & LIMITATIONS", section), Paragraph(
        "This report contains automated first-line diagnostic observations for Windows support work. Ping/ICMP failures are not definitive because ICMP may be blocked. Resource measurements are point-in-time observations. This report does not replace hardware diagnostics, packet capture, vulnerability assessment, endpoint security, enterprise monitoring, or professional investigation.", normal),
        Spacer(1,18), Paragraph(f"Generated by Windows IT Toolkit {APP_VERSION}", subtitle)]

    try:
        progress_update(92, "Writing PDF file to Desktop...")
        doc.build(items)
        progress_complete("PDF report created successfully")
        messagebox.showinfo("PDF Report Created", "PDF report created successfully.\n\n" + file_path)
        set_status(overall)
    except Exception as exc:
        progress_fail("PDF report generation failed")
        messagebox.showerror("PDF Report Error", str(exc))


root = tk.Tk()
root.title(f"{APP_NAME} {APP_VERSION}")
root.geometry("1180x790")
root.minsize(1000, 680)
root.configure(bg=BG_MAIN)

sidebar = tk.Frame(root, bg=BG_SIDEBAR, width=250)
sidebar.pack(side=tk.LEFT, fill=tk.Y)
sidebar.pack_propagate(False)

tk.Label(sidebar, text="WINDOWS\nIT TOOLKIT", bg=BG_SIDEBAR, fg=TEXT_LIGHT, font=("Segoe UI",20,"bold"), justify=tk.LEFT).pack(anchor="w", padx=25, pady=(30,5))
tk.Label(sidebar, text=APP_VERSION, bg=BG_SIDEBAR, fg="#9CA3AF", font=("Segoe UI",9)).pack(anchor="w", padx=25, pady=(0,20))

def sidebar_button(text, command):
    b = tk.Button(sidebar, text=text, command=command, anchor="w", bg=BG_SIDEBAR, fg=TEXT_LIGHT, activebackground="#374151", activeforeground=TEXT_LIGHT, relief=tk.FLAT, bd=0, font=("Segoe UI",10), padx=25, pady=9, cursor="hand2")
    b.pack(fill=tk.X, padx=8, pady=1)

for text, command in [
    ("Quick Diagnostic", quick_diagnostic), ("System Information", system_info), ("Network Information", network_info),
    ("Ping Test", ping_test), ("DNS Test", dns_test), ("TCP Port Test", tcp_port_test), ("PC Health Check", health_check),
    ("Smart Network Diagnostics", network_diagnostics), ("Generate PDF Report", generate_report), ("About / Tool Scope", about_tool)
]: sidebar_button(text, command)

tk.Label(sidebar, text="Windows first-line diagnostics", bg=BG_SIDEBAR, fg="#9CA3AF", font=("Segoe UI",8)).pack(side=tk.BOTTOM, pady=20)

main = tk.Frame(root, bg=BG_MAIN)
main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
header = tk.Frame(main, bg=BG_HEADER, height=90); header.pack(fill=tk.X); header.pack_propagate(False)
tk.Label(header, text="IT Diagnostics Dashboard", bg=BG_HEADER, fg=TEXT_PRIMARY, font=("Segoe UI",18,"bold")).pack(anchor="w", padx=30, pady=(18,0))
tk.Label(header, text=f"Computer: {socket.gethostname()}  |  Windows-focused first-line diagnostic assistant", bg=BG_HEADER, fg=TEXT_SECONDARY, font=("Segoe UI",9)).pack(anchor="w", padx=30)
status_label = tk.Label(header, text="● LAST TEST STATUS: READY", bg=BG_HEADER, fg=ACCENT, font=("Segoe UI",9,"bold")); status_label.place(relx=0.97, rely=0.50, anchor="e")

input_card = tk.Frame(main, bg=BG_CARD); input_card.pack(fill=tk.X, padx=25, pady=(20,10))
tk.Label(input_card, text="Diagnostic Targets", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI",11,"bold")).grid(row=0,column=0,columnspan=6,sticky="w",padx=20,pady=(15,10))
tk.Label(input_card, text="Ping / DNS Target", bg=BG_CARD, fg=TEXT_SECONDARY).grid(row=1,column=0,sticky="w",padx=(20,5),pady=(0,15))
target_entry = ttk.Entry(input_card, width=24); target_entry.insert(0,"8.8.8.8"); target_entry.grid(row=1,column=1,padx=(0,25),pady=(0,15))
tk.Label(input_card, text="TCP Host", bg=BG_CARD, fg=TEXT_SECONDARY).grid(row=1,column=2,sticky="w",padx=(0,5),pady=(0,15))
tcp_host_entry = ttk.Entry(input_card,width=22); tcp_host_entry.insert(0,"google.com"); tcp_host_entry.grid(row=1,column=3,padx=(0,20),pady=(0,15))
tk.Label(input_card, text="Port", bg=BG_CARD, fg=TEXT_SECONDARY).grid(row=1,column=4,sticky="w",padx=(0,5),pady=(0,15))
tcp_port_entry = ttk.Entry(input_card,width=8); tcp_port_entry.insert(0,"443"); tcp_port_entry.grid(row=1,column=5,padx=(0,20),pady=(0,15))

report_card = tk.Frame(main, bg=BG_CARD); report_card.pack(fill=tk.X,padx=25,pady=(0,10))
tk.Label(report_card,text="Report Information",bg=BG_CARD,fg=TEXT_PRIMARY,font=("Segoe UI",11,"bold")).grid(row=0,column=0,columnspan=4,sticky="w",padx=20,pady=(12,8))
tk.Label(report_card,text="Customer / Company",bg=BG_CARD,fg=TEXT_SECONDARY).grid(row=1,column=0,sticky="w",padx=(20,5),pady=(0,12))
customer_entry = ttk.Entry(report_card,width=30); customer_entry.insert(0,"Customer Name"); customer_entry.grid(row=1,column=1,padx=(0,30),pady=(0,12))
tk.Label(report_card,text="Technician",bg=BG_CARD,fg=TEXT_SECONDARY).grid(row=1,column=2,sticky="w",padx=(0,5),pady=(0,12))
technician_entry = ttk.Entry(report_card,width=25); technician_entry.insert(0,"Technician Name"); technician_entry.grid(row=1,column=3,padx=(0,20),pady=(0,12))

# OPERATION PROGRESS
progress_card = tk.Frame(main, bg=BG_CARD)
progress_card.pack(fill=tk.X, padx=25, pady=(0,10))
progress_top = tk.Frame(progress_card, bg=BG_CARD)
progress_top.pack(fill=tk.X, padx=20, pady=(10,4))
tk.Label(progress_top, text="Operation Progress", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI",10,"bold")).pack(side=tk.LEFT)
progress_percent_label = tk.Label(progress_top, text="0%", bg=BG_CARD, fg=ACCENT, font=("Segoe UI",10,"bold"))
progress_percent_label.pack(side=tk.RIGHT)
progress_bar = ttk.Progressbar(progress_card, orient="horizontal", mode="determinate", maximum=100)
progress_bar.pack(fill=tk.X, padx=20, pady=(0,5))
progress_stage_label = tk.Label(progress_card, text="Ready - select a diagnostic function", bg=BG_CARD, fg=TEXT_SECONDARY, font=("Segoe UI",9), anchor="w")
progress_stage_label.pack(fill=tk.X, padx=20, pady=(0,10))

output_card = tk.Frame(main,bg=BG_CARD); output_card.pack(fill=tk.BOTH,expand=True,padx=25,pady=(10,25))
tk.Label(output_card,text="Diagnostic Output",bg=BG_CARD,fg=TEXT_PRIMARY,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=20,pady=(15,10))
output_frame = tk.Frame(output_card,bg=BG_CARD); output_frame.pack(fill=tk.BOTH,expand=True,padx=20,pady=(0,20))
scrollbar = ttk.Scrollbar(output_frame); scrollbar.pack(side=tk.RIGHT,fill=tk.Y)
output_text = tk.Text(output_frame,font=("Consolas",10),bg="#FAFAFA",fg=TEXT_PRIMARY,relief=tk.FLAT,padx=15,pady=15,yscrollcommand=scrollbar.set)
output_text.pack(side=tk.LEFT,fill=tk.BOTH,expand=True); scrollbar.config(command=output_text.yview)
output_text.insert(tk.END, f"{APP_NAME} {APP_VERSION}\n{'='*70}\n\nToolkit is ready.\n\nRecommended first step: run Quick Diagnostic.\nUse the individual tools for deeper first-line troubleshooting.")

root.mainloop()
