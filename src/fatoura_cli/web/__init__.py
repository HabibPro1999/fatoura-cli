import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from ..cli import (
    CLIENTS_FILE,
    CONFIG_FILE,
    DEFAULT_OUTPUT_DIR,
    HISTORY_FILE,
    SERVICES_FILE,
    assemble_invoice,
    bump_number,
    ensure_directories,
    format_amount,
    format_invoice_number,
    format_percentage,
    format_product_ref,
    get_output_dir,
    load_config,
    load_json,
    make_item,
    parse_amount,
    render_pdf,
    save_history_entry,
    save_json,
    save_unique_entry,
)

PDF_NUMBER_RE = re.compile(r"FAC-\d{6}")
CONFIG_FIELDS = ("name", "city", "address", "tva_code", "bank_name", "iban", "output_dir")


def resolve_client(data) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Client manquant.")
    if "index" in data:
        clients = load_json(CLIENTS_FILE, [])
        try:
            selected = clients[int(data["index"])]
        except (TypeError, ValueError, IndexError):
            raise ValueError("Client introuvable.")
        return {"name": selected["name"], "mf": selected["mf"]}
    name = str(data.get("name", "")).strip()
    mf = str(data.get("mf", "")).strip()
    if not name or not mf:
        raise ValueError("Nom du client et M/F obligatoires.")
    client = {"name": name, "mf": mf}
    if data.get("save"):
        save_unique_entry(CLIENTS_FILE, client, ("name", "mf"))
    return client


def resolve_items(raw_items) -> list[dict]:
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("Ajoutez au moins une ligne.")
    services = load_json(SERVICES_FILE, [])
    items = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("Ligne invalide.")
        if "service_index" in raw:
            try:
                service = services[int(raw["service_index"])]
            except (TypeError, ValueError, IndexError):
                raise ValueError("Service introuvable.")
            items.append(
                make_item(
                    service["reference"],
                    service["description"],
                    parse_amount(str(service["unit_price"])),
                    parse_amount(str(service["tva"])),
                )
            )
            continue
        description = str(raw.get("description", "")).strip()
        if not description:
            raise ValueError("Description obligatoire pour chaque ligne.")
        unit_price = parse_amount(str(raw.get("unit_price", "")))
        if unit_price <= 0:
            raise ValueError("Le prix unitaire doit être supérieur à zéro.")
        tva = parse_amount(str(raw.get("tva") or "0"))
        if tva < 0:
            raise ValueError("Le taux TVA ne peut pas être négatif.")
        reference = str(raw.get("reference") or "").strip() or format_product_ref(
            bump_number("product")
        )
        items.append(make_item(reference, description, unit_price, tva))
        if raw.get("save"):
            save_unique_entry(
                SERVICES_FILE,
                {
                    "reference": reference,
                    "description": description,
                    "unit_price": str(unit_price),
                    "tva": str(tva),
                },
                ("description", "unit_price", "tva"),
            )
    return items


def parse_invoice_date(raw) -> str:
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        raise ValueError("Date invalide.")


def display_date_to_iso(display: str) -> str:
    return datetime.strptime(display, "%d-%m-%Y").strftime("%Y-%m-%d")


def persist_invoice(number: str, payload: dict) -> dict:
    client = resolve_client(payload.get("client"))
    invoice_date = parse_invoice_date(payload.get("date"))
    items = resolve_items(payload.get("items"))
    invoice = assemble_invoice(number, invoice_date, client, items)
    render_pdf(invoice, load_config())
    save_history_entry(invoice)
    return invoice


