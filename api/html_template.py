# Файл: api/html_template.py

COMBINED_HTML = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Valeo Cab</title>
    <link href="https://jsdelivr.net" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; font-family: sans-serif; }
        .navbar { background-color: #212529; }
        .card { border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); background-color: #ffffff; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark mb-4">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">🏭 Кабінет Valeo</span>
            {% if authorized %}
                <a href="/logout" class="btn btn-outline-light btn-sm">Вихід</a>
            {% endif %}
        </div>
    </nav>

    <div class="container mb-5">
        <!-- ЕКРАН ВХОДУ -->
        {% if not authorized %}
        <div class="row justify-content-center">
            <div class="col-md-4 card p-4 text-center mt-5">
                <h3>🔒 Вхід до кабінету</h3>
                <form method="POST" class="mt-3">
                    <input type="password" name="password" class="form-control mb-3" placeholder="Введіть особистий пароль" required>
                    <button type="submit" class="btn btn-primary w-100">Увійти</button>
                </form>
                {% if error %}
                    <p class="text-danger mt-2 fw-bold">{{ error }}</p>
                {% endif %}
            </div>
        </div>
        {% endif %}

        <!-- ГОЛОВНА ПАНЕЛЬ -->
        {% if authorized %}
        <div class="row g-4">
            <!-- Форма внесення рапорту -->
            <div class="col-md-4">
                <div class="card p-4">
                    <h4>📝 Внесення рапорту за зміну</h4>
                    <form action="/add_report" method="POST" class="mt-3">
                        <label class="form-label">Дата зміни</label>
                        <input type="date" name="data" class="form-control mb-2" required>
                        
                        <label class="form-label">Назва лінії</label>
                        <input type="text" name="linia" class="form-control mb-2" value="LF74" required>
                        
                        <label class="form-label">Зміна</label>
                        <select name="zmiana" class="form-select mb-2">
                            <option value="1">1 зміна</option>
                            <option value="2">2 зміна</option>
                            <option value="3">3 зміна</option>
                        </select>
                        
                        <label class="form-label">Планові години</label>
                        <input type="number" name="godziny_plan" class="form-control mb-2" value="8">
                        
                        <label class="form-label">Фактичні години</label>
                        <input type="number" name="godziny_fakt" class="form-control mb-3" value="8">
                        
                        <hr>
                        <label class="form-label text-success fw-bold">Перевірено ламп (OK)</label>
                        <input type="number" name="komponenty_ok" class="form-control mb-2" value="0">
                        
                        <label class="form-label text-danger fw-bold">Брак (NOK)</label>
                        <input type="number" name="komponenty_nok" class="form-control mb-3" value="0">
                        
                        <button type="submit" class="btn btn-success w-100">Зберегти в базу</button>
                    </form>
                </div>
            </div>
            
            <!-- Таблиця та кнопка скачування Excel -->
            <div class="col-md-8">
                <div class="card p-4 h-100">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h4>📊 Твої відпрацьовані зміни</h4>
                        <a href="/download_excel" class="btn btn-outline-primary btn-sm">📥 Скачати Excel</a>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-hover table-striped">
                            <thead class="table-dark">
                                <tr>
                                    <th>Дата</th>
                                    <th>Лінія</th>
                                    <th>Зміна</th>
                                    <th>Години</th>
                                    <th>Рапорт деталей</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for row in logs %}
                                <tr>
                                    <td>{{ row.data }}</td>
                                    <td>{{ row.linia }}</td>
                                    <td>{{ row.zmiana }} зміна</td>
                                    <td>{{ row.godziny_fakt }} год (Нічні: {{ row.godziny_nocne }}, Надгодини: {{ row.nadgodziny }})</td>
                                    <td><span class="text-success">OK: {{ row.komponenty_ok }}</span> / <span class="text-danger">NOK: {{ row.komponenty_nok }}</span></td>
                                </tr>
                                {% else %}
                                <tr><td colspan="5" class="text-center text-muted py-3">База даних порожня. Внеси першу зміну ліворуч!</td></tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""
