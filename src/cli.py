"""CLI tool for interacting with the Library corpus.

Usage:
    python -m src.cli ingest ./path/to/pdfs --source "World Bank"
    python -m src.cli search "industrial policy Africa"
    python -m src.cli ask "What evidence exists for short briefs being more effective?"
    python -m src.cli scrape worldbank --query "climate" --max 50
    python -m src.cli stats
    python -m src.cli serve
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


@click.group()
def cli():
    """Library — Policy report corpus search and analysis."""
    pass


@cli.command()
@click.argument("directory")
@click.option("--source", required=True, help="Source organization name")
@click.option("--doc-type", default="report", help="Document type")
@click.option("--topics", default="", help="Comma-separated topic tags")
@click.option("--region", default="", help="Region")
def ingest(directory, source, doc_type, topics, region):
    """Ingest all PDFs from a directory into the corpus."""
    from src.ingestion.pipeline import ingest_directory

    console.print(f"[bold]Ingesting PDFs from:[/bold] {directory}")
    console.print(f"[bold]Source:[/bold] {source}")

    report_ids = ingest_directory(
        directory, source_org=source, doc_type=doc_type, topics=topics, region=region
    )

    console.print(f"\n[green]Done.[/green] Ingested {len(report_ids)} reports.")


@cli.command()
@click.argument("query")
@click.option("--source", default=None, help="Filter by source org")
@click.option("--limit", default=10, help="Max results")
def search(query, source, limit):
    """Semantic search across the corpus."""
    from src.analysis.rag import search_chunks

    chunks = search_chunks(query, limit=limit, source_org=source)

    if not chunks:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(title=f"Results for: {query}")
    table.add_column("Sim", style="green", width=6)
    table.add_column("Source", style="cyan", width=20)
    table.add_column("Title", width=40)
    table.add_column("Year", width=6)
    table.add_column("Pages", width=8)

    for c in chunks:
        sim = f"{c['similarity']:.1%}" if c.get('similarity') else "-"
        table.add_row(
            sim,
            c.get("source_org", ""),
            c.get("title", "")[:40],
            str(c.get("year", "")),
            f"{c.get('page_start', '?')}-{c.get('page_end', '?')}",
        )

    console.print(table)


@cli.command()
@click.argument("query")
@click.option("--source", default=None, help="Filter by source org")
@click.option("--year-min", default=None, type=int)
@click.option("--year-max", default=None, type=int)
@click.option("--limit", default=10, help="Number of chunks to retrieve")
def ask(query, source, year_min, year_max, limit):
    """Ask a question and get a synthesized answer from the corpus."""
    from src.analysis.rag import ask as rag_ask

    console.print(f"\n[bold]Question:[/bold] {query}\n")
    console.print("[dim]Searching and synthesizing...[/dim]\n")

    result = rag_ask(
        query, limit=limit, source_org=source, year_min=year_min, year_max=year_max
    )

    console.print(Panel(Markdown(result["answer"]), title="Answer", border_style="blue"))

    if result["sources"]:
        console.print(f"\n[bold]Sources ({len(result['sources'])} reports):[/bold]")
        for s in result["sources"]:
            sim = f"{s['similarity']:.1%}" if s.get('similarity') else ""
            console.print(
                f"  [{sim}] {s['source_org']} — {s['title']} ({s.get('year', 'n.d.')})"
            )


@cli.command()
@click.argument("scraper_name")
@click.option("--query", default="", help="Search query")
@click.option("--max", "max_reports", default=50, help="Max reports to download")
def scrape(scraper_name, query, max_reports):
    """Download reports from a source. Scrapers: worldbank, un, imf, brookings, cgd"""
    import asyncio

    scrapers = {
        "worldbank": "src.scrapers.worldbank:WorldBankScraper",
        "un": "src.scrapers.un:UNScraper",
        "imf": "src.scrapers.imf:IMFScraper",
        "brookings": "src.scrapers.thinktanks:BrookingsScraper",
        "cgd": "src.scrapers.thinktanks:CGDScraper",
    }

    if scraper_name not in scrapers:
        console.print(f"[red]Unknown scraper: {scraper_name}[/red]")
        console.print(f"Available: {', '.join(scrapers.keys())}")
        return

    module_path, class_name = scrapers[scraper_name].rsplit(":", 1)
    import importlib
    module = importlib.import_module(module_path)
    scraper_cls = getattr(module, class_name)

    async def run():
        scraper = scraper_cls()
        try:
            results = await scraper.scrape_and_download(query=query, max_reports=max_reports)
            downloaded = sum(1 for _, path in results if path is not None)
            console.print(f"\n[green]Done.[/green] {downloaded}/{len(results)} PDFs downloaded.")
            console.print(f"Saved to: {scraper.corpus_dir}")
        finally:
            await scraper.close()

    asyncio.run(run())


@cli.command()
def stats():
    """Show corpus statistics."""
    from sqlalchemy import text
    from src.db.database import SyncSession

    with SyncSession() as session:
        result = session.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT source_org) as sources,
                COALESCE(SUM(page_count), 0) as pages,
                COALESCE(SUM(word_count), 0) as words,
                COALESCE(ROUND(AVG(page_count)), 0) as avg_pages
            FROM reports
        """))
        row = result.mappings().first()

        console.print(Panel(
            f"Reports: {row['total']:,}\n"
            f"Sources: {row['sources']}\n"
            f"Total pages: {row['pages']:,}\n"
            f"Total words: {row['words']:,}\n"
            f"Avg pages/report: {row['avg_pages']}",
            title="Corpus Stats",
            border_style="blue",
        ))

        result = session.execute(text("""
            SELECT source_org, COUNT(*) as n, ROUND(AVG(page_count)) as avg_pg
            FROM reports GROUP BY source_org ORDER BY n DESC
        """))
        rows = result.mappings().all()

        if rows:
            table = Table(title="By Source")
            table.add_column("Source")
            table.add_column("Reports", justify="right")
            table.add_column("Avg Pages", justify="right")
            for r in rows:
                table.add_row(r["source_org"], str(r["n"]), str(r["avg_pg"]))
            console.print(table)


@cli.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=8000, type=int)
def serve(host, port):
    """Start the web server."""
    import uvicorn
    console.print(f"[bold]Starting Library server at http://{host}:{port}[/bold]")
    uvicorn.run("src.api.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    cli()
