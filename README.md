# Smart Manufacturing Digital Twin, Yuva Yodha 2026

This project was built for the Yuva Yodha Energy Tech Hackathon 2026, organized by Schneider Electric, under the Smart Manufacturing theme.

The problem we are trying to solve is that small and medium manufacturers in India usually have no real visibility into how their machines use energy, no early warning when something starts to break down, and no easy way to plan production around cheaper or cleaner electricity hours. Big factories can afford enterprise systems like Schneider's own EcoStruxure to handle this, but most SMEs cannot. So instead of building five separate tools, we built one shared prediction engine, a digital twin, and made everything else read from it.

## What is in this repo

There are two folders.

**dashboard**
The web app. Built with React, Vite, Tailwind and Supabase. It has five screens: live power draw, fault alerts, the production schedule, the BEE energy audit report, and the carbon emissions report.

**digital twin**
The Python simulation that stands in for a real factory, since the hackathon brief did not require physical hardware. It generates realistic sensor data for three machines, a motor, a compressor and a furnace, along with what the twin expects those readings to be at that point in time. When a machine's real readings start drifting away from what the twin expected, that gap is how a developing fault gets caught early. The script also writes production scheduling, audit and carbon emission data.

## How the two parts work together

Both the dashboard and the digital twin connect to the same Supabase project. The twin writes data in, the dashboard reads it out live. So if you run main.py and let the fault injection kick in on the compressor, you can actually watch the dashboard's fault alert screen update a few seconds later on its own. That live link between the two is really the proof that the whole thing works end to end, not just two demos sitting side by side.

## Running the dashboard

Open a terminal inside the dashboard folder.

```
npm install
npm run dev
```

It will print a local link, usually something like http://localhost:5173. Open that in a browser.

## Running the digital twin

Open a terminal inside the digital twin folder.

```
pip install -r requirements.txt
python main.py
```

Let it run for a couple of minutes, past the fault injection step (step 40 by default, this can be changed in config.py). Then stop it and run:

```
python visualize.py
```

This generates compressor_fault_demo.png and compressor_power_demo.png, which show the expected and actual readings tracking together and then pulling apart once the fault starts.

## Why we went this way

While researching, we looked closely at what Schneider Electric already sells, EcoStruxure for real estate and logistics, Wiser Home for residential, machine builder solutions and so on. Almost all of it is aimed at large enterprises or single homes, not small manufacturers running older, uninstrumented equipment. That is the gap we are trying to fill here, by keeping hardware cost under a few thousand rupees, using one twin instead of five disconnected tools, and designing so that a cluster of nearby SMEs could eventually pool their energy flexibility together, similar to how BEE already groups manufacturing clusters for support in India.

## Team

Built for Yuva Yodha Energy Tech Hackathon 2026, Smart Manufacturing theme.
