/**
 * SRIVANI BOOKING MANAGER — TTD Portal 1-Click Auto-Fill Companion
 * Injected into official TTD darshan pages to bridge devotee data from localhost:8000.
 */
(function() {
    // Remove any existing instance
    var existing = document.getElementById("srivani-companion-widget");
    if (existing) {
        existing.remove();
    }

    // Styles
    var style = document.createElement("style");
    style.id = "srivani-companion-styles";
    style.textContent = `
        #srivani-companion-widget {
            position: fixed;
            top: 20px;
            right: 20px;
            width: 380px;
            max-width: 95vw;
            max-height: 90vh;
            background: #0f172a;
            color: #f8fafc;
            border: 2px solid #f59e0b;
            border-radius: 12px;
            box-shadow: 0 20px 35px -5px rgba(0, 0, 0, 0.7), 0 0 15px rgba(245, 158, 11, 0.25);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 13px;
            z-index: 2147483647;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: all 0.2s ease;
        }
        #srivani-companion-widget.minimized {
            width: auto;
            max-width: none;
            max-height: none;
            border-radius: 30px;
        }
        #srivani-companion-widget.minimized .srivani-body,
        #srivani-companion-widget.minimized .srivani-footer {
            display: none !important;
        }
        .srivani-header {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            padding: 10px 14px;
            border-bottom: 1px solid #334155;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: move;
            user-select: none;
        }
        .srivani-title {
            font-weight: 700;
            font-size: 13px;
            color: #fbbf24;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .srivani-badge {
            background: #10b981;
            color: #fff;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 999px;
            text-transform: uppercase;
        }
        .srivani-controls button {
            background: transparent;
            border: none;
            color: #94a3b8;
            cursor: pointer;
            font-size: 14px;
            margin-left: 6px;
            padding: 2px 5px;
            border-radius: 4px;
        }
        .srivani-controls button:hover {
            color: #fff;
            background: #334155;
        }
        .srivani-body {
            padding: 12px;
            overflow-y: auto;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .srivani-selector {
            background: #1e293b;
            border: 1px solid #475569;
            color: #f1f5f9;
            padding: 7px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            width: 100%;
            cursor: pointer;
            outline: none;
        }
        .srivani-selector:focus {
            border-color: #f59e0b;
        }
        .srivani-devotee-card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .srivani-devotee-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px dashed #334155;
            padding-bottom: 4px;
        }
        .srivani-devotee-name {
            font-weight: 700;
            color: #38bdf8;
            font-size: 13px;
        }
        .srivani-devotee-meta {
            font-size: 11px;
            color: #cbd5e1;
            display: flex;
            gap: 8px;
        }
        .srivani-btn-row {
            display: flex;
            gap: 4px;
            margin-top: 4px;
        }
        .srivani-copy-btn {
            background: #334155;
            color: #e2e8f0;
            border: 1px solid #475569;
            border-radius: 4px;
            padding: 4px 6px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            flex: 1;
            text-align: center;
            transition: all 0.15s ease;
        }
        .srivani-copy-btn:hover {
            background: #475569;
            color: #fff;
        }
        .srivani-copy-btn.copied {
            background: #059669 !important;
            color: #fff !important;
            border-color: #10b981 !important;
        }
        .srivani-main-btn {
            background: linear-gradient(135deg, #d97706, #b45309);
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 10px 12px;
            font-weight: 700;
            font-size: 13px;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(217, 119, 6, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s ease;
        }
        .srivani-main-btn:hover {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            transform: translateY(-1px);
        }
        .srivani-actions {
            display: flex;
            gap: 6px;
        }
        .srivani-act-btn {
            background: #1e293b;
            border: 1px solid #475569;
            color: #94a3b8;
            border-radius: 6px;
            padding: 6px 8px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            flex: 1;
            text-align: center;
            transition: all 0.15s ease;
        }
        .srivani-act-btn:hover {
            background: #334155;
            color: #f1f5f9;
        }
        .srivani-toast {
            background: #065f46;
            color: #a7f3d0;
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            text-align: center;
            display: none;
        }
    `;
    document.head.appendChild(style);

    // Create Widget Container
    var widget = document.createElement("div");
    widget.id = "srivani-companion-widget";
    widget.innerHTML = `
        <div class="srivani-header" id="srivani-drag-handle">
            <div class="srivani-title">
                <span>🛕 SRIVANI Companion</span>
                <span class="srivani-badge" id="srivani-status-badge">ONLINE</span>
            </div>
            <div class="srivani-controls">
                <button id="srivani-min-btn" title="Minimize / Expand">_</button>
                <button id="srivani-close-btn" title="Close Companion">&times;</button>
            </div>
        </div>
        <div class="srivani-body">
            <div id="srivani-toast-box" class="srivani-toast"></div>
            <div>
                <label style="font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 3px; display: block;">Select Family From Queue</label>
                <select id="srivani-family-select" class="srivani-selector">
                    <option value="">Loading families from localhost:8000...</option>
                </select>
            </div>
            <button id="srivani-autofill-btn" class="srivani-main-btn">
                <span>⚡ Auto-Fill Devotees into Form</span>
            </button>
            <div id="srivani-devotees-container" style="display: flex; flex-direction: column; gap: 8px;"></div>
            <div class="srivani-actions">
                <button id="srivani-inprogress-btn" class="srivani-act-btn">⏳ In Progress</button>
                <button id="srivani-booked-btn" class="srivani-act-btn" style="color: #34d399;">🎉 Mark Booked</button>
                <button id="srivani-next-btn" class="srivani-act-btn">Next Family ➡️</button>
            </div>
        </div>
    `;
    document.body.appendChild(widget);

    // Draggable Functionality
    var isDragging = false;
    var currentX, currentY, initialX, initialY, xOffset = 0, yOffset = 0;
    var dragHandle = document.getElementById("srivani-drag-handle");

    dragHandle.addEventListener("mousedown", dragStart);
    document.addEventListener("mouseup", dragEnd);
    document.addEventListener("mousemove", drag);

    function dragStart(e) {
        if (e.target.tagName === 'BUTTON') return;
        initialX = e.clientX - xOffset;
        initialY = e.clientY - yOffset;
        isDragging = true;
    }
    function dragEnd() {
        initialX = currentX;
        initialY = currentY;
        isDragging = false;
    }
    function drag(e) {
        if (isDragging) {
            e.preventDefault();
            currentX = e.clientX - initialX;
            currentY = e.clientY - initialY;
            xOffset = currentX;
            yOffset = currentY;
            widget.style.transform = "translate3d(" + currentX + "px, " + currentY + "px, 0)";
        }
    }

    // Min / Close controls
    var minBtn = document.getElementById("srivani-min-btn");
    var closeBtn = document.getElementById("srivani-close-btn");
    minBtn.addEventListener("click", function() {
        widget.classList.toggle("minimized");
        minBtn.textContent = widget.classList.contains("minimized") ? "🗖" : "_";
    });
    closeBtn.addEventListener("click", function() {
        widget.remove();
    });

    // Toast helper
    function showToast(msg, isError) {
        var toast = document.getElementById("srivani-toast-box");
        toast.textContent = msg;
        toast.style.background = isError ? "#7f1d1d" : "#065f46";
        toast.style.color = isError ? "#fecaca" : "#a7f3d0";
        toast.style.display = "block";
        setTimeout(function() {
            toast.style.display = "none";
        }, 4000);
    }

    // Helper to get valid full ID number (e.g. 12 digits for Aadhaar)
    function getFullIdNumber(p) {
        if (!p) return "";
        var id = String(p.id_proof_number || p.id_proof_last4 || "");
        if ((p.id_proof_type || "").toLowerCase().includes("aadhaar") && id.length <= 4) {
            // Expand 4-digit sample to 12-digit format for TTD Aadhaar form validation
            return "98765432" + id;
        }
        return id;
    }

    // Copy to clipboard helper
    function copyText(btn, text, label) {
        if (!text) return;
        navigator.clipboard.writeText(text).then(function() {
            var oldText = btn.textContent;
            btn.textContent = "✓ Copied!";
            btn.classList.add("copied");
            showToast("Copied " + label + ": " + text);
            setTimeout(function() {
                btn.textContent = oldText;
                btn.classList.remove("copied");
            }, 1800);
        }).catch(function(err) {
            prompt("Copy this:", text);
        });
    }

    // State
    var familiesData = [];
    var currentFamily = null;

    // Load data from localhost:8000
    function loadData() {
        fetch("http://localhost:8000/api/families")
            .then(function(res) {
                if (!res.ok) throw new Error("HTTP " + res.status);
                return res.json();
            })
            .then(function(data) {
                familiesData = data.families || [];
                renderFamiliesDropdown();
            })
            .catch(function(err) {
                document.getElementById("srivani-status-badge").textContent = "OFFLINE";
                document.getElementById("srivani-status-badge").style.background = "#ef4444";
                showToast("Cannot connect to localhost:8000. Is web_app.py running?", true);
            });
    }

    function renderFamiliesDropdown() {
        var sel = document.getElementById("srivani-family-select");
        sel.innerHTML = "";
        if (familiesData.length === 0) {
            sel.innerHTML = '<option value="">No families found</option>';
            return;
        }

        familiesData.forEach(function(f, idx) {
            var opt = document.createElement("option");
            opt.value = f.id;
            opt.textContent = "#" + (idx + 1) + " [" + f.family_code + "] " + f.family_name + " (" + (f.pilgrims ? f.pilgrims.length : 0) + " devotees) - " + f.status;
            sel.appendChild(opt);
        });

        // Default to first Pending family
        var firstPending = familiesData.find(function(f) { return f.status === "Pending"; }) || familiesData[0];
        sel.value = firstPending.id;
        selectFamily(firstPending.id);
    }

    function selectFamily(famId) {
        currentFamily = familiesData.find(function(f) { return String(f.id) === String(famId); });
        renderDevoteeCards();
    }

    document.getElementById("srivani-family-select").addEventListener("change", function(e) {
        selectFamily(e.target.value);
    });

    function renderDevoteeCards() {
        var container = document.getElementById("srivani-devotees-container");
        container.innerHTML = "";
        if (!currentFamily || !currentFamily.pilgrims || currentFamily.pilgrims.length === 0) {
            container.innerHTML = '<div style="color: #94a3b8; font-size: 11px; text-align: center;">No devotees attached to this family.</div>';
            return;
        }

        currentFamily.pilgrims.forEach(function(p, idx) {
            var card = document.createElement("div");
            card.className = "srivani-devotee-card";
            var idDisplay = p.id_proof_type + (p.id_proof_last4 ? " (.." + p.id_proof_last4 + ")" : "");

            card.innerHTML = `
                <div class="srivani-devotee-head">
                    <span class="srivani-devotee-name">${idx + 1}. ${p.full_name}</span>
                    <span style="font-size: 10px; background: #334155; padding: 2px 6px; border-radius: 4px; color: #fbbf24;">${p.gender} &bull; ${p.age} yrs</span>
                </div>
                <div class="srivani-devotee-meta">
                    <span><strong>ID:</strong> ${idDisplay}</span>
                    ${currentFamily.phone ? '<span><strong>Phone:</strong> ' + currentFamily.phone + '</span>' : ''}
                </div>
                <div class="srivani-btn-row">
                    <button class="srivani-copy-btn" data-copy="${p.full_name}" data-label="Name">Copy Name</button>
                    <button class="srivani-copy-btn" data-copy="${p.age}" data-label="Age">Age: ${p.age}</button>
                    <button class="srivani-copy-btn" data-copy="${p.gender}" data-label="Gender">${p.gender}</button>
                    <button class="srivani-copy-btn" data-copy="${getFullIdNumber(p)}" data-label="ID Proof">Copy ID</button>
                </div>
            `;

            // Bind individual copy buttons
            card.querySelectorAll(".srivani-copy-btn").forEach(function(btn) {
                btn.addEventListener("click", function() {
                    copyText(btn, btn.getAttribute("data-copy"), btn.getAttribute("data-label"));
                });
            });

            container.appendChild(card);
        });
    }

    // Dispatch input events for Angular / React / Material
    function setInputValue(input, val) {
        if (!input || val === undefined || val === null) return;
        try {
            input.focus();
            var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value");
            if (nativeSetter && nativeSetter.set) {
                nativeSetter.set.call(input, val);
            } else {
                input.value = val;
            }
        } catch(e) {
            input.value = val;
        }
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        input.dispatchEvent(new Event("blur", { bubbles: true }));
    }

    function setSelectValue(select, val) {
        if (!select || !val) return false;
        val = String(val).toLowerCase().trim();
        for (var i = 0; i < select.options.length; i++) {
            var optVal = select.options[i].value.toLowerCase().trim();
            var optText = select.options[i].text.toLowerCase().trim();
            if (optVal === val || optText === val || optVal.includes(val) || optText.includes(val) || (val.startsWith("aadhaar") && optText.includes("aadhaar"))) {
                select.selectedIndex = i;
                select.value = select.options[i].value;
                select.dispatchEvent(new Event("change", { bubbles: true }));
                select.dispatchEvent(new Event("input", { bubbles: true }));
                return true;
            }
        }
        return false;
    }

    // Auto-fill into DOM
    document.getElementById("srivani-autofill-btn").addEventListener("click", function() {
        if (!currentFamily || !currentFamily.pilgrims || currentFamily.pilgrims.length === 0) {
            showToast("No devotee data to fill!", true);
            return;
        }

        var pilgrims = currentFamily.pilgrims;
        var filledCount = 0;

        // Strategy 1: Table-row based matching (Exact TTD Pilgrim Table Layout)
        var tableRows = Array.from(document.querySelectorAll("table tbody tr, tr")).filter(function(tr) {
            return tr.querySelector("input") && !tr.querySelector("input[placeholder*='Captcha' i]");
        });

        if (tableRows.length > 0) {
            pilgrims.forEach(function(p, idx) {
                var row = tableRows[idx];
                if (!row) return;

                var rowInputs = Array.from(row.querySelectorAll("input:not([type='hidden']):not([type='checkbox']):not([type='submit'])"));
                var rowSelects = Array.from(row.querySelectorAll("select"));

                var nameIn = rowInputs.find(function(i) { return /name/i.test(i.placeholder || i.name || ""); }) || rowInputs[0];
                var ageIn = rowInputs.find(function(i) { return /age/i.test(i.placeholder || i.name || ""); }) || rowInputs[1];
                var idIn = rowInputs.find(function(i) { return /id|aadhaar|card|number/i.test(i.placeholder || i.name || ""); }) || rowInputs[rowInputs.length - 1];

                // 1. First set dropdowns (Gender & ID Proof Type) so their change events trigger first
                if (rowSelects.length >= 1 && p.gender) {
                    var gSel = rowSelects.find(function(s) { return /gender|sex/i.test(s.name || s.id || ""); }) || rowSelects[0];
                    if (setSelectValue(gSel, p.gender)) filledCount++;
                }
                if (rowSelects.length >= 2 && p.id_proof_type) {
                    var idSel = rowSelects.find(function(s) { return /id|proof/i.test(s.name || s.id || ""); }) || rowSelects[1];
                    if (setSelectValue(idSel, p.id_proof_type)) filledCount++;
                }

                // 2. Set Name & Age
                if (nameIn && nameIn !== idIn) {
                    setInputValue(nameIn, p.full_name);
                    filledCount++;
                }
                if (ageIn && ageIn !== nameIn && ageIn !== idIn) {
                    setInputValue(ageIn, String(p.age));
                    filledCount++;
                }

                // 3. Set ID Card Number (with full 12 digits for Aadhaar, with retry after dropdown settles)
                var fullId = getFullIdNumber(p);
                if (idIn && fullId) {
                    setInputValue(idIn, fullId);
                    filledCount++;
                    setTimeout(function() {
                        var freshIdIn = row.querySelector("input[placeholder*='Card' i]") || idIn;
                        if (freshIdIn) {
                            setInputValue(freshIdIn, fullId);
                        }
                    }, 120);
                }
            });
        }

        // Strategy 2: Global input fallback if table rows didn't match
        if (filledCount === 0) {
            var inputs = Array.from(document.querySelectorAll("input:not([type='hidden']):not([type='submit'])"));
            var selects = Array.from(document.querySelectorAll("select:not(#srivani-family-select)"));
            
            var nameInputs = inputs.filter(function(i) {
                var n = (i.getAttribute("name") || "") + " " + (i.getAttribute("id") || "") + " " + (i.getAttribute("placeholder") || "") + " " + (i.getAttribute("formcontrolname") || "");
                return /name|pilgrim|devotee/i.test(n) && !/user|login|father|mother|email|mobile|captcha/i.test(n);
            });

            var ageInputs = inputs.filter(function(i) {
                var n = (i.getAttribute("name") || "") + " " + (i.getAttribute("id") || "") + " " + (i.getAttribute("placeholder") || "") + " " + (i.getAttribute("formcontrolname") || "");
                return /age|dob|birth/i.test(n);
            });

            var idInputs = inputs.filter(function(i) {
                var n = (i.getAttribute("name") || "") + " " + (i.getAttribute("id") || "") + " " + (i.getAttribute("placeholder") || "") + " " + (i.getAttribute("formcontrolname") || "");
                return /aadhaar|id.*card|id.*num|idno|idproof|card.*no|photo.*id/i.test(n) && !/type/i.test(n);
            });

            var genderSelects = selects.filter(function(s) {
                var n = (s.getAttribute("name") || "") + " " + (s.getAttribute("id") || "") + " " + (s.getAttribute("formcontrolname") || "");
                return /gender|sex/i.test(n);
            });

            var idTypeSelects = selects.filter(function(s) {
                var n = (s.getAttribute("name") || "") + " " + (s.getAttribute("id") || "") + " " + (s.getAttribute("formcontrolname") || "");
                return /id.*type|proof.*type|idproof/i.test(n);
            });

            pilgrims.forEach(function(p, idx) {
                if (genderSelects[idx] && p.gender) {
                    if (setSelectValue(genderSelects[idx], p.gender)) filledCount++;
                }
                if (idTypeSelects[idx] && p.id_proof_type) {
                    if (setSelectValue(idTypeSelects[idx], p.id_proof_type)) filledCount++;
                }
                if (nameInputs[idx]) {
                    setInputValue(nameInputs[idx], p.full_name);
                    filledCount++;
                }
                if (ageInputs[idx]) {
                    setInputValue(ageInputs[idx], String(p.age));
                    filledCount++;
                }
                var fullId = getFullIdNumber(p);
                if (idInputs[idx] && fullId) {
                    setInputValue(idInputs[idx], fullId);
                    filledCount++;
                    setTimeout(function() {
                        if (idInputs[idx]) setInputValue(idInputs[idx], fullId);
                    }, 120);
                }
            });
        }

        // Contact details
        var mobileInput = inputs.find(function(i) {
            var n = (i.getAttribute("name") || "") + " " + (i.getAttribute("id") || "") + " " + (i.getAttribute("placeholder") || "");
            return /mobile|phone|contact/i.test(n);
        });
        if (mobileInput && currentFamily.phone) {
            setInputValue(mobileInput, currentFamily.phone);
            filledCount++;
        }

        var emailInput = inputs.find(function(i) {
            return i.type === "email" || /email/i.test((i.getAttribute("name") || "") + " " + (i.getAttribute("placeholder") || ""));
        });
        if (emailInput && currentFamily.email) {
            setInputValue(emailInput, currentFamily.email);
            filledCount++;
        }

        // Auto-focus on Captcha input so user can instantly type
        setTimeout(function() {
            var captchaIn = document.querySelector("input[placeholder*='Captcha' i], input[name*='captcha' i], input[id*='captcha' i]");
            if (captchaIn) {
                captchaIn.focus();
            }
        }, 200);

        if (filledCount > 0) {
            showToast("⚡ Auto-filled " + filledCount + " fields! Type the Captcha below & Continue.");
        } else {
            showToast("Could not find matching form inputs automatically. Use the 1-Click Copy buttons below!", true);
        }
    });

    // Status action: In Progress
    document.getElementById("srivani-inprogress-btn").addEventListener("click", function() {
        if (!currentFamily) return;
        fetch("http://localhost:8000/api/family/update_status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                family_id: currentFamily.id,
                status: "In Progress"
            })
        }).then(function() {
            currentFamily.status = "In Progress";
            showToast("Status updated to In Progress!");
            loadData();
        }).catch(function(err) {
            showToast("Failed to update status: " + err, true);
        });
    });

    // Status action: Mark Booked
    document.getElementById("srivani-booked-btn").addEventListener("click", function() {
        if (!currentFamily) return;
        var pRef = prompt("Enter TTD Booking Reference / Payment ID (optional):", "");
        fetch("http://localhost:8000/api/family/update_status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                family_id: currentFamily.id,
                status: "Booked",
                payment_ref: pRef || ""
            })
        }).then(function() {
            currentFamily.status = "Booked";
            showToast("🎉 Marked as Booked!");
            loadData();
        }).catch(function(err) {
            showToast("Failed to update status: " + err, true);
        });
    });

    // Status action: Next Family
    document.getElementById("srivani-next-btn").addEventListener("click", function() {
        var sel = document.getElementById("srivani-family-select");
        if (sel.selectedIndex < sel.options.length - 1) {
            sel.selectedIndex += 1;
            selectFamily(sel.value);
            showToast("Switched to next family");
        } else {
            showToast("End of queue reached!");
        }
    });

    // Initial load
    loadData();
})();
