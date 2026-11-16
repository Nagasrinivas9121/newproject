"""
SRIVANI BOOKING MANAGER - Web Application & Local REST API Server
Provides browser-based dashboard access, queue management, analytics, and operational reports.

Usage:
    python web_app.py [--port 8000]
"""
import sys
import os
import datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, Response
import jinja2

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from database import (
    init_db,
    get_all_families,
    get_family,
    get_family_pilgrims,
    get_stats,
    update_status_and_payment,
    get_queue_history,
)
from import_export import (
    export_to_csv,
    export_to_excel,
)
from reports import (
    get_daily_completed_report,
    get_weekly_report,
    get_booking_status_summary_report,
    get_total_pilgrims_report,
    validate_report_totals,
    generate_printable_pdf_report,
)
from analytics_engine import (
    get_analytics_summary,
    get_booking_performance,
    get_queue_intelligence,
    get_payment_analytics,
    get_document_analytics,
    get_operational_intelligence,
)
from analytics_export import (
    export_full_analytics_workbook_xlsx,
    export_analytics_report_pdf,
    export_summary_to_csv,
)

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "srivani_booking_local_web_secret_2026"

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

# Ensure core database tables exist
init_db()

# -----------------------------------------------------------------------------
# Templates Dictionary for Jinja DictLoader
# -----------------------------------------------------------------------------

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} — SRIVANI Booking Manager</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex flex-col">

    <!-- Top Navigation Bar -->
    <header class="bg-slate-800 border-b border-slate-700 sticky top-0 z-50 shadow-md">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
            <div class="flex items-center space-x-3">
                <div class="bg-amber-600 text-white p-2 rounded-lg font-bold text-lg tracking-wider flex items-center justify-center w-10 h-10 shadow">
                    <i class="fa-solid fa-om"></i>
                </div>
                <div>
                    <h1 class="text-base font-bold text-white tracking-tight leading-none">SRIVANI BOOKING MANAGER</h1>
                    <span class="text-xs text-amber-400 font-semibold uppercase tracking-wider">Web Portal v7.0.0</span>
                </div>
            </div>

            <!-- Nav Links -->
            <nav class="hidden md:flex space-x-1">
                <a href="/" class="px-3 py-2 rounded-md text-sm font-medium {{ 'bg-slate-900 text-amber-400 border border-slate-700' if active_page == 'dashboard' else 'text-slate-300 hover:bg-slate-700 hover:text-white' }}">
                    <i class="fa-solid fa-gauge mr-1.5"></i> Dashboard
                </a>
                <a href="/queue" class="px-3 py-2 rounded-md text-sm font-medium {{ 'bg-slate-900 text-amber-400 border border-slate-700' if active_page == 'queue' else 'text-slate-300 hover:bg-slate-700 hover:text-white' }}">
                    <i class="fa-solid fa-list-ol mr-1.5"></i> Queue Assistant
                </a>
                <a href="/analytics" class="px-3 py-2 rounded-md text-sm font-medium {{ 'bg-slate-900 text-amber-400 border border-slate-700' if active_page == 'analytics' else 'text-slate-300 hover:bg-slate-700 hover:text-white' }}">
                    <i class="fa-solid fa-chart-line mr-1.5"></i> Analytics
                </a>
                <a href="/reports" class="px-3 py-2 rounded-md text-sm font-medium {{ 'bg-slate-900 text-amber-400 border border-slate-700' if active_page == 'reports' else 'text-slate-300 hover:bg-slate-700 hover:text-white' }}">
                    <i class="fa-solid fa-file-invoice mr-1.5"></i> Reports & Export
                </a>
            </nav>

            <!-- Action Buttons -->
            <div class="flex items-center space-x-2">
                <a href="/demo-ttd-booking" class="bg-slate-700 hover:bg-slate-600 text-amber-300 border border-slate-600 px-3 py-1.5 rounded-md text-xs font-semibold flex items-center shadow transition duration-150">
                    <i class="fa-solid fa-flask mr-1.5"></i> 🎯 Live TTD Demo
                </a>
                <button onclick="document.getElementById('autofill-modal').classList.remove('hidden')" class="bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-md text-xs font-semibold flex items-center shadow transition duration-150">
                    <i class="fa-solid fa-wand-magic-sparkles mr-1.5"></i> ⚡ TTD 1-Click Auto-Fill
                </button>
                <a href="https://tirupatibalaji.ap.gov.in/#/userLogin" target="_blank" rel="noopener" class="bg-amber-600 hover:bg-amber-500 text-white px-3 py-1.5 rounded-md text-xs font-semibold flex items-center shadow transition duration-150">
                    <i class="fa-solid fa-arrow-up-right-from-square mr-1.5"></i> Open TTD Login Portal
                </a>
            </div>
        </div>
    </header>

    <!-- Main Content Container -->
    <main class="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">
        {% block content %}{% endblock %}
    </main>

    <!-- 1-Click Auto-Fill Setup Modal -->
    <div id="autofill-modal" class="hidden fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
        <div class="bg-slate-800 border border-amber-500/40 rounded-xl max-w-2xl w-full p-6 shadow-2xl relative text-slate-200">
            <button onclick="document.getElementById('autofill-modal').classList.add('hidden')" class="absolute top-4 right-4 text-slate-400 hover:text-white text-xl">
                <i class="fa-solid fa-xmark"></i>
            </button>
            <div class="flex items-center space-x-3 mb-4">
                <div class="bg-amber-500 text-slate-900 w-10 h-10 rounded-lg flex items-center justify-center text-xl font-bold">
                    <i class="fa-solid fa-wand-magic-sparkles"></i>
                </div>
                <div>
                    <h2 class="text-lg font-bold text-white">TTD Portal 1-Click Auto-Fill Companion</h2>
                    <p class="text-xs text-amber-400">TTD వెబ్‌సైట్ లోకి భక్తుల వివరాలు ఆటోమేటిక్‌గా ఫిల్ అవ్వడానికి</p>
                </div>
            </div>

            <div class="space-y-4 text-sm">
                <!-- Method 1: Bookmarklet -->
                <div class="bg-slate-900 border border-slate-700 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-bold text-amber-300 text-sm">
                            <i class="fa-solid fa-bookmark mr-1.5"></i> పద్ధతి 1: బుక్‌మార్క్ బటన్ (అత్యంత సులభం - రికమండెడ్)
                        </span>
                        <span class="text-xs bg-emerald-900/60 text-emerald-300 px-2 py-0.5 rounded border border-emerald-700">సులభమైన విధానం</span>
                    </div>
                    <p class="text-xs text-slate-300 mb-3">
                        క్రింది బటన్‌ను మీ Chrome <strong>Bookmarks Bar</strong> లోకి Drag & Drop చేయండి. మీరు TTD వెబ్‌సైట్‌లో లాగిన్ అయ్యాక Darshan Form వద్ద దీనిపై ఒక క్లిక్ చేస్తే చాలు, స్క్రీన్ పై ఆటో-ఫిల్ విడ్జెట్ కనిపిస్తుంది:
                    </p>
                    <div class="flex items-center justify-center p-3 bg-slate-950 rounded border border-slate-800">
                        <a href="javascript:(function(){var s=document.createElement('script');s.src='http://localhost:8000/api/autofill.js?t='+Date.now();document.body.appendChild(s);})();" 
                           class="bg-amber-600 hover:bg-amber-500 text-white font-bold text-sm px-5 py-2.5 rounded-lg shadow-lg flex items-center cursor-grab active:cursor-grabbing border border-amber-400/50 hover:scale-105 transition transform">
                            <i class="fa-solid fa-om mr-2 text-lg"></i> 🛕 TTD 1-Click Auto-Fill (Drag me to Bookmarks bar)
                        </a>
                    </div>
                </div>

                <!-- Method 2: Console Paste -->
                <div class="bg-slate-900 border border-slate-700 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-bold text-sky-300 text-sm">
                            <i class="fa-solid fa-terminal mr-1.5"></i> పద్ధతి 2: F12 Console కోడ్ (ఇన్‌స్టంట్ రన్)
                        </span>
                    </div>
                    <p class="text-xs text-slate-300 mb-2">
                        TTD వెబ్‌సైట్ ట్యాబ్‌లో ఉండి కీబోర్డులో <kbd class="px-1.5 py-0.5 bg-slate-800 border border-slate-600 rounded text-amber-300 font-mono">F12</kbd> నొక్కి, <strong>Console</strong> లో క్రింది 1 లైన్ కోడ్‌ను Paste చేసి <kbd class="px-1.5 py-0.5 bg-slate-800 border border-slate-600 rounded text-amber-300 font-mono">Enter</kbd> నొక్కండి:
                    </p>
                    <div class="flex items-center space-x-2">
                        <input id="autofill-snippet" type="text" readonly value="fetch('http://localhost:8000/api/autofill.js?t='+Date.now()).then(r=>r.text()).then(eval);" class="bg-slate-950 border border-slate-700 text-amber-300 font-mono text-xs px-3 py-2 rounded flex-grow outline-none select-all">
                        <button onclick="navigator.clipboard.writeText(document.getElementById('autofill-snippet').value); this.innerText='✓ Copied!';" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded shadow">
                            Copy Code
                        </button>
                    </div>
                </div>

                <!-- Method 3: Queue Split Screen -->
                <div class="bg-slate-900 border border-slate-700 rounded-lg p-3 flex items-center justify-between">
                    <div>
                        <div class="font-semibold text-slate-200 text-xs">
                            <i class="fa-solid fa-table-columns mr-1 text-amber-400"></i> పద్ధతి 3: Queue Assistant (స్ప్లిట్ స్క్రీన్ కాపీ)
                        </div>
                        <div class="text-xs text-slate-400">
                            ఒక్క క్లిక్‌తో భక్తుడి పేరు, ఆధార్, వయస్సులను కాపీ చేసుకోవడానికి
                        </div>
                    </div>
                    <a href="/queue" class="bg-slate-800 hover:bg-slate-700 text-amber-400 border border-slate-600 text-xs font-semibold px-3 py-1.5 rounded transition">
                        Open Queue <i class="fa-solid fa-arrow-right ml-1"></i>
                    </a>
                </div>
            </div>

            <div class="mt-5 text-right">
                <button onclick="document.getElementById('autofill-modal').classList.add('hidden')" class="bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold px-4 py-2 rounded">
                    Close
                </button>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="bg-slate-950 border-t border-slate-800 py-4 mt-auto">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center text-xs text-slate-400">
            <div>
                SRIVANI Booking Manager &bull; Assisted Devotee Darshan Workflow Engine &bull; Strictly Offline Security
            </div>
            <div class="mt-2 sm:mt-0">
                Official Portal: <a href="https://ttdevasthanams.ap.gov.in" target="_blank" class="text-amber-400 hover:underline">ttdevasthanams.ap.gov.in</a>
            </div>
        </div>
    </footer>

