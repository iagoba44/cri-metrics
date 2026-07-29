// ============================================================
    // INTEGRACION CON APIs REALES - CRI Metrics v2.4
    // ============================================================
    const API_BASE = '/api/v1';
    let token = localStorage.getItem('cri_token');

    async function apiCall(method, endpoint, body=null) {
        try {
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const options = { method, headers };
            if (body) options.body = JSON.stringify(body);
            const r = await fetch(API_BASE + endpoint, options);
            if (r.status === 401) {
                showLoginModal();
                throw new Error("No autenticado");
            }
            if (!r.ok) throw new Error(await r.text());
            return await r.json();
        } catch (e) {
            logToTerminal(`ERROR: API ${endpoint} -> ${e.message}`, 'error');
            return null;
        }
    }

    function showLoginModal() {
        document.getElementById('login-modal').style.display = 'flex';
    }

    function hideLoginModal() {
        document.getElementById('login-modal').style.display = 'none';
    }

    async function handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const errEl = document.getElementById('login-error');
        errEl.classList.add('hidden');
        
        try {
            const r = await fetch(API_BASE + '/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            if (!r.ok) throw new Error("Credenciales inválidas");
            const data = await r.json();
            token = data.token;
            localStorage.setItem('cri_token', token);
            hideLoginModal();
            logToTerminal('SUCCESS: Authenticated successfully', 'success');
            
            // Re-load the dashboard charts as they might have failed during init
            initTrendChart();
            initHistoryCharts();
            loadScenarios();
            loadRealData();
        } catch (err) {
            errEl.classList.remove('hidden');
            logToTerminal('ERROR: Authentication failed', 'error');
        }
    }

    function logToTerminal(msg, type='info') {
        const term = document.getElementById('terminal-content');
        const p = document.createElement('p');
        const time = new Date().toLocaleTimeString('es-ES', {hour12:false});
        let colorClass = 'text-on-surface-variant';
        if (type === 'error') colorClass = 'text-danger-alert';
        else if (type === 'success') colorClass = 'text-success-glow';
        else if (type === 'warn') colorClass = 'text-warning-amber';
        else if (type === 'system') colorClass = 'text-primary-fixed-dim';
        p.className = colorClass;
        p.innerText = `[${time}] ${msg}`;
        term.appendChild(p);
        if (term.childNodes.length > 100) term.removeChild(term.firstChild);
        term.scrollTop = term.scrollHeight;
    }

    // --- CRI Gauge Animation ---
    const arcElement = document.getElementById('cri-gauge-arc');
    const valueDisplay = document.getElementById('cri-gauge-value');
    const statusDisplay = document.getElementById('cri-gauge-status');
    const circumference = 2 * Math.PI * 88;

    function animateGauge(targetValue, duration=2000) {
        const startTime = performance.now();
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeOutBack = (x) => {
                const c1 = 1.70158;
                const c3 = c1 + 1;
                return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);
            };
            const currentValue = Math.min(targetValue * easeOutBack(progress), 100);
            valueDisplay.innerText = currentValue.toFixed(2);
            arcElement.style.strokeDashoffset = circumference - (currentValue / 100) * circumference;
            let color, glow, status;
            if (currentValue < 30) { color = '#3fb950'; glow = '0 0 10px rgba(63,185,80,0.5)'; status = 'LOW RISK'; }
            else if (currentValue < 70) { color = '#d29922'; glow = '0 0 10px rgba(210,153,34,0.5)'; status = 'MODERATE'; }
            else { color = '#f85149'; glow = '0 0 10px rgba(248,81,73,0.5)'; status = 'CRITICAL'; }
            arcElement.style.color = color;
            valueDisplay.style.color = color;
            valueDisplay.style.textShadow = glow;
            statusDisplay.innerText = status;
            if (progress < 1) requestAnimationFrame(update);
            else valueDisplay.innerText = targetValue.toFixed(2);
        }
        requestAnimationFrame(update);
    }

    // --- Cargar Datos Reales ---
    async function loadRealData() {
        logToTerminal('SYSTEM: Initializing CRI core engine v2.4...', 'system');

        // 1. Ingesta
        logToTerminal('INFO: Executing data ingestion from 10+ real-time sources...');
        const ingest = await apiCall('POST', '/run-ingestion?use_real=true');
        if (ingest) logToTerminal(`SUCCESS: ${ingest.inserted} records ingested from live APIs`, 'success');

        // 2. CRI
        logToTerminal('INFO: Calculating Composite Risk Index (CRI)...');
        const cri = await apiCall('POST', '/calculate-cri');
        if (cri && cri.data) {
            const score = cri.data.cri_score;
            const zone = cri.data.risk_zone;
            animateGauge(score);
            logToTerminal(`SUCCESS: CRI=${score} (${zone})`, 'success');

            // KPIs
            const comps = cri.data.component_scores || {};
            const kpis = ['GSPI', 'SHPD', 'LTCR', 'CFBR', 'UOR'];
            const colors = { 'GSPI':'#a2c9ff', 'SHPD':'#f85149', 'LTCR':'#3fb950', 'CFBR':'#d29922', 'UOR':'#f85149' };
            kpis.forEach(kpi => {
                const info = comps[kpi];
                if (info) {
                    const valEl = document.getElementById('kpi-' + kpi.toLowerCase() + '-val');
                    const barEl = document.getElementById('kpi-' + kpi.toLowerCase() + '-bar');
                    if (valEl) valEl.innerText = info.normalized_score.toFixed(1);
                    if (barEl) { barEl.style.width = info.normalized_score + '%'; barEl.style.background = colors[kpi]; }
                }
            });

            // Donut chart real
            const donutData = kpis.map(k => {
                const info = comps[k];
                return info ? (info.normalized_score * info.weight) : 0;
            });
            if (window.riskDonut) {
                window.riskDonut.data.datasets[0].data = donutData;
                window.riskDonut.update();
            }
        }

        // 3. TMI
        logToTerminal('INFO: Calculating Temperature Market Index (TMI)...');
        const tmi = await apiCall('GET', '/calculate-tmi');
        if (tmi && tmi.data && tmi.data.tmi_score !== null) {
            const score = tmi.data.tmi_score;
            const zone = tmi.data.zone;
            const cov = tmi.data.coverage_pct;
            document.getElementById('tmi-score-value').innerText = score.toFixed(2);
            document.getElementById('tmi-status-badge').innerText = zone;
            document.getElementById('tmi-coverage').innerText = `COVERAGE: ${cov}%`;
            const tmiDesc = zone === 'COLD' ? 'Market cooling down. Low activity detected.' :
                           zone === 'WARM' ? 'Market showing steady accumulation pressure.' :
                           'Market overheating. High risk of correction.';
            document.getElementById('tmi-desc').innerText = tmiDesc;
            // Color del termómetro
            const tmiBar = document.querySelector('.col-span-12.md\\:col-span-6.lg\\:col-span-4 .absolute.bottom-0');
            if (tmiBar) tmiBar.style.height = score + '%';
            logToTerminal(`SUCCESS: TMI=${score} (${zone}) Coverage=${cov}%`, 'success');

            // TMI Components
            const details = tmi.data.component_details || {};
            const compNames = {
                'fear_greed': 'Fear & Greed Proxy',
                'arxiv_velocity': 'arXiv Velocity',
                'hn_activity': 'Hacker News Activity',
                'hashrate': 'Global Hashrate (AI)',
                'ai_tokens': 'AI Token Performance',
                'news_coverage': 'News Coverage',
                'ai_revenue': 'AI Revenue (NVDA)'
            };
            const rows = document.querySelectorAll('.tmi-bar-row');
            let idx = 0;
            for (const [key, info] of Object.entries(details)) {
                if (idx < rows.length) {
                    const row = rows[idx];
                    const label = row.querySelector('.col-span-3');
                    const bar = row.querySelector('.tmi-bar-container');
                    const valSpan = row.querySelector('.col-span-2');
                    if (label) label.innerText = compNames[key] || key;
                    if (bar && info.value !== null) {
                        bar.dataset.metric = info.value.toFixed(1);
                        bar.dataset.pct = Math.round(info.value);
                        const fill = bar.querySelector('.tmi-bar-fill:not([style*="left"])');
                        if (fill) fill.style.width = info.value + '%';
                        // Mover indicador
                        const indicator = bar.querySelector('.absolute.top-0.bottom-0');
                        if (indicator) indicator.style.left = info.value + '%';
                    }
                    if (valSpan && info.value !== null) valSpan.innerText = info.value.toFixed(1);
                }
                idx++;
            }
        } else {
            logToTerminal('WARN: TMI data unavailable', 'warn');
        }

        // 4. Sources / Heatmap
        logToTerminal('INFO: Fetching data source health status...');
        const sources = await apiCall('GET', '/sources');
        if (sources && sources.sources) {
            const active = sources.active_kpis || 0;
            const total = sources.total_kpis || 5;
            const pct = Math.round((active / total) * 100);
            document.querySelector('.md\\:col-span-4 .text-success-glow').innerText = pct + '%';
            document.querySelector('.md\\:col-span-4 .bg-success-glow').style.width = pct + '%';

            // Actualizar heatmap
            const heatmapCells = document.querySelectorAll('.md\\:col-span-4 .grid.grid-cols-5 > div');
            const sourceMap = {};
            sources.sources.forEach(s => {
                sourceMap[s.kpi] = s;
            });
            // Mapear KPIs a celdas del heatmap (VAST, CGK, BIN, etc. es genérico en el diseño)
            // Solo marcamos colores según estado
            heatmapCells.forEach((cell, i) => {
                const span = cell.querySelector('span');
                if (!span) return;
                const label = span.innerText;
                let status = 'OFFLINE';
                let kpi = '';
                if (label === 'VAST') kpi = 'GSPI';
                else if (label === 'CGK') kpi = 'CFBR';
                else if (label === 'BIN') kpi = 'CFBR';
                else if (label === 'RSS') kpi = 'LTCR';
                else if (label === 'GTH') kpi = 'SHPD';
                else if (label === 'TWT') kpi = 'SHPD';
                else if (label === 'DIS') kpi = 'UOR';
                else if (label === 'XCH') kpi = 'UOR';
                else if (label === 'RED') kpi = 'LTCR';
                else if (label === 'CMC') kpi = 'CFBR';

                if (kpi && sourceMap[kpi]) {
                    status = sourceMap[kpi].status;
                }
                cell.className = cell.className.replace(/bg-\w+\/20|border-\w+/g, '');
                if (status === 'ACTIVE' || status === 'SIMULATED') {
                    cell.classList.add('bg-success-glow/20', 'border-success-glow');
                    span.className = span.className.replace(/text-\w+/g, 'text-success-glow');
                } else {
                    cell.classList.add('bg-danger-alert/20', 'border-danger-alert');
                    span.className = span.className.replace(/text-\w+/g, 'text-danger-alert');
                }
            });
            logToTerminal(`SUCCESS: ${active}/${total} data sources active`, 'success');
        }

        // 5. Mode & Alerts
        const mode = await apiCall('GET', '/mode');
        if (mode) {
            const isSim = mode.is_simulation;
            const badge = document.querySelector('.bg-success-glow\\/10 span');
            const dot = document.querySelector('.animate-pulse-live');
            if (isSim) {
                document.querySelector('.bg-success-glow\\/10').className = 'bg-danger-alert/10 border-b border-danger-alert/20 py-2 px-10 flex items-center gap-3';
                badge.innerText = '● SIMULATION: ' + (mode.scenario_name || mode.active_scenario);
                badge.className = 'font-label-caps text-label-caps text-danger-alert tracking-widest';
                dot.className = 'w-2 h-2 rounded-full bg-danger-alert animate-pulse-live';
                document.getElementById('tmi-mode-text').innerText = 'SIMULATION';
                document.getElementById('tmi-mode-text').className = 'font-label-caps text-[10px] text-danger-alert';
                logToTerminal(`WARN: Simulation mode active - ${mode.scenario_name || mode.active_scenario}`, 'warn');
                document.getElementById('scenarios-panel').style.display = 'block';
            } else {
                document.querySelector('.bg-success-glow\\/10').className = 'bg-success-glow/10 border-b border-success-glow/20 py-2 px-10 flex items-center gap-3';
                badge.innerText = '● LIVE MODE: 10+ Active APIs';
                badge.className = 'font-label-caps text-label-caps text-success-glow tracking-widest';
                dot.className = 'w-2 h-2 rounded-full bg-success-glow animate-pulse-live';
                document.getElementById('tmi-mode-text').innerText = 'LIVE';
                document.getElementById('tmi-mode-text').className = 'font-label-caps text-[10px] text-success-glow';
                logToTerminal('SUCCESS: Live mode - 10+ APIs connected', 'success');
                document.getElementById('scenarios-panel').style.display = 'none';
            }
        }

        // Alertas
        if (cri && cri.data && cri.data.cri_score > 65) {
            showAlert('CRITICAL RISK', `CRI at ${cri.data.cri_score} - Market entering danger zone`, 'critical');
        }
        if (tmi && tmi.data && cri && cri.data && Math.abs(tmi.data.tmi_score - cri.data.cri_score) > 40) {
            showAlert('DIVERGENCE', `TMI (${tmi.data.tmi_score}) and CRI (${cri.data.cri_score}) diverging >40pts`, 'warning');
        }

        // Update history charts
        updateHistoryCharts();

        // Consensus Diff (non-blocking)
        updateConsensusDiff();
        updateAlgorithmicStatus();
        updatePredictiveStatus();
        updateAlertLog();
        updateHeatmap();
        updateSourceMetrics();

        logToTerminal('SYSTEM: Dashboard synchronized with live market data', 'system');
    }

    // --- 24h Trend Chart (Real Data) ---
    let trendChart;
    async function initTrendChart() {
        const history = await apiCall('GET', '/history');
        let data = [45, 48, 52, 50, 55, 55]; // fallback
        let labels = Array.from({length: data.length}, (_, i) => i);
        
        if (history && history.cri && history.cri.length > 0) {
            data = history.cri.map(r => r.score);
            labels = history.cri.map((r, i) => i);
            logToTerminal(`SUCCESS: Loaded ${history.cri.length} CRI snapshots for sparkline`, 'success');
        } else {
            logToTerminal('WARN: No historical data yet, using placeholder', 'warn');
        }
        
        const ctx = document.getElementById('trendChart').getContext('2d');
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'CRI',
                    data: data,
                    borderColor: '#58a6ff',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 0,
                    fill: true,
                    backgroundColor: (ctx) => {
                        const {chartArea} = ctx.chart;
                        if (!chartArea) return null;
                        const g = ctx.chart.ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                        g.addColorStop(0, 'rgba(88,166,255,0)');
                        g.addColorStop(1, 'rgba(88,166,255,0.1)');
                        return g;
                    }
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { x: { display: false }, y: { display: false } }
            }
        });
    }

    // --- Risk Donut ---
    let riskDonut;
    function initDonut() {
        const ctx = document.getElementById('riskDonut').getContext('2d');
        riskDonut = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['GSPI', 'LTCR', 'SHPD', 'CFBR', 'UOR'],
                datasets: [{
                    data: [25, 20, 15, 20, 20],
                    backgroundColor: ['#a2c9ff', '#d29922', '#f85149', '#41474f', '#e2e2e8'],
                    borderWidth: 0,
                    hoverOffset: 20
                }]
            },
            options: {
                cutout: '80%',
                plugins: { legend: { display: false } }
            }
        });
        window.riskDonut = riskDonut;
    }

    // --- Sidebar Toggle ---
    function toggleSidebar() {
        const sidebar = document.querySelector('aside');
        sidebar.classList.toggle('hidden');
    }

    // --- Escenarios ---
    let SCENARIOS = [];
    async function loadScenarios() {
        try {
            const data = await apiCall('GET', '/scenarios');
            if (!data || !data.scenarios) return;
            SCENARIOS = data.scenarios;
            const grid = document.getElementById('scenario-grid');
            grid.innerHTML = '';
            data.scenarios.forEach(s => {
                const zoneColor = s.cri_preview <= 30 ? '#3fb950' : s.cri_preview <= 65 ? '#d29922' : '#f85149';
                const zoneClass = s.cri_preview <= 30 ? 'zone-low' : s.cri_preview <= 65 ? 'zone-moderate' : 'zone-critical';
                const div = document.createElement('div');
                div.className = 'glass-panel p-4 rounded-lg cursor-pointer hover:border-primary transition-all active:scale-95';
                div.style.borderLeft = `4px solid ${zoneColor}`;
                div.onclick = () => selectScenario(s.id);
                div.innerHTML = `
                    <div class="flex items-center gap-2 mb-2">
                        <span class="text-2xl">${s.icon || '⚡'}</span>
                        <span class="font-label-caps text-[10px] text-on-surface-variant">${s.id}</span>
                    </div>
                    <div class="font-body-md text-body-md text-on-surface font-bold">${s.name}</div>
                    <div class="font-metric-sm text-metric-sm mt-1" style="color:${zoneColor}">CRI: ${s.cri_preview}</div>
                    <div class="font-label-caps text-[9px] text-on-surface-variant mt-1">${s.description.substring(0, 40)}...</div>
                `;
                grid.appendChild(div);
            });
        } catch (e) {
            logToTerminal('ERROR: Failed to load scenarios', 'error');
        }
    }

    async function selectScenario(id) {
        logToTerminal(`INFO: Activating scenario: ${id}...`);
        const result = await apiCall('POST', '/simulate-scenario', { scenario_id: id });
        if (result && result.data) {
            const cri = result.data.cri_score;
            const zone = result.data.risk_zone;
            logToTerminal(`SUCCESS: Scenario ${id} -> CRI=${cri} (${zone})`, 'success');
            animateGauge(cri, 1500);
            // Update KPIs
            const comps = result.data.component_scores || {};
            for (const [kpi, info] of Object.entries(comps)) {
                const valEl = document.getElementById('kpi-' + kpi.toLowerCase() + '-val');
                const barEl = document.getElementById('kpi-' + kpi.toLowerCase() + '-bar');
                if (valEl) valEl.innerText = info.normalized_score.toFixed(1);
                if (barEl) barEl.style.width = info.normalized_score + '%';
            }
            // Show scenario panel
            document.getElementById('scenarios-panel').style.display = 'block';
        }
    }

    async function setRealMode() {
        logToTerminal('INFO: Switching to LIVE mode...');
        await apiCall('POST', '/mode', { mode: 'REAL' });
        document.getElementById('scenarios-panel').style.display = 'none';
        loadRealData();
    }

    // --- Alertas ---
    function showAlert(title, message, type='warning') {
        const alert = document.createElement('div');
        const color = type === 'critical' ? '#f85149' : type === 'warning' ? '#d29922' : '#3fb950';
        alert.className = 'fixed top-20 right-10 z-50 p-4 rounded-lg border shadow-lg';
        alert.style.cssText = `background: rgba(22,27,34,0.95); border-color: ${color}; box-shadow: 0 0 20px ${color}40;`;
        alert.innerHTML = `
            <div class="flex items-center gap-3">
                <span class="material-symbols-outlined" style="color:${color}">${type === 'critical' ? 'warning' : 'info'}</span>
                <div>
                    <div class="font-label-caps text-[10px] font-bold" style="color:${color}">${title}</div>
                    <div class="font-body-md text-body-md text-on-surface mt-1">${message}</div>
                </div>
            </div>
        `;
        document.body.appendChild(alert);
        setTimeout(() => { alert.style.opacity = '0'; alert.style.transition = 'opacity 0.5s'; setTimeout(() => alert.remove(), 500); }, 6000);
    }

    // --- Export ---
    async function exportData(format='json') {
        logToTerminal(`INFO: Exporting data as ${format.toUpperCase()}...`);
        const cri = await apiCall('POST', '/calculate-cri');
        const tmi = await apiCall('GET', '/calculate-tmi');
        const sources = await apiCall('GET', '/sources');
        const data = {
            timestamp: new Date().toISOString(),
            cri: cri ? cri.data : null,
            tmi: tmi ? tmi.data : null,
            sources: sources ? sources.sources : null,
        };
        if (format === 'json') {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `cri-metrics-${Date.now()}.json`; a.click();
            URL.revokeObjectURL(url);
            logToTerminal('SUCCESS: JSON export complete', 'success');
        } else {
            // CSV
            let csv = 'timestamp,kpi,raw_value,source\n';
            if (sources && sources.sources) {
                sources.sources.forEach(s => {
                    csv += `${new Date().toISOString()},${s.kpi},${s.raw_value},${s.data_source}\n`;
                });
            }
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `cri-metrics-${Date.now()}.csv`; a.click();
            URL.revokeObjectURL(url);
            logToTerminal('SUCCESS: CSV export complete', 'success');
        }
    }

    // --- Historical Charts ---
    let criHistoryChart, tmiHistoryChart;
    async function initHistoryCharts() {
        const history = await apiCall('GET', '/history');
        if (!history || !history.cri) return;
        
        const criData = history.cri.map(r => r.score);
        const criLabels = history.cri.map(r => new Date(r.timestamp).toLocaleTimeString('es-ES', {hour:'2-digit', minute:'2-digit'}));
        const tmiData = history.tmi ? history.tmi.map(r => r.score) : [];
        const tmiLabels = history.tmi ? history.tmi.map(r => new Date(r.timestamp).toLocaleTimeString('es-ES', {hour:'2-digit', minute:'2-digit'})) : [];
        
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#8b919d', font: {size:10}, maxTicksLimit: 6 }, grid: { color: 'rgba(48,54,61,0.3)' } },
                y: { ticks: { color: '#8b919d', font: {size:10} }, grid: { color: 'rgba(48,54,61,0.3)' }, min: 0, max: 100 }
            },
            elements: { point: { radius: 3, hoverRadius: 6 }, line: { tension: 0.4 } }
        };
        
        if (document.getElementById('criHistoryChart')) {
            criHistoryChart = new Chart(document.getElementById('criHistoryChart').getContext('2d'), {
                type: 'line',
                data: {
                    labels: criLabels,
                    datasets: [{
                        label: 'CRI',
                        data: criData,
                        borderColor: '#58a6ff',
                        backgroundColor: 'rgba(88,166,255,0.1)',
                        fill: true,
                        borderWidth: 2
                    }]
                },
                options: { ...commonOptions, plugins: { ...commonOptions.plugins, title: { display: true, text: 'CRI History (24h)', color: '#dae3ee', font: {size:12} } } }
            });
        }
        
        if (document.getElementById('tmiHistoryChart')) {
            tmiHistoryChart = new Chart(document.getElementById('tmiHistoryChart').getContext('2d'), {
                type: 'line',
                data: {
                    labels: tmiLabels.length ? tmiLabels : criLabels,
                    datasets: [{
                        label: 'TMI',
                        data: tmiData.length ? tmiData : criData.map(() => null),
                        borderColor: '#d29922',
                        backgroundColor: 'rgba(210,153,34,0.1)',
                        fill: true,
                        borderWidth: 2
                    }]
                },
                options: { ...commonOptions, plugins: { ...commonOptions.plugins, title: { display: true, text: 'TMI History (24h)', color: '#dae3ee', font: {size:12} } } }
            });
        }
    }

    async function updateHistoryCharts() {
        const history = await apiCall('GET', '/history');
        if (!history || !history.cri) return;
        
        const criData = history.cri.map(r => r.score);
        const criLabels = history.cri.map(r => new Date(r.timestamp).toLocaleTimeString('es-ES', {hour:'2-digit', minute:'2-digit'}));
        const tmiData = history.tmi ? history.tmi.map(r => r.score) : [];
        const tmiLabels = history.tmi ? history.tmi.map(r => new Date(r.timestamp).toLocaleTimeString('es-ES', {hour:'2-digit', minute:'2-digit'})) : [];
        
        if (criHistoryChart) {
            criHistoryChart.data.labels = criLabels;
            criHistoryChart.data.datasets[0].data = criData;
            criHistoryChart.update('none');
        }
        if (tmiHistoryChart) {
            tmiHistoryChart.data.labels = tmiLabels.length ? tmiLabels : criLabels;
            tmiHistoryChart.data.datasets[0].data = tmiData.length ? tmiData : criData.map(() => null);
            tmiHistoryChart.update('none');
        }
    }

    // --- Predictive Panel ---
    let projectionChart;
    let currentProjectionDays = 180;

    function setProjectionRange(days, btn) {
        currentProjectionDays = days;
        document.querySelectorAll('#range-selector .range-btn').forEach(b => b.classList.remove('active'));
        if (btn) btn.classList.add('active');
        updateProjectionChart();
    }

    async function updatePredictiveStatus() {
        const result = await apiCall('GET', '/predictive-status');
        if (!result || !result.data) return;

        const d = result.data;
        const ews = d.early_warning || {};
        const proj = d.projections || {};

        // TTD
        const ttdEl = document.getElementById('pred-ttd');
        const ttd = ews.days_to_collapse;
        if (ttd !== null && ttd !== undefined) {
            ttdEl.innerText = ttd;
            if (ttd < 30) { ttdEl.className = 'font-metric-xl text-metric-xl text-danger-alert'; }
            else if (ttd < 90) { ttdEl.className = 'font-metric-xl text-metric-xl text-warning-amber'; }
            else { ttdEl.className = 'font-metric-xl text-metric-xl text-on-surface'; }
        } else {
            ttdEl.innerText = 'N/A';
        }

        // EW Signal
        const signalEl = document.getElementById('pred-ew-signal');
        signalEl.innerText = ews.ew_signal || '--';
        if (ews.ew_signal === 'CRITICAL') signalEl.style.color = '#f85149';
        else if (ews.ew_signal === 'PRE_ALERT') signalEl.style.color = '#d29922';
        else signalEl.style.color = '#3fb950';

        // Collapse prob 30d
        document.getElementById('pred-collapse-30').innerText = proj.projections ? proj.projections['30'].collapse_probability_pct : '--';
        document.getElementById('pred-proj-30').innerText = proj.projections ? proj.projections['30'].projected_cri : '--';
        document.getElementById('pred-acf1').innerText = ews.autocorrelation || '--';
        document.getElementById('pred-summary').innerText = d.summary || '--';

        // Projection chart
        updateProjectionChart();
    }

    async function updateProjectionChart() {
        const proj = await apiCall('GET', '/projections?days=' + currentProjectionDays);
        if (!proj || !proj.data || !proj.data.history) return;

        const d = proj.data;
        const history = d.history.map(r => ({ x: new Date(r.timestamp), y: r.score }));

        const ctx = document.getElementById('projectionChart');
        if (!ctx) return;
        if (projectionChart) projectionChart.destroy();

        const lastTs = history[history.length - 1]?.x || new Date();
        const futurePts = [];
        if (d.projections) {
            for (const [days, p] of Object.entries(d.projections)) {
                const futTs = new Date(lastTs.getTime() + parseInt(days) * 86400000);
                futurePts.push({ x: futTs, y: p.projected_cri, upper: p.band.upper, lower: p.band.lower, collapse: p.collapse_probability_pct, days: parseInt(days) });
            }
        }

        const upperData = futurePts.map(p => ({ x: p.x, y: p.upper }));
        const lowerData = futurePts.map(p => ({ x: p.x, y: p.lower }));

        projectionChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'CRI Historical',
                        data: history,
                        borderColor: '#58a6ff',
                        borderWidth: 2,
                        tension: 0.2,
                        pointRadius: 0,
                        segment: { borderColor: '#58a6ff' },
                        fill: false,
                    },
                    {
                        label: 'CRI Projected',
                        data: futurePts,
                        borderColor: '#58a6ff',
                        borderWidth: 2,
                        borderDash: [6, 3],
                        tension: 0.2,
                        pointRadius: 4,
                        pointBackgroundColor: '#f85149',
                        fill: false,
                    },
                    {
                        label: 'Confidence Band',
                        data: upperData,
                        borderColor: 'transparent',
                        backgroundColor: 'rgba(88,166,255,0.1)',
                        pointRadius: 0,
                        tension: 0.2,
                        fill: '+1',
                    },
                    {
                        label: 'Lower Bound',
                        data: lowerData,
                        borderColor: 'transparent',
                        pointRadius: 0,
                        tension: 0.2,
                        fill: false,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, labels: { color: '#dae3ee', font: { size: 10 } } },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(ctx) {
                                const dsIdx = ctx.datasetIndex;
                                const raw = ctx.raw;
                                const date = raw.x ? new Date(raw.x).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '';
                                if (dsIdx === 0) {
                                    const score = raw.y.toFixed(2);
                                    let zone = 'LOW';
                                    if (raw.y >= 65) zone = 'CRITICAL';
                                    else if (raw.y >= 30) zone = 'MODERATE';
                                    const prevIdx = ctx.dataIndex > 0 ? ctx.dataIndex - 1 : -1;
                                    const delta = prevIdx >= 0 && ctx.dataset.data[prevIdx] ? (raw.y - ctx.dataset.data[prevIdx].y).toFixed(2) : '--';
                                    return `Date: ${date} | CRI: ${score} | Zone: ${zone} | Δ: ${delta}`;
                                }
                                if (dsIdx === 1) {
                                    const score = raw.y.toFixed(2);
                                    let zone = 'LOW';
                                    if (raw.y >= 65) zone = 'CRITICAL';
                                    else if (raw.y >= 30) zone = 'MODERATE';
                                    return `Date: ${date} | CRI: ${score} | Zone: ${zone} (Projected) | Collapse: ${raw.collapse ? raw.collapse + '%' : '--'}`;
                                }
                                return '';
                            }
                        }
                    },
                    annotation: {
                        annotations: {
                            criticalLine: { type: 'line', yMin: 65, yMax: 65, borderColor: 'rgba(248,81,73,0.6)', borderWidth: 1, borderDash: [5,5], label: { display: true, content: 'CRITICAL (65)', position: 'end', backgroundColor: 'rgba(248,81,73,0.8)', color: '#fff', font: { size: 10 } } },
                            moderateLine: { type: 'line', yMin: 30, yMax: 30, borderColor: 'rgba(63,185,80,0.6)', borderWidth: 1, borderDash: [5,5], label: { display: true, content: 'LOW (30)', position: 'end', backgroundColor: 'rgba(63,185,80,0.8)', color: '#fff', font: { size: 10 } } },
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: { unit: 'month', displayFormats: { month: 'MMM' } },
                        ticks: { color: '#8b919d', font: { size: 10 } },
                        grid: { color: 'rgba(48,54,61,0.3)' },
                    },
                    y: {
                        min: 0, max: 100,
                        ticks: { color: '#8b919d', font: { size: 10 } },
                        grid: { color: 'rgba(48,54,61,0.3)' },
                    },
                },
            },
        });
    }
    async function updateConsensusDiff() {
        const result = await apiCall('GET', '/consensus-diff');
        if (!result || !result.data) return;
        const d = result.data;
        document.getElementById('consensus-ai-score').innerText = d.ai_risk_score !== null ? d.ai_risk_score : '--';
        document.getElementById('consensus-cri-score').innerText = d.cri_algoritmico !== null ? d.cri_algoritmico : '--';
        
        // Gemini reasoning (primer LLM con score)
        let geminiReasoning = '--';
        if (d.individual) {
            const gemini = d.individual.find(r => r.score !== null && r.llm.includes('Gemini'));
            if (gemini) geminiReasoning = gemini.reasoning || '--';
        }
        document.getElementById('consensus-reasoning-short').innerText = geminiReasoning.length > 80 ? geminiReasoning.substring(0, 80) + '...' : geminiReasoning;
        
        const diffEl = document.getElementById('consensus-diff');
        if (d.diff !== null) {
            diffEl.innerText = d.diff;
            if (d.diff_alert) {
                diffEl.style.color = '#f85149';
                diffEl.className = 'font-metric-lg text-metric-lg';
                document.getElementById('consensus-alert-badge').innerHTML = '<span class="bg-danger-alert/20 border border-danger-alert rounded px-2 py-1 font-label-caps text-[10px] text-danger-alert">⚠ DIVERGENCIA</span>';
                logToTerminal(`WARN: Consenso IA diverge del CRI algorítmico (Δ=${d.diff})`, 'warn');
            } else {
                diffEl.style.color = '#3fb950';
                document.getElementById('consensus-alert-badge').innerHTML = '';
            }
        }
    }

    // --- Algorithmic Status Panel ---
    async function updateAlgorithmicStatus() {
        const result = await apiCall('GET', '/algorithmic-status');
        if (!result) return;
        const d = result;
        
        if (d.z_score) {
            document.getElementById('algo-zscore').innerText = d.z_score.z_score;
            document.getElementById('algo-zmean').innerText = d.z_score.mean;
            const alertEl = document.getElementById('algo-zalert');
            alertEl.innerText = d.z_score.severity;
            if (d.z_score.alert) {
                alertEl.style.color = '#f85149';
            } else {
                alertEl.style.color = '#3fb950';
            }
        }
        
        if (d.ema) {
            const raw = d.ema.last_24h ? d.ema.last_24h[d.ema.last_24h.length - 1] : '--';
            document.getElementById('algo-ema-raw').innerText = raw !== null ? raw : '--';
            document.getElementById('algo-ema-smoothed').innerText = d.ema.current !== null ? d.ema.current : '--';
        }
        
        if (d.decay) {
            const list = document.getElementById('algo-decay-list');
            list.innerHTML = '';
            if (d.decay.effective_weights) {
                Object.entries(d.decay.effective_weights).forEach(([kpi, weight]) => {
                    const div = document.createElement('div');
                    div.className = 'flex justify-between py-0.5';
                    const base = d.decay.report && d.decay.report[kpi] ? d.decay.report[kpi].confidence : 100;
                    const color = base > 80 ? '#3fb950' : base > 50 ? '#d29922' : '#f85149';
                    div.innerHTML = `<span class="text-on-surface-variant">${kpi}</span><span style="color:${color}">${weight} (${base}%)</span>`;
                    list.appendChild(div);
                });
            }
        }
    }

    async function updateAlertLog() {
        const result = await apiCall('GET', '/alert-log');
        if (!result || !result.alerts) return;
        const container = document.getElementById('alert-log-list');
        if (result.alerts.length === 0) {
            container.innerHTML = '<div style="color:#3fb950;padding:8px;">Sin alertas criticas</div>';
            return;
        }
        container.innerHTML = result.alerts.map(a => {
            const d = new Date(a.timestamp);
            const time = d.toLocaleString();
            return '<div style="padding: 3px 8px; border-bottom: 1px solid rgba(48,54,61,0.3); color: #f85149;">' +
                time + ' — CRI: ' + a.cri_score.toFixed(1) + ' (' + a.zone + ')</div>';
        }).join('');
    }

    async function updateHeatmap() {
        const result = await apiCall('GET', '/correlations');
        if (!result || !result.correlations) return;
        const ctx = document.getElementById('heatmapChart');
        if (!ctx) return;

        if (window.heatmapChart) window.heatmapChart.destroy();

        const kpis = result.kpis;
        const data = [];
        const bgColors = [];
        for (let i = 0; i < kpis.length; i++) {
            for (let j = 0; j < kpis.length; j++) {
                if (j <= i) {
                    const c = result.correlations.find(x => x.kpi1 === kpis[i] && x.kpi2 === kpis[j]);
                    const val = c ? c.correlation : 0;
                    data.push({ x: kpis[i] + '/' + kpis[j], y: val });
                    const r = val > 0 ? Math.round(255 * val) : 0;
                    const g = val < 0 ? Math.round(255 * Math.abs(val)) : 0;
                    bgColors.push('rgba(' + r + ',' + g + ',100,0.7)');
                }
            }
        }

        window.heatmapChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.x),
                datasets: [{
                    label: 'Correlation',
                    data: data.map(d => d.y),
                    backgroundColor: bgColors,
                    borderColor: bgColors,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: {
                    x: { min: -1, max: 1, ticks: { color: '#8b919d', font: { size: 9 } } },
                    y: { ticks: { color: '#8b919d', font: { size: 10 } } },
                }
            }
        });
    }

    async function updateSourceMetrics() {
        const result = await apiCall('GET', '/source-metrics');
        if (!result || !result.metrics) return;
        const container = document.getElementById('source-metrics-list');
        const top5 = result.metrics.slice(0, 5);
        container.innerHTML = top5.map(m => {
            const color = m.status === 'ACTIVE' ? '#3fb950' : m.status === 'STALE' ? '#d29922' : '#f85149';
            const age = m.age_seconds < 60 ? Math.round(m.age_seconds) + 's' :
                m.age_seconds < 3600 ? Math.round(m.age_seconds / 60) + 'm' :
                Math.round(m.age_seconds / 3600) + 'h';
            return '<div style="padding: 4px 8px; border-bottom: 1px solid rgba(48,54,61,0.3); display:flex;justify-content:space-between;">' +
                '<span style="color:#dae3ee;">' + (m.source.length > 16 ? m.source.substring(0, 15) + '…' : m.source) + '</span>' +
                '<span style="color:' + color + ';">' + m.status + ' (' + age + ')</span></div>';
        }).join('');
    }

    function initSSE() {
        try {
            const evtSource = new EventSource(API_BASE + '/events');
            evtSource.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    document.getElementById('status-mode').innerText = data.zone;
                    document.getElementById('status-latency').innerText = 'LIVE';
                    document.getElementById('status-region').innerText =
                        new Date(data.timestamp).toLocaleTimeString();
                } catch(e) {}
            };
            evtSource.onerror = function() { /* silent fail, polling still works */ };
        } catch(e) {}
    }

    document.addEventListener('DOMContentLoaded', () => {
        logToTerminal('SYSTEM: Boot sequence initiated...', 'system');
        initDonut();
        initSSE();
        if (!token) {
            showLoginModal();
        } else {
            initTrendChart();
            initHistoryCharts();
            loadScenarios();
            // Load real data after short delay
            setTimeout(loadRealData, 800);
        }
        // Auto-refresh every 30s
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                logToTerminal('INFO: Auto-refreshing live data...');
                loadRealData();
            }
        }, 30000);

        // Tooltip logic
        const globalTooltip = document.getElementById('global-tooltip');
        document.querySelectorAll('.tmi-bar-container').forEach(c => {
            c.addEventListener('mousemove', (e) => {
                globalTooltip.innerHTML = `<span class="text-primary-fixed-dim">${c.dataset.metric}</span>`;
                globalTooltip.style.opacity = '1';
                globalTooltip.style.left = (e.clientX + 15) + 'px';
                globalTooltip.style.top = (e.clientY - 30) + 'px';
            });
            c.addEventListener('mouseleave', () => { globalTooltip.style.opacity = '0'; });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'r' && e.ctrlKey) { e.preventDefault(); loadRealData(); }
            if (e.key === 'e' && e.ctrlKey) { e.preventDefault(); exportData('json'); }
            if (e.key === 'g' && e.ctrlKey) { e.preventDefault(); runGeminiAnalysis(); }
        });
    });

    // --- Gemini Market Analysis ---
    async function runGeminiAnalysis() {
        const modal = document.getElementById('gemini-modal');
        const content = document.getElementById('gemini-content');
        const customInput = document.getElementById('gemini-custom-prompt');
        const customPrompt = customInput ? customInput.value.trim() : '';
        
        modal.classList.remove('hidden');
        content.innerHTML = `<div class="flex items-center justify-center py-12">
            <div class="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
            <span class="font-body-md text-body-md text-on-surface-variant ml-4">Consultando a Gemini 2.5 Flash...</span>
        </div>`;
        logToTerminal('SYSTEM: Consultando Gemini 2.5 Flash para análisis de mercado...', 'system');

        const endpoint = '/gemini-analysis' + (customPrompt ? '?custom_prompt=' + encodeURIComponent(customPrompt) : '');
        const result = await apiCall('GET', endpoint);
        if (!result || !result.data) {
            content.innerHTML = `<div class="text-danger-alert font-body-md">Error: Sin respuesta de Gemini.</div>`;
            return;
        }

        const d = result.data;
        if (d.status === 'error') {
            content.innerHTML = `<div class="text-danger-alert font-body-md">${d.error || 'Error desconocido'}</div>`;
            return;
        }

        const drivers = d.key_drivers && d.key_drivers.length ? d.key_drivers.map(x => '<li class="text-on-surface">'+x+'</li>').join('') : '<li class="text-on-surface-variant">No identificados</li>';
        const recs = d.recommendations && d.recommendations.length ? d.recommendations.map(x => '<li class="text-on-surface">'+x+'</li>').join('') : '<li class="text-on-surface-variant">No disponibles</li>';

        content.innerHTML = `
            <div>
                <span class="font-label-caps text-[10px] text-primary">RESUMEN EJECUTIVO</span>
                <p class="font-body-lg text-body-lg text-on-surface mt-1 leading-relaxed">${d.market_summary || 'No disponible'}</p>
            </div>
            <div class="bg-surface-container-low p-4 rounded-lg border border-outline-variant">
                <span class="font-label-caps text-[10px] text-warning-amber">EVALUACIÓN DE RIESGO</span>
                <p class="font-body-md text-body-md text-on-surface mt-1">${d.risk_assessment || 'No disponible'}</p>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-surface-container-low p-4 rounded-lg border border-outline-variant">
                    <span class="font-label-caps text-[10px] text-danger-alert">KEY DRIVERS</span>
                    <ul class="mt-2 space-y-1.5 list-disc list-inside font-body-md text-body-md">${drivers}</ul>
                </div>
                <div class="bg-surface-container-low p-4 rounded-lg border border-outline-variant">
                    <span class="font-label-caps text-[10px] text-success-glow">RECOMENDACIONES</span>
                    <ul class="mt-2 space-y-1.5 list-disc list-inside font-body-md text-body-md">${recs}</ul>
                </div>
            </div>
            <div class="bg-surface-container-low p-4 rounded-lg border border-outline-variant">
                <span class="font-label-caps text-[10px] text-primary">OUTLOOK</span>
                <p class="font-body-md text-body-md text-on-surface mt-1">${d.outlook || 'No disponible'}</p>
            </div>
            <div class="text-right font-metric-sm text-[10px] text-on-surface-variant border-t border-outline-variant pt-3 mt-2">
                Generado por Gemini 2.5 Flash · ${new Date().toLocaleString()}
            </div>
        `;
        logToTerminal('SUCCESS: Análisis Gemini recibido con recomendaciones', 'success');
    }

    function closeGeminiModal() {
        document.getElementById('gemini-modal').classList.add('hidden');
    }

    // --- Custom What-If Simulation ---
    window.updateSliderVal = function(kpi, val) {
        document.getElementById('val-' + kpi).innerText = val;
    }

    window.applyCustomSimulation = async function() {
        logToTerminal('INFO: Executing Custom What-If Simulation...', 'system');
        const params = {
            GSPI: parseFloat(document.getElementById('slider-gspi').value),
            SHPD: parseFloat(document.getElementById('slider-shpd').value),
            LTCR: parseFloat(document.getElementById('slider-ltcr').value),
            CFBR: parseFloat(document.getElementById('slider-cfbr').value),
            UOR: parseFloat(document.getElementById('slider-uor').value)
        };

        const result = await apiCall('POST', '/simulate-custom', { params });
        if (result && result.data) {
            const score = result.data.cri_score;
            const zone = result.data.risk_zone;
            animateGauge(score);
            logToTerminal(`SUCCESS: Custom Simulation -> CRI=${score} (${zone})`, 'success');

            // Update KPIs in UI
            const comps = result.data.component_scores || {};
            const colors = { 'GSPI':'#a2c9ff', 'SHPD':'#f85149', 'LTCR':'#3fb950', 'CFBR':'#d29922', 'UOR':'#f85149' };
            for (const [kpi, info] of Object.entries(comps)) {
                const valEl = document.getElementById('kpi-' + kpi.toLowerCase() + '-val');
                const barEl = document.getElementById('kpi-' + kpi.toLowerCase() + '-bar');
                if (valEl) valEl.innerText = info.normalized_score.toFixed(1);
                if (barEl) {
                    barEl.style.width = info.normalized_score + '%';
                    barEl.style.background = colors[kpi];
                }
            }

            // Donut chart
            const donutData = ['GSPI', 'LTCR', 'SHPD', 'CFBR', 'UOR'].map(k => {
                const info = comps[k];
                return info ? (info.normalized_score * info.weight) : 0;
            });
            if (window.riskDonut) {
                window.riskDonut.data.datasets[0].data = donutData;
                window.riskDonut.update();
            }

            // Sync status mode
            const badge = document.querySelector('.bg-success-glow\\/10 span');
            const dot = document.querySelector('.animate-pulse-live');
            document.querySelector('.bg-success-glow\\/10').className = 'bg-danger-alert/10 border-b border-danger-alert/20 py-2 px-10 flex items-center gap-3';
            badge.innerText = '● SIMULATION: Custom (What-If)';
            badge.className = 'font-label-caps text-label-caps text-danger-alert tracking-widest';
            dot.className = 'w-2 h-2 rounded-full bg-danger-alert animate-pulse-live';
            document.getElementById('tmi-mode-text').innerText = 'SIMULATION';
            document.getElementById('tmi-mode-text').className = 'font-label-caps text-[10px] text-danger-alert';
        }
    }

    window.downloadExecutiveReport = async function() {
        logToTerminal('INFO: Generating Executive Market Report via Gemini...', 'system');
        try {
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const r = await fetch(API_BASE + '/download-report', { headers });
            if (!r.ok) throw new Error("No se pudo generar el reporte");
            const html = await r.text();
            
            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const w = window.open(url, '_blank');
            if (!w) {
                const a = document.createElement('a');
                a.href = url;
                a.download = `CRI-Executive-Report-${Date.now()}.html`;
                a.click();
            }
            logToTerminal('SUCCESS: Executive report opened/downloaded', 'success');
        } catch (e) {
            logToTerminal(`ERROR: Failed to generate report: ${e.message}`, 'error');
        }
    }

    window.openSettingsModal = async function() {
        logToTerminal('INFO: Fetching system configurations...', 'system');
        const res = await apiCall('GET', '/settings');
        if (res && res.settings) {
            const s = res.settings;
            document.getElementById('settings-threshold').value = s.alert_threshold || 65;
            
            const channels = s.channels || {};
            
            // Slack
            const slack = channels.slack || {};
            document.getElementById('chan-slack-enabled').checked = !!slack.enabled;
            document.getElementById('chan-slack-url').value = slack.url || '';
            
            // Discord
            const discord = channels.discord || {};
            document.getElementById('chan-discord-enabled').checked = !!discord.enabled;
            document.getElementById('chan-discord-url').value = discord.url || '';
            
            // Telegram
            const tg = channels.telegram || {};
            document.getElementById('chan-telegram-enabled').checked = !!tg.enabled;
            document.getElementById('chan-telegram-token').value = tg.bot_token || '';
            document.getElementById('chan-telegram-chatid').value = tg.chat_id || '';
            
            // Email
            const email = channels.email || {};
            document.getElementById('chan-email-enabled').checked = !!email.enabled;
            document.getElementById('chan-email-host').value = email.smtp_server || '';
            document.getElementById('chan-email-port').value = email.smtp_port || 587;
            document.getElementById('chan-email-user').value = email.username || '';
            document.getElementById('chan-email-pass').value = email.password || '';
            document.getElementById('chan-email-to').value = email.to_email || '';
            
            document.getElementById('settings-modal').classList.remove('hidden');
            logToTerminal('SUCCESS: Settings loaded into editor', 'success');
        } else {
            logToTerminal('ERROR: Failed to load system settings', 'error');
        }
    }

    window.closeSettingsModal = function() {
        document.getElementById('settings-modal').classList.add('hidden');
    }

    window.saveSystemSettings = async function() {
        logToTerminal('INFO: Saving updated system configurations...', 'system');
        const payload = {
            alert_threshold: parseFloat(document.getElementById('settings-threshold').value),
            channels: {
                slack: {
                    enabled: document.getElementById('chan-slack-enabled').checked,
                    url: document.getElementById('chan-slack-url').value
                },
                discord: {
                    enabled: document.getElementById('chan-discord-enabled').checked,
                    url: document.getElementById('chan-discord-url').value
                },
                telegram: {
                    enabled: document.getElementById('chan-telegram-enabled').checked,
                    bot_token: document.getElementById('chan-telegram-token').value,
                    chat_id: document.getElementById('chan-telegram-chatid').value
                },
                email: {
                    enabled: document.getElementById('chan-email-enabled').checked,
                    smtp_server: document.getElementById('chan-email-host').value,
                    smtp_port: parseInt(document.getElementById('chan-email-port').value) || 587,
                    username: document.getElementById('chan-email-user').value,
                    password: document.getElementById('chan-email-pass').value,
                    to_email: document.getElementById('chan-email-to').value
                }
            }
        };

        const res = await apiCall('POST', '/settings', payload);
        if (res && res.status === 'success') {
            closeSettingsModal();
            logToTerminal('SUCCESS: Configurations updated and applied', 'success');
            showAlert('SETTINGS UPDATED', 'Alert configurations saved successfully', 'success');
        } else {
            logToTerminal('ERROR: Failed to update configurations', 'error');
        }
    }