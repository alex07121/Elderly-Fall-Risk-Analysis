import { createApp } from 'vue'

import App from '@/App.vue'
import { registerPlugins } from '@core/utils/plugins'

// Styles
import '@core/scss/template/index.scss'
import '@styles/styles.scss'

const fakeApiEnabled = import.meta.env.VITE_ENABLE_FAKE_API === 'true'
  || import.meta.env.VITE_ENABLE_MSW === 'true'

/**
 * Remove a mock worker left behind by an earlier template run.  Merely
 * skipping worker.start() is not enough: an already registered service
 * worker can continue intercepting requests for the current tab.
 */
async function disableLegacyMockServiceWorker() {
  if (fakeApiEnabled || !('serviceWorker' in navigator))
    return

  try {
    const registrations = await navigator.serviceWorker.getRegistrations()
    const mockRegistrations = registrations.filter(registration => {
      const workerUrls = [
        registration.active?.scriptURL,
        registration.waiting?.scriptURL,
        registration.installing?.scriptURL,
      ].filter(Boolean)

      return workerUrls.some(scriptUrl => {
        try {
          return new URL(scriptUrl as string, window.location.href).pathname.endsWith('/mockServiceWorker.js')
        }
        catch {
          return false
        }
      })
    })

    if (!mockRegistrations.length)
      return

    // Tell MSW to stop intercepting this client immediately, then unregister
    // the registration so future reloads cannot re-activate it.  Send the
    // message to the matching worker rather than an unrelated controller.
    mockRegistrations.forEach(registration => {
      registration.active?.postMessage({ type: 'MOCK_DEACTIVATE' })
    })
    await Promise.all(mockRegistrations.map(registration => registration.unregister()))
  }
  catch {
    // A browser that blocks service-worker inspection should not prevent the
    // application from mounting.  The real API and UI remain usable.
  }
}

async function bootstrap() {
  await disableLegacyMockServiceWorker()

  // Create vue app
  const app = createApp(App)

  // Register plugins
  registerPlugins(app)

  // Mount vue app
  app.mount('#app')
}

void bootstrap()
