import os
from datetime import datetime
from urllib.parse import urlparse

import validators
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

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


@app.route('/', endpoint='index')
def index():
    return render_template('index.html')


@app.route('/urls', methods=['POST'], endpoint='create_url')
def create_url():
    raw_url = request.form.get('url', '').strip()

    if not raw_url or len(raw_url) > 255:
        flash('Некорректный URL', 'danger')
        return redirect(url_for('index'))

    if not validators.url(raw_url):
        flash('Некорректный URL', 'danger')
        return redirect(url_for('index'))

    parsed_url = urlparse(raw_url)
    normalized_url = f'{parsed_url.scheme}://{parsed_url.netloc}'

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM urls WHERE name = %s;',
                (normalized_url,)
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
                (normalized_url, datetime.now())
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
                SELECT id, name, created_at
                FROM urls
                ORDER BY created_at DESC;
                '''
            )
            rows = cur.fetchall()

    urls_list = [
        {
            'id': row[0],
            'name': row[1],
            'created_at': row[2],
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
            row = cur.fetchone()

    if not row:
        flash('Страница не найдена', 'danger')
        return redirect(url_for('index'))

    return render_template(
        'url.html',
        url={
            'id': row[0],
            'name': row[1],
            'created_at': row[2],
        }
    )
