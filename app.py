import json
import os
import socket
import urllib.request

import redis
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# REDIS_HOST is "redis" in Docker Compose and Kubernetes (the service name), localhost otherwise
r = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'), port=6379, decode_responses=True)

STATUSES = ['applied', 'interviewing', 'offer', 'rejected']

# the stats microservice; "stats" is its service name in Docker Compose and Kubernetes
STATS_URL = os.environ.get('STATS_URL', 'http://localhost:5000')


def get_stats():
    # if the stats service is down, return None so the tracker page still works without it
    try:
        with urllib.request.urlopen(f'{STATS_URL}/stats', timeout=2) as response:
            return json.load(response)
    except Exception:
        return None


@app.route('/')
@app.route('/applications')
def applications():
    # each application is a Redis hash at "application:<id>"; "next_id" counts how many ids were handed out
    last_id = int(r.get('next_id') or 0)
    apps = {}
    for application_id in range(last_id, 0, -1):  # newest first
        application = r.hgetall(f'application:{application_id}')
        if application:
            apps[application_id] = application

    counts = {status: 0 for status in STATUSES}
    for application in apps.values():
        counts[application['status']] += 1

    # optional ?status=offer filter, applied after counting so the summary always shows totals
    selected = request.args.get('status')
    if selected in STATUSES:
        apps = {i: a for i, a in apps.items() if a['status'] == selected}

    return render_template('starting-page.html', apps=apps, statuses=STATUSES, counts=counts,
                           selected=selected, pod=socket.gethostname(), stats=get_stats())


@app.route('/applications', methods=['POST'])
def add_application():
    application_id = r.incr('next_id')  # INCR adds 1 and returns the new value in one step
    r.hset(f'application:{application_id}', mapping={
        'company_name': request.form['company_name'],
        'company_description': request.form.get('company_description', ''),
        'job_title': request.form['job_title'],
        'salary_min': request.form['salary_min'],
        'salary_max': request.form['salary_max'],
        'status': 'applied',
        'date_applied': request.form['date_applied'],
    })
    return redirect(url_for('applications'))


@app.route('/applications/<int:application_id>/status', methods=['POST'])
def update_status(application_id):
    r.hset(f'application:{application_id}', 'status', request.form['status'])
    return redirect(url_for('applications'))


@app.route('/applications/<int:application_id>/delete', methods=['POST'])
def delete_application(application_id):
    r.delete(f'application:{application_id}')
    return redirect(url_for('applications'))


@app.route('/health')
def health():
    r.ping()  # raises an error (500) if Redis is unreachable
    return {'status': 'ok'}

# ---------- REST API ----------

FIELDS = ['company_name', 'company_description', 'job_title', 'salary_min', 'salary_max', 'date_applied']
REQUIRED = ['company_name', 'job_title', 'salary_min', 'salary_max', 'date_applied']


@app.route('/api/applications', methods=['GET'])
def api_list_applications():
    last_id = int(r.get('next_id') or 0)
    result = []
    for application_id in range(1, last_id + 1):
        application = r.hgetall(f'application:{application_id}')
        if application:
            result.append({'id': application_id, **application})
    return result


@app.route('/api/applications', methods=['POST'])
def api_create_application():
    data = request.get_json(silent=True) or {}
    missing = [field for field in REQUIRED if not data.get(field)]
    if missing:
        return {'error': f'missing fields: {", ".join(missing)}'}, 400

    application_id = r.incr('next_id')
    application = {field: str(data.get(field, '')) for field in FIELDS}
    application['status'] = 'applied'
    r.hset(f'application:{application_id}', mapping=application)
    return {'id': application_id, **application}, 201


@app.route('/api/applications/<int:application_id>', methods=['GET'])
def api_get_application(application_id):
    application = r.hgetall(f'application:{application_id}')
    if not application:
        return {'error': 'application not found'}, 404
    return {'id': application_id, **application}


@app.route('/api/applications/<int:application_id>', methods=['PUT'])
def api_update_application(application_id):
    key = f'application:{application_id}'
    if not r.exists(key):
        return {'error': 'application not found'}, 404

    data = request.get_json(silent=True) or {}
    if 'status' in data and data['status'] not in STATUSES:
        return {'error': f'status must be one of: {", ".join(STATUSES)}'}, 400

    updates = {field: str(data[field]) for field in FIELDS + ['status'] if field in data}
    if updates:
        r.hset(key, mapping=updates)
    return {'id': application_id, **r.hgetall(key)}


@app.route('/api/applications/<int:application_id>', methods=['DELETE'])
def api_delete_application(application_id):
    if not r.delete(f'application:{application_id}'):
        return {'error': 'application not found'}, 404
    return '', 204