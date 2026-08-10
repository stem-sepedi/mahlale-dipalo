<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polelo — Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, -apple-system, sans-serif; background: #f5f5f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        h1 { font-size: 1.5rem; margin-bottom: 0.5rem; color: #1a1a1a; }
        p { color: #666; margin-bottom: 1.5rem; font-size: 0.9rem; }
        label { display: block; margin-bottom: 0.25rem; font-weight: 500; font-size: 0.85rem; color: #333; }
        input { width: 100%; padding: 0.6rem; border: 1px solid #ddd; border-radius: 4px; font-size: 1rem; margin-bottom: 1rem; }
        input:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37,99,235,0.2); }
        button { width: 100%; padding: 0.7rem; background: #2563eb; color: white; border: none; border-radius: 4px; font-size: 1rem; cursor: pointer; }
        button:hover { background: #1d4ed8; }
        .error { color: #dc2626; font-size: 0.85rem; margin-bottom: 1rem; display: none; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Polelo</h1>
        <p>STEM Sepedi Translation Layer — Sign in</p>
        <div id="error" class="error"></div>
        <form id="loginForm">
            <label for="username">Username</label>
            <input type="text" id="username" name="username" required autocomplete="username">
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required autocomplete="current-password">
            <button type="submit">Sign In</button>
        </form>
    </div>
    <script>
        const API = window.location.origin + '/api/v1' || '';
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const errEl = document.getElementById('error');
            errEl.style.display = 'none';
            try {
                const resp = await fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: document.getElementById('username').value,
                        password: document.getElementById('password').value,
                    }),
                });
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.detail || 'Login failed');
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                window.location.href = 'search.php';
            } catch (err) {
                errEl.textContent = err.message;
                errEl.style.display = 'block';
            }
        });
    </script>
</body>
</html>
