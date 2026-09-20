// Sidebar panel "We Eat": a ready-to-use page that embeds the we-eat-card,
// so users get a dedicated "Dieta" view without adding anything by hand.
//
// The card itself is loaded globally by the integration (add_extra_js_url), so
// this panel only waits for its definition and then mounts an instance. The
// frontend never sets `hass` on inner elements, so we forward it ourselves.
class WeEatPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" }).innerHTML = `
      <style>
        :host { display: block; }
        .wrap { max-width: 680px; margin: 24px auto; padding: 0 16px; }
      </style>
      <div class="wrap"></div>`;
    this._wrap = this.shadowRoot.querySelector(".wrap");
    this._card = null;
    this._hass = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (this._card) {
      this._card.hass = hass;
      return;
    }
    if (customElements.get("we-eat-card")) {
      this._mount();
    } else {
      customElements.whenDefined("we-eat-card").then(() => this._mount());
    }
  }

  _mount() {
    if (this._card) return;
    this._card = document.createElement("we-eat-card");
    this._card.setConfig({
      entity: "sensor.we_eat_menu",
      plan_entity: "sensor.we_eat_piano_settimana",
      kcal_entity: "sensor.we_eat_kcal_consumate",
    });
    this._wrap.appendChild(this._card);
    if (this._hass) this._card.hass = this._hass;
  }
}

if (!customElements.get("we-eat-panel")) {
  customElements.define("we-eat-panel", WeEatPanel);
}