</body>
</html>
"""

DASHBOARD_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<!-- KPI Summary Row -->
<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow">
        <span class="text-xs font-semibold uppercase text-slate-400">Total Families</span>
        <div class="text-2xl font-bold text-white mt-1">{{ stats.total_families }}</div>
    </div>
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow">
        <span class="text-xs font-semibold uppercase text-slate-400">Total Devotees</span>
        <div class="text-2xl font-bold text-amber-400 mt-1">{{ stats.total_pilgrims }}</div>
    </div>
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow">
        <span class="text-xs font-semibold uppercase text-slate-400">Pending Queue</span>
        <div class="text-2xl font-bold text-amber-500 mt-1">{{ stats.pending_families }}</div>
    </div>
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow">
        <span class="text-xs font-semibold uppercase text-slate-400">In Progress</span>
        <div class="text-2xl font-bold text-blue-400 mt-1">{{ stats.in_progress }}</div>
    </div>
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow">
        <span class="text-xs font-semibold uppercase text-slate-400">Booked</span>
        <div class="text-2xl font-bold text-emerald-400 mt-1">{{ stats.booked }}</div>
    </div>
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow">
        <span class="text-xs font-semibold uppercase text-slate-400">Total Donations</span>
        <div class="text-2xl font-bold text-emerald-400 mt-1">₹{{ "{:,.0f}".format(stats.total_donation) }}</div>
    </div>
</div>

<!-- Active Families Table Card -->
<div class="bg-slate-800 border border-slate-700 rounded-lg shadow overflow-hidden">
    <div class="p-4 border-b border-slate-700 flex flex-col sm:flex-row justify-between items-center gap-3">
        <div>
            <h2 class="text-lg font-bold text-white flex items-center">
                <i class="fa-solid fa-users text-amber-500 mr-2"></i> Family & Devotee Booking Records
            </h2>
            <p class="text-xs text-slate-400 mt-0.5">Prioritized sequential darshan booking queue</p>
        </div>
        <div class="flex items-center space-x-2">
            <a href="/api/export/excel" class="bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold px-3 py-1.5 rounded flex items-center transition shadow">
                <i class="fa-solid fa-file-excel mr-1.5"></i> Export Excel
            </a>
            <a href="/api/export/csv" class="bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold px-3 py-1.5 rounded flex items-center transition shadow">
                <i class="fa-solid fa-file-csv mr-1.5"></i> Export CSV
            </a>
        </div>
    </div>

    <div class="overflow-x-auto">
        <table class="w-full text-left text-sm text-slate-300">
            <thead class="bg-slate-900 text-xs uppercase text-slate-400 font-semibold border-b border-slate-700">
                <tr>
                    <th class="px-4 py-3">Queue #</th>
                    <th class="px-4 py-3">Family Code & Name</th>
                    <th class="px-4 py-3">Contact</th>
                    <th class="px-4 py-3">Devotees</th>
                    <th class="px-4 py-3">Preferred Date</th>
                    <th class="px-4 py-3">Donation</th>
                    <th class="px-4 py-3">Priority</th>
                    <th class="px-4 py-3">Status</th>
                    <th class="px-4 py-3">Payment</th>
                    <th class="px-4 py-3 text-right">Actions</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-700/60 font-normal">
                {% for f in families %}
                <tr class="hover:bg-slate-700/40 transition">
                    <td class="px-4 py-3 text-xs font-mono text-slate-400">#{{ loop.index }}</td>
                    <td class="px-4 py-3 font-semibold text-white">
                        <div>{{ f.family_name }}</div>
                        <span class="text-xs font-mono text-amber-400 bg-amber-950/60 border border-amber-800/60 px-1.5 py-0.5 rounded">{{ f.family_code }}</span>
                    </td>
                    <td class="px-4 py-3 text-xs">
                        <div class="font-medium text-slate-200">{{ f.contact_name or '—' }}</div>
                        <div class="text-slate-400 font-mono">{{ f.phone }}</div>
                    </td>
                    <td class="px-4 py-3">
                        <span class="bg-slate-700 text-slate-200 text-xs px-2 py-0.5 rounded-full font-semibold">
                            {{ f.pilgrim_count }} Pilgrim(s)
                        </span>
                    </td>
                    <td class="px-4 py-3 text-xs font-mono text-slate-300">
                        {{ f.preferred_date or 'Flexible' }}
                    </td>
                    <td class="px-4 py-3 text-xs font-semibold text-emerald-400">
                        ₹{{ "{:,.0f}".format(f.donation_amount or 0) }}
                    </td>
                    <td class="px-4 py-3 text-xs">
                        {% if f.priority == 'Urgent' %}
                        <span class="bg-red-950 text-red-300 border border-red-800 px-2 py-0.5 rounded text-xs font-bold uppercase">Urgent</span>
                        {% elif f.priority == 'High' %}
                        <span class="bg-amber-950 text-amber-300 border border-amber-800 px-2 py-0.5 rounded text-xs font-bold uppercase">High</span>
                        {% else %}
                        <span class="bg-slate-800 text-slate-300 border border-slate-600 px-2 py-0.5 rounded text-xs font-semibold">Normal</span>
                        {% endif %}
                    </td>
                    <td class="px-4 py-3 text-xs">
                        {% if f.status == 'Booked' %}
                        <span class="bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-semibold">Booked</span>
                        {% elif f.status == 'In progress' %}
                        <span class="bg-blue-950 text-blue-300 border border-blue-800 px-2 py-0.5 rounded font-semibold">In Progress</span>
                        {% elif f.status == 'Cancelled' %}
                        <span class="bg-red-950 text-red-300 border border-red-800 px-2 py-0.5 rounded font-semibold">Cancelled</span>
                        {% else %}
                        <span class="bg-amber-950 text-amber-300 border border-amber-800 px-2 py-0.5 rounded font-semibold">Pending</span>
                        {% endif %}
                    </td>
                    <td class="px-4 py-3 text-xs">
                        {% if f.payment_status == 'Paid' %}
                        <span class="text-emerald-400 font-semibold"><i class="fa-solid fa-circle-check mr-1"></i> Paid</span>
                        {% elif f.payment_status == 'Request sent' %}
                        <span class="text-blue-400 font-semibold"><i class="fa-solid fa-clock mr-1"></i> Sent</span>
                        {% else %}
                        <span class="text-slate-400">{{ f.payment_status }}</span>
                        {% endif %}
                    </td>
                    <td class="px-4 py-3 text-right text-xs">
                        <a href="/queue" class="bg-amber-600 hover:bg-amber-500 text-white px-2.5 py-1 rounded font-medium transition shadow">
                            Assist <i class="fa-solid fa-chevron-right ml-1"></i>
                        </a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""

QUEUE_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<div class="mb-6 flex justify-between items-center">
    <div>
        <h2 class="text-xl font-bold text-white flex items-center">
            <i class="fa-solid fa-hands-praying text-amber-500 mr-2"></i> Assisted Booking Companion
        </h2>
        <p class="text-xs text-slate-400 mt-1">1-click copy helpers to streamline data entry on the official TTD Portal</p>
    </div>
    <a href="https://tirupatibalaji.ap.gov.in/#/userLogin" target="_blank" class="bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center shadow">
        Launch TTD User Login <i class="fa-solid fa-arrow-up-right-from-square ml-1.5"></i>
    </a>
</div>

<!-- Family Cards with Pilgrim Details & Copy Buttons -->
<div class="space-y-4">
    {% for f in families %}
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-5 shadow">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center pb-3 border-b border-slate-700 gap-2">
            <div>
                <span class="text-xs font-mono text-amber-400 bg-amber-950/70 border border-amber-800 px-2 py-0.5 rounded mr-2 font-bold">{{ f.family_code }}</span>
                <span class="text-base font-bold text-white">{{ f.family_name }}</span>
                <span class="text-xs text-slate-400 ml-2">({{ f.pilgrim_count }} Devotees &bull; ₹{{ "{:,.0f}".format(f.donation_amount or 0) }})</span>
            </div>
            <div class="flex items-center space-x-2">
                <span class="text-xs px-2.5 py-0.5 rounded-full font-bold uppercase {{ 'bg-red-950 text-red-300 border border-red-800' if f.priority == 'Urgent' else ('bg-amber-950 text-amber-300 border border-amber-800' if f.priority == 'High' else 'bg-slate-700 text-slate-300') }}">{{ f.priority }}</span>
                <span class="text-xs px-2.5 py-0.5 rounded-full font-bold uppercase {{ 'bg-emerald-950 text-emerald-300 border border-emerald-800' if f.status == 'Booked' else ('bg-blue-950 text-blue-300 border border-blue-800' if f.status == 'In progress' else 'bg-amber-950 text-amber-300 border border-amber-800') }}">{{ f.status }}</span>
            </div>
        </div>

        <!-- Devotees List -->
        <div class="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {% for p in f.pilgrims %}
            <div class="bg-slate-900 border border-slate-700/80 rounded p-3 flex justify-between items-center text-xs">
                <div>
                    <div class="font-bold text-slate-100">{{ p.full_name }}</div>
                    <div class="text-slate-400 text-xs mt-0.5">
                        {{ p.age }} yrs &bull; {{ p.gender }} &bull; {{ p.id_proof_type }} (..{{ p.id_proof_last4 }})
                    </div>
                </div>
                <button onclick="navigator.clipboard.writeText('{{ p.full_name }}'); alert('Copied: {{ p.full_name }}');" class="bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 px-2 py-1 rounded text-xs font-semibold">
                    <i class="fa-regular fa-copy mr-1"></i> Name
                </button>
            </div>
            {% endfor %}
        </div>

        <!-- Action Bar -->
        <div class="mt-4 pt-3 border-t border-slate-700/60 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-xs">
            <div class="text-slate-400">
                <span class="font-semibold text-slate-300">Contact:</span> {{ f.contact_name }} ({{ f.phone }})
                &bull; <span class="font-semibold text-slate-300">Preferred Date:</span> {{ f.preferred_date or 'Flexible' }}
            </div>
            <form action="/api/family/update_status" method="POST" class="flex flex-wrap items-center gap-2">
                <input type="hidden" name="family_id" value="{{ f.id }}">
                <select name="status" class="bg-slate-900 border border-slate-600 text-xs text-white rounded px-2 py-1">
                    <option value="Pending" {{ 'selected' if f.status == 'Pending' else '' }}>Pending</option>
                    <option value="In progress" {{ 'selected' if f.status == 'In progress' else '' }}>In Progress</option>
                    <option value="Booked" {{ 'selected' if f.status == 'Booked' else '' }}>Booked</option>
                    <option value="Cancelled" {{ 'selected' if f.status == 'Cancelled' else '' }}>Cancelled</option>
                </select>
                <select name="payment_status" class="bg-slate-900 border border-slate-600 text-xs text-white rounded px-2 py-1">
                    <option value="Not requested" {{ 'selected' if f.payment_status == 'Not requested' else '' }}>Not Requested</option>
                    <option value="Request sent" {{ 'selected' if f.payment_status == 'Request sent' else '' }}>Request Sent</option>
                    <option value="Paid" {{ 'selected' if f.payment_status == 'Paid' else '' }}>Paid</option>
                </select>
                <input type="text" name="payment_ref" placeholder="Txn Ref #" value="{{ f.payment_ref or '' }}" class="bg-slate-900 border border-slate-600 text-xs text-white rounded px-2 py-1 w-28">
                <button type="submit" class="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1 rounded font-semibold transition">
                    Save
                </button>
            </form>
        </div>
    </div>
    {% endfor %}
</div>
{% endblock %}
"""

