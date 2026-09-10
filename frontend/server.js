const http = require('http')
const fs = require('fs')
const path = require('path')

process.env.NODE_ENV = 'production';
process.env.NEXT_PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.sajhanews.yagyatech.com.np';

const port = process.env.PORT || 3000

// Polyfills for Node.js < 20 (e.g. Node 18 on cPanel)
if (!Array.prototype.toSorted) {
  Array.prototype.toSorted = function(compareFn) {
    return [...this].sort(compareFn);
  };
}
if (!Array.prototype.toReversed) {
  Array.prototype.toReversed = function() {
    return [...this].reverse();
  };
}
if (!Array.prototype.toSpliced) {
  Array.prototype.toSpliced = function(start, deleteCount, ...items) {
    const copy = [...this];
    copy.splice(start, deleteCount, ...items);
    return copy;
  };
}
if (!Array.prototype.with) {
  Array.prototype.with = function(index, value) {
    const copy = [...this];
    copy[index] = value;
    return copy;
  };
}

function logError(msg) {
  try {
    fs.appendFileSync(path.join(__dirname, 'frontend_error.log'), `[${new Date().toISOString()}] ${msg}\n\n`);
  } catch (e) {}
}

function serveError(errTitle, errDetails, solution) {
  const server = http.createServer((req, res) => {
    res.statusCode = 500;
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.end(`<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SajhaNews - Server Diagnostics</title>
<style>
body { font-family: system-ui, -apple-system, sans-serif; background: #090d16; color: #e2e8f0; padding: 40px 20px; line-height: 1.6; margin: 0; }
.card { max-width: 800px; margin: 0 auto; background: #131b2e; border: 1px solid #1e293b; border-radius: 12px; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
h1 { color: #f43f5e; font-size: 24px; margin-top: 0; }
.alert { background: rgba(244,63,94,0.1); border-left: 4px solid #f43f5e; padding: 16px; margin: 20px 0; border-radius: 4px; }
.fix { background: rgba(16,185,129,0.1); border-left: 4px solid #10b981; padding: 16px; margin: 20px 0; border-radius: 4px; color: #a7f3d0; }
pre { background: #0b1120; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 13px; color: #cbd5e1; white-space: pre-wrap; word-break: break-word; }
.meta { font-size: 12px; color: #64748b; margin-top: 24px; border-top: 1px solid #1e293b; padding-top: 16px; }
</style>
</head>
<body>
<div class="card">
  <h1>⚠️ SajhaNews Frontend Startup Issue</h1>
  <div class="alert"><strong>Problem:</strong> ${errTitle}</div>
  <div class="fix"><strong>Recommended Fix:</strong><br>${solution}</div>
  <h3>Technical Details / Trace:</h3>
  <pre>${errDetails}</pre>
  <div class="meta">Current Node Version: <b>${process.version}</b> | Server Port: <b>${port}</b> | Directory: <code>${__dirname}</code></div>
</div>
</body>
</html>`);
  });

  server.listen(port, () => {
    console.log(`Diagnostic server running on port ${port}`);
  });
}

let next;
try {
  next = require('next');
} catch (err) {
  logError('Failed to require next:\n' + (err.stack || err.message));
  serveError(
    "Missing 'next' or dependencies in node_modules",
    err.stack || err.message,
    "In cPanel, open <b>Setup Node.js App</b> and click the <b>Run NPM Install</b> button, then click <b>Restart</b>."
  );
}

if (next) {
  try {
    const dev = process.env.NODE_ENV !== 'production';
    const app = next({ dev });
    const handle = app.getRequestHandler();

    app.prepare()
      .then(() => {
        const server = http.createServer((req, res) => {
          handle(req, res).catch(err => {
            console.error('Request error:', err);
            logError('Request error: ' + (err.stack || err.message));
            if (!res.headersSent) {
              res.statusCode = 500;
              res.end('Internal Server Error: ' + err.message);
            }
          });
        });

        server.listen(port, () => {
          console.log(`> Ready on port ${port} (PID: ${process.pid})`);
        });
      })
      .catch(err => {
        logError('Next.js prepare failed:\n' + (err.stack || err.message));
        serveError(
          "Next.js preparation failed",
          err.stack || err.message,
          "If the error mentions <code>toSorted is not a function</code>, switch the Node.js version to <b>Node 20.x</b> in cPanel 'Setup Node.js App' and click <b>Restart</b>."
        );
      });
  } catch (err) {
    logError('Next.js initialization exception:\n' + (err.stack || err.message));
    serveError(
      "Next.js initialization exception",
      err.stack || err.message,
      "Please verify your Node.js version in cPanel (recommended: Node 20.x) and click Restart."
    );
  }
}
