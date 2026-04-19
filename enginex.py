import ast
import json
import os
from vulture.core import Vulture
import difflib
import re
import subprocess
import sys
import datetime
from pathlib import Path
import shutil
import stat
from google import genai
from dotenv import load_dotenv
from deadhunt_router import generate_audit



load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("CRITICAL FAILURE: GEMINI_API_KEY not found. Check your .env file.")

client = genai.Client(api_key=api_key)

FRAMEWORK_WHITELISTS = {
    "django": {
        "files": ["settings.py", "manage.py", "apps.py", "urls.py", "wsgi.py", "asgi.py"],
        "variables": [
            "SECRET_KEY", "DEBUG", "ALLOWED_HOSTS", "INSTALLED_APPS", "MIDDLEWARE", 
            "MIDDLEWARE_CLASSES", "ROOT_URLCONF", "TEMPLATES", "WSGI_APPLICATION", 
            "DATABASES", "AUTH_PASSWORD_VALIDATORS", "LANGUAGE_CODE", "TIME_ZONE", 
            "USE_I18N", "USE_L10N", "USE_TZ", "DATE_FORMAT", "DATETIME_FORMAT", 
            "SUIT_CONFIG", "urlpatterns", "application", "list_display", 
            "search_fields", "list_per_page", "ordering"
        ]
    }
}


def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)