ANALYTICS_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<div class="mb-6 flex justify-between items-center">
    <div>
        <h2 class="text-xl font-bold text-white flex items-center">
            <i class="fa-solid fa-chart-pie text-amber-500 mr-2"></i> Operational Intelligence & Performance Analytics
        </h2>
        <p class="text-xs text-slate-400 mt-1">Live computed metrics from local SQLite records &bull; Zero external cloud telemetry</p>
    </div>
    <div class="flex space-x-2">
        <a href="/api/export/analytics-xlsx" class="bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold px-3 py-1.5 rounded flex items-center transition shadow">
            <i class="fa-solid fa-file-excel mr-1.5"></i> Multi-Tab Excel (.xlsx)
        </a>
        <a href="/api/export/analytics-pdf" class="bg-rose-700 hover:bg-rose-600 text-white text-xs font-semibold px-3 py-1.5 rounded flex items-center transition shadow">
            <i class="fa-solid fa-file-pdf mr-1.5"></i> Executive PDF
        </a>
    </div>
</div>

<!-- Analytics KPI Cards -->
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow">
        <div class="text-xs font-semibold uppercase text-slate-400">Completion Rate</div>
        <div class="text-2xl font-bold text-emerald-400 mt-1">{{ summary.booking_completion_percentage }}%</div>
        <div class="text-xs text-slate-400 mt-1">{{ summary.completed_bookings }} of {{ summary.total_families }} families booked</div>
    </div>
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow">
        <div class="text-xs font-semibold uppercase text-slate-400">Average Turnaround</div>
        <div class="text-2xl font-bold text-amber-400 mt-1">{{ perf.avg_turnaround_hours or 0 }} hrs</div>
        <div class="text-xs text-slate-400 mt-1">Lead time to confirmed booking</div>
    </div>
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow">
        <div class="text-xs font-semibold uppercase text-slate-400">Payment Ref Capture</div>
        <div class="text-2xl font-bold text-blue-400 mt-1">{{ pay_intel.payment_ref_capture_rate or 0 }}%</div>
        <div class="text-xs text-slate-400 mt-1">Transaction audit reconciliation</div>
    </div>
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow">
        <div class="text-xs font-semibold uppercase text-slate-400">Ticket Compliance</div>
        <div class="text-2xl font-bold text-purple-400 mt-1">{{ doc_intel.ticket_compliance_percentage or 0 }}%</div>
        <div class="text-xs text-slate-400 mt-1">Booked with official ticket PDFs</div>
    </div>
