/* Library — Frontend Application */

const API = {
    search: (params) => fetchAPI('/api/search', params),
    semantic: (params) => fetchAPI('/api/search/semantic', params),
    reports: (params) => fetchAPI('/api/reports', params),
    report: (id) => fetchAPI(`/api/reports/${id}`),
    stats: () => fetchAPI('/api/reports/stats'),
    sources: () => fetchAPI('/api/reports/sources/list'),
    ask: (body) => postAPI('/api/analysis/ask', body),
    impact: (params) => fetchAPI('/api/analysis/impact', params),
    compare: () => fetchAPI('/api/analysis/compare'),
};

async function fetchAPI(path, params = {}) {
    const url = new URL(path, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
        if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v);
    });
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

async function postAPI(path, body) {
    const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

// ---- Navigation ----
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`view-${btn.dataset.view}`).classList.add('active');

        if (btn.dataset.view === 'stats') loadStats();
        if (btn.dataset.view === 'browse') loadBrowse();
    });
});

// ---- Search ----
let searchPage = 1;

document.getElementById('search-btn').addEventListener('click', () => { searchPage = 1; doSearch(); });
document.getElementById('semantic-btn').addEventListener('click', () => doSemanticSearch());
document.getElementById('search-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { searchPage = 1; doSearch(); }
});

async function doSearch() {
    const q = document.getElementById('search-input').value;
    if (!q) return;

    const container = document.getElementById('search-results');
    container.innerHTML = '<div class="loading">Searching</div>';

    try {
        const data = await API.search({
            q,
            source: document.getElementById('filter-source').value,
            year_min: document.getElementById('filter-year-min').value,
            year_max: document.getElementById('filter-year-max').value,
            sort: document.getElementById('filter-sort').value,
            page: searchPage,
        });
        renderResults(container, data.results);
        renderPagination('search-pagination', data.total, data.page, data.per_page, (p) => {
            searchPage = p;
            doSearch();
        });
    } catch (err) {
        container.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
    }
}

async function doSemanticSearch() {
    const q = document.getElementById('search-input').value;
    if (!q) return;

    const container = document.getElementById('search-results');
    container.innerHTML = '<div class="loading">Running semantic search</div>';

    try {
        const data = await API.semantic({
            q,
            source: document.getElementById('filter-source').value,
            year_min: document.getElementById('filter-year-min').value,
            year_max: document.getElementById('filter-year-max').value,
        });
        renderSemanticResults(container, data.results);
    } catch (err) {
        container.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
    }
}

// ---- Browse ----
let browsePage = 1;

document.getElementById('browse-sort').addEventListener('change', () => { browsePage = 1; loadBrowse(); });
document.getElementById('browse-source').addEventListener('change', () => { browsePage = 1; loadBrowse(); });

async function loadBrowse() {
    const container = document.getElementById('browse-results');
    container.innerHTML = '<div class="loading">Loading</div>';

    try {
        const data = await API.reports({
            source: document.getElementById('browse-source').value,
            sort: document.getElementById('browse-sort').value,
            page: browsePage,
        });
        renderResults(container, data.results);
        renderPagination('browse-pagination', data.total, data.page, data.per_page, (p) => {
            browsePage = p;
            loadBrowse();
        });
    } catch (err) {
        container.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
    }
}

// ---- Ask (RAG) ----
document.getElementById('ask-btn').addEventListener('click', doAsk);
document.getElementById('ask-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) doAsk();
});

async function doAsk() {
    const query = document.getElementById('ask-input').value;
    if (!query) return;

    const container = document.getElementById('ask-result');
    container.innerHTML = '<div class="loading">Searching corpus and synthesizing answer</div>';

    try {
        const data = await API.ask({
            query,
            source: document.getElementById('ask-source').value || null,
            year_min: parseInt(document.getElementById('ask-year-min').value) || null,
            year_max: parseInt(document.getElementById('ask-year-max').value) || null,
        });

        let html = `<div class="ask-answer">${formatText(data.answer)}</div>`;

        if (data.sources && data.sources.length > 0) {
            html += `<div class="ask-sources"><h4>Sources (${data.chunks_used} passages from ${data.sources.length} reports)</h4>`;
            data.sources.forEach(s => {
                const sim = s.similarity ? `${(s.similarity * 100).toFixed(1)}%` : '';
                html += `
                    <div class="source-item" onclick="openReport(${s.report_id})">
                        <span>${s.source_org} &mdash; ${s.title} (${s.year || 'n.d.'})</span>
                        <span class="similarity">${sim}</span>
                    </div>`;
            });
            html += '</div>';
        }

        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
    }
}

