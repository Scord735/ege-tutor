document.addEventListener('DOMContentLoaded', () => {

    // ============================================================
    // 0. ГЛИТЧ-ПЕРЕХОД (ПЕРВЫМ, ЧТОБЫ РАБОТАЛ ВЕЗДЕ)
    // ============================================================
    let glitchOverlay = document.getElementById('glitchOverlay');
    if (!glitchOverlay) {
        glitchOverlay = document.createElement('div');
        glitchOverlay.id = 'glitchOverlay';
        document.body.appendChild(glitchOverlay);
    }

    document.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        if (!link) return;
        const href = link.getAttribute('href');
        if (!href) return;
        if (
            href.startsWith('#') ||
            href.startsWith('mailto:') ||
            href.startsWith('http') ||
            href.startsWith('javascript:')
        ) return;
        if (link.classList.contains('active')) {
            e.preventDefault();
            return;
        }
        e.preventDefault();
        if (glitchOverlay.classList.contains('active')) return;
        glitchOverlay.classList.add('active');
        document.body.classList.add('glitching');
        setTimeout(() => { window.location.href = href; }, 550);
    });

    window.addEventListener('pageshow', () => {
        glitchOverlay.classList.remove('active');
        document.body.classList.remove('glitching');
    });

    // ============================================================
    // 1. АВТО-ПОДСВЕТКА АКТИВНОГО ПУНКТА МЕНЮ
    // ============================================================
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav a').forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPage) link.classList.add('active');
    });

    // ============================================================
    // 2. ЭФФЕКТ ПЕЧАТАЮЩЕГОСЯ ТЕКСТА
    // ============================================================
    function typeText(element, text, speed = 25) {
        element.innerHTML = '';
        const cursor = document.createElement('span');
        cursor.className = 'cursor';
        element.appendChild(cursor);
        let i = 0;
        const timer = setInterval(() => {
            if (i < text.length) {
                cursor.insertAdjacentText('beforebegin', text[i]);
                i++;
            } else clearInterval(timer);
        }, speed);
    }
    document.querySelectorAll('[data-type]').forEach(el => {
        const text = el.textContent.trim();
        const delay = parseInt(el.dataset.delay || '0', 10);
        setTimeout(() => typeText(el, text), delay);
    });

    // ============================================================
    // 3. КНОПКА «ПРОВЕРИТЬ СВЯЗЬ» (главная)
    // ============================================================
    const button = document.getElementById('checkBtn');
    const message = document.getElementById('message');
    if (button && message) {
        button.addEventListener('click', () => {
            button.disabled = true;
            button.textContent = 'OK';
            typeText(message, 'JavaScript работает. Переходи по меню — все страницы уже готовы.', 20);
        });
    }

    // ============================================================
    // 4. ЛОГ В КОНСОЛЬ
    // ============================================================
    console.log('%c>> EGE-TUTOR v1.0 // MATRIX MODE', 'color:#00ff66;font-family:monospace;font-size:14px');
    console.log('%c>> текущая страница: ' + currentPage, 'color:#00cc52;font-family:monospace');

    // ============================================================
    // 5. КНОПКА «ПРОВЕРИТЬ СЕРВЕР» (профиль)
    // ============================================================
    const pingBtn = document.getElementById('pingServerBtn');
    const serverResponse = document.getElementById('serverResponse');
    if (pingBtn && serverResponse) {
        pingBtn.addEventListener('click', async () => {
            pingBtn.disabled = true;
            pingBtn.textContent = '...';
            serverResponse.classList.remove('error', 'visible');
            serverResponse.textContent = '';
            const result = await API.health();
            if (result.ok) {
                serverResponse.classList.add('visible');
                serverResponse.textContent = '> HTTP ' + result.status + '\n> ' + JSON.stringify(result.data, null, 2);
                pingBtn.textContent = 'OK';
            } else {
                serverResponse.classList.add('visible', 'error');
                serverResponse.textContent = '> ОШИБКА\n> ' + JSON.stringify(result.error, null, 2);
                pingBtn.disabled = false;
                pingBtn.textContent = 'Повторить';
            }
        });
    }
           // === 6. ПРОФИЛЬ — прогресс по предметам ===
    const totalProgressEl = document.getElementById('totalProgress');
    const subjectProgressEl = document.getElementById('subjectProgress');
    const weakTopicsProfileEl = document.getElementById('weakTopicsProfile');

    if (totalProgressEl && subjectProgressEl) {
        (async () => {
            const result = await API.profileStats();
            if (!result.ok) {
                totalProgressEl.innerHTML = '<div class="placeholder" style="color:#ff3355;">[ ошибка — backend запущен? ]</div>';
                subjectProgressEl.innerHTML = '';
                return;
            }

            const d = result.data;

            // === ОБЩИЙ ПРОГРЕСС ===
            totalProgressEl.innerHTML =
                '<div class="profile-total">' +
                    '<div class="profile-total-num">' +
                        d.total_done + '<span>/' + d.total_topics + '</span>' +
                    '</div>' +
                    '<div class="profile-total-label">тем пройдено</div>' +
                    '<div class="profile-total-percent">' + d.total_percent + '%</div>' +
                '</div>' +
                '<div class="profile-bar profile-bar-big">' +
                    '<i style="width:' + d.total_percent + '%"></i>' +
                '</div>' +
                '<div class="profile-mini-stats">' +
                    '<div class="profile-mini">' +
                        '<span class="profile-mini-num">' + d.total_attempts + '</span>' +
                        '<span class="profile-mini-label">попыток</span>' +
                    '</div>' +
                    '<div class="profile-mini">' +
                        '<span class="profile-mini-num">' + d.total_errors + '</span>' +
                        '<span class="profile-mini-label">ошибок</span>' +
                    '</div>' +
                '</div>';

            // === ПРОГРЕСС ПО ПРЕДМЕТАМ ===
            const subjIcons = {
                math: '📐',
                phys: '⚛',
                rus: '📖',
                chem: '🧪',
            };

            let subjectsHtml = '<div class="subj-progress-list">';
            d.by_subject.forEach(s => {
                const icon = subjIcons[s.code] || '•';
                subjectsHtml +=
                    '<div class="subj-progress-item">' +
                        '<div class="subj-progress-head">' +
                            '<span class="subj-progress-icon">' + icon + '</span>' +
                            '<span class="subj-progress-name">' + escapeHtml(s.name) + '</span>' +
                            '<span class="subj-progress-count">' + s.done + ' / ' + s.total + '</span>' +
                            '<span class="subj-progress-percent">' + s.percent + '%</span>' +
                        '</div>' +
                        '<div class="profile-bar">' +
                            '<i style="width:' + s.percent + '%"></i>' +
                        '</div>' +
                        '<div class="subj-progress-meta">' +
                            'попыток: ' + s.attempts + ' · ошибок: ' + s.errors +
                        '</div>' +
                    '</div>';
            });
            subjectsHtml += '</div>';
            subjectProgressEl.innerHTML = subjectsHtml;

            // === СЛАБЫЕ ТЕМЫ ===
            if (weakTopicsProfileEl) {
                if (!d.weak_topics.length) {
                    weakTopicsProfileEl.innerHTML = '<div class="placeholder">[ появится после первых ошибок ]</div>';
                } else {
                    let html = '';
                    d.weak_topics.forEach(w => {
                        html +=
                            '<div class="weak-item">' +
                                '<div class="weak-top">' +
                                    '<span class="weak-name">' + escapeHtml(w.topic) + '</span>' +
                                    '<span class="weak-count">' + w.errors + ' ошиб.</span>' +
                                '</div>' +
                                '<div class="weak-where">' + escapeHtml(w.subject) + '</div>' +
                            '</div>';
                    });
                    weakTopicsProfileEl.innerHTML = html;
                }
            }
        })();
    }
    // ============================================================
    // 7. ПРОФИЛЬ УЧЕНИКА
    // ============================================================
    const viewMode = document.getElementById('viewMode');
    const editMode = document.getElementById('editMode');
    const editStudentBtn = document.getElementById('editStudentBtn');
    const saveStudentBtn = document.getElementById('saveStudentBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    const formMessage = document.getElementById('formMessage');
    const inputName = document.getElementById('inputName');
    const inputGrade = document.getElementById('inputGrade');
    const inputTarget = document.getElementById('inputTarget');
    const elName = document.getElementById('studentName');
    const elGrade = document.getElementById('studentGrade');
    const elTarget = document.getElementById('studentTarget');
    const elLevel = document.getElementById('studentLevel');
    const elCreated = document.getElementById('studentCreated');

    if (viewMode && editMode) {
        async function loadStudent() {
            const result = await API.getStudent();
            if (!result.ok) return;
            const student = result.data.student;
            if (!student) {
                elName.textContent = '—';
                elGrade.textContent = '—';
                elTarget.textContent = '—';
                elLevel.textContent = '0 / 100';
                elCreated.textContent = '—';
                return;
            }
            elName.textContent = student.name || '—';
            elGrade.textContent = student.grade ?? '—';
            elTarget.textContent = student.target_score ?? '—';
            elLevel.textContent = (student.current_level ?? 0) + ' / 100';
            elCreated.textContent = new Date(student.created_at).toLocaleDateString('ru-RU');
        }

        editStudentBtn.addEventListener('click', async () => {
            const result = await API.getStudent();
            const student = result.ok ? result.data.student : null;
            inputName.value = student?.name || '';
            inputGrade.value = student?.grade ?? '';
            inputTarget.value = student?.target_score ?? '';
            formMessage.classList.remove('visible', 'error');
            formMessage.textContent = '';
            viewMode.style.display = 'none';
            editMode.style.display = 'block';
        });

        cancelEditBtn.addEventListener('click', () => {
            viewMode.style.display = 'block';
            editMode.style.display = 'none';
        });

        saveStudentBtn.addEventListener('click', async () => {
            const name = inputName.value.trim();
            if (!name) {
                formMessage.classList.add('visible', 'error');
                formMessage.textContent = '> Имя не может быть пустым';
                return;
            }
            saveStudentBtn.disabled = true;
            saveStudentBtn.textContent = '...';
            const payload = {
                name: name,
                grade: inputGrade.value ? parseInt(inputGrade.value, 10) : null,
                target_score: inputTarget.value ? parseInt(inputTarget.value, 10) : null,
            };
            const result = await API.saveStudent(payload);
            if (result.ok) {
                await loadStudent();
                const statsResult = await API.stats();
                if (statsResult.ok) {
                    for (const key of ['students','subjects','topics','tasks','attempts','errors']) {
                        const el = document.getElementById('stat' + key[0].toUpperCase() + key.slice(1));
                        if (el) el.textContent = statsResult.data[key];
                    }
                }
                viewMode.style.display = 'block';
                editMode.style.display = 'none';
            } else {
                formMessage.classList.add('visible', 'error');
                formMessage.textContent = '> ОШИБКА: ' + JSON.stringify(result.error);
            }
            saveStudentBtn.disabled = false;
            saveStudentBtn.textContent = 'Сохранить';
        });

        loadStudent();
    }

    // ============================================================
    // 8. ДВУХПАНЕЛЬНЫЙ РЕЖИМ: ЗАДАНИЯ СЛЕВА, ТЕМЫ СПРАВА
    // ============================================================
    const sidebar = document.getElementById('subjectsSidebar');
    const topicPanel = document.getElementById('topicPanel');

    if (sidebar && topicPanel) {
        (async () => {
            const result = await API.subjects();
            if (!result.ok) {
                sidebar.innerHTML = '<div class="placeholder" style="color:#ff3355;">[ ошибка — backend запущен? ]</div>';
                return;
            }
            const subjects = result.data;
            if (!subjects.length) {
                sidebar.innerHTML = '<div class="placeholder">[ предметов нет ]</div>';
                return;
            }
            sidebar.innerHTML = '';

            const subjectHeaders = [];
            const subjectLists = [];

            subjects.forEach((subject) => {
                const subjectBlock = document.createElement('div');
                subjectBlock.className = 'sidebar-subject';

                const subjectHeader = document.createElement('div');
                subjectHeader.className = 'sidebar-subject-header';
                subjectHeader.innerHTML =
                    '<span class="chevron">▸</span>' +
                    '<span class="subject-name">' + escapeHtml(subject.name) + '</span>';
                subjectBlock.appendChild(subjectHeader);

                const tgList = document.createElement('div');
                tgList.className = 'sidebar-task-list collapsed';

                subject.task_groups.forEach((tg) => {
                    const btn = document.createElement('button');
                    btn.className = 'sidebar-task-btn';
                    btn.dataset.subjectId = subject.id;
                    btn.dataset.tgId = tg.id;
                    btn.innerHTML =
                        '<span class="task-num">№' + tg.task_number + '</span>' +
                        '<span class="task-name">' + escapeHtml(tg.name) + '</span>' +
                        '<span class="task-count">' + tg.topics.length + '</span>';
                    tgList.appendChild(btn);
                });

                subjectBlock.appendChild(tgList);
                sidebar.appendChild(subjectBlock);

                subjectHeaders.push(subjectHeader);
                subjectLists.push(tgList);

                subjectHeader.addEventListener('click', () => {
                    const isCurrentlyOpen = !tgList.classList.contains('collapsed');
                    subjectLists.forEach((list) => list.classList.add('collapsed'));
                    subjectHeaders.forEach((h) => {
                        const ch = h.querySelector('.chevron');
                        if (ch) ch.textContent = '▸';
                    });
                    if (!isCurrentlyOpen) {
                        tgList.classList.remove('collapsed');
                        subjectHeader.querySelector('.chevron').textContent = '▾';
                    }
                });
            });

            function renderTopics(subjectName, tg) {
                topicPanel.classList.remove('tutor-mode');
                topicPanel.innerHTML = '';
                const header = document.createElement('div');
                header.className = 'topic-panel-header';
                header.innerHTML =
                    '<div class="tp-breadcrumb">' + escapeHtml(subjectName) +
                        ' <span class="tp-sep">/</span> Задание ' + tg.task_number + '</div>' +
                    '<h2 class="tp-title">' + escapeHtml(tg.name) + '</h2>' +
                    '<div class="tp-meta">' + tg.topics.length + ' тем</div>';
                topicPanel.appendChild(header);
                if (!tg.topics.length) {
                    const empty = document.createElement('div');
                    empty.className = 'topic-panel-empty';
                    empty.innerHTML = '<div class="empty-hint">[ темы не заданы ]</div>';
                    topicPanel.appendChild(empty);
                    return;
                }
                const list = document.createElement('ul');
                list.className = 'topic-panel-list';
                tg.topics.forEach((t, i) => {
                    const li = document.createElement('li');
                    li.className = 'topic-panel-item';
                    li.dataset.topicId = t.id;
                    li.innerHTML =
                        '<span class="topic-num">' + String(i + 1).padStart(2, '0') + '</span>' +
                        '<span class="topic-name">' + escapeHtml(t.name) + '</span>' +
                        '<span class="topic-arrow">→</span>';
                    li.addEventListener('click', () => openTutor(subjectName, tg, t));
                    list.appendChild(li);
                });
                topicPanel.appendChild(list);
            }

            const tutorSessions = {};
            const TUTOR_START =
                'Начинаем тему. Коротко объясни главное (3–6 предложений) ' +
                'и сразу дай задание 1 из 5 — самое простое. Условие пиши полностью.';

            function formatAi(text) {
                return escapeHtml(text).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
            }

            function openTutor(subjectName, tg, topic) {
                topicPanel.innerHTML = '';
                topicPanel.classList.add('tutor-mode');

                // ★ Сохраняем последнюю тему
                try { localStorage.setItem('last_topic_id', String(topic.id)); } catch (e) {}

                const session = tutorSessions[topic.id] || (tutorSessions[topic.id] = { history: [] });

                topicPanel.innerHTML =
                    '<div class="tutor-head">' +
                        '<button class="tutor-back">← к темам</button>' +
                        '<div class="tutor-titles">' +
                            '<div class="tp-breadcrumb">' + escapeHtml(subjectName) +
                                ' <span class="tp-sep">/</span> Задание ' + tg.task_number +
                                ' <span class="tp-sep">/</span> ' + escapeHtml(tg.name) + '</div>' +
                            '<h2 class="tp-title">' + escapeHtml(topic.name) + '</h2>' +
                        '</div>' +
                    '</div>' +
                    '<div class="tutor-messages"></div>' +
                    '<div class="tutor-quick">' +
                        '<button class="tutor-quick-btn" data-q="Дай следующее задание, сложнее предыдущего.">Следующее</button>' +
                        '<button class="tutor-quick-btn" data-q="Дай подсказку к текущему заданию, но не говори ответ.">Подсказка</button>' +
                        '<button class="tutor-quick-btn" data-q="Объясни теорию по этой теме подробнее, с примером.">Теория</button>' +
                        '<button class="tutor-quick-btn tutor-open-global">→ В общий чат</button>' +
                    '</div>' +
                    '<div class="tutor-input-row">' +
                        '<textarea class="tutor-input" rows="2" placeholder="Твой ответ или вопрос... (Enter — отправить)"></textarea>' +
                        '<button class="tutor-send">Отправить</button>' +
                    '</div>';

                const box = topicPanel.querySelector('.tutor-messages');
                const input = topicPanel.querySelector('.tutor-input');
                const sendBtn = topicPanel.querySelector('.tutor-send');
                const quickBtns = topicPanel.querySelectorAll('.tutor-quick-btn:not(.tutor-open-global)');
                let busy = false;

                function scrollDown() { box.scrollTop = box.scrollHeight; }

                function addMsg(role, text) {
                    const div = document.createElement('div');
                    div.className = 'tutor-msg ' + (role === 'user' ? 'tutor-user' : 'tutor-ai');
                    div.innerHTML = role === 'user'
                        ? '<span class="tutor-prompt">&gt;</span> ' + escapeHtml(text)
                        : formatAi(text);
                    box.appendChild(div);
                    scrollDown();
                    return div;
                }

                function setBusy(v) {
                    busy = v;
                    sendBtn.disabled = v;
                    input.disabled = v;
                    quickBtns.forEach(b => b.disabled = v);
                }

                async function send(text, hidden = false) {
                    if (busy) return;
                    session.history.push({ role: 'user', content: text, hidden });
                    if (!hidden) addMsg('user', text);
                    setBusy(true);
                    const loading = document.createElement('div');
                    loading.className = 'tutor-msg tutor-loading';
                    loading.textContent = '> ИИ думает...';
                    box.appendChild(loading);
                    scrollDown();

                    const result = await API.tutor({
                        subject: subjectName,
                        task_number: tg.task_number,
                        task_name: tg.name,
                        topic: topic.name,
                        topic_id: topic.id,
                        messages: session.history.map(m => ({ role: m.role, content: m.content })),
                    });

                    const stillOpen = document.body.contains(box);

                    if (result.ok) {
                        const answer = result.data.answer;
                        session.history.push({ role: 'assistant', content: answer });
                        if (stillOpen) {
                            loading.remove();
                            addMsg('assistant', answer);
                            if (result.data.recorded === 'error') {
                                const note = document.createElement('div');
                                note.className = 'tutor-note tutor-note-err';
                                note.textContent = '✖ ошибка записана в журнал';
                                box.appendChild(note);
                            } else if (result.data.recorded === 'correct') {
                                const note = document.createElement('div');
                                note.className = 'tutor-note tutor-note-ok';
                                note.textContent = '✔ решено верно';
                                box.appendChild(note);
                            }
                            scrollDown();
                        }
                    } else {
                        session.history.pop();
                        if (stillOpen) {
                            loading.remove();
                            const err = document.createElement('div');
                            err.className = 'tutor-msg tutor-error';
                            const detail = (result.error && (result.error.detail || result.error.message)) || 'неизвестная ошибка';
                            err.innerHTML = '> ОШИБКА: ' + escapeHtml(detail) + '<br>';
                            const retry = document.createElement('button');
                            retry.className = 'tutor-quick-btn';
                            retry.textContent = 'Повторить';
                            retry.addEventListener('click', () => { err.remove(); send(text, hidden); });
                            err.appendChild(retry);
                            box.appendChild(err);
                            scrollDown();
                        }
                    }
                    if (stillOpen) { setBusy(false); input.focus(); }
                }

                session.history.forEach(m => { if (!m.hidden) addMsg(m.role, m.content); });

                const backBtn = topicPanel.querySelector('.tutor-back');
                backBtn.addEventListener('click', () => renderTopics(subjectName, tg));

                function onEsc(e) {
                    if (!document.body.contains(box)) {
                        document.removeEventListener('keydown', onEsc);
                        return;
                    }
                    if (e.key === 'Escape') backBtn.click();
                }
                document.addEventListener('keydown', onEsc);

                quickBtns.forEach(b => b.addEventListener('click', () => send(b.dataset.q)));

                // ★ Кнопка «В общий чат»
                const globalBtn = topicPanel.querySelector('.tutor-open-global');
                if (globalBtn) {
                    globalBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        try { localStorage.setItem('last_topic_id', String(topic.id)); } catch (err) {}
                        window.location.href = 'chat.html';
                    });
                }

                sendBtn.addEventListener('click', () => {
                    const text = input.value.trim();
                    if (!text) return;
                    input.value = '';
                    send(text);
                });
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendBtn.click();
                    }
                });

                if (!session.history.length) send(TUTOR_START, true);
                else input.focus();
            }

            let activeBtn = null;
            sidebar.querySelectorAll('.sidebar-task-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    if (activeBtn) activeBtn.classList.remove('active');
                    btn.classList.add('active');
                    activeBtn = btn;
                    const subjectId = parseInt(btn.dataset.subjectId, 10);
                    const tgId = parseInt(btn.dataset.tgId, 10);
                    const subject = subjects.find(s => s.id === subjectId);
                    const tg = subject.task_groups.find(g => g.id === tgId);
                    renderTopics(subject.name, tg);
                });
            });

            // === 12. ПЕРЕХОД ИЗ ПЛАНИРОВЩИКА В ТЕМУ ===
            const urlParams = new URLSearchParams(window.location.search);
            const targetTopicId = parseInt(urlParams.get('topic'), 10);
            const autoOpen = urlParams.get('auto') === '1';

            if (targetTopicId) {
                try { localStorage.setItem('last_topic_id', String(targetTopicId)); } catch (e) {}

                setTimeout(async () => {
                    let foundSubject = null;
                    let foundTG = null;
                    for (const subj of subjects) {
                        for (const tg of subj.task_groups) {
                            for (const t of tg.topics) {
                                if (t.id === targetTopicId) {
                                    foundSubject = subj;
                                    foundTG = tg;
                                    break;
                                }
                            }
                            if (foundSubject) break;
                        }
                        if (foundSubject) break;
                    }
                    if (!foundSubject) return;

                    const subjectBlocks = sidebar.querySelectorAll('.sidebar-subject');
                    subjectBlocks.forEach(block => {
                        const nameEl = block.querySelector('.subject-name');
                        if (nameEl && nameEl.textContent.trim() === foundSubject.name) {
                            const header = block.querySelector('.sidebar-subject-header');
                            const list = block.querySelector('.sidebar-task-list');
                            if (header && list && list.classList.contains('collapsed')) header.click();
                        }
                    });

                    let foundBtn = null;
                    sidebar.querySelectorAll('.sidebar-task-btn').forEach(btn => {
                        if (parseInt(btn.dataset.tgId, 10) === foundTG.id) foundBtn = btn;
                    });

                    if (foundBtn) {
                        foundBtn.click();
                        setTimeout(() => {
                            const items = topicPanel.querySelectorAll('.topic-panel-item');
                            items.forEach(item => {
                                if (parseInt(item.dataset.topicId, 10) === targetTopicId) {
                                    item.classList.add('topic-highlight');
                                    if (autoOpen) item.click();
                                }
                            });
                            setTimeout(() => {
                                const hl = topicPanel.querySelector('.topic-highlight');
                                if (hl) hl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            }, 300);
                        }, 400);
                    }
                }, 300);
            }
        })();
    }

    // ============================================================
    // 10. ЖУРНАЛ ОШИБОК (errors.html)
    // ============================================================
    const errList = document.getElementById('errorsList');
    const weakList = document.getElementById('weakTopics');

    if (errList && weakList) {
        (async () => {
            const result = await API.errors();
            if (!result.ok) {
                const msg = '<div class="placeholder" style="color:#ff3355;">[ ошибка — backend запущен? ]</div>';
                errList.innerHTML = msg;
                weakList.innerHTML = msg;
                return;
            }
            const { errors, weak_topics } = result.data;

            if (!errors.length) {
                errList.innerHTML = '<div class="placeholder">[ пусто — ошибок пока нет ]</div>';
            } else {
                errList.innerHTML = errors.map(e => {
                    const where = [e.subject, e.task_number ? 'Задание ' + e.task_number : null, e.topic]
                        .filter(Boolean).map(escapeHtml).join(' <span class="tp-sep">/</span> ');
                    const date = e.created_at
                        ? new Date(e.created_at + 'Z').toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' })
                        : '';
                    return '<div class="err-item">' +
                        '<div class="err-head"><span class="err-where">' + where + '</span>' +
                        '<span class="err-date">' + escapeHtml(date) + '</span></div>' +
                        (e.question ? '<div class="err-q">' + escapeHtml(e.question) + '</div>' : '') +
                        '<div class="err-row"><span class="err-label">твой ответ</span>' +
                            '<span class="err-bad">' + escapeHtml(e.user_answer || '—') + '</span></div>' +
                        (e.correct_answer
                            ? '<div class="err-row"><span class="err-label">правильно</span>' +
                              '<span class="err-good">' + escapeHtml(e.correct_answer) + '</span></div>'
                            : '') +
                        (e.description
                            ? '<div class="err-row"><span class="err-label">ошибка</span>' +
                              '<span class="err-desc">' + escapeHtml(e.description) + '</span></div>'
                            : '') +
                        '</div>';
                }).join('');
            }

            if (!weak_topics.length) {
                weakList.innerHTML = '<div class="placeholder">[ появится после первых ошибок ]</div>';
            } else {
                weakList.innerHTML = weak_topics.map(w => {
                    const pct = Math.min(100, Math.round(w.errors / w.attempts * 100));
                    const where = [w.subject, w.task_number ? '№' + w.task_number : null]
                        .filter(Boolean).map(escapeHtml).join(' · ');
                    return '<div class="weak-item">' +
                        '<div class="weak-top"><span class="weak-name">' + escapeHtml(w.topic) + '</span>' +
                        '<span class="weak-count">' + w.errors + ' ошиб. / ' + w.attempts + ' попыт.</span></div>' +
                        '<div class="weak-where">' + where + '</div>' +
                        '<div class="weak-bar"><i style="width:' + pct + '%"></i></div>' +
                        '</div>';
                }).join('');
            }
        })();
    }

    // ============================================================
    // 13. ПЛАНИРОВЩИК ПО PDF (planner.html)
    // ============================================================
    const dateInput = document.getElementById('dateInput');
    const loadTodayBtn = document.getElementById('loadTodayBtn');
    const loadDateBtn = document.getElementById('loadDateBtn');
    const prevDayBtn = document.getElementById('prevDayBtn');
    const nextDayBtn = document.getElementById('nextDayBtn');
    const newPlanContainer = document.getElementById('planContainer');
    const phasesContainer = document.getElementById('phasesContainer');

    if (newPlanContainer && loadDateBtn) {
        function shiftDate(dateStr, days) {
            const d = new Date(dateStr);
            d.setDate(d.getDate() + days);
            return d.toISOString().slice(0, 10);
        }

        function renderPlan(plan) {
            if (!plan.items || !plan.items.length) {
                newPlanContainer.innerHTML = '<div class="placeholder">[ на этот день в плане пусто ]</div>';
                return;
            }
            let html = '<div class="plan-header">' +
                '<div class="plan-date">' + plan.date + '</div>' +
                '<div class="plan-summary">' +
                    'Фаза: <b>' + escapeHtml(plan.phase || '—') + '</b> · ' +
                    'Режим: <b>' + plan.mode + '</b>' +
                '</div>' +
            '</div>';

            const bySubject = {};
            plan.items.forEach(it => {
                const key = it.subject_code || 'other';
                if (!bySubject[key]) bySubject[key] = { name: it.subject, items: [] };
                bySubject[key].items.push(it);
            });

            const subjOrder = ['math', 'phys', 'rus', 'chem'];
            const subjTitles = { math: '📐 МАТЕМАТИКА', phys: '⚛ ФИЗИКА', rus: '📖 РУССКИЙ', chem: '🧪 ХИМИЯ' };

            subjOrder.forEach(code => {
                const group = bySubject[code];
                if (!group) return;
                html += '<div class="plan-subject">';
                html += '<div class="plan-subject-title">' + (subjTitles[code] || code.toUpperCase()) + '</div>';
                html += '<ul class="plan-list">';
                group.items.forEach(item => {
                    html += '<li class="plan-item plan-new" ' +
                                'data-topic-id="' + item.topic_id + '">' +
                        '<div class="plan-item-type">' +
                            'Задание ' + (item.task_number || '—') +
                            ' · ' + item.minutes + ' мин →' +
                        '</div>' +
                        '<div class="plan-item-name">' + escapeHtml(item.topic_name) + '</div>' +
                        '<div class="plan-item-meta">' + escapeHtml(item.task_group_name || '') + '</div>' +
                    '</li>';
                });
                html += '</ul></div>';
            });

            newPlanContainer.innerHTML = html;

            newPlanContainer.querySelectorAll('.plan-item').forEach(li => {
                li.addEventListener('click', () => {
                    const tid = li.dataset.topicId;
                    if (!tid) return;
                    if (glitchOverlay) {
                        glitchOverlay.classList.add('active');
                        document.body.classList.add('glitching');
                        setTimeout(() => {
                            window.location.href = 'subjects.html?topic=' + tid + '&auto=1';
                        }, 550);
                    } else {
                        window.location.href = 'subjects.html?topic=' + tid + '&auto=1';
                    }
                });
            });
        }

        async function loadPlanByDate(dateStr) {
            newPlanContainer.innerHTML = '<div class="placeholder">[ загрузка... ]</div>';
            const result = await API.planByDate(dateStr);
            if (!result.ok) {
                newPlanContainer.innerHTML = '<div class="placeholder" style="color:#ff3355;">[ ошибка или день не найден ]</div>';
                return;
            }
            renderPlan(result.data);
        }

        async function loadToday() {
            newPlanContainer.innerHTML = '<div class="placeholder">[ загрузка... ]</div>';
            const result = await API.planToday();
            if (!result.ok || result.data.error) {
                newPlanContainer.innerHTML = '<div class="placeholder" style="color:#ff3355;">[ ошибка загрузки ]</div>';
                return;
            }
            if (result.data.date) dateInput.value = result.data.date;
            renderPlan(result.data);
        }

        (async () => {
            const result = await API.planPhases();
            if (!result.ok) {
                phasesContainer.innerHTML = '<div class="placeholder">[ ошибка ]</div>';
                return;
            }
            const phases = result.data;
            let html = '<ul class="phases-list">';
            phases.forEach(p => {
                html += '<li class="phase-item">' +
                    '<span class="phase-order">' + String(p.order).padStart(2, '0') + '</span>' +
                    '<span class="phase-name">' + escapeHtml(p.name) + '</span>' +
                    '<span class="phase-dates">' + p.start_date + ' → ' + p.end_date + '</span>' +
                '</li>';
            });
            html += '</ul>';
            phasesContainer.innerHTML = html;
        })();

        loadTodayBtn.addEventListener('click', loadToday);
        loadDateBtn.addEventListener('click', () => loadPlanByDate(dateInput.value));
        prevDayBtn.addEventListener('click', () => {
            dateInput.value = shiftDate(dateInput.value, -1);
            loadPlanByDate(dateInput.value);
        });
        nextDayBtn.addEventListener('click', () => {
            dateInput.value = shiftDate(dateInput.value, 1);
            loadPlanByDate(dateInput.value);
        });
    }

    // ============================================================
    // 14. ОБЩИЙ ЧАТ С ИИ (chat.html)
    // ============================================================
    const chatMessagesEl = document.getElementById('chatMessages');
    const chatInputEl = document.getElementById('chatInput');
    const sendBtnEl = document.getElementById('sendBtn');

    if (chatMessagesEl && chatInputEl && sendBtnEl) {
        const globalHistory = [];
        let globalBusy = false;

        let lastTopicId = null;
        try {
            const saved = localStorage.getItem('last_topic_id');
            if (saved) lastTopicId = parseInt(saved, 10);
        } catch (e) {}

        function addChatMsg(role, text) {
            const ph = document.getElementById('chatPlaceholder');
            if (ph) ph.remove();

            const div = document.createElement('div');
            div.className = 'tutor-msg ' + (role === 'user' ? 'tutor-user' : 'tutor-ai');
            div.innerHTML = role === 'user'
                ? '<span class="tutor-prompt">&gt;</span> ' + escapeHtml(text).replaceAll('\n', '<br>')
                : escapeHtml(text).replaceAll('\n', '<br>').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
            chatMessagesEl.appendChild(div);
            chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
        }

        function setChatBusy(v) {
            globalBusy = v;
            sendBtnEl.disabled = v;
            chatInputEl.disabled = v;
        }

        async function sendGlobal(text, hidden = false) {
            if (globalBusy || !text.trim()) return;
            if (!hidden) addChatMsg('user', text);
            globalHistory.push({ role: 'user', content: text });

            setChatBusy(true);
            const loading = document.createElement('div');
            loading.className = 'tutor-msg tutor-loading';
            loading.textContent = '> ИИ думает...';
            chatMessagesEl.appendChild(loading);
            chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;

            const result = await API.globalChat({
                messages: globalHistory.map(m => ({ role: m.role, content: m.content })),
                topic_id: lastTopicId,
            });

            loading.remove();

            if (result.ok) {
                const answer = result.data.answer;
                globalHistory.push({ role: 'assistant', content: answer });
                addChatMsg('assistant', answer);
            } else {
                globalHistory.pop();
                const err = document.createElement('div');
                err.className = 'tutor-msg tutor-error';
                const detail = (result.error && (result.error.detail || result.error.message)) || 'неизвестная ошибка';
                err.innerHTML = '> ОШИБКА: ' + escapeHtml(detail) + '<br>';
                const retry = document.createElement('button');
                retry.className = 'tutor-quick-btn';
                retry.textContent = 'Повторить';
                retry.addEventListener('click', () => { err.remove(); sendGlobal(text, hidden); });
                err.appendChild(retry);
                chatMessagesEl.appendChild(err);
            }

            setChatBusy(false);
            chatInputEl.focus();
        }

        sendBtnEl.addEventListener('click', () => {
            const text = chatInputEl.value.trim();
            if (!text) return;
            chatInputEl.value = '';
            sendGlobal(text);
        });

        chatInputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendBtnEl.click();
            }
        });

        document.querySelectorAll('.global-chat-quick .tutor-quick-btn').forEach(btn => {
            btn.addEventListener('click', () => sendGlobal(btn.dataset.q));
        });
    }

    // ============================================================
    // ЭКРАНИРОВАНИЕ HTML
    // ============================================================
    function escapeHtml(s) {
        return String(s)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;');
    }

});  // ← КОНЕЦ DOMContentLoaded
    // ============================================================
    // 15. ГЛАВНАЯ — «Что делать сейчас?»
    // ============================================================
    const dashboardContainer = document.getElementById('dashboardContainer');

    if (dashboardContainer) {
        (async () => {
            const result = await API.dashboard();

            if (!result.ok || result.data.error) {
                dashboardContainer.innerHTML =
                    '<div class="placeholder" style="color:#ff3355;">[ план не найден — запусти import_plan.py ]</div>';
                return;
            }

            const d = result.data;

            const percent = d.percent || 0;
            const total = d.items_total || 0;
            const done = d.items_done || 0;
            const minutesLeft = d.minutes_left || 0;

            let html = '<div class="dash-card">' +
                '<div class="dash-head">' +
                    '<span class="dash-label">сегодня</span>' +
                    '<span class="dash-date">' + d.date_human + '</span>' +
                '</div>' +
                '<div class="dash-phase">' +
                    '<span class="dash-phase-label">фаза:</span> ' +
                    '<span class="dash-phase-name">' + escapeHtml(d.phase || '—') + '</span>' +
                '</div>' +
                '<div class="dash-stats">' +
                    '<div class="dash-stat">' +
                        '<div class="dash-stat-num">' + done + '<span>/' + total + '</span></div>' +
                        '<div class="dash-stat-label">заданий</div>' +
                    '</div>' +
                    '<div class="dash-stat">' +
                        '<div class="dash-stat-num">' + percent + '<span>%</span></div>' +
                        '<div class="dash-stat-label">прогресс</div>' +
                    '</div>' +
                    '<div class="dash-stat">' +
                        '<div class="dash-stat-num">' + minutesLeft + '<span>м</span></div>' +
                        '<div class="dash-stat-label">осталось</div>' +
                    '</div>' +
                '</div>' +
                '<div class="dash-bar"><i style="width:' + percent + '%"></i></div>';

            if (total > 0 && done === total) {
                html += '<div class="dash-done">✓ день закрыт — молодец!</div>';
            } else if (total > 0) {
                html += '<a href="planner.html" class="dash-btn">▶ начать занятие →</a>';
            } else {
                html += '<div class="dash-empty">[ на сегодня задач нет ]</div>';
            }

            html += '</div>';
            dashboardContainer.innerHTML = html;
        })();
    }