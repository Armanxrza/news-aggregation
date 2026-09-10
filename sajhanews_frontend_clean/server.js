const next = require('next')
const http = require('http')

const dev = process.env.NODE_ENV !== 'production'
const app = next({ dev })
const handle = app.getRequestHandler()
const port = process.env.PORT || 3000

app.prepare()
  .then(() => {
    const server = http.createServer((req, res) => {
      handle(req, res).catch(err => {
        console.error('Request error:', err)
        if (!res.headersSent) {
          res.statusCode = 500
          res.end('Internal Server Error: ' + err.message)
        }
      })
    })

    server.listen(port, () => {
      console.log(`> Ready on port ${port} (PID: ${process.pid})`)
    })
  })
  .catch(err => {
    console.error('Next.js prepare failed:', err)
    // Always start a server on the port so Passenger never hangs
    const server = http.createServer((req, res) => {
      res.statusCode = 500
      res.setHeader('Content-Type', 'text/plain; charset=utf-8')
      res.end(`Next.js failed to start:\n\n${err.stack || err.message}`)
    })
    server.listen(port, () => {
      console.log(`> Fallback error server listening on port ${port}`)
    })
  })
