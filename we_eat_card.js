const DAYS = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"];
const MEALS = ["colazione", "spuntino", "pranzo", "merenda", "cena"];
const MAX_FILE_BYTES = 3 * 1024 * 1024;
const DISCLAIMER = "Le calorie stimate dall'AI sono approssimative e non sono un parere medico.";

function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") el.className = value;
    else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else if (value !== undefined && value !== null && value !== false) el.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return el;
}

const cap = (text) => text.charAt(0).toUpperCase() + text.slice(1);
const mealKcal = (items) => items.reduce((sum, item) => sum + item.kcal, 0);

function readAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = () => reject(new Error("Lettura del file non riuscita"));
    reader.readAsDataURL(file);
  });
}

async function shrinkImage(file) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
  return { file_b64: dataUrl.split(",")[1], mime_type: "image/jpeg" };
}

class WeEatCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      entity: "sensor.we_eat_menu",
      plan_entity: "sensor.we_eat_piano_settimana",
      kcal_entity: "sensor.we_eat_kcal_consumate",
      ...config,
    };
    this._tab = this._tab || "oggi";
    this._message = "";
  }

  getCardSize() {
    return 6;
  }

  set hass(hass) {
    this._hass = hass;
    const menu = hass.states[this.config.entity];
    const plan = hass.states[this.config.plan_entity];
    const kcal = hass.states[this.config.kcal_entity];
    if (!menu || !plan || !kcal) {
      this.replaceChildren(h("ha-card", { header: "We Eat" }, h("div", { class: "card-content" }, "Entità di We Eat non trovate.")));
      return;
    }
    const signature = [menu, plan, kcal].map((s) => s.last_updated).join("|");
    const typing = this.contains(document.activeElement) && document.activeElement.matches("input, textarea");
    if (signature === this._signature || typing) return;
    if (!this._signature || plan.attributes.draft_days !== this._plan?.attributes.draft_days) this._draft = null;
    this._signature = signature;
    this._menu = menu;
    this._plan = plan;
    this._kcal = kcal;
    this._render();
  }

  _call(service, data, success) {
    this._message = "…";
    this._render();
    return this._hass
      .callService("we_eat", service, data)
      .then(() => {
        this._message = success || "";
        this._signature = null;
      })
      .catch((err) => {
        this._message = err.message || "Operazione non riuscita";
      })
      .finally(() => this._render());
  }

  _setTab(tab) {
    this._tab = tab;
    this._render();
  }

  _render() {
    if (!this._menu) return;
    const tabs = [["oggi", "Oggi"], ["settimana", "Settimana"], ["importa", "Importa"]];
    const body = { oggi: () => this._today(), settimana: () => this._week(), importa: () => this._import() }[this._tab]();
    this.replaceChildren(
      h(
        "ha-card",
        { header: "We Eat" },
        h(
          "div",
          { class: "card-content" },
          h("div", {}, ...tabs.map(([id, label]) =>
            h("button", { onclick: () => this._setTab(id), disabled: this._tab === id }, label))),
          this._message && h("p", {}, this._message),
          body,
          h("p", { style: "opacity:.6;font-size:.8em" }, DISCLAIMER),
        ),
      ),
    );
  }

  _today() {
    const today = this._menu.attributes.today || {};
    const entries = this._kcal.attributes.entries || [];
    const target = this._kcal.attributes.target;
    const total = Number(this._kcal.state) || 0;
    const rows = MEALS.filter((meal) => (today[meal] || []).length).map((meal) => {
      const done = entries.some((e) => e.meal === meal && e.source === "plan");
      const items = today[meal];
      return h(
        "div",
        { style: this._menu.attributes.meal === meal ? "font-weight:600" : "" },
        `${cap(meal)} (${mealKcal(items)} kcal): `,
        items.map((i) => `${i.food}${i.quantity ? " " + i.quantity : ""}${i.estimated ? " (stimato)" : ""}`).join(", "),
        " ",
        h("button", { disabled: done, onclick: () => this._call("log_plan_meal", { meal }) }, done ? "Fatto ✓" : "Fatto come da piano"),
      );
    });
    const mealSelect = h("select", {}, ...MEALS.map((m) => h("option", { value: m }, cap(m))));
    const text = h("input", { type: "text", placeholder: "Extra (es. 2 fette di pizza)" });
    const kcal = h("input", { type: "number", min: "0", placeholder: "kcal (facoltative)", style: "width:9em" });
    const add = () => {
      if (!text.value.trim()) return;
      const data = { text: text.value.trim(), meal: mealSelect.value };
      if (kcal.value !== "") data.kcal = Number(kcal.value);
      this._call("log_extra", data);
    };
    return h(
      "div",
      {},
      h("p", {}, `Consumate: ${total} kcal` + (target ? ` su ${target}` : "")),
      target && h("progress", { max: target, value: Math.min(total, target), style: "width:100%" }),
      rows.length ? rows : h("p", {}, "Nessun pasto previsto oggi dal piano."),
      h("div", {}, text, mealSelect, kcal, h("button", { onclick: add }, "Aggiungi")),
      h("ul", {}, ...entries.map((e) =>
        h("li", {}, `${e.time} ${cap(e.meal)}: ${e.text || "come da piano"} — ${e.kcal} kcal${e.estimated ? " (stimato)" : ""} `,
          h("button", { onclick: () => this._call("remove_entry", { entry_id: e.id }) }, "×")))),
    );
  }

  _week() {
    const days = this._plan.attributes.days || {};
    if (!Object.keys(days).length) return h("p", {}, "Nessun piano attivo: importalo dalla scheda Importa.");
    const todayIndex = (new Date().getDay() + 6) % 7;
    const cell = (items) => (items || []).map((i) => `${i.food} (${i.kcal})`).join(", ");
    return h(
      "table",
      { style: "width:100%;border-collapse:collapse" },
      h("tr", {}, h("th", {}), ...MEALS.map((m) => h("th", {}, cap(m)))),
      ...DAYS.map((name, index) =>
        h("tr", { style: index === todayIndex ? "font-weight:600;background:rgba(127,127,127,.15)" : "" },
          h("td", {}, name),
          ...MEALS.map((meal) => h("td", { style: "vertical-align:top;font-size:.85em" }, cell((days[index] || {})[meal])))),
      ),
    );
  }

  _import() {
    const draftDays = this._plan.attributes.draft_days || {};
    const hasDraft = this._plan.state === "bozza" && Object.keys(draftDays).length;
    const textarea = h("textarea", { rows: "5", style: "width:100%", placeholder: "Incolla qui il piano del dietologo" });
    const file = h("input", { type: "file", accept: "application/pdf,image/*" });
    const send = async () => {
      try {
        if (file.files[0]) {
          const chosen = file.files[0];
          if (chosen.size > MAX_FILE_BYTES && chosen.type === "application/pdf") throw new Error("Il PDF supera i 3 MB");
          const payload = chosen.type === "application/pdf"
            ? { file_b64: await readAsBase64(chosen), mime_type: chosen.type }
            : await shrinkImage(chosen);
          await this._call("import_plan", payload, "Bozza creata: controllala qui sotto.");
        } else if (textarea.value.trim()) {
          await this._call("import_plan", { text: textarea.value.trim() }, "Bozza creata: controllala qui sotto.");
        }
      } catch (err) {
        this._message = err.message;
        this._render();
      }
    };
    return h(
      "div",
      {},
      h("p", {}, "Importa il piano da testo, PDF o foto. Dovrai controllarlo prima di attivarlo."),
      textarea,
      h("div", {}, file, h("button", { onclick: send }, "Importa")),
      hasDraft && this._draftEditor(draftDays),
    );
  }

  _draftEditor(draftDays) {
    if (!this._draft) this._draft = JSON.parse(JSON.stringify(draftDays));
    const draft = this._draft;
    const input = (item, key, type, width) =>
      h("input", {
        type, value: item[key], style: `width:${width}`,
        oninput: (ev) => { item[key] = type === "number" ? Number(ev.target.value) : ev.target.value; item.estimated = key === "kcal" ? false : item.estimated; },
      });
    const blocks = DAYS.flatMap((name, index) =>
      MEALS.filter((meal) => ((draft[index] || {})[meal] || []).length).map((meal) => {
        const items = draft[index][meal];
        return h("div", { style: "margin:.5em 0" },
          h("strong", {}, `${name} — ${cap(meal)}`),
          ...items.map((item, pos) => h("div", {},
            input(item, "food", "text", "40%"), input(item, "quantity", "text", "20%"), input(item, "kcal", "number", "6em"),
            item.estimated ? " (stimato) " : " ",
            h("button", { onclick: () => { items.splice(pos, 1); this._render(); } }, "×"))),
          h("button", { onclick: () => { items.push({ food: "", quantity: "", kcal: 0, estimated: false }); this._render(); } }, "+ alimento"));
      }));
    const save = () => this._call("save_draft", { days: this._draft }, "Bozza salvata.");
    const confirm = async () => {
      await this._call("save_draft", { days: this._draft });
      if (!this._message) await this._call("confirm_plan", {}, "Piano attivato.");
    };
    return h("div", {}, h("h3", {}, "Bozza da controllare"), ...blocks,
      h("button", { onclick: save }, "Salva bozza"), h("button", { onclick: confirm }, "Conferma e attiva"));
  }

  static getConfigElement() {
    return document.createElement("hui-entities-card-editor");
  }

  static getStubConfig() {
    return { entity: "sensor.we_eat_menu" };
  }
}
customElements.define("we-eat-card", WeEatCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "we-eat-card",
  name: "We Eat Card",
  description: "Piano settimanale del dietologo, diario dei pasti e conteggio calorie.",
});
