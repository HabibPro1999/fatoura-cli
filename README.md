# fatoura-cli

Clean PDF invoice generator for Tunisian freelancers.

`fatoura-cli` is intentionally narrow: it helps Tunisian freelancers generate professional invoices quickly from the terminal, without spreadsheets or web apps.

> [!IMPORTANT]
> The repository and documentation are in English. The CLI prompts and generated invoices stay in French by design.

![Preview of a generated mock invoice](assets/mock-invoice.png)

## Why this exists

- save your business details once
- reuse frequent clients
- reuse frequent services
- auto-increment invoice numbers like `FAC-000001`
- auto-increment line references like `P-00001`
- generate Tunisian-formatted totals like `13 750,000 DT`
- keep all personal data local

## Scope

This project is for Tunisian freelancers only.

- currency: Tunisian dinar (`DT`)
- language: French invoice labels and prompts
- local fields: `Code TVA`, `M/F`, bank information

This is not a multi-country invoicing engine.

## Commands

| Command | What it does |
| --- | --- |
| `fatoura init` | Save your profile, tax, bank, and output settings |
| `fatoura create` | Create a new invoice with interactive prompts |
| `fatoura list` | List previously generated invoices |

## Quick start

### 1. Install system dependencies

<details>
<summary>macOS</summary>

GitHub renders `<details>` blocks as collapsible sections. The official WeasyPrint documentation recommends installing WeasyPrint and its dependencies with Homebrew:

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

### 2. Install the CLI

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

You will be prompted for:

- full name
- city
- address
- VAT code
- bank name
- IBAN
- output directory for generated PDFs

### 4. Create your first invoice

```bash
fatoura create
```

The flow is interactive:

1. choose an existing client or add a new one
2. choose an existing service or add a new one
3. review the invoice summary in the terminal
4. generate the PDF

### 5. Check invoice history

```bash
fatoura list
```

## What gets stored locally

> [!NOTE]
> `fatoura-cli` does not send data to any remote service.

By default, app data lives in:

```text
~/.fatoura-cli/
```

<details>
<summary>Stored files</summary>

- `data/config.json`
- `data/clients.json`
- `data/services.json`
- `data/counters.json`
- `data/history.json`

</details>

Generated PDFs go to `~/fatoura-invoices/` by default unless you choose another directory during `fatoura init`.

You can override the app data directory with:

```bash
export FATOURA_HOME=/your/custom/path
```

## Example files

- `config.example.json` shows the expected configuration shape
- `assets/mock-invoice.png` is a screenshot generated from fake data
- `assets/mock-invoice.pdf` is the matching fake PDF preview

## Privacy

- generated PDFs are ignored by git
- local config and invoice history are ignored by git
- the repository ships with mock data only

## License

MIT
