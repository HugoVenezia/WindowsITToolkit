import tkinter as tk
from tkinter import ttk, messagebox
import platform
import socket
import subprocess
import psutil
import os
import time
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)

# =========================================================
# APPLICATION SETTINGS
# =========================================================

APP_NAME = "Windows IT Toolkit"
APP_VERSION = "v1.0"

BG_MAIN = "#F4F6F8"
BG_SIDEBAR = "#1F2937"
BG_HEADER = "#FFFFFF"
BG_CARD = "#FFFFFF"

TEXT_PRIMARY = "#111827"
TEXT_SECONDARY = "#6B7280"
TEXT_LIGHT = "#F9FAFB"

ACCENT = "#2563EB"
SUCCESS = "#15803D"
WARNING = "#D97706"
ERROR = "#B91C1C"


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def clear_output():
    output_text.delete("1.0", tk.END)


def show_result(title, result, status="INFO"):
    clear_output()

    output_text.insert(
        tk.END,
        f"{title}\n"
        f"{'=' * 70}\n\n"
        f"{result}"
    )

    set_status(status)


def set_status(status):
    if status == "OK":
        status_label.config(
            text="● LAST TEST STATUS: OK",
            fg=SUCCESS
        )

    elif status == "WARNING":
        status_label.config(
            text="● LAST TEST STATUS: WARNING",
            fg=WARNING
        )

    elif status == "ERROR":
        status_label.config(
            text="● LAST TEST STATUS: ERROR",
            fg=ERROR
        )

    else:
        status_label.config(
            text="● LAST TEST STATUS: READY",
            fg=ACCENT
        )

