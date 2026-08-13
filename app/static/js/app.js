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

    function isOptInQuestion(question) {
        return question.text.includes('пилоте агента "Импульс"');
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

        async function loadPrepared() {
            const questions = await jsonFetch(`/api/events/${eventId}/prepared-questions?participant_id=${participantId}`);
            const cards = questions.map((question) => {
                const answerText = question.answer_text || "";
                const input = isOptInQuestion(question)
                    ? `<label class="check opt-in-check">
                            <input type="checkbox" data-answer-check="${question.id}" ${answerText === "Да" ? "checked" : ""}>
                            <span>Да, хочу принять участие</span>
                        </label>`
                    : `<textarea rows="3" data-answer-text="${question.id}" placeholder="Короткий ответ">${escapeHtml(answerText)}</textarea>`;
                return `
                    <article class="question-card">
                        <p class="question-text">${escapeHtml(question.text)}</p>
                        ${question.description ? `<p class="muted">${escapeHtml(question.description)}</p>` : ""}
                        ${input}
                    </article>
                `;
            }).join("");
            preparedBox.innerHTML = cards
                ? `${cards}
                    <div class="answer-actions">
                        <p class="notice" id="answersNotice"></p>
                        <button class="btn secondary" id="saveAllAnswers" type="button">Сохранить ответы</button>
                    </div>`
                : "<p class='muted'>Фокус-вопросов пока нет.</p>";
        }

        document.addEventListener("click", async (event) => {
            const saveButton = event.target.closest("#saveAllAnswers");
            if (saveButton) {
                const notice = document.querySelector("#answersNotice");
                const answerFields = [
                    ...document.querySelectorAll("[data-answer-text]"),
                    ...document.querySelectorAll("[data-answer-check]"),
                ];
                const answers = answerFields
                    .map((field) => ({
                        questionId: field.dataset.answerText || field.dataset.answerCheck,
                        answerText: field.matches("[data-answer-check]") ? (field.checked ? "Да" : "Нет") : field.value.trim(),
                    }))
                    .filter((answer) => answer.answerText);
                try {
                    saveButton.disabled = true;
                    await Promise.all(answers.map((answer) => jsonFetch(`/api/prepared-questions/${answer.questionId}/answers`, {
                        method: "POST",
                        body: JSON.stringify({ participant_id: Number(participantId), answer_text: answer.answerText }),
                    })));
                    notice.textContent = "Ответы сохранены";
                } catch (error) {
                    notice.textContent = error.message;
                } finally {
                    saveButton.disabled = false;
                }
            }
        });

        loadPrepared();
    }

    return { initParticipant };
})();
