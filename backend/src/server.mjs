import http from 'node:http'

const host = process.env.HOST || '127.0.0.1'
const port = Number(process.env.PORT || 8000)

const json = (response, statusCode, body) => {
  response.writeHead(statusCode, {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET,POST,PATCH,DELETE,OPTIONS',
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'application/json; charset=utf-8',
  })
  response.end(JSON.stringify(body))
}

const server = http.createServer((request, response) => {
  const url = new URL(request.url || '/', `http://${request.headers.host}`)

  if (request.method === 'OPTIONS') {
    response.writeHead(204, {
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Allow-Methods': 'GET,POST,PATCH,DELETE,OPTIONS',
      'Access-Control-Allow-Origin': '*',
    })
    response.end()
    return
  }

  if (request.method === 'GET' && url.pathname === '/') {
    json(response, 200, {
      service: 'agenthub-backend',
      status: 'ok',
      health: '/health',
    })
    return
  }

  if (request.method === 'GET' && (url.pathname === '/health' || url.pathname === '/api/health')) {
    json(response, 200, {
      service: 'agenthub-backend',
      status: 'ok',
      timestamp: new Date().toISOString(),
    })
    return
  }

  json(response, 404, {
    error: 'not_found',
    message: `No route registered for ${request.method} ${url.pathname}`,
  })
})

server.listen(port, host, () => {
  console.log(`AgentHub backend listening on http://${host}:${port}`)
})
