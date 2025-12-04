# ⚡ Copper Coil Coordinate Generator

A web-based utility for generating precise coordinate paths for **rectangular spiral copper coils** used in PCB inductors, wireless charging modules, and electromagnetic projects.

This tool computes outer and (optionally) inner trace coordinates and provides:
- A downloadable **CSV** of coil coordinates
- A **visual coil plot** for validation
- A clean UI for inputting design parameters

---

## 📸 Interface & Output

| Input Form | Generated Coordinates | Coil Visualization |
|-----------|----------------------|------------------|
| ![UI](images/ui.png) | ![Coordinates](images/table.png) | ![Plot](images/coil_plot.png) |

---

## 🎯 Features

- Adjustable geometry inputs: **Lx, By, Trace Width, Gap, Turns**
- Optional **inner trace corner** coordinate export
- CSV download for CAD/production use
- Auto-generated spiral visualization
- Runs fully on your local machine — **no external servers needed**

---

## 🧮 Parameter Definitions

| Parameter | Description | Units |
|----------|-------------|-------|
| Lx | Outer coil width | mm |
| By | Outer coil height | mm |
| Width | Trace width | mm |
| Gap | Spacing between turns | mm |
| Number of Turns | Spiral count | — |
| Include inner points | Offset inner copper trace | — |

---

## 🛠️ Tech Stack

- **Python 3**
- **Flask** (Web Framework)
- **Matplotlib** (Visualization)
- **HTML + CSS** (Frontend UI)

---

## 🚀 Run Locally

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/<YOUR-USERNAME>/<REPO-NAME>.git
cd <REPO-NAME>
```
### 2️⃣ Install Dependencies
```
pip install flask matplotlib

```
3️⃣ Run the App
```
python app.py

```
4️⃣ Open in Browser
```
http://127.0.0.1:5000/
```
You’re ready to generate coil paths! 🌀

📜 License

Distributed under the MIT License.
Feel free to modify and use in your own projects.

