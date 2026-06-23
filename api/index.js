const express = require('express');
const { createClient } = require('@supabase/supabase-js');
const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');
const https = require('https');

const app = express();
const publicDir = path.join(__dirname, '..', 'public');
const viewsDir = path.join(__dirname, '..', 'views');

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;
const supabase = supabaseUrl && supabaseKey ? createClient(supabaseUrl, supabaseKey) : null;

app.disable('x-powered-by');
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(
  express.static(publicDir, {
    etag: true,
    maxAge: '1h',
    setHeaders: (res) => {
      res.setHeader('Connection', 'close');
    },
  }),
);

function setFastHeaders(res) {
  res.setHeader('Connection', 'close');
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
}

function isAuthorized(req) {
  const cookie = req.headers.cookie || '';
  return cookie.split(';').some((part) => part.trim() === 'authorized=true');
}

function requireAuth(req, res) {
  if (!isAuthorized(req)) {
    res.status(401).json({ success: false, error: 'Не авторизовано.' });
    return false;
  }
  if (!supabase) {
    res.status(500).json({ success: false, error: 'Supabase не налаштовано.' });
    return false;
  }
  return true;
}

function normalizeDate(value) {
  if (!value) return '';
  if (value instanceof Date && !Number.isNaN(value.getTime())) return value.toISOString().slice(0, 10);

  if (typeof value === 'number') {
    const parsed = XLSX.SSF.parse_date_code(value);
    if (parsed) return `${parsed.y}-${String(parsed.m).padStart(2, '0')}-${String(parsed.d).padStart(2, '0')}`;
  }

  const text = String(value).trim();
  const iso = text.match(/\b(20\d{2})[-./](\d{1,2})[-./](\d{1,2})\b/);
  if (iso) return `${iso[1]}-${iso[2].padStart(2, '0')}-${iso[3].padStart(2, '0')}`;

  const european = text.match(/\b(\d{1,2})[-./](\d{1,2})[-./](20\d{2})\b/);
  if (european) return `${european[3]}-${european[2].padStart(2, '0')}-${european[1].padStart(2, '0')}`;

  return text;
}

function getShiftByColumn(columnIndex) {
  const position = ((columnIndex - 1) % 3) + 1;
  return position === 1 ? 1 : position === 2 ? 2 : 3;
}

function downloadBuffer(url, timeoutMs = 15000) {
  return new Promise((resolve, reject) => {
    const request = https.get(
      url,
      {
        headers: {
          'User-Agent': 'valeo-time-tracker/1.0',
          Connection: 'close',
        },
        timeout: timeoutMs,
      },
      (response) => {
        if (response.statusCode && response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
          response.resume();
          downloadBuffer(response.headers.location, timeoutMs).then(resolve).catch(reject);
          return;
        }

        if (response.statusCode !== 200) {
          response.resume();
          reject(new Error(`Google Sheets повернув статус ${response.statusCode}`));
          return;
        }

        const chunks = [];
        response.on('data', (chunk) => chunks.push(chunk));
        response.on('end', () => resolve(Buffer.concat(chunks)));
      },
    );

    request.on('timeout', () => request.destroy(new Error('Перевищено час очікування завантаження графіка.')));
    request.on('error', reject);
  });
}

app.get('/', (req, res) => {
  setFastHeaders(res);
  const fileName = isAuthorized(req) ? 'dashboard.html' : 'login.html';

  fs.readFile(path.join(viewsDir, fileName), 'utf8', (error, html) => {
    if (error) {
      res.status(500).send('Не вдалося завантажити сторінку.');
      return;
    }

    res.type('html').send(html);
  });
});

app.post('/api/login', (req, res) => {
  setFastHeaders(res);
  if (req.body.password === 'valeo2026') {
    res.setHeader('Set-Cookie', 'authorized=true; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000');
    res.json({ success: true });
    return;
  }

  res.status(401).json({ success: false, error: 'Неправильний пароль.' });
});

