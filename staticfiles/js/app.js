(function () {
  console.log("Quiz JS Loaded");

  const onReady = (callback) => {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, { once: true });
    } else {
      callback();
    }
  };

  const csrf = () => document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const safeLocalGet = (key) => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  };

  const safeLocalSet = (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch {}
  };

  const safeLocalRemove = (key) => {
    try {
      localStorage.removeItem(key);
    } catch {}
  };

  const safeSessionGet = (key) => {
    try {
      return sessionStorage.getItem(key);
    } catch {
      return null;
    }
  };

  const safeSessionSet = (key, value) => {
    try {
      sessionStorage.setItem(key, value);
    } catch {}
  };

  const safeSessionRemove = (key) => {
    try {
      sessionStorage.removeItem(key);
    } catch {}
  };

  const notify = (message, type = "info") => {
    const center = document.getElementById("toastCenter");
    if (!center) return;
    const toast = document.createElement("div");
    toast.className = `app-toast ${type}`;
    toast.innerHTML = `<span>${message}</span><button type="button" aria-label="Dismiss">&times;</button>`;
    center.appendChild(toast);
    toast.querySelector("button").addEventListener("click", () => toast.remove());
    window.setTimeout(() => toast.remove(), 4200);
  };
  window.quizNotify = notify;

  const run = (name, callback) => {
    try {
      callback();
    } catch (err) {
      console.error(`${name} failed`, err);
    }
  };

  function initTheme() {
    const themeToggle = document.getElementById("themeToggle");
    console.log("Theme Toggle Found", themeToggle);

    const systemPrefersDark = () => window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const resolveTheme = (preference) => preference === "system" ? (systemPrefersDark() ? "dark" : "light") : preference;
    const applyTheme = (preference, persist = true) => {
      const resolved = resolveTheme(preference);
      document.documentElement.dataset.themePreference = preference;
      document.documentElement.dataset.theme = resolved;
      if (persist) safeLocalSet("quizlearn-theme", preference);
      if (themeToggle) themeToggle.title = `Theme: ${preference}`;
      console.log("Theme Applied", { preference, resolved });
    };

    const initialTheme = safeLocalGet("quizlearn-theme") || document.documentElement.dataset.themePreference || "system";
    applyTheme(initialTheme, false);

    if (themeToggle) {
      themeToggle.addEventListener("click", async () => {
        const current = document.documentElement.dataset.themePreference || "system";
        const next = current === "system" ? "light" : current === "light" ? "dark" : "system";
        applyTheme(next);
        notify(`Theme set to ${next}`, "info");
        if (themeToggle.dataset.saveUrl) {
          const body = new URLSearchParams({ theme: next });
          await fetch(themeToggle.dataset.saveUrl, { method: "POST", headers: { "X-CSRFToken": csrf() }, body }).catch(console.error);
        }
      });
    }

    window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if ((document.documentElement.dataset.themePreference || "system") === "system") applyTheme("system", false);
    });
  }

  function initFormStyling() {
    $$("input, textarea, select").forEach((el) => {
      if (!el.classList.contains("form-check-input")) el.classList.add("form-control");
      if (el.type === "checkbox" || el.type === "radio") el.classList.remove("form-control");
    });
  }

  function initAi() {
    const addBubble = (messages, text, role, typing = false) => {
      if (!messages) return null;
      const div = document.createElement("div");
      div.className = `ai-bubble ${role === "user" ? "ai-user" : "ai-bot"}${typing ? " typing" : ""}`;
      div.textContent = typing ? "Typing..." : text;
      messages.appendChild(div);
      messages.scrollTop = messages.scrollHeight;
      return div;
    };

    const saveChatHistory = (key, messages) => {
      if (!messages) return;
      const items = $$(".ai-bubble:not(.typing)", messages).map((node) => ({
        role: node.classList.contains("ai-user") ? "user" : "bot",
        text: node.textContent,
      })).slice(-30);
      safeSessionSet(key, JSON.stringify(items));
    };

    const restoreChatHistory = (key, messages) => {
      if (!messages || messages.dataset.restored) return;
      const raw = safeSessionGet(key);
      if (!raw) return;
      messages.dataset.restored = "1";
      try {
        JSON.parse(raw).forEach((item) => addBubble(messages, item.text, item.role));
      } catch {
        safeSessionRemove(key);
      }
    };

    const wireAiForm = (formId, inputId, messagesId, context) => {
      const form = document.getElementById(formId);
      const input = document.getElementById(inputId);
      const messages = document.getElementById(messagesId);
      if (!form || !input || !messages) return;
      const historyKey = `quizlearn-chat-${messagesId}`;
      restoreChatHistory(historyKey, messages);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const text = input.value.trim();
        if (!text) return;
        addBubble(messages, text, "user");
        saveChatHistory(historyKey, messages);
        input.value = "";
        const typing = addBubble(messages, "", "bot", true);
        try {
          const res = await fetch(form.dataset.endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
            body: JSON.stringify({ message: text, context }),
          });
          const data = await res.json();
          typing.remove();
          addBubble(messages, data.response || "I could not answer that yet.", "bot");
          saveChatHistory(historyKey, messages);
          notify("AI assistant reply received", "success");
        } catch {
          typing.remove();
          addBubble(messages, "Support is temporarily unavailable. Please try again soon.", "bot");
          saveChatHistory(historyKey, messages);
          notify("AI assistant could not reply", "error");
        }
      });
    };

    const launcher = document.getElementById("aiLauncher");
    const panel = document.getElementById("aiPanel");
    const close = document.getElementById("aiClose");
    const globalInput = document.getElementById("aiInput");
    const openAi = (seed) => {
      panel?.classList.add("open");
      if (seed && globalInput) globalInput.value = seed;
      globalInput?.focus();
    };

    launcher?.addEventListener("click", () => openAi());
    close?.addEventListener("click", () => panel?.classList.remove("open"));
    window.addEventListener("open-ai", (event) => openAi(event.detail));
    wireAiForm("aiForm", "aiInput", "aiMessages", document.body.dataset.aiContext || "general");
    wireAiForm("contactAiForm", "contactAiInput", "contactAiMessages", "contact_support");
  }

  function initPageNotifications() {
    const pageNotify = $("[data-page-notify]");
    if (pageNotify) notify(pageNotify.dataset.pageNotify, pageNotify.dataset.pageNotifyType || "info");
  }

  function initCharts() {
    const chartEl = document.getElementById("performanceChart");
    if (chartEl && window.Chart) {
      const labels = chartEl.dataset.labels ? chartEl.dataset.labels.split(",") : [];
      const values = chartEl.dataset.values ? chartEl.dataset.values.split(",").map(Number) : [];
      new Chart(chartEl, {
        type: "line",
        data: { labels, datasets: [{ label: "Score %", data: values, borderColor: "#3b82f6", backgroundColor: "rgba(59,130,246,.18)", tension: .35, fill: true }] },
        options: { responsive: true, scales: { y: { min: 0, max: 100 } } },
      });
    }

    const pieEl = document.getElementById("resultPie");
    if (pieEl && window.Chart) {
      const values = pieEl.dataset.values ? pieEl.dataset.values.split(",").map(Number) : [0, 0, 0];
      new Chart(pieEl, {
        type: "doughnut",
        data: { labels: ["Correct", "Incorrect", "Unanswered"], datasets: [{ data: values, backgroundColor: ["#22c55e", "#ef4444", "#64748b"], borderWidth: 0 }] },
      });
    }
  }

  function initQuiz() {
    const shell = document.querySelector(".quiz-shell");
    console.log("Quiz Shell Found", shell);
    if (!shell) return;

    console.log(shell.dataset.endsAt);

    const cards = $$(".question-card");
    const palette = $$(".palette-btn");
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");
    const submitBtn = document.getElementById("submitBtn");
    const bar = document.getElementById("quizProgress");
    const form = document.getElementById("quizForm");
    const timer = document.getElementById("timer");
    const timerBox = document.getElementById("timerBox");
    const questionProgressText = document.getElementById("questionProgressText");
    const progressPercent = document.getElementById("progressPercent");

    console.log("Next Button Found", nextBtn);
    console.log("Prev Button Found", prevBtn);
    console.log("Palette Buttons Found", palette.length);

    if (!cards.length || !form) return;

    const total = cards.length;
    const visited = new Set([0]);
    const warned = new Set();
    const attemptId = shell.dataset.attempt || "unknown";
    const timerKey = `quizlearn-attempt-${attemptId}-timer-end`;
    const visitedKey = `quizlearn-attempt-${attemptId}-visited`;
    let index = 0;
    let submitting = false;
    let timerId = null;

    cards.forEach((card, i) => {
      if ($("input:checked", card)) visited.add(i);
    });

    try {
      JSON.parse(safeSessionGet(visitedKey) || "[]").forEach((value) => {
        const parsed = Number(value);
        if (Number.isInteger(parsed) && parsed >= 0 && parsed < total) visited.add(parsed);
      });
    } catch {
      safeSessionRemove(visitedKey);
    }

    const answeredIndexes = () => new Set(cards.map((card, i) => $("input:checked", card) ? i : null).filter((value) => value !== null));
    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };
    const persistVisited = () => safeSessionSet(visitedKey, JSON.stringify(Array.from(visited)));

    const updateStatus = () => {
      const answered = answeredIndexes();
      setText("attemptedCount", answered.size);
      setText("notAttemptedCount", total - answered.size);
      setText("visitedCount", visited.size);
      setText("notVisitedCount", total - visited.size);
      palette.forEach((btn, i) => {
        btn.className = "palette-btn";
        if (i === index) btn.classList.add("current");
        else if (answered.has(i)) btn.classList.add("attempted");
        else if (visited.has(i)) btn.classList.add("visited");
        else btn.classList.add("not-visited");
        btn.setAttribute("aria-current", i === index ? "step" : "false");
      });
    };

    const show = (nextIndex, skipped = false) => {
      index = Math.max(0, Math.min(total - 1, nextIndex));
      visited.add(index);
      persistVisited();
      cards.forEach((card, i) => card.classList.toggle("d-none", i !== index));
      if (prevBtn) prevBtn.disabled = index === 0;
      if (nextBtn) nextBtn.disabled = index === total - 1;
      const percent = Math.round(((index + 1) / total) * 100);
      if (bar) bar.style.width = `${percent}%`;
      if (questionProgressText) questionProgressText.textContent = `Question ${index + 1} of ${total}`;
      if (progressPercent) progressPercent.textContent = `${percent}%`;
      updateStatus();
      if (skipped) notify("Question skipped", "warning");
    };
    window.show = show;

    const saveAnswerForCard = async (card) => {
      const selected = $("input:checked", card);
      if (!selected) return true;
      const body = new URLSearchParams({ question_id: selected.dataset.question, choice_id: selected.value });
      try {
        const res = await fetch(shell.dataset.saveUrl, { method: "POST", headers: { "X-CSRFToken": csrf() }, body });
        if (res.status === 409) submitQuiz();
        return res.ok;
      } catch {
        notify("Answer is kept on this page and will be saved on submit.", "warning");
        return false;
      }
    };

    const submitQuiz = () => {
      if (!form || submitting) return;
      submitting = true;
      safeLocalRemove(timerKey);
      safeSessionRemove(visitedKey);
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
      }
      if (form.requestSubmit) form.requestSubmit();
      else form.submit();
    };

    prevBtn?.addEventListener("click", (event) => {
      event.preventDefault();
      const currentCard = cards[index];
      show(index - 1);
      saveAnswerForCard(currentCard);
    });

    nextBtn?.addEventListener("click", (event) => {
      event.preventDefault();
      if (index >= total - 1) return;
      const currentCard = cards[index];
      const skipped = !$("input:checked", currentCard);
      show(index + 1, skipped);
      saveAnswerForCard(currentCard);
    });

    palette.forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        const currentCard = cards[index];
        show(Number(btn.dataset.index));
        saveAnswerForCard(currentCard);
      });
    });

    $$(".choice input").forEach((radio) => {
      radio.addEventListener("change", async () => {
        updateStatus();
        const body = new URLSearchParams({ question_id: radio.dataset.question, choice_id: radio.value });
        try {
          const res = await fetch(shell.dataset.saveUrl, { method: "POST", headers: { "X-CSRFToken": csrf() }, body });
          if (res.status === 409) submitQuiz();
          else if (res.ok) notify("Answer saved", "success");
        } catch {
          notify("Answer could not be saved", "error");
        }
      });
    });

    form.addEventListener("submit", () => {
      if (submitting) return;
      submitting = true;
      safeLocalRemove(timerKey);
      safeSessionRemove(visitedKey);
      notify("Quiz submitted", "success");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
      }
    });

    const formatTime = (seconds) => {
      const h = String(Math.floor(seconds / 3600)).padStart(2, "0");
      const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
      const s = String(seconds % 60).padStart(2, "0");
      return `${h}:${m}:${s}`;
    };

    const parseEndTime = () => {
      const parsedEnd = Date.parse(shell.dataset.endsAt || "");
      const serverEnd = Number.isFinite(parsedEnd) ? parsedEnd : 0;
      const remaining = Number(shell.dataset.remainingSeconds || 0);
      const fallbackEnd = remaining > 0 ? Date.now() + remaining * 1000 : 0;
      const storedEnd = Number(safeLocalGet(timerKey) || 0);
      if (storedEnd > Date.now() && serverEnd > Date.now()) return Math.min(storedEnd, serverEnd);
      if (serverEnd > Date.now()) return serverEnd;
      return fallbackEnd;
    };

    const end = parseEndTime();
    if (!end) {
      console.error("Quiz timer could not parse endsAt", shell.dataset.endsAt);
      if (timer) timer.textContent = "00:00:00";
    } else {
      safeLocalSet(timerKey, String(end));
      const tick = () => {
        const left = Math.max(0, Math.floor((end - Date.now()) / 1000));
        if (timer) timer.textContent = formatTime(left);
        if (left <= 300 && !warned.has(300)) {
          warned.add(300);
          timerBox?.classList.add("warning");
          notify("Less than 5 minutes remaining", "warning");
        }
        if (left <= 60 && !warned.has(60)) {
          warned.add(60);
          notify("1 minute remaining", "warning");
        }
        if (left <= 30 && !warned.has(30)) {
          warned.add(30);
          timerBox?.classList.add("danger");
          notify("30 seconds remaining", "warning");
        }
        if (left <= 0 && !submitting) {
          notify("Time expired. Submitting quiz.", "error");
          window.clearInterval(timerId);
          submitQuiz();
        }
      };
      tick();
      timerId = window.setInterval(tick, 1000);
    }

    show(0);
  }

  onReady(() => {
    run("initTheme", initTheme);
    run("initFormStyling", initFormStyling);
    run("initAi", initAi);
    run("initPageNotifications", initPageNotifications);
    run("initCharts", initCharts);
    run("initQuiz", initQuiz);
  });
})();
