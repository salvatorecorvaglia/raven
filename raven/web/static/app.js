/* ─────────────────────────────────────────────────────────────────────────
   Raven Web Dashboard — Client-side JavaScript
   ───────────────────────────────────────────────────────────────────────── */

(() => {
    "use strict";

    // ── Constants ───────────────────────────────────────────────────────
    const MAX_HISTORY = 60;
    const RECONNECT_DELAY = 3000;

    // ── State ───────────────────────────────────────────────────────────
    let ws = null;
    let cpuChart = null;
    let memChart = null;
    let netChart = null;
    let cpuHistory = [];
    let memHistory = [];
    let netSentHistory = [];
    let netRecvHistory = [];
    let prevNetSent = 0;
    let prevNetRecv = 0;
    let prevIfaceData = {};
    let lastSnapshot = null;
    let sortKey = "cpu_percent";
    let sortAsc = false;

    // ── Utilities ───────────────────────────────────────────────────────
    function escapeHtml(str) {
        const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
        return String(str).replace(/[&<>"']/g, (c) => map[c]);
    }

    // Encrypts/obfuscates the API key before storage to prevent clear text exposure in localStorage/sessionStorage.
    function encryptKey(text) {
        if (!text) return "";
        const salt = "raven_secure_obfuscation_salt";
        let result = "";
        for (let i = 0; i < text.length; i++) {
            result += String.fromCharCode(text.charCodeAt(i) ^ salt.charCodeAt(i % salt.length));
        }
        return btoa(result);
    }

    // Decrypts the stored API key. Falls back to returning the ciphertext directly if it's not base64 encoded.
    function decryptKey(ciphertext) {
        if (!ciphertext) return "";
        try {
            const decoded = atob(ciphertext);
            const salt = "raven_secure_obfuscation_salt";
            let result = "";
            for (let i = 0; i < decoded.length; i++) {
                result += String.fromCharCode(decoded.charCodeAt(i) ^ salt.charCodeAt(i % salt.length));
            }
            return result;
        } catch (e) {
            return ciphertext;
        }
    }

    function humanBytes(bytes) {
        const units = ["B", "KB", "MB", "GB", "TB"];
        let i = 0;
        let val = bytes;
        while (Math.abs(val) >= 1024 && i < units.length - 1) {
            val /= 1024;
            i++;
        }
        return val.toFixed(1) + " " + units[i];
    }

    // Convert to rating
    function humanBytesRate(bytes) {
        return humanBytes(bytes) + "/s";
    }

    function classForPercent(pct) {
        if (pct < 50) return "metric-ok";
        if (pct < 80) return "metric-warn";
        return "metric-crit";
    }

    function bgClassForPercent(pct) {
        if (pct < 50) return "bg-ok";
        if (pct < 80) return "bg-warn";
        return "bg-crit";
    }

    function formatUptime(seconds) {
        const d = Math.floor(seconds / 86400);
        const h = Math.floor((seconds % 86400) / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        let parts = [];
        if (d > 0) parts.push(d + "d");
        parts.push(h + "h");
        parts.push(m + "m");
        return parts.join(" ");
    }

    const EMPTY_LABELS = Array.from({ length: MAX_HISTORY }, () => "");

    function timeLabels() {
        return EMPTY_LABELS;
    }

    // ── Chart Setup ─────────────────────────────────────────────────────
    function createChart(canvasId, label, borderColor, bgColor) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        return new Chart(ctx, {
            type: "line",
            data: {
                labels: timeLabels(),
                datasets: [{
                    label: label,
                    data: [],
                    borderColor: borderColor,
                    backgroundColor: bgColor,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 3,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 300 },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "rgba(20, 27, 45, 0.95)",
                        titleColor: "#00d2ff",
                        bodyColor: "#e6f1ff",
                        borderColor: "rgba(0, 210, 255, 0.3)",
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 8,
                    },
                },
                scales: {
                    x: { display: false },
                    y: {
                        display: true,
                        min: 0,
                        grid: {
                            color: "rgba(255, 255, 255, 0.04)",
                            drawBorder: false,
                        },
                        ticks: {
                            color: "#5a6785",
                            font: { size: 10, family: "'JetBrains Mono', monospace" },
                        },
                    },
                },
            },
        });
    }

    function createNetChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        return new Chart(ctx, {
            type: "line",
            data: {
                labels: timeLabels(),
                datasets: [
                    {
                        label: "Sent",
                        data: [],
                        borderColor: "#00d2ff",
                        backgroundColor: "rgba(0, 210, 255, 0.08)",
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0,
                    },
                    {
                        label: "Received",
                        data: [],
                        borderColor: "#64ffda",
                        backgroundColor: "rgba(100, 255, 218, 0.08)",
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 300 },
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: "#8892b0",
                            font: { size: 10, family: "'JetBrains Mono', monospace" },
                            boxWidth: 12,
                        },
                    },
                    tooltip: {
                        backgroundColor: "rgba(20, 27, 45, 0.95)",
                        titleColor: "#00d2ff",
                        bodyColor: "#e6f1ff",
                        borderColor: "rgba(0, 210, 255, 0.3)",
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {
                            label: (ctx) => ctx.dataset.label + ": " + humanBytesRate(ctx.parsed.y),
                        },
                    },
                },
                scales: {
                    x: { display: false },
                    y: {
                        display: true,
                        min: 0,
                        grid: {
                            color: "rgba(255, 255, 255, 0.04)",
                            drawBorder: false,
                        },
                        ticks: {
                            color: "#5a6785",
                            font: { size: 10, family: "'JetBrains Mono', monospace" },
                            callback: (v) => humanBytes(v),
                        },
                    },
                },
            },
        });
    }

    // ── Update Functions ────────────────────────────────────────────────
    function updateHeader(snap) {
        const si = snap.system_info || {};
        document.getElementById("hostname").textContent = si.hostname || "";
        document.getElementById("os-info").textContent =
            (si.os_name || "") + " " + (si.os_version || "") + " (" + (si.architecture || "") + ")";
        document.getElementById("uptime").textContent = "⏱ " + formatUptime(si.uptime_seconds || 0);
        document.getElementById("clock").textContent = new Date().toLocaleTimeString();
    }

    function updateCpu(snap) {
        const cpu = snap.cpu || {};
        const overall = cpu.percent_overall || 0;

        // Value
        const el = document.getElementById("cpu-overall");
        el.textContent = overall.toFixed(1) + "%";
        el.className = "card-value " + classForPercent(overall);

        // Details
        document.getElementById("cpu-cores").textContent =
            (cpu.core_count_physical || "?") + "P / " + (cpu.core_count_logical || "?") + "L";
        document.getElementById("cpu-freq").textContent =
            cpu.frequency_current_mhz ? cpu.frequency_current_mhz.toFixed(0) + " MHz" : "—";
        document.getElementById("cpu-load").textContent =
            cpu.load_avg_1 != null
                ? cpu.load_avg_1.toFixed(2) + " / " + cpu.load_avg_5.toFixed(2) + " / " + cpu.load_avg_15.toFixed(2)
                : "—";

        // Core bars
        const coreBars = document.getElementById("cpu-core-bars");
        const cores = cpu.percent_per_core || [];

        // Rebuild containers if counts mismatch to avoid layout thrashing
        if (coreBars.children.length !== cores.length) {
            coreBars.innerHTML = cores
                .map((_, i) => {
                    return `<div class="core-bar">
                        <span class="core-bar-label">C${i}</span>
                        <div class="core-bar-track"><div class="core-bar-fill"></div></div>
                    </div>`;
                })
                .join("");
        }

        // Update in-place
        cores.forEach((pct, i) => {
            const safePct = Number(pct) || 0;
            const fill = coreBars.children[i].querySelector(".core-bar-fill");
            if (fill) {
                fill.style.width = safePct + "%";
                fill.className = "core-bar-fill " + bgClassForPercent(safePct);
            }
        });

        // Chart
        cpuHistory.push(overall);
        if (cpuHistory.length > MAX_HISTORY) cpuHistory.shift();
        if (cpuChart) {
            cpuChart.data.datasets[0].data = cpuHistory;
            cpuChart.options.scales.y.max = 100;
            cpuChart.update("none");
        }
    }

    function updateMemory(snap) {
        const mem = snap.memory || {};

        const el = document.getElementById("mem-overall");
        el.textContent = (mem.percent || 0).toFixed(1) + "%";
        el.className = "card-value " + classForPercent(mem.percent || 0);

        document.getElementById("mem-used").textContent = humanBytes(mem.used || 0);
        document.getElementById("mem-total").textContent = humanBytes(mem.total || 0);
        document.getElementById("mem-avail").textContent = humanBytes(mem.available || 0);

        // Progress bars
        document.getElementById("ram-bar").style.width = (mem.percent || 0) + "%";
        if ((mem.percent || 0) > 80) {
            document.getElementById("ram-bar").classList.add("warn");
        } else {
            document.getElementById("ram-bar").classList.remove("warn");
        }

        document.getElementById("swap-bar").style.width = (mem.swap_percent || 0) + "%";

        // Chart
        memHistory.push(mem.percent || 0);
        if (memHistory.length > MAX_HISTORY) memHistory.shift();
        if (memChart) {
            memChart.data.datasets[0].data = memHistory;
            memChart.options.scales.y.max = 100;
            memChart.update("none");
        }
    }

    function updateNetwork(snap) {
        const net = snap.network || {};
        document.getElementById("net-connections").textContent = (net.connections_count || 0) + " conn";

        const interfaces = (net.interfaces || []).filter((i) => !i.name.startsWith("lo"));
        const container = document.getElementById("net-interfaces");

        // Calculate total rates
        let totalSent = 0;
        let totalRecv = 0;
        interfaces.forEach((iface) => {
            totalSent += iface.bytes_sent || 0;
            totalRecv += iface.bytes_recv || 0;
        });

        const rateSent = Math.max(0, totalSent - prevNetSent);
        const rateRecv = Math.max(0, totalRecv - prevNetRecv);
        if (prevNetSent > 0) {
            netSentHistory.push(rateSent);
            netRecvHistory.push(rateRecv);
            if (netSentHistory.length > MAX_HISTORY) netSentHistory.shift();
            if (netRecvHistory.length > MAX_HISTORY) netRecvHistory.shift();
        }
        prevNetSent = totalSent;
        prevNetRecv = totalRecv;

        // Update chart
        if (netChart && netSentHistory.length > 0) {
            netChart.data.datasets[0].data = netSentHistory;
            netChart.data.datasets[1].data = netRecvHistory;
            netChart.update("none");
        }

        // Interface list - update in-place
        if (container.children.length !== interfaces.length) {
            container.innerHTML = interfaces
                .map(() => {
                    return `<div class="iface-row">
                        <span class="iface-name"></span>
                        <span class="iface-rate"></span>
                        <span class="iface-addr"></span>
                    </div>`;
                })
                .join("");
        }

        interfaces.forEach((iface, i) => {
            const row = container.children[i];
            const nameEl = row.querySelector(".iface-name");
            const rateEl = row.querySelector(".iface-rate");
            const addrEl = row.querySelector(".iface-addr");

            const addr = iface.addrs && iface.addrs.length > 0 ? iface.addrs[0] : "—";
            const name = iface.name;

            // Compute rates
            let rateSent = 0;
            let rateRecv = 0;
            const now = Date.now();
            if (prevIfaceData[name]) {
                const prev = prevIfaceData[name];
                const dt = (now - prev.time) / 1000.0;
                if (dt > 0.1) {
                    rateSent = Math.max(0, (iface.bytes_sent - prev.sent) / dt);
                    rateRecv = Math.max(0, (iface.bytes_recv - prev.recv) / dt);
                }
            }
            prevIfaceData[name] = {
                sent: iface.bytes_sent,
                recv: iface.bytes_recv,
                time: now
            };

            nameEl.textContent = name;
            rateEl.textContent = `▲ ${humanBytesRate(rateSent)}  ▼ ${humanBytesRate(rateRecv)}`;
            addrEl.textContent = addr;
        });
    }

    function updateDisk(snap) {
        const disk = snap.disk || {};
        const partitions = disk.partitions || [];
        const container = document.getElementById("disk-partitions");

        // Partitions list - update in-place
        if (container.children.length !== partitions.length) {
            container.innerHTML = partitions
                .map(() => {
                    return `<div class="partition-row">
                        <span class="partition-mount"></span>
                        <div class="partition-usage">
                            <div class="partition-bar"><div class="partition-bar-fill"></div></div>
                            <span class="partition-pct"></span>
                        </div>
                        <span class="partition-size"></span>
                    </div>`;
                })
                .join("");
        }

        partitions.forEach((p, i) => {
            const row = container.children[i];
            const mountEl = row.querySelector(".partition-mount");
            const fillEl = row.querySelector(".partition-bar-fill");
            const pctEl = row.querySelector(".partition-pct");
            const sizeEl = row.querySelector(".partition-size");

            const safePct = Number(p.percent) || 0;

            mountEl.textContent = p.mountpoint;
            fillEl.style.width = safePct + "%";
            fillEl.className = "partition-bar-fill " + bgClassForPercent(safePct);
            pctEl.textContent = safePct.toFixed(1) + "%";
            pctEl.className = "partition-pct " + classForPercent(safePct);
            sizeEl.textContent = `${humanBytes(p.used || 0)} / ${humanBytes(p.total || 0)}`;
        });

        const io = disk.io || {};
        document.getElementById("disk-read").textContent = humanBytes(io.read_bytes || 0);
        document.getElementById("disk-write").textContent = humanBytes(io.write_bytes || 0);
    }

    function updateSensors(snap) {
        const sensors = snap.sensors || {};

        // Temperatures
        const temps = sensors.temperatures || [];
        const tempContainer = document.getElementById("temp-list");
        if (temps.length) {
            let header = tempContainer.querySelector(".sensor-section-header");
            if (!header || tempContainer.children.length !== (temps.length + 1)) {
                let html = `<div class="sensor-section-header">Temperatures</div>`;
                temps.forEach(() => {
                    html += `<div class="sensor-row">
                        <span class="sensor-label"></span>
                        <span class="sensor-value"></span>
                    </div>`;
                });
                tempContainer.innerHTML = html;
            }

            temps.forEach((t, i) => {
                const row = tempContainer.children[i + 1];
                const labelEl = row.querySelector(".sensor-label");
                const valEl = row.querySelector(".sensor-value");

                labelEl.textContent = t.label;
                valEl.textContent = t.current.toFixed(0) + "°C";
                valEl.className = "sensor-value " + classForPercent(t.current);
            });
        } else {
            tempContainer.innerHTML = "";
        }

        // Fans
        const fans = sensors.fans || [];
        const fanContainer = document.getElementById("fan-list");
        if (fans.length) {
            let header = fanContainer.querySelector(".sensor-section-header");
            if (!header || fanContainer.children.length !== (fans.length + 1)) {
                let html = `<div class="sensor-section-header">Fans</div>`;
                fans.forEach(() => {
                    html += `<div class="sensor-row">
                        <span class="sensor-label"></span>
                        <span class="sensor-value"></span>
                    </div>`;
                });
                fanContainer.innerHTML = html;
            }

            fans.forEach((f, i) => {
                const row = fanContainer.children[i + 1];
                const labelEl = row.querySelector(".sensor-label");
                const valEl = row.querySelector(".sensor-value");

                labelEl.textContent = f.label;
                valEl.textContent = (Number(f.current) || 0) + " RPM";
            });
        } else {
            fanContainer.innerHTML = "";
        }

        // Battery
        const bat = sensors.battery;
        const batContainer = document.getElementById("battery-info");
        if (bat) {
            let header = batContainer.querySelector(".sensor-section-header");
            if (!header || batContainer.children.length !== 2) {
                batContainer.innerHTML = `<div class="sensor-section-header">Battery</div>
                <div class="sensor-row">
                    <span class="sensor-label"></span>
                    <span class="sensor-value"></span>
                </div>`;
            }
            const row = batContainer.children[1];
            const labelEl = row.querySelector(".sensor-label");
            const valEl = row.querySelector(".sensor-value");

            labelEl.textContent = bat.power_plugged ? "⚡ Plugged" : "🔋 Battery";
            valEl.textContent = (bat.percent || 0).toFixed(0) + "%";
            valEl.className = "sensor-value " + (bat.percent > 20 ? "temp-ok" : "temp-crit");
        } else {
            batContainer.innerHTML = "";
        }
    }

    function updateUsers(snap) {
        const users = snap.users || [];
        document.getElementById("user-count").textContent = users.length;
        const seen = new Set();
        const filteredUsers = users.filter((u) => {
            if (seen.has(u.name)) return false;
            seen.add(u.name);
            return true;
        });

        const container = document.getElementById("user-list");
        if (container.children.length !== filteredUsers.length) {
            container.innerHTML = filteredUsers
                .map(() => {
                    return `<div class="user-row">
                        <span class="user-name"></span>
                        <span class="user-terminal"></span>
                    </div>`;
                })
                .join("");
        }

        filteredUsers.forEach((u, i) => {
            const row = container.children[i];
            const nameEl = row.querySelector(".user-name");
            const termEl = row.querySelector(".user-terminal");

            nameEl.textContent = u.name;
            termEl.textContent = u.terminal || "—";
        });
    }

    function updateContainers(snap) {
        const ct = snap.containers || {};
        const containers = ct.containers || [];
        const running = containers.filter((c) => c.status === "running" || c.status === "up").length;
        document.getElementById("container-count").textContent = running + " / " + containers.length;

        const container = document.getElementById("container-list");
        if (containers.length) {
            const displayLimit = 10;
            const showList = containers.slice(0, displayLimit);

            if (container.children.length !== showList.length || container.querySelector(".no-containers")) {
                container.innerHTML = showList
                    .map(() => {
                        return `<div class="container-row">
                            <span class="container-runtime"></span>
                            <span class="container-name"></span>
                            <span class="container-status"></span>
                            <span class="container-image"></span>
                        </div>`;
                    })
                    .join("");
            }

            showList.forEach((c, i) => {
                const row = container.children[i];
                const runtimeEl = row.querySelector(".container-runtime");
                const nameEl = row.querySelector(".container-name");
                const statusEl = row.querySelector(".container-status");
                const imageEl = row.querySelector(".container-image");

                const isRunning = c.status === "running" || c.status === "up";

                runtimeEl.textContent = c.runtime;
                nameEl.textContent = c.name;
                statusEl.textContent = c.status;
                statusEl.className = `container-status ${isRunning ? "status-running" : "status-stopped"}`;
                imageEl.textContent = c.image;
            });
        } else {
            container.innerHTML = '<div class="no-containers" style="color:var(--text-dim);font-size:0.8rem;padding:0.5rem">No containers detected</div>';
        }
    }

    function updateProcesses(snap) {
        const procs = snap.processes || [];
        document.getElementById("proc-count").textContent = procs.length + " processes";

        // Sort
        const sorted = [...procs].sort((a, b) => {
            const va = a[sortKey] || 0;
            const vb = b[sortKey] || 0;
            if (typeof va === "string") return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
            return sortAsc ? va - vb : vb - va;
        });

        // Update header sort indicators
        document.querySelectorAll("#process-table th[data-sort]").forEach((th) => {
            const key = th.getAttribute("data-sort");
            let baseText = th.getAttribute("data-base");
            if (!baseText) {
                baseText = th.textContent.replace(/ [▲▼]/g, "");
                th.setAttribute("data-base", baseText);
            }
            if (key === sortKey) {
                th.textContent = baseText + (sortAsc ? " ▲" : " ▼");
                th.setAttribute("aria-sort", sortAsc ? "ascending" : "descending");
            } else {
                th.textContent = baseText;
                th.removeAttribute("aria-sort");
            }
        });

        const tbody = document.getElementById("process-tbody");
        const displayLimit = 40;
        const showProcs = sorted.slice(0, displayLimit);

        if (tbody.children.length !== showProcs.length) {
            tbody.innerHTML = showProcs
                .map(() => {
                    return `<tr>
                        <td class="proc-pid"></td>
                        <td class="proc-name"></td>
                        <td class="proc-user"></td>
                        <td class="proc-cpu"></td>
                        <td class="proc-mem"></td>
                        <td class="proc-status"></td>
                    </tr>`;
                })
                .join("");
        }

        showProcs.forEach((p, i) => {
            const row = tbody.children[i];
            const pidEl = row.querySelector(".proc-pid");
            const nameEl = row.querySelector(".proc-name");
            const userEl = row.querySelector(".proc-user");
            const cpuEl = row.querySelector(".proc-cpu");
            const memEl = row.querySelector(".proc-mem");
            const statusEl = row.querySelector(".proc-status");

            const cpuPct = p.cpu_percent || 0;
            const memPct = p.memory_percent || 0;

            pidEl.textContent = p.pid;
            nameEl.textContent = (p.name || "").substring(0, 30);
            userEl.textContent = (p.username || "—").substring(0, 12);

            cpuEl.textContent = cpuPct.toFixed(1);
            cpuEl.className = "proc-cpu " + classForPercent(cpuPct);

            memEl.textContent = memPct.toFixed(1);
            memEl.className = "proc-mem " + classForPercent(memPct);

            statusEl.textContent = (p.status || "").substring(0, 10);
        });
    }

    // ── Process table sorting ───────────────────────────────────────────
    const processTable = document.getElementById("process-table");

    function handleSort(th) {
        const key = th.getAttribute("data-sort");
        if (sortKey === key) {
            sortAsc = !sortAsc;
        } else {
            sortKey = key;
            sortAsc = false;
        }
        if (lastSnapshot) {
            updateProcesses(lastSnapshot);
        }
    }

    processTable.addEventListener("click", (e) => {
        const th = e.target.closest("th[data-sort]");
        if (th) handleSort(th);
    });

    processTable.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            const th = e.target.closest("th[data-sort]");
            if (th) {
                e.preventDefault();
                handleSort(th);
            }
        }
    });

    // ── WebSocket ───────────────────────────────────────────────────────
    function showAuthModal() {
        const modal = document.getElementById("auth-modal");
        if (modal) {
            modal.style.display = "flex";
            const input = document.getElementById("auth-key-input");
            if (input) {
                input.value = "";
                input.focus();
            }
        }
    }

    function hideAuthModal() {
        const modal = document.getElementById("auth-modal");
        if (modal) {
            modal.style.display = "none";
        }
    }

    function connect() {
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        const params = new URLSearchParams(location.search);
        let apiKey = params.get("api_key");

        if (apiKey) {
            sessionStorage.setItem("raven_api_key", encryptKey(apiKey));
            localStorage.setItem("raven_api_key", encryptKey(apiKey));
            params.delete("api_key");
            const newUrl = location.pathname + (params.toString() ? "?" + params.toString() : "");
            window.history.replaceState({}, document.title, newUrl);
        } else {
            apiKey = decryptKey(sessionStorage.getItem("raven_api_key") || localStorage.getItem("raven_api_key") || "");
        }

        const url = proto + "//" + location.host + "/ws/live";
        ws = new WebSocket(url);

        ws.onopen = () => {
            // Send API key as first message (avoids leaking in URL/logs)
            ws.send(apiKey);

            const badge = document.getElementById("status-badge");
            badge.textContent = "Live";
            badge.classList.add("connected");
            document.body.classList.remove("disconnected");
            hideAuthModal();

            // Fetch version from health endpoint
            fetch("/health")
                .then((r) => r.json())
                .then((d) => {
                    document.getElementById("app-version").textContent = "v" + (d.version || "?");
                })
                .catch(() => {});
        };

        ws.onmessage = (event) => {
            try {
                const snap = JSON.parse(event.data);
                lastSnapshot = snap;
                updateHeader(snap);
                updateCpu(snap);
                updateMemory(snap);
                updateNetwork(snap);
                updateDisk(snap);
                updateSensors(snap);
                updateUsers(snap);
                updateContainers(snap);
                updateProcesses(snap);
                document.body.classList.remove("loading");
                document.getElementById("last-update").textContent =
                    "Last update: " + new Date().toLocaleTimeString();
            } catch (err) {
                console.error("Failed to parse snapshot:", err);
            }
        };

        ws.onclose = (event) => {
            const badge = document.getElementById("status-badge");
            badge.classList.remove("connected");
            document.body.classList.add("disconnected");

            if (event.code === 4001) {
                badge.textContent = "Auth Required";
                sessionStorage.removeItem("raven_api_key");
                localStorage.removeItem("raven_api_key");
                showAuthModal();
            } else {
                badge.textContent = "Reconnecting…";
                setTimeout(connect, RECONNECT_DELAY);
            }
        };

        ws.onerror = () => {
            ws.close();
        };
    }

    // ── Clock ───────────────────────────────────────────────────────────
    setInterval(() => {
        document.getElementById("clock").textContent = new Date().toLocaleTimeString();
    }, 1000);

    // ── Theme Management ────────────────────────────────────────────────
    function updateChartTheme() {
        const isLight = document.body.classList.contains("light-theme");
        const gridColor = isLight ? "rgba(0, 0, 0, 0.06)" : "rgba(255, 255, 255, 0.04)";
        const tickColor = isLight ? "#64748b" : "#5a6785";

        [cpuChart, memChart, netChart].forEach((chart) => {
            if (!chart) return;
            chart.options.scales.y.grid.color = gridColor;
            chart.options.scales.y.ticks.color = tickColor;
            chart.options.plugins.tooltip.backgroundColor = isLight ? "rgba(255, 255, 255, 0.95)" : "rgba(20, 27, 45, 0.95)";
            chart.options.plugins.tooltip.bodyColor = isLight ? "#1e293b" : "#e6f1ff";
            chart.options.plugins.tooltip.borderColor = isLight ? "rgba(0, 0, 0, 0.1)" : "rgba(0, 210, 255, 0.3)";
            chart.update();
        });
    }

    const themeBtn = document.getElementById("theme-toggle");
    if (themeBtn) {
        themeBtn.addEventListener("click", () => {
            document.body.classList.toggle("light-theme");
            const isLight = document.body.classList.contains("light-theme");
            localStorage.setItem("theme", isLight ? "light" : "dark");
            updateChartTheme();
        });

        // Restore saved theme on load (applied to body class in HTML, but update charts)
        const savedTheme = localStorage.getItem("theme");
        if (savedTheme === "light") {
            document.body.classList.add("light-theme");
        }
    }

    // ── Init ────────────────────────────────────────────────────────────
    cpuChart = createChart("cpu-chart", "CPU %", "#00d2ff", "rgba(0, 210, 255, 0.1)");
    memChart = createChart("mem-chart", "Memory %", "#c084fc", "rgba(192, 132, 252, 0.1)");
    netChart = createNetChart("net-chart");
    if (document.body.classList.contains("light-theme")) {
        updateChartTheme();
    }
    const authForm = document.getElementById("auth-form");
    if (authForm) {
        authForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const input = document.getElementById("auth-key-input");
            if (input) {
                const key = input.value.trim();
                sessionStorage.setItem("raven_api_key", encryptKey(key));
                localStorage.setItem("raven_api_key", encryptKey(key));
                hideAuthModal();
                connect();
            }
        });
    }

    connect();
})();
