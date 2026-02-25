#!/usr/bin/env bash
set -e

python src/fetch_list.py
python src/fetch_posts.py
python src/analyze.py
python src/highlights.py
python src/action_cards.py
python src/trending.py

python -c "import sqlite3,datetime; c=sqlite3.connect('data/voc.db'); d=datetime.date.today().isoformat(); n=c.execute('select count(*) from posts where date(fetched_at)=?',(d,)).fetchone()[0]; print(f'TODAY_NEW_POSTS: {n}')"
echo "DONE"