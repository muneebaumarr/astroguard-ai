# Reference-inspired orbital dashboard

Overview now uses a full spacewalk scene with translucent navy telemetry instruments,
amber API-backed sparklines, white numeric readings, a compact navigation rail and
fictional crew selector cards. Health readings are positioned on the left; cabin
CO2/radiation instruments sit across the top; crew and mission context sit on the right.
Responsive tablet/mobile layouts retain all five instruments and accessible navigation.
Simulation controls, detailed charts, summaries and recent alerts remain below the scene.

All measurements still come from the existing FastAPI/SQLite workflows. Unsupported
reference-image fields such as suit pressure, nitrogen mass, bone mass, battery and
external temperature were not fabricated. The crew-card bars are decorative, hidden
from assistive technology, and do not claim voice activity or actual communications.
Fictional avatars use initials rather than photographs of real people labelled as demo crew.

Background asset: `frontend/public/images/spacewalk.jpg`, downloaded from
https://images-assets.nasa.gov/image/iss068e026356/iss068e026356~large.jpg .
Official source: [NASA: Astronaut Frank Rubio installs a roll-out solar array during a spacewalk](https://www.nasa.gov/image-article/astronaut-frank-rubio-installs-roll-out-solar-array-during-spacewalk/).
Credit: NASA, image iss068e026356, December 3, 2022. The scene is illustrative only;
its actual astronaut is not the selected fictional profile and it does not represent
the timestamp or conditions of the demo readings. An attribution link appears in the UI.
The image is stored locally (~227 kB), so it does not depend on a remote image request
while using the app. No NASA endorsement is implied.

Changed files: Dashboard.jsx, AppShell.jsx, global.css, App.test.jsx and the new local
image/documentation. No backend, database, contracts or measurement units changed.
