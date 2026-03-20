# fatoura-cli

Generate clean PDF invoices for Tunisian freelancers from the terminal.

`fatoura-cli` is intentionally opinionated. It focuses on one use case and does it well: fast, local, professional invoice generation for freelancers in Tunisia.

> [!IMPORTANT]
> The repository, README, and release notes are in English. The CLI prompts and generated invoices stay in French on purpose.

![Mock invoice preview](assets/mock-invoice.png)

## Overview

- built for Tunisian freelancers, not for generic invoicing
- generates polished PDF invoices with French labels
- keeps data local on your machine
- remembers clients and recurring services
- auto-increments invoice numbers like `FAC-000001`
- auto-increments line references like `P-00001`
- uses Tunisian number formatting like `13 750,000 DT`

## Table of contents

- [Why this project exists](#why-this-project-exists)
- [What it does](#what-it-does)
- [Who it is for](#who-it-is-for)
- [Quick start](#quick-start)
- [Example workflow](#example-workflow)
- [Local storage](#local-storage)
- [Project files](#project-files)
- [Privacy](#privacy)
- [Roadmap](#roadmap)
- [License](#license)

## Why this project exists

Most invoicing tools are too broad for a solo Tunisian freelancer.

- spreadsheets are repetitive and easy to break
- generic invoicing apps usually assume other tax fields, currencies, or layouts
- web tools add accounts, subscriptions, and data sprawl you may not want

`fatoura-cli` keeps the workflow small: fill the missing invoice details, review the summary, generate the PDF, move on.

## What it does

| Feature | Details |
| --- | --- |
| Profile setup | Save your name, address, VAT code, bank details, and default output directory once |
| Client reuse | Pick a saved client or create a new one during invoice creation |
| Service reuse | Pick a saved service or create a new one during invoice creation |
| Invoice numbering | Automatic `FAC-000001` style invoice numbers |
| Line references | Automatic `P-00001` style line references |
| PDF output | Generates a clean invoice PDF matching the project template |
| Local history | Keeps a local history of generated invoices |

## Who it is for

This tool is for Tunisian freelancers only.

| Constraint | Current choice |
| --- | --- |
| Currency | Tunisian dinar (`DT`) |
| Language | French prompts and invoice labels |
| Tax fields | `Code TVA`, `M/F`, bank information |
| Output style | Single professional PDF invoice layout |

> [!NOTE]
> This is not a multi-country invoicing engine. That limitation is deliberate.

## Quick start

### 1. Install system dependencies

<details>
<summary>macOS</summary>

The official WeasyPrint documentation recommends installing WeasyPrint and its dependencies with Homebrew:

```bash
brew install weasyprint
```

</details>

<details>
<summary>Ubuntu 20.04+</summary>

The official WeasyPrint documentation recommends at least:

```bash
sudo apt install python3-pip libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 libharfbuzz-subset0
```

</details>

### 2. Clone and install

```bash
git clone https://github.com/HabibPro1999/fatoura-cli.git
cd fatoura-cli
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

### 3. Configure your profile

```bash
fatoura init
```

You will be asked for:

- full name
- city
- address
- VAT code
- bank name
- IBAN
- output directory for generated PDFs

### 4. Create an invoice

```bash
fatoura create
```

### 5. View invoice history

```bash
fatoura list
```

## Example workflow

```text
$ fatoura create

Nouvelle facture

Client
  [1] ACME SARL (M/F 1234567A)
  [n] Nouveau client

Choix: 1

Date
Date de facture (JJ-MM-AAAA) [21-03-2026]:

Lignes
  [1] P-00001  Mobile application development  -  4 200,000 DT  (TVA 19%)
  [n] Nouveau service

Choix: 1
Ajouter une autre ligne ? [y/N]: n

Resume
  Facture : FAC-000012
  Client  : ACME SARL (M/F 1234567A)
  Date    : 21-03-2026

Generer le PDF ? [Y/n]: y
PDF genere: /Users/you/fatoura-invoices/FAC-000012.pdf
```

## Commands

| Command | Purpose |
| --- | --- |
| `fatoura init` | Save or update your business information |
| `fatoura create` | Create a new invoice interactively |
| `fatoura list` | Show locally generated invoice history |

## Local storage

> [!TIP]
> `fatoura-cli` is local-first. It does not send invoice data to any remote service.

By default, application data lives in:

```text
~/.fatoura-cli/
```

Generated PDFs go to:

```text
~/fatoura-invoices/
```

You can override the app data directory with:

```bash
export FATOURA_HOME=/your/custom/path
```

<details>
<summary>Stored local files</summary>

- `data/config.json`
- `data/clients.json`
- `data/services.json`
- `data/counters.json`
- `data/history.json`

</details>

## Project files

| File | Purpose |
| --- | --- |
| `src/fatoura_cli/cli.py` | Main CLI logic |
| `src/fatoura_cli/template.html` | Invoice HTML template used for PDF generation |
| `config.example.json` | Example config structure |
| `assets/mock-invoice.png` | Screenshot generated from fake data |
| `assets/mock-invoice.pdf` | Matching fake PDF preview |

## Privacy

- real user data is stored outside the repository by default
- generated PDFs are ignored by git
- local config and invoice history are ignored by git
- the repository contains mock assets only

## Roadmap

- [ ] better README demo assets
- [ ] PyPI publishing
- [ ] changelog for future releases

## License

MIT
