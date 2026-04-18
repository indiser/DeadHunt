from flask import Flask, render_template, request
from enginex import analyze_repo
import re
import datetime

app=Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/scan",methods=["GET"])
def scan():
    repo_url = request.args.get("repo_url")
    
    if not repo_url:
        return "Error: No repository URL provided. Go back and enter a valid URL.", 400

    # 2. Extract the repo name to populate the UI header
    regex = r"github\.com/([^/]+)/([^/?#]+?)(?:\.git)?(?:/|\\?|#|$)"
    match = re.search(regex, repo_url, re.IGNORECASE)
    repo_name = f"{match.group(1)}/{match.group(2)}" if match else "unknown/repo"

    print(f"--- INITIATING SCAN FOR: {repo_name} ---")
    
    # 3. Execute the Engine
    markdown_report = analyze_repo(repo_url)

    # 4. Extract stats from the markdown report for the sidebar UI
    stats = extract_stats(markdown_report)

    # 5. Render the Resulting Report
    return render_template(
        "report.html", 
        report_markdown=markdown_report,
        repo_name=repo_name,
        scan_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        language_version="",
        total_files_scanned=stats["total_files_scanned"],
        dead_code_count=stats["dead_code_count"],
        zombie_dep_count=stats["zombie_dep_count"],
        false_positive_count=stats["false_positive_count"],
        actionable_count=stats["actionable_count"]
    )


def extract_stats(markdown):
    """Extract report statistics by counting verdict patterns in the LLM markdown."""
    stats = {
        "total_files_scanned": 0,
        "dead_code_count": 0,
        "zombie_dep_count": 0,
        "false_positive_count": 0,
        "actionable_count": 0,
    }

    if not markdown:
        return stats

    text_lower = markdown.lower()

    # ── Count unique files from "## filename — entity" headings ──
    # Match lines like: ## loaders\image_folder.py — read_array (function)
    file_headings = re.findall(r'^##\s+(.+?)\s*(?:—|-)\s+', markdown, re.MULTILINE)
    unique_files = set()
    for fh in file_headings:
        fname = fh.strip()
        if fname.lower() not in ('executive summary', 'zombie dependencies'):
            unique_files.add(fname.lower())
    stats["total_files_scanned"] = len(unique_files)

    # Fallback: try to extract from executive summary text
    if stats["total_files_scanned"] == 0:
        files_match = re.search(r'files\s+scanned[:\s|]*(\d+)', text_lower)
        if files_match:
            stats["total_files_scanned"] = int(files_match.group(1))

    # ── Count verdicts ──
    # Match "**Verdict:** Confirmed Dead" (case-insensitive, with or without extra bold markers)
    stats["dead_code_count"] = len(re.findall(
        r'\*\*verdict:?\*\*\s*confirmed\s+dead', text_lower
    ))
    stats["false_positive_count"] = len(re.findall(
        r'\*\*verdict:?\*\*\s*false\s+positive', text_lower
    ))
    
    # Zombie deps: count the section or individual zombie flags
    zombie_section = re.findall(r'^##\s*zombie\s+dependenc', text_lower, re.MULTILINE)
    zombie_inline = re.findall(r'\*\*verdict:?\*\*\s*(?:truly\s+)?zombie', text_lower)
    stats["zombie_dep_count"] = max(len(zombie_section), len(zombie_inline))
    
    # Actionable = confirmed dead code items + unverified
    unverified = len(re.findall(
        r'\*\*verdict:?\*\*\s*unverified', text_lower
    ))
    stats["actionable_count"] = stats["dead_code_count"] + unverified

    return stats


if __name__=="__main__":
    app.run(debug=False)