#!/usr/bin/env python3
"""Rich table examples for asset ingestion display."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


# ============================================================================
# EXAMPLE 1: Simple Asset Table
# ============================================================================
def example_1_simple_table():
    """Basic table with asset metadata."""
    console.print("\n[bold cyan]EXAMPLE 1: Simple Asset Table[/bold cyan]\n")
    
    table = Table(title="Assets in Batch")
    table.add_column("File", style="green")
    table.add_column("Type", style="cyan")
    table.add_column("Size", justify="right")
    
    table.add_row("chair_01.jpg", "Furniture", "2.4 MB")
    table.add_row("lamp_02.jpg", "Fixture", "1.8 MB")
    table.add_row("plant_03.jpg", "Vegetation", "3.1 MB")
    
    console.print(table)


# ============================================================================
# EXAMPLE 2: Status Table with Colors
# ============================================================================
def example_2_status_table():
    """Table with status indicators."""
    console.print("\n[bold cyan]EXAMPLE 2: Status Table with Colors[/bold cyan]\n")
    
    table = Table(title="Ingestion Status")
    table.add_column("Filename", style="yellow")
    table.add_column("Status", width=15)
    table.add_column("Progress", justify="right")
    
    table.add_row("asset_1.jpg", "[green]✓ Complete[/green]", "[green]100%[/green]")
    table.add_row("asset_2.jpg", "[yellow]⏳ Processing[/yellow]", "[yellow]45%[/yellow]")
    table.add_row("asset_3.jpg", "[red]✗ Error[/red]", "[red]0%[/red]")
    table.add_row("asset_4.jpg", "[blue]⊘ Skipped[/blue]", "[blue]—[/blue]")
    
    console.print(table)


# ============================================================================
# EXAMPLE 3: Metadata Detail Table
# ============================================================================
def example_3_metadata_table():
    """Detailed metadata fields."""
    console.print("\n[bold cyan]EXAMPLE 3: Asset Metadata Detail[/bold cyan]\n")
    
    table = Table(title="Asset Details: armchair_bright_01.jpg")
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="white")
    
    table.add_row("Filename", "armchair_bright_01.jpg")
    table.add_row("Subject", "Furniture/Seating/Armchair")
    table.add_row("Title", "Modern Armchair")
    table.add_row("Company", "Hermann Miller")
    table.add_row("Album", "Contemporary")
    table.add_row("Color (cp_0)", "Teal Blue")
    table.add_row("Location (cp_1)", "Living Room")
    table.add_row("CRC-32", "4E85EE94")
    table.add_row("Tags", "modern; minimalist; comfortable")
    
    console.print(table)


# ============================================================================
# EXAMPLE 4: Batch Summary with Emojis
# ============================================================================
def example_4_summary_table():
    """Summary statistics with emoji."""
    console.print("\n[bold cyan]EXAMPLE 4: Batch Summary[/bold cyan]\n")
    
    table = Table(title="Ingestion Summary")
    table.add_column("Metric", style="magenta", width=20)
    table.add_column("Count", justify="right", style="cyan")
    table.add_column("Percentage", justify="right", style="yellow")
    
    table.add_row("📦 Total", "10", "100%")
    table.add_row("✓ Success", "8", "80%")
    table.add_row("⚠ Warnings", "1", "10%")
    table.add_row("✗ Errors", "1", "10%")
    
    console.print(table)


# ============================================================================
# EXAMPLE 5: Category Breakdown
# ============================================================================
def example_5_category_table():
    """Asset types breakdown."""
    console.print("\n[bold cyan]EXAMPLE 5: Category Breakdown[/bold cyan]\n")
    
    table = Table(title="Assets by Category")
    table.add_column("Category", style="green")
    table.add_column("Count", justify="right", style="cyan")
    table.add_column("Examples", style="yellow")
    
    table.add_row("Furniture", "15", "armchair, sofa, table")
    table.add_row("Fixture", "8", "lamp, switch, outlet")
    table.add_row("Vegetation", "5", "tree, plant, grass")
    table.add_row("Material", "12", "wood, marble, fabric")
    
    console.print(table)


# ============================================================================
# EXAMPLE 6: Complex Table (Like ingest_asset.py batch)
# ============================================================================
def example_6_complex_batch_table():
    """Full batch preview with multiple columns."""
    console.print("\n[bold cyan]EXAMPLE 6: Complex Batch Preview[/bold cyan]\n")
    
    table = Table(
        title="📦 Ingestion Batch Preview",
        show_header=True,
        header_style="bold white on blue"
    )
    table.add_column("ID", style="dim yellow", width=4)
    table.add_column("Filename", style="cyan", width=40)
    table.add_column("Category", style="green", width=25)
    table.add_column("Label", style="magenta", width=18)
    table.add_column("Confidence", style="yellow", width=12, justify="right")
    table.add_column("Status", width=12, justify="center")
    
    # Add rows
    table.add_row(
        "1",
        "armchair_bright_4E85EE94.jpg",
        "Furniture/Seating",
        "Armchair",
        "0.95",
        "[green]✓ OK[/green]"
    )
    table.add_row(
        "2",
        "coffee_table_modern_EA78D53F.jpg",
        "Furniture/Table",
        "CoffeeTable",
        "0.88",
        "[green]✓ OK[/green]"
    )
    table.add_row(
        "3",
        "pendant_light_brass_7F8E867A.jpg",
        "Fixture/Lighting",
        "PendantLight",
        "0.92",
        "[green]✓ OK[/green]"
    )
    table.add_row(
        "4",
        "potted_plant_fake_12345678.jpg",
        "Vegetation",
        "PottedPlant",
        "0.71",
        "[red]✗ Error[/red]"
    )
    table.add_row(
        "5",
        "marble_slab_white_ABCDEF01.jpg",
        "Material",
        "Marble",
        "0.84",
        "[yellow]⚠ Warning[/yellow]"
    )
    
    console.print(table)


# ============================================================================
# EXAMPLE 7: Nested Info with Panel + Table
# ============================================================================
def example_7_panel_with_table():
    """Combine panel and table."""
    console.print("\n[bold cyan]EXAMPLE 7: Panel with Summary Table[/bold cyan]\n")
    
    # Create summary table
    summary = Table(show_header=False, box=None)
    summary.add_row("[cyan]Total Assets:[/cyan]", "[bold]10[/bold]")
    summary.add_row("[cyan]Ready to Ingest:[/cyan]", "[bold green]9[/bold green]")
    summary.add_row("[cyan]Errors:[/cyan]", "[bold red]1[/bold red]")
    
    # Wrap in panel
    panel = Panel(
        summary,
        title="[bold]Ingestion Status[/bold]",
        style="blue",
        expand=False
    )
    console.print(panel)


# ============================================================================
# EXAMPLE 8: Diff-style Table (Before/After)
# ============================================================================
def example_8_before_after_table():
    """Show before/after metadata changes."""
    console.print("\n[bold cyan]EXAMPLE 8: Before/After Metadata[/bold cyan]\n")
    
    table = Table(title="Metadata Changes")
    table.add_column("Field", style="cyan")
    table.add_column("Before", style="red")
    table.add_column("After", style="green")
    
    table.add_row("Subject", "-", "Furniture/Seating/Armchair")
    table.add_row("Title", "-", "Modern Armchair")
    table.add_row("Label", "-", "Armchair")
    table.add_row("Confidence", "-", "0.95")
    table.add_row("Tags", "-", "modern; contemporary")
    
    console.print(table)


# ============================================================================
# EXAMPLE 9: File Operations Table
# ============================================================================
def example_9_file_ops_table():
    """Track file operations."""
    console.print("\n[bold cyan]EXAMPLE 9: File Operations[/bold cyan]\n")
    
    table = Table(title="File Operations Log")
    table.add_column("Action", style="magenta", width=15)
    table.add_column("Source", style="yellow", width=35)
    table.add_column("Destination", style="green", width=35)
    table.add_column("Result", width=12)
    
    table.add_row(
        "Copy",
        "D:\\local\\chair_01.jpg",
        "G:\\DB\\Furniture\\chair_01.jpg",
        "[green]✓[/green]"
    )
    table.add_row(
        "Copy",
        "D:\\local\\chair_01.zip",
        "G:\\DB\\Furniture\\chair_01.zip",
        "[green]✓[/green]"
    )
    table.add_row(
        "Write",
        "—",
        ".metadata.efu",
        "[green]✓[/green]"
    )
    
    console.print(table)


# ============================================================================
# EXAMPLE 10: Keyword/Tag Table
# ============================================================================
def example_10_keywords_table():
    """Display keywords and tags."""
    console.print("\n[bold cyan]EXAMPLE 10: Keywords & Tags[/bold cyan]\n")
    
    table = Table(title="Asset Keywords")
    table.add_column("Asset", style="cyan")
    table.add_column("Subject", style="green")
    table.add_column("Tags", style="yellow")
    
    table.add_row(
        "armchair_01.jpg",
        "Furniture/Seating/Armchair",
        "modern, teak, scandinavian"
    )
    table.add_row(
        "lamp_02.jpg",
        "Fixture/Lighting/TableLamp",
        "brass, minimalist, warm"
    )
    table.add_row(
        "marble_03.jpg",
        "Material",
        "white, italian, polished"
    )
    
    console.print(table)


# ============================================================================
# RUN ALL EXAMPLES
# ============================================================================
if __name__ == "__main__":
    console.print("[bold magenta]=" * 80 + "[/bold magenta]")
    console.print("[bold magenta]RICH TABLE EXAMPLES FOR ASSET INGESTION[/bold magenta]")
    console.print("[bold magenta]=" * 80 + "[/bold magenta]")
    
    example_1_simple_table()
    example_2_status_table()
    example_3_metadata_table()
    example_4_summary_table()
    example_5_category_table()
    example_6_complex_batch_table()
    example_7_panel_with_table()
    example_8_before_after_table()
    example_9_file_ops_table()
    example_10_keywords_table()
    
    console.print("\n[bold cyan]Done![/bold cyan]\n")
