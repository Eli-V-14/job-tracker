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
