import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'app.nightguide',
  appName: 'NightGuide',
  webDir: 'www',
  backgroundColor: '#0d0d14',
  android: {
    // Bundled static web app; no remote API traffic in v1.
    allowMixedContent: false,
  },
  ios: {
    contentInset: 'automatic',
  },
};

export default config;
