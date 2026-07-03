"""Career Copilot CLI — one command that produces your daily briefing."""
from __future__ import annotations

import click

from . import briefing, jobs as jobs_mod, triage


@click.group()
def cli():
    """Your personal job-search copilot."""


@cli.command()
@click.option("--query", default="newer_than:1d", help="Gmail search window.")
@click.option("--max", "max_results", default=40, help="Max emails to scan.")
@click.option("--email/--no-email", default=False, help="Email the briefing to yourself.")
@click.option("--to", default=None, help="Recipient for --email (defaults to you).")
@click.option("--out", default="briefing.md", help="Write the briefing to this file.")
@click.option("--no-gmail", is_flag=True, help="Skip Gmail; render an empty-inbox briefing.")
def briefingcmd(query, max_results, email, to, out, no_gmail):
    """Fetch recent mail → triage → render today's briefing."""
    if no_gmail:
        summary = triage.summarize([])
    else:
        from . import gmail_client
        msgs = gmail_client.fetch_recent(query=query, max_results=max_results)
        summary = triage.summarize(msgs)

    matches = jobs_mod.top_new_jobs(seen_ids=set())
    text = briefing.render(summary, jobs=matches)
    with open(out, "w") as f:
        f.write(text)
    click.echo(text)
    click.echo(f"\n(written to {out})")

    if email:
        from . import gmail_client
        recipient = to or "me"
        gmail_client.send_email(recipient, "☀️ Your Career Copilot briefing", text)
        click.echo(f"emailed to {recipient}")


# expose as `copilot briefing`
cli.add_command(briefingcmd, name="briefing")

if __name__ == "__main__":
    cli()
