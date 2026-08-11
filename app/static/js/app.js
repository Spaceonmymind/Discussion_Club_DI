const DiscussionClub = (() => {
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

    function isOptInQuestion(question) {
        return question.text.includes('пилоте агента "Импульс"');
    }

    function questionCard(question, mode, participantId) {
        const meta = mode === "moderator"
            ? `<span>${escapeHtml(participantName(question))}</span>`
            : "<span>ваш вопрос</span>";
        return `
            <article class="question-card" data-question-id="${question.id}">
                <div class="question-meta">${meta}</div>
                <p class="question-text">${escapeHtml(question.text)}</p>
            </article>
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

    function initParticipant() {
        const root = document.querySelector(".discussion-grid");
        if (!root) return;
        const eventId = root.dataset.eventId;
        const participantId = root.dataset.participantId;
        const preparedBox = document.querySelector("#preparedQuestions");
        const liveBox = document.querySelector("#liveQuestions");
        const notice = document.querySelector("#questionNotice");

        async function loadPrepared() {
            const questions = await jsonFetch(`/api/events/${eventId}/prepared-questions?participant_id=${participantId}`);
            preparedBox.innerHTML = questions.map((question) => {
                const answerText = question.answer_text || "";
                const input = isOptInQuestion(question)
                    ? `<label class="check opt-in-check">
                            <input type="checkbox" data-answer-check="${question.id}" ${answerText === "Да" ? "checked" : ""}>
                            <span>Да, хочу принять участие</span>
                        </label>`
                    : `<textarea rows="3" data-answer-text="${question.id}" placeholder="Короткий ответ">${escapeHtml(answerText)}</textarea>`;
                const buttonText = answerText ? "Сохранить ответ" : "Отправить ответ";
                return `
                    <article class="question-card">
                        <p class="question-text">${escapeHtml(question.text)}</p>
                        ${question.description ? `<p class="muted">${escapeHtml(question.description)}</p>` : ""}
                        ${input}
                        <div class="answer-actions">
                            <p class="notice" data-answer-notice="${question.id}">${answerText ? "Ответ сохранён" : ""}</p>
                            <button class="btn secondary" data-answer="${question.id}" type="button">${buttonText}</button>
                        </div>
                    </article>
                `;
            }).join("") || "<p class='muted'>Фокус-вопросов пока нет.</p>";
        }

        async function loadLive() {
            const questions = await jsonFetch(`/api/events/${eventId}/live-questions?participant_id=${participantId}`);
            liveBox.innerHTML = questions.map((question) => questionCard(question, "participant", participantId)).join("")
                || "<p class='muted'>Вы пока не задавали вопросов.</p>";
        }

        document.querySelector("#sendLiveQuestion").addEventListener("click", async () => {
            const input = document.querySelector("#liveQuestionText");
            try {
                await jsonFetch(`/api/events/${eventId}/live-questions`, {
                    method: "POST",
                    body: JSON.stringify({ participant_id: Number(participantId), text: input.value }),
                });
                input.value = "";
                notice.textContent = "Вопрос сохранён. Его увидит модератор.";
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
                const checkbox = document.querySelector(`[data-answer-check="${questionId}"]`);
                const answerNotice = document.querySelector(`[data-answer-notice="${questionId}"]`);
                const answerText = checkbox ? (checkbox.checked ? "Да" : "Нет") : textarea.value;
                try {
                    await jsonFetch(`/api/prepared-questions/${questionId}/answers`, {
                        method: "POST",
                        body: JSON.stringify({ participant_id: Number(participantId), answer_text: answerText }),
                    });
                    answerNotice.textContent = "Ответ сохранён";
                    answerButton.textContent = "Сохранить ответ";
                } catch (error) {
                    answerNotice.textContent = error.message;
                }
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
            const list = document.querySelector("#moderatorLiveQuestions");
            const count = document.querySelector("#moderatorLiveCount");
            count.textContent = questions.length;
            list.innerHTML = questions.map((question) => questionCard(question, "moderator")).join("")
                || "<p class='muted'>Вопросов пока нет.</p>";
        }

        loadModeration();
        setInterval(loadModeration, 5000);
    }

    return { initParticipant, initModerator };
})();
