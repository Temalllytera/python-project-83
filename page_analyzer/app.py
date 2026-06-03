import os
from datetime import datetime

import requests
import validators
from requests import RequestException
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from dotenv import load_dotenv

from page_analyzer.db.database import get_connection
from page_analyzer.parser import parse_page
from page_analyzer.url_normalizer import normalize_url

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


@app.route('/', endpoint='index')
def index():
    return render_template('index.html')


@app.route('/urls', methods=['POST'], endpoint='create_url')
def create_url():
    raw_url = request.form.get('url', '').strip()

    if not raw_url or len(raw_url) > 255 or not validators.url(raw_url):
        flash('Некорректный URL', 'danger')
        return render_template('index.html'), 422

    normalized = normalize_url(raw_url)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM urls WHERE name = %s;',
                (normalized,)
            )
            existing = cur.fetchone()

            if existing:
                flash('Страница уже существует', 'info')
                return redirect(url_for('show_url', id=existing[0]))

            cur.execute(
                '''
                INSERT INTO urls (name, created_at)
                VALUES (%s, %s)
                RETURNING id;
                ''',
                (normalized, datetime.now())
            )
            url_id = cur.fetchone()[0]

    flash('Страница успешно добавлена', 'success')
    return redirect(url_for('show_url', id=url_id))


@app.route('/urls', methods=['GET'], endpoint='urls')
def urls():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    u.id,
                    u.name,
                    u.created_at,
                    c.created_at AS last_check,
                    c.status_code
                FROM urls u
                LEFT JOIN url_checks c ON c.id = (
                    SELECT id FROM url_checks
                    WHERE url_id = u.id
                    ORDER BY created_at DESC
                    LIMIT 1
                )
                ORDER BY u.created_at DESC;
                '''
            )
            rows = cur.fetchall()

    urls_list = [
        {
            'id': row[0],
            'name': row[1],
            'created_at': row[2],
            'last_check': row[3],
            'status_code': row[4],
        }
        for row in rows
    ]

    return render_template('urls.html', urls=urls_list)


@app.route('/urls/<int:id>', endpoint='show_url')
def show_url(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, name, created_at FROM urls WHERE id = %s;',
                (id,)
            )
            url_row = cur.fetchone()

            if not url_row:
                flash('Страница не найдена', 'danger')
                return redirect(url_for('index'))

            cur.execute(
                '''
                SELECT id, status_code, h1, title, description, created_at
                FROM url_checks
                WHERE url_id = %s
                ORDER BY created_at DESC;
                ''',
                (id,)
            )
            checks_rows = cur.fetchall()

    checks = [
        {
            'id': row[0],
            'status_code': row[1],
            'h1': row[2],
            'title': row[3],
            'description': row[4],
            'created_at': row[5],
        }
        for row in checks_rows
    ]

    return render_template(
        'url.html',
        url={
            'id': url_row[0],
            'name': url_row[1],
            'created_at': url_row[2],
        },
        checks=checks,
    )


@app.route('/urls/<int:id>/checks', methods=['POST'], endpoint='create_check')
def create_check(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT name FROM urls WHERE id = %s;',
                (id,)
            )
            url_row = cur.fetchone()

            if not url_row:
                flash('Страница не найдена', 'danger')
                return redirect(url_for('index'))

    url_name = url_row[0]

    try:
        response = requests.get(url_name, timeout=10)
        response.raise_for_status()
    except RequestException:
        flash('Произошла ошибка при проверке', 'danger')
        return redirect(url_for('show_url', id=id))

    parsed = parse_page(response.text)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO url_checks
                    (url_id, status_code, h1, title, description, created_at)
                VALUES (%s, %s, %s, %s, %s, %s);
                ''',
                (
                    id,
                    response.status_code,
                    parsed['h1'],
                    parsed['title'],
                    parsed['description'],
                    datetime.now(),
                )
            )

    flash('Страница успешно проверена', 'success')
    return redirect(url_for('show_url', id=id))