</div>

<!-- Queue Aging & Operational Insights -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
    <!-- Aging Buckets -->
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-5 shadow">
        <h3 class="text-base font-bold text-white mb-3 flex items-center">
            <i class="fa-solid fa-hourglass-half text-amber-400 mr-2"></i> Queue Aging Distribution
        </h3>
        <div class="space-y-3">
            {% for bucket, count in queue_intel.aging_buckets.items() %}
            <div>
                <div class="flex justify-between text-xs mb-1 font-semibold text-slate-300">
                    <span>{{ bucket }}</span>
                    <span class="font-mono text-amber-400">{{ count }} family(ies)</span>
                </div>
                <div class="w-full bg-slate-900 rounded-full h-2">
                    <div class="bg-amber-500 h-2 rounded-full" style="width: {{ 100 if count > 0 else 0 }}%"></div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Operational Insights & Heuristic Priority -->
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-5 shadow">
        <h3 class="text-base font-bold text-white mb-3 flex items-center">
            <i class="fa-solid fa-brain text-amber-400 mr-2"></i> Deterministic Prioritization Scoring
        </h3>
        {% if op_intel.recommended_queue %}
        <div class="space-y-2">
            {% for item in op_intel.recommended_queue %}
            <div class="bg-slate-900 border border-slate-700 p-3 rounded flex justify-between items-center text-xs">
                <div>
                    <span class="font-bold text-white">{{ item.family_name }}</span>
                    <span class="text-xs font-mono text-amber-400 ml-1">({{ item.family_code }})</span>
                    <div class="text-slate-400 text-xs mt-0.5">Priority: {{ item.priority }} &bull; Date: {{ item.preferred_date or 'Flexible' }}</div>
                </div>
                <div class="text-right">
                    <div class="bg-amber-600/30 text-amber-300 border border-amber-600/60 px-2 py-0.5 rounded font-mono font-bold">Score: {{ item.score }}</div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="text-xs text-slate-400">All pending requests are prioritized. No stalled backlog detected.</div>
        {% endif %}
    </div>
