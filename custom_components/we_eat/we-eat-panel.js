// Sidebar panel "We Eat": a ready-to-use page that embeds the we-eat-card.
//
// The panel loads the card itself, from its own directory, instead of waiting for the copy the
// integration adds to the page: waiting on customElements.whenDefined() never resolves when that
// copy fails to load, which leaves a blank page with nothing to explain it. The frontend does not
// set `hass` on inner elements, so we forward it ourselves.
const CARD_URL = new URL("./we-eat-card.js", import.meta.url).href;

class WeEatPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" }).innerHTML = `
      <style>
        :host { display: block; }
        .wrap { max-width: 680px; margin: 24px auto; padding: 0 16px; }
        .error { color: var(--error-color, #c62828); font-family: sans-serif; line-height: 1.5; }
        code { word-break: break-all; }
      </style>
      <div class="wrap"></div>`;
    this._wrap = this.shadowRoot.querySelector(".wrap");
    this._card = null;
    this._hass = null;
    this._loading = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (this._card) {
      this._card.hass = hass;
      return;
    }
    this._loading = this._loading || this._load();
  }

  async _load() {
    if (!customElements.get("we-eat-card")) {
      try {
        await import(CARD_URL);
      } catch (err) {
        this._fail(err);
        return;
      }
    }
    this._mount();
  }

  _mount() {
    if (this._card) return;
    this._card = document.createElement("we-eat-card");
    this._card.setConfig({ entity: "sensor.we_eat_menu" });
    this._wrap.appendChild(this._card);
    if (this._hass) this._card.hass = this._hass;
  }

  _fail(err) {
    this._wrap.innerHTML = `
      <div class="error">
        <p><strong>Impossibile caricare la card We Eat.</strong></p>
        <p>Il file non è stato servito da <code>${CARD_URL}</code>.</p>
        <p>Riavvia Home Assistant; se il problema resta, reinstalla We Eat da HACS e controlla
        <em>Impostazioni → Sistema → Log</em> cercando <code>we_eat</code>.</p>
        <p><code>${String(err && err.message ? err.message : err)}</code></p>
      </div>`;
  }
}

if (!customElements.get("we-eat-panel")) {
  customElements.define("we-eat-panel", WeEatPanel);
}