def ping_host(target):
    try:
        result = subprocess.run(
            ["ping", "-n", "2", "-w", "1500", target],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        return result.returncode == 0

    except Exception:
        return False


def get_default_gateway():
    try:
        result = subprocess.run(
            ["route", "print", "-4"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        for line in result.stdout.splitlines():
            parts = line.split()

            if len(parts) >= 5:
                if (
                    parts[0] == "0.0.0.0"
                    and parts[1] == "0.0.0.0"
                ):
                    return parts[2]

        return "Not detected"

    except Exception:
        return "Not detected"


# =========================================================
# SYSTEM INFORMATION
# =========================================================

def system_info():
    hostname = socket.gethostname()

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")

    info = (
        f"Computer Name     : {hostname}\n"
        f"Operating System  : {platform.system()}\n"
        f"Windows Version   : {platform.release()}\n"
        f"Architecture      : {platform.machine()}\n"
        f"Processor         : {platform.processor()}\n\n"
        f"RAM Total         : {memory.total / (1024 ** 3):.1f} GB\n"
        f"Disk Total        : {disk.total / (1024 ** 3):.1f} GB\n"
    )

    show_result(
        "SYSTEM INFORMATION",
        info,
        "OK"
    )


# =========================================================
# NETWORK INFORMATION
# =========================================================

def network_info():
    try:
        result = subprocess.run(
            ["ipconfig", "/all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        show_result(
            "NETWORK INFORMATION",
            result.stdout
        )

    except Exception as error:
        messagebox.showerror(
            "Error",
            str(error)
        )


# =========================================================
# PING TEST
# =========================================================

def ping_test():
    target = target_entry.get().strip()

    if not target:
        messagebox.showwarning(
            "Missing Target",
            "Enter an IP address or hostname."
        )
        return

    try:
        result = subprocess.run(
            ["ping", "-n", "4", target],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        if result.returncode == 0:
            status = "OK"
        else:
            status = "WARNING"

        show_result(
            f"PING TEST - {target}",
            result.stdout,
            status
        )

    except Exception as error:
        messagebox.showerror(
            "Error",
            str(error)
        )


# =========================================================
# DNS TEST
# =========================================================

def dns_test():
    target = target_entry.get().strip()

    if not target:
        messagebox.showwarning(
            "Missing Target",
            "Enter a domain name."
        )
        return

    try:
        addresses = socket.getaddrinfo(
            target,
            None
        )

        ips = []

        for item in addresses:
            ip = item[4][0]

            if ip not in ips:
                ips.append(ip)

        result = (
            "DNS Resolution Successful\n\n"
            f"Domain : {target}\n\n"
            "Resolved Addresses:\n"
        )

        for ip in ips:
            result += f"- {ip}\n"

        show_result(
            "DNS TEST",
            result,
            "OK"
        )

    except socket.gaierror:
        show_result(
            "DNS TEST",
            "DNS resolution failed.",
            "ERROR"
        )


# =========================================================
# TCP PORT TEST
# =========================================================

def tcp_port_test():
    host = tcp_host_entry.get().strip()
    port_text = tcp_port_entry.get().strip()

    if not host:
        messagebox.showwarning(
            "Missing Host",
            "Enter a hostname or IP address."
        )
        return

    if not port_text:
        messagebox.showwarning(
            "Missing Port",
            "Enter a TCP port number."
        )
        return

    try:
        port = int(port_text)

        if port < 1 or port > 65535:
            raise ValueError

    except ValueError:
        messagebox.showerror(
            "Invalid Port",
            "Port must be between 1 and 65535."
        )
        return

    services = {
        22: "SSH",
        53: "DNS",
        80: "HTTP",
        443: "HTTPS",
        445: "SMB / File Sharing",
        3389: "Remote Desktop (RDP)"
    }

    service_name = services.get(
        port,
        "Unknown / Custom Service"
    )

    try:
        start_time = time.perf_counter()

        sock = socket.create_connection(
            (host, port),
            timeout=3
        )

        elapsed_ms = (
            time.perf_counter() - start_time
        ) * 1000

        peer_ip = sock.getpeername()[0]

        sock.close()

        result = (
            f"Host       : {host}\n"
            f"IP Address : {peer_ip}\n"
            f"Port       : {port}\n"
            f"Service    : {service_name}\n"
            f"Status     : OPEN\n"
            f"Time       : {elapsed_ms:.1f} ms\n\n"
            "DIAGNOSIS\n"
            "---------------------------------\n"
            "OK: TCP connection succeeded.\n"
            "The target service is reachable on this port."
        )

        show_result(
            "TCP PORT TEST",
            result,
            "OK"
        )

    except socket.gaierror:
        result = (
            f"Host    : {host}\n"
            f"Port    : {port}\n"
            f"Service : {service_name}\n\n"
            "STATUS\n"
            "---------------------------------\n"
            "FAILED: Hostname could not be resolved.\n\n"
            "DIAGNOSIS\n"
            "---------------------------------\n"
            "Check hostname and DNS resolution."
        )

        show_result(
            "TCP PORT TEST",
            result,
            "ERROR"
        )

    except (ConnectionRefusedError, TimeoutError, OSError):
        result = (
            f"Host    : {host}\n"
            f"Port    : {port}\n"
            f"Service : {service_name}\n"
            f"Status  : CLOSED / UNREACHABLE\n\n"
            "DIAGNOSIS\n"
            "---------------------------------\n"
            "The TCP connection could not be established.\n\n"
            "Possible causes:\n"
            "- Service is not running\n"
            "- Port is closed\n"
            "- Firewall may be blocking access\n"
            "- Host may be unreachable"
        )

        show_result(
            "TCP PORT TEST",
            result,
            "WARNING"
        )


# =========================================================
# PC HEALTH CHECK
# =========================================================

def collect_health_report():
    hostname = socket.gethostname()

    try:
        ip_address = socket.gethostbyname(hostname)
    except Exception:
        ip_address = "Unknown"

    cpu_usage = psutil.cpu_percent(interval=1)

    memory = psutil.virtual_memory()

    total_ram = memory.total / (1024 ** 3)
    available_ram = memory.available / (1024 ** 3)

    disk = psutil.disk_usage("C:\\")

    total_disk = disk.total / (1024 ** 3)
    free_disk = disk.free / (1024 ** 3)

    warnings = []

    if memory.percent >= 90:
        warnings.append(
            "CRITICAL: RAM usage is very high."
        )

    elif memory.percent >= 80:
        warnings.append(
            "WARNING: RAM usage is high."
        )

    if disk.percent >= 90:
        warnings.append(
            "CRITICAL: Disk usage is very high."
        )

    elif disk.percent >= 80:
        warnings.append(
            "WARNING: Disk usage is high."
        )

    if cpu_usage >= 90:
        warnings.append(
            "CRITICAL: CPU usage is very high."
        )

    elif cpu_usage >= 80:
        warnings.append(
            "WARNING: CPU usage is high."
        )

    if warnings:
        health_status = "\n".join(warnings)
        overall_status = "WARNING"

    else:
        health_status = (
            "OK: No critical resource problems detected."
        )
        overall_status = "OK"

    report = (
        f"Computer Name : {hostname}\n"
        f"IP Address    : {ip_address}\n"
        f"Windows       : {platform.release()}\n\n"
        f"CPU Usage     : {cpu_usage:.1f}%\n\n"
        f"RAM Total     : {total_ram:.1f} GB\n"
        f"RAM Available : {available_ram:.1f} GB\n"
        f"RAM Usage     : {memory.percent:.1f}%\n\n"
        f"Disk Total    : {total_disk:.1f} GB\n"
        f"Disk Free     : {free_disk:.1f} GB\n"
        f"Disk Usage    : {disk.percent:.1f}%\n\n"
        "HEALTH STATUS\n"
        "---------------------------------\n"
        f"{health_status}"
    )

    return report, overall_status


def health_check():
    report, status = collect_health_report()

    show_result(
        "PC HEALTH CHECK",
        report,
        status
    )


# =========================================================
# SMART NETWORK DIAGNOSIS
# =========================================================

def diagnose_network(
    gateway_found,
    gateway_ok,
    internet_ok,
    dns_ok
):
    diagnosis = []
    actions = []

    if not gateway_found:
        diagnosis.append(
            "Possible local IP configuration problem."
        )

        actions.append(
            "Check IP address, subnet mask and default gateway."
        )

        actions.append(
            "Check Wi-Fi/Ethernet connection and DHCP."
        )

        return diagnosis, actions, "ERROR"

    if not gateway_ok:
        diagnosis.append(
            "The computer cannot reach the default gateway."
        )

        actions.append(
            "Check Ethernet cable or Wi-Fi."
        )

        actions.append(
            "Check network adapter status."
        )

        actions.append(
            "Verify IP configuration."
        )

        actions.append(
            "Check router or switch connectivity."
        )

        return diagnosis, actions, "ERROR"

    if gateway_ok and not internet_ok:
        diagnosis.append(
            "Local network is reachable but Internet test failed."
        )

        actions.append(
            "Check router/modem Internet connection."
        )

        actions.append(
            "Check ISP connectivity."
        )

        actions.append(
            "Check firewall or upstream routing."
        )

        return diagnosis, actions, "WARNING"

    if internet_ok and not dns_ok:
        diagnosis.append(
            "Internet connectivity works but DNS resolution failed."
        )

        actions.append(
            "Check configured DNS servers."
        )

        actions.append(
            "Try another trusted DNS server."
        )

        actions.append(
            "Run ipconfig /flushdns."
        )

        return diagnosis, actions, "WARNING"

    diagnosis.append(
        "No obvious network connectivity problem detected."
    )

    actions.append(
        "If problems continue, test the specific website, "
        "application, server or TCP port."
    )

    return diagnosis, actions, "OK"


def collect_network_report():
    gateway = get_default_gateway()

    gateway_found = gateway != "Not detected"

    if gateway_found:
        gateway_ok = ping_host(gateway)
    else:
        gateway_ok = False

    internet_ok = ping_host("8.8.8.8")

    try:
        addresses = socket.getaddrinfo(
            "google.com",
            None
        )

        resolved_ips = []

        for address in addresses:
            ip = address[4][0]

            if ip not in resolved_ips:
                resolved_ips.append(ip)

        dns_ok = True

        dns_ip = (
            resolved_ips[0]
            if resolved_ips
            else "Unknown"
        )

    except socket.gaierror:
        dns_ip = "Resolution failed"
        dns_ok = False

    gateway_status = (
        "OK" if gateway_ok else "FAILED"
    )

    internet_status = (
        "OK" if internet_ok else "FAILED"
    )

    dns_status = (
        "OK" if dns_ok else "FAILED"
    )

    diagnosis, actions, overall_status = diagnose_network(
        gateway_found,
        gateway_ok,
        internet_ok,
        dns_ok
    )

    diagnosis_text = ""

    for item in diagnosis:
        diagnosis_text += f"- {item}\n"

    action_text = ""

    for number, item in enumerate(
        actions,
        start=1
    ):
        action_text += (
            f"{number}. {item}\n"
        )

    report = (
        f"Default Gateway : {gateway}\n"
        f"Gateway Test    : {gateway_status}\n\n"
        f"Internet Target : 8.8.8.8\n"
        f"Internet Test   : {internet_status}\n\n"
        f"DNS Test Domain : google.com\n"
        f"Resolved IP     : {dns_ip}\n"
        f"DNS Test        : {dns_status}\n\n"
        "SMART DIAGNOSIS\n"
        "---------------------------------\n"
        f"{diagnosis_text}\n"
        "RECOMMENDED NEXT STEPS\n"
        "---------------------------------\n"
        f"{action_text}"
    )

    return report, overall_status


def network_diagnostics():
    report, status = collect_network_report()

    show_result(
        "SMART NETWORK DIAGNOSTICS",
        report,
        status
    )


# =========================================================
# =========================================================
# PDF REPORT
# =========================================================

def generate_report():
    hostname = socket.gethostname()

    customer_name = customer_entry.get().strip()
    technician_name = technician_entry.get().strip()

    if not customer_name or customer_name == "Customer Name":
        customer_name = "Not specified"

    if not technician_name or technician_name == "Technician Name":
        technician_name = "Not specified"

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    report_date = now.strftime("%d/%m/%Y %H:%M:%S")
    report_id = "WIT-" + now.strftime("%Y%m%d-%H%M%S")

    # -------------------------
    # COLLECT SYSTEM HEALTH
    # -------------------------
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")

    total_ram = memory.total / (1024 ** 3)
    available_ram = memory.available / (1024 ** 3)
    total_disk = disk.total / (1024 ** 3)
    free_disk = disk.free / (1024 ** 3)

    try:
        ip_address = socket.gethostbyname(hostname)
    except Exception:
        ip_address = "Unknown"

    if cpu_usage >= 90:
        cpu_status = "CRITICAL"
    elif cpu_usage >= 80:
        cpu_status = "WARNING"
    else:
        cpu_status = "OK"

    if memory.percent >= 90:
        ram_status = "CRITICAL"
    elif memory.percent >= 80:
        ram_status = "WARNING"
    else:
        ram_status = "OK"

    if disk.percent >= 90:
        disk_status = "CRITICAL"
    elif disk.percent >= 80:
        disk_status = "WARNING"
    else:
        disk_status = "OK"

    # -------------------------
    # COLLECT NETWORK HEALTH
    # -------------------------
    gateway = get_default_gateway()
    gateway_found = gateway != "Not detected"
    gateway_ok = ping_host(gateway) if gateway_found else False
    internet_ok = ping_host("8.8.8.8")

    try:
        socket.getaddrinfo("google.com", None)
        dns_ok = True
    except socket.gaierror:
        dns_ok = False

    gateway_status = "OK" if gateway_ok else "FAILED"
    internet_status = "OK" if internet_ok else "FAILED"
    dns_status = "OK" if dns_ok else "FAILED"

    # -------------------------
    # OVERALL STATUS
    # -------------------------
    system_statuses = [cpu_status, ram_status, disk_status]
    network_statuses = [gateway_status, internet_status, dns_status]

    if "CRITICAL" in system_statuses or "FAILED" in network_statuses:
        overall_status = "CRITICAL"
    elif "WARNING" in system_statuses:
        overall_status = "WARNING"
    else:
        overall_status = "OK"

    # -------------------------
    # RECOMMENDATIONS
    # -------------------------
    recommendations = []

    if ram_status == "CRITICAL":
        recommendations.append(
            "RAM usage is critically high. Review running applications and background processes."
        )
    elif ram_status == "WARNING":
        recommendations.append(
            "RAM usage is high. Review running applications and startup programs."
        )

    if cpu_status == "CRITICAL":
        recommendations.append(
            "CPU usage is critically high. Check processes consuming excessive CPU resources."
        )
    elif cpu_status == "WARNING":
        recommendations.append(
            "CPU usage is high. Review active processes and applications."
        )

    if disk_status == "CRITICAL":
        recommendations.append(
            "Disk usage is critically high. Free disk space as soon as possible."
        )
    elif disk_status == "WARNING":
        recommendations.append(
            "Disk usage is high. Consider removing unnecessary files."
        )

    if not gateway_ok:
        recommendations.append(
            "Default gateway could not be reached. Check the local network connection and router."
        )

    if not internet_ok:
        recommendations.append(
            "Internet connectivity test failed. Check modem, router or ISP connectivity."
        )

    if not dns_ok:
        recommendations.append(
            "DNS resolution failed. Check configured DNS servers."
        )

    if not recommendations:
        recommendations.append(
            "No major system or network problems were detected."
        )

    # -------------------------
    # FILE PATH
    # -------------------------
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    filename = f"IT_Health_Report_{hostname}_{timestamp}.pdf"
    file_path = os.path.join(desktop, filename)

    # -------------------------
    # PDF DOCUMENT
    # -------------------------
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        alignment=TA_CENTER,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        textColor=colors.HexColor("#6B7280"),
        alignment=TA_CENTER,
        spaceAfter=20
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=colors.HexColor("#1F2937"),
        spaceBefore=12,
        spaceAfter=8
    )

    normal_style = ParagraphStyle(
        "NormalCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13
    )

    recommendation_style = ParagraphStyle(
        "Recommendation",
        parent=normal_style,
        leftIndent=12,
        spaceAfter=6
    )

    # HEADER
    elements.append(Paragraph("WINDOWS IT TOOLKIT", title_style))
    elements.append(Paragraph("IT HEALTH REPORT", subtitle_style))

    # DEVICE INFO
    device_data = [
        ["Customer / Company", customer_name],
        ["Technician", technician_name],
        ["Report ID", report_id],
        ["Report Date", report_date],
        ["Computer", hostname],
        ["IP Address", ip_address],
        ["Windows", platform.release()],
        ["Overall Status", overall_status]
    ]

    device_table = Table(device_data, colWidths=[130, 330])
    device_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F4F6")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
    ]))

    if overall_status == "OK":
        overall_color = colors.HexColor("#15803D")
    elif overall_status == "WARNING":
        overall_color = colors.HexColor("#D97706")
    else:
        overall_color = colors.HexColor("#B91C1C")

    device_table.setStyle(TableStyle([
        ("TEXTCOLOR", (1, 7), (1, 7), overall_color),
        ("FONTNAME", (1, 7), (1, 7), "Helvetica-Bold")
    ]))

    elements.append(device_table)
    elements.append(Spacer(1, 18))

    # EXECUTIVE SUMMARY
    elements.append(Paragraph("EXECUTIVE SUMMARY", section_style))

    if overall_status == "OK":
        summary_text = (
            "Overall system and network health is GOOD. "
            "No significant problems were detected during the automated diagnostic checks."
        )
    elif overall_status == "WARNING":
        summary_text = (
            "The computer is operational, but one or more conditions require attention. "
            "Review the recommendations in this report."
        )
    else:
        summary_text = (
            "One or more critical system or network problems were detected. "
            "Technical investigation is recommended."
        )

    elements.append(Paragraph(
        f"<b>Overall Status: {overall_status}</b><br/><br/>{summary_text}",
        normal_style
    ))
    elements.append(Spacer(1, 18))

    # SYSTEM HEALTH
    elements.append(Paragraph("SYSTEM HEALTH", section_style))

    system_data = [
        ["Component", "Value", "Status"],
        ["CPU Usage", f"{cpu_usage:.1f}%", cpu_status],
        ["RAM Usage", f"{memory.percent:.1f}%", ram_status],
        ["RAM Available", f"{available_ram:.1f} GB / {total_ram:.1f} GB", ram_status],
        ["Disk Usage", f"{disk.percent:.1f}%", disk_status],
        ["Disk Free", f"{free_disk:.1f} GB / {total_disk:.1f} GB", disk_status]
    ]

    system_table = Table(system_data, colWidths=[150, 190, 120])
    system_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
    ]))

    for row_number, row in enumerate(system_data[1:], start=1):
        status = row[2]
        if status == "OK":
            status_color = colors.HexColor("#15803D")
        elif status == "WARNING":
            status_color = colors.HexColor("#D97706")
        else:
            status_color = colors.HexColor("#B91C1C")

        system_table.setStyle(TableStyle([
            ("TEXTCOLOR", (2, row_number), (2, row_number), status_color),
            ("FONTNAME", (2, row_number), (2, row_number), "Helvetica-Bold")
        ]))

    elements.append(system_table)
    elements.append(Spacer(1, 18))

    # NETWORK HEALTH
    elements.append(Paragraph("NETWORK HEALTH", section_style))

    network_data = [
        ["Test", "Target", "Status"],
        ["Default Gateway", gateway, gateway_status],
        ["Internet Connectivity", "8.8.8.8", internet_status],
        ["DNS Resolution", "google.com", dns_status]
    ]

    network_table = Table(network_data, colWidths=[160, 180, 120])
    network_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
    ]))

    for row_number, row in enumerate(network_data[1:], start=1):
        status_color = (
            colors.HexColor("#15803D")
            if row[2] == "OK"
            else colors.HexColor("#B91C1C")
        )
        network_table.setStyle(TableStyle([
            ("TEXTCOLOR", (2, row_number), (2, row_number), status_color),
            ("FONTNAME", (2, row_number), (2, row_number), "Helvetica-Bold")
        ]))

    elements.append(network_table)
    elements.append(Spacer(1, 18))

    # RECOMMENDATIONS
    elements.append(Paragraph("RECOMMENDATIONS", section_style))

    for number, recommendation in enumerate(recommendations, start=1):
        elements.append(Paragraph(
            f"{number}. {recommendation}",
            recommendation_style
        ))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        (
            f"Generated by Windows IT Toolkit {APP_VERSION}<br/>"
            "This report provides automated diagnostic observations "
            "and should be used together with professional IT assessment."
        ),
        subtitle_style
    ))

    try:
        doc.build(elements)

        messagebox.showinfo(
            "PDF Report Created",
            "PDF report created successfully.\n\n" + file_path
        )

        if overall_status == "OK":
            set_status("OK")
        elif overall_status == "WARNING":
            set_status("WARNING")
        else:
            set_status("ERROR")

    except Exception as error:
        messagebox.showerror(
            "PDF Report Error",
            str(error)
        )


