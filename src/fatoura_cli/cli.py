#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path

from importlib.resources import files

from . import __version__


APP_HOME = Path(os.environ.get("FATOURA_HOME", Path.home() / ".fatoura-cli")).expanduser()
DATA_DIR = APP_HOME / "data"
CONFIG_FILE = DATA_DIR / "config.json"
CLIENTS_FILE = DATA_DIR / "clients.json"
SERVICES_FILE = DATA_DIR / "services.json"
COUNTERS_FILE = DATA_DIR / "counters.json"
HISTORY_FILE = DATA_DIR / "history.json"
DEFAULT_OUTPUT_DIR = (Path.home() / "fatoura-invoices").expanduser()
AMOUNT_STEP = Decimal("0.001")


def fail(message: str, exit_code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def ensure_directories(output_dir: Path | None = None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        fail(
            f"Impossible de lire `{path}`: JSON invalide a la ligne {exc.lineno}. "
            "Corrigez le fichier ou supprimez-le."
        )
    except OSError as exc:
        fail(f"Impossible de lire `{path}`: {exc}")


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except OSError as exc:
        fail(f"Impossible d'ecrire `{path}`: {exc}")


def load_config() -> dict:
    return load_json(CONFIG_FILE, {})


def get_output_dir(config: dict | None = None) -> Path:
    active_config = config if config is not None else load_config()
    raw_path = active_config.get("output_dir") if active_config else None
    if raw_path:
        return Path(raw_path).expanduser()
    return DEFAULT_OUTPUT_DIR


def load_counters() -> dict:
    return load_json(COUNTERS_FILE, {"invoice": 1, "product": 1})


def bump_number(key: str) -> int:
    counters = load_counters()
    value = int(counters.get(key, 1))
    counters[key] = value + 1
    save_json(COUNTERS_FILE, counters)
    return value


def format_invoice_number(number: int) -> str:
    return f"FAC-{number:06d}"


def format_product_ref(number: int) -> str:
    return f"P-{number:05d}"


def quantize_amount(value: Decimal) -> Decimal:
    return value.quantize(AMOUNT_STEP, rounding=ROUND_HALF_UP)


def parse_amount(raw_value: str) -> Decimal:
    normalized = raw_value.strip().replace(" ", "").replace(",", ".")
    try:
        return quantize_amount(Decimal(normalized))
    except InvalidOperation:
        raise ValueError(f"Montant invalide: `{raw_value}`")


def format_amount(value: Decimal) -> str:
    quantized = quantize_amount(value)
    negative = quantized < 0
    absolute = abs(quantized)
    integer_str, decimal_str = f"{absolute:.3f}".split(".")
    groups = []
    while integer_str:
        groups.append(integer_str[-3:])
        integer_str = integer_str[:-3]
    grouped = " ".join(reversed(groups)) or "0"
    return f"-{grouped},{decimal_str}" if negative else f"{grouped},{decimal_str}"


def format_percentage(value: Decimal) -> str:
    quantized = quantize_amount(value)
    if quantized == quantized.to_integral():
        return str(int(quantized))
    return format_amount(quantized)


def amount_in_words(value: Decimal) -> str:
    try:
        from num2words import num2words
    except ImportError:
        fail(
            "La dependance `num2words` est manquante. Reinstallez le projet avec `pip install .`."
        )

    quantized = quantize_amount(value)
    integer_part = int(quantized)
    millimes = int((quantized - Decimal(integer_part)) * 1000)

    words = num2words(integer_part, lang="fr")
    words = words[0].upper() + words[1:] if words else "Zero"

    if millimes > 0:
        millimes_words = num2words(millimes, lang="fr")
        return f"{words} dinars et {millimes_words} millimes"
    return f"{words} dinars"


def generate_barcode_svg(text: str) -> str:
    try:
        import barcode
        from barcode.writer import SVGWriter
    except ImportError:
        fail(
            "La dependance `python-barcode` est manquante. Reinstallez le projet avec `pip install .`."
        )

    buffer = BytesIO()
    code = barcode.get("code128", text, writer=SVGWriter())
    code.write(
        buffer,
        options={
            "module_height": 10.0,
            "font_size": 0,
            "quiet_zone": 2.0,
            "write_text": False,
        },
    )
    svg = buffer.getvalue().decode("utf-8")
    return svg[svg.find("<svg") :]


def load_template_source() -> str:
    try:
        return files("fatoura_cli").joinpath("template.html").read_text(encoding="utf-8")
    except FileNotFoundError:
        fail("Template HTML introuvable dans le package. Reinstallez `fatoura-cli`.")


def render_pdf(invoice: dict, config: dict) -> Path:
    try:
        from jinja2 import Environment
        from weasyprint import HTML
    except ImportError as exc:
        fail(
            "Impossible de charger la generation PDF. Installez les dependances Python avec `pip install .` "
            "et les bibliotheques systeme requises par WeasyPrint.\n"
            f"Detail: {exc}"
        )

    output_dir = get_output_dir(config)
    ensure_directories(output_dir)

    template = Environment(autoescape=True).from_string(load_template_source())
    html = template.render(invoice=invoice, config=config, barcode_svg=generate_barcode_svg(invoice["number"]))

    output_path = output_dir / f"{invoice['number']}.pdf"
    try:
        HTML(string=html, base_url=str(output_dir)).write_pdf(str(output_path))
    except Exception as exc:
        fail(f"Generation du PDF impossible: {exc}")
    return output_path


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nOperation annulee.")
        raise SystemExit(0)
    return value if value else default


def ask_non_empty(prompt: str, default: str = "") -> str:
    while True:
        value = ask(prompt, default)
        if value.strip():
            return value.strip()
        print("Ce champ est obligatoire.")


def ask_confirm(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = ask(f"{prompt} {hint}").lower()
        if not answer:
            return default
        if answer in {"y", "yes", "o", "oui"}:
            return True
        if answer in {"n", "no", "non"}:
            return False
        print("Reponse invalide. Entrez y ou n.")


def ask_date(prompt: str, default: str) -> str:
    while True:
        value = ask(prompt, default)
        try:
            datetime.strptime(value, "%d-%m-%Y")
            return value
        except ValueError:
            print("Date invalide. Format attendu: JJ-MM-AAAA.")


def ask_positive_amount(prompt: str) -> Decimal:
    while True:
        raw_value = ask_non_empty(prompt)
        try:
            value = parse_amount(raw_value)
        except ValueError as exc:
            print(exc)
            continue
        if value <= 0:
            print("Le montant doit etre superieur a zero.")
            continue
        return value


def ask_percentage(prompt: str, default: str = "0") -> Decimal:
    while True:
        raw_value = ask(prompt, default)
        try:
            value = parse_amount(raw_value)
        except ValueError as exc:
            print(exc)
            continue
        if value < 0:
            print("Le taux TVA ne peut pas etre negatif.")
            continue
        return value


def save_unique_entry(path: Path, entry: dict, unique_keys: tuple[str, ...]) -> bool:
    existing_entries = load_json(path, [])
    for existing in existing_entries:
        if all(existing.get(key) == entry.get(key) for key in unique_keys):
            return False
    existing_entries.append(entry)
    save_json(path, existing_entries)
    return True


def prompt_client() -> dict:
    clients = load_json(CLIENTS_FILE, [])
    if clients:
        print("\nClients enregistres:")
        for index, client in enumerate(clients, start=1):
            print(f"  [{index}] {client['name']} (M/F {client['mf']})")
        print("  [n] Nouveau client")
        choice = ask("Choix", "1")
        if choice.lower() != "n":
            try:
                selected = clients[int(choice) - 1]
                return selected
            except (ValueError, IndexError):
                print("Choix invalide. Saisie d'un nouveau client.")

    print()
    client = {
        "name": ask_non_empty("Nom du client"),
        "mf": ask_non_empty("M/F"),
    }
    if ask_confirm("Enregistrer ce client pour plus tard ?"):
        if save_unique_entry(CLIENTS_FILE, client, ("name", "mf")):
            print("Client enregistre.")
        else:
            print("Client deja present.")
    return client


def make_item(reference: str, description: str, unit_price: Decimal, tva: Decimal) -> dict:
    total_ht = quantize_amount(unit_price)
    return {
        "reference": reference,
        "description": description,
        "unit_price": str(unit_price),
        "tva": str(tva),
        "total_ht": str(total_ht),
        "unit_price_fmt": format_amount(unit_price),
        "total_ht_fmt": format_amount(total_ht),
        "tva_fmt": format_percentage(tva),
    }


def prompt_items() -> list[dict]:
    services = load_json(SERVICES_FILE, [])
    items = []

    while True:
        print()
        choice = "n"
        if services:
            print("Services enregistres:")
            for index, service in enumerate(services, start=1):
                price = format_amount(parse_amount(str(service["unit_price"])))
                tva = format_percentage(parse_amount(str(service["tva"])))
                print(
                    f"  [{index}] {service['reference']}  {service['description']}  -  {price} DT  (TVA {tva}%)"
                )
            print("  [n] Nouveau service")
            choice = ask("Choix", "n")

        if choice.lower() != "n":
            try:
                service = services[int(choice) - 1]
            except (ValueError, IndexError):
                print("Choix invalide.")
                continue
            item = make_item(
                service["reference"],
                service["description"],
                parse_amount(str(service["unit_price"])),
                parse_amount(str(service["tva"])),
            )
            items.append(item)
            print(f"Ajoute: {service['description']}")
        else:
            reference = format_product_ref(bump_number("product"))
            description = ask_non_empty("Description")
            unit_price = ask_positive_amount("Prix unitaire (DT)")
            tva = ask_percentage("TVA %", "0")
            item = make_item(reference, description, unit_price, tva)
            items.append(item)
            if ask_confirm("Enregistrer ce service pour plus tard ?"):
                service_entry = {
                    "reference": reference,
                    "description": description,
                    "unit_price": str(unit_price),
                    "tva": str(tva),
                }
                if save_unique_entry(
                    SERVICES_FILE,
                    service_entry,
                    ("description", "unit_price", "tva"),
                ):
                    print("Service enregistre.")
                else:
                    print("Service deja present.")

        if not ask_confirm("Ajouter une autre ligne ?", default=False):
            return items


def prompt_invoice_date() -> str:
    today = date.today().strftime("%d-%m-%Y")
    return ask_date("Date de facture (JJ-MM-AAAA)", today)


def calculate_totals(items: list[dict]) -> dict:
    total_ht = Decimal("0")
    base_tva = Decimal("0")
    total_tva = Decimal("0")

    for item in items:
        line_total = parse_amount(item["total_ht"])
        line_tva = parse_amount(item["tva"])
        total_ht += line_total
        if line_tva > 0:
            base_tva += line_total
        total_tva += quantize_amount(line_total * line_tva / Decimal("100"))

    total_ht = quantize_amount(total_ht)
    base_tva = quantize_amount(base_tva)
    total_tva = quantize_amount(total_tva)
    net = quantize_amount(total_ht + total_tva)

    return {
        "total_ht": total_ht,
        "base_tva": base_tva,
        "total_tva": total_tva,
        "net": net,
    }


def print_summary(invoice: dict) -> None:
    print("\nResume")
    print(f"  Facture : {invoice['number']}")
    print(f"  Client  : {invoice['client']['name']} (M/F {invoice['client']['mf']})")
    print(f"  Date    : {invoice['date']}")
    print()
    print(f"  {'#':<3} {'Ref':<10} {'Description':<35} {'PU HT':>12}  {'TVA':>8}  {'Total HT':>12}")
    print("  " + "-" * 87)
    for index, item in enumerate(invoice["line_items"], start=1):
        print(
            f"  {index:<3} {item['reference']:<10} {item['description'][:35]:<35} "
            f"{item['unit_price_fmt']:>12}  {item['tva_fmt']:>7}%  {item['total_ht_fmt']:>12}"
        )
    print()
    print(f"  {'TOTAL HT':>62} : {invoice['total_ht_fmt']} DT")
    print(f"  {'TOTAL TVA':>62} : {invoice['total_tva_fmt']} DT")
    print(f"  {'NET A PAYER':>62} : {invoice['net_fmt']} DT")


def save_history_entry(invoice: dict) -> None:
    history = load_json(HISTORY_FILE, [])
    history.append(
        {
            "number": invoice["number"],
            "client": invoice["client"]["name"],
            "net": invoice["net_fmt"],
            "date": invoice["date"],
        }
    )
    save_json(HISTORY_FILE, history)


def open_pdf(path: Path) -> None:
    command = None
    if sys.platform == "darwin":
        command = ["open", str(path)]
    elif sys.platform.startswith("linux"):
        command = ["xdg-open", str(path)]
    elif sys.platform.startswith("win"):
        command = ["cmd", "/c", "start", "", str(path)]

    if command is None:
        print(f"PDF genere: {path}")
        return

    try:
        subprocess.run(command, check=False)
    except OSError as exc:
        print(f"Impossible d'ouvrir automatiquement le PDF: {exc}")
        print(f"Ouvrez-le manuellement: {path}")


def cmd_init() -> None:
    existing = load_config()
    print("Configuration de fatoura-cli\n")
    config = {
        "name": ask_non_empty("Nom complet", existing.get("name", "")),
        "city": ask_non_empty("Ville", existing.get("city", "")),
        "address": ask_non_empty("Adresse", existing.get("address", "")),
        "tva_code": ask_non_empty("Code TVA", existing.get("tva_code", "")),
        "bank_name": ask_non_empty("Banque", existing.get("bank_name", "")),
        "iban": ask_non_empty("IBAN", existing.get("iban", "")),
        "output_dir": ask_non_empty(
            "Dossier de sortie des PDF",
            existing.get("output_dir", str(DEFAULT_OUTPUT_DIR)),
        ),
    }
    ensure_directories(Path(config["output_dir"]).expanduser())
    save_json(CONFIG_FILE, config)
    print(f"\nConfiguration enregistree dans `{CONFIG_FILE}`")


def cmd_create() -> None:
    config = load_config()
    if not config:
        fail("Aucune configuration trouvee. Lancez `fatoura init` d'abord.")

    ensure_directories(get_output_dir(config))

    print("Nouvelle facture")
    print("\nClient")
    client = prompt_client()
    print("\nDate")
    invoice_date = prompt_invoice_date()
    print("\nLignes")
    line_items = prompt_items()

    if not line_items:
        fail("Aucune ligne ajoutee. Facture annulee.")

    number = format_invoice_number(bump_number("invoice"))
    totals = calculate_totals(line_items)
    invoice = {
        "number": number,
        "date": invoice_date,
        "client": client,
        "line_items": line_items,
        "total_ht": str(totals["total_ht"]),
        "base_tva": str(totals["base_tva"]),
        "total_tva": str(totals["total_tva"]),
        "net": str(totals["net"]),
        "total_ht_fmt": format_amount(totals["total_ht"]),
        "base_tva_fmt": format_amount(totals["base_tva"]),
        "total_tva_fmt": format_amount(totals["total_tva"]),
        "net_fmt": format_amount(totals["net"]),
        "amount_in_words": amount_in_words(totals["net"]),
    }

    print_summary(invoice)
    print()
    if not ask_confirm("Generer le PDF ?"):
        print("Operation annulee. Le numero de facture reserve n'est pas reutilise.")
        return

    output_path = render_pdf(invoice, config)
    save_history_entry(invoice)
    print(f"\nPDF genere: {output_path}")

    if ask_confirm("Ouvrir le PDF maintenant ?"):
        open_pdf(output_path)


def cmd_list() -> None:
    history = load_json(HISTORY_FILE, [])
    if not history:
        print("Aucune facture generee pour le moment.")
        return

    print(f"\n  {'Facture':<14} {'Client':<25} {'Net':>15}  {'Date'}")
    print("  " + "-" * 68)
    for entry in history:
        print(f"  {entry['number']:<14} {entry['client'][:25]:<25} {entry['net']:>15} DT  {entry['date']}")
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generer des factures tunisiennes en PDF")
    parser.add_argument("--version", action="version", version=f"fatoura-cli {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("init", help="Configurer vos informations")
    subparsers.add_parser("create", help="Creer une nouvelle facture")
    subparsers.add_parser("list", help="Lister les factures generees")
    return parser


def main() -> None:
    ensure_directories()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        cmd_init()
    elif args.command == "create":
        cmd_create()
    elif args.command == "list":
        cmd_list()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
