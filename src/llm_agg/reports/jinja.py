import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Literal
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from src.llm_agg.reports.plots import plot_180_radar, plot_360_radar


def _safe_filename(name: str, fallback: str = "employee") -> str:
    """
    Return a filesystem‑safe filename derived from the given string.

    The function trims whitespace and keeps only alphanumerics, spaces,
    dots, underscores, and hyphens. If the sanitized value is empty,
    `fallback` is returned.

    Parameters:
        name: Raw input (e.g., employee display name) to sanitize.
        fallback: Value to return when `name` is empty or sanitization
            results in an empty string.

    Returns:
        A sanitized filename string.
    """
    name = (name or "").strip()
    if not name:
        return fallback
    filtered = "".join(ch for ch in name if ch.isalnum() or ch in (" ", ".", "_", "-")).strip()
    return filtered or fallback


def _ensure_plot_path(visualization_url: str | None, employee_name: str) -> Path:
    """Resolve and prepare the output path for the radar image.

    If `visualization_url` is provided, its parent directory is created (if
    needed) and that path is returned. Otherwise, a path in the system temp
    folder is created in the `employee_reviews_plots` subdirectory with a
    filename based on the employee name.

    Parameters:
        visualization_url: Target file path for the image, or None to
            auto‑generate a temporary path.
        employee_name: Employee name used to compose the filename when
            `visualization_url` is not provided.
    """
    if visualization_url:
        plot_path = Path(visualization_url)
        plot_path.parent.mkdir(parents=True, exist_ok=True)
        return plot_path
    tmp_dir = Path(tempfile.gettempdir()) / "employee_reviews_plots"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir / f"radar-{_safe_filename(employee_name)}.png"

