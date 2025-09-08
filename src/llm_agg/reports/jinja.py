import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML


def create_report(
    templates_dir: str,
    template_name: str,
    context: dict,
    employee_name: str = "employee",
    write_intermediate_html: bool = True,
) -> Path:
    """
    Рендерит Jinja-шаблон в HTML и конвертирует в PDF через WeasyPrint.
    Важно: base_url указывает на каталог шаблонов, чтобы корректно подтянуть шрифты/картинки/относительные пути.

    Возвращает путь к PDF.
    """
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    html = template.render(**context)

    pdf_name = f"review-{employee_name}.pdf"
    tmp_root = Path(tempfile.gettempdir()) / "employee_reviews_html"
    tmp_root.mkdir(parents=True, exist_ok=True)

    # Сохраняем промежуточный HTML для отладки
    if write_intermediate_html:
        html_path = tmp_root / f"{pdf_name}.html"
        html_path.write_text(html, encoding="utf-8")

    out_dir = Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / pdf_name

    base_url = str(Path(templates_dir).resolve())
    HTML(string=html, base_url=base_url).write_pdf(str(pdf_path))
    return pdf_path