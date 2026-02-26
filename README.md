# INF2007-IoT-Project-

## Links

- Final Report (Google Docs): `<add-report-link>`
- Poster: `<add-poster-link>`
- Demo Video: `<add-demo-video-link>`

## Repo Structure

- `firmware/node/`: Embedded node firmware source and node-side scripts.
- `firmware/gateway/`: Gateway firmware/services for LoRa-to-MQTT bridging.
- `dashboard/`: UI/dashboard application and related assets.
- `docs/`: Working documentation for topics, schemas, and experiment logs.
- `docs/figures/`: Diagrams and images referenced by documentation.

## Dashboard Setup

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

> **Note:** Dashboard runs in simulation mode by default. To connect to the live MQTT broker, set `USE_REAL_MQTT = true` and update `MQTT_BROKER_URL` in `src/hooks/useDashboard.js`.
