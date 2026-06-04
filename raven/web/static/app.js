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
    let sortKey = "cpu_percent";
    let sortAsc = false;

    // ── Utilities ───────────────────────────────────────────────────────
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

    function humanBytesRate(bytes) {
        return humanBytes(bytes) + "/s";
    }

    function colorForPercent(pct) {
        if (pct < 50) return "#64ffda";
        if (pct < 80) return "#ffd93d";
        return "#ff6b6b";
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

    function timeLabels() {
        return Array.from({ length: MAX_HISTORY }, (_, i) => "");
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
        el.style.color = colorForPercent(overall);

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
        coreBars.innerHTML = cores
            .map((pct, i) => {
                const color = colorForPercent(pct);
                return `<div class="core-bar">
                    <span class="core-bar-label">C${i}</span>
                    <div class="core-bar-track"><div class="core-bar-fill" style="width:${pct}%;background:${color}"></div></div>
                </div>`;
            })
            .join("");

        // Chart
        cpuHistory.push(overall);
        if (cpuHistory.length > MAX_HISTORY) cpuHistory.shift();
        if (cpuChart) {
            cpuChart.data.datasets[0].data = [...cpuHistory];
            cpuChart.data.labels = timeLabels();
            cpuChart.options.scales.y.max = 100;
            cpuChart.update("none");
        }
    }

    function updateMemory(snap) {
        const mem = snap.memory || {};

        const el = document.getElementById("mem-overall");
        el.textContent = (mem.percent || 0).toFixed(1) + "%";
        el.style.color = colorForPercent(mem.percent || 0);

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
            memChart.data.datasets[0].data = [...memHistory];
            memChart.data.labels = timeLabels();
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
            netChart.data.datasets[0].data = [...netSentHistory];
            netChart.data.datasets[1].data = [...netRecvHistory];
            netChart.data.labels = timeLabels();
            netChart.update("none");
        }

        // Interface list
        container.innerHTML = interfaces
            .slice(0, 5)
            .map((iface) => {
                const addr = iface.addrs && iface.addrs.length > 0 ? iface.addrs[0] : "—";
                return `<div class="iface-row">
                    <span class="iface-name">${iface.name}</span>
                    <span class="iface-rate">▲ ${humanBytes(iface.bytes_sent)}  ▼ ${humanBytes(iface.bytes_recv)}</span>
                    <span class="iface-addr">${addr}</span>
                </div>`;
            })
            .join("");
    }

    function updateDisk(snap) {
        const disk = snap.disk || {};
        const partitions = disk.partitions || [];
        const container = document.getElementById("disk-partitions");

        container.innerHTML = partitions
            .slice(0, 6)
            .map((p) => {
                const color = colorForPercent(p.percent || 0);
                return `<div class="partition-row">
                    <span class="partition-mount">${p.mountpoint}</span>
                    <div class="partition-usage">
                        <div class="partition-bar"><div class="partition-bar-fill" style="width:${p.percent}%;background:${color}"></div></div>
                        <span class="partition-pct" style="color:${color}">${(p.percent || 0).toFixed(1)}%</span>
                    </div>
                    <span class="partition-size">${humanBytes(p.used || 0)} / ${humanBytes(p.total || 0)}</span>
                </div>`;
            })
            .join("");

        const io = disk.io || {};
        document.getElementById("disk-read").textContent = humanBytes(io.read_bytes || 0);
        document.getElementById("disk-write").textContent = humanBytes(io.write_bytes || 0);
    }

    function updateSensors(snap) {
        const sensors = snap.sensors || {};

        // Temperatures
        const temps = sensors.temperatures || [];
        document.getElementById("temp-list").innerHTML = temps.length
            ? "<div style='font-size:0.7rem;color:#00d2ff;text-transform:uppercase;font-weight:600;margin-bottom:0.3rem'>Temperatures</div>" +
              temps
                  .slice(0, 6)
                  .map((t) => {
                      let cls = "temp-ok";
                      if (t.critical && t.current >= t.critical) cls = "temp-crit";
                      else if (t.high && t.current >= t.high) cls = "temp-warn";
                      else if (t.current >= 80) cls = "temp-warn";
                      return `<div class="sensor-row">
                        <span class="sensor-label">${t.label}</span>
                        <span class="sensor-value ${cls}">${t.current.toFixed(0)}°C</span>
                    </div>`;
                  })
                  .join("")
            : "";

        // Fans
        const fans = sensors.fans || [];
        document.getElementById("fan-list").innerHTML = fans.length
            ? "<div style='font-size:0.7rem;color:#00d2ff;text-transform:uppercase;font-weight:600;margin-bottom:0.3rem'>Fans</div>" +
              fans
                  .slice(0, 4)
                  .map(
                      (f) =>
                          `<div class="sensor-row"><span class="sensor-label">${f.label}</span><span class="sensor-value">${f.current} RPM</span></div>`
                  )
                  .join("")
            : "";

        // Battery
        const bat = sensors.battery;
        document.getElementById("battery-info").innerHTML = bat
            ? `<div style='font-size:0.7rem;color:#00d2ff;text-transform:uppercase;font-weight:600;margin-bottom:0.3rem'>Battery</div>
               <div class="sensor-row">
                   <span class="sensor-label">${bat.power_plugged ? "⚡ Plugged" : "🔋 Battery"}</span>
                   <span class="sensor-value" style="color:${bat.percent > 20 ? "#64ffda" : "#ff6b6b"}">${(bat.percent || 0).toFixed(0)}%</span>
               </div>`
            : "";
    }

    function updateUsers(snap) {
        const users = snap.users || [];
        document.getElementById("user-count").textContent = users.length;
        const seen = new Set();
        document.getElementById("user-list").innerHTML = users
            .filter((u) => {
                if (seen.has(u.name)) return false;
                seen.add(u.name);
                return true;
            })
            .map(
                (u) =>
                    `<div class="user-row"><span>${u.name}</span><span style="color:var(--text-dim);font-size:0.75rem">${u.terminal || "—"}</span></div>`
            )
            .join("");
    }

    function updateContainers(snap) {
        const ct = snap.containers || {};
        const containers = ct.containers || [];
        const running = containers.filter((c) => c.status === "running" || c.status === "up").length;
        document.getElementById("container-count").textContent = running + " / " + containers.length;

        document.getElementById("container-list").innerHTML = containers.length
            ? containers
                  .slice(0, 10)
                  .map((c) => {
                      const isRunning = c.status === "running" || c.status === "up";
                      return `<div class="container-row">
                        <span class="container-runtime">${c.runtime}</span>
                        <span class="container-name">${c.name}</span>
                        <span class="container-status ${isRunning ? "status-running" : "status-stopped"}">${c.status}</span>
                        <span class="container-image">${c.image}</span>
                    </div>`;
                  })
                  .join("")
            : '<div style="color:var(--text-dim);font-size:0.8rem;padding:0.5rem">No containers detected</div>';
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

        const tbody = document.getElementById("process-tbody");
        tbody.innerHTML = sorted
            .slice(0, 40)
            .map(
                (p) =>
                    `<tr>
                    <td>${p.pid}</td>
                    <td>${(p.name || "").substring(0, 30)}</td>
                    <td>${(p.username || "—").substring(0, 12)}</td>
                    <td style="color:${colorForPercent(p.cpu_percent || 0)}">${(p.cpu_percent || 0).toFixed(1)}</td>
                    <td style="color:${colorForPercent(p.memory_percent || 0)}">${(p.memory_percent || 0).toFixed(1)}</td>
                    <td>${(p.status || "").substring(0, 10)}</td>
                </tr>`
            )
            .join("");
    }

    // ── Process table sorting ───────────────────────────────────────────
    document.getElementById("process-table").addEventListener("click", (e) => {
        const th = e.target.closest("th[data-sort]");
        if (!th) return;
        const key = th.getAttribute("data-sort");
        if (sortKey === key) {
            sortAsc = !sortAsc;
        } else {
            sortKey = key;
            sortAsc = false;
        }
    });

    // ── WebSocket ───────────────────────────────────────────────────────
    function connect() {
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        const url = proto + "//" + location.host + "/ws/live";
        ws = new WebSocket(url);

        ws.onopen = () => {
            const badge = document.getElementById("status-badge");
            badge.textContent = "Live";
            badge.classList.add("connected");
        };

        ws.onmessage = (event) => {
            try {
                const snap = JSON.parse(event.data);
                updateHeader(snap);
                updateCpu(snap);
                updateMemory(snap);
                updateNetwork(snap);
                updateDisk(snap);
                updateSensors(snap);
                updateUsers(snap);
                updateContainers(snap);
                updateProcesses(snap);
                document.getElementById("last-update").textContent =
                    "Last update: " + new Date().toLocaleTimeString();
            } catch (err) {
                console.error("Failed to parse snapshot:", err);
            }
        };

        ws.onclose = () => {
            const badge = document.getElementById("status-badge");
            badge.textContent = "Reconnecting…";
            badge.classList.remove("connected");
            setTimeout(connect, RECONNECT_DELAY);
        };

        ws.onerror = () => {
            ws.close();
        };
    }

    // ── Clock ───────────────────────────────────────────────────────────
    setInterval(() => {
        document.getElementById("clock").textContent = new Date().toLocaleTimeString();
    }, 1000);

    // ── Init ────────────────────────────────────────────────────────────
    cpuChart = createChart("cpu-chart", "CPU %", "#00d2ff", "rgba(0, 210, 255, 0.1)");
    memChart = createChart("mem-chart", "Memory %", "#c084fc", "rgba(192, 132, 252, 0.1)");
    netChart = createNetChart("net-chart");
    connect();
})();
