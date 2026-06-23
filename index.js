const express = require('express');
const { createClient } = require('@supabase/supabase-js');
const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');
const app = express();

app.use(express.urlencoded({ extended: true }));

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;
const supabase = (supabaseUrl && supabaseKey) ? createClient(supabaseUrl, supabaseKey) : null;

const isAuth = (req) => req.headers.cookie && req.headers.cookie.includes('authorized=true');
const viewsDir = path.join(__dirname, 'views');

// ХАК ШВИДКОСТІ: Зчитуємо файли в пам'ять ОДИН РАЗ при старті сервера, а не при кожному кліку
const loginHtmlTemplate = fs.readFileSync(path.join(viewsDir, 'login.html'), 'utf8');
const dashboardHtmlTemplate = fs.readFileSync(path.join(viewsDir, 'dashboard.html'), 'utf8');

const sendQuickResponse = (res, htmlContent) => {
    const buffer = Buffer.from(htmlContent, 'utf8');
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Content-Length', buffer.length);
    res.setHeader('Connection', 'close');
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.end(buffer);
};

app.get('/', async (req, res) => {
    if (!isAuth(req)) {
        return sendQuickResponse(res, loginHtmlTemplate.replace('<!-- ERROR_PLACEHOLDER -->', ''));
    }

    let logs = [];
    if (supabase) {
        try {
            const { data } = await supabase.from('work_logs').select('*').order('data', { ascending: false });
            logs = data || [];
        } catch (e) { console.log(e); }
    }

    let rowsHtml = logs.map(row => `
        <tr>
            <td>${row.data}</td>
            <td>${row.linia}</td>
            <td>${row.zmiana} зміна</td>
            <td>${row.godziny_fakt} год (Нічні: ${row.godziny_nocne}, Надгодини: ${row.nadgodziny})</td>
            <td><span class="text-success">OK: ${row.komponenty_ok}</span> / <span class="text-danger">NOK: ${row.komponenty_nok}</span></td>
        </tr>
    `).join('');

    if (logs.length === 0) {
        rowsHtml = '<tr><td colspan="5" class="text-center text-muted py-3">База даних порожня. Внеси першу зміну ліворуч!</td></tr>';
    }

    sendQuickResponse(res, dashboardHtmlTemplate.replace('<!-- TABLE_ROWS_PLACEHOLDER -->', rowsHtml));
});

app.post('/login', (req, res) => {
    if (req.body.password === 'valeo2026') {
        res.setHeader('Set-Cookie', 'authorized=true; Path=/; HttpOnly; Secure');
        res.redirect('/');
    } else {
        res.send(loginHtmlTemplate.replace('<!-- ERROR_PLACEHOLDER -->', '<p class="text-danger mt-2 fw-bold">❌ Неправильний пароль!</p>'));
    }
});

app.post('/add_report', async (req, res) => {
    if (!isAuth(req) || !supabase) return res.redirect('/');
    const { data, linia, zmiana, godziny_plan, godziny_fakt, komponenty_ok, komponenty_nok } = req.body;
    const g_plan = parseInt(godziny_plan) || 8;
    const g_fakt = parseInt(godziny_fakt) || 8;
    const nadgodziny = Math.max(0, g_fakt - g_plan);
    const godziny_nocne = parseInt(zmiana) === 3 ? Math.min(8, g_fakt) : 0;
    
    try {
        await supabase.from('work_logs').upsert({
            data, linia, zmiana: parseInt(zmiana),
            godziny_plan: g_plan, godziny_fakt: g_fakt,
            nadgodziny, godziny_nocne,
            komponenty_ok: parseInt(komponenty_ok) || 0,
            komponenty_nok: parseInt(komponenty_nok) || 0
        });
    } catch (e) { console.log(e); }
    res.redirect('/');
});

app.get('/download_excel', async (req, res) => {
    if (!isAuth(req) || !supabase) return res.redirect('/');
    const { data } = await supabase.from('work_logs').select('*').order('data', { ascending: false });
    const worksheet = XLSX.utils.json_to_sheet(data || []);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Звіт_Valeo');
    const buffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });
    res.setHeader('Content-Disposition', 'attachment; filename=zvit_valeo.xlsx');
    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    res.end(buffer);
});

app.get('/logout', (req, res) => {
    res.setHeader('Set-Cookie', 'authorized=false; Path=/; Max-Age=0; HttpOnly; Secure');
    res.redirect('/');
});

module.exports = app;