def formatted_services() -> list[dict]:
    services = load_json(SERVICES_FILE, [])
    for service in services:
        service["unit_price_fmt"] = format_amount(parse_amount(str(service["unit_price"])))
        service["tva_fmt"] = format_percentage(parse_amount(str(service["tva"])))
    return services


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "fatoura-local-ui"

    @app.before_request
    def require_config():
        if request.endpoint in {"settings", "save_settings", "static"}:
            return None
        if not load_config():
            flash("Renseignez d'abord vos informations.")
            return redirect(url_for("settings"))
        return None

    @app.get("/")
    def index():
        history = load_json(HISTORY_FILE, [])
        output_dir = get_output_dir()
        total = Decimal("0")
        entries = []
        for entry in reversed(history):
            total += parse_amount(entry["net"])
            entries.append(
                {
                    **entry,
                    "pdf_exists": (output_dir / f"{entry['number']}.pdf").exists(),
                    "editable": bool(entry.get("source")),
                }
            )
        return render_template(
            "index.html",
            active="invoices",
            entries=entries,
            count=len(entries),
            total_fmt=format_amount(total),
            created=request.args.get("created"),
            updated=request.args.get("updated"),
        )

    @app.get("/new")
    def new_invoice():
        return render_template(
            "new_invoice.html",
            active="new",
            clients=load_json(CLIENTS_FILE, []),
            services=formatted_services(),
            today=date.today().isoformat(),
        )

    @app.post("/api/invoices")
    def create_invoice():
        payload = request.get_json(silent=True) or {}
        number = format_invoice_number(bump_number("invoice"))
        try:
            persist_invoice(number, payload)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"number": number, "pdf_url": url_for("invoice_pdf", number=number)})

    @app.get("/edit/<number>")
    def edit_invoice(number):
        entry = next(
            (e for e in load_json(HISTORY_FILE, []) if e["number"] == number), None
        )
        if entry is None or not entry.get("source"):
            flash("Cette facture ne peut pas être modifiée.")
            return redirect(url_for("index"))
        source = entry["source"]
        return render_template(
            "new_invoice.html",
            active="",
            clients=load_json(CLIENTS_FILE, []),
            services=formatted_services(),
            today=display_date_to_iso(entry["date"]),
            edit={
                "number": number,
                "client": source["client"],
                "items": source["line_items"],
                "date": display_date_to_iso(entry["date"]),
            },
        )

    @app.put("/api/invoices/<number>")
    def update_invoice(number):
        if not PDF_NUMBER_RE.fullmatch(number):
            abort(404)
        if not any(e["number"] == number for e in load_json(HISTORY_FILE, [])):
            return jsonify({"error": "Facture introuvable."}), 404
        payload = request.get_json(silent=True) or {}
        try:
            persist_invoice(number, payload)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"number": number, "pdf_url": url_for("invoice_pdf", number=number)})

    @app.get("/pdf/<number>")
    def invoice_pdf(number):
        if not PDF_NUMBER_RE.fullmatch(number):
            abort(404)
        path = get_output_dir() / f"{number}.pdf"
        if not path.exists():
            abort(404)
        return send_file(path)

    @app.get("/clients")
    def clients_page():
        return render_template("clients.html", active="clients", clients=load_json(CLIENTS_FILE, []))

    @app.post("/clients")
    def add_client():
        name = request.form.get("name", "").strip()
        mf = request.form.get("mf", "").strip()
        if not name or not mf:
            flash("Nom et M/F obligatoires.")
        elif save_unique_entry(CLIENTS_FILE, {"name": name, "mf": mf}, ("name", "mf")):
            flash("Client enregistré.")
        else:
            flash("Client déjà présent.")
        return redirect(url_for("clients_page"))

    @app.post("/clients/<int:index>/delete")
    def delete_client(index):
        clients = load_json(CLIENTS_FILE, [])
        if 0 <= index < len(clients):
            removed = clients.pop(index)
            save_json(CLIENTS_FILE, clients)
            flash(f"Client supprimé : {removed['name']}")
        return redirect(url_for("clients_page"))

    @app.get("/services")
    def services_page():
        return render_template("services.html", active="services", services=formatted_services())

    @app.post("/services")
    def add_service():
        description = request.form.get("description", "").strip()
        try:
            unit_price = parse_amount(request.form.get("unit_price", ""))
            tva = parse_amount(request.form.get("tva") or "0")
        except ValueError:
            flash("Montant invalide.")
            return redirect(url_for("services_page"))
        if not description or unit_price <= 0 or tva < 0:
            flash("Description, prix positif et TVA valide obligatoires.")
            return redirect(url_for("services_page"))
        entry = {
            "reference": format_product_ref(bump_number("product")),
            "description": description,
            "unit_price": str(unit_price),
            "tva": str(tva),
        }
        if save_unique_entry(SERVICES_FILE, entry, ("description", "unit_price", "tva")):
            flash("Service enregistré.")
        else:
            flash("Service déjà présent.")
        return redirect(url_for("services_page"))

    @app.post("/services/<int:index>/delete")
    def delete_service(index):
        services = load_json(SERVICES_FILE, [])
        if 0 <= index < len(services):
            removed = services.pop(index)
            save_json(SERVICES_FILE, services)
            flash(f"Service supprimé : {removed['description']}")
        return redirect(url_for("services_page"))

    @app.get("/settings")
    def settings():
        return render_template(
            "settings.html",
            active="settings",
            config=load_config(),
            default_output=str(DEFAULT_OUTPUT_DIR),
        )

    @app.post("/settings")
    def save_settings():
        config = {field: request.form.get(field, "").strip() for field in CONFIG_FIELDS}
        if not all(config.values()):
            flash("Tous les champs sont obligatoires.")
            return render_template(
                "settings.html",
                active="settings",
                config=config,
                default_output=str(DEFAULT_OUTPUT_DIR),
            ), 400
        ensure_directories(Path(config["output_dir"]).expanduser())
        save_json(CONFIG_FILE, config)
        flash("Configuration enregistrée.")
        return redirect(url_for("index"))

    return app
