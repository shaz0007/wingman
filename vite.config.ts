import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Support the requested lowercase vite_api_base_url as well as Vite's standard VITE_* names.
// Only variables with these explicit public prefixes are exposed to browser code.
export default defineConfig({
  plugins: [react()],
  envPrefix: ['VITE_', 'vite_'],
})
