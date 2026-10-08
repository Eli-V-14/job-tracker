import os
from datetime import date, timedelta

import redis
from flask import Flask

app = Flask(__name__)

# same Redis the tracker writes to; REDIS_HOST is "redis" in Docker Compose and Kubernetes
r = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'), port=6379, decode_responses=True)


def load_applications():
    last_id = int(r.get('next_id') or 0)
    applications = []
    for application_id in range(1, last_id + 1):
        application = r.hgetall(f'application:{application_id}')
        if application:
            applications.append(application)
    return applications


@app.route('/stats')
def stats():
    applications = load_applications()
    total = len(applications)
    if total == 0:
        return {'total': 0, 'this_week': 0, 'response_rate': 0, 'offer_rate': 0,
                'avg_salary_min': 0, 'avg_salary_max': 0}

    week_ago = date.today() - timedelta(days=7)
    this_week = 0
    for application in applications:
        try:
            if date.fromisoformat(application['date_applied']) >= week_ago:
                this_week += 1
        except (KeyError, ValueError):
            pass

    # "responded" = the company got back to you in any way (moved past "applied")
    responded = sum(1 for a in applications if a.get('status') in ('interviewing', 'offer', 'rejected'))
    offers = sum(1 for a in applications if a.get('status') == 'offer')

    return {
        'total': total,
        'this_week': this_week,
        'response_rate': round(100 * responded / total),
        'offer_rate': round(100 * offers / total),
        'avg_salary_min': round(sum(int(a.get('salary_min') or 0) for a in applications) / total),
        'avg_salary_max': round(sum(int(a.get('salary_max') or 0) for a in applications) / total),
    }


@app.route('/health')
def health():
    r.ping()
    return {'status': 'ok'}
