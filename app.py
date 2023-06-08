import requests
import pandas as pd
from tabula import read_pdf
from flask import Flask, render_template, request, redirect
from flask_bootstrap import Bootstrap
import seaborn as sns

app = Flask(__name__)
app.debug = True
Bootstrap(app)

green_cm = sns.light_palette("green", as_cmap=True)


@app.route('/add_task', methods=['POST'])
def add_task():
    ftv = float(request.form['ftv']) / 100
    url = request.form['url']
    op = request.form['action']
    return get_results(url, ftv, op)


@app.route('/results', methods=['POST'])
def get_results(url=False, ftv=False, operation=False, amount=900):
    if ftv:
        ftv = ftv
    else:
        ftv = int(request.form['ftv']) / 100

    if url:
        url = url
    else :
        url = request.form['url']

    if operation and operation != 'Reset!':
        operation = operation

    if url :
        r = requests.get(url, allow_redirects=True)
        table = pd.read_html(r.content)
        df = table[3].drop(['ID', 'Glider', 'Score', 'Sponsor'], axis=1)

    final_results = []
    pilot_quantity = df.shape[0]
    if operation == 'Add 0 point':
        df['0'] = ['0' for k in range(pilot_quantity)]
    if operation == 'Add 950 points':
        df['950'] = ['950' for k in range(pilot_quantity)]
    if operation == 'Add 1000 points':
        df['1000'] = ['1000' for k in range(pilot_quantity)]
    if operation == 'Add this amount':
        amount = request.form['add_custom_points']
        df[amount] = [amount for k in range(pilot_quantity)]

    column_scores = get_score_column(df)
    df[column_scores] = df[column_scores].applymap(remove_discard_display)

    maxi_scores = get_maximal_scores(df[column_scores])
    if operation and operation != 'Reset!':
        maxi_scores[-1] = 1000

    credit_discard = get_credit_discard(maxi_scores, ftv)

    df_relative = pd.DataFrame()
    i = 0
    for k in column_scores :
        df_relative[i] = df[k].apply(lambda x : x / maxi_scores[i])
        i += 1

    pilots_sorted_scores = []
    for k in range(pilot_quantity) :
        score_list = df_relative.values.tolist()[k]
        score_dict = {v: i for v, i in enumerate(score_list)}
        pilots_sorted_scores.append(dict(sorted(score_dict.items(), key=lambda x:x[1])))

    for k in range(len(pilots_sorted_scores)) :
        pilot_credit = credit_discard
        i = 0
        result = 0

        scores_dict = pilots_sorted_scores[k]
        order = list(scores_dict.keys())

        while pilot_credit > 0 :
            task_number = order[i]
            pilot_score = pilots_sorted_scores[k][task_number] * maxi_scores[task_number]
            if pilot_score < pilot_credit:
                pilot_credit -= maxi_scores[task_number]
                i += 1
            else:
                remaining_coef = 1 - pilot_credit / maxi_scores[task_number]
                pilot_task_result = pilot_score * remaining_coef
                result += pilot_task_result
                pilot_credit = 0
                i += 1

        while i < len(pilots_sorted_scores[k]) :
            task_number = order[i]
            result += pilots_sorted_scores[k][task_number] * maxi_scores[task_number]
            i += 1
        final_results.append(round(result,1))

    df['Results'] = final_results
    df = df.sort_values('Results', ascending = False)
    if operation and operation != "Reset!" :
        df.insert(0, "New Rank", [k+1 for k in range(pilot_quantity)])
        df['diff'] = df['Rank'] - df['New Rank']
        df.style.background_gradient(cmap=green_cm, subset=pd.IndexSlice[:, ['diff']])

    return render_template('index.html',
                           amount = 800,
                           ftv=ftv*100,
                           url=url,
                           table= df.to_html(
                               classes=["table", "table-bordered", "table-striped", "table-hover"],
                               index=False
                           ),
                           op = operation,
                           )

def get_score_column(df) :
    return df.columns[3::]

def remove_discard_display(score):
    score = score.replace('-', '0')

    if "/" in score:
        return float(score.split("/")[1])
    else:
        return float(score)

def get_maximal_scores(df) :
    return df.max().to_frame().T.values.tolist()[0]

def get_credit_discard(maxi_scores, ftv) :
    return sum(maxi_scores) * ftv


@app.route('/')
def hello_world():
    return render_template('index.html')


if __name__ == '__main__':
    app.run()