# =========================================================
# WINDOW
# =========================================================

root = tk.Tk()

root.title(
    f"{APP_NAME} {APP_VERSION}"
)

root.geometry(
    "1180x760"
)

root.minsize(
    1000,
    650
)

root.configure(
    bg=BG_MAIN
)


# =========================================================
# SIDEBAR
# =========================================================

sidebar = tk.Frame(
    root,
    bg=BG_SIDEBAR,
    width=250
)

sidebar.pack(
    side=tk.LEFT,
    fill=tk.Y
)

sidebar.pack_propagate(False)


logo_label = tk.Label(
    sidebar,
    text="WINDOWS\nIT TOOLKIT",
    bg=BG_SIDEBAR,
    fg=TEXT_LIGHT,
    font=("Segoe UI", 20, "bold"),
    justify=tk.LEFT
)

logo_label.pack(
    anchor="w",
    padx=25,
    pady=(30, 5)
)


version_label = tk.Label(
    sidebar,
    text=APP_VERSION,
    bg=BG_SIDEBAR,
    fg="#9CA3AF",
    font=("Segoe UI", 9)
)

version_label.pack(
    anchor="w",
    padx=25,
    pady=(0, 25)
)


def sidebar_button(text, command):
    button = tk.Button(
        sidebar,
        text=text,
        command=command,
        anchor="w",
        bg=BG_SIDEBAR,
        fg=TEXT_LIGHT,
        activebackground="#374151",
        activeforeground=TEXT_LIGHT,
        relief=tk.FLAT,
        bd=0,
        font=("Segoe UI", 10),
        padx=25,
        pady=11,
        cursor="hand2"
    )

    button.pack(
        fill=tk.X,
        padx=8,
        pady=2
    )

    return button


