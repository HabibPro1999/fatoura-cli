const items = [];

const $ = (id) => document.getElementById(id);

function formatAmount(value) {
  const negative = value < 0;
  const [integer, decimals] = Math.abs(value).toFixed(3).split(".");
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return (negative ? "-" : "") + grouped + "," + decimals;
}

function formatPercentage(value) {
  return Number.isInteger(value) ? String(value) : formatAmount(value);
}

function round3(value) {
  return Math.round(value * 1000) / 1000;
}

function renderItems() {
  const table = $("items-table");
  const body = $("items-body");
  body.innerHTML = "";
  items.forEach((item, index) => {
    const row = document.createElement("tr");

    const ref = document.createElement("td");
    ref.className = "mono";
    ref.textContent = item.reference || "auto";

    const desc = document.createElement("td");
    desc.textContent = item.description;

    const price = document.createElement("td");
    price.className = "right mono";
    price.textContent = formatAmount(item.unit_price) + " DT";

    const tva = document.createElement("td");
    tva.className = "right mono";
    tva.textContent = formatPercentage(item.tva) + " %";

    const total = document.createElement("td");
    total.className = "right mono";
    total.textContent = formatAmount(item.unit_price) + " DT";

    const remove = document.createElement("td");
    remove.className = "right";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn danger small";
    button.textContent = "Retirer";
    button.addEventListener("click", () => {
      items.splice(index, 1);
      renderItems();
    });
    remove.appendChild(button);

    row.append(ref, desc, price, tva, total, remove);
    body.appendChild(row);
  });
  table.hidden = items.length === 0;

  const totalHt = round3(items.reduce((sum, item) => sum + item.unit_price, 0));
  const totalTva = round3(items.reduce((sum, item) => sum + round3(item.unit_price * item.tva / 100), 0));
  $("total-ht").textContent = formatAmount(totalHt) + " DT";
  $("total-tva").textContent = formatAmount(totalTva) + " DT";
  $("total-net").textContent = formatAmount(round3(totalHt + totalTva)) + " DT";
}

function showError(message) {
  const banner = $("form-error");
  banner.textContent = message;
  banner.hidden = !message;
}

const SUBMIT_LABEL = EDIT ? "Mettre à jour la facture" : "Générer la facture";

const clientSelect = $("client-select");
clientSelect.addEventListener("change", () => {
  $("new-client-fields").hidden = clientSelect.value !== "new";
});

const addServiceButton = $("add-service");
if (addServiceButton) {
  addServiceButton.addEventListener("click", () => {
    const index = Number($("service-select").value);
    const service = SERVICES[index];
    items.push({
      service_index: index,
      reference: service.reference,
      description: service.description,
      unit_price: Number(String(service.unit_price).replace(",", ".")),
      tva: Number(String(service.tva).replace(",", ".")),
    });
    showError("");
    renderItems();
  });
}

["item-desc", "item-price", "item-tva"].forEach((id) => {
  $(id).addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      $("add-item").click();
    }
  });
});

$("add-item").addEventListener("click", () => {
  const description = $("item-desc").value.trim();
  const unitPrice = Number($("item-price").value);
  const tva = Number($("item-tva").value || "0");
  if (!description) return showError("Description obligatoire.");
  if (!(unitPrice > 0)) return showError("Le prix unitaire doit être supérieur à zéro.");
  if (!(tva >= 0)) return showError("Le taux TVA ne peut pas être négatif.");
  items.push({
    description,
    unit_price: unitPrice,
    tva,
    save: $("item-save").checked,
  });
  $("item-desc").value = "";
  $("item-price").value = "";
  $("item-tva").value = "0";
  $("item-save").checked = false;
  showError("");
  renderItems();
});

$("submit").addEventListener("click", async () => {
  let client;
  if (clientSelect.value === "new") {
    const name = $("client-name").value.trim();
    const mf = $("client-mf").value.trim();
    if (!name || !mf) return showError("Nom du client et M/F obligatoires.");
    client = { name, mf, save: $("client-save").checked };
  } else {
    client = { index: Number(clientSelect.value) };
  }
  if (!$("invoice-date").value) return showError("Date obligatoire.");
  if (items.length === 0) return showError("Ajoutez au moins une ligne.");

  const payload = {
    client,
    date: $("invoice-date").value,
    items: items.map((item) =>
      "service_index" in item
        ? { service_index: item.service_index }
        : { description: item.description, unit_price: String(item.unit_price), tva: String(item.tva), save: item.save, reference: item.reference }
    ),
  };

  const submit = $("submit");
  submit.disabled = true;
  submit.textContent = EDIT ? "Mise à jour…" : "Génération…";
  try {
    const response = await fetch(EDIT ? "/api/invoices/" + EDIT.number : "/api/invoices", {
      method: EDIT ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Erreur lors de la génération.");
    window.location = (EDIT ? "/?updated=" : "/?created=") + encodeURIComponent(data.number);
  } catch (error) {
    showError(error.message);
    submit.disabled = false;
    submit.textContent = SUBMIT_LABEL;
  }
});

if (EDIT) {
  clientSelect.value = "new";
  $("new-client-fields").hidden = false;
  $("client-name").value = EDIT.client.name;
  $("client-mf").value = EDIT.client.mf;
  $("client-save").checked = false;
  $("invoice-date").value = EDIT.date;
  EDIT.items.forEach((line) => {
    items.push({
      reference: line.reference,
      description: line.description,
      unit_price: Number(String(line.unit_price).replace(",", ".")),
      tva: Number(String(line.tva).replace(",", ".")),
    });
  });
  $("submit").textContent = SUBMIT_LABEL;
}

renderItems();
