// Portal Fake - RPA (estatico) - CRUD + filtros + export/import + modal fechavel
(function () {
  const STORAGE_KEY = "PF_RPA_DB_V1";

  // --- elementos (DOM ids estaveis p/ Playwright) ---
  const q = document.getElementById("q");
  const statusSel = document.getElementById("status");
  const btnBuscar = document.getElementById("btnBuscar");
  const btnLimpar = document.getElementById("btnLimpar");
  const btnNovo = document.getElementById("btnNovo");

  const btnExportCsv = document.getElementById("btnExportCsv");
  const btnExportJson = document.getElementById("btnExportJson");
  const fileImportJson = document.getElementById("fileImportJson");
  const btnClearAll = document.getElementById("btnClearAll");

  const tbody = document.getElementById("tbody");
  const empty = document.getElementById("empty");
  const count = document.getElementById("count");

  const detailsCard = document.getElementById("detailsCard");
  const details = document.getElementById("details");
  const btnFecharDetalhes = document.getElementById("btnFecharDetalhes");

  const modal = document.getElementById("modal");
  const modalBackdrop = document.getElementById("modalBackdrop");
  const btnModalClose = document.getElementById("btnModalClose");
  const modalTitle = document.getElementById("modalTitle");

  const form = document.getElementById("form");
  const formMsg = document.getElementById("formMsg");
  const btnCancelar = document.getElementById("btnCancelar");

  // form fields
  const f_id = document.getElementById("f_id");
  const f_nome = document.getElementById("f_nome");
  const f_sobrenome = document.getElementById("f_sobrenome");
  const f_cpf = document.getElementById("f_cpf");
  const f_email = document.getElementById("f_email");
  const f_telefone = document.getElementById("f_telefone");
  const f_nascimento = document.getElementById("f_nascimento");
  const f_status = document.getElementById("f_status");
  const f_endereco = document.getElementById("f_endereco");
  const f_observacao = document.getElementById("f_observacao");

  // --- utils ---
  function norm(s) {
    return (s || "")
      .toString()
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "");
  }

  function escapeHtml(str) {
    return (str ?? "").toString()
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function onlyDigits(s){ return (s||"").toString().replace(/\D/g, ""); }

  function isEmail(s){
    const v = (s||"").toString().trim();
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  }

  function buildFullName(nome, sobrenome){
    return [String(nome||"").trim(), String(sobrenome||"").trim()].filter(Boolean).join(" ");
  }

  function statusBadge(status) {
    const s = (status || "").toUpperCase();
    let cls = "badge";
    if (s === "ATIVO") cls += " ok";
    else if (s === "PENDENTE") cls += " warn";
    else if (s === "BLOQUEADO") cls += " bad";
    return `<span class="${cls}"><span class="dot"></span>${s}</span>`;
  }

  // --- storage ---
  function loadDB() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  function saveDB(db){ localStorage.setItem(STORAGE_KEY, JSON.stringify(db)); }

  let DB = loadDB();

  function nextId(){
    let max = 0;
    for (const p of DB) max = Math.max(max, Number(p.id)||0);
    return max + 1;
  }

  // --- filters/render ---
  function matches(p, query){
    const hay = norm([p.nome_completo, p.nome, p.sobrenome, p.cpf, p.email].join(" "));
    const needle = norm(query);
    if (!needle) return true;
    return hay.includes(needle);
  }

  function applyFilters(){
    const query = q.value;
    const st = (statusSel.value||"").toUpperCase();

    const filtered = DB.filter(p => {
      const okQuery = matches(p, query);
      const okStatus = !st || (p.status||"").toUpperCase() === st;
      return okQuery && okStatus;
    });

    renderTable(filtered);
    closeDetails();
  }

  function renderTable(list){
    tbody.innerHTML = "";

    if (!list.length){
      empty.style.display = "block";
      count.textContent = "0 encontrados";
      return;
    }

    empty.style.display = "none";
    count.textContent = `${list.length} encontrado(s)`;

    for (const p of list){
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(p.nome_completo)}</td>
        <td><code>${escapeHtml(p.cpf)}</code></td>
        <td>${escapeHtml(p.email)}</td>
        <td>${statusBadge(p.status)}</td>
        <td style="text-align:right; white-space:nowrap;">
          <button class="btn secondary" data-action="ver" data-id="${p.id}">Ver</button>
          <button class="btn secondary" data-action="editar" data-id="${p.id}">Editar</button>
          <button class="btn danger" data-action="excluir" data-id="${p.id}">Excluir</button>
        </td>
      `;
      tbody.appendChild(tr);
    }
  }

  // --- details ---
  function openDetails(id){
    const p = DB.find(x => String(x.id) === String(id));
    if (!p) return;

    details.innerHTML = `
      <div class="kv"><div class="k">Nome completo</div><div class="v">${escapeHtml(p.nome_completo)}</div></div>
      <div class="kv"><div class="k">Status</div><div class="v">${statusBadge(p.status)}</div></div>

      <div class="kv"><div class="k">Nome</div><div class="v">${escapeHtml(p.nome)}</div></div>
      <div class="kv"><div class="k">Sobrenome</div><div class="v">${escapeHtml(p.sobrenome)}</div></div>

      <div class="kv"><div class="k">CPF</div><div class="v"><code>${escapeHtml(p.cpf)}</code></div></div>
      <div class="kv"><div class="k">E-mail</div><div class="v">${escapeHtml(p.email)}</div></div>

      <div class="kv"><div class="k">Telefone</div><div class="v">${escapeHtml(p.telefone||"")}</div></div>
      <div class="kv"><div class="k">Nascimento</div><div class="v">${escapeHtml(p.nascimento||"")}</div></div>

      <div class="kv" style="grid-column: 1 / -1;"><div class="k">Endereco</div><div class="v">${escapeHtml(p.endereco||"")}</div></div>
      <div class="kv" style="grid-column: 1 / -1;"><div class="k">Observacao</div><div class="v">${escapeHtml(p.observacao||"")}</div></div>
    `;
    detailsCard.hidden = false;
    detailsCard.scrollIntoView({behavior:"smooth", block:"start"});
  }

  function closeDetails(){
    detailsCard.hidden = true;
    details.innerHTML = "";
  }

  // --- modal control (fix de travar) ---
  function openModal(mode, person){
    form.reset();
    formMsg.textContent = "";
    f_id.value = "";

    if (mode === "new"){
      modalTitle.textContent = "Novo cadastro";
    } else {
      modalTitle.textContent = "Editar cadastro";
      f_id.value = String(person.id);
      f_nome.value = person.nome || "";
      f_sobrenome.value = person.sobrenome || "";
      f_cpf.value = person.cpf || "";
      f_email.value = person.email || "";
      f_telefone.value = person.telefone || "";
      f_nascimento.value = person.nascimento || "";
      f_status.value = (person.status || "ATIVO").toUpperCase();
      f_endereco.value = person.endereco || "";
      f_observacao.value = person.observacao || "";
    }

    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");

    // foco inicial (bom pro PyAutoGUI também)
    setTimeout(() => f_nome.focus(), 0);
  }

  function closeModal(){
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    form.reset();
    formMsg.textContent = "";
  }

  function validateForm(){
    const nome = f_nome.value.trim();
    const sobrenome = f_sobrenome.value.trim();
    const cpf = onlyDigits(f_cpf.value);
    const email = f_email.value.trim();

    if (!nome || !sobrenome) return "Nome e sobrenome sao obrigatorios.";
    if (cpf.length !== 11) return "CPF deve ter 11 numeros (somente numeros).";
    if (!isEmail(email)) return "E-mail invalido.";

    const id = f_id.value ? String(f_id.value) : null;
    const exists = DB.some(p => p.cpf === cpf && String(p.id) !== String(id));
    if (exists) return "CPF ja existe na base.";
    return null;
  }

  function upsertPerson(){
    const id = f_id.value ? Number(f_id.value) : null;
    const cpf = onlyDigits(f_cpf.value);

    const person = {
      id: id ?? nextId(),
      nome: f_nome.value.trim(),
      sobrenome: f_sobrenome.value.trim(),
      nome_completo: buildFullName(f_nome.value, f_sobrenome.value),
      cpf,
      email: f_email.value.trim(),
      telefone: f_telefone.value.trim(),
      nascimento: f_nascimento.value,
      status: (f_status.value || "ATIVO").toUpperCase(),
      endereco: f_endereco.value.trim(),
      observacao: f_observacao.value.trim()
    };

    if (id == null){
      DB.unshift(person);
    } else {
      const idx = DB.findIndex(p => String(p.id) === String(id));
      if (idx >= 0) DB[idx] = person;
      else DB.unshift(person);
    }
    saveDB(DB);
  }

  function deletePerson(id){
    DB = DB.filter(p => String(p.id) !== String(id));
    saveDB(DB);
  }

  // --- export/import ---
  function downloadText(filename, text, mime){
    const blob = new Blob([text], {type: mime});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function exportJSON(){
    const payload = JSON.stringify(DB, null, 2);
    const ts = new Date().toISOString().replaceAll(":","").slice(0,15);
    downloadText(`cadastros_${ts}.json`, payload, "application/json");
  }

  function csvEscape(v){
    const s = (v ?? "").toString();
    if (/[",\n\r;]/.test(s)) return `"${s.replaceAll('"','""')}"`;
    return s;
  }

  function exportCSV(){
    const cols = ["id","nome","sobrenome","nome_completo","cpf","email","telefone","nascimento","status","endereco","observacao"];
    const header = cols.join(";");
    const lines = [header];
    for (const p of DB){
      lines.push(cols.map(c => csvEscape(p[c])).join(";"));
    }
    const ts = new Date().toISOString().replaceAll(":","").slice(0,15);
    downloadText(`cadastros_${ts}.csv`, lines.join("\n"), "text/csv");
  }

  async function importJSON(file){
    const txt = await file.text();
    const parsed = JSON.parse(txt);
    if (!Array.isArray(parsed)) throw new Error("JSON precisa ser uma lista (array).");

    const cleaned = [];
    const seenCpf = new Set();

    for (let i=0; i<parsed.length; i++){
      const p = parsed[i] || {};
      const nome = String(p.nome || "").trim();
      const sobrenome = String(p.sobrenome || "").trim();
      const cpf = onlyDigits(p.cpf || "");
      const email = String(p.email || "").trim();

      if (!nome || !sobrenome) continue;
      if (cpf.length !== 11) continue;
      if (!isEmail(email)) continue;
      if (seenCpf.has(cpf)) continue;
      seenCpf.add(cpf);

      cleaned.push({
        id: Number(p.id) || (i+1),
        nome,
        sobrenome,
        nome_completo: p.nome_completo ? String(p.nome_completo) : buildFullName(nome, sobrenome),
        cpf,
        email,
        telefone: String(p.telefone || ""),
        nascimento: String(p.nascimento || ""),
        status: String(p.status || "ATIVO").toUpperCase(),
        endereco: String(p.endereco || ""),
        observacao: String(p.observacao || "")
      });
    }

    DB = cleaned;
    saveDB(DB);
  }

  // --- events ---
  btnBuscar.addEventListener("click", applyFilters);
  btnLimpar.addEventListener("click", () => { q.value=""; statusSel.value=""; applyFilters(); });
  q.addEventListener("keydown", (e) => { if (e.key === "Enter") applyFilters(); });

  btnNovo.addEventListener("click", () => openModal("new"));

  btnFecharDetalhes.addEventListener("click", closeDetails);

  // table actions
  tbody.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    const action = btn.getAttribute("data-action");
    const id = btn.getAttribute("data-id");
    const person = DB.find(p => String(p.id) === String(id));
    if (!person) return;

    if (action === "ver") openDetails(id);
    if (action === "editar") openModal("edit", person);
    if (action === "excluir") {
      const ok = confirm(`Excluir cadastro de ${person.nome_completo}?`);
      if (!ok) return;
      deletePerson(id);
      applyFilters();
      closeDetails();
    }
  });

  // modal close controls (3 jeitos):
  // 1) botao X
  // 2) clicar no backdrop
  // 3) tecla ESC
  btnModalClose.addEventListener("click", closeModal);
  btnCancelar.addEventListener("click", closeModal);
  modalBackdrop.addEventListener("click", closeModal);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.hidden) closeModal();
  });

  // form submit
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    formMsg.textContent = "";
    const err = validateForm();
    if (err) { formMsg.textContent = err; return; }

    upsertPerson();
    closeModal();
    applyFilters();
  });

  // export/import/clear
  btnExportJson.addEventListener("click", exportJSON);
  btnExportCsv.addEventListener("click", exportCSV);

  fileImportJson.addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    try {
      await importJSON(f);
      alert("Importacao concluida.");
      applyFilters();
    } catch (err) {
      alert("Falha ao importar: " + (err?.message || err));
    } finally {
      fileImportJson.value = "";
    }
  });

  btnClearAll.addEventListener("click", () => {
    const ok = confirm("Zerar base? Isso apaga todos os cadastros.");
    if (!ok) return;
    DB = [];
    saveDB(DB);
    applyFilters();
    closeDetails();
    closeModal();
  });

  // init
  applyFilters();
})();