// ---- Stats ----
async function loadStats() {
    try {
        const [stats, comparison] = await Promise.all([API.stats(), API.compare()]);

        document.getElementById('stat-total').textContent = fmt(stats.overall.total_reports);
        document.getElementById('stat-sources').textContent = fmt(stats.overall.total_sources);
        document.getElementById('stat-pages').textContent = fmt(stats.overall.total_pages);
        document.getElementById('stat-avg-pages').textContent = fmt(stats.overall.avg_pages);

        // Source breakdown table
        const sourceDiv = document.getElementById('stats-by-source');
        if (stats.by_source.length > 0) {
            let table = '<table><tr><th>Source</th><th>Reports</th><th>Avg Pages</th><th>Avg Citations</th><th>Years</th></tr>';
            stats.by_source.forEach(s => {
                table += `<tr>
                    <td>${s.source_org}</td>
                    <td>${fmt(s.count)}</td>
                    <td>${fmt(s.avg_pages)}</td>
                    <td>${fmt(s.avg_citations)}</td>
                    <td>${s.earliest || '?'} - ${s.latest || '?'}</td>
                </tr>`;
            });
            table += '</table>';
            sourceDiv.innerHTML = table;
        } else {
            sourceDiv.innerHTML = '<div class="empty-state">No data yet. Ingest some reports first.</div>';
        }

        // Comparison table
        const compDiv = document.getElementById('stats-comparison');
        if (comparison.comparison.length > 0) {
            let table = '<table><tr><th>Source</th><th>Reports</th><th>Avg Pages</th><th>Avg Downloads</th><th>Citations/Page</th><th>Downloads/Page</th><th>Impact</th></tr>';
            comparison.comparison.forEach(c => {
                table += `<tr>
                    <td>${c.source_org}</td>
                    <td>${fmt(c.total_reports)}</td>
                    <td>${fmt(c.avg_pages)}</td>
                    <td>${fmt(c.avg_downloads)}</td>
                    <td>${c.citations_per_page}</td>
                    <td>${c.downloads_per_page}</td>
                    <td>${c.avg_impact}</td>
                </tr>`;
            });
            table += '</table>';
            compDiv.innerHTML = table;
        } else {
            compDiv.innerHTML = '<div class="empty-state">No data yet.</div>';
        }
    } catch (err) {
        console.error('Stats error:', err);
    }
}

// ---- Report Detail Modal ----
async function openReport(id) {
    const modal = document.getElementById('report-modal');
    const detail = document.getElementById('report-detail');
    detail.innerHTML = '<div class="loading">Loading report</div>';
    modal.classList.add('active');

    try {
        const r = await API.report(id);
        let html = `
            <div class="report-header">
                <h2>${r.title}</h2>
                <div class="result-meta">
                    <span class="tag source">${r.source_org}</span>
                    ${r.year ? `<span>${r.year}</span>` : ''}
                    ${r.doc_type ? `<span class="tag type">${r.doc_type}</span>` : ''}
                </div>
            </div>
            <div class="report-meta-grid">
                ${metaItem('Authors', r.authors)}
                ${metaItem('Pages', r.page_count)}
                ${metaItem('Words', fmt(r.word_count))}
                ${metaItem('Downloads', fmt(r.download_count))}
                ${metaItem('Citations', fmt(r.citation_count))}
                ${metaItem('Impact Score', r.impact_score)}
                ${metaItem('Region', r.region)}
                ${metaItem('Country', r.country)}
                ${metaItem('Topics', r.topics)}
            </div>
        `;

        if (r.source_url) {
            html += `<p style="margin-bottom:16px"><a href="${r.source_url}" target="_blank" rel="noopener" style="color:var(--accent);font-size:12px">View original &rarr;</a></p>`;
        }

        if (r.summary) {
            html += `<div class="report-section"><h3>Summary</h3><p style="font-size:13px">${r.summary}</p></div>`;
        }
        if (r.key_findings) {
            html += `<div class="report-section"><h3>Key Findings</h3><p style="font-size:13px">${r.key_findings}</p></div>`;
        }
        if (r.policy_recommendations) {
            html += `<div class="report-section"><h3>Policy Recommendations</h3><p style="font-size:13px">${r.policy_recommendations}</p></div>`;
        }

        if (r.chunks && r.chunks.length > 0) {
            html += `<div class="report-section"><h3>Content Chunks (${r.chunks.length})</h3><div class="chunk-list">`;
            r.chunks.slice(0, 10).forEach(c => {
                html += `<div class="chunk">
                    <div class="chunk-header">Chunk ${c.chunk_index + 1} | Pages ${c.page_start}-${c.page_end} | ~${c.token_count} tokens</div>
                    ${c.content.substring(0, 500)}${c.content.length > 500 ? '...' : ''}
                </div>`;
            });
            if (r.chunks.length > 10) {
                html += `<div class="empty-state">+ ${r.chunks.length - 10} more chunks</div>`;
            }
            html += '</div></div>';
        }

        detail.innerHTML = html;
    } catch (err) {
        detail.innerHTML = `<div class="empty-state">Error loading report: ${err.message}</div>`;
    }
}