app.get('/api/logs', async (req, res) => {
  setFastHeaders(res);
  if (!requireAuth(req, res)) return;

  try {
    const { data, error } = await supabase.from('work_logs').select('*').order('data', { ascending: false });
    if (error) throw error;
    res.json(data || []);
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/add_report', async (req, res) => {
  setFastHeaders(res);
  if (!requireAuth(req, res)) return;

  const plan = Number(req.body.godziny_plan) || 8;
  const fakt = Number(req.body.godziny_fakt) || 8;
  const zmiana = Number(req.body.zmiana) || 1;
  const report = {
    data: req.body.data,
    linia: String(req.body.linia || '').trim(),
    zmiana,
    godziny_plan: plan,
    godziny_fakt: fakt,
    nadgodziny: Math.max(0, fakt - plan),
    godziny_nocne: zmiana === 3 ? 8 : 0,
    komponenty_ok: Number(req.body.komponenty_ok) || 0,
    komponenty_nok: Number(req.body.komponenty_nok) || 0,
  };

  if (!report.data || !report.linia) {
    res.status(400).json({ success: false, error: 'Дата і лінія є обовʼязковими.' });
    return;
  }

  try {
    const { error } = await supabase.from('work_logs').upsert(report, { onConflict: 'data,linia,zmiana' });
    if (error) throw error;
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/sync_schedule', async (req, res) => {
  setFastHeaders(res);
  if (!requireAuth(req, res)) return;

  const searchName = String(req.body.search_name || '').trim().toLowerCase();
  if (searchName.length < 3) {
    res.status(400).json({ success: false, error: 'Введіть мінімум 3 символи ПІБ.' });
    return;
  }

  const sheetId = '1SaN_9NsYdkQ_KSJ0_7ZOil3_yUSwBiqkCrgo19OTrVY';
  const url = `https://docs.google.com/spreadsheets/d/${sheetId}/export?format=xlsx`;

  try {
    const buffer = await downloadBuffer(url);
    const workbook = XLSX.read(buffer, { type: 'buffer', cellDates: true });
    const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(firstSheet, { header: 1, raw: false, defval: '' });
    const detectedShifts = [];

    for (const row of rows) {
      if (!Array.isArray(row) || row.length < 2) continue;
      const date = normalizeDate(row[0]);
      if (!date) continue;

      for (let columnIndex = 1; columnIndex < row.length; columnIndex += 1) {
        const cell = String(row[columnIndex] || '').trim().toLowerCase();
        if (!cell.includes(searchName)) continue;

        const zmiana = getShiftByColumn(columnIndex);
        const lineHeader = rows[0] && rows[0][columnIndex] ? String(rows[0][columnIndex]).trim() : '';
        detectedShifts.push({
          data: date,
          linia: lineHeader || `Kolumna ${columnIndex + 1}`,
          zmiana,
          godziny_plan: 8,
          godziny_fakt: 8,
          nadgodziny: 0,
          godziny_nocne: zmiana === 3 ? 8 : 0,
          komponenty_ok: 0,
          komponenty_nok: 0,
        });
      }
    }

    if (detectedShifts.length > 0) {
      const { error } = await supabase.from('work_logs').upsert(detectedShifts, { onConflict: 'data,linia,zmiana' });
      if (error) throw error;
    }

    res.json({ success: true, count: detectedShifts.length });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/download_excel', async (req, res) => {
  setFastHeaders(res);
  if (!isAuthorized(req)) {
    res.redirect('/');
    return;
  }
  if (!supabase) {
    res.status(500).send('Supabase не налаштовано.');
    return;
  }

  try {
    const { data, error } = await supabase.from('work_logs').select('*').order('data', { ascending: false });
    if (error) throw error;

    const worksheet = XLSX.utils.json_to_sheet(data || []);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Zvit Valeo');
    const buffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });

    res.setHeader('Content-Disposition', 'attachment; filename="zvit_valeo.xlsx"');
    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    res.end(buffer);
  } catch (error) {
    res.status(500).send(error.message);
  }
});

app.get('/logout', (req, res) => {
  setFastHeaders(res);
  res.setHeader('Set-Cookie', 'authorized=false; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict');
  res.redirect('/');
});

if (require.main === module) {
  const port = process.env.PORT || 3000;
  app.listen(port, () => {
    console.log(`Valeo cabinet is running on http://localhost:${port}`);
  });
}

module.exports = app;