def _as_dict(obj: Any):
    """
    Normalize a JSON‑like object into a plain Python dict.

    Accepted inputs:
    - dict/Mapping: returned as a new dict copy.
    - Pydantic BaseModel: converted via `.model_dump()` (v2) or `.dict()` (v1).
    - JSON string: parsed via `json.loads()`.

    Parameters:
        obj: Source object to normalize.
    """
    if obj is None:
        return {}
    if isinstance(obj, str):
        return json.loads(obj)
    if isinstance(obj, Mapping):
        return dict(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    raise TypeError(f"Unsupported input type: {type(obj)!r}")


def _append_unique_side(bucket: list[dict], description: str, proofs: list[str]):
    """
    Append or merge a side item into the list in place.

    If an item with the same `side_description` already exists in `bucket`,
    the function merges `proofs` into it, preserving order and removing
    exact duplicates. Otherwise, a new item is appended.

    Parameters:
        bucket: Target list of side dictionaries to mutate.
        description: Canonical side description (merge key).
        proofs: A list of quote strings to add to the item.
    """
    description = str(description).strip()
    cleaned = [str(p).strip() for p in (proofs or [])]

    for item in bucket:
        if item["side_description"] == description:
            seen = set(item["proofs"])
            for p in cleaned:
                if p not in seen:
                    item["proofs"].append(p)
                    seen.add(p)
            return
    bucket.append({"side_description": description, "proofs": cleaned})


def build_context_from_jsons(
    sides_json: Any,
    recommendations_json: Any,
    *,
    mark_name: str,
    employee_name: str,
    visualization_url: str = "",
    quotes_layout: Literal["inline", "sublist"] = "inline",
):
    """
    Convert Sides and Recommendations payloads to a Jinja template context.

    The function normalizes inputs (dict, Pydantic model, or JSON string),
    merges duplicate sides by `side_description` (concatenating unique proofs),
    passes ambiguous sides as description‑only items, and assembles the final
    context expected by the template.

    Parameters:
        sides_json: Sides payload (dict/Mapping, Pydantic model, or JSON string).
        recommendations_json: Recommendations payload (dict/Mapping, Pydantic model,
            or JSON string).
        mark_name: Label of the assessment to show in headings (e.g., "180°" or "360°").
        employee_name: Employee full name used in the report.
        visualization_url: URL or filesystem path to the visualization image
            (empty string if not available).
        quotes_layout: Quote rendering mode in the template: "inline" or "sublist".
    """
    sides = _as_dict(sides_json)
    recs = _as_dict(recommendations_json)

    strong_sides = []
    weak_sides = []
    ambiguous_sides = []

    for s in sides.get("sides", []):
        kind = s.get("kind")
        if kind == "unambiguous":
            side = s.get("side")
            desc = s.get("side_description", "")
            proofs = s.get("proofs", []) or []
            if side == "strong":
                _append_unique_side(strong_sides, desc, proofs)
            elif side == "weak":
                _append_unique_side(weak_sides, desc, proofs)
        elif kind == "ambiguous":
            ambiguous_sides.append(
                {"side_description": str(s.get("side_description", "")).strip()}
            )

    recommendations = []
    for it in recs.get("items", []):
        if it.get("kind") != "recommended":
            continue
        side_ref = it.get("side_ref") or {}
        recommendations.append(
            {
                "side_description": str(side_ref.get("side_description", "")).strip(),
                "brief_explanation": str(it.get("brief_explanation", "")).strip(),
                "recommendation": str(it.get("recommendation", "")).strip(),
            }
        )

    context = {
        "mark_name": mark_name,
        "employee_name": employee_name,
        "summary": str(sides.get("summary", "")).strip(),
        "quotes_layout": quotes_layout,
        "strong_sides": strong_sides,
        "weak_sides": weak_sides,
        "ambiguous_sides": ambiguous_sides,
        "recommendations": recommendations,
        "visualization_url": visualization_url,
    }
    return context


def create_report(
    templates_dir: str,
    template_name: str,
    *,
    sides_json: Any,
    recommendations_json: Any,
    numeric_values: dict,
    employee_name: str = "employee",
    visualization_url: str | None = None,
    quotes_layout: Literal["inline", "sublist"] = "inline",
    write_intermediate_html: bool = True,
) -> str:
    """
    Render a PDF report from a Jinja template and numeric scores.

    Generates a radar image (360° if both manager and self scores are present,
    otherwise 180° from manager scores), saves it to `visualization_url` (or a
    temporary path), builds the template context from `sides_json` and
    `recommendations_json`, renders HTML, and writes the PDF to ./out.

    Args:
        templates_dir: Directory containing Jinja templates.
        template_name: Template filename within `templates_dir`.
        sides_json: Sides payload (dict/Mapping, Pydantic model, or JSON string).
        recommendations_json: Recommendations payload (dict/Mapping, Pydantic model, or JSON string).
        numeric_values: Score dicts:
            {"manage-esteem": {label: value, ...} (required, ≥3),
             "self-esteem":   {label: value, ...} (optional, ≥3)}.
        employee_name: Employee name used in the header and output filename.
        visualization_url: Optional path/URL for the radar image; temp path if None.
        quotes_layout: Quote rendering mode: "inline" or "sublist".
        write_intermediate_html: If True, also save the rendered HTML for debugging.
    """
    self_scores = numeric_values.get("self-esteem", {})
    mgr_scores = numeric_values.get("manage-esteem", {})

    if not isinstance(mgr_scores, dict) or len(mgr_scores) < 3:
        plot_uri = None
    elif self_scores is not None and (not isinstance(self_scores, dict) or len(mgr_scores) < 3):
        plot_uri = None
    else:
        plot_path = _ensure_plot_path(visualization_url, employee_name)
        if len(self_scores) > 0:
            plot_360_radar(
                pairs_self=self_scores,
                pairs_mgr=mgr_scores,
                save_to=str(plot_path),
            )
            auto_mark_name = "360°"
        else:
            plot_180_radar(
                pairs_self=mgr_scores,
                save_to=str(plot_path),
            )
            auto_mark_name = "180°"

        try:
            plot_uri = plot_path.resolve().as_uri()
        except ValueError:
            plot_uri = str(plot_path.resolve())

    context = build_context_from_jsons(
        sides_json=sides_json,
        recommendations_json=recommendations_json,
        mark_name=auto_mark_name,
        employee_name=employee_name,
        visualization_url=plot_uri,
        quotes_layout=quotes_layout,
    )

    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    html = template.render(**context)

    pdf_name = f"review-{_safe_filename(employee_name)}.pdf"
    tmp_root = Path(tempfile.gettempdir()) / "employee_reviews_html"
    tmp_root.mkdir(parents=True, exist_ok=True)

    if write_intermediate_html:
        html_path = tmp_root / f"{pdf_name}.html"
        html_path.write_text(html, encoding="utf-8")

    out_dir = Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / pdf_name

    base_url = str(Path(templates_dir).resolve())
    HTML(string=html, base_url=base_url).write_pdf(str(pdf_path))
    return str(pdf_path)