sidebar_button(
    "System Information",
    system_info
)

sidebar_button(
    "Network Information",
    network_info
)

sidebar_button(
    "Ping Test",
    ping_test
)

sidebar_button(
    "DNS Test",
    dns_test
)

sidebar_button(
    "TCP Port Test",
    tcp_port_test
)

sidebar_button(
    "PC Health Check",
    health_check
)

sidebar_button(
    "Smart Network Diagnostics",
    network_diagnostics
)

sidebar_button(
    "Generate PDF Report",
    generate_report
)


footer_label = tk.Label(
    sidebar,
    text="IT Diagnostic Utility",
    bg=BG_SIDEBAR,
    fg="#9CA3AF",
    font=("Segoe UI", 8)
)

footer_label.pack(
    side=tk.BOTTOM,
    pady=20
)


# =========================================================
# MAIN AREA
# =========================================================

main = tk.Frame(
    root,
    bg=BG_MAIN
)

main.pack(
    side=tk.LEFT,
    fill=tk.BOTH,
    expand=True
)


# HEADER
header = tk.Frame(
    main,
    bg=BG_HEADER,
    height=90
)

header.pack(
    fill=tk.X
)

header.pack_propagate(False)


computer_name = socket.gethostname()


header_title = tk.Label(
    header,
    text="IT Diagnostics Dashboard",
    bg=BG_HEADER,
    fg=TEXT_PRIMARY,
    font=("Segoe UI", 18, "bold")
)