// Close modal
document.querySelector('.modal-close').addEventListener('click', () => {
    document.getElementById('report-modal').classList.remove('active');
});
document.getElementById('report-modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
        e.currentTarget.classList.remove('active');
    }
});

// ---- Rendering Helpers ----

function renderResults(container, results) {
    if (!results || results.length === 0) {
        container.innerHTML = '<div class="empty-state">No results found</div>';
        return;
    }

    container.innerHTML = results.map(r => `
        <div class="result-item" onclick="openReport(${r.id})">
            <div class="result-title">${r.title}</div>
            <div class="result-meta">
                <span class="tag source">${r.source_org}</span>
                ${r.year ? `<span>${r.year}</span>` : ''}
                ${r.doc_type ? `<span class="tag type">${r.doc_type}</span>` : ''}
                ${r.page_count ? `<span>${r.page_count} pages</span>` : ''}
                ${r.download_count ? `<span>${fmt(r.download_count)} downloads</span>` : ''}
                ${r.citation_count ? `<span>${fmt(r.citation_count)} citations</span>` : ''}
                ${r.impact_score ? `<span>impact: ${r.impact_score.toFixed(2)}</span>` : ''}
            </div>
            ${r.summary ? `<div class="result-summary">${r.summary.substring(0, 200)}${r.summary.length > 200 ? '...' : ''}</div>` : ''}
        </div>
    `).join('');
}

function renderSemanticResults(container, results) {
    if (!results || results.length === 0) {
        container.innerHTML = '<div class="empty-state">No results found</div>';
        return;
    }

    container.innerHTML = results.map(r => `
        <div class="result-item" onclick="openReport(${r.report_id})">
            <div class="result-title">${r.title}</div>
            <div class="result-meta">
                <span class="tag source">${r.source_org}</span>
                ${r.year ? `<span>${r.year}</span>` : ''}
                <span style="color:var(--green)">similarity: ${(r.similarity * 100).toFixed(1)}%</span>
                <span>pages ${r.page_start}-${r.page_end}</span>
            </div>
            <div class="result-summary">${r.content.substring(0, 300)}...</div>
        </div>
    `).join('');
}

function renderPagination(containerId, total, page, perPage, onPage) {
    const container = document.getElementById(containerId);
    const totalPages = Math.ceil(total / perPage);
    if (totalPages <= 1) { container.innerHTML = ''; return; }

    let html = '';
    if (page > 1) html += `<button onclick="void(0)" data-page="${page - 1}">&laquo; Prev</button>`;

    const start = Math.max(1, page - 3);
    const end = Math.min(totalPages, page + 3);
    for (let i = start; i <= end; i++) {
        html += `<button class="${i === page ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }

    if (page < totalPages) html += `<button data-page="${page + 1}">Next &raquo;</button>`;

    container.innerHTML = html;
    container.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => onPage(parseInt(btn.dataset.page)));
    });
}

function metaItem(label, value) {
    if (!value && value !== 0) return '';
    return `<div class="meta-item"><span class="label">${label}</span>${value}</div>`;
}

function fmt(n) {
    if (n === null || n === undefined) return '-';
    return Number(n).toLocaleString();
}

function formatText(text) {
    return text
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/\[Source (\d+)\]/g, '<strong>[Source $1]</strong>')
        .replace(/^/, '<p>') + '</p>';
}

// ---- Init ----
async function init() {
    try {
        const data = await API.sources();
        const sources = data.sources || [];
        const selects = ['filter-source', 'browse-source', 'ask-source'];
        selects.forEach(id => {
            const el = document.getElementById(id);
            sources.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s;
                opt.textContent = s;
                el.appendChild(opt);
            });
        });
    } catch (err) {
        console.log('Could not load sources:', err.message);
    }
}

init();
