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
import uuid
import json
from dataset_importer import (
    read_dataset_file,
    detect_column_mapping,
    validate_and_analyze_dataset,
    execute_dataset_import,
    ALL_TARGET_FIELDS,
    TARGET_FAMILY_FIELDS,
    TARGET_PILGRIM_FIELDS,
    DUP_POLICY_SKIP,
    DUP_POLICY_UPDATE,
    DUP_POLICY_CANCEL,
)
from backup_manager import create_database_backup

UPLOAD_SESSIONS = {}
TEMP_UPLOADS_DIR = Path(config.DATA_DIR) / "temp_imports"
TEMP_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

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
                <!-- 📥 Upload Dataset Action Button -->
                <button onclick="triggerDatasetUpload()" id="btn-upload-dataset" title="Upload CSV or Excel dataset (.csv, .xlsx)" class="bg-amber-600 hover:bg-amber-500 active:bg-amber-700 text-white border border-amber-400/40 px-3.5 py-1.5 rounded-md text-xs font-bold flex items-center shadow-md transition duration-150 cursor-pointer">
                    <i class="fa-solid fa-cloud-arrow-up mr-1.5 text-sm"></i> 📥 Upload Dataset
                </button>

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

    <!-- Hidden OS File Input for Dataset Upload -->
    <input type="file" id="global-dataset-file-input" accept=".csv, .xlsx, .xls" class="hidden" onchange="handleDatasetFileSelected(this)">

    <!-- Modern Dataset Upload & Ingestion Modal -->
    <div id="dataset-upload-modal" class="hidden fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 overflow-y-auto">
        <div class="bg-slate-800 border border-amber-500/50 rounded-xl max-w-5xl w-full p-6 shadow-2xl relative text-slate-200 max-h-[92vh] flex flex-col">
            <!-- Modal Header -->
            <div class="flex items-center justify-between border-b border-slate-700 pb-3 mb-4">
                <div class="flex items-center space-x-3">
                    <div class="bg-amber-600 text-white w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold shadow">
                        <i class="fa-solid fa-cloud-arrow-up"></i>
                    </div>
                    <div>
                        <h2 class="text-lg font-bold text-white tracking-tight">📥 Upload Dataset — Devotee Ingestion Wizard</h2>
                        <p class="text-xs text-slate-400">Universal CSV & Excel Ingestion &bull; Dynamic Column Mapping &bull; Strict Validation &bull; Zero Duplicates</p>
                    </div>
                </div>
                <button onclick="closeDatasetUploadModal()" class="text-slate-400 hover:text-white text-2xl font-bold cursor-pointer">
                    &times;
                </button>
            </div>

            <!-- Modal Body (Scrollable) -->
            <div class="flex-grow overflow-y-auto pr-2 space-y-4 text-xs">
                <!-- 1. File Selection & Progress Card -->
                <div class="bg-slate-900 border border-slate-700 rounded-lg p-4">
                    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-3">
                        <div class="flex flex-wrap items-center gap-2">
                            <span class="text-slate-400 font-semibold text-xs">Selected File:</span>
                            <span id="upload-filename-display" class="font-bold text-amber-300 text-sm">None</span>
                            <span id="upload-filesize-display" class="text-slate-400 text-xs">(0 KB)</span>
                            <span id="upload-format-display" class="bg-slate-800 text-sky-400 border border-slate-700 text-2xs px-2 py-0.5 rounded font-mono uppercase">CSV/Excel</span>
                        </div>
                        <div class="flex items-center space-x-2">
                            <button onclick="triggerDatasetUpload()" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 px-3 py-1 rounded text-xs transition cursor-pointer">
                                <i class="fa-solid fa-folder-open mr-1"></i> Choose Other File
                            </button>
                            <button onclick="closeDatasetUploadModal()" class="bg-slate-800 hover:bg-rose-900/40 text-slate-300 hover:text-rose-300 border border-slate-600 px-3 py-1 rounded text-xs transition cursor-pointer">
                                <i class="fa-solid fa-xmark mr-1"></i> Cancel
                            </button>
                        </div>
                    </div>

                    <!-- Upload Progress Bar -->
                    <div id="upload-progress-container" class="space-y-1.5">
                        <div class="flex justify-between text-2xs font-semibold">
                            <span id="upload-progress-status" class="text-amber-400">Uploading dataset...</span>
                            <span id="upload-progress-percent" class="text-slate-300">0%</span>
                        </div>
                        <div class="w-full bg-slate-950 rounded-full h-2.5 overflow-hidden border border-slate-800">
                            <div id="upload-progress-bar" class="bg-gradient-to-r from-amber-500 to-emerald-500 h-2.5 rounded-full transition-all duration-300" style="width: 0%"></div>
                        </div>
                    </div>

                    <!-- Error Alert Box -->
                    <div id="upload-error-alert" class="hidden mt-3 p-3 bg-rose-950/70 border border-rose-700 rounded text-rose-200 text-xs">
                        <i class="fa-solid fa-triangle-exclamation mr-1.5 text-rose-400"></i>
                        <span id="upload-error-message"></span>
                    </div>
                </div>

                <!-- 2. Tabs: Data Preview, Column Mapping, Validation & Errors, Summary & Options -->
                <div id="upload-workbench" class="hidden space-y-3">
                    <!-- Tab Buttons -->
                    <div class="flex border-b border-slate-700 space-x-2">
                        <button onclick="switchUploadTab('preview')" id="tab-btn-preview" class="px-4 py-2 text-xs font-bold border-b-2 border-amber-500 text-amber-400 cursor-pointer">
                            <i class="fa-solid fa-table mr-1.5"></i> Data Preview
                        </button>
                        <button onclick="switchUploadTab('mapping')" id="tab-btn-mapping" class="px-4 py-2 text-xs font-bold border-b-2 border-transparent text-slate-400 hover:text-white cursor-pointer">
                            <i class="fa-solid fa-network-wired mr-1.5"></i> Column Mapping
                        </button>
                        <button onclick="switchUploadTab('errors')" id="tab-btn-errors" class="px-4 py-2 text-xs font-bold border-b-2 border-transparent text-slate-400 hover:text-white cursor-pointer">
                            <i class="fa-solid fa-circle-exclamation mr-1.5"></i> Validation Errors (<span id="tab-error-count">0</span>)
                        </button>
                        <button onclick="switchUploadTab('summary')" id="tab-btn-summary" class="px-4 py-2 text-xs font-bold border-b-2 border-transparent text-slate-400 hover:text-white cursor-pointer">
                            <i class="fa-solid fa-sliders mr-1.5"></i> Import Options & Summary
                        </button>
                    </div>

                    <!-- Content 1: Data Preview Table -->
                    <div id="tab-content-preview" class="space-y-2">
                        <div class="text-slate-400 text-2xs flex justify-between items-center">
                            <span>Showing first 50 rows of uploaded dataset with horizontal scrolling:</span>
                            <span id="preview-row-count" class="font-bold text-slate-300">0 rows</span>
                        </div>
                        <div class="overflow-x-auto max-h-64 border border-slate-700 rounded-lg bg-slate-950">
                            <table class="w-full text-left text-2xs text-slate-300 whitespace-nowrap">
                                <thead id="preview-table-head" class="bg-slate-900 text-slate-400 sticky top-0 uppercase border-b border-slate-700"></thead>
                                <tbody id="preview-table-body" class="divide-y divide-slate-800"></tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Content 2: Column Mapping -->
                    <div id="tab-content-mapping" class="hidden space-y-2">
                        <p class="text-slate-400 text-2xs">Match spreadsheet headers to SRIVANI database fields. Unmatched columns are marked in amber:</p>
                        <div id="mapping-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-64 overflow-y-auto p-1"></div>
                    </div>

                    <!-- Content 3: Validation Errors -->
                    <div id="tab-content-errors" class="hidden space-y-2">
                        <div class="flex justify-between items-center">
                            <span id="validation-errors-status" class="text-slate-300 text-xs font-semibold"></span>
                            <button onclick="downloadValidationErrorsCSV()" id="btn-export-errors-csv" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1 rounded text-2xs cursor-pointer">
                                <i class="fa-solid fa-file-csv mr-1"></i> Export Error Report
                            </button>
                        </div>
                        <div class="overflow-x-auto max-h-64 border border-slate-700 rounded-lg bg-slate-950">
                            <table class="w-full text-left text-2xs text-slate-300">
                                <thead class="bg-slate-900 text-slate-400 sticky top-0 uppercase border-b border-slate-700">
                                    <tr>
                                        <th class="px-3 py-2 w-16">Row #</th>
                                        <th class="px-3 py-2 w-32">Column</th>
                                        <th class="px-3 py-2 w-32">Value</th>
                                        <th class="px-3 py-2">Error Description</th>
                                    </tr>
                                </thead>
                                <tbody id="errors-table-body" class="divide-y divide-slate-800"></tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Content 4: Summary & Options -->
                    <div id="tab-content-summary" class="hidden space-y-4">
                        <!-- 7 Summary Cards -->
                        <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 text-center">
                            <div class="bg-slate-900 border border-slate-700 p-2.5 rounded">
                                <span class="text-3xs font-semibold uppercase text-slate-400">Total Rows</span>
                                <div id="sum-total-rows" class="text-base font-bold text-white mt-0.5">0</div>
                            </div>
                            <div class="bg-slate-900 border border-slate-700 p-2.5 rounded">
                                <span class="text-3xs font-semibold uppercase text-emerald-400">Valid</span>
                                <div id="sum-valid-rows" class="text-base font-bold text-emerald-400 mt-0.5">0</div>
                            </div>
                            <div class="bg-slate-900 border border-slate-700 p-2.5 rounded">
                                <span class="text-3xs font-semibold uppercase text-rose-400">Invalid</span>
                                <div id="sum-invalid-rows" class="text-base font-bold text-rose-400 mt-0.5">0</div>
                            </div>
                            <div class="bg-slate-900 border border-slate-700 p-2.5 rounded">
                                <span class="text-3xs font-semibold uppercase text-sky-400">New Fams</span>
                                <div id="sum-new-families" class="text-base font-bold text-sky-400 mt-0.5">0</div>
                            </div>
                            <div class="bg-slate-900 border border-slate-700 p-2.5 rounded">
                                <span class="text-3xs font-semibold uppercase text-indigo-400">New Devotees</span>
                                <div id="sum-new-pilgrims" class="text-base font-bold text-indigo-400 mt-0.5">0</div>
                            </div>
                            <div class="bg-slate-900 border border-slate-700 p-2.5 rounded">
                                <span class="text-3xs font-semibold uppercase text-amber-400">Duplicates</span>
                                <div id="sum-duplicate-rows" class="text-base font-bold text-amber-400 mt-0.5">0</div>
                            </div>
                            <div class="bg-slate-900 border border-slate-700 p-2.5 rounded">
                                <span class="text-3xs font-semibold uppercase text-slate-400">Skipped</span>
                                <div id="sum-skipped-rows" class="text-base font-bold text-slate-400 mt-0.5">0</div>
                            </div>
                        </div>

                        <!-- Duplicate Policy Box -->
                        <div class="bg-slate-900 border border-slate-700 rounded-lg p-3.5 space-y-2">
                            <span class="font-bold text-slate-200 text-xs block mb-1">
                                <i class="fa-solid fa-copy text-amber-400 mr-1.5"></i> Duplicate Record Handling Policy:
                            </span>
                            <label class="flex items-start space-x-2.5 cursor-pointer">
                                <input type="radio" name="dup_policy" value="SKIP" checked onchange="onDuplicatePolicyChanged()" class="mt-0.5 text-amber-600 focus:ring-amber-500">
                                <div>
                                    <span class="font-semibold text-white text-xs">Skip duplicate records (Recommended)</span>
                                    <p class="text-2xs text-slate-400">Preserves existing records. When importing pilgrims belonging to an existing family, reuses the family ID without creating duplicate families.</p>
                                </div>
                            </label>
                            <label class="flex items-start space-x-2.5 cursor-pointer">
                                <input type="radio" name="dup_policy" value="UPDATE" onchange="onDuplicatePolicyChanged()" class="mt-0.5 text-amber-600 focus:ring-amber-500">
                                <div>
                                    <span class="font-semibold text-white text-xs">Update existing records</span>
                                    <p class="text-2xs text-slate-400">Updates existing family and devotee records with new information after confirmation.</p>
                                </div>
                            </label>
                            <label class="flex items-start space-x-2.5 cursor-pointer">
                                <input type="radio" name="dup_policy" value="CANCEL" onchange="onDuplicatePolicyChanged()" class="mt-0.5 text-amber-600 focus:ring-amber-500">
                                <div>
                                    <span class="font-semibold text-white text-xs">Cancel import if duplicates found</span>
                                    <p class="text-2xs text-slate-400">Strict zero-tolerance policy; aborts entire transaction if any duplicate is found.</p>
                                </div>
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Modal Sticky Footer -->
            <div class="border-t border-slate-700 pt-3 mt-3 flex flex-col sm:flex-row justify-between items-center gap-3">
                <div id="modal-bottom-status" class="text-xs font-semibold text-slate-300">
                    Ready to validate records.
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="closeDatasetUploadModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded text-xs font-semibold transition cursor-pointer">
                        Cancel
                    </button>
                    <button onclick="confirmAndCommitImport()" id="btn-confirm-import" disabled class="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 py-2 rounded text-xs font-bold flex items-center shadow-lg transition cursor-pointer">
                        <i class="fa-solid fa-check-double mr-1.5"></i> Confirm & Import Dataset
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Dataset Upload Client-Side Controller Script -->
    <script>
    var currentUploadData = null;

    function triggerDatasetUpload() {
        var input = document.getElementById('global-dataset-file-input');
        input.value = '';
        input.click();
    }

    function closeDatasetUploadModal() {
        document.getElementById('dataset-upload-modal').classList.add('hidden');
    }

    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        var k = 1024;
        var sizes = ['B', 'KB', 'MB', 'GB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function handleDatasetFileSelected(input) {
        if (!input.files || input.files.length === 0) return;
        var file = input.files[0];

        var modal = document.getElementById('dataset-upload-modal');
        modal.classList.remove('hidden');

        document.getElementById('upload-filename-display').innerText = file.name;
        document.getElementById('upload-filesize-display').innerText = '(' + formatBytes(file.size) + ')';
        var ext = file.name.split('.').pop().toUpperCase();
        document.getElementById('upload-format-display').innerText = ext;

        document.getElementById('upload-error-alert').classList.add('hidden');
        document.getElementById('upload-workbench').classList.add('hidden');
        document.getElementById('upload-progress-container').classList.remove('hidden');
        document.getElementById('btn-confirm-import').disabled = true;

        var formData = new FormData();
        formData.append('file', file);

        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/dataset/parse', true);

        xhr.upload.onprogress = function(e) {
            if (e.lengthComputable) {
                var pct = Math.round((e.loaded / e.total) * 90);
                document.getElementById('upload-progress-bar').style.width = pct + '%';
                document.getElementById('upload-progress-percent').innerText = pct + '%';
                document.getElementById('upload-progress-status').innerText = 'Uploading dataset (' + pct + '%)...';
            }
        };

        xhr.onload = function() {
            if (xhr.status === 200) {
                try {
                    var resp = JSON.parse(xhr.responseText);
                    if (resp.success) {
                        document.getElementById('upload-progress-bar').style.width = '100%';
                        document.getElementById('upload-progress-percent').innerText = '100%';
                        document.getElementById('upload-progress-status').innerText = 'Dataset parsed and validated!';
                        currentUploadData = resp;
                        renderUploadWorkbench(resp);
                    } else {
                        showUploadError(resp.error || 'Failed to parse dataset.');
                    }
                } catch(e) {
                    showUploadError('Error parsing server response: ' + e);
                }
            } else {
                try {
                    var errResp = JSON.parse(xhr.responseText);
                    showUploadError(errResp.error || ('Upload failed with status ' + xhr.status));
                } catch(e) {
                    showUploadError('Upload failed with status ' + xhr.status);
                }
            }
        };

        xhr.onerror = function() {
            showUploadError('Network error while uploading dataset file.');
        };

        xhr.send(formData);
    }

    function showUploadError(msg) {
        document.getElementById('upload-progress-container').classList.add('hidden');
        var alertBox = document.getElementById('upload-error-alert');
        alertBox.classList.remove('hidden');
        document.getElementById('upload-error-message').innerText = msg;
        document.getElementById('modal-bottom-status').innerText = 'Error: ' + msg;
    }

    function switchUploadTab(tabName) {
        ['preview', 'mapping', 'errors', 'summary'].forEach(function(t) {
            document.getElementById('tab-content-' + t).classList.add('hidden');
            var btn = document.getElementById('tab-btn-' + t);
            btn.className = 'px-4 py-2 text-xs font-bold border-b-2 border-transparent text-slate-400 hover:text-white cursor-pointer';
        });
        document.getElementById('tab-content-' + tabName).classList.remove('hidden');
        var activeBtn = document.getElementById('tab-btn-' + tabName);
        activeBtn.className = 'px-4 py-2 text-xs font-bold border-b-2 border-amber-500 text-amber-400 cursor-pointer';
    }

    function renderUploadWorkbench(data) {
        document.getElementById('upload-workbench').classList.remove('hidden');

        // 1. Data Preview Table
        renderPreviewTable(data.headers, data.preview_rows, data.mapping);

        // 2. Column Mapping Grid
        renderMappingGrid(data.headers, data.mapping, data.target_fields);

        // 3. Validation Errors Table
        renderValidationErrors(data.errors || []);

        // 4. Summary Badges
        updateSummaryMetrics(data.summary || {});

        // 5. Update bottom status & confirm button
        var valid = (data.summary && data.summary.valid_records) ? data.summary.valid_records : 0;
        var invalid = (data.summary && data.summary.invalid_records) ? data.summary.invalid_records : 0;
        var tot = (data.summary && data.summary.total_rows) ? data.summary.total_rows : 0;
        document.getElementById('modal-bottom-status').innerText = '📊 Total: ' + tot + ' | ✅ Valid: ' + valid + ' | ⚠️ Invalid: ' + invalid;

        document.getElementById('btn-confirm-import').disabled = (valid <= 0);
        switchUploadTab('preview');
    }

    function renderPreviewTable(headers, rows, mapping) {
        var headTr = '<tr>';
        headTr += '<th class="px-3 py-2 bg-slate-900 border-r border-slate-800 text-amber-400">Row #</th>';
        headTr += '<th class="px-3 py-2 bg-slate-900 border-r border-slate-800">Family ID</th>';
        headTr += '<th class="px-3 py-2 bg-slate-900 border-r border-slate-800">Family Name</th>';
        headTr += '<th class="px-3 py-2 bg-slate-900 border-r border-slate-800">Pilgrim Name</th>';
        headTr += '<th class="px-3 py-2 bg-slate-900 border-r border-slate-800">Age</th>';
        headTr += '<th class="px-3 py-2 bg-slate-900 border-r border-slate-800">Gender</th>';
        headTr += '<th class="px-3 py-2 bg-slate-900 border-r border-slate-800">Mobile Number</th>';

        // Find non-core headers
        var coreTargets = ['family_code', 'family_name', 'full_name', 'age', 'gender', 'phone'];
        var targetToHdr = {};
        for (var h in mapping) {
            var t = mapping[h];
            if (t && !targetToHdr[t]) targetToHdr[t] = h;
        }

        var coreHdrsSet = {};
        coreTargets.forEach(function(k) { if (targetToHdr[k]) coreHdrsSet[targetToHdr[k]] = true; });
        var otherHdrs = headers.filter(function(h) { return !coreHdrsSet[h]; });

        otherHdrs.forEach(function(h) {
            headTr += '<th class="px-3 py-2 bg-slate-900 border-r border-slate-800">' + escapeHtml(h) + '</th>';
        });
        headTr += '</tr>';
        document.getElementById('preview-table-head').innerHTML = headTr;

        var bodyHtml = '';
        var fIdHdr = targetToHdr['family_code'];
        var fNameHdr = targetToHdr['family_name'];
        var pNameHdr = targetToHdr['full_name'];
        var ageHdr = targetToHdr['age'];
        var genHdr = targetToHdr['gender'];
        var phoneHdr = targetToHdr['phone'];

        rows.forEach(function(r, idx) {
            var rowNum = r['_row_num'] || (idx + 1);
            var famId = fIdHdr ? (r[fIdHdr] || '') : '';
            var famName = fNameHdr ? (r[fNameHdr] || '') : '';
            var pilName = pNameHdr ? (r[pNameHdr] || '') : '';
            var age = ageHdr ? (r[ageHdr] || '') : '';
            var gen = genHdr ? (r[genHdr] || '') : '';
            var phone = phoneHdr ? (r[phoneHdr] || '') : '';

            if (!famName && pilName) famName = pilName + ' Family';

            bodyHtml += '<tr class="hover:bg-slate-800/60">';
            bodyHtml += '<td class="px-3 py-1.5 font-mono text-amber-400 font-bold border-r border-slate-800">' + rowNum + '</td>';
            bodyHtml += '<td class="px-3 py-1.5 font-mono text-slate-300 border-r border-slate-800">' + escapeHtml(famId) + '</td>';
            bodyHtml += '<td class="px-3 py-1.5 font-semibold text-white border-r border-slate-800">' + escapeHtml(famName) + '</td>';
            bodyHtml += '<td class="px-3 py-1.5 text-slate-200 border-r border-slate-800">' + escapeHtml(pilName) + '</td>';
            bodyHtml += '<td class="px-3 py-1.5 text-center border-r border-slate-800">' + escapeHtml(age) + '</td>';
            bodyHtml += '<td class="px-3 py-1.5 text-center border-r border-slate-800">' + escapeHtml(gen) + '</td>';
            bodyHtml += '<td class="px-3 py-1.5 font-mono border-r border-slate-800">' + escapeHtml(phone) + '</td>';

            otherHdrs.forEach(function(h) {
                bodyHtml += '<td class="px-3 py-1.5 text-slate-400 border-r border-slate-800">' + escapeHtml(r[h] || '') + '</td>';
            });
            bodyHtml += '</tr>';
        });

        document.getElementById('preview-table-body').innerHTML = bodyHtml;
        document.getElementById('preview-row-count').innerText = rows.length + ' rows previewed';
    }

    function renderMappingGrid(headers, mapping, targetFields) {
        var grid = document.getElementById('mapping-grid');
        grid.innerHTML = '';

        headers.forEach(function(h) {
            var currentTarget = mapping[h] || '';
            var isMatched = Boolean(currentTarget);

            var cell = document.createElement('div');
            cell.className = 'bg-slate-900 border border-slate-800 p-2.5 rounded-lg flex flex-col justify-between space-y-1.5';

            var topRow = document.createElement('div');
            topRow.className = 'flex items-center justify-between';

            var lbl = document.createElement('span');
            lbl.className = 'font-bold text-slate-200 text-xs truncate';
            lbl.title = h;
            lbl.innerText = h.length > 20 ? (h.substring(0, 18) + '...') : h;
            topRow.appendChild(lbl);

            var badge = document.createElement('span');
            badge.id = 'mapping-badge-' + sanitizeId(h);
            badge.className = isMatched
                ? 'text-3xs font-semibold px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800'
                : 'text-3xs font-semibold px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800';
            badge.innerText = isMatched ? 'Matched' : 'Unmatched';
            topRow.appendChild(badge);
            cell.appendChild(topRow);

            var sel = document.createElement('select');
            sel.className = 'bg-slate-950 border border-slate-700 text-slate-200 text-2xs rounded px-2 py-1 outline-none w-full focus:border-amber-500';

            var optSkip = document.createElement('option');
            optSkip.value = '';
            optSkip.innerText = '-- Unmatched / Skip --';
            sel.appendChild(optSkip);

            targetFields.forEach(function(t) {
                var opt = document.createElement('option');
                opt.value = t[0];
                opt.innerText = t[0] + ' (' + t[1] + ')';
                if (t[0] === currentTarget) opt.selected = true;
                sel.appendChild(opt);
            });

            sel.onchange = function() {
                onColumnMappingChanged(h, sel.value);
            };

            cell.appendChild(sel);
            grid.appendChild(cell);
        });
    }

    function sanitizeId(str) {
        return str.replace(/[^a-zA-Z0-9]/g, '_');
    }

    function onColumnMappingChanged(header, newTarget) {
        if (!currentUploadData) return;
        currentUploadData.mapping[header] = newTarget || null;

        var badge = document.getElementById('mapping-badge-' + sanitizeId(header));
        if (badge) {
            if (newTarget) {
                badge.className = 'text-3xs font-semibold px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800';
                badge.innerText = 'Matched';
            } else {
                badge.className = 'text-3xs font-semibold px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800';
                badge.innerText = 'Unmatched';
            }
        }

        revalidateCurrentUpload();
    }

    function onDuplicatePolicyChanged() {
        revalidateCurrentUpload();
    }

    function getSelectedDupPolicy() {
        var radios = document.getElementsByName('dup_policy');
        for (var i = 0; i < radios.length; i++) {
            if (radios[i].checked) return radios[i].value;
        }
        return 'SKIP';
    }

    function revalidateCurrentUpload() {
        if (!currentUploadData) return;
        var policy = getSelectedDupPolicy();

        fetch('/api/dataset/revalidate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                token: currentUploadData.token,
                mapping: currentUploadData.mapping,
                dup_policy: policy
            })
        })
        .then(function(r) { return r.json(); })
        .then(function(res) {
            if (res.success) {
                currentUploadData.summary = res.summary;
                currentUploadData.errors = res.errors;
                updateSummaryMetrics(res.summary);
                renderValidationErrors(res.errors || []);
                renderPreviewTable(currentUploadData.headers, currentUploadData.preview_rows, currentUploadData.mapping);

                var valid = res.summary.valid_records || 0;
                var invalid = res.summary.invalid_records || 0;
                var tot = res.summary.total_rows || 0;
                document.getElementById('modal-bottom-status').innerText = '📊 Total: ' + tot + ' | ✅ Valid: ' + valid + ' | ⚠️ Invalid: ' + invalid;
                document.getElementById('btn-confirm-import').disabled = (valid <= 0);
            }
        })
        .catch(function(err) {
            console.error('Re-validation error:', err);
        });
    }

    function renderValidationErrors(errors) {
        document.getElementById('tab-error-count').innerText = errors.length;
        var tbody = document.getElementById('errors-table-body');
        tbody.innerHTML = '';

        if (!errors || errors.length === 0) {
            document.getElementById('validation-errors-status').innerText = '✅ Zero errors found. All records meet strict data quality rules.';
            document.getElementById('validation-errors-status').className = 'text-emerald-400 text-xs font-semibold';
            tbody.innerHTML = '<tr><td colspan="4" class="px-4 py-6 text-center text-slate-500">No validation errors detected.</td></tr>';
            return;
        }

        document.getElementById('validation-errors-status').innerText = '⚠️ ' + errors.length + ' error(s) flagged:';
        document.getElementById('validation-errors-status').className = 'text-rose-400 text-xs font-semibold';

        errors.forEach(function(e) {
            var tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-800/60';
            tr.innerHTML = '<td class="px-3 py-2 font-mono text-amber-400 font-bold">' + (e.row || '') + '</td>' +
                           '<td class="px-3 py-2 text-slate-300 font-semibold">' + escapeHtml(e.column || '') + '</td>' +
                           '<td class="px-3 py-2 font-mono text-rose-300">' + escapeHtml(e.value || '') + '</td>' +
                           '<td class="px-3 py-2 text-slate-200">' + escapeHtml(e.error || '') + '</td>';
            tbody.appendChild(tr);
        });
    }

    function updateSummaryMetrics(s) {
        document.getElementById('sum-total-rows').innerText = s.total_rows || 0;
        document.getElementById('sum-valid-rows').innerText = s.valid_records || 0;
        document.getElementById('sum-invalid-rows').innerText = s.invalid_records || 0;
        document.getElementById('sum-new-families').innerText = s.new_families || 0;
        document.getElementById('sum-new-pilgrims').innerText = s.new_pilgrims || 0;
        document.getElementById('sum-duplicate-rows').innerText = s.duplicate_records || 0;
        document.getElementById('sum-skipped-rows').innerText = s.records_to_skip || 0;
    }

    function confirmAndCommitImport() {
        if (!currentUploadData || !currentUploadData.summary) return;
        var s = currentUploadData.summary;
        var policy = getSelectedDupPolicy();

        if (policy === 'UPDATE') {
            if (!confirm('⚠️ Update Policy Selected:\\nExisting database records will be updated with new data.\\n\\nDo you want to proceed?')) {
                return;
            }
        }

        var confirmMsg = '📋 Confirm Dataset Import:\\n\\n' +
                         '• Total Rows: ' + s.total_rows + '\\n' +
                         '• Valid Records to Commit: ' + s.valid_records + '\\n' +
                         '• Rejected Invalid Rows: ' + s.invalid_records + '\\n' +
                         '• New Families to Create: ' + s.new_families + '\\n' +
                         '• New Pilgrims to Link: ' + s.new_pilgrims + '\\n' +
                         '• Duplicate Policy: ' + policy + '\\n\\n' +
                         'An automatic SQLite database backup will be created before committing.\\n' +
                         'Proceed with committing to database?';

        if (!confirm(confirmMsg)) return;

        var btn = document.getElementById('btn-confirm-import');
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Committing...';

        fetch('/api/dataset/commit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                token: currentUploadData.token,
                mapping: currentUploadData.mapping,
                dup_policy: policy
            })
        })
        .then(function(r) { return r.json(); })
        .then(function(res) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-check-double mr-1.5"></i> Confirm & Import Dataset';

            if (res.success) {
                alert('✅ ' + (res.message || 'Dataset imported successfully!') + '\\n\\n' +
                      '• Records Imported: ' + (res.successful_records || s.valid_records) + '\\n' +
                      '• Batch ID: ' + (res.batch_id || 'N/A') + '\\n\\n' +
                      'Dashboard statistics will now refresh.');
                closeDatasetUploadModal();
                window.location.reload();
            } else {
                alert('❌ Import Failed:\\n' + (res.error || 'Unknown database error occurred.'));
            }
        })
        .catch(function(err) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-check-double mr-1.5"></i> Confirm & Import Dataset';
            alert('❌ Network/Server Error while committing import:\\n' + err);
        });
    }

    function downloadValidationErrorsCSV() {
        if (!currentUploadData || !currentUploadData.errors || currentUploadData.errors.length === 0) {
            alert('No validation errors to export.');
            return;
        }
        var csv = 'Row Number,Column Name,Problematic Value,Error Description\\r\\n';
        currentUploadData.errors.forEach(function(e) {
            csv += '"' + (e.row || '') + '","' + (e.column || '').replace(/"/g, '""') + '","' + (e.value || '').toString().replace(/"/g, '""') + '","' + (e.error || '').replace(/"/g, '""') + '"\\r\\n';
        });
        var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'validation_errors_' + Date.now() + '.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    </script>
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


# -----------------------------------------------------------------------------
# Dataset Upload & Import REST Endpoints
# -----------------------------------------------------------------------------

@app.route("/api/dataset/parse", methods=["POST"])
def api_dataset_parse():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"success": False, "error": "No file selected."}), 400

    orig_name = file.filename
    ext = Path(orig_name).suffix.lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        return jsonify({"success": False, "error": f"Unsupported file extension '{ext}'. Only .csv, .xlsx, .xls are supported."}), 400

    token = uuid.uuid4().hex
    safe_name = "".join(c for c in orig_name if c.isalnum() or c in (".", "_", "-")).strip() or f"dataset{ext}"
    saved_path = TEMP_UPLOADS_DIR / f"{token}_{safe_name}"

    try:
        file.save(str(saved_path))
        headers, raw_rows, file_size, fmt = read_dataset_file(saved_path)
        if not raw_rows:
            return jsonify({"success": False, "error": "The uploaded dataset contains no data rows."}), 400

        mapping = detect_column_mapping(headers)
        analysis = validate_and_analyze_dataset(headers, raw_rows, mapping, dup_policy=DUP_POLICY_SKIP, db_path=Path(config.DB_PATH))

        UPLOAD_SESSIONS[token] = {
            "token": token,
            "file_path": str(saved_path),
            "file_name": orig_name,
            "file_size": file_size,
            "format": fmt,
            "headers": headers,
            "raw_rows": raw_rows,
            "mapping": mapping,
            "dup_policy": DUP_POLICY_SKIP,
            "analysis": analysis,
        }

        summary = {
            "total_rows": analysis.get("total_rows", len(raw_rows)),
            "valid_records": analysis.get("valid_rows_count", 0),
            "invalid_records": analysis.get("invalid_rows_count", 0),
            "new_families": analysis.get("new_families_count", 0),
            "new_pilgrims": analysis.get("new_pilgrims_count", 0),
            "duplicate_records": analysis.get("duplicate_records_count", 0),
            "records_to_skip": analysis.get("skipped_records_count", 0),
        }

        return jsonify({
            "success": True,
            "token": token,
            "file_name": orig_name,
            "file_size": file_size,
            "format": fmt,
            "headers": headers,
            "mapping": mapping,
            "target_fields": [[f[0], f[1]] for f in ALL_TARGET_FIELDS],
            "preview_rows": raw_rows[:150],
            "summary": summary,
            "errors": analysis.get("validation_errors", []),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dataset/revalidate", methods=["POST"])
def api_dataset_revalidate():
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    mapping = data.get("mapping") or {}
    dup_policy_str = data.get("dup_policy", "SKIP")

    if not token or token not in UPLOAD_SESSIONS:
        return jsonify({"success": False, "error": "Upload session expired or invalid. Please re-upload your file."}), 404

    session = UPLOAD_SESSIONS[token]
    policy = DUP_POLICY_UPDATE if dup_policy_str == "UPDATE" else (DUP_POLICY_CANCEL if dup_policy_str == "CANCEL" else DUP_POLICY_SKIP)

    try:
        analysis = validate_and_analyze_dataset(session["headers"], session["raw_rows"], mapping, dup_policy=policy, db_path=Path(config.DB_PATH))
        session["mapping"] = mapping
        session["dup_policy"] = policy
        session["analysis"] = analysis

        summary = {
            "total_rows": analysis.get("total_rows", len(session["raw_rows"])),
            "valid_records": analysis.get("valid_rows_count", 0),
            "invalid_records": analysis.get("invalid_rows_count", 0),
            "new_families": analysis.get("new_families_count", 0),
            "new_pilgrims": analysis.get("new_pilgrims_count", 0),
            "duplicate_records": analysis.get("duplicate_records_count", 0),
            "records_to_skip": analysis.get("skipped_records_count", 0),
        }

        return jsonify({
            "success": True,
            "summary": summary,
            "errors": analysis.get("validation_errors", []),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/dataset/commit", methods=["POST"])
def api_dataset_commit():
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    mapping = data.get("mapping")
    dup_policy_str = data.get("dup_policy", "SKIP")

    if not token or token not in UPLOAD_SESSIONS:
        return jsonify({"success": False, "error": "Upload session expired or invalid. Please re-upload your file."}), 404

    session = UPLOAD_SESSIONS[token]
    policy = DUP_POLICY_UPDATE if dup_policy_str == "UPDATE" else (DUP_POLICY_CANCEL if dup_policy_str == "CANCEL" else DUP_POLICY_SKIP)
    active_mapping = mapping if mapping is not None else session["mapping"]

    try:
        analysis = validate_and_analyze_dataset(session["headers"], session["raw_rows"], active_mapping, dup_policy=policy, db_path=Path(config.DB_PATH))
        if analysis.get("valid_rows_count", 0) <= 0:
            return jsonify({"success": False, "error": "No valid records to import. Please check validation errors."}), 400

        res = execute_dataset_import(
            analysis=analysis,
            file_name=session["file_name"],
            file_size=session["file_size"],
            file_format=session["format"],
            column_mapping=active_mapping,
            admin_user="admin",
            db_path=Path(config.DB_PATH),
        )

        return jsonify({
            "success": True,
            "message": f"Successfully imported {res.get('successful_records', 0)} devotee/family record(s) into database.",
            "batch_id": res.get("batch_id"),
            "successful_records": res.get("successful_records", 0),
            "new_families": res.get("new_families", analysis.get("new_families_count", 0)),
            "new_pilgrims": res.get("new_pilgrims", analysis.get("new_pilgrims_count", 0)),
            "updated_records": res.get("updated_records", 0),
            "skipped_records": res.get("skipped_records", 0),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