header_title.pack(
    anchor="w",
    padx=30,
    pady=(18, 0)
)


header_subtitle = tk.Label(
    header,
    text=f"Computer: {computer_name}",
    bg=BG_HEADER,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 9)
)

header_subtitle.pack(
    anchor="w",
    padx=30
)


status_label = tk.Label(
    header,
    text="● SYSTEM STATUS: READY",
    bg=BG_HEADER,
    fg=ACCENT,
    font=("Segoe UI", 9, "bold")
)

status_label.place(
    relx=0.97,
    rely=0.50,
    anchor="e"
)


# =========================================================
# TEST INPUT CARD
# =========================================================

input_card = tk.Frame(
    main,
    bg=BG_CARD
)

input_card.pack(
    fill=tk.X,
    padx=25,
    pady=(20, 10)
)


input_title = tk.Label(
    input_card,
    text="Diagnostic Targets",
    bg=BG_CARD,
    fg=TEXT_PRIMARY,
    font=("Segoe UI", 11, "bold")
)

input_title.grid(
    row=0,
    column=0,
    columnspan=6,
    sticky="w",
    padx=20,
    pady=(15, 10)
)


target_label = tk.Label(
    input_card,
    text="Ping / DNS Target",
    bg=BG_CARD,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 9)
)

target_label.grid(
    row=1,
    column=0,
    sticky="w",
    padx=(20, 5),
    pady=(0, 15)
)


