import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML


def create_report(
    templates_dir: str,
    template_name: str,
    context: dict,
    employee_name: str = "employee"
) -> None:
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"])
    )
    template = env.get_template(template_name)
    html = template.render(**context)
    
    tmp_root = Path(tempfile.gettempdir()) / "employee_reviews_html"
    tmp_root.mkdir(parents=True, exist_ok=True)
    html_path = tmp_root / f"review-{employee_name}.html"
    html_path.write_text(html, encoding="utf-8")

    out_dir = Path("out"); out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"review-{employee_name}.pdf"

    HTML(filename=str(html_path)).write_pdf(str(pdf_path))