</div>
{% endblock %}
"""

REPORTS_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<div class="mb-6 flex justify-between items-center">
    <div>
        <h2 class="text-xl font-bold text-white flex items-center">
            <i class="fa-solid fa-file-invoice text-amber-500 mr-2"></i> Operational Reports & Reconciliation
        </h2>
        <p class="text-xs text-slate-400 mt-1">Audit-ready operational summaries with automated totals reconciliation</p>
    </div>
    <div class="flex space-x-2">
        <a href="/api/export/report-pdf?type=booking_status_summary" class="bg-rose-700 hover:bg-rose-600 text-white text-xs font-semibold px-3 py-1.5 rounded flex items-center shadow transition">
            <i class="fa-solid fa-file-pdf mr-1.5"></i> Printable PDF Summary
        </a>
        <a href="/api/export/csv" class="bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold px-3 py-1.5 rounded flex items-center shadow transition">
            <i class="fa-solid fa-file-csv mr-1.5"></i> Export CSV
        </a>
    </div>
</div>

<!-- Totals Reconciliation Card -->
<div class="bg-slate-800 border {{ 'border-emerald-600/50 bg-emerald-950/10' if reconciliation.is_valid else 'border-red-600/50 bg-red-950/10' }} rounded-lg p-5 mb-6 shadow">
    <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
            <div class="text-2xl {{ 'text-emerald-400' if reconciliation.is_valid else 'text-red-400' }}">
                <i class="fa-solid {{ 'fa-circle-check' if reconciliation.is_valid else 'fa-triangle-exclamation' }}"></i>
            </div>
            <div>
                <h3 class="text-base font-bold text-white">Database Totals Reconciliation Status</h3>
                <p class="text-xs text-slate-300">
                    {{ 'Cross-table verification passed. Devotee totals, statuses, and payment checksums match perfectly.' if reconciliation.is_valid else 'Anomalies detected in database cross-check.' }}
                </p>
            </div>
        </div>
        <div class="text-right text-xs font-mono text-slate-300">
            <div>Total Families: <span class="font-bold text-white">{{ reconciliation.total_families }}</span></div>
            <div>Total Devotees: <span class="font-bold text-amber-400">{{ reconciliation.total_pilgrims }}</span></div>
            <div>Orphaned Records: <span class="font-bold text-emerald-400">{{ reconciliation.orphaned_pilgrims }}</span></div>
        </div>
    </div>
</div>

<!-- Status Breakdown Table -->
<div class="bg-slate-800 border border-slate-700 rounded-lg p-5 shadow">
    <h3 class="text-base font-bold text-white mb-3">Booking Status Distribution</h3>
    <table class="w-full text-left text-xs text-slate-300">
        <thead class="bg-slate-900 uppercase font-semibold text-slate-400 border-b border-slate-700">
            <tr>
                <th class="px-4 py-2.5">Status</th>
                <th class="px-4 py-2.5">Families</th>
                <th class="px-4 py-2.5">Devotees</th>
                <th class="px-4 py-2.5">Total Donations</th>
                <th class="px-4 py-2.5">Tickets Attached</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-slate-700">
            {% for r in status_summary %}
            <tr class="hover:bg-slate-700/40">
                <td class="px-4 py-2.5 font-bold text-white">{{ r.status }}</td>
                <td class="px-4 py-2.5">{{ r.family_count }}</td>
                <td class="px-4 py-2.5">{{ r.pilgrim_count }}</td>
                <td class="px-4 py-2.5 text-emerald-400 font-semibold">₹{{ "{:,.0f}".format(r.total_donation) }}</td>
                <td class="px-4 py-2.5">{{ r.tickets_attached }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
"""