target_entry = ttk.Entry(
    input_card,
    width=24
)

target_entry.insert(
    0,
    "8.8.8.8"
)

target_entry.grid(
    row=1,
    column=1,
    padx=(0, 25),
    pady=(0, 15)
)


tcp_host_label = tk.Label(
    input_card,
    text="TCP Host",
    bg=BG_CARD,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 9)
)

tcp_host_label.grid(
    row=1,
    column=2,
    sticky="w",
    padx=(0, 5),
    pady=(0, 15)
)


tcp_host_entry = ttk.Entry(
    input_card,
    width=22
)

tcp_host_entry.insert(
    0,
    "google.com"
)

tcp_host_entry.grid(
    row=1,
    column=3,
    padx=(0, 20),
    pady=(0, 15)
)


tcp_port_label = tk.Label(
    input_card,
    text="Port",
    bg=BG_CARD,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 9)
)

tcp_port_label.grid(
    row=1,
    column=4,
    sticky="w",
    padx=(0, 5),
    pady=(0, 15)
)


tcp_port_entry = ttk.Entry(
    input_card,
    width=8
)

tcp_port_entry.insert(
    0,
    "443"
)

tcp_port_entry.grid(
    row=1,
    column=5,
    padx=(0, 20),
    pady=(0, 15)
)

