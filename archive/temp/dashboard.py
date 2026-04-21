#!/usr/bin/env python3
"""
RR_Repo Dashboard — 3x2 grid layout
  [Clock/Stats]  [Scripts DataTable]  [Assets DataTable]
  [Sparkline   ]  [Activity Log     ]  [Todos DataTable  ]
"""

from __future__ import annotations

import csv
import random
import subprocess
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Label, Log, Sparkline, Static


REPO = Path(r"D:\rr_repo")
EFU  = REPO / "Database" / ".metadata.efu"


# ── helpers ──────────────────────────────────────────────────────────────────

def _scripts() -> list[tuple[str, str, Path]]:
    rows: list[tuple[str, str, Path]] = []
    for d in [REPO / "tools", REPO / "scripts"]:
        if d.exists():
            for f in d.glob("*.py"):
                if not f.name.startswith("__"):
                    rows.append((f.name, f"{f.stat().st_size / 1024:.0f} KB", f))
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows[:12]


def _top_assets() -> list[tuple[str, str, str]]:
    assets: list[tuple[str, str, int]] = []
    try:
        if EFU.exists():
            with open(EFU, encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    try:
                        r = int(row.get("Rating", "0") or "0")
                        if r >= 75:
                            assets.append((
                                row.get("Filename", "")[:30],
                                row.get("Subject",  "-")[:22],
                                r,
                            ))
                    except (ValueError, TypeError):
                        pass
    except Exception:
        pass
    assets.sort(key=lambda x: x[2], reverse=True)
    return [(n, s, "★" * (r // 25)) for n, s, r in assets[:10]]


def _efu_ratings_sparkline() -> list[float]:
    """Return count of assets per rating bucket as sparkline data."""
    buckets = {1: 0, 25: 0, 50: 0, 75: 0, 99: 0}
    try:
        if EFU.exists():
            with open(EFU, encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    try:
                        r = int(row.get("Rating", "0") or "0")
                        if r in buckets:
                            buckets[r] += 1
                    except (ValueError, TypeError):
                        pass
    except Exception:
        pass
    # Return as list ordered 1★ → 5★, repeated a few times to fill width
    values = list(buckets.values())
    return (values * 6)[:30]  # enough points for a nice sparkline


# ── widgets ──────────────────────────────────────────────────────────────────

class ClockStats(Static):
    """Top-left: clock + repo stats. Clock reactive, stats every 60s."""

    _time: reactive[str] = reactive("")

    def on_mount(self) -> None:
        self._tick()
        self.set_interval(1, self._tick)
        self.set_interval(60, self._draw)

    def _tick(self) -> None:
        self._time = datetime.now().strftime("%H:%M:%S")

    def watch__time(self, v: str) -> None:
        self._draw()

    def _draw(self) -> None:
        py   = len(list(REPO.rglob("*.py")))
        jpg  = len(list(REPO.rglob("*.jpg"))) + len(list(REPO.rglob("*.jpeg")))
        rows = 0
        try:
            if EFU.exists():
                with open(EFU, encoding="utf-8-sig") as fh:
                    rows = sum(1 for _ in fh) - 1
        except Exception:
            pass
        date = datetime.now().strftime("%a %d %b %Y")
        self.update(
            f"[bold cyan]{self._time}[/bold cyan]  [dim]{date}[/dim]\n\n"
            f"[yellow]Python files[/yellow]  [cyan]{py}[/cyan]\n"
            f"[yellow]Images      [/yellow]  [cyan]{jpg}[/cyan]\n"
            f"[yellow]EFU entries [/yellow]  [cyan]{rows}[/cyan]\n"
            f"[yellow]Status      [/yellow]  [green]✓ Ready[/green]"
        )


class ScriptsTable(DataTable):
    """Top-middle: navigable scripts, Enter to run."""

    BINDINGS = [Binding("enter", "run_script", "Run", show=True)]

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.add_columns("Script", "Size", "Dir")
        self._paths: dict[int, Path] = {}
        self._load()
        self.set_interval(60, self._load)

    def _load(self) -> None:
        self.clear()
        self._paths = {}
        for i, (name, size, path) in enumerate(_scripts()):
            self.add_row(name, size, path.parent.name, key=str(i))
            self._paths[i] = path

    def action_run_script(self) -> None:
        path = self._paths.get(self.cursor_row)
        if path:
            self.app.query_one(ActivityLog).add_line(
                f"[green]▶[/green] {path.name}  [{datetime.now().strftime('%H:%M:%S')}]"
            )
            self.app.notify(f"▶ Running {path.name}", timeout=3)
            subprocess.Popen(
                ["python", str(path)],
                cwd=str(REPO),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )


class AssetsTable(DataTable):
    """Top-right: highest rated assets."""

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.add_columns("Asset", "Category", "★")
        self._load()
        self.set_interval(20, self._load)

    def _load(self) -> None:
        self.clear()
        assets = _top_assets()
        if assets:
            for name, subj, stars in assets:
                self.add_row(name, subj, stars)
        else:
            self.add_row("—", "No 4+ star assets yet", "—")


class RatingsSparkline(Sparkline):
    """Bottom-left: asset ratings distribution sparkline."""

    def on_mount(self) -> None:
        self._load()
        self.set_interval(30, self._load)

    def _load(self) -> None:
        data = _efu_ratings_sparkline()
        if not any(data):
            data = [random.randint(1, 10) for _ in range(30)]
        self.data = data


class ActivityLog(Log):
    """Bottom-middle: activity feed."""

    def on_mount(self) -> None:
        self.write_line(f"[dim]Dashboard started — {datetime.now().strftime('%H:%M:%S')}[/dim]")
        self.write_line("[dim]↑↓ scripts · Enter to run · Tab switch panel[/dim]")


class TodosTable(DataTable):
    """Bottom-right: todos."""

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.add_columns("Task", "Status", "%")
        self._load()

    def _load(self) -> None:
        self.clear()
        todos = [
            ("Ingest Q2 assets",        "in_progress", "[blue]80%[/blue]"),
            ("Update keyword table",    "pending",      "[yellow]—[/yellow]"),
            ("Review material library", "pending",      "[yellow]—[/yellow]"),
            ("Vector reindex",          "done",         "[green]✓[/green]"),
        ]
        colors = {"pending": "yellow", "in_progress": "blue", "done": "green"}
        for task, status, pct in todos:
            c = colors.get(status, "white")
            self.add_row(task, f"[{c}]{status}[/{c}]", pct)


# ── app ──────────────────────────────────────────────────────────────────────

class DashboardApp(App):

    TITLE = "RR_Repo Dashboard"
    CSS = """
    Grid {
        grid-size: 3 2;
        grid-gutter: 1;
        padding: 1;
        height: 1fr;
    }

    /* labels above each cell */
    .cell-label {
        height: 1;
        text-style: bold;
        background: $panel;
        color: $text;
        padding: 0 1;
    }

    /* individual cells */
    #cell-clock   { border: round $primary;   }
    #cell-scripts { border: round $warning;   }
    #cell-assets  { border: round $success;   }
    #cell-spark   { border: round $accent;    }
    #cell-log     { border: round $secondary; }
    #cell-todos   { border: round $error;     }

    RatingsSparkline { height: 1fr; }

    /* sparkline cell is shorter */
    #cell-spark { height: 12; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "focus_next", "Next", show=True),
        Binding("shift+tab", "focus_previous", "Prev", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Grid():
            # Row 1
            with Static(id="cell-clock"):
                yield Label("⏱ Clock & Stats", classes="cell-label")
                yield ClockStats()
            with Static(id="cell-scripts"):
                yield Label("🔧 Scripts  (Enter = run)", classes="cell-label")
                yield ScriptsTable()
            with Static(id="cell-assets"):
                yield Label("⭐ Highest Rated Assets", classes="cell-label")
                yield AssetsTable()
            # Row 2
            with Static(id="cell-spark"):
                yield Label("📈 Ratings Distribution", classes="cell-label")
                yield RatingsSparkline([], summary_function=max)
            with Static(id="cell-log"):
                yield Label("📋 Activity Log", classes="cell-label")
                yield ActivityLog()
            with Static(id="cell-todos"):
                yield Label("✅ Todos", classes="cell-label")
                yield TodosTable()
        yield Footer()


if __name__ == "__main__":
    DashboardApp().run()
