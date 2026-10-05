"""Tâches Celery des rapports (génération PDF, diffusion client)."""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("kemta.tasks.reports")


@shared_task(name="apps.reports.tasks.generate_periodic_report_pdf", bind=True, max_retries=2)
def generate_periodic_report_pdf(self, report_id: int) -> dict:
    """Produit le PDF d'un rapport périodique puis le publie au client.

    La génération se fait hors requête HTTP : un rapport volumineux (nombreuses
    photos) ne doit jamais faire patienter le chargé de suivi.
    """
    from apps.notifications.services import notify
    from apps.reports.models import PeriodicReport
    from common.constants import AssetKind, AssetStatus, NotificationType, UploadKind
    from common.models import Asset
    from common.services.uploads import build_key
    from common.storage import object_storage

    try:
        report = PeriodicReport.objects.select_related("project", "project__customer").get(pk=report_id)
    except PeriodicReport.DoesNotExist:
        return {"status": "missing"}

    PeriodicReport.objects.filter(pk=report.pk).update(status=PeriodicReport.Status.GENERATING)
    report.build_snapshot()

    try:
        pdf_bytes = _render_pdf(report)
    except Exception as exc:  # pragma: no cover
        PeriodicReport.objects.filter(pk=report.pk).update(status=PeriodicReport.Status.FAILED)
        raise self.retry(exc=exc, countdown=60) from exc

    key = build_key(
        upload_kind=UploadKind.REPORT,
        filename=f"{report.project.reference}-rapport-{report.period_end}.pdf",
        owner_id=report.project.customer_id,
        prefix="reports",
    )
    import io

    object_storage.put(key, io.BytesIO(pdf_bytes), "application/pdf")
    asset = Asset.objects.create(
        kind=AssetKind.DOCUMENT,
        status=AssetStatus.READY,
        bucket=settings.OBJECT_STORAGE_BUCKET or "local",
        key=key,
        original_filename=f"{report.project.reference}-rapport.pdf",
        mime_type="application/pdf",
        size_bytes=len(pdf_bytes),
        variants={"original": key},
    )

    report.file = asset
    report.status = PeriodicReport.Status.READY
    report.generated_at = timezone.now()
    report.save(update_fields=["file", "status", "generated_at", "progress_snapshot"])

    if report.project.customer_id:
        notify(
            recipient=report.project.customer,
            notification_type=NotificationType.REPORT,
            title=f"Rapport disponible — {report.project.name}",
            body=f"{report.title} ({report.period_start} → {report.period_end}) est prêt à consulter.",
            action_url=f"/espace/projets/{report.project_id}",
            action_label="Ouvrir le rapport",
            entity_type="PeriodicReport",
            entity_id=report.pk,
            project=report.project,
            payload={"reference": report.project.reference},
            dedupe_key=f"report:{report.pk}:ready",
            also_sms=True,
        )
    return {"status": "ready", "asset_id": asset.pk}


def _render_pdf(report) -> bytes:
    """Rendu PDF minimaliste, sans dépendance lourde.

    On construit un PDF 1.4 texte (titres, listes, indicateurs) plutôt que de
    tirer WeasyPrint/ReportLab : le besoin client est un document lisible et
    léger, pas une brochure. Le rendu HTML riche reste possible plus tard en
    branchant un moteur de template → PDF.
    """
    lines: list[str] = []
    brand = settings.KEMTA_BRAND_NAME
    lines.append(f"{brand} — {report.title}")
    lines.append(f"Projet : {report.project.reference} — {report.project.name}")
    lines.append(f"Période : {report.period_start} au {report.period_end}")
    lines.append("")
    snapshot = report.progress_snapshot or {}
    lines.append("Indicateurs clés")
    lines.append(f"  Avancement physique : {snapshot.get('physical_progress', 0)} %")
    lines.append(f"  Budget consommé     : {snapshot.get('budget_used_percent', 0)} %")
    lines.append(f"  Jours renseignés    : {snapshot.get('days_reported', 0)}")
    lines.append(f"  Effectif moyen      : {snapshot.get('average_workers', 0)}")
    lines.append(f"  Preuves validées    : {snapshot.get('evidences_validated', 0)}")
    lines.append("")
    if report.summary:
        lines.append("Synthèse")
        lines.extend(_wrap(report.summary))
        lines.append("")
    for block_title, items in (
        ("Points marquants", report.highlights),
        ("Risques et alertes", report.risks),
        ("Prochaines étapes", report.next_steps),
    ):
        if items:
            lines.append(block_title)
            for item in items:
                lines.extend(_wrap(f"- {item}"))
            lines.append("")
    lines.append(f"Document généré automatiquement par {brand} le {timezone.localdate()}.")
    return _simple_pdf(lines)


def _wrap(text: str, width: int = 95) -> list[str]:
    words = str(text).split()
    out, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            out.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        out.append(current)
    return out


def _simple_pdf(lines: list[str]) -> bytes:
    """Génère un PDF texte valide (Helvetica 10 pt, une page par 55 lignes)."""
    pages = [lines[i : i + 55] for i in range(0, len(lines), 55)] or [[]]
    objects: list[bytes] = []
    font_object_number = 3 + len(pages) * 2
    content_streams = []
    for page_lines in pages:
        text = ["BT", "/F1 10 Tf", "14 TL", "56 780 Td"]
        for line in page_lines:
            escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
            text.append(f"({escaped}) Tj T*")
        text.append("ET")
        content_streams.append("\n".join(text).encode("latin-1", "replace"))

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Count {len(pages)} /Kids [{kids}] >>".encode("latin-1"))
    for index, stream in enumerate(content_streams):
        page_number = 3 + index * 2
        content_number = page_number + 1
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 {font_object_number} 0 R >> >> "
                f"/Contents {content_number} 0 R >>"
            ).encode("latin-1")
        )
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    buffer = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(buffer))
        buffer += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_position = len(buffer)
    buffer += f"xref\n0 {len(objects) + 1}\n".encode()
    buffer += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        buffer += f"{offset:010d} 00000 n \n".encode()
    buffer += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF\n"
    ).encode()
    return bytes(buffer)
