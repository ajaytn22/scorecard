from flask import Flask, render_template, request, redirect
import sqlite3
import os
import zipfile
from flask import send_file
import openpyxl
from openpyxl.styles import Font

app = Flask(__name__)

# Initialize DB
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team TEXT,
            round TEXT,
            match1_placement INTEGER,
            match1_kills INTEGER,
            match2_placement INTEGER,
            match2_kills INTEGER,
            match1_points INTEGER,
            match2_points INTEGER,
            round_total INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

placement_points = [50, 45, 40, 35, 30, 25, 20, 15, 10, 5, 3, 0]

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM scores')
    rows = c.fetchall()
    conn.close()

    from collections import defaultdict
    round_data = defaultdict(list)
    team_totals = defaultdict(int)

    for row in rows:
        score_id = row[0]  # id
        team = row[1]
        round_name = row[2]
        m1_pts = row[7]
        m2_pts = row[8]
        total = row[9]
        round_data[round_name].append((score_id, team, m1_pts, m2_pts, total))
        team_totals[team] += total

    return render_template("index.html", round_data=round_data, team_totals=team_totals)

@app.route('/export_rounds_excel')
def export_rounds_excel():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM scores')
    rows = c.fetchall()
    conn.close()

    # Group data by round
    from collections import defaultdict
    round_scores = defaultdict(list)
    for row in rows:
        round_name = row[2]
        round_scores[round_name].append(row)

    output_dir = "round_excel_exports"
    os.makedirs(output_dir, exist_ok=True)

    created_files = []

    for round_name, entries in round_scores.items():
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = round_name

        headers = [
            "Team", "Round",
            "Match 1 Placement", "Match 1 Kills", "Match 1 Points",
            "Match 2 Placement", "Match 2 Kills", "Match 2 Points",
            "Round Total"
        ]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FF9900")

        for row in entries:
            team = row[1]
            round_name = row[2]
            if round_name == "Final":
                ws.append([
                    team, round_name,
                    row[3], row[4], row[7],
                    "", "", "",
                    row[7]
                ])
            else:
                ws.append([
                    team, round_name,
                    row[3], row[4], row[7],
                    row[5], row[6], row[8],
                    row[9]
                ])

        file_name = f"{output_dir}/{round_name.replace(' ', '_')}.xlsx"
        wb.save(file_name)
        created_files.append(file_name)

    # Zip them
    zip_path = "firezone_all_rounds.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in created_files:
            zipf.write(file)

    # Clean up Excel files after zipping
    for file in created_files:
        os.remove(file)
    os.rmdir(output_dir)

    return send_file(zip_path, as_attachment=True)


@app.route('/submit', methods=['POST'])
def submit():
    team = request.form['team'].strip()
    round_name = request.form['round']
    m1_place = int(request.form['m1place'])
    m1_kills = int(request.form['m1kills'])
    m2_place = int(request.form['m2place'])
    m2_kills = int(request.form['m2kills'])

    m1_points = placement_points[m1_place - 1] + m1_kills * 5
    m2_points = placement_points[m2_place - 1] + m2_kills * 5
    round_total = m1_points + m2_points

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO scores (
            team, round, match1_placement, match1_kills, match2_placement, match2_kills,
            match1_points, match2_points, round_total
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (team, round_name, m1_place, m1_kills, m2_place, m2_kills, m1_points, m2_points, round_total))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM scores WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