# =========================================================
# REPORT INFORMATION CARD
# =========================================================

report_info_card = tk.Frame(
    main,
    bg=BG_CARD
)

report_info_card.pack(
    fill=tk.X,
    padx=25,
    pady=(0, 10)
)


report_info_title = tk.Label(
    report_info_card,
    text="Report Information",
    bg=BG_CARD,
    fg=TEXT_PRIMARY,
    font=("Segoe UI", 11, "bold")
)

report_info_title.grid(
    row=0,
    column=0,
    columnspan=4,
    sticky="w",
    padx=20,
    pady=(12, 8)
)


customer_label = tk.Label(
    report_info_card,
    text="Customer / Company",
    bg=BG_CARD,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 9)
)

customer_label.grid(
    row=1,
    column=0,
    sticky="w",
    padx=(20, 5),
    pady=(0, 12)
)


customer_entry = ttk.Entry(
    report_info_card,
    width=30
)

customer_entry.insert(
    0,
    "Customer Name"
)

customer_entry.grid(
    row=1,
    column=1,
    padx=(0, 30),
    pady=(0, 12)
)


technician_label = tk.Label(
    report_info_card,
    text="Technician",
    bg=BG_CARD,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 9)
)

technician_label.grid(
    row=1,
    column=2,
    sticky="w",
    padx=(0, 5),
    pady=(0, 12)
)


