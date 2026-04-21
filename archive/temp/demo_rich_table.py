#!/usr/bin/env python3
"""Quick demo of Rich table display with asset data."""

from rich.console import Console
from rich.table import Table

console = Console()

# Example: Display batch items as a table
def show_batch_table(items: list[dict]):
    """Display ingestion batch as a formatted table."""
    table = Table(title="📦 Ingestion Batch Preview", show_header=True, header_style="bold cyan")
    table.add_column("Index", style="yellow", width=6)
    table.add_column("Filename", style="green", width=50)
    table.add_column("Subject", style="magenta", width=25)
    table.add_column("Label", style="blue", width=15)
    table.add_column("Confidence", style="cyan", width=12, justify="right")
    table.add_column("Status", width=10)
    
    for item in items:
        status = "✓ OK" if item.get("can_commit") else "✗ Error"
        status_style = "green" if item.get("can_commit") else "red"
        table.add_row(
            str(item["index"]),
            item["filename"],
            item["subject"],
            item["label"],
            f"{item['confidence']:.2f}",
            f"[{status_style}]{status}[/{status_style}]"
        )
    
    console.print(table)


# Example data (simulating PreparedBatchItem)
demo_items = [
    {
        "index": 1,
        "filename": "armchair_bernie_bright_4E85EE94.jpg",
        "subject": "Furniture/Seating/Armchair",
        "label": "Armchair",
        "confidence": 0.95,
        "can_commit": True,
    },
    {
        "index": 2,
        "filename": "table_coffee_modern_EA78D53F.jpg",
        "subject": "Furniture/Table/CoffeeTable",
        "label": "CoffeeTable",
        "confidence": 0.88,
        "can_commit": True,
    },
    {
        "index": 3,
        "filename": "lamp_pendant_brass_7F8E867A.jpg",
        "subject": "Fixture/Lighting/PendantLight",
        "label": "PendantLight",
        "confidence": 0.92,
        "can_commit": True,
    },
    {
        "index": 4,
        "filename": "plant_potted_fake_12345678.jpg",
        "subject": "Vegetation",
        "label": "PottedPlant",
        "confidence": 0.71,
        "can_commit": False,
    },
]

if __name__ == "__main__":
    show_batch_table(demo_items)