DEMO_TTD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tirumala Tirupati Devasthanams — Pilgrim Registration Simulation</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f8fafc; color: #1e293b; }
        .ttd-header-bar { background: linear-gradient(90deg, #991b1b, #7f1d1d); }
    </style>
</head>
<body class="min-h-screen flex flex-col">

    <!-- Official Style TTD Header -->
    <header class="ttd-header-bar text-white shadow-md">
        <div class="max-w-5xl mx-auto px-4 py-3 flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 bg-amber-400 rounded-full flex items-center justify-center text-red-900 font-bold text-xl shadow">
                    🕉️
                </div>
                <div>
                    <h1 class="text-lg font-bold tracking-wide">తిరుమల తిరుపతి దేవస్థానములు &bull; TTD</h1>
                    <p class="text-xs text-amber-200">SRIVANI Trust Darshan Booking — Pilgrim Registration</p>
                </div>
            </div>
            <div>
                <a href="/" class="bg-amber-500 hover:bg-amber-400 text-slate-900 font-bold text-xs px-3 py-1.5 rounded shadow">
                    &larr; Back to Dashboard
                </a>
            </div>
        </div>
    </header>

    <!-- Simulation Banner -->
    <div class="bg-amber-100 border-b border-amber-300 px-4 py-3 text-amber-900 text-sm">
        <div class="max-w-5xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-2">
            <div class="flex items-center space-x-2">
                <i class="fa-solid fa-flask text-amber-700 text-lg"></i>
                <span><strong>TTD Booking Simulation Mode:</strong> This page simulates the official TTD darshan pilgrim form to verify auto-fill.</span>
            </div>
            <button id="launch-companion-btn" onclick="launchCompanion()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs px-4 py-2 rounded-lg shadow flex items-center gap-1.5 transition">
                <i class="fa-solid fa-wand-magic-sparkles"></i> ⚡ Launch Auto-Fill Companion
            </button>
        </div>
    </div>

    <!-- Main Booking Form Content -->
    <main class="max-w-5xl mx-auto px-4 py-6 flex-grow w-full">

        <!-- Quota summary badge -->
        <div class="bg-white rounded-lg border border-slate-300 p-4 mb-6 shadow-sm flex justify-between items-center">
            <div>
                <span class="text-xs uppercase font-bold text-slate-500">Selected Darshan Quota</span>
                <div class="text-base font-bold text-slate-800">SRIVANI VIP Break Darshan &bull; 25-Dec-2026 (08:00 AM)</div>
            </div>
            <div class="bg-emerald-100 text-emerald-800 px-3 py-1 rounded text-xs font-bold border border-emerald-300">
                Quota Reserved (Time Left: 09:45)
            </div>
        </div>

        <form id="ttd-pilgrim-form" onsubmit="event.preventDefault(); alert('Form submitted successfully!');" class="space-y-6">

            <!-- Pilgrim 1 Card -->
            <div class="bg-white rounded-lg border border-slate-300 shadow-sm overflow-hidden">
                <div class="bg-slate-100 px-4 py-2.5 border-b border-slate-200 font-bold text-slate-700 text-sm flex justify-between items-center">
                    <span>1. Primary Devotee / Pilgrim 1</span>
                    <span class="text-xs text-rose-600 font-semibold">* Mandatory</span>
                </div>
                <div class="p-4 grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Pilgrim Full Name *</label>
                        <input type="text" name="pilgrimName0" id="pilgrimName0" placeholder="Full Name as in ID Proof" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Age *</label>
                        <input type="number" name="age0" id="age0" placeholder="Age" min="1" max="110" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Gender *</label>
                        <select name="gender0" id="gender0" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none bg-white">
                            <option value="">Select Gender</option>
                            <option value="Male">Male</option>
                            <option value="Female">Female</option>
                            <option value="Transgender">Transgender</option>
                        </select>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Photo ID Proof *</label>
                        <select name="idProofType0" id="idProofType0" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none bg-white">
                            <option value="">Select ID Proof</option>
                            <option value="Aadhaar">Aadhaar Card</option>
                            <option value="Passport">Passport</option>
                            <option value="Voter ID">Voter ID</option>
                        </select>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Photo ID Card Number *</label>
                        <input type="text" name="idNumber0" id="idNumber0" placeholder="Enter ID Proof Number" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none">
                    </div>
                </div>
            </div>

            <!-- Pilgrim 2 Card -->
            <div class="bg-white rounded-lg border border-slate-300 shadow-sm overflow-hidden">
                <div class="bg-slate-100 px-4 py-2.5 border-b border-slate-200 font-bold text-slate-700 text-sm flex justify-between items-center">
                    <span>2. Devotee / Pilgrim 2</span>
                    <span class="text-xs text-rose-600 font-semibold">* Mandatory</span>
                </div>
                <div class="p-4 grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Pilgrim Full Name *</label>
                        <input type="text" name="pilgrimName1" id="pilgrimName1" placeholder="Full Name as in ID Proof" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Age *</label>
                        <input type="number" name="age1" id="age1" placeholder="Age" min="1" max="110" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Gender *</label>
                        <select name="gender1" id="gender1" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none bg-white">
                            <option value="">Select Gender</option>
                            <option value="Male">Male</option>
                            <option value="Female">Female</option>
                            <option value="Transgender">Transgender</option>
                        </select>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Photo ID Proof *</label>
                        <select name="idProofType1" id="idProofType1" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none bg-white">
                            <option value="">Select ID Proof</option>
                            <option value="Aadhaar">Aadhaar Card</option>
                            <option value="Passport">Passport</option>
                            <option value="Voter ID">Voter ID</option>
                        </select>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Photo ID Card Number *</label>
                        <input type="text" name="idNumber1" id="idNumber1" placeholder="Enter ID Proof Number" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none">
                    </div>
                </div>
            </div>

            <!-- Contact Information -->
            <div class="bg-white rounded-lg border border-slate-300 shadow-sm overflow-hidden">
                <div class="bg-slate-100 px-4 py-2.5 border-b border-slate-200 font-bold text-slate-700 text-sm">
                    3. Contact Details
                </div>
                <div class="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Mobile Number (for SMS confirmation) *</label>
                        <input type="tel" name="mobileNumber" id="mobileNumber" placeholder="10-digit mobile number" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Email ID (for e-Darshan ticket) *</label>
                        <input type="email" name="emailId" id="emailId" placeholder="name@example.com" class="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:border-amber-600 focus:outline-none">
                    </div>
                </div>
            </div>

            <div class="flex justify-end space-x-3 pt-2">
                <button type="reset" class="bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold px-4 py-2 rounded text-sm">Clear Form</button>
                <button type="submit" class="bg-amber-600 hover:bg-amber-700 text-white font-bold px-6 py-2 rounded text-sm shadow">Proceed to Payment &rarr;</button>
            </div>
        </form>
    </main>

    <footer class="bg-slate-800 text-slate-400 text-xs py-4 text-center border-t border-slate-700">
        TTD Darshan Booking Simulation Engine &bull; Connected to SRIVANI Booking Manager Local Host
    </footer>

    <script>
        function launchCompanion() {
            var s = document.createElement('script');
            s.src = '/api/autofill.js?t=' + Date.now();
            document.body.appendChild(s);
        }
    </script>
</body>
</html>
"""

# Configure Jinja template loader
app.jinja_loader = jinja2.DictLoader({
    "base.html": BASE_TEMPLATE,
    "dashboard.html": DASHBOARD_TEMPLATE,
    "queue.html": QUEUE_TEMPLATE,
    "analytics.html": ANALYTICS_TEMPLATE,
    "reports.html": REPORTS_TEMPLATE,
    "demo_ttd.html": DEMO_TTD_TEMPLATE,
})

# -----------------------------------------------------------------------------
# Page Views
# -----------------------------------------------------------------------------

@app.route("/demo-ttd-booking")
def demo_ttd_booking_view():
    return render_template("demo_ttd.html")

@app.route("/")
def dashboard_view():
    stats = get_stats()
    families = get_all_families(sort_by="queue")
    
    families_with_pilgrims = []
    for f in families:
        f_dict = dict(f)
        p_list = get_family_pilgrims(f["id"])
        f_dict["pilgrim_count"] = len(p_list)
        f_dict["pilgrims"] = [dict(p) for p in p_list]
        families_with_pilgrims.append(f_dict)

    return render_template(
        "dashboard.html",
        title="Dashboard",
        active_page="dashboard",
        stats=stats,
        families=families_with_pilgrims,
    )


@app.route("/queue")
def queue_view():
    families = get_all_families(sort_by="queue")
    families_with_pilgrims = []
    for f in families:
        f_dict = dict(f)
        p_list = get_family_pilgrims(f["id"])
        f_dict["pilgrim_count"] = len(p_list)
        f_dict["pilgrims"] = [dict(p) for p in p_list]
        families_with_pilgrims.append(f_dict)

    return render_template(
        "queue.html",
        title="Queue Assistant",
        active_page="queue",
        families=families_with_pilgrims,
    )


@app.route("/analytics")
def analytics_view():
    summary = get_analytics_summary()
    perf = get_booking_performance()
    queue_intel = get_queue_intelligence()
    pay_intel = get_payment_analytics()
    doc_intel = get_document_analytics()
    op_intel = get_operational_intelligence()

    return render_template(
        "analytics.html",
        title="Analytics",
        active_page="analytics",
        summary=summary,
        perf=perf,
        queue_intel=queue_intel,
        pay_intel=pay_intel,
        doc_intel=doc_intel,
        op_intel=op_intel,
    )


@app.route("/reports")
def reports_view():
    reconciliation = validate_report_totals()
    status_summary = get_booking_status_summary_report()

    return render_template(
        "reports.html",
        title="Reports",
        active_page="reports",
        reconciliation=reconciliation,
        status_summary=status_summary,
    )

# -----------------------------------------------------------------------------
# REST API Endpoints
# -----------------------------------------------------------------------------

@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())

@app.route("/api/families")
def api_families():
    sort_by = request.args.get("sort_by", "queue")
    families = get_all_families(sort_by=sort_by)
    res = []
    for f in families:
        f_dict = dict(f)
        f_dict["pilgrims"] = [dict(p) for p in get_family_pilgrims(f["id"])]
        res.append(f_dict)
    return jsonify({"count": len(res), "families": res})

@app.route("/api/family/<int:family_id>")
def api_family(family_id):
    fam = get_family(family_id)
    if not fam:
        return jsonify({"error": "Not found"}), 404
    f_dict = dict(fam)
    f_dict["pilgrims"] = [dict(p) for p in get_family_pilgrims(family_id)]
    f_dict["history"] = [dict(h) for h in get_queue_history(family_id)]
    return jsonify(f_dict)

@app.route("/api/family/update_status", methods=["POST"])
def api_update_status():
    if request.is_json:
        data = request.get_json(silent=True) or {}
        fid = data.get("family_id")
        status = data.get("status")
        payment_status = data.get("payment_status")
        payment_ref = data.get("payment_ref")
        notes = data.get("notes")
    else:
        fid = request.form.get("family_id", type=int)
        status = request.form.get("status")
        payment_status = request.form.get("payment_status")
        payment_ref = request.form.get("payment_ref")
        notes = request.form.get("notes")

    if fid and status:
        if not payment_status:
            fam = get_family(fid)
            payment_status = fam["payment_status"] if fam else "Not requested"
        update_status_and_payment(fid, status, payment_status, notes=notes, payment_ref=payment_ref)
        if request.is_json:
            return jsonify({"status": "ok", "family_id": fid})
    
    referrer = request.referrer or "/queue"
    return redirect(referrer)

@app.route("/api/autofill.js")
def api_autofill_js():
    js_path = Path(__file__).resolve().parent / "static" / "autofill.js"
    if js_path.exists():
        content = js_path.read_text(encoding="utf-8")
    else:
        content = "// autofill script not found"
    return Response(content, mimetype="application/javascript")

@app.route("/api/analytics")
def api_analytics():
    return jsonify({
        "summary": get_analytics_summary(),
        "performance": get_booking_performance(),
        "queue_intelligence": get_queue_intelligence(),
        "payment_analytics": get_payment_analytics(),
        "document_analytics": get_document_analytics(),
        "operational_intelligence": get_operational_intelligence(),
    })

# -----------------------------------------------------------------------------
# Export Downloads
# -----------------------------------------------------------------------------

@app.route("/api/export/excel")
def api_export_excel():
    temp_p = Path(config.DATA_DIR) / f"srivani_export_{datetime.datetime.now():%Y%m%d_%H%M%S}.xlsx"
    export_to_excel(temp_p)
    return send_file(temp_p, as_attachment=True, download_name="Srivani_Bookings.xlsx")

@app.route("/api/export/csv")
def api_export_csv():
    temp_p = Path(config.DATA_DIR) / f"srivani_export_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv"
    export_to_csv(temp_p)
    return send_file(temp_p, as_attachment=True, download_name="Srivani_Bookings.csv")

@app.route("/api/export/analytics-xlsx")
def api_export_analytics_xlsx():
    temp_p = Path(config.DATA_DIR) / f"srivani_analytics_{datetime.datetime.now():%Y%m%d_%H%M%S}.xlsx"
    export_full_analytics_workbook_xlsx(temp_p)
    return send_file(temp_p, as_attachment=True, download_name="Srivani_Analytics_Workbook.xlsx")

@app.route("/api/export/analytics-pdf")
def api_export_analytics_pdf():
    temp_p = Path(config.DATA_DIR) / f"srivani_analytics_report_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf"
    export_analytics_report_pdf("summary", temp_p)
    return send_file(temp_p, as_attachment=True, download_name="Srivani_Analytics_Report.pdf")

@app.route("/api/export/report-pdf")
def api_export_report_pdf():
    rep_type = request.args.get("type", "booking_status_summary")
    temp_p = Path(config.DATA_DIR) / f"srivani_report_{rep_type}_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf"
    generate_printable_pdf_report(rep_type, temp_p)
    return send_file(temp_p, as_attachment=True, download_name=f"Srivani_Report_{rep_type}.pdf")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\n==================================================================")
    print(f"  SRIVANI BOOKING MANAGER — LOCAL WEB PORTAL & REST API SERVER")
    print(f"==================================================================")
    print(f"  Web Dashboard:    http://localhost:{port}")
    print(f"  Queue Assistant:  http://localhost:{port}/queue")
    print(f"  Analytics:        http://localhost:{port}/analytics")
    print(f"  Reports:          http://localhost:{port}/reports")
    print(f"  REST API:         http://localhost:{port}/api/families")
    print(f"  Official Portal:  https://ttdevasthanams.ap.gov.in")
    print(f"==================================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
