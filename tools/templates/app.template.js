(() => {
  "use strict";

  const pad = (value) => String(value).padStart(2, "0");

  const sequence = (count, folder, prefix, title, note, variant, tone = "green") =>
    Array.from({ length: count }, (_, index) => {
      const id = pad(index + 1);
      return {
        id,
        title: `${title} ${id}`,
        src: `./assets/images/${folder}/${prefix}-${id}.png`,
        note,
        kicker: "FULL IMAGE · NO CROP",
        variant,
        tone,
      };
    });

  const groups = {
    evidence: [
      ["01", "16 ABR 2025 · FACTURA APPLE", "evidencia-01.png", "PÁG. 05"],
      ["02", "14 MAY 2025 · FACTURACIÓN APPLE", "evidencia-02.png", "PÁG. 06"],
      ["03", "31/12/69 · ESTADO ANÓMALO", "evidencia-03.png", "PÁG. 07"],
      ["04", "13 JUL 2025 · OPENAI / AUTH", "evidencia-04.png", "PÁG. 08"],
      ["05", "RETORNO · 18/05/25", "evidencia-05.png", "PÁG. 09"],
      ["06", "MARZO 2025 · APROX.", "evidencia-06.png", "PÁG. 10"],
    ].map(([id, title, file, kicker]) => ({
      id,
      title,
      src: `./assets/images/evidencia/${file}`,
      kicker,
      note: "BLOQUE E001",
      variant: "standard",
      tone: "green",
    })),
    error1969: sequence(
      7,
      "error-31-12-69",
      "error-31-12-69",
      "CAPTURA ERROR 31/12/69",
      "SESIÓN ANÓMALA",
      "tall",
      "red",
    ),
    remake666: sequence(
      9,
      "remake-666",
      "remake-666",
      "666 MODERNO REMAKE",
      "MEMORIA REACTIVADA",
      "tall",
      "red",
    ),
    routes: sequence(
      6,
      "rutas-sixtem",
      "rutas-sixtem",
      "EVIDENCIA DE RUTA",
      "C:/T6D6 · C:/SIXTX · C:/Z6N6",
      "wide",
    ),
    sixtem: sequence(
      7,
      "lseo-sixtem",
      "lseo-sixtem",
      "LSEØ SIXTEM",
      "CUERPO TÉCNICO",
      "tall",
    ),
    extras: sequence(
      20,
      "bloque-extra",
      "bloque-extra",
      "ARCHIVO EXTRA",
      "RESERVA ABIERTA",
      "extra",
    ),
    songs: [
      {
        id: "01",
        title: "LEY DEL SEXTO",
        src: "./assets/images/canciones/01-ley-del-sexto.jpg",
        kicker: "LANZADA",
        note: "EL ORIGEN VISIBLE DE LA LEY DEL SEXTO.",
      },
      {
        id: "02",
        title: "ZONA GRIS",
        src: "./assets/images/canciones/02-zona-gris.jpg",
        kicker: "LANZADA",
        note: "QUIEN MANIPULA LO INVISIBLE, CONTROLA LO QUE SE VE.",
      },
      {
        id: "03",
        title: "CLONES Y FANTASMAS",
        src: "./assets/images/canciones/03-clones-y-fantasmas.jpg",
        kicker: "LANZADA",
        note: "IDENTIDAD, DUPLICACIÓN Y RESIDUOS DE PRESENCIA.",
      },
      {
        id: "04",
        title: "NADA ME BORRA",
        src: "./assets/images/canciones/04-nada-me-borra.jpg",
        kicker: "LANZADA",
        note: "LA HERIDA COMO SELLO DE PERMANENCIA.",
      },
      {
        id: "05",
        title: "LIBRE PRISIONERO",
        src: "./assets/images/canciones/05-libre-prisionero.jpg",
        kicker: "LANZADA",
        note: "NI LIBRE NI PRESO: GRADOS DE ESCLAVITUD.",
      },
      {
        id: "06",
        title: "ERROR 404",
        src: "./assets/images/canciones/06-error-404.jpg",
        kicker: "LANZADA",
        note: "CIERRE DE LA GRIETA Y EXPANSIÓN DEL MAPA VARIABLE.",
      },
    ].map((slot) => ({ ...slot, variant: "song", tone: "amber" })),
  };

  const escapeHtml = (value) =>
    String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const filenameOf = (path) => path.split("/").pop() || path;

  const slotMarkup = (slot) => {
    const isLogo = slot.variant === "logo";
    const filename = filenameOf(slot.src);
    const head = isLogo
      ? ""
      : `
        <div class="slot-head">
          <span class="slot-id">${escapeHtml(slot.id)}</span>
          <strong>${escapeHtml(slot.title)}</strong>
          <small>${escapeHtml(slot.kicker || "FULL IMAGE · NO CROP")}</small>
        </div>`;
    const foot = isLogo
      ? ""
      : `
        <div class="slot-foot">
          <span>⌁ ${escapeHtml(slot.note || "ARCHIVO LOCAL")}</span>
          <span class="slot-path">${escapeHtml(slot.src)}</span>
        </div>`;

    return `
      <article
        class="archive-slot tone-${escapeHtml(slot.tone || "green")} variant-${escapeHtml(slot.variant || "standard")} is-loading"
        data-file="${escapeHtml(filename)}"
      >
        ${head}
        <button
          class="slot-media"
          type="button"
          disabled
          aria-label="Espacio reservado para ${escapeHtml(filename)}"
        >
          <img src="${escapeHtml(slot.src)}" alt="${escapeHtml(slot.title)}" ${isLogo ? "" : 'loading="lazy"'}>
          <span class="slot-placeholder">
            <span class="slot-reticle"></span>
            <small>${isLogo ? "NODO DE LOGO" : "ESPACIO LISTO"}</small>
            <code>${escapeHtml(filename)}</code>
            <b>${isLogo ? "INSERTA AQUÍ TU LOGO" : "INSERTA AQUÍ TU IMAGEN"}</b>
          </span>
          <span class="slot-scan" aria-hidden="true"></span>
          <span class="slot-corner corner-a" aria-hidden="true"></span>
          <span class="slot-corner corner-b" aria-hidden="true"></span>
          <span class="slot-corner corner-c" aria-hidden="true"></span>
          <span class="slot-corner corner-d" aria-hidden="true"></span>
        </button>
        ${foot}
      </article>`;
  };

  const activateSlot = (article) => {
    const image = article.querySelector("img");
    const button = article.querySelector(".slot-media");
    if (!image || !button) return;

    const setState = (state) => {
      article.classList.remove("is-loading", "is-ready", "is-missing");
      article.classList.add(`is-${state}`);
      button.disabled = state !== "ready";
      button.setAttribute(
        "aria-label",
        state === "ready"
          ? `Abrir ${image.alt}`
          : `Espacio reservado para ${article.dataset.file || "imagen"}`,
      );
    };

    image.addEventListener("load", () => setState("ready"), { once: true });
    image.addEventListener("error", () => setState("missing"), { once: true });
    button.addEventListener("click", () => {
      if (article.classList.contains("is-ready")) {
        window.open(image.src, "_blank", "noopener,noreferrer");
      }
    });

    if (image.complete) {
      setState(image.naturalWidth > 0 ? "ready" : "missing");
    }
  };

  document.querySelectorAll("[data-slot-group]").forEach((container) => {
    const name = container.dataset.slotGroup;
    const slots = groups[name] || [];
    container.innerHTML = slots.map(slotMarkup).join("");
    container.querySelectorAll(".archive-slot").forEach(activateSlot);
  });

  document.querySelectorAll("[data-single-slot]").forEach((container) => {
    const slot = {
      id: container.dataset.id || "L",
      title: container.dataset.title || "Logo LSE6",
      src: container.dataset.src || "",
      tone: container.dataset.tone || "green",
      variant: "logo",
    };
    const wrapper = document.createElement("div");
    wrapper.innerHTML = slotMarkup(slot).trim();
    const article = wrapper.firstElementChild;
    if (article) {
      container.replaceWith(article);
      activateSlot(article);
    }
  });

  const eye = document.querySelector(".eye-frame");
  if (eye) {
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;
    let energy = 0;
    let lastInputAt = performance.now();
    let lastPointerX = window.innerWidth / 2;
    let lastPointerY = window.innerHeight / 2;

    const aim = (clientX, clientY) => {
      const rect = eye.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      targetX = Math.max(-1, Math.min(1, (clientX - centerX) / Math.max(rect.width * 0.52, 1)));
      targetY = Math.max(-1, Math.min(1, (clientY - centerY) / Math.max(rect.height * 0.72, 1)));

      const velocity = Math.hypot(clientX - lastPointerX, clientY - lastPointerY);
      energy = Math.min(1, energy + velocity / 150);
      lastInputAt = performance.now();
      lastPointerX = clientX;
      lastPointerY = clientY;
    };

    window.addEventListener("pointermove", (event) => aim(event.clientX, event.clientY), { passive: true });
    document.documentElement.addEventListener("pointerleave", () => {
      lastInputAt = 0;
    });

    const animateEye = (time) => {
      const idle = time - lastInputAt > 1450;
      const idleX = Math.sin(time / 1550) * 0.34 + Math.sin(time / 5300) * 0.11;
      const idleY = Math.cos(time / 2100) * 0.17 + Math.sin(time / 3900) * 0.08;
      const activeX = idle ? idleX : targetX;
      const activeY = idle ? idleY : targetY;

      currentX += (activeX - currentX) * (idle ? 0.026 : 0.115);
      currentY += (activeY - currentY) * (idle ? 0.026 : 0.115);
      energy *= 0.92;

      eye.style.setProperty("--look-shell-x", `${(currentX * 7).toFixed(3)}px`);
      eye.style.setProperty("--look-shell-y", `${(currentY * 5).toFixed(3)}px`);
      eye.style.setProperty("--look-gaze-x", `${(currentX * 24).toFixed(3)}px`);
      eye.style.setProperty("--look-gaze-y", `${(currentY * 15).toFixed(3)}px`);
      eye.style.setProperty("--look-rotate-x", `${(currentY * -3).toFixed(3)}deg`);
      eye.style.setProperty("--look-rotate-y", `${(currentX * 4).toFixed(3)}deg`);
      eye.style.setProperty("--eye-energy", energy.toFixed(4));
      document.documentElement.style.setProperty("--title-drift-x", `${(currentX * 4).toFixed(3)}px`);
      document.documentElement.style.setProperty("--title-drift-y", `${(currentY * 2).toFixed(3)}px`);

      requestAnimationFrame(animateEye);
    };

    requestAnimationFrame(animateEye);
  }

  const navLinks = [...document.querySelectorAll('.archive-nav a[href^="#"]')];
  const sections = navLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        const active = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!active) return;
        navLinks.forEach((link) => {
          link.classList.toggle("is-active", link.getAttribute("href") === `#${active.target.id}`);
        });
      },
      { rootMargin: "-15% 0px -68%", threshold: [0.05, 0.2, 0.45] },
    );
    sections.forEach((section) => observer.observe(section));
  }
})();
