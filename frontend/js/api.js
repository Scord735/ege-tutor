// ============================================
// API-МОДУЛЬ // общение с backend
// ============================================

const API_BASE = 'http://127.0.0.1:8000';

async function api(path, options = {}) {
    const url = API_BASE + path;

    const defaultOptions = {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    };

    const finalOptions = { ...defaultOptions, ...options };

    try {
        const response = await fetch(url, finalOptions);
        const data = await response.json();

        if (!response.ok) {
            return { ok: false, status: response.status, error: data };
        }
        return { ok: true, status: response.status, data };
    } catch (err) {
        return { ok: false, status: 0, error: { message: err.message } };
    }
}

const API = {
    health:  () => api('/api/health'),
    ping:    () => api('/api/ping'),
    stats:   () => api('/api/stats'),

    getStudent: () => api('/api/student'),
    saveStudent: (data) => api('/api/student', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    subjects: () => api('/api/subjects'),
    errors:   () => api('/api/errors'),
        // Профиль — прогресс по предметам
    profileStats: () => api('/api/profile-stats'),

    // Старый планировщик (генерирует на лету)
    plannerToday: (minutes) => api('/api/planner/today?minutes=' + minutes),
    plannerWeek:  ()        => api('/api/planner/week'),

    // План из PDF
    planToday:    ()         => api('/api/plan/today'),
    planPhases:   ()         => api('/api/plan/phases'),
    planByDate:   (dateStr)  => api('/api/plan/date/' + dateStr),

    // ИИ-учитель (по теме)
    tutor: (data) => api('/api/ai/tutor', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    // ★ Общий чат с ИИ (видит ошибки, слабые темы, последнюю тему)
    globalChat: (data) => api('/api/ai/global-chat', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

};