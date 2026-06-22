const DiscussionClub = (() => {
    const statusLabels = {
        moderation: "на модерации",
        approved: "одобрен",
        rejected: "отклонён",
        discussion: "в обсуждении",
        answered: "отвечен",
    };

    async function jsonFetch(url, options = {}) {
        const response = await fetch(url, {
            headers: { "Content-Type": "application/json", ...(options.headers || {}) },
            ...options,
        });
        if (!response.ok) {
            const detail = await response.json().catch(() => ({ detail: "Ошибка запроса" }));
            throw new Error(detail.detail || "Ошибка запроса");
        }
        return response.json();
    }

    function participantName(question) {
        return question.participant_name || "Участник";
    }

    function questionCard(question, mode, participantId) {
        const pinned = question.is_pinned ? " pinned" : "";
        const status = `<span class="status ${question.status}">${statusLabels[question.status] || question.status}</span>`;
        const pin = question.is_pinned ? "<span>закреплён</span>" : "";
        const voteButton = mode === "participant" && ["approved", "discussion"].includes(question.status)
            ? `<button class="btn secondary" data-vote="${question.id}" type="button">Поддержать · ${question.votes_count}</button>`
            : `<span>голосов: ${question.votes_count}</span>`;
        const owner = Number(question.participant_id) === Number(participantId) ? "<span>ваш вопрос</span>" : "";
        const moderationActions = mode === "moderator" ? moderatorActions(question) : "";
        const comment = question.moderator_comment ? `<p class="muted">Комментарий: ${escapeHtml(question.moderator_comment)}</p>` : "";
        return `
            <article class="question-card${pinned}" data-question-id="${question.id}">
                <div class="question-meta">${status}${pin}<span>${escapeHtml(participantName(question))}</span>${owner}</div>
                <p class="question-text">${escapeHtml(question.text)}</p>
                ${comment}
                <div class="question-actions">${voteButton}${moderationActions}</div>
            </article>
        `;
    }

    function moderatorActions(question) {
        return `
            <button class="btn secondary" data-status="${question.id}:approved" type="button">Одобрить</button>
            <button class="btn secondary" data-status="${question.id}:discussion" type="button">В обсуждение</button>
            <button class="btn secondary" data-status="${question.id}:answered" type="button">Отвечен</button>
            <button class="btn danger" data-status="${question.id}:rejected" type="button">Отклонить</button>
            <button class="btn ghost" data-pin="${question.id}:${!question.is_pinned}" type="button">${question.is_pinned ? "Открепить" : "Закрепить"}</button>
            <input class="comment-input" data-comment-input="${question.id}" value="${escapeAttr(question.moderator_comment || "")}" placeholder="Комментарий">
            <button class="btn ghost" data-comment="${question.id}" type="button">Сохранить</button>
        `;
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, (char) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
        }[char]));
    }

    function escapeAttr(value) {
        return escapeHtml(value).replace(/`/g, "&#96;");
    }

    function initParticipant() {
        const root = document.querySelector(".discussion-grid");
        if (!root) return;
        const eventId = root.dataset.eventId;
        const participantId = root.dataset.participantId;
        const preparedBox = document.querySelector("#preparedQuestions");
        const liveBox = document.querySelector("#liveQuestions");
        const notice = document.querySelector("#questionNotice");

        async function loadPrepared() {
            const questions = await jsonFetch(`/api/events/${eventId}/prepared-questions`);
            preparedBox.innerHTML = questions.map((question) => `
                <article class="question-card">
                    <p class="question-text">${escapeHtml(question.text)}</p>
                    ${question.description ? `<p class="muted">${escapeHtml(question.description)}</p>` : ""}
                    <textarea rows="3" data-answer-text="${question.id}" placeholder="Ваш ответ"></textarea>
                    <div class="row between">
                        <p class="notice" data-answer-notice="${question.id}"></p>
                        <button class="btn secondary" data-answer="${question.id}" type="button">Отправить ответ</button>
                    </div>
                </article>
            `).join("") || "<p class='muted'>Подготовленных вопросов пока нет.</p>";
        }

        async function loadLive() {
            const questions = await jsonFetch(`/api/events/${eventId}/live-questions?participant_id=${participantId}`);
            liveBox.innerHTML = questions.map((question) => questionCard(question, "participant", participantId)).join("")
                || "<p class='muted'>Пока нет одобренных вопросов.</p>";
        }

        document.querySelector("#sendLiveQuestion").addEventListener("click", async () => {
            const input = document.querySelector("#liveQuestionText");
            try {
                await jsonFetch(`/api/events/${eventId}/live-questions`, {
                    method: "POST",
                    body: JSON.stringify({ participant_id: Number(participantId), text: input.value }),
                });
                input.value = "";
                notice.textContent = "Вопрос отправлен на модерацию";
                await loadLive();
            } catch (error) {
                notice.textContent = error.message;
            }
        });

        document.addEventListener("click", async (event) => {
            const answerButton = event.target.closest("[data-answer]");
            if (answerButton) {
                const questionId = answerButton.dataset.answer;
                const textarea = document.querySelector(`[data-answer-text="${questionId}"]`);
                const answerNotice = document.querySelector(`[data-answer-notice="${questionId}"]`);
                try {
                    await jsonFetch(`/api/prepared-questions/${questionId}/answers`, {
                        method: "POST",
                        body: JSON.stringify({ participant_id: Number(participantId), answer_text: textarea.value }),
                    });
                    textarea.value = "";
                    answerNotice.textContent = "Ответ отправлен";
                } catch (error) {
                    answerNotice.textContent = error.message;
                }
            }
            const voteButton = event.target.closest("[data-vote]");
            if (voteButton) {
                await jsonFetch(`/api/live-questions/${voteButton.dataset.vote}/vote?participant_id=${participantId}`, { method: "POST" });
                await loadLive();
            }
        });

        loadPrepared();
        loadLive();
        setInterval(loadLive, 5000);
    }

    function initModerator() {
        const root = document.querySelector(".moderator-layout");
        if (!root) return;
        const eventId = root.dataset.eventId;

        async function loadModeration() {
            const questions = await jsonFetch(`/api/events/${eventId}/moderation/live-questions`);
            const grouped = { moderation: [], approved: [], discussion: [], answered: [], rejected: [] };
            questions.forEach((question) => grouped[question.status]?.push(question));
            Object.entries(grouped).forEach(([status, items]) => {
                const list = document.querySelector(`[data-moderation-list="${status}"]`);
                const count = document.querySelector(`[data-count="${status}"]`);
                count.textContent = items.length;
                list.innerHTML = items.map((question) => questionCard(question, "moderator")).join("")
                    || "<p class='muted'>Нет вопросов.</p>";
            });
        }

        document.addEventListener("click", async (event) => {
            const statusButton = event.target.closest("[data-status]");
            if (statusButton) {
                const [id, status] = statusButton.dataset.status.split(":");
                await jsonFetch(`/api/live-questions/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
                await loadModeration();
            }
            const pinButton = event.target.closest("[data-pin]");
            if (pinButton) {
                const [id, isPinned] = pinButton.dataset.pin.split(":");
                await jsonFetch(`/api/live-questions/${id}/pin`, { method: "PATCH", body: JSON.stringify({ is_pinned: isPinned === "true" }) });
                await loadModeration();
            }
            const commentButton = event.target.closest("[data-comment]");
            if (commentButton) {
                const id = commentButton.dataset.comment;
                const input = document.querySelector(`[data-comment-input="${id}"]`);
                await jsonFetch(`/api/live-questions/${id}/comment`, { method: "PATCH", body: JSON.stringify({ moderator_comment: input.value }) });
                await loadModeration();
            }
        });

        loadModeration();
        setInterval(loadModeration, 5000);
    }

    return { initParticipant, initModerator };
})();