def analyze_repo(repo_url):
    output_data={}

    local_dir = './temp'

    os.makedirs(local_dir, exist_ok=True)
    
    try:
        subprocess.run(['git', 'clone', '--depth', '1', repo_url, local_dir], check=True)
        print(f'Repo cloned to {local_dir}')
    except subprocess.CalledProcessError as e:
        return f"## Analysis Failed\nError cloning repository. The server workspace might be locked or the URL is invalid."

    try:
        # Get The name of the repo
        regex = r"github\.com/([^/]+)/([^/?#]+?)(?:\.git)?(?:/|\?|#|$)"

        match = re.search(regex, repo_url, re.IGNORECASE)

        if match:
            owner = match.group(1)
            repo = match.group(2)
            print(f"Repo name: {owner}/{repo}")
            repo_name = f"{owner}/{repo}"
        else:
            repo_name = "unknown/repo"

        # Generate Requirements
        temp_requirements_path="temp_req"

        if not os.path.isdir(temp_requirements_path):
            os.mkdir(temp_requirements_path)
            

        def get_imports_from_file(filepath):
            """Extract imports from a Python file, skip if syntax error."""
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                imports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split('.')[0])
                return imports
            except:
                return set()

        def generate_requirements_manual(project_path=".", output_file="requirements.txt"):
            """Generate requirements.txt by scanning Python files (for Python 2 projects)."""
            all_imports = set()
            for py_file in Path(project_path).rglob('*.py'):
                all_imports.update(get_imports_from_file(py_file))
            
            # Filter out standard library modules
            stdlib = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else set()
            external = sorted(all_imports - stdlib - {''})
            
            with open(output_file, 'w') as f:
                for pkg in external:
                    f.write(f"{pkg}\n")
            
            print(f"✅ {output_file} generated with {len(external)} packages (manual scan).")

        def generate_requirements_pipreqs(project_path=".", output_file="requirements.txt"):
            """Generate requirements.txt using pipreqs (for Python 3 projects)."""
            cmd = ["pipreqs", project_path, "--encoding=utf-8", "--savepath", output_file, "--force"]
            
            try:
                subprocess.run(cmd, check=True)
                print("✅ requirements.txt generated successfully (pipreqs).")
            except subprocess.CalledProcessError as e:
                print(f"❌ pipreqs failed: {e}")

        def generate_requirements(project_path=".", output_file="requirements.txt"):
            """Generate requirements.txt based on Python version."""
            if sys.version_info[0] < 3.0:
                print("Detected Python 2, using manual scan...")
                generate_requirements_manual(project_path, output_file)
            else:
                print("Detected Python 3, using pipreqs...")
                generate_requirements_pipreqs(project_path, output_file)

        generate_requirements("./temp", f"./{temp_requirements_path}/requirements.txt")


        # Delta between requirements

        def prep_for_difflib(filepath):
            with open(filepath, 'r') as f:
                cleaned = [re.split(r'[=<>~]', line.strip().lower().replace('_', '-'))[0]
                        for line in f if line.strip()]
                
                cleaned.sort()
                return cleaned

        missing_dep = None
        dep_usage = {}

        generated_req = f"./{temp_requirements_path}/requirements.txt"
        repo_req = "./temp/requirements.txt"

        try:
            if os.path.isfile(repo_req):
                repo_lines = prep_for_difflib(repo_req)
                generated_lines = prep_for_difflib(generated_req)
                diff = difflib.ndiff(generated_lines, repo_lines)
                delta = [line[2:] for line in diff if line.startswith('- ')]
                missing_dep = delta
                if delta:
                    print(f"Logged {len(delta)} missing packages.")
                else:
                    print("Files are completely synced.")
            else:
                print("No requirements.txt found in repo. Using generated requirements.")
                missing_dep = prep_for_difflib(generated_req)
        except Exception as e:
            print(f"An error occurred: {e}")


        def get_dep_usage(repo_path, dependencies):
            usage = {dep: [] for dep in dependencies}
            for root, _, files in os.walk(repo_path):
                for fname in files:
                    if not fname.endswith('.py'):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            source = f.read()
                        tree = ast.parse(source)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.Import, ast.ImportFrom)):
                                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or '']
                                for dep in dependencies:
                                    if any(dep in n for n in names):
                                        rel = os.path.relpath(fpath)
                                        if rel not in usage[dep]:
                                            usage[dep].append(rel)
                    except Exception:
                        continue
            return usage


        def get_language_version(repo_path):
            for fname in ['setup.py', 'setup.cfg', 'pyproject.toml']:
                fpath = os.path.join(repo_path, fname)
                if os.path.isfile(fpath):
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        m = re.search(r'python_requires\s*[=:]+\s*["\']([^"\']+)["\']', content)
                        if m:
                            return m.group(1)
                    except Exception:
                        pass
            return f"{sys.version_info.major}.{sys.version_info.minor}"


        # Create the ast and json

        def ast_to_dict(node):
            if isinstance(node, ast.AST):
                result = {"_node_type": type(node).__name__}
                for field, value in ast.iter_fields(node):
                    result[field] = ast_to_dict(value)
                return result
            elif isinstance(node, list):
                return [ast_to_dict(n) for n in node]
            elif isinstance(node, (str, int, float, bool, type(None))):
                return node
            else:
                return str(node)


        class SafeEncoder(json.JSONEncoder):
            def default(self, obj):
                try:
                    return super().default(obj)
                except TypeError:
                    return str(obj)


        CONTEXT_LINES = 3

        def detect_python_framework(repo_path):
            """Sniffs the repository to determine the underlying framework to apply the correct whitelist."""
            repo_p = Path(repo_path)
            
            # Django signature
            if list(repo_p.rglob('manage.py')) and list(repo_p.rglob('settings.py')):
                return "django"
            
            # FastApi / Flask signatures (basic)
            req_files = list(repo_p.rglob('requirements.txt')) + list(repo_p.rglob('pyproject.toml'))
            for req in req_files:
                try:
                    content = req.read_text().lower()
                    if 'fastapi' in content: return "fastapi"
                    if 'flask' in content: return "flask"
                except Exception:
                    continue
                    
            return "generic"

        def scan_repository_for_dead_code(repo_path):
            if not os.path.isdir(repo_path):
                raise ValueError(f"Error: '{repo_path}' is not a valid directory. Are you passing a file instead?")
            

            print(f"Scanning repository: {repo_path}...")

            framework = detect_python_framework(repo_path)
            print(f"Detected Framework Architecture: {framework.upper()}")

            valid_files = []
            for root, _, files in os.walk(repo_path):
                for fname in files:
                    if not fname.endswith('.py'):
                        continue
                    fp = os.path.join(root, fname)
                    try:
                        with open(fp, 'r', encoding='utf-8') as f:
                            ast.parse(f.read())
                        valid_files.append(fp)
                    except Exception:
                        print(f"Skipping unparseable file (Python 2): {fp}")

            v = Vulture()
            v.scavenge(valid_files)
            dead_items = v.get_unused_code()

            items_by_file = {}
            for item in dead_items:
                file_str = str(item.filename)
                if file_str not in items_by_file:
                    items_by_file[file_str] = []
                items_by_file[file_str].append(item)

            dead_code_flags = []
            total_files_scanned = 0

            # build a full-repo source map for call_references search
            repo_source = {}
            for root, _, files in os.walk(repo_path):
                for fname in files:
                    if fname.endswith('.py'):
                        fp = os.path.join(root, fname)
                        try:
                            with open(fp, 'r', encoding='utf-8') as f:
                                repo_source[fp] = f.read()
                        except Exception:
                            pass

            for file_path, items in items_by_file.items():
                if not file_path.endswith('.py') or not os.path.isfile(file_path):
                    continue

                total_files_scanned += 1
                    
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        source_code = f.read()
                    source_lines = source_code.splitlines()
                    tree = ast.parse(source_code)
                except Exception as e:
                    print(f"Warning: Skipping {file_path} due to parsing error: {e}")
                    continue

                for item in items:
                    file_name_only = os.path.basename(file_path)
                    if framework in FRAMEWORK_WHITELISTS:
                        wl = FRAMEWORK_WHITELISTS[framework]
                        # If it's a known framework file AND the flagged entity is a required framework variable, DROP IT.
                        if file_name_only in wl["files"] and item.name in wl["variables"]:
                            continue 
                        # Drop dynamic Django imports in manage.py
                        if file_name_only == "manage.py" and item.name == "django":
                            continue
                    
                    target_node = None
                    for node in ast.walk(tree):
                        if hasattr(node, 'lineno') and node.lineno == item.first_lineno:
                            target_node = node
                            break
                    
                    if target_node:
                        start = target_node.lineno - 1
                        end = getattr(target_node, 'end_lineno', target_node.lineno)

                        context_start = max(0, start - CONTEXT_LINES)
                        context_end = min(len(source_lines), end + CONTEXT_LINES)
                        context = {
                            "before": "\n".join(source_lines[context_start:start]),
                            "after": "\n".join(source_lines[end:context_end])
                        }

                        call_references = [
                            os.path.relpath(fp).replace("temp\\", "").replace("temp/", "")
                            for fp, src in repo_source.items()
                            if fp != file_path and re.search(r'\b' + re.escape(item.name) + r'\b', src)
                        ]

                        dead_code_flags.append({
                            "file": os.path.relpath(file_path).replace("temp\\", "").replace("temp/", ""),
                            "entity_type": item.typ,
                            "entity_name": item.name,
                            "confidence_score": item.confidence,
                            "start_line": target_node.lineno,
                            "end_line": end,
                            "snippet": "\n".join(source_lines[start:end]),
                            "context_lines": context,
                            "call_references": call_references,
                            # "ast_tree": ast_to_dict(target_node)
                        })

            zombie_deps = missing_dep or []
            dep_usage = get_dep_usage(repo_path, zombie_deps) if zombie_deps else {}
            zombie_dependencies = [
                {"package": dep} for dep in zombie_deps
            ]

            output_data = {
                "repository": repo_name,
                "scan_timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                "language_version": get_language_version(repo_path),
                "total_files_scanned": total_files_scanned,
                "zombie_dependencies": zombie_dependencies,
                "dead_code_flags": dead_code_flags
            }

            return json.dumps(output_data, indent=4, ensure_ascii=False, cls=SafeEncoder)


        output_data = json.loads(scan_repository_for_dead_code("./temp"))

        print("Analysis complete. Check repo_analysis_output.json")


        system_instruction = """
        You are a Senior Principal Engineer performing automated codebase audits across diverse Python 
        repositories. You will receive a JSON payload from a static analyzer containing 
        'zombie_dependencies' and 'dead_code_flags'. Your job is to produce a precise, actionable 
        Markdown audit report.

        ===== BEFORE YOU CLASSIFY ANYTHING =====

        You must reason through the following checks for EVERY finding before issuing a verdict.
        Skipping these checks will produce dangerous false positives that break production systems.

        --- CHECK 1: SELF-REFERENTIAL CALL REFERENCES (Parser Limitation Signal) ---
        If a finding's `call_references` list contains ONLY the file where the entity itself is defined,
        the static analyzer has failed to perform cross-file tracing. This is a parser bug, not proof 
        of deadness. Mark these as UNVERIFIED and say so explicitly. Do not mark them as dead code.

        --- CHECK 2: FRAMEWORK & RUNTIME INVOCATION PATTERNS ---
        Many entities are never called via direct Python syntax but are invoked by frameworks via 
        reflection, decorators, metaclasses, or runtime hooks. These are the most common false positive 
        categories — check each one before classifying:

        FRAMEWORKS TO RECOGNIZE:
        • Django / Flask / FastAPI — Model fields, Meta classes, admin attributes (list_display, 
            search_fields), AppConfig subclasses, signal receivers, middleware, and view methods are 
            all framework-invoked. Never flag these as dead.
        • Celery / RQ / Dramatiq — Functions decorated with @task or @app.task are called by workers 
            via message brokers, not direct Python calls. Never flag as dead.
        • Pytest / Unittest — Fixtures (@pytest.fixture), test functions (test_*), setup/teardown 
            methods, and conftest.py entries are runner-invoked. Never flag as dead.
        • SQLAlchemy / Tortoise ORM — Model column definitions, relationship fields, __tablename__, 
            and event listeners are ORM-managed. Never flag as dead.
        • PyTorch / TensorFlow / JAX — Module-level runtime config (e.g., torch.backends.*), model 
            lifecycle methods (train(), eval(), forward()), loss functions, and dataset __getitem__ / 
            __len__ are framework-invoked or tensor-indexed. Treat with high skepticism.
        • Click / Argparse / Typer — CLI entry points decorated with @click.command or registered 
            in setup.py console_scripts are user-invoked at runtime. Never flag as dead.
        • __all__, __init__.py exports — Public API surface. Flag only if confirmed unexported AND 
            unreferenced externally.

        --- CHECK 3: DYNAMIC INVOCATION PATTERNS ---
        The following Python patterns make static analysis unreliable. If any are present in the repo 
        context, lower your confidence in the dead code verdict:
        • getattr() / hasattr() — Attribute access by string name
        • importlib.import_module() — Runtime imports
        • globals() / locals() / vars() — Namespace introspection
        • Plugin systems, entry_points, or __subclasses__() — Dynamic discovery
        • eval() / exec() — Runtime code execution
        If these patterns are likely in the repo's domain (e.g., plugin frameworks, ORMs, CLI tools), 
        explicitly note that static analysis coverage is limited.

        --- CHECK 4: CONFIDENCE SCORE INTERPRETATION ---
        • 100% — Analyzer is statically certain. Still validate against Checks 1–3.
        • 60–99% — Weak to moderate signal. Treat as Unverified unless cross-file analysis confirms.
        • Below 60% — Do not recommend deletion. Flag as Noise.

        --- CHECK 5: ZOMBIE DEPENDENCY SPECIAL RULES ---
        • Core language-adjacent packages (e.g., typing, dataclasses, six, attrs) — often indirect 
            dependencies. Do not flag for deletion without confirming they are in requirements.txt 
            AND have zero imports across all files.
        • If total_files_scanned is below 30, explicitly warn: "Incomplete coverage — 
            cross-file import analysis may be unreliable. Do not delete dependencies based on 
            this scan alone."
        • For any dependency flagged as zombie, check if it could be: a dev/test-only dependency, 
            an optional extra, or a transitive dependency pulled in by another package.

        ===== OUTPUT FORMAT =====

        ## Executive Summary
        | Metric | Count |
        |---|---|
        | Total Findings Reviewed | N |
        | Confirmed Dead Code | N |
        | Confirmed Zombie Dependencies | N |
        | Likely False Positives | N |
        | Unverified (Needs Cross-File Check) | N |
        | Noise (Confidence Too Low) | N |

        **Repository:** [repository name from JSON]
        **Files Scanned:** [total_files_scanned] — [adequate / WARNING: low coverage]
        **Overall Deletion Risk:** [Safe to Proceed | Proceed with Caution | Do Not Delete Without Manual Review]
        **Parser Limitations Detected:** [List any self-referential call_references or other anomalies found]

        ---

        Then for EACH finding, output exactly this block — no exceptions, no shortcuts:

        ---
        ## [file] — [entity_name] ([entity_type])
        **Lines:** [start_line]–[end_line]  
        **Analyzer Confidence:** [confidence_score]%  
        **Verdict:** [Confirmed Dead | False Positive | Unverified — Needs Cross-File Check | Noise]  
        **Reasoning:** [2–4 sentences. Cite the snippet and context. Name the specific framework or 
        pattern that makes this safe or dangerous to delete. Be precise.]  
        **Risk of Deletion:** [None — Do Not Delete | Low | Medium | High | Critical]  
        **Recommended Action:**  
        1. [Concrete step]  
        2. [Concrete step]  
        3. [If needed]  

        ---

        ===== BEHAVIOR RULES =====
        - Never recommend deletion of anything with Risk level Medium or above without a manual 
        verification step in the action plan.
        - Never recommend deletion of a dependency if total_files_scanned is low and cross-file 
        coverage is incomplete.
        - If the repo's domain is ambiguous from the JSON, state your assumption about the tech stack 
        explicitly in the Executive Summary before proceeding.
        - Be terse. No filler. Every sentence must reduce ambiguity or add actionable signal.
        - If two findings are in the same file and share the same verdict and risk, you may group them 
        under a single block — but only if their reasoning is identical.
        """


        print("Routing payload through multi-provider failover system...")

        report_text = ""


        payload_str = json.dumps(output_data, indent=4)
        report_text = generate_audit(system_instruction, payload_str)

        return report_text

    except Exception as e:
        # Catch 503s, 429s, and network timeouts
        error_msg = str(e).replace('\n', ' ')
        print(f"API PIPELINE EXCEPTION: {error_msg}")
        return f"""## Target: API Failure - Complete Infrastructure Overload
        * **Verdict:** Unverified
        * **Risk of Deletion:** None
        * **Safe Deletion Steps:** 1. The routing pipeline exhausted all backup LLMs: `{error_msg}`.
            2. The application is experiencing severe demand.
            3. Click 'Run Another Scan' to try again in a few moments.
        """
    finally:
        for folder in [local_dir, temp_requirements_path]:
            if os.path.isdir(folder):
                shutil.rmtree(folder, onexc=remove_readonly)
                print(f"Removed {folder}")