technician_entry = ttk.Entry(
    report_info_card,
    width=25
)

technician_entry.insert(
    0,
    "Technician Name"
)

technician_entry.grid(
    row=1,
    column=3,
    padx=(0, 20),
    pady=(0, 12)
)
# =========================================================
# OUTPUT CARD
# =========================================================

output_card = tk.Frame(
    main,
    bg=BG_CARD
)

output_card.pack(
    fill=tk.BOTH,
    expand=True,
    padx=25,
    pady=(10, 25)
)


output_header = tk.Label(
    output_card,
    text="Diagnostic Output",
    bg=BG_CARD,
    fg=TEXT_PRIMARY,
    font=("Segoe UI", 11, "bold")
)

output_header.pack(
    anchor="w",
    padx=20,
    pady=(15, 10)
)


output_frame = tk.Frame(
    output_card,
    bg=BG_CARD
)

output_frame.pack(
    fill=tk.BOTH,
    expand=True,
    padx=20,
    pady=(0, 20)
)


scrollbar = ttk.Scrollbar(
    output_frame
)

scrollbar.pack(
    side=tk.RIGHT,
    fill=tk.Y
)


output_text = tk.Text(
    output_frame,
    font=("Consolas", 10),
    bg="#FAFAFA",
    fg=TEXT_PRIMARY,
    relief=tk.FLAT,
    padx=15,
    pady=15,
    yscrollcommand=scrollbar.set
)

output_text.pack(
    side=tk.LEFT,
    fill=tk.BOTH,
    expand=True
)

scrollbar.config(
    command=output_text.yview
)


output_text.insert(
    tk.END,
    f"{APP_NAME} {APP_VERSION}\n"
    f"{'=' * 70}\n\n"
    "Toolkit is ready.\n\n"
    "Select a diagnostic function from the left menu."
)


# =========================================================
# START
# =========================================================

root.mainloop(),
