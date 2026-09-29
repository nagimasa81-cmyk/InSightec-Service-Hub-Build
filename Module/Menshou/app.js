(() => {
  "use strict";

  const STORAGE_KEY = "menshou_hanten_people_v1";

  /** @typedef {{id:string, name:string, total:number, history:{date:string, amount:number}[]}} Person */

  /** @type {Person[]} */
  let people = [];

  // ---------- 永続化 ----------
  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      people = raw ? JSON.parse(raw) : [];
    } catch (e) {
      console.error("読み込みに失敗しました", e);
      people = [];
    }
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(people));
  }

  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  // ---------- フォーマット ----------
  function formatYen(amount) {
    const sign = amount > 0 ? "+" : amount < 0 ? "\u2212" : "";
    return `${sign}${Math.abs(amount).toLocaleString("ja-JP")}円`;
  }

  function toneClass(amount) {
    if (amount > 0) return "plus";
    if (amount < 0) return "minus";
    return "zero";
  }

  function formatDate(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString("ja-JP", { year: "numeric", month: "2-digit", day: "2-digit" }) +
      " " + d.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
  }

  // ---------- 要素参照 ----------
  const personListEl = document.getElementById("personList");
  const emptyStateEl = document.getElementById("emptyState");
  const updateBtn = document.getElementById("updateBtn");
  const addForm = document.getElementById("addForm");
  const addNameInput = document.getElementById("addNameInput");
  const historyOverlay = document.getElementById("historyOverlay");
  const historyTitle = document.getElementById("historyTitle");
  const historyList = document.getElementById("historyList");
  const historyEmpty = document.getElementById("historyEmpty");
  const historyClose = document.getElementById("historyClose");
  const toastEl = document.getElementById("toast");

  let toastTimer = null;
  function showToast(message) {
    toastEl.textContent = message;
    toastEl.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toastEl.hidden = true; }, 2200);
  }

  // ---------- 一覧描画 ----------
  function render() {
    personListEl.innerHTML = "";

    if (people.length === 0) {
      emptyStateEl.hidden = false;
      return;
    }
    emptyStateEl.hidden = true;

    for (const person of people) {
      personListEl.appendChild(renderRow(person));
    }
  }

  function renderRow(person) {
    const li = document.createElement("li");
    li.className = "person-row";
    li.dataset.id = person.id;

    // チェックボックス
    const chkWrap = document.createElement("label");
    chkWrap.className = "chk";
    const chk = document.createElement("input");
    chk.type = "checkbox";
    chk.setAttribute("aria-label", `${person.name}を更新対象にする`);
    chkWrap.appendChild(chk);

    // 名前（タップで履歴表示）
    const nameBtn = document.createElement("button");
    nameBtn.type = "button";
    nameBtn.className = "person-name";
    nameBtn.textContent = person.name;
    nameBtn.addEventListener("click", () => openHistory(person.id));

    // 合計金額
    const totalEl = document.createElement("span");
    totalEl.className = `person-total ${toneClass(person.total)}`;
    totalEl.textContent = formatYen(person.total);

    // 入力欄（チェック時のみ有効）
    const inputWrap = document.createElement("div");
    inputWrap.className = "person-input-wrap";
    const input = document.createElement("input");
    input.type = "number";
    input.inputMode = "decimal";
    input.className = "person-input";
    input.placeholder = "±金額を入力";
    input.disabled = true;
    input.setAttribute("aria-label", `${person.name}の増減金額`);

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "person-delete";
    delBtn.setAttribute("aria-label", `${person.name}を削除`);
    delBtn.textContent = "\u00d7";
    delBtn.addEventListener("click", () => deletePerson(person.id, person.name));

    inputWrap.appendChild(input);
    inputWrap.appendChild(delBtn);

    chk.addEventListener("change", () => {
      input.disabled = !chk.checked;
      li.classList.toggle("is-checked", chk.checked);
      if (chk.checked) {
        input.focus();
      } else {
        input.value = "";
      }
    });

    li.appendChild(chkWrap);
    li.appendChild(nameBtn);
    li.appendChild(totalEl);
    li.appendChild(inputWrap);

    return li;
  }

  // ---------- 更新処理 ----------
  function handleUpdate() {
    const rows = personListEl.querySelectorAll(".person-row");
    let appliedCount = 0;
    const now = new Date().toISOString();

    rows.forEach((row) => {
      const chk = row.querySelector('input[type="checkbox"]');
      const input = row.querySelector(".person-input");
      if (!chk.checked) return;

      const amount = parseFloat(input.value);
      if (!Number.isFinite(amount) || amount === 0) return;

      const person = people.find((p) => p.id === row.dataset.id);
      if (!person) return;

      person.total += amount;
      person.history.push({ date: now, amount });
      appliedCount += 1;
    });

    if (appliedCount === 0) {
      showToast("反映できる金額がありません");
      return;
    }

    // 履歴は新しい順に保持
    people.forEach((p) => p.history.sort((a, b) => new Date(b.date) - new Date(a.date)));

    save();
    render();
    showToast(`${appliedCount}件を更新しました`);
  }

  // ---------- 履歴モーダル ----------
  let currentHistoryPersonId = null;

  function openHistory(personId) {
    const person = people.find((p) => p.id === personId);
    if (!person) return;

    currentHistoryPersonId = personId;
    historyTitle.textContent = `${person.name} の履歴`;
    historyList.innerHTML = "";

    if (person.history.length === 0) {
      historyEmpty.hidden = false;
    } else {
      historyEmpty.hidden = true;
      for (const entry of person.history) {
        const li = document.createElement("li");
        li.className = "history-row";

        const dateEl = document.createElement("span");
        dateEl.className = "history-date";
        dateEl.textContent = formatDate(entry.date);

        const amountEl = document.createElement("span");
        amountEl.className = `history-amount ${toneClass(entry.amount)}`;
        amountEl.textContent = formatYen(entry.amount);

        li.appendChild(dateEl);
        li.appendChild(amountEl);
        historyList.appendChild(li);
      }
    }

    historyOverlay.hidden = false;
  }

  function closeHistory() {
    historyOverlay.hidden = true;
    currentHistoryPersonId = null;
  }

  historyClose.addEventListener("click", closeHistory);
  historyOverlay.addEventListener("click", (e) => {
    if (e.target === historyOverlay) closeHistory();
  });

  // ---------- 追加・削除 ----------
  addForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const name = addNameInput.value.trim();
    if (!name) return;

    people.push({ id: uid(), name, total: 0, history: [] });
    save();
    render();
    addNameInput.value = "";
    showToast(`「${name}」を追加しました`);
  });

  function deletePerson(id, name) {
    const ok = window.confirm(`「${name}」を削除しますか？履歴も削除されます。`);
    if (!ok) return;
    people = people.filter((p) => p.id !== id);
    save();
    render();
    showToast(`「${name}」を削除しました`);
  }

  // ---------- 初期化 ----------
  updateBtn.addEventListener("click", handleUpdate);
  load();
  render();

  // ---------- Service Worker 登録（オフライン対応） ----------
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("sw.js").catch((e) => {
        console.warn("Service Worker登録に失敗しました", e);
      });
    });
  }
})();
