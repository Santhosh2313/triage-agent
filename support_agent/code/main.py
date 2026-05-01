import argparse
import pandas as pd
import os
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from scraper import main as run_scraper
from agent import SupportAgent
from logger import Logger

console = Console()

def scrape():
    console.print("[bold blue]Starting scraper...[/bold blue]")
    run_scraper()
    console.print("[bold green]Scraping complete![/bold green]")

def run(input_file, output_file, single_row=None, fast_mode=False):
    if not os.path.exists(input_file):
        console.print(f"[bold red]Error: Input file {input_file} not found.[/bold red]")
        return

    df = pd.read_csv(input_file)
    
    if single_row is not None:
        if single_row < 0 or single_row >= len(df):
            console.print(f"[bold red]Error: Row index {single_row} out of range.[/bold red]")
            return
        df = df.iloc[[single_row]]
        console.print(f"[yellow]Processing only row {single_row}...[/yellow]")

    agent = SupportAgent(fast_mode=fast_mode)
    logger = Logger()
    
    results = []
    stats = {
        "replied": 0,
        "escalated": 0,
        "companies": {}
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Processing tickets...", total=len(df))
        
        for i, row in df.iterrows():
            issue = str(row.get('issue', ''))
            subject = str(row.get('subject', ''))
            company = str(row.get('company', 'None'))
            
            # Process
            try:
                output = agent.process_ticket(issue, subject, company)
            except Exception as e:
                console.print(f"[red]Error on row {i}: {e}[/red]")
                output = {
                    "company": company,
                    "status": "escalated",
                    "product_area": "Error",
                    "request_type": "product_issue",
                    "response": f"We're escalating your case due to an internal error: {str(e)}",
                    "justification": "System error during processing."
                }
            
            # Update stats
            status = output.get('status', 'escalated')
            stats[status] += 1
            
            co = output.get('company', 'Unknown')
            if co not in stats['companies']:
                stats['companies'][co] = {"replied": 0, "escalated": 0}
            stats['companies'][co][status] += 1
            
            # Log
            logger.log_ticket(i, row.to_dict(), output)
            
            # Prepare result row
            res_row = row.to_dict()
            res_row.update({
                "status": output.get('status'),
                "product_area": output.get('product_area'),
                "response": output.get('response'),
                "justification": output.get('justification'),
                "request_type": output.get('request_type'),
                "company": co # Use inferred company
            })
            results.append(res_row)
            
            # Progress update
            status_color = "green" if status == "replied" else "yellow"
            progress.console.print(f"Ticket #{i}: [{status_color}]{status}[/{status_color}] ({co})")
            progress.advance(task)

    # Save results
    out_df = pd.DataFrame(results)
    # Ensure original order and all columns
    cols = list(df.columns)
    new_cols = ["status", "product_area", "response", "justification", "request_type"]
    # Reorder company if it was modified
    if "company" not in cols: cols.append("company")
    final_cols = [c for c in cols if c not in new_cols] + new_cols
    out_df = out_df[final_cols]
    
    out_df.to_csv(output_file, index=False)
    console.print(f"\n[bold green]Success![/bold green] Output saved to {output_file}")
    
    # Summary Table
    print_summary(stats)

def print_summary(stats):
    table = Table(title="Support Triage Summary")
    table.add_column("Company", style="cyan")
    table.add_column("Replied", style="green")
    table.add_column("Escalated", style="yellow")
    table.add_column("Total", style="bold")

    total_replied = 0
    total_escalated = 0

    for company, counts in stats['companies'].items():
        display_company = "Unknown" if str(company).lower() == "nan" else company
        r = counts['replied']
        e = counts['escalated']
        t = r + e
        table.add_row(display_company, str(r), str(e), str(t))
        total_replied += r
        total_escalated += e

    table.add_section()
    table.add_row("TOTAL", str(total_replied), str(total_escalated), str(total_replied + total_escalated), style="bold magenta")
    
    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Support Triage Agent CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Scrape command
    subparsers.add_parser("scrape", help="Crawl support sites and build corpus")

    # Run command
    run_parser = subparsers.add_parser("run", help="Process support tickets")
    run_parser.add_argument("--input", required=True, help="Path to input CSV")
    run_parser.add_argument("--output", required=True, help="Path to output CSV")
    run_parser.add_argument("--row", type=int, help="Process only a specific row index")
    run_parser.add_argument("--fast", action="store_true", help="Run in fast mode (skip heavy model loading)")

    args = parser.parse_args()

    if args.command == "scrape":
        scrape()
    elif args.command == "run":
        run(args.input, args.output, args.row, args.fast)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
