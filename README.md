# fatoura-cli

CLI pour generer des factures tunisiennes propres en PDF.

`fatoura-cli` cible un cas precis: freelances tunisiens qui veulent une facture simple, propre, locale, sans tableur ni outil web.

![Apercu d'une facture generee](assets/mock-invoice.png)

## Ce que fait l'outil

- enregistre vos informations une seule fois
- reutilise vos clients frequents
- reutilise vos services frequents
- incremente automatiquement les numeros de facture (`FAC-000001`) et de reference (`P-00001`)
- genere un PDF avec format tunisien (`13 750,000 DT`)
- garde vos donnees localement sur votre machine

## Public vise

Ce projet est volontairement limite aux freelances tunisiens:

- dinar tunisien (`DT`)
- numerotation et libelles en francais
- champs locaux comme `Code TVA`, `M/F` et informations bancaires tunisiennes

Ce n'est pas un moteur de facturation multi-pays.

## Prerequis

- Python 3.10+
- `pip`
- dependances systeme WeasyPrint

WeasyPrint est la seule partie un peu sensible a l'installation.

### macOS

La documentation officielle WeasyPrint recommande Homebrew:

```bash
brew install weasyprint
```

### Ubuntu 20.04+

La documentation officielle WeasyPrint recommande au minimum:

```bash
sudo apt install python3-pip libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 libharfbuzz-subset0
```

## Installation

```bash
git clone <repo-url>
cd fatoura-cli
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Une fois installe, la commande `fatoura` est disponible dans l'environnement actif.

## Demarrage rapide

### 1. Initialiser vos informations

```bash
fatoura init
```

L'outil enregistre:

- nom complet
- ville
- adresse
- code TVA
- banque
- IBAN
- dossier de sortie des PDF

### 2. Creer une facture

```bash
fatoura create
```

Le flux est interactif:

- choix ou creation du client
- choix ou creation des lignes de facture
- sauvegarde optionnelle du client et du service pour reutilisation
- apercu terminal
- generation du PDF

### 3. Lister les factures generees

```bash
fatoura list
```

## Stockage local

Par defaut, `fatoura-cli` stocke ses donnees dans:

```text
~/.fatoura-cli/
```

Ce dossier contient notamment:

- `data/config.json`
- `data/clients.json`
- `data/services.json`
- `data/counters.json`
- `data/history.json`

Les PDF sont ecrits dans `~/fatoura-invoices/` par defaut, sauf si vous choisissez un autre dossier pendant `fatoura init`.

Pour forcer un autre dossier de donnees, vous pouvez definir:

```bash
export FATOURA_HOME=/chemin/perso
```

## Fichiers d'exemple

- `config.example.json` montre la forme attendue du fichier de configuration
- `assets/mock-invoice.png` est un apercu genere avec des donnees factices

## Confidentialite

Le projet ne pousse rien vers un service distant.

- vos donnees restent locales
- le repo ignore les PDF generes
- le repo ignore vos fichiers de configuration et vos historiques locaux

## Licence

MIT
