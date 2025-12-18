from flask import Flask, render_template, request, send_file
import csv
import io

import matplotlib
matplotlib.use("Agg")        # Use a non-interactive backend for server-side image generation
import matplotlib.pyplot as plt
import base64
from io import BytesIO

app = Flask(__name__)


# -----------------------------
# Geometry helpers
# -----------------------------
def compute_coords(Lx, By, N, width, gap):
    """
    Compute the four corner points (P1..P4) of each rectangular turn
    of the spiral coil, starting from the outermost turn.
    """
    d = width + gap  # Center-to-center spacing between adjacent turns
    turns = []

    for t in range(1, N + 1):
        if t == 1:
            # Outermost rectangle (origin at bottom-left)
            P1 = (0.0, 0.0)
            P2 = (0.0, By)
            P3 = (Lx, By)
            P4 = (Lx, 0.0)
        else:
            # Shrink the rectangle inward each turn
            i = t - 1  # inward offset index
            x_in = i * d
            y_bottom_in = (i - 1) * d
            y_top_in = By - i * d
            x_right_in = Lx - i * d

            P1 = (x_in,       y_bottom_in)  # left, lower
            P2 = (x_in,       y_top_in)     # left, upper
            P3 = (x_right_in, y_top_in)     # right, upper
            P4 = (x_right_in, i * d)        # right, lower

        turns.append([P1, P2, P3, P4])

    return turns


def outer_path_from_turns(turns):
    """
    Flatten the per-turn corner points into a single polyline:
    P1 -> P2 -> P3 -> P4 for each turn in order.
    """
    path = []
    for (P1, P2, P3, P4) in turns:
        path.extend([P1, P2, P3, P4])
    return path


def inner_path_from_outer(outer_path, width):
    """
    Offset the spiral polyline to the INSIDE edge of the copper trace by 'width'.
    Assumes the outer path is clockwise and axis-aligned.
    Inside is always on the RIGHT side of travel for a clockwise path.
    Returns a vertex list same length as outer_path.
    """
    n = len(outer_path)
    if n < 2:
        return []

    segs = []
    for i in range(n - 1):
        x1, y1 = outer_path[i]
        x2, y2 = outer_path[i + 1]
        dx, dy = (x2 - x1), (y2 - y1)

        # Validate that each segment is axis-aligned and non-zero length
        if abs(dx) > 1e-12 and abs(dy) > 1e-12:
            raise ValueError("Non-axis-aligned segment found.")
        if abs(dx) < 1e-12 and abs(dy) < 1e-12:
            raise ValueError("Zero-length segment found.")

        # Compute right-hand offset for each segment
        if abs(dx) < 1e-12:  # vertical segment
            if dy > 0:        # going up => right is +x
                offx, offy = width, 0.0
            else:             # going down => right is -x
                offx, offy = -width, 0.0
            ori = "v"
        else:  # horizontal segment
            if dx > 0:        # going right => right is -y
                offx, offy = 0.0, -width
            else:             # going left => right is +y
                offx, offy = 0.0, width
            ori = "h"

        segs.append(((x1 + offx, y1 + offy), (x2 + offx, y2 + offy), ori))

    # Intersect consecutive offset segments to get inner vertices
    inner = [segs[0][0]]
    for i in range(1, len(segs)):
        (a1, a2, ori1) = segs[i - 1]
        (b1, b2, ori2) = segs[i]

        if ori1 == ori2:
            # Same orientation: join at start of next segment
            inner.append(b1)
        else:
            # Intersection of vertical and horizontal lines
            if ori1 == "v":
                inner.append((a1[0], b1[1]))
            else:
                inner.append((b1[0], a1[1]))

    inner.append(segs[-1][1])
    return inner


def inner_turns_from_inner_path(inner_path, N):
    """
    Regroup the inner polyline into blocks of 4 vertices per turn
    so the indexing matches the outer corners.
    """
    return [inner_path[4*k:4*k+4] for k in range(N)]


def build_spiral_path_from_turns(turns):
    """
    Build a single continuous clockwise spiral polyline from the
    per-turn corner points [P1, P2, P3, P4].

    Order: for each turn, go P1 -> P2 -> P3 -> P4.
    The connection P4_k -> P1_{k+1} is along the bottom, so
    the whole path is a clockwise spiral.
    """
    path = []

    for idx, (P1, P2, P3, P4) in enumerate(turns):
        if idx == 0:
            # Start at the outer P1
            path.extend([P1, P2, P3, P4])
        else:
            # Continue with the next turn
            path.extend([P1, P2, P3, P4])

    return path


# -----------------------------
# Plotting helper
# -----------------------------
def plot_spiral(path):
    """
    Plot the spiral path and return the image as a base64-encoded PNG.
    """
    fig, ax = plt.subplots()

    xs = [p[0] for p in path]
    ys = [p[1] for p in path]

    ax.plot(xs, ys)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.grid(True)

    # Save plot to an in-memory buffer
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    plt.close(fig)

    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_base64

# -----------------------------
# Formatting helper 
# -----------------------------
def format_points_txt(points):
    """
    Take a list of (x, y) points and return a string
    where each line is: 'x y'.
    """
    lines = []
    for x, y in points:
        lines.append(f"{x:.2f} {y:.2f}")
    return "\n".join(lines)


# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main page:
      - Displays a form for coil parameters
      - Computes outer (and optionally inner) coordinates
      - Generates a preview plot
      - Prepares .txt file for download (outer + inner points)
    """
    # Default form values
    Lx = 10
    By = 6
    width = 0.15
    gap = 0.15
    N = 5

    turns = []
    inner_turns = None
    include_inner = False

    txt_data  = None
    coil_plot = None

    if request.method == "POST":
        # Read parameters from HTML form
        Lx = float(request.form["lx"])
        By = float(request.form["by"])
        width = float(request.form["width"])
        gap = float(request.form["gap"])
        N = int(request.form["turns"])

        include_inner = (request.form.get("include_inner") == "1")

        # Compute outer turn coordinates
        turns = compute_coords(Lx, By, N, width, gap)

        # Build and plot outer spiral polyline
        outer_path = outer_path_from_turns(turns)
        coil_plot = plot_spiral(outer_path)

        # Compute inner corners if requested (not plotted, only exported)
        if include_inner:
            inner_path = inner_path_from_outer(outer_path, width)
            inner_turns = inner_turns_from_inner_path(inner_path, N)

        # Build .txt data file content
        # First all outer points, then all inner points (if enabled).
        all_points = list(outer_path)

        if include_inner and inner_path:
            # Reverse the inner path so COMSOL draws correctly
            reversed_inner = list(reversed(inner_path))
            all_points.extend(reversed_inner)

        if outer_path:
            all_points.append(outer_path[0])

        txt_data = format_points_txt(all_points)

    return render_template(
        "index.html",
        lx=Lx,
        by=By,
        width=width,
        gap=gap,
        n=N,
        turns=turns,
        include_inner=include_inner,
        inner_turns=inner_turns,
        txt_data=txt_data,
        coil_plot=coil_plot
    )


@app.route("/download", methods=["POST"])
def download():
    """
    Endpoint to download the generated .txt  as a file attachment.
    """
    data = request.form['data']
    mem = io.BytesIO()
    mem.write(data.encode("utf-8"))
    mem.seek(0)

    return send_file(
        mem,
        as_attachment=True,
        download_name="coil_coordinates.txt",
        mimetype="text/plain"
    )

## Run the app (for local testing)
## wsgi.py will handle production deployment

# if __name__ == "__main__":
#     app.run(debug=True)
