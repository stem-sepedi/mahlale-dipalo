<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polelo — Search</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, -apple-system, sans-serif; background: #f5f5f5; min-height: 100vh; }
        .header { background: white; padding: 1rem 2rem; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 1.25rem; color: #1a1a1a; }
        .header a { color: #666; text-decoration: none; font-size: 0.85rem; }
        .search-bar { max-width: 700px; margin: 2rem auto; padding: 0 1rem; }
        .search-bar input { width: 100%; padding: 0.75rem 1rem; font-size: 1rem; border: 1px solid #ddd; border-radius: 6px; }
        .search-bar input:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37,99,235,0.2); }
        .filters { max-width: 700px; margin: 0.5rem auto; padding: 0 1rem; display: flex; gap: 1rem; }
        .filters select { padding: 0.4rem; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem; }
        .results { max-width: 700px; margin: 1rem auto; padding: 0 1rem; }
        .result-card { background: white; padding: 1rem; margin-bottom: 0.75rem; border-radius: 6px; border: 1px solid #e5e7eb; }
        .result-card h3 { font-size: 1rem; color: #1a1a1a; margin-bottom: 0.25rem; }
        .result-card .meta { font-size: 0.8rem; color: #888; }
        .result-card .score { float: right; background: #e0f2fe; color: #0369a1; padding: 0.1rem 0.5rem; border-radius: 10px; font-size: 0.75rem; }
        .facets { display: flex; gap: 1rem; margin-top: 0.5rem; font-size: 0.8rem; color: #666; }
        .facets span { background: #f3f4f6; padding: 0.15rem 0.5rem; border-radius: 4px; }
        .empty { text-align: center; color: #888; padding: 3rem; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Polelo Search</h1>
        <a href="login.php">Sign Out</a>
    </div>
    <div class="search-bar">
        <input type="text" id="q" placeholder="Search STEM terms in Sepedi or English..." autofocus>
    </div>
    <div class="filters">
        <select id="domain">
            <option value="">All Domains</option>
            <option value="Biology">Biology</option>
            <option value="Physics">Physics</option>
            <option value="Chemistry">Chemistry</option>
            <option value="Mathematics">Mathematics</option>
            <option value="Geography">Geography</option>
        </select>
        <select id="grade">
            <option value="">All Grades</option>
            <option value="5">Grade 5</option>
            <option value="7">Grade 7</option>
            <option value="8">Grade 8</option>
            <option value="9">Grade 9</option>
            <option value="10">Grade 10</option>
            <option value="11">Grade 11</option>
            <option value="12">Grade 12</option>
        </select>
    </div>
    <div class="results" id="results">
        <div class="empty">Type to search for STEM concepts...</div>
    </div>
    <script>
        const token = localStorage.getItem('access_token');
        if (!token) window.location.href = 'login.php';

        let debounce;
        const qEl = document.getElementById('q');
        const domainEl = document.getElementById('domain');
        const gradeEl = document.getElementById('grade');
        const resultsEl = document.getElementById('results');

        async function search() {
            const q = qEl.value.trim();
            if (!q) { resultsEl.innerHTML = '<div class="empty">Type to search for STEM concepts...</div>'; return; }
            const params = new URLSearchParams({ q, include_translations: 'true' });
            if (domainEl.value) params.set('domain', domainEl.value);
            if (gradeEl.value) params.set('grade', gradeEl.value);
            try {
                const resp = await fetch('/search?' + params, { headers: { 'Authorization': 'Bearer ' + token } });
                if (resp.status === 401) { window.location.href = 'login.php'; return; }
                const data = await resp.json();
                if (!data.results || data.results.length === 0) {
                    resultsEl.innerHTML = '<div class="empty">No results found.</div>';
                    return;
                }
                resultsEl.innerHTML = data.results.map(r => `
                    <div class="result-card">
                        <span class="score">${(r.score * 100).toFixed(0)}%</span>
                        <h3>${r.entity.name_en || r.entity.sepedi_term || ''}</h3>
                        <div class="meta">${r.type}${r.entity.domain ? ' — ' + r.entity.domain : ''}</div>
                        ${r.entity.grade_levels ? '<div class="facets">' + r.entity.grade_levels.map(g => '<span>Grade ' + g + '</span>').join('') + '</div>' : ''}
                    </div>
                `).join('');
            } catch (err) {
                resultsEl.innerHTML = '<div class="empty">Search failed: ' + err.message + '</div>';
            }
        }

        qEl.addEventListener('input', () => { clearTimeout(debounce); debounce = setTimeout(search, 300); });
        domainEl.addEventListener('change', search);
        gradeEl.addEventListener('change', search);
    </script>
</body>
</html>
