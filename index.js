const express = require('express');
const { createClient } = require('@supabase/supabase-js');
const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');
const https = require('https');
const app = express();

app.use(express.urlencoded({ extended: true }));
app.use(express.json()); // Додаємо підтримку JSON запитів

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;
const supabase = (supabaseUrl && supabaseKey) ? createClient(supabaseUrl, supabaseKey) : null;

const isAuth = (req) => req.headers.cookie && req.headers.cookie.includes('authorized=true');
const viewsDir = path.join(__dirname, 'views');

// 1. ГОЛОВНИЙ МАРШРУТ: Тепер він ВЗАГАЛІ не робить запитів до бази при завантаженні сторінки!
app.get('/', (req, res) => {
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.setHeader('Connection', 'close'); // Жорстко обриваємо Keep-Alive
    
    if (!isAuth(req)) {
        return fs.readFile(path.join(viewsDir, 'login.html'), 'utf8', (err, html) => {
            res.send(html.replace('<!-- ERROR_PLACEHOLDER -->', ''));
        });
    }

    // Миттєво віддаємо порожній каркас кабінету, сайт завантажиться за 0.01 сек
    fs.readFile(path.join(viewsDir, 'dashboard.html'), 'utf8', (err, html) => {
        res.send(html);
    });
});

// 2. ОКРЕМЕ АПІ ДЛЯ ФОНОВОГО ЗАВАНТАЖЕННЯ ДАНИХ (Працює пасивно після відкриття сайту)
app.get('/api/logs', async (req, res) => {
    if (!isAuth(req) || !supabase) return res.json([]);
    try {
        const { data } = await supabase.from('work_logs').select('*').order('data', { ascending: false });
        res.json(data || []);
    } catch (e) {
        res.json([]);
    }
});

// Автоматичний імпорт графіка з Google Sheets
app.post('/sync_schedule', async (req, res) => {
    if (!isAuth(req) || !supabase) return res.redirect('/');
    const searchName = req.body.search_name.trim().toLowerCase();
    const sheetId = "1SaN_9NsYdkQ_KSJ0_7ZOil3_yUSwBiqkCrgo19OTrVY";
    const url = `https://google.com{sheetId}/export?format=xlsx`;

    https.get(url, (response) => {
        let dataBuffers = [];
        response.on('data', (chunk) => dataBuffers.push(chunk));
        response.on('end', async () => {
            try {
                const buffer = Buffer.concat(dataBuffers);
                const workbook = XLSX.read(buffer, { type: 'buffer' });
                const sheetData = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames], { header: 1 });
                let detectedShifts = [];
                let currentDate = "";

                for (let r = 0; r < sheetData.length; r++) {
                    const row = sheetData[r];
                    if (!row || row.length === 0) continue;
                    if (row && String(row).match(/\d/)) { currentDate = String(row).trim(); }

                    for (let c = 1; c < row.length; c++) {
                        const cellText = String(row[c] || '').trim().toLowerCase();
                        if (cellText.includes(searchName) && searchName.length > 2) {
                            let foundShift = (c % 3 === 0) ? 3 : ((c % 3 === 2) ? 2 : 1);
                            let dbDate = currentDate || new Date().toISOString().split('T')[0];
                            detectedShifts.push({
                                data: dbDate, linia: "LF74", zmiana: foundShift, godziny_plan: 8, godziny_fakt: 8,
                                nadgodziny: 0, godziny_nocne: foundShift === 3 ? 8 : 0, komponenty_ok: 0, komponenty_nok: 0
                            });
                        }
                    }
                }
                if (detectedShifts.length > 0) {
                    for (const shift of detectedShifts) { await supabase.from('work_logs').upsert(shift); }
                }
                res.redirect('/');
            } catch (err) { res.redirect('/'); }
        });
    }).on('error', () => res.redirect('/'));
});

app.post('/login', (req, res) => {
    if (req.body.password === 'valeo2026') {
        res.setHeader('Set-Cookie', 'authorized=true; Path=/; HttpOnly; Secure');
        res.redirect('/');
    } else {
        fs.readFile(path.join(viewsDir, 'login.html'), 'utf8', (err, html) => {
            res.send(html.replace('<!-- ERROR_PLACEHOLDER -->', '<p class="text-danger mt-2 fw-bold">❌ Neправильний пароль!</p>'));
        });
    }
});

app.post('/add_report', async (req, res) => {
    if (!isAuth(req) || !supabase) return res.redirect('/');
    const { data, linia, zmiana, godziny_plan, godziny_fakt, komponenty_ok, komponenty_nok } = req.body;
    const g_plan = parseInt(godziny_plan) || 8; const g_fakt = parseInt(godziny_fakt) || 8;
    const nadgodziny = Math.max(0, g_fakt - g_plan);
    const godziny_nocne = parseInt(zmiana) === 3 ? Math.min(8, g_fakt) : 0;
    try {
        await supabase.from('work_logs').upsert({
            data, linia, zmiana: parseInt(zmiana), godziny_plan: g_plan, godziny_fakt: g_fakt,
            nadgodziny, godziny_nocne, komponenty_ok: parseInt(komponenty_ok) || 0, komponenty_nok: parseInt(komponenty_nok) || 0
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
    res.send(buffer);
});

app.get('/logout', (req, res) => {
    res.setHeader('Set-Cookie', 'authorized=false; Path=/; Max-Age=0; HttpOnly; Secure');
    res.redirect('/');
});

module.exports = app;
