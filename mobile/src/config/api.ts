// The current development workflow targets only the iOS Simulator. `localhost`
// uses the app's iOS local-network transport exception without enabling insecure
// HTTP globally. Reintroduce environment-based URLs for hosted backend support.
export const API_BASE_URL = 'http://localhost:8000';
