from flask import Flask

app = Flask(__name__)

apps = {
        0:{
            'application_id':0,
            'company_name':'blueberries inc.',
            'company_description':'many blueberries',
            'job_title':'blueberry farmer',
            'salary_min':80000,
            'salary_max':100000,
            'status': 'applied',
            'date_applied': '10-6-2026'
        },
        1:{
            'application_id':1,
            'company_name':'strawberries inc.',
            'company_description':'many strawberries',
            'job_title':'strawberry farmer',
            'salary_min':85000,
            'salary_max':120000,
            'status': 'applied',
            'date_applied':'10-6-2026'
        },
    }

counter = max(apps) + 1

@app.route('/applications')
def applications():
    # return {'next_counter':counter}
    return apps

@app.route('/health')
def start():
    return {"status":"ok"}