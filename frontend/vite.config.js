import { readFile } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// O catálogo fica disponível apenas no servidor local de desenvolvimento.
function coordenadasLocais() {
  return {
    name: 'radarlead-coordenadas-locais',
    apply: 'serve',
    configureServer(servidor) {
      const base = new URL(servidor.config.base, 'http://localhost').pathname
      const rota = `${base}dados-locais/coordenadas-municipios.json`
      const arquivo = resolve(servidor.config.root, '.dados-locais/coordenadas-municipios.json')
      servidor.middlewares.use((req, res, next) => {
        if (req.method !== 'GET' || req.url.split('?')[0] !== rota) return next()
        if (!['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(req.socket.remoteAddress)) {
          res.statusCode = 404
          return res.end()
        }
        res.setHeader('Cache-Control', 'no-store')
        readFile(arquivo, (erro, dados) => {
          if (erro) {
            res.statusCode = erro.code === 'ENOENT' ? 404 : 500
            return res.end()
          }
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.end(dados)
        })
      })
    },
  }
}

export default defineConfig({
  server: {
    fs: {
      deny: [
        '.env', '.env.*', '*.{crt,pem,key,p12,pfx,cer,der}', '.npmrc', '.yarnrc.yml',
        '**/.git/**', '**/.dados-locais/**',
      ],
    },
  },
  plugins: [react(), tailwindcss(), coordenadasLocais()],
  test: {
    setupFiles: ['./tests/setup.js'],
  },
})
