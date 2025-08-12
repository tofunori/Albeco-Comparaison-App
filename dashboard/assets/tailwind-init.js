// Tailwind CDN init for Dash
// - Use prefix to avoid Bootstrap conflicts
// - Disable preflight to preserve existing styles
if (typeof tailwind !== 'undefined' && tailwind.config) {
  tailwind.config = {
    prefix: 'tw-',
    corePlugins: {
      preflight: false,
    },
    theme: {
      extend: {
        colors: {
          brand: {
            50: '#eff6ff',
            100: '#dbeafe',
            200: '#bfdbfe',
            300: '#93c5fd',
            400: '#60a5fa',
            500: '#3b82f6',
            600: '#2563eb',
            700: '#1d4ed8',
            800: '#1e40af',
            900: '#1e3a8a'
          }
        }
      }
    }
  }
